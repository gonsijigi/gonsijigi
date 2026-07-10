"""LangGraph 상태 정의 — 그래프의 모든 노드가 읽고 쓰는 공유 메모장.

각 필드에 '누가 쓰고(생산) 누가 읽는지(소비)'를 명시한다 — 노드 간 계약서.
필드를 추가할 때는 run_agent의 초기화에도 반드시 함께 추가할 것(부분 상태 방지).
"""
from typing import TypedDict, Optional


class AgentState(TypedDict):
    user_input: str          # 입력: 사용자 질문 원문 — guardrail·parse·fetch·interpret가 읽음
    stock_codes: list        # 입력: 관심종목 코드 — fetch가 '명시 종목 없음'일 때 읽음
    parsed_stocks: list      # parse가 씀: 질문에서 뽑은 종목 [{code, name}] — fetch·interpret가 읽음
    parsed_keywords: list    # parse가 씀: 질문 키워드(유상증자 등) — interpret의 RAG 검색어
    clarify: bool            # parse가 씀: 무의미 입력 → route_parse가 되묻기 종료에 사용
    disclosures: list        # fetch가 씀: 조회된 공시 목록 — interpret·risk·notify·hitl이 읽음
    interpretation: str      # interpret가 씀: 해석 본문 — notify·hitl이 카드에 담음
    risk_level: str          # risk가 씀: "normal" | "high" — route_risk의 분기 근거
    risk_keywords: list      # risk가 씀: 걸린 고위험 키워드 — hitl이 검토 화면 태그로 전달
    review_disclosure: Optional[dict]  # risk가 씀: 고위험으로 '걸린 그 공시' — hitl이 큐에 넣음
    blocked: bool            # guardrail이 씀 — route_guard의 종료 근거
    response: Optional[str]  # 최종 응답 — blocked/clarify/notify/hitl 중 한 곳이 채움
