"""[노드] 공시 조회 — MCP 도구 호출로 관심 종목의 당일 공시 수집."""
from app.agent.state import AgentState
from app.tools import dart_search


def fetch_node(state: AgentState) -> dict:
    found = []
    for code in state["stock_codes"]:
        found.extend(dart_search(code))
    return {"disclosures": found}
