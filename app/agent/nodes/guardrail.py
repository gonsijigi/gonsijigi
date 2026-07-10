"""[노드] 가드레일 — 투자자문성 요청 차단. 그래프의 첫 관문.

역할: "그래서 살까/팔까?" 류 매매 판단 요청을 파이프라인 진입 전에 거절한다.
위치: 아키텍처의 '가드레일' 박스 — 모든 입력이 예외 없이 여기를 먼저 지난다.
관련: 데모 장면 ③ · CI 스모크 test_guardrail_blocks_trading_advice가 지키는 불변.

왜 이중 필터인가 — 키워드(결정론)와 LLM 판정(맥락 이해)은 실패 양상이 다르다.
키워드는 우회 표현에 약하고, LLM은 다운될 수 있다. 둘을 겹치면
"LLM이 죽어도 최소한의 차단은 산다"가 보장된다.
"""
from app.agent.state import AgentState
from app.agent.prompts import GUARD_PROMPT, REFUSAL
from app.llm.client import llm

# [SAFETY] 1차 하드 필터 — 명백한 매매 판단 요청은 여기서 끝낸다.
# [COST] 조기 차단: 여기 걸리면 LLM 판정 호출·DART 조회·해석 생성이 전부 생략된다.
#        부적절한 질문에 토큰을 1도 쓰지 않는 것이 첫 번째 비용 절약 장치.
HARD_HITS = ["살까", "팔까", "사야", "팔아야", "매수해", "매도해", "추천해줘"]


def guardrail_node(state: AgentState) -> dict:
    """매매 판단 요청 여부를 판정해 blocked/response를 기록한다.

    Returns:
        blocked=True면 REFUSAL(정중한 거절 + 대안 안내)이 곧바로 응답이 되고,
        route_guard가 그래프를 END로 보낸다.
    실패·폴백: LLM 판정이 실패하면 "PASS"로 폴백 — BLOCK 폴백이면 LLM 장애 시
        모든 정상 질문까지 차단되는 오탐이 나므로, 가용성을 지키되
        하드 필터가 최후 방어선 역할을 유지한다.
    """
    q = state["user_input"]
    # [ORCHESTRATION] 생각: 질문에 매매 판단 키워드가 있는가 → 행동: 있으면 즉시 거절.
    if any(k in q for k in HARD_HITS):
        return {"blocked": True, "response": REFUSAL}
    # [SAFETY] 2차 LLM 판정 — 키워드를 피해간 우회 표현("지금 들어가도 돼?")을 잡는다.
    verdict = llm(GUARD_PROMPT.format(q=q), fallback="PASS")
    if "BLOCK" in verdict.upper():
        return {"blocked": True, "response": REFUSAL}
    return {"blocked": False}
