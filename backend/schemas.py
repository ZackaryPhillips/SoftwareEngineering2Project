"""Request data structures and validation for the bug-report API."""
from dataclasses import dataclass, field, asdict

import config


class ValidationError(ValueError):
    """Raised when a request body is missing fields or exceeds limits."""


@dataclass
class SourceFile:
    path: str
    content: str


@dataclass
class BugReport:
    description: str
    error_output: str = ""
    files: list[SourceFile] = field(default_factory=list)

    @classmethod
    def from_json(cls, data) -> "BugReport":
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object.")

        description = data.get("description")
        if not isinstance(description, str) or not description.strip():
            raise ValidationError("'description' is required.")

        error_output = data.get("error_output") or ""
        if not isinstance(error_output, str):
            raise ValidationError("'error_output' must be a string.")

        raw_files = data.get("files") or []
        if not isinstance(raw_files, list):
            raise ValidationError("'files' must be a list.")
        if len(raw_files) > config.MAX_FILES:
            raise ValidationError(f"Too many files (max {config.MAX_FILES}).")

        files = []
        for f in raw_files:
            if not isinstance(f, dict) or not isinstance(f.get("path"), str) \
                    or not isinstance(f.get("content"), str):
                raise ValidationError("Each file needs a 'path' and 'content' string.")
            files.append(SourceFile(f["path"], f["content"]))

        total = len(description) + len(error_output) + sum(len(f.content) for f in files)
        if total > config.MAX_TOTAL_CHARS:
            raise ValidationError(
                f"Submission is {total} characters; the limit is {config.MAX_TOTAL_CHARS}. "
                "Attach fewer or smaller files.")

        return cls(description.strip(), error_output, files)

    def to_dict(self) -> dict:
        return asdict(self)


DECISIONS = ("accept", "reject", "modify")

# Shape we ask the LLM to return. Also passed to Ollama to force JSON output.
DIAGNOSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "explanation": {"type": "string"},
        "suspected_locations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file": {"type": "string"},
                    "function": {"type": "string"},
                    "line": {"type": "integer"},
                    "reason": {"type": "string"},
                },
                "required": ["file", "reason"],
            },
        },
        "proposed_fix": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file": {"type": "string"},
                    "original": {"type": "string"},
                    "replacement": {"type": "string"},
                },
                "required": ["file", "original", "replacement"],
            },
        },
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
    "required": ["summary", "explanation", "suspected_locations", "proposed_fix", "confidence"],
}
