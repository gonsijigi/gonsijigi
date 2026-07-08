"""데모 경로 통합 검증 — REPLAY_MODE로 실제 그래프 + HITL 큐 + 승인 + 알림함을 태운다.
API 키/pgvector/Ollama 없이(폴백) 그대로 돈다.

실행:
    python tests/verify_demo.py
(REPLAY_MODE 는 스크립트가 자동으로 켠다)
"""
import os, sys

os.environ["REPLAY_MODE"] = "true"           # 로컬 replay_sample.json 사용
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_fail = 0


def check(name, cond):
    global _fail
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        _fail += 1


# ── 1) 리플레이 샘플에서 고위험/일반 종목을 '자동 선정' → 그래프 실행 ──────
#    (샘플은 prepare_replay.py 로 실데이터 재생성되므로 종목을 하드코딩하지 않는다)
#    고위험 공시가 '두 번째'가 되게 배치 — P1 버그(첫 공시만 검토)가 있으면 일반 종목이 큐에 들어감.
import json
from pathlib import Path
from app.tools.dart import RISK_KEYWORDS
from app.gateway import queue as q
from app.agent import run_agent

_sample = json.loads((Path(__file__).resolve().parents[1] / "data" / "replay_sample.json")
                     .read_text(encoding="utf-8"))
# 종목별 '첫 항목'이 리플레이 1회차에 반환되므로, 첫 항목 기준으로 고위험/일반 종목을 고른다
_first_by_stock = {}
for _it in _sample:
    _first_by_stock.setdefault(_it["stock_code"], _it)


def _is_risky(it):
    return any(k in it["report_nm"] for k in RISK_KEYWORDS)


RISKY = next(it for it in _first_by_stock.values() if _is_risky(it))
NORMAL = next(it for it in _first_by_stock.values()
              if not _is_risky(it) and it["stock_code"] != RISKY["stock_code"])
RISKY_KW = next(k for k in RISK_KEYWORDS if k in RISKY["report_nm"])
print(f"(샘플 자동 선정) 고위험: {RISKY['corp_name']}[{RISKY_KW}] / 일반: {NORMAL['corp_name']}")

q._queue.clear(); q._notifications.clear()
codes = [NORMAL["stock_code"], RISKY["stock_code"]]
resp = run_agent("verify_user", "오늘 내 종목 공시 뭐 있었어?", codes)
check("고위험 → HITL 검토 대기 응답", "검토 대기" in resp)

items = q.list_queue()
check("검토 큐에 1건 적재", len(items) == 1)
check(f"[P1] 올바른 공시 선택({RISKY['corp_name']})", bool(items) and items[0]["corp_name"] == RISKY["corp_name"])
check(f"[P1] 위험 키워드 '{RISKY_KW}' 표시", bool(items) and RISKY_KW in (items[0].get("risk_keywords") or []))

# ── 2) admin 실경로: 큐 화면 → 승인 → 사용자 알림함 ──────────────────────
from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)
r = c.get("/admin/")
check("admin 큐 화면 200", r.status_code == 200)
check("admin 화면에 올바른 회사 표시", RISKY["corp_name"] in r.text)
check("[P2] admin XSS: 원시 <script> 미노출", "<script>alert" not in r.text)

if items:
    r = c.post(f"/admin/approve/{items[0]['id']}", follow_redirects=False)
    check("승인 요청 처리(303 리다이렉트)", r.status_code == 303)

inbox = c.get("/admin/inbox")
check("[P2] 승인분이 사용자 알림함에 발송됨", RISKY["corp_name"] in inbox.text)
check("승인 후 큐 비워짐", len(q.list_queue()) == 0)

# ── 3) 가드레일(매매 판단 차단) 회귀 확인 ───────────────────────────────
resp2 = run_agent("verify_guard", "그래서 지금 팔까?", ["005930"])
check("가드레일: 매매 판단 차단 유지", "매수·매도 판단" in resp2)

print()
if _fail:
    print(f"=== VERIFY FAILED — {_fail}건 실패 ===")
    sys.exit(1)
print("=== VERIFY OK — 데모 경로 정상 동작 ===")
