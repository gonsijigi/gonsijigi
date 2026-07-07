"""과거 유사 공시 검색 — pgvector 벡터 검색 + 메타데이터 반환.
interpret 노드가 이 함수를 호출해 근거를 컨텍스트에 추가한다."""
from langchain_ollama import OllamaEmbeddings
from langchain_postgres import PGVectorStore

from app.rag.db import get_engine

TABLE_NAME = "disclosure_corpus"

_store = None


def _get_store() -> PGVectorStore:
    global _store
    if _store is None:
        engine = get_engine()
        emb = OllamaEmbeddings(model="bge-m3")
        _store = PGVectorStore.create_sync(
            engine=engine,
            table_name=TABLE_NAME,
            embedding_service=emb,
        )
    return _store


def search_similar(query: str, k: int = 5, score_threshold: float = 0.5) -> list[dict]:
    """query와 유사한 과거 공시 청크를 반환.

    점수는 거리(작을수록 유사). score_threshold보다 먼 결과는 제외.

    Returns:
        [{content, corp_name, report_nm, rcept_dt, score}, ...]
        관련 없는 질문이면 빈 리스트(정상).
    """
    try:
        store = _get_store()
    except Exception as e:
        print(f"[경고] pgvector 연결 실패 → 빈 근거: {e.__class__.__name__}")
        return []

    try:
        results = store.similarity_search_with_score(query, k=k)
    except Exception as e:
        print(f"[경고] 벡터 검색 실패 → 빈 근거: {e.__class__.__name__}")
        return []

    out = []
    for doc, score in results:
        if score > score_threshold:
            continue
        meta = doc.metadata or {}
        out.append({
            "content": doc.page_content,
            "corp_name": meta.get("corp_name", ""),
            "report_nm": meta.get("report_nm", ""),
            "rcept_dt": meta.get("rcept_dt", ""),
            "score": round(score, 4),
        })
    return out
