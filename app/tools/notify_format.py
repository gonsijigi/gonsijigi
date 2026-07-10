"""알림 카드 조립 — 출처·면책을 '프롬프트가 아니라 코드가' 강제하는 지점.

역할: 사용자에게 나가는 모든 카드(알림·HITL 승인분)의 최종 포장.
관련: 데모 장면 ①④ · 보고서 6.2절 · 스모크 test_notification_*이 지키는 불변.

[SAFETY] 설계 원칙 — 모델에게 "출처를 붙여줘"라고 부탁하면 언젠가 빼먹는다.
그래서 원문 링크(접수번호)와 면책 문구는 이 함수가 무조건 붙이고,
발송 직전 redact 마스킹(OWASP LLM02)까지 거친다. LLM이 무엇을 생성하든
이 함수를 지나지 않은 텍스트는 사용자에게 도달할 수 없다.
"""
from app.core.redact import redact


def build_notification(corp_name: str, report_nm: str, interpretation: str, rcept_no: str) -> str:
    """해석 텍스트를 출처·면책·마스킹이 강제된 최종 카드로 만든다.

    Args:
        rcept_no: DART 접수번호 — 원문 링크의 근거. 이 값이 곧 '출처'다.
    Returns:
        [관심종목 알림] 헤더 + 해석 + 근거 링크 + 면책, 마스킹 적용 완료본.
    """
    link = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
    card = (
        f"[관심종목 알림] {corp_name} — {report_nm}\n"
        f"{interpretation}\n"
        f"근거: 공시 원문 {link}\n"
        f"※ 본 내용은 정보 제공 목적이며, 투자 판단의 책임은 투자자 본인에게 있습니다."
    )
    return redact(card)  # [SAFETY] 발송 직전 마지막 관문 — 개인정보·키 마스킹
