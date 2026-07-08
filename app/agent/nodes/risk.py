"""[노드] 위험도 판단 — 고위험 공시는 사람 검토(HITL) 경로로."""
from app.agent.state import AgentState
from app.tools import RISK_KEYWORDS


def risk_node(state: AgentState) -> dict:
    # 실제로 고위험 키워드가 걸린 '그 공시'를 찾아 HITL 경로로 넘긴다.
    # (첫 번째 공시가 아니라 걸린 공시를 사용해야 엉뚱한 공시가 큐에 들어가지 않음)
    review = None
    triggered: list[str] = []
    for d in state["disclosures"]:
        hits = [k for k in RISK_KEYWORDS if k in d["report_nm"]]
        if hits:
            review = d
            triggered = hits
            break
    level = "high" if review else "normal"
    return {"risk_level": level, "risk_keywords": triggered,
            "review_disclosure": review}
