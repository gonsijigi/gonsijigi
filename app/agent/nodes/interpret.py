"""[노드] RAG 해석 생성 — 근거에 없는 말은 하지 않는다(오픈북 원칙).

역할: 현재 공시 원문 발췌 + 과거 유사 공시(RAG)를 근거로 펴놓고 해석을 생성한다.
위치: 아키텍처의 'RAG 해석 생성' 박스 — 이 에이전트에서 가장 큰 '생각'이 일어나는 곳.
관련: 데모 장면 ② · 보고서 6.5절 · README RAG 섹션.

구조화: LangChain PydanticOutputParser로 [유형/사실/해석 참고] 3필드 —
'단정하지 않는다'는 원칙이 프롬프트 부탁이 아니라 출력 구조로 강제된다.
파싱 실패 시 원문 텍스트로 폴백(서비스는 계속 산다).
"""
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

# [COST] 원문 전문(수천~수만 자)을 통째로 넣지 않고 발췌만 주입 — 입력 토큰을
# 정보 밀도가 높은 구간에만 쓴다. 소형 LLM의 컨텍스트 보호 겸 비용 절약.
DOC_EXCERPT_CHARS = 1500

# '무엇을 위한 돈인가'가 해석의 핵심 — 원문에서 자금 목적 구간을 찾아 발췌에 반드시 포함한다
_PURPOSE_KEYS = ("조달자금의 구체적 사용목적", "자금조달의 목적", "사용목적")


def _doc_excerpt(doc: str) -> str:
    """원문 머리(개요·정정사항) + 자금 목적 구간을 함께 발췌.
    목적 구간이 앞부분에 이미 포함돼 있으면 그대로 머리만 쓴다."""
    head = doc[:1000]
    for kw in _PURPOSE_KEYS:
        i = doc.find(kw)
        if 0 <= i <= 800:                     # 이미 머리 발췌에 포함됨
            break
        if i > 800:
            return f"{head}\n…\n[{kw}]\n{doc[i:i + 900]}"
    return doc[:DOC_EXCERPT_CHARS]


class Interpretation(BaseModel):
    """공시 해석 구조 — 단정 대신 '유형 + 사실 + 해석 참고'로 나눈다."""
    disclosure_type: str = Field(description="공시 유형을 짧게 (예: 유상증자, 자기주식취득, 타법인 지분취득)")
    facts: List[str] = Field(description="공시 원문 발췌에 실제로 적힌 사실만 1~3개 — 금액·주식수·발행가·목적 같은 구체 수치가 있으면 그것을 우선. 추측·수치 창작 금지")
    caution: str = Field(description="이 유형이 일반적으로 어떻게 해석되는지 한두 문장 — 원문에 자금 사용목적(시설투자·운영자금 등)이 있으면 그 목적을 근거로 '일반적으로 ~로 해석되는 경우가 많다'고 조건부 서술. 호재/악재 단정 금지")


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
        # 리플레이 모드는 '샘플에 있는 종목만' 재생되므로, 그 사실을 밝혀 혼동을 막는다.
        from app.core.config import REPLAY_MODE
        hint = ("\n(지금은 리플레이 모드예요 — 데모 샘플에 없는 종목은 조회되지 않습니다. "
                "실데이터 조회는 라이브 모드로 실행하세요.)") if REPLAY_MODE else ""
        asked = ", ".join(s["name"] for s in state.get("parsed_stocks", []) if s.get("name"))
        if asked:
            return {"interpretation": f"{asked}에 조회 기간 내 새 공시가 없습니다.{hint}"}
        return {"interpretation": f"등록하신 관심 종목에 조회 기간 내 새 공시가 없습니다.{hint}"}

    # 현재 공시 컨텍스트
    context_lines = [
        f"- {d['corp_name']} / {d['report_nm']} / {d['summary']}"
        for d in state["disclosures"]
    ]

    d0 = state["disclosures"][0]

    # [ORCHESTRATION] 근거 수집 1 — 현재 공시 원문 접지.
    # 생각: "이 공시가 실제로 뭐라고 적었나"가 사실관계의 유일한 출처다.
    # 행동: 원문을 도구로 가져와 발췌를 근거 맨 앞에 놓는다. [사실]이 제목이나
    #       과거 유사 사례가 아니라 이 공시 자체(금액·방식·목적)에 접지된다.
    #       키 없음/호출 실패 시 빈 값 → 발췌 없이 진행(폴백, 서비스 유지).
    try:
        doc = get_document_text(d0.get("rcept_no", ""))
    except Exception:
        doc = ""
    if doc:
        context_lines.append(f"\n[현재 공시 원문 발췌 — {d0['corp_name']} / {d0['report_nm']}]")
        context_lines.append(_doc_excerpt(doc))

    # [ORCHESTRATION] 근거 수집 2 — 과거 유사 공시 검색(RAG).
    # 생각: "이런 유형의 공시가 과거에 어떻게 해석됐나"는 해석의 맥락 근거다.
    # 행동: 사용자가 물은 종목/키워드가 있으면 그걸로 검색(질문 반영),
    #       없으면 첫 공시 기준으로 검색해 상위 3건만 근거에 붙인다.
    # [COST] k=3 + 거리 필터(retriever) — 관련 청크만 프롬프트에 들어간다.
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
