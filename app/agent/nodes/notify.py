"""[노드] 알림 생성 — 일반(normal) 공시의 응답 카드를 만든다.

역할: 해석 결과를 사용자에게 나가는 최종 카드로 포장한다.
위치: route_risk의 normal 경로 종착점.
관련: 데모 장면 ①② · 보고서 6.2절.
"""
from app.agent.state import AgentState
from app.tools import build_notification


def notify_node(state: AgentState) -> dict:
    """첫 공시 기준으로 알림 카드를 생성해 응답으로 반환한다.

    왜 build_notification을 반드시 거치나 — [SAFETY] 원문 링크(접수번호)와
        면책 문구를 '모델에게 부탁'하는 게 아니라 코드가 붙이고, 발송 직전
        마스킹까지 강제하기 위해서다. 프롬프트는 뚫려도 이 함수는 안 뚫린다.
    한계(의도된 단순화): 다건 공시는 첫 건 기준으로 카드를 만든다 —
        해석 본문에는 전체 목록이 반영되며, 건별 카드 분리는 로드맵.
    """
    if not state["disclosures"]:
        return {"response": state["interpretation"]}
    d = state["disclosures"][0]
    return {"response": build_notification(d["corp_name"], d["report_nm"],
                                           state["interpretation"], d["rcept_no"])}
