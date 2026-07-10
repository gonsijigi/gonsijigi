"""과거 유사 공시 검색 — pgvector 벡터 검색 + 메타데이터 반환.

역할: interpret 노드의 'RAG 검색' 도구. 질문/공시와 비슷한 과거 공시 청크를 찾는다.
위치: 아키텍처의 '데이터 저장소(pgvector)' 박스의 읽기 창구. 적재는 ingest.py.
관련: 데모 장면 ② · 보고서 6.5절.

점수 방향 주의 — 이 점수는 '거리'다: 작을수록 유사, 클수록 무관.
(유사도로 착각하면 필터 방향이 뒤집힌다.)

[COST] score_threshold(기본 0.5)로 무관한 청크를 잘라낸다 — 억지 근거가
프롬프트에 들어가 토큰을 낭비하고 해석을 오염시키는 것을 동시에 막는다.
"""
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
