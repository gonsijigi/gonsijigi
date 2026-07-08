"""[노드] RAG 해석 생성 — 근거에 없는 말은 하지 않는다(오픈북 원칙).
해석은 LangChain OutputParser로 유형/사실/주의 3필드로 구조화한다(파싱 실패 시 원문 폴백)."""
import json
import re
from typing import List

from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

from app.agent.state import AgentState
from app.agent.prompts import INTERPRET_STRUCT_PROMPT
from app.llm.client import llm
from app.rag.retriever import search_similar
from app.tools.dart import get_document_text

DOC_EXCERPT_CHARS = 1500  # 현재 공시 원문 발췌 길이 — 소형 LLM 컨텍스트 보호


class Interpretation(BaseModel):
    """공시 해석 구조 — 단정 대신 '유형 + 사실 + 해석 참고'로 나눈다."""
    disclosure_type: str = Field(description="공시 유형을 짧게 (예: 유상증자, 자기주식취득, 타법인 지분취득)")
    facts: List[str] = Field(description="공시 원문 발췌에 실제로 적힌 사실만 1~3개 — 금액·주식수·발행가·목적 같은 구체 수치가 있으면 그것을 우선. 추측·수치 창작 금지")
    caution: str = Field(description="이 유형이 일반적으로 어떻게 해석되는지 + 단정하지 않는 주의 한 문장")


_parser = PydanticOutputParser(pydantic_object=Interpretation)


def _clean(text: str) -> str:
    """gemma 계열이 흘리는 공백 마커(▁)·코드펜스(```json)를 제거해 읽히게 만든다."""
    t = text.replace("▁", " ")            # SentencePiece 공백 마커
    t = re.sub(r"```(?:json)?", "", t)          # 코드블록 표시 제거
    return t.strip()


def _to_struct(text: str):
    """구조화 시도 — 표준 파서 → 실패하면 관대한 보정(펜스·마커 제거 후 JSON 추출)."""
    try:
        return _parser.parse(text)
    except Exception:
        pass
    cleaned = _clean(text)
    m = re.search(r"\{.*\}", cleaned, re.S)     # 첫 JSON 객체
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data.get("facts"), str):   # 사실이 문자열이면 리스트로
                data["facts"] = [data["facts"]]
            return Interpretation(**data)
        except Exception:
            pass
    return None


def _render(o: "Interpretation") -> str:
    facts = "\n".join(f"· {f}" for f in o.facts) if o.facts else "· 상세는 원문 참고"
    return f"[유형] {o.disclosure_type}\n[사실]\n{facts}\n[해석 참고] {o.caution}"


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

    d0 = state["disclosures"][0]

    # 현재 공시의 '원문 발췌'를 근거로 주입 — [사실]이 제목이나 과거 유사 사례가 아니라
    # 이 공시 자체(금액·방식·목적 등)에 접지되게 한다. 키 없음/호출 실패 시 빈 값 → 기존 동작.
    try:
        doc = get_document_text(d0.get("rcept_no", ""))
    except Exception:
        doc = ""
    if doc:
        context_lines.append(f"\n[현재 공시 원문 발췌 — {d0['corp_name']} / {d0['report_nm']}]")
        context_lines.append(doc[:DOC_EXCERPT_CHARS])

    # 과거 유사 공시 근거 (RAG) — 사용자가 물은 종목/키워드가 있으면 그걸로 검색(질문 반영),
    # 없으면 첫 공시 기준으로 검색.
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
    prompt = INTERPRET_STRUCT_PROMPT.format(
        format_instructions=_parser.get_format_instructions(),
        context=context, q=state["user_input"])
    text = llm(prompt, fallback=rule_based)
    # 구조화 시도 → 실패해도 최소한 ▁·코드펜스는 벗겨 읽히게(지저분한 원문 노출 방지).
    o = _to_struct(text)
    if o:
        return {"interpretation": _render(o)}
    return {"interpretation": _clean(text)}
