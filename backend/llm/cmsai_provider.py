"""Instructor-provided AI service (plain prompt in, text out)."""
import requests

from llm.base import LLMError, LLMProvider


class CmsaiProvider(LLMProvider):
    name = "cmsai"

    def __init__(self, url: str, max_tokens: int, timeout: float):
        self.url = url
        self.max_tokens = max_tokens
        self.timeout = timeout

    def generate(self, prompt: str, json_schema: dict | None = None) -> str:
        # The service has no JSON mode, so json_schema is ignored; the prompt asks for JSON instead.
        try:
            resp = requests.post(self.url,
                                 json={"prompt": prompt, "max_tokens": self.max_tokens},
                                 timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()["response"]
        except requests.exceptions.Timeout:
            raise LLMError(f"cmsai service timed out after {self.timeout}s.")
        except requests.exceptions.ConnectionError:
            raise LLMError(f"Could not reach cmsai service at {self.url}. "
                           "Are you on the campus network/VPN?")
        except requests.exceptions.RequestException as e:
            raise LLMError(f"cmsai request failed: {e}")
        except (ValueError, KeyError) as e:
            raise LLMError(f"Invalid response from cmsai service: {e}")
