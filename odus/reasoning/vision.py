"""
Gemini Vision API Client.

DEV 2 owns this module.

Sends compressed screenshots to Gemini 2.5 Flash/Pro and returns
structured AnalysisResult objects. Now supports multi-step action plans
with both CLI commands and desktop control actions.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field

from google import genai
from google.genai import types

from odus.reasoning.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class SuggestedCommand:
    """A single command suggested by the AI (legacy format)."""

    command: str
    description: str
    safety_tier: int  # 1=safe, 2=caution, 3=danger


@dataclass
class AnalysisResult:
    """Structured output from the Vision API."""

    summary: str
    explanation_for_user: str
    suggested_commands: list[SuggestedCommand] = field(default_factory=list)
    plan: list[dict] = field(default_factory=list)  # Multi-step action plan
    confidence: float = 0.0
    follow_up_hint: str = ""
    raw_response: str = ""  # Full text for debugging


class VisionAnalyzer:
    """
    Sends images to the Gemini Vision API and returns structured analysis.

    Usage:
        analyzer = VisionAnalyzer()
        result = await analyzer.analyze(jpeg_bytes, "I see an error in my terminal")
    """

    # Maximum conversation turns to keep in memory
    _MAX_HISTORY = 10

    def __init__(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not set. "
                "Copy .env.example to .env and add your key."
            )

        self._client = genai.Client(api_key=api_key)
        self._model_fast = os.environ.get("ODUS_MODEL_FAST", "gemini-2.5-flash")
        self._model_deep = os.environ.get("ODUS_MODEL_DEEP", "gemini-2.5-pro")

        # In-memory conversation history (auto-clears on restart)
        self._history: list[dict[str, str]] = []

        logger.info(
            "VisionAnalyzer initialized | fast=%s | deep=%s",
            self._model_fast,
            self._model_deep,
        )

    async def analyze(
        self,
        image_bytes: bytes,
        user_context: str = "",
        use_deep_model: bool = False,
        image_width: int | None = None,
        image_height: int | None = None,
    ) -> AnalysisResult:
        """
        Analyze a screenshot with Gemini Vision.

        Args:
            image_bytes: JPEG-compressed screenshot bytes.
            user_context: Optional user-provided context about the issue.
            use_deep_model: If True, use gemini-2.5-pro instead of flash.
            image_width, image_height: Resolution of the image being sent.

        Returns:
            AnalysisResult with structured findings.
        """
        model = self._model_deep if use_deep_model else self._model_fast
        logger.info("Analyzing screenshot | model=%s | context=%r", model, user_context[:80])

        # Build the content parts
        prompt_text = SYSTEM_PROMPT
        
        if image_width and image_height:
            prompt_text += f"\n\n## Screenshot Resolution\nResolution: {image_width}x{image_height}"

        # Include conversation history for context
        if self._history:
            prompt_text += "\n\n## Conversation History\n"
            prompt_text += "The following is the history of our conversation so far. "
            prompt_text += "Use this context to understand follow-up questions and maintain continuity.\n"
            for turn in self._history:
                prompt_text += f"\n**User:** {turn['user']}\n"
                prompt_text += f"**Odus:** {turn['assistant']}\n"

        if user_context:
            prompt_text += f"\n\n## Current User Query\n{user_context}"
        prompt_text += (
            "\n\nAnalyze the attached screenshot. "
            "Respond ONLY with the JSON object specified in the output format. "
            "Take the conversation history into account when answering."
        )

        try:
            response = await self._client.aio.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    prompt_text,
                ],
            )

            raw_text = response.text
            logger.debug("Raw API response: %s", raw_text[:500])

            result = self._parse_response(raw_text)

            # Save this exchange to history
            self._history.append({
                "user": user_context or "[screenshot analysis]",
                "assistant": result.summary + " — " + result.explanation_for_user,
            })
            # Trim to max history size
            if len(self._history) > self._MAX_HISTORY:
                self._history = self._history[-self._MAX_HISTORY:]

            logger.info("Conversation history: %d turns", len(self._history))
            return result

        except Exception as e:
            logger.error("Vision API call failed: %s", e)
            message = str(e)
            retry_after = self._extract_retry_delay_seconds(message)

            if retry_after is not None or "RESOURCE_EXHAUSTED" in message or "429" in message:
                retry_text = f"Retry in {retry_after:.0f}s." if retry_after is not None else "Retry later."
                return AnalysisResult(
                    summary="Gemini rate limit reached",
                    explanation_for_user=(
                        f"Gemini is temporarily rate limited. {retry_text}"
                        " Check your API key or wait for the quota window to reset."
                    ),
                    follow_up_hint="Try again after the retry window or update the Gemini API key.",
                    confidence=0.0,
                    raw_response=message,
                )

            return AnalysisResult(
                summary="Analysis failed",
                explanation_for_user=f"I couldn't analyze the screenshot: {message}",
                follow_up_hint="Try again after checking the API key, network connection, or the current screenshot.",
                confidence=0.0,
                raw_response=message,
            )

    def _extract_retry_delay_seconds(self, error_message: str) -> float | None:
        match = re.search(r'retry in ([0-9.]+)s', error_message, re.IGNORECASE)
        if not match:
            return None

        try:
            return float(match.group(1))
        except ValueError:
            return None

    def _parse_response(self, raw_text: str) -> AnalysisResult:
        """Parse the JSON response from Gemini into an AnalysisResult."""
        try:
            # Strip markdown code fences if present
            text = raw_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]  # Remove opening fence line
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            text = text.strip()

            data = json.loads(text)

            # Parse multi-step plan (new format)
            plan = []
            for step in data.get("plan", []):
                plan.append({
                    "step": step.get("step", 0),
                    "action_type": step.get("action_type", ""),
                    "params": step.get("params", {}),
                    "description": step.get("description", ""),
                    "safety_tier": step.get("safety_tier", 2),
                })

            # Parse legacy suggested_commands (backward compat)
            commands = []
            for cmd in data.get("suggested_commands", []):
                commands.append(
                    SuggestedCommand(
                        command=cmd.get("command", ""),
                        description=cmd.get("description", ""),
                        safety_tier=cmd.get("safety_tier", 2),
                    )
                )

            return AnalysisResult(
                summary=data.get("summary", "No summary"),
                explanation_for_user=data.get("explanation_for_user", ""),
                suggested_commands=commands,
                plan=plan,
                confidence=float(data.get("confidence", 0.0)),
                follow_up_hint=data.get("follow_up_hint", ""),
                raw_response=raw_text,
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to parse structured response: %s", e)
            # Graceful fallback — treat the raw text as the explanation
            return AnalysisResult(
                summary="Analysis complete (unstructured)",
                explanation_for_user=raw_text,
                confidence=0.5,
                raw_response=raw_text,
            )
