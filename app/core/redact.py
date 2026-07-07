"""출력 마스킹(redaction) — OWASP LLM02 민감정보 유출 대응.
알림·답변이 사용자에게 나가기 직전, 개인정보·비밀키 패턴을 마스킹한다."""
import re

_REDACT_PATTERNS = {
    "API_KEY": re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    "EMAIL": re.compile(r"[\w.\-]+@[\w.\-]+\.\w+"),
    "KR_RRN": re.compile(r"\b\d{6}-\d{7}\b"),
}


def redact(text: str) -> str:
    for label, pat in _REDACT_PATTERNS.items():
        text = pat.sub(f"[{label} 마스킹]", text)
    return text
