"""Flask backend for the AI-assisted debugging application.

Run:  python app.py        (from the backend/ folder)
"""
import logging
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, jsonify, request

import config
from llm import LLMProvider, get_provider
from prompts import build_prompt, format_diagnosis, parse_diagnosis
from schemas import DECISIONS, DIAGNOSIS_SCHEMA, BugReport, ValidationError
from store import BugStore

log = logging.getLogger(__name__)


def create_app(provider: LLMProvider | None = None) -> Flask:
    app = Flask(__name__)
    store = BugStore()
    provider = provider or get_provider(config.LLM_PROVIDER)
    # LLM calls can take a minute or more, so they run in the background
    # and the client polls GET /bugs/<id>/response.
    executor = ThreadPoolExecutor(max_workers=4)

    def run_diagnosis(bug_id: str, report: BugReport):
        try:
            raw = provider.generate(build_prompt(report), json_schema=DIAGNOSIS_SCHEMA)
            store.complete(bug_id, parse_diagnosis(raw), raw)
        except Exception as e:
            log.exception("Diagnosis failed for bug %s", bug_id)
            store.fail(bug_id, str(e))

    @app.get("/health")
    def health():
        return jsonify(status="ok", provider=provider.name)

    @app.post("/bugs")
    def create_bug():
        try:
            report = BugReport.from_json(request.get_json(silent=True))
        except ValidationError as e:
            return jsonify(error=str(e)), 400

        bug_id = store.create(report)
        executor.submit(run_diagnosis, bug_id, report)
        return jsonify(bug_id=bug_id), 202

    @app.get("/bugs/<bug_id>/response")
    def get_response(bug_id):
        bug = store.get(bug_id)
        if bug is None:
            return jsonify(error="Bug not found."), 404

        body = {"bug_id": bug_id, "status": bug["status"]}
        if bug["status"] == "done":
            body["diagnosis"] = bug["diagnosis"]
            body["answer"] = format_diagnosis(bug["diagnosis"])  # plain text for the current GUI
        elif bug["status"] == "error":
            body["error"] = bug["error"]
        return jsonify(body)

    @app.post("/bugs/<bug_id>/decision")
    def record_decision(bug_id):
        bug = store.get(bug_id)
        if bug is None:
            return jsonify(error="Bug not found."), 404
        if bug["status"] != "done":
            return jsonify(error="No diagnosis to review yet."), 409

        data = request.get_json(silent=True) or {}
        decision = data.get("decision")
        if decision not in DECISIONS:
            return jsonify(error=f"'decision' must be one of {', '.join(DECISIONS)}."), 400
        if decision == "modify" and not isinstance(data.get("edited_fix"), list):
            return jsonify(error="'edited_fix' (a list of fixes) is required when modifying."), 400

        store.set_decision(bug_id, {"decision": decision, "edited_fix": data.get("edited_fix")})
        return jsonify(bug_id=bug_id, decision=decision)

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_app().run(host=config.HOST, port=config.PORT)
