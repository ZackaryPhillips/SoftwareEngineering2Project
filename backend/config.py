"""Backend settings, read from environment variables (or a .env file if python-dotenv is installed)."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Which LLM backend to use: "mock", "cmsai", or "ollama"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")

# Instructor-provided AI service
CMSAI_URL = os.getenv("CMSAI_URL", "http://cmsai:8000/generate/")
CMSAI_MAX_TOKENS = int(os.getenv("CMSAI_MAX_TOKENS", "1024"))
CMSAI_TIMEOUT = float(os.getenv("CMSAI_TIMEOUT", "120"))

# Local Ollama server
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))  # Ollama's default context is too small for multi-file prompts
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "300"))

# Limits on what we accept (and therefore send to the AI service)
MAX_FILES = int(os.getenv("MAX_FILES", "10"))
MAX_TOTAL_CHARS = int(os.getenv("MAX_TOTAL_CHARS", "60000"))

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
