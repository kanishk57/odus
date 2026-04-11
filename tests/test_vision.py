"""Tests for the Gemini Vision API client."""

from __future__ import annotations

import json
from unittest.mock import patch


from odus.reasoning.vision import VisionAnalyzer


class TestResponseParsing:
    """Test that API responses are correctly parsed into AnalysisResult."""

    def setup_method(self):
        # Patch the genai client so we don't need a real API key
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key-123"}):
            with patch("google.genai.Client"):
                self.analyzer = VisionAnalyzer()

    def test_parse_valid_json_response(self):
        raw = json.dumps({
            "summary": "Package not found error",
            "explanation_for_user": "You need to install the package.",
            "suggested_commands": [
                {
                    "command": "sudo apt install vim",
                    "description": "Install vim editor",
                    "safety_tier": 2,
                }
            ],
            "confidence": 0.92,
            "follow_up_hint": "Check if it installed correctly",
        })
        result = self.analyzer._parse_response(raw)

        assert result.summary == "Package not found error"
        assert result.confidence == 0.92
        assert len(result.suggested_commands) == 1
        assert result.suggested_commands[0].command == "sudo apt install vim"
        assert result.suggested_commands[0].safety_tier == 2

    def test_parse_markdown_fenced_json(self):
        """Model sometimes wraps JSON in ```json ... ``` fences."""
        raw = '```json\n{"summary": "Test", "explanation_for_user": "x", "confidence": 0.5}\n```'
        result = self.analyzer._parse_response(raw)
        assert result.summary == "Test"

    def test_parse_invalid_json_falls_back(self):
        """Unparseable text should gracefully become the explanation."""
        raw = "I see a terminal error but cannot format my response."
        result = self.analyzer._parse_response(raw)
        assert result.summary == "Analysis complete (unstructured)"
        assert raw in result.explanation_for_user

    def test_parse_empty_commands(self):
        raw = json.dumps({
            "summary": "No issues detected",
            "explanation_for_user": "Everything looks fine!",
            "suggested_commands": [],
            "confidence": 0.95,
        })
        result = self.analyzer._parse_response(raw)
        assert len(result.suggested_commands) == 0
        assert result.confidence == 0.95
