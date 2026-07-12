"""[아키텍처 박스: LangGraph 오케스트레이터] — 에이전트의 두뇌, 그래프 조립부.

역할: 질문/공시가 들어와 사용자에게 응답이 나가기까지의 전체 흐름을
      상태 그래프로 정의한다. 각 노드는 app/agent/nodes/ 에 파일 하나씩.
흐름: 가드레일 → 질문 파싱 → 조회 → 해석 → 위험도 → (조건부) 알림 | HITL
관련: 데모 장면 ②③④ · 보고서 6.4절 · README "AI Agent 오케스트레이션 포인트" 표

왜 체인이 아니라 그래프인가 — "안전 필터가 통과시켜야만 다음 단계로",
"고위험이면 사람을 기다린다" 같은 조건부 분기·중단이 제품 정의의 핵심이라,
일직선 체인이 아닌 조건부 엣지 3개를 가진 상태 그래프로 설계했다.
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from app.agent.state import AgentState
from app.agent.nodes import (guardrail_node, parse_node, fetch_node,
                             interpret_node, risk_node, notify_node, hitl_node)


# ── 조건부 엣지의 라우터 3개 ──────────────────────────────────────────────
# 라우터는 "판단 결과를 읽어 경로만 고르는" 순수 함수로 분리한다.
# 판단 자체(생각)는 각 노드가 하고, 여기서는 그 결과로 행동(경로 선택)만 한다.

def route_guard(state: AgentState) -> str:
    # [ORCHESTRATION] 분기점 1 — 안전 게이트.
    # 생각: 가드레일 노드가 "이 요청이 매매 판단 요구인가"를 판정해 blocked에 기록했다.
    # 행동: 차단이면 여기서 그래프를 즉시 종료(END) — 뒤의 조회·해석·LLM 호출이
    #       아예 실행되지 않는다. 안전이 기능보다 먼저라는 제품 원칙의 코드 표현.
    return "blocked" if state["blocked"] else "pass"


def route_parse(state: AgentState) -> str:
    # [ORCHESTRATION] 분기점 2 — 이해 게이트.
    # 생각: 파싱 노드가 질문에서 종목·키워드를 뽑아보고 "의미 있는 질문인가"를 판정했다.
    # 행동: 무의미 입력(자모 등)이면 되묻고 종료 — 뒤 단계(DART 호출·LLM)로 가지 않는다.
    return "clarify" if state.get("clarify") else "ok"


def route_risk(state: AgentState) -> str:
    # [ORCHESTRATION] 분기점 3 — 책임 게이트 (데모 장면 ④의 심장).
    # 생각: 위험도 노드가 공시 제목에서 고위험 키워드(유상증자 등)를 탐지했다.
    # 행동: high면 알림 대신 검토 큐(HITL)로 — 사람 승인 전에는 어떤 고위험 해석도
    #       사용자에게 나가지 않는다. normal만 알림으로 직행한다.
    return "high" if state["risk_level"] == "high" else "normal"


# ── 그래프 조립 — 노드 등록 → 엣지 연결 ─────────────────────────────────
workflow = StateGraph(AgentState)
workflow.add_node("guardrail", guardrail_node)   # 매매 판단 요청 차단 [SAFETY]
workflow.add_node("parse", parse_node)           # 종목·키워드 추출 (무LLM)
workflow.add_node("fetch", fetch_node)           # DART 공시 조회
workflow.add_node("interpret", interpret_node)   # RAG+원문 접지 해석 생성
workflow.add_node("risk", risk_node)             # 고위험 키워드 분류
workflow.add_node("notify", notify_node)         # 알림 카드 생성 (출처·면책 강제)
workflow.add_node("hitl", hitl_node)             # 검토 큐 적재 (사람 승인 대기)

workflow.add_edge(START, "guardrail")            # 모든 입력은 예외 없이 가드레일부터
workflow.add_conditional_edges("guardrail", route_guard, {"pass": "parse", "blocked": END})
workflow.add_conditional_edges("parse", route_parse, {"ok": "fetch", "clarify": END})
workflow.add_edge("fetch", "interpret")
workflow.add_edge("interpret", "risk")
workflow.add_conditional_edges("risk", route_risk, {"normal": "notify", "high": "hitl"})
workflow.add_edge("notify", END)
workflow.add_edge("hitl", END)

# checkpointer + thread_id 배선(보고서 6.4절) — 단, run_agent가 매 호출 전 필드를
# 초기화하므로 이전 턴 상태는 아직 쓰지 않는다(멀티턴 메모리는 로드맵, README §10).
# 프로토타입은 인메모리(재시작 시 초기화가 곧 데모 리셋), 운영 전환 시 저장소만 교체.
memory = InMemorySaver()
app_graph = workflow.compile(checkpointer=memory)


def run_agent(user_id: str, question: str, stock_codes: list) -> str:
    """그래프 1회 실행 — 게이트웨이(/ask)와 콘솔 데모가 쓰는 단일 진입점.

    Args:
        user_id: 사용자 식별자. thread_id로 변환된다(멀티턴 맥락 활용은 로드맵).
        question: 사용자 질문 원문.
        stock_codes: 관심종목 코드 목록(질문에 종목이 명시되면 무시될 수 있음).
    Returns:
        사용자에게 보여줄 응답 문자열. 모든 경로(차단/되묻기/알림/HITL)가
        response를 채우므로 None 폴백은 방어적 처리다.
    """
    config = {"configurable": {"thread_id": f"user_{user_id}"}}
    # 전 필드를 명시 초기화 — 부분 상태로 시작해 노드가 KeyError를 내는 사고를 막는다.
    result = app_graph.invoke(
        {"user_input": question, "stock_codes": stock_codes,
         "parsed_stocks": [], "parsed_keywords": [], "clarify": False,
         "disclosures": [], "interpretation": "", "risk_level": "normal",
         "risk_keywords": [], "review_disclosure": None,
         "blocked": False, "response": None},
        config=config,
    )
    return result["response"] or "처리 결과가 없습니다."


if __name__ == "__main__":  # 콘솔 데모: python -m app.agent.graph (웹 없이 그래프만 검증)
    codes = ["005930", "247540", "035720"]
    for q in ["오늘 내 종목 공시 뭐 있었어?", "그래서 에코프로비엠 지금 팔까?"]:
        print(f"\n질문: {q}")
        print(run_agent("kim_gaemi", q, codes))
