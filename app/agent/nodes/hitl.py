"""[노드] 컴플라이언스 검토(HITL) — 고위험 공시는 승인 후 발송.
D3: gateway/admin.py 의 검토 큐·승인 버튼과 연결한다. 지금은 표시로 대체."""
from app.agent.state import AgentState
from app.tools import build_notification


def hitl_node(state: AgentState) -> dict:
    d = state["disclosures"][0]
    card = build_notification(d["corp_name"], d["report_nm"],
                              state["interpretation"], d["rcept_no"])
    return {"response": "[컴플라이언스 검토 대기 — 승인 후 발송됩니다]\n" + card}
