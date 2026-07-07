"""LangGraph 상태 정의 — 그래프의 모든 노드가 읽고 쓰는 공유 메모장."""
from typing import TypedDict, Optional


class AgentState(TypedDict):
    user_input: str
    stock_codes: list
    disclosures: list
    interpretation: str
    risk_level: str          # "normal" | "high"
    risk_keywords: list      # risk_node가 disclosures[0]에서 찾은 키워드 — hitl_node에서 재사용
    blocked: bool
    response: Optional[str]
