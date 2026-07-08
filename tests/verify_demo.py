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


# ── 1) 리플레이 기본 포트폴리오 → 그래프 실행 ────────────────────────────
#    잡히는 공시: [삼성전자 IR(일반), 에코프로비엠 유상증자(고위험), 카카오 취득(일반)]
#    유상증자가 '두 번째'라 P1 버그가 있으면 삼성전자가 큐에 들어감.
from app.gateway import queue as q
from app.agent import run_agent

q._queue.clear(); q._notifications.clear()
codes = ["005930", "247540", "035720"]
resp = run_agent("verify_user", "오늘 내 종목 공시 뭐 있었어?", codes)
check("고위험 → HITL 검토 대기 응답", "검토 대기" in resp)

items = q.list_queue()
check("검토 큐에 1건 적재", len(items) == 1)
check("[P1] 올바른 공시 선택(에코프로비엠)", bool(items) and items[0]["corp_name"] == "에코프로비엠")
check("[P1] 위험 키워드 '유상증자' 표시", bool(items) and "유상증자" in (items[0].get("risk_keywords") or []))

# ── 2) admin 실경로: 큐 화면 → 승인 → 사용자 알림함 ──────────────────────
from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)
r = c.get("/admin/")
check("admin 큐 화면 200", r.status_code == 200)
check("admin 화면에 올바른 회사 표시", "에코프로비엠" in r.text)
check("[P2] admin XSS: 원시 <script> 미노출", "<script>alert" not in r.text)

if items:
    r = c.post(f"/admin/approve/{items[0]['id']}", follow_redirects=False)
    check("승인 요청 처리(303 리다이렉트)", r.status_code == 303)

inbox = c.get("/admin/inbox")
check("[P2] 승인분이 사용자 알림함에 발송됨", "에코프로비엠" in inbox.text)
check("승인 후 큐 비워짐", len(q.list_queue()) == 0)

# ── 3) 가드레일(매매 판단 차단) 회귀 확인 ───────────────────────────────
resp2 = run_agent("verify_guard", "그래서 지금 팔까?", ["005930"])
check("가드레일: 매매 판단 차단 유지", "매수·매도 판단" in resp2)

print()
if _fail:
    print(f"=== VERIFY FAILED — {_fail}건 실패 ===")
    sys.exit(1)
print("=== VERIFY OK — 데모 경로 정상 동작 ===")
