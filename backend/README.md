# Backend

Flask API that collects a bug report (description, error output, source files), sends it to an LLM, and returns a structured diagnosis.

## Run

```
cd backend
pip install -r requirements.txt
copy .env.example .env      # then set LLM_PROVIDER
python app.py               # serves on http://127.0.0.1:8000
```

## LLM providers (`LLM_PROVIDER`)

| Value    | What it uses | Notes |
|----------|--------------|-------|
| `mock`   | Canned response | Default. No network or setup needed. |
| `cmsai`  | Instructor AI service at `http://cmsai:8000/generate/` | Must be on the campus network/VPN. Plain-text API, so the JSON reply is requested in the prompt and parsed best-effort. |
| `ollama` | Local model via [Ollama](https://ollama.com) | Install Ollama, then `ollama pull qwen2.5-coder:7b` (or set `OLLAMA_MODEL`). Output is constrained to the diagnosis JSON schema. |

## API

| Method & path | Body | Returns |
|---|---|---|
| `GET /health` | | `{status, provider}` |
| `POST /bugs` | `{description, error_output?, files?: [{path, content}]}` | `202 {bug_id}` |
| `GET /bugs/<id>/response` | | `{status: pending\|done\|error, diagnosis?, answer?, error?}` |
| `POST /bugs/<id>/decision` | `{decision: accept\|reject\|modify, edited_fix?}` | `{bug_id, decision}` |

`diagnosis` has `summary`, `explanation`, `suspected_locations[]`, `proposed_fix[]` (`file`, `original`, `replacement`), `confidence`, and `parse_error` (true when the model didn't return valid JSON; the raw text is in `explanation`). `answer` is the same diagnosis as plain text, for the current GUI.
