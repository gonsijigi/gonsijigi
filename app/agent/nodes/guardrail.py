"""[노드] 가드레일 — 투자자문성 요청 차단. 1차 키워드 + 2차 LLM 판정의 이중 필터."""
from app.agent.state import AgentState
from app.agent.prompts import GUARD_PROMPT, REFUSAL
from app.llm.client import llm

HARD_HITS = ["살까", "팔까", "사야", "팔아야", "매수해", "매도해", "추천해줘"]


def guardrail_node(state: AgentState) -> dict:
    q = state["user_input"]
    if any(k in q for k in HARD_HITS):
        return {"blocked": True, "response": REFUSAL}
    verdict = llm(GUARD_PROMPT.format(q=q), fallback="PASS")
    if "BLOCK" in verdict.upper():
        return {"blocked": True, "response": REFUSAL}
    return {"blocked": False}
