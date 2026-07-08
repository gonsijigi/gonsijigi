"""LangGraph 상태 정의 — 그래프의 모든 노드가 읽고 쓰는 공유 메모장."""
from typing import TypedDict, Optional


class AgentState(TypedDict):
    user_input: str
    stock_codes: list
    parsed_stocks: list      # parse_node가 질문에서 뽑은 종목 [{code, name}, ...]
    parsed_keywords: list    # parse_node가 질문에서 뽑은 키워드(유상증자 등)
    clarify: bool            # 무의미 입력 → 되묻기 후 종료
    disclosures: list
    interpretation: str
    risk_level: str          # "normal" | "high"
    risk_keywords: list      # risk_node가 실제 걸린 공시에서 찾은 키워드 — hitl_node에서 재사용
    review_disclosure: Optional[dict]  # 고위험으로 걸린 실제 공시 — hitl_node가 큐에 넣음
    blocked: bool
    response: Optional[str]
