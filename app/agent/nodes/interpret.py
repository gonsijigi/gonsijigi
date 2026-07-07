"""[노드] RAG 해석 생성 — 근거에 없는 말은 하지 않는다(오픈북 원칙)."""
from app.agent.state import AgentState
from app.agent.prompts import INTERPRET_PROMPT
from app.llm.client import llm
from app.rag.retriever import search_similar


def interpret_node(state: AgentState) -> dict:
    if not state["disclosures"]:
        return {"interpretation": "오늘 등록하신 관심 종목에 새 공시가 없습니다."}

    # 현재 공시 컨텍스트
    context_lines = [
        f"- {d['corp_name']} / {d['report_nm']} / {d['summary']}"
        for d in state["disclosures"]
    ]

    # 과거 유사 공시 근거 (RAG)
    d0 = state["disclosures"][0]
    query = f"{d0['report_nm']} {d0.get('summary', '')}"
    similar = search_similar(query, k=3)
    if similar:
        context_lines.append("\n[참고: 과거 유사 공시]")
        for s in similar:
            context_lines.append(
                f"- {s['corp_name']} / {s['report_nm']} ({s['rcept_dt']}) : {s['content'][:200]}"
            )

    context = "\n".join(context_lines)

    rule_based = "(LLM 연결 실패 — 원문 요약으로 대체) " + " / ".join(
        d["summary"] for d in state["disclosures"])
    text = llm(INTERPRET_PROMPT.format(context=context, q=state["user_input"]),
               fallback=rule_based)
    return {"interpretation": text}
