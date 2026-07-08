"""발표 아침 점검 스크립트 — 인프라 상태 + 오늘 공시 스캔을 한 번에.

실행: python scripts/demo_morning.py          (전체: 점검 + 스캔)
      python scripts/demo_morning.py --check   (점검만 — DART 호출 안 함, 한도 절약)

출력이 알려주는 것:
  1) 지금 라이브 데모가 가능한 상태인가 (키·DB·Ollama·모드)
  2) 오늘 실제 공시를 낸 상장사 목록 → 시연 때 관심종목으로 등록할 후보
  3) 고위험 키워드(유상증자 등) 공시가 있으면 ⚠️ 표시 → HITL 장면을 라이브로!
스캔은 DART를 1회만 호출한다(사용한도 보호). 결과가 없거나 실패하면 리플레이 모드 권고.
"""
from __future__ import annotations
import os
import sys
import warnings

warnings.filterwarnings("ignore", category=SyntaxWarning)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from app.tools.dart import RISK_KEYWORDS  # 고위험 키워드 — 위험도 노드와 동일 기준

MAX_ROWS = 15  # 스캔 출력 상한


def _ok(label: str, good: bool, detail: str = "") -> bool:
    print(f"  {'✓' if good else '✗'} {label}" + (f" — {detail}" if detail else ""))
    return good


def check_env() -> dict:
    """라이브 데모 전제조건 점검. 실패해도 폴백/리플레이로 데모는 가능함을 함께 안내."""
    print("\n[1/2] 인프라 점검")
    r: dict = {}

    r["key"] = _ok("DART_API_KEY", bool(os.environ.get("DART_API_KEY")),
                   "설정됨" if os.environ.get("DART_API_KEY") else "없음 → mock 폴백으로만 동작")

    replay = os.environ.get("REPLAY_MODE", "false").lower() == "true"
    _ok("REPLAY_MODE", True, "true (리플레이)" if replay else "false (라이브)")
    r["replay"] = replay

    # pgvector — RAG 근거용(없어도 해석은 동작, 근거만 빠짐)
    try:
        import psycopg
        conninfo = (f"host={os.environ.get('POSTGRES_HOST', 'localhost')} "
                    f"port={os.environ.get('POSTGRES_PORT', '5432')} "
                    f"dbname={os.environ.get('POSTGRES_DB', 'gonsijigi')} "
                    f"user={os.environ.get('POSTGRES_USER', 'gonsijigi')} "
                    f"password={os.environ.get('POSTGRES_PASSWORD', '')}")
        with psycopg.connect(conninfo, connect_timeout=3):
            r["db"] = _ok("pgvector DB", True, "연결 OK (RAG 근거 사용 가능)")
    except Exception as e:
        r["db"] = _ok("pgvector DB", False,
                      f"연결 실패({e.__class__.__name__}) → RAG 근거 없이 동작(폴백 정상)")

    # Ollama — bge-m3(RAG 검색용)·gemma3n(해석용)
    try:
        import requests
        tags = requests.get("http://localhost:11434/api/tags", timeout=3).json()
        names = [m.get("name", "") for m in tags.get("models", [])]
        r["emb"] = _ok("Ollama bge-m3", any("bge-m3" in n for n in names), "임베딩(RAG 검색)")
        r["llm"] = _ok("Ollama gemma3n", any("gemma3n" in n for n in names),
                       "해석 LLM (없으면 폴백 요약)")
    except Exception:
        r["emb"] = r["llm"] = _ok("Ollama", False, "미응답 → LLM 폴백·RAG 근거 생략으로 동작")
    return r


def scan_today(api_key: str) -> None:
    """오늘 공시를 1회 조회해 시연 후보 종목을 추린다."""
    print("\n[2/2] 오늘 공시 스캔 (DART 1회 호출)")
    import OpenDartReader
    today = datetime.now().strftime("%Y%m%d")
    try:
        listing = OpenDartReader(api_key).list(start=today, end=today)
    except Exception as e:
        print(f"  ✗ 조회 실패({e.__class__.__name__}) → 리플레이 모드로 발표 권고")
        return
    if listing is None or (hasattr(listing, "empty") and listing.empty):
        print("  오늘 공시 없음(아직 이른 시각일 수 있음) → 늦게 재시도하거나 리플레이 모드로")
        return

    risky, normal = [], []
    for _, row in listing.iterrows():
        stock = str(row.get("stock_code", "") or "").strip()
        if not stock:                     # 비상장 제외 — 관심종목 등록이 안 됨
            continue
        item = {"stock": stock,
                "corp": str(row.get("corp_name", "")),
                "report": str(row.get("report_nm", ""))}
        hits = [k for k in RISK_KEYWORDS if k in item["report"]]
        (risky if hits else normal).append((item, hits))

    total = len(risky) + len(normal)
    print(f"  상장사 공시 {total}건 (고위험 후보 {len(risky)}건)")
    print("  ── 시연 등록 후보 (⚠️=고위험 → HITL 장면을 라이브로 가능) ──")
    for item, hits in (risky + normal)[:MAX_ROWS]:
        mark = f"⚠️ [{','.join(hits)}] " if hits else ""
        print(f"   {mark}{item['stock']}  {item['corp']} — {item['report']}")
    if total > MAX_ROWS:
        print(f"   ... 외 {total - MAX_ROWS}건 생략")

    print("\n다음 순서:")
    print("  1. 위에서 종목 하나 고르기 (⚠️ 있으면 그걸로 — HITL까지 라이브)")
    print("  2. 서버 켜고 /watchlist/ 에서 그 종목 등록 → 홈 '새 공시 확인'")
    print("  3. ⚠️ 리허설을 했다면 본 시연 전 서버 재시작 필수 (폴러가 본 공시 기억)")
    print("  4. 여기서 스캔 반복 금지 — DART 사용한도 보호 (필요시 --check 만)")


def main() -> None:
    print("=== 공시지기 발표 아침 점검 ===")
    r = check_env()
    if "--check" in sys.argv:
        print("\n(--check: 스캔 생략)")
        return
    if r.get("replay"):
        print("\nREPLAY_MODE=true 상태 — 스캔 없이 리플레이 데모 준비 완료. "
              "라이브로 가려면 REPLAY_MODE 없이 서버를 켜세요.")
        return
    if not r.get("key"):
        print("\nDART 키가 없어 스캔 불가 → 리플레이 모드로 발표 권고")
        return
    scan_today(os.environ["DART_API_KEY"])


if __name__ == "__main__":
    main()
