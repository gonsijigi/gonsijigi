"""[노드] 공시 조회 — MCP 도구 호출로 관심 종목의 공시 수집.
기본은 '당일'만 조회하되, 질문에 '최근' 류 표현이 있으면 최근 7일로 창을 넓힌다."""
from __future__ import annotations
from datetime import datetime, timedelta

from app.agent.state import AgentState
from app.tools import dart_search

# '오늘'을 넘어 과거를 묻는 표현 — 결정론 매칭(파싱 노드와 같은 원칙: LLM 없이 지연·환각 0)
RECENT_WORDS = ("최근", "요즘", "이번주", "이번 주", "지난주", "지난 주")
RECENT_DAYS = 7


def _recent_window(q: str) -> str | None:
    """'최근 공시' 류 질문이면 조회 시작일(YYYYMMDD)을 반환, 아니면 None(당일만)."""
    if any(w in q for w in RECENT_WORDS):
        return (datetime.now() - timedelta(days=RECENT_DAYS)).strftime("%Y%m%d")
    return None


def fetch_node(state: AgentState) -> dict:
    # 사용자가 특정 종목을 명시했으면 '그 종목만' 조회한다(의도 존중 — 관심종목을 섞지 않음).
    # 명시가 없으면 관심종목 전체를 조회한다.
    parsed = [s["code"] for s in state.get("parsed_stocks", []) if s.get("code")]
    codes = parsed if parsed else list(state.get("stock_codes") or [])
    bgn = _recent_window(state.get("user_input") or "")
    found = []
    for code in codes:
        found.extend(dart_search(code, bgn_de=bgn))
    return {"disclosures": found}
