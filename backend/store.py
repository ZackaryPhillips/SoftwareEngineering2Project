"""In-memory storage for bug reports and their diagnoses. Data is lost on restart."""
import threading
import uuid

from schemas import BugReport


class BugStore:

    def __init__(self):
        self._bugs = {}
        self._lock = threading.Lock()

    def create(self, report: BugReport) -> str:
        bug_id = uuid.uuid4().hex
        with self._lock:
            self._bugs[bug_id] = {
                "report": report,
                "status": "pending",
                "diagnosis": None,
                "raw_response": None,
                "error": None,
                "decision": None,
            }
        return bug_id

    def get(self, bug_id: str):
        with self._lock:
            bug = self._bugs.get(bug_id)
            return dict(bug) if bug else None

    def complete(self, bug_id: str, diagnosis: dict, raw_response: str):
        self._update(bug_id, status="done", diagnosis=diagnosis, raw_response=raw_response)

    def fail(self, bug_id: str, error: str):
        self._update(bug_id, status="error", error=error)

    def set_decision(self, bug_id: str, decision: dict):
        self._update(bug_id, decision=decision)

    def _update(self, bug_id: str, **fields):
        with self._lock:
            self._bugs[bug_id].update(fields)
