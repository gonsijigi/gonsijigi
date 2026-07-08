"""RAG 코퍼스 적재 검증 (읽기 전용) — pgvector에 실제로 무엇이 들어갔는지 실측한다.

우리가 방금 적재 경로 버그를 둘 고쳤으므로(pandas append shim, document_all→document),
A/B 기능을 얹기 전에 코퍼스가 '진짜 원문 + 임베딩'으로 채워졌는지부터 확인한다.

실행: python tests/verify_rag.py
필요: pgvector 컨테이너 + Ollama(bge-m3)가 떠 있어야 함(검색 임베딩용).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

TABLE = "disclosure_corpus"


def _conninfo() -> str:
    return (
        f"dbname={os.environ.get('POSTGRES_DB','gonsijigi')} "
        f"user={os.environ.get('POSTGRES_USER','gonsijigi')} "
        f"password={os.environ.get('POSTGRES_PASSWORD','devpass')} "
        f"host={os.environ.get('POSTGRES_HOST','localhost')} "
        f"port={os.environ.get('POSTGRES_PORT','5432')}"
    )


def check_rows():
    """① 테이블에 몇 개의 청크가 저장됐나 + 서로 다른 공시는 몇 건인가."""
    import psycopg
    try:
        with psycopg.connect(_conninfo(), connect_timeout=5) as conn:
            n = conn.execute(f'SELECT count(*) FROM "{TABLE}"').fetchone()[0]
            # 빈 content 가 있는지(추출 실패가 섞였는지)
            empty = conn.execute(
                f"SELECT count(*) FROM \"{TABLE}\" WHERE content IS NULL OR length(content)=0"
            ).fetchone()[0]
            print(f"① 저장된 청크 수: {n}  (빈 content: {empty})")
            if n == 0:
                print("   ⚠️ 0건 — 적재가 실제로 안 됐다. ingest 로그를 다시 봐야 함.")
            return n
    except Exception as e:
        print(f"① DB 접속/조회 실패: {e.__class__.__name__}: {e}")
        print("   → pgvector 컨테이너가 떠 있는지(docker ps), .env POSTGRES_* 확인 필요")
        return 0


def check_search():
    """② 실제 검색이 '관련 있는' 공시를 낮은 거리로 돌려주나(임베딩 정상 여부)."""
    from app.rag.retriever import search_similar
    queries = ["유상증자 결정", "자기주식 취득", "타법인 주식 양수"]
    for q in queries:
        # score_threshold를 크게 줘서 필터 없이 원시 거리까지 관찰(진단용)
        res = search_similar(q, k=3, score_threshold=999)
        print(f"\n② 검색 '{q}' → {len(res)}건")
        if not res:
            print("   ⚠️ 결과 0 — 임베딩/검색 경로 문제(빈 테이블 or Ollama 미기동)")
        for r in res:
            print(f"   dist={r['score']:.3f}  {r['corp_name']}  {r['report_nm']}")
            print(f"        원문발췌: {r['content'][:60].strip()}...")


if __name__ == "__main__":
    print("=== RAG 코퍼스 검증 ===")
    n = check_rows()
    if n:
        check_search()
    print("\n판정 기준: ①이 45 근처(성공 건수만큼)이고, ②에서 질문과 같은 유형 공시가")
    print("dist 0.3~0.6 수준으로 상위에 뜨면 정상. dist가 다 크거나 엉뚱하면 임베딩 문제.")
