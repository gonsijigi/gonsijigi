"""[노드] RAG 해석 생성 — 근거에 없는 말은 하지 않는다(오픈북 원칙)."""
from app.agent.state import AgentState
from app.agent.prompts import INTERPRET_PROMPT
from app.llm.client import llm
from app.rag.retriever import search_similar  # D2: 과거 유사 공시 근거 추가


def interpret_node(state: AgentState) -> dict:
    if not state["disclosures"]:
        return {"interpretation": "오늘 등록하신 관심 종목에 새 공시가 없습니다."}
    context = "\n".join(
        f"- {d['corp_name']} / {d['report_nm']} / {d['summary']}" for d in state["disclosures"]
    )
    # D2 구현 후: search_similar() 결과(과거 유사 공시)를 context 에 덧붙인다
    rule_based = "(LLM 연결 실패 — 원문 요약으로 대체) " + " / ".join(
        d["summary"] for d in state["disclosures"])
    text = llm(INTERPRET_PROMPT.format(context=context, q=state["user_input"]),
               fallback=rule_based)
    return {"interpretation": text}
