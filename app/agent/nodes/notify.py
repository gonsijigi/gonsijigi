"""[노드] 알림 생성·발송 — 출처·면책은 build_notification 이 코드로 강제."""
from app.agent.state import AgentState
from app.tools import build_notification


def notify_node(state: AgentState) -> dict:
    if not state["disclosures"]:
        return {"response": state["interpretation"]}
    d = state["disclosures"][0]
    return {"response": build_notification(d["corp_name"], d["report_nm"],
                                           state["interpretation"], d["rcept_no"])}
