"""PGEngine 팩토리 — .env의 POSTGRES_* 변수로 연결 문자열을 만들어 반환.
ingest.py 와 retriever.py 에서 공용으로 import 한다."""
import os
from dotenv import load_dotenv
from langchain_postgres import PGEngine

load_dotenv()


def get_engine() -> PGEngine:
    user = os.environ["POSTGRES_USER"]
    pw = os.environ["POSTGRES_PASSWORD"]
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ["POSTGRES_DB"]
    url = f"postgresql+psycopg://{user}:{pw}@{host}:{port}/{db}"
    return PGEngine.from_connection_string(url=url)
