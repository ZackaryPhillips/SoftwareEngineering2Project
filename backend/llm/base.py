"""Common interface every LLM provider implements."""


class LLMError(RuntimeError):
    """Raised when a provider can't produce a response (network error, bad reply, etc.)."""


class LLMProvider:
    name = "base"

    def generate(self, prompt: str, json_schema: dict | None = None) -> str:
        """Send the prompt to the model and return its text reply.

        json_schema is a hint for providers that can enforce JSON output;
        providers that can't should ignore it.
        """
        raise NotImplementedError
