import os
import time
import requests

API_BASE = "http://localhost:8000"  # adjust to your backend

def relative_names(paths: list) -> list:
    """Name each file relative to the files' shared folder, e.g. "utils/math.py".

    This is what the AI sees (and what the GUI lists), so local folder names aren't sent.
    """
    if not paths:
        return []
    try:
        base = os.path.dirname(paths[0]) if len(paths) == 1 else os.path.commonpath(paths)
    except ValueError:  # files on different drives share no folder
        base = None
    names = [os.path.relpath(p, base) if base else os.path.basename(p) for p in paths]
    return [n.replace("\\", "/") for n in names]

def _read_files(paths: list) -> list:
    """Load attached files as [{path, content}] for the backend."""
    files = []
    for path, name in zip(paths, relative_names(paths)):
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            raise ValueError(f"{os.path.basename(path)} is not a text file.")
        files.append({"path": name, "content": content})
    return files

def _raise_for_status(resp):
    """Like resp.raise_for_status(), but uses the backend's error message when there is one."""
    if resp.ok:
        return
    try:
        message = resp.json()["error"]
    except (ValueError, KeyError, TypeError):
        resp.raise_for_status()
    else:
        raise RuntimeError(message)

def post_bug(the_bug) -> str:
    """Send the bug report (description, error output, attached files), return its bug id."""
    print('post_bug() method invoked')
    payload = {
        "description": the_bug.get_bug_description(),
        "error_output": the_bug.get_error_output(),
        "files": _read_files(the_bug.get_files()),
    }
    resp = requests.post(f"{API_BASE}/bugs", json=payload, timeout=10)
    _raise_for_status(resp)
    return resp.json()["bug_id"]

# The timeout is above the backend's slowest provider (Ollama, 300s) so slow models aren't cut off.
def get_AI_response(bug_id: str, poll_interval: float = 2.0, timeout: float = 330.0) -> dict:
    """Poll the backend until the AI answer is ready.

    Returns {"answer": plain-text diagnosis, "diagnosis": structured diagnosis with
    summary, explanation, suspected_locations, proposed_fix, confidence, parse_error}.
    """
    print('get_AI_response() method invoked')
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{API_BASE}/bugs/{bug_id}/response", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "done":
            return {"answer": data["answer"], "diagnosis": data["diagnosis"]}
        if data.get("status") == "error":
            raise RuntimeError(data.get("error", "The diagnosis could not be completed."))
        time.sleep(poll_interval)
    raise TimeoutError("AI response timed out")

def post_decision(bug_id: str, decision: str, edited_fix: list | None = None):
    """Record whether the user accepted, rejected or modified the AI's suggested fix.

    For "modify", edited_fix is the user's version: [{file, original, replacement}].
    """
    print('post_decision() method invoked')
    payload = {"decision": decision}
    if edited_fix is not None:
        payload["edited_fix"] = edited_fix
    resp = requests.post(f"{API_BASE}/bugs/{bug_id}/decision", json=payload, timeout=10)
    _raise_for_status(resp)
