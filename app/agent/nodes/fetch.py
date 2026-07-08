"""[노드] 공시 조회 — MCP 도구 호출로 관심 종목의 당일 공시 수집."""
from app.agent.state import AgentState
from app.tools import dart_search


def fetch_node(state: AgentState) -> dict:
    # 사용자가 특정 종목을 명시했으면 '그 종목만' 조회한다(의도 존중 — 관심종목을 섞지 않음).
    # 명시가 없으면 관심종목 전체를 조회한다.
    parsed = [s["code"] for s in state.get("parsed_stocks", []) if s.get("code")]
    codes = parsed if parsed else list(state.get("stock_codes") or [])
    found = []
    for code in codes:
        found.extend(dart_search(code))
    return {"disclosures": found}
