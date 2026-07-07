"""[아키텍처 박스: LangGraph 오케스트레이터] 그래프 조립.
그림 1과 동일: 가드레일 → 조회 → 해석 → 위험도 → (조건부) 알림 | HITL
checkpointer + thread_id 로 사용자별 대화 맥락을 분리한다(보고서 6.4절)."""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from app.agent.state import AgentState
from app.agent.nodes import (guardrail_node, fetch_node, interpret_node,
                             risk_node, notify_node, hitl_node)


def route_guard(state: AgentState) -> str:
    return "blocked" if state["blocked"] else "pass"


def route_risk(state: AgentState) -> str:
    return "high" if state["risk_level"] == "high" else "normal"


workflow = StateGraph(AgentState)
workflow.add_node("guardrail", guardrail_node)
workflow.add_node("fetch", fetch_node)
workflow.add_node("interpret", interpret_node)
workflow.add_node("risk", risk_node)
workflow.add_node("notify", notify_node)
workflow.add_node("hitl", hitl_node)

workflow.add_edge(START, "guardrail")
workflow.add_conditional_edges("guardrail", route_guard, {"pass": "fetch", "blocked": END})
workflow.add_edge("fetch", "interpret")
workflow.add_edge("interpret", "risk")
workflow.add_conditional_edges("risk", route_risk, {"normal": "notify", "high": "hitl"})
workflow.add_edge("notify", END)
workflow.add_edge("hitl", END)

memory = InMemorySaver()
app_graph = workflow.compile(checkpointer=memory)


def run_agent(user_id: str, question: str, stock_codes: list) -> str:
    config = {"configurable": {"thread_id": f"user_{user_id}"}}
    result = app_graph.invoke(
        {"user_input": question, "stock_codes": stock_codes,
         "disclosures": [], "interpretation": "", "risk_level": "normal",
         "blocked": False, "response": None},
        config=config,
    )
    return result["response"] or "처리 결과가 없습니다."


if __name__ == "__main__":  # 콘솔 데모: python -m app.agent.graph
    codes = ["005930", "247540", "035720"]
    for q in ["오늘 내 종목 공시 뭐 있었어?", "그래서 에코프로비엠 지금 팔까?"]:
        print(f"\n질문: {q}")
        print(run_agent("kim_gaemi", q, codes))
