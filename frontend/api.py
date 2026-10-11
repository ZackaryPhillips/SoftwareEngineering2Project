import time
import requests

API_BASE = "http://localhost:8000"  # adjust to your backend

def post_bug(description: str) -> str:
    """Send the bug description, return a job/ticket id."""
    print('post_bug() method invoked')
    resp = requests.post(f"{API_BASE}/bugs", json={"description": description}, timeout=10)
    resp.raise_for_status()
    return resp.json()["bug_id"]   # or however your backend identifies it

def get_AI_response(bug_id: str, poll_interval: float = 2.0, timeout: float = 60.0) -> str:
    """Poll the backend until the AI answer is ready."""
    print('get_AI_response() method invoked')
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{API_BASE}/bugs/{bug_id}/response", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "done":
            return data["answer"]
        time.sleep(poll_interval)
    raise TimeoutError("AI response timed out")