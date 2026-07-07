"""[노드] 위험도 판단 — 고위험 공시는 사람 검토(HITL) 경로로."""
from app.agent.state import AgentState
from app.tools import RISK_KEYWORDS


def risk_node(state: AgentState) -> dict:
    joined = " ".join(d["report_nm"] for d in state["disclosures"])
    level = "high" if any(k in joined for k in RISK_KEYWORDS) else "normal"
    return {"risk_level": level}
