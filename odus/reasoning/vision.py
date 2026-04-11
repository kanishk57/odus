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
    ) -> AnalysisResult:
        """
        Analyze a screenshot with Gemini Vision.

        Args:
            image_bytes: JPEG-compressed screenshot bytes.
            user_context: Optional user-provided context about the issue.
            use_deep_model: If True, use gemini-2.5-pro instead of flash.

        Returns:
            AnalysisResult with structured findings.
        """
        model = self._model_deep if use_deep_model else self._model_fast
        logger.info("Analyzing screenshot | model=%s | context=%r", model, user_context[:80])

        # Build the content parts
        prompt_text = SYSTEM_PROMPT
        if user_context:
            prompt_text += f"\n\n## User Context\n{user_context}"
        prompt_text += (
            "\n\nAnalyze the attached screenshot. "
            "Respond ONLY with the JSON object specified in the output format."
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

            return self._parse_response(raw_text)

        except Exception as e:
            logger.error("Vision API call failed: %s", e)
            return AnalysisResult(
                summary="Analysis failed",
                explanation_for_user=f"I couldn't analyze the screenshot: {e}",
                confidence=0.0,
                raw_response=str(e),
            )

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
