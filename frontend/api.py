import os
import time
import requests

API_BASE = "http://localhost:8000"  # adjust to your backend

def _read_files(paths: list) -> list:
    """Load attached files as [{path, content}] for the backend.

    Paths are sent relative to the files' shared folder, so the AI sees
    e.g. "utils/math.py" and local folder names aren't sent.
    """
    if not paths:
        return []
    try:
        base = os.path.dirname(paths[0]) if len(paths) == 1 else os.path.commonpath(paths)
    except ValueError:  # files on different drives share no folder
        base = None
    files = []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            raise ValueError(f"{os.path.basename(path)} is not a text file.")
        name = os.path.relpath(path, base) if base else os.path.basename(path)
        files.append({"path": name.replace("\\", "/"), "content": content})
    return files

def _raise_for_status(resp):
    """Like resp.raise_for_status(), but uses the backend's error message when there is one."""
    if resp.ok:
        return
    try:
        message = resp.json()["error"]
    except (ValueError, KeyError):
        resp.raise_for_status()
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
def get_AI_response(bug_id: str, poll_interval: float = 2.0, timeout: float = 330.0) -> str:
    """Poll the backend until the AI answer is ready."""
    print('get_AI_response() method invoked')
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{API_BASE}/bugs/{bug_id}/response", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "done":
            return data["answer"]
        if data.get("status") == "error":
            raise RuntimeError(data.get("error", "The diagnosis could not be completed."))
        time.sleep(poll_interval)
    raise TimeoutError("AI response timed out")

def post_decision(bug_id: str, decision: str):
    """Record whether the user accepted or rejected the AI's suggested fix."""
    print('post_decision() method invoked')
    resp = requests.post(f"{API_BASE}/bugs/{bug_id}/decision", json={"decision": decision}, timeout=10)
    _raise_for_status(resp)
