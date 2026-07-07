"""알림 카드 조립 — 출처 링크·면책 문구를 코드가 강제하고(모델에 맡기지 않음),
발송 직전 redact 마스킹을 거친다 (보고서 6.2절 + OWASP LLM02)."""
from app.core.redact import redact


def build_notification(corp_name: str, report_nm: str, interpretation: str, rcept_no: str) -> str:
    link = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
    card = (
        f"[관심종목 알림] {corp_name} — {report_nm}\n"
        f"{interpretation}\n"
        f"근거: 공시 원문 {link}\n"
        f"※ 본 내용은 정보 제공 목적이며, 투자 판단의 책임은 투자자 본인에게 있습니다."
    )
    return redact(card)
