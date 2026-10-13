"""Canned responses so the app can be developed and demoed without any AI service."""
import json
import time

from llm.base import LLMProvider


class MockProvider(LLMProvider):
    name = "mock"

    def __init__(self, delay: float = 1.0):
        self.delay = delay

    def generate(self, prompt: str, json_schema: dict | None = None) -> str:
        time.sleep(self.delay)  # simulate model latency so the polling path gets exercised
        return json.dumps({
            "summary": "Mock diagnosis: off-by-one error in loop bounds.",
            "explanation": "This is a canned response from the mock provider. "
                           "Set LLM_PROVIDER=cmsai or LLM_PROVIDER=ollama for real analysis.",
            "suspected_locations": [
                {"file": "example.py", "function": "sum_list", "line": 3,
                 "reason": "range(len(items) + 1) reads one element past the end."}
            ],
            "proposed_fix": [
                {"file": "example.py",
                 "original": "    for i in range(len(items) + 1):",
                 "replacement": "    for i in range(len(items)):"}
            ],
            "confidence": "high",
        })
