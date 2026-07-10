"""[노드] 위험도 판단 — 고위험 공시를 골라 사람 검토(HITL) 경로로 보낸다.

역할: 조회된 공시들 중 고위험 키워드가 걸린 공시를 찾아 risk_level을 판정한다.
위치: 해석 다음, 발송 직전 — 여기서의 판정이 알림/검토 큐 분기(route_risk)를 결정.
관련: 데모 장면 ④ · 보고서 6.6절 · 스모크 test_risk_* 2종이 지키는 불변.
"""
from app.agent.state import AgentState
from app.tools import RISK_KEYWORDS


def risk_node(state: AgentState) -> dict:
    """공시 제목에서 고위험 키워드를 탐지해 high/normal을 판정한다.

    Returns:
        risk_level: "high"|"normal" — route_risk의 분기 근거.
        review_disclosure: 실제로 키워드가 걸린 '그 공시' — hitl_node가 큐에 넣는 대상.
        risk_keywords: 걸린 키워드 목록 — 검토 화면에 태그로 노출.
    왜 '걸린 그 공시'를 따로 기록하나 — 첫 번째 공시를 관성적으로 쓰면
        고위험 공시가 두 번째일 때 엉뚱한 공시가 검토 큐에 들어간다(실제 겪은 P1 버그,
        스모크 test_risk_picks_actual_high_risk_disclosure가 회귀 방어).
    """
    # [ORCHESTRATION] 생각: 각 공시 제목에 고위험 키워드(유상증자·거래정지 등)가 있는가
    #                 → 행동: 처음 걸린 공시를 review_disclosure로 지목하고 high 판정.
    #                 이 판정 하나로 "즉시 발송이냐, 사람 승인 대기냐"가 갈린다.
    review = None
    triggered: list[str] = []
    for d in state["disclosures"]:
        hits = [k for k in RISK_KEYWORDS if k in d["report_nm"]]
        if hits:
            review = d
            triggered = hits
            break
    level = "high" if review else "normal"
    return {"risk_level": level, "risk_keywords": triggered,
            "review_disclosure": review}
