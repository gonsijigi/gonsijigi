"""[노드] 컴플라이언스 검토(HITL) — 고위험 공시는 승인 후 발송.
큐에 항목을 적재하고, 사용자에게는 '검토 대기' 메시지만 즉시 반환한다."""
from app.agent.state import AgentState
from app.tools import build_notification
from app.gateway.queue import enqueue


def hitl_node(state: AgentState) -> dict:
    # risk_node가 지목한 '실제 고위험 공시'를 큐에 넣는다(없으면 방어적으로 첫 공시).
    d = state.get("review_disclosure") or state["disclosures"][0]
    card = build_notification(d["corp_name"], d["report_nm"],
                              state["interpretation"], d["rcept_no"])
    enqueue({
        "corp_name":      d["corp_name"],
        "report_nm":      d["report_nm"],
        "rcept_no":       d["rcept_no"],
        "rcept_dt":       d["rcept_dt"],
        "interpretation": state["interpretation"],
        "risk_keywords":  state["risk_keywords"],
        "card":           card,
    })
    return {"response": f"[컴플라이언스 검토 대기 — 승인 후 발송됩니다]\n{card}"}
