"""설정 로더 — 모든 비밀값은 .env 에서만 읽는다 (코드·저장소에 하드코딩 금지)."""
import os
from dotenv import load_dotenv

load_dotenv()

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:8000/v1/")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "EMPTY")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemma-4-e4b-it")
