"""[노드] 컴플라이언스 검토(HITL) — 고위험 공시는 사람 승인 후에만 발송.

역할: 고위험으로 분류된 공시를 검토 큐에 넣고, 사용자에게는 '검토 대기'만 알린다.
위치: route_risk의 high 경로 종착점. 승인/반려는 /admin/ 화면(gateway/admin.py)에서.
관련: 데모 장면 ④ · 보고서 6.6절 — "자동화할 수 있는 것은 자동화하되,
      위험한 알림은 기계에만 맡기지 않는다"의 코드 구현.
"""
from app.agent.state import AgentState
from app.tools import build_notification
from app.gateway.queue import enqueue


def hitl_node(state: AgentState) -> dict:
    """고위험 공시를 검토 큐에 적재하고 '검토 대기' 응답을 돌려준다.

    실패·폴백: review_disclosure가 비어 있으면(이론상 없지만) 첫 공시로 방어 —
        고위험 판정을 받고도 큐 적재가 누락되는 최악을 피한다.
    """
    # [SAFETY] 발송 보류 게이트 — 카드는 지금 만들어 두되(승인 즉시 발송 가능하게),
    # 사용자에게는 절대 직접 보내지 않는다. deliver()는 오직 관리자 승인 핸들러만 호출.
    d = state.get("review_disclosure") or state["disclosures"][0]
    card = build_notification(d["corp_name"], d["report_nm"],
                              state["interpretation"], d["rcept_no"])
    # 검토 화면이 "에이전트의 생각"을 검증할 수 있도록 판단 근거(risk_keywords)와
    # 해석(interpretation)을 그대로 큐에 남긴다 — 사람이 AI의 판단을 보고 승인/반려.
    enqueue({
        "corp_name":      d["corp_name"],
        "report_nm":      d["report_nm"],
        "rcept_no":       d["rcept_no"],
        "rcept_dt":       d["rcept_dt"],
        "interpretation": state["interpretation"],
        "risk_keywords":  state["risk_keywords"],
        "card":           card,
    })
    return {"response": f"[컴플라이언스 검토 대기 — 승인 후 발송됩니다]\n{card}"}
