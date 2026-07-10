"""[노드] 공시 조회 — 도구(dart_search)를 호출해 해석 대상 공시를 모은다.

역할: '어느 종목을, 어느 기간으로' 조회할지 결정하고 DART 도구를 호출한다.
위치: 파싱 통과 후 첫 도구 사용(Tool Use) 지점.
관련: 데모 장면 ①② · 기본은 당일, '최근' 질문은 7일 창.
"""
from __future__ import annotations
from datetime import datetime, timedelta

from app.agent.state import AgentState
from app.tools import dart_search

# '오늘'을 넘어 과거를 묻는 표현 — 결정론 매칭(파싱 노드와 같은 원칙: LLM 없이 지연·환각 0)
RECENT_WORDS = ("최근", "요즘", "이번주", "이번 주", "지난주", "지난 주")
RECENT_DAYS = 7


def _recent_window(q: str) -> str | None:
    """'최근 공시' 류 질문이면 조회 시작일(YYYYMMDD)을 반환, 아니면 None(당일만).

    왜 7일인가 — 개인투자자의 '최근'은 통상 지난 한 주. 창을 무한정 넓히면
    조회량·해석 대상이 늘어 응답이 느려지고 요지가 흐려진다.
    """
    if any(w in q for w in RECENT_WORDS):
        return (datetime.now() - timedelta(days=RECENT_DAYS)).strftime("%Y%m%d")
    return None


def fetch_node(state: AgentState) -> dict:
    """조회 대상·기간을 정해 dart_search를 호출하고 disclosures를 채운다.

    실패·폴백: dart_search 내부에서 키 없음/호출 실패/한도 초과를 mock으로
        폴백하므로 이 노드는 항상 리스트를 받는다(빈 리스트 포함).
    """
    # [ORCHESTRATION] 조회 범위 결정.
    # 생각: 사용자가 특정 종목을 명시했는가(파싱 결과) → 행동: 명시했으면 '그 종목만'
    #       조회한다(의도 존중 — 관심종목을 섞으면 엉뚱한 회사가 답에 나온다).
    #       명시가 없을 때만 관심종목 전체를 조회한다.
    parsed = [s["code"] for s in state.get("parsed_stocks", []) if s.get("code")]
    codes = parsed if parsed else list(state.get("stock_codes") or [])
    # 생각: 질문이 '최근'을 묻는가 → 행동: 7일 창으로 확장, 아니면 당일만.
    bgn = _recent_window(state.get("user_input") or "")
    found = []
    for code in codes:
        found.extend(dart_search(code, bgn_de=bgn))
    return {"disclosures": found}
