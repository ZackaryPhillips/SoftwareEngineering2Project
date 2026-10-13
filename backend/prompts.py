"""Builds the LLM prompt from a bug report and parses the LLM's reply into a diagnosis."""
import json
import re

from schemas import BugReport

INSTRUCTIONS = """You are a debugging assistant for Python programs.
Analyze the bug report below. Identify the most likely cause, where it is in the code,
and a minimal fix.

Reply with ONLY a JSON object (no markdown, no text before or after it) in this format:
{
  "summary": "one-sentence description of the defect",
  "explanation": "why the bug happens",
  "suspected_locations": [
    {"file": "path", "function": "name", "line": 0, "reason": "why this location is involved"}
  ],
  "proposed_fix": [
    {"file": "path", "original": "exact lines to replace", "replacement": "corrected lines"}
  ],
  "confidence": "low | medium | high"
}
"""


def build_prompt(report: BugReport) -> str:
    parts = [INSTRUCTIONS, "## Bug description", report.description]

    if report.error_output.strip():
        parts += ["## Error output / stack trace", report.error_output]

    for f in report.files:
        # Line numbers help the model point at specific locations.
        numbered = "\n".join(f"{i:4d} | {line}"
                             for i, line in enumerate(f.content.splitlines(), start=1))
        parts += [f"## File: {f.path}", numbered]

    parts.append("## Your JSON response")
    return "\n\n".join(parts)


def parse_diagnosis(raw: str) -> dict:
    """Extract the JSON diagnosis from the model's reply.

    Models (especially the plain-text cmsai service) sometimes wrap JSON in markdown
    fences or add commentary, so we look for the outermost {...}. If that still fails,
    the raw text is returned as the explanation so the user sees something useful.
    """
    text = re.sub(r"```(?:json)?", "", raw)
    start, end = text.find("{"), text.rfind("}")
    try:
        data = json.loads(text[start:end + 1]) if start != -1 and end > start else None
    except json.JSONDecodeError:
        data = None

    if not isinstance(data, dict):
        return {
            "summary": "",
            "explanation": raw.strip(),
            "suspected_locations": [],
            "proposed_fix": [],
            "confidence": "low",
            "parse_error": True,
        }

    return {
        "summary": str(data.get("summary", "")),
        "explanation": str(data.get("explanation", "")),
        "suspected_locations": _list_of_dicts(data.get("suspected_locations")),
        "proposed_fix": _list_of_dicts(data.get("proposed_fix")),
        "confidence": data.get("confidence") if data.get("confidence") in ("low", "medium", "high") else "low",
        "parse_error": False,
    }


def format_diagnosis(d: dict) -> str:
    """Plain-text rendering of a diagnosis, for clients that only display text."""
    if d.get("parse_error"):
        return d["explanation"] + "\n"

    lines = [f"Summary: {d['summary']}", f"Confidence: {d['confidence']}", "",
             "Explanation:", d["explanation"], ""]
    if d["suspected_locations"]:
        lines.append("Suspected locations:")
        for loc in d["suspected_locations"]:
            where = loc.get("file", "?")
            if loc.get("function"):
                where += f" in {loc['function']}()"
            if loc.get("line"):
                where += f", line {loc['line']}"
            lines.append(f"  - {where}: {loc.get('reason', '')}")
        lines.append("")
    for fix in d["proposed_fix"]:
        lines += [f"Proposed fix for {fix.get('file', '?')}:",
                  "--- original", fix.get("original", ""),
                  "+++ replacement", fix.get("replacement", ""), ""]
    return "\n".join(lines)


def _list_of_dicts(value) -> list:
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []
