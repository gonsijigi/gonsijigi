"""[노드] RAG 해석 생성 — 근거에 없는 말은 하지 않는다(오픈북 원칙)."""
from app.agent.state import AgentState
from app.agent.prompts import INTERPRET_PROMPT
from app.llm.client import llm
from app.rag.retriever import search_similar


def interpret_node(state: AgentState) -> dict:
    if not state["disclosures"]:
        # 특정 종목을 물었으면 그 종목명을 짚어 정직하게 답한다(관심종목으로 얼버무리지 않음).
        asked = ", ".join(s["name"] for s in state.get("parsed_stocks", []) if s.get("name"))
        if asked:
            return {"interpretation": f"{asked}에 오늘 접수된 새 공시가 없습니다."}
        return {"interpretation": "오늘 등록하신 관심 종목에 새 공시가 없습니다."}

    # 현재 공시 컨텍스트
    context_lines = [
        f"- {d['corp_name']} / {d['report_nm']} / {d['summary']}"
        for d in state["disclosures"]
    ]

    # 과거 유사 공시 근거 (RAG) — 사용자가 물은 종목/키워드가 있으면 그걸로 검색(질문 반영),
    # 없으면 첫 공시 기준으로 검색.
    d0 = state["disclosures"][0]
    parsed_terms = " ".join(
        state.get("parsed_keywords", [])
        + [s["name"] for s in state.get("parsed_stocks", []) if s.get("name")]
    ).strip()
    query = parsed_terms or f"{d0['report_nm']} {d0.get('summary', '')}"
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
