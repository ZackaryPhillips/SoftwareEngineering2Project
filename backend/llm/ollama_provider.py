"""Local model served by Ollama (https://ollama.com)."""
import requests

from llm.base import LLMError, LLMProvider


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, host: str, model: str, num_ctx: int, timeout: float):
        self.host = host.rstrip("/")
        self.model = model
        self.num_ctx = num_ctx
        self.timeout = timeout

    def generate(self, prompt: str, json_schema: dict | None = None) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_ctx": self.num_ctx},
        }
        if json_schema:
            payload["format"] = json_schema  # Ollama constrains output to this schema

        try:
            resp = requests.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
        except requests.exceptions.Timeout:
            raise LLMError(f"Ollama timed out after {self.timeout}s.")
        except requests.exceptions.ConnectionError:
            raise LLMError(f"Could not reach Ollama at {self.host}. Is it running ('ollama serve')?")

        if resp.status_code == 404:
            raise LLMError(f"Ollama model '{self.model}' not found. Run: ollama pull {self.model}")
        try:
            resp.raise_for_status()
            return resp.json()["message"]["content"]
        except requests.exceptions.RequestException as e:
            raise LLMError(f"Ollama request failed: {e} {resp.text[:200]}")
        except (ValueError, KeyError) as e:
            raise LLMError(f"Invalid response from Ollama: {e}")
