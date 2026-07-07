"""[노드] 위험도 판단 — 고위험 공시는 사람 검토(HITL) 경로로."""
from app.agent.state import AgentState
from app.tools import RISK_KEYWORDS


def risk_node(state: AgentState) -> dict:
    joined = " ".join(d["report_nm"] for d in state["disclosures"])
    level = "high" if any(k in joined for k in RISK_KEYWORDS) else "normal"
    # 키워드는 disclosures[0] 기준 — 큐에 들어가는 공시와 범위를 일치시킨다
    first_nm = state["disclosures"][0]["report_nm"] if state["disclosures"] else ""
    triggered = [k for k in RISK_KEYWORDS if k in first_nm]
    return {"risk_level": level, "risk_keywords": triggered}
