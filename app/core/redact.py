"""출력 마스킹(redaction) — OWASP LLM02 민감정보 유출 대응.

역할: 사용자에게 나가기 직전의 텍스트에서 개인정보·비밀키 패턴을 마스킹한다.
위치: build_notification의 마지막 단계 — 모든 카드가 예외 없이 통과.
관련: 스모크 test_redact_masks_secrets가 지키는 불변.

[SAFETY] 왜 출력 단계에서 거나 — 입력·프롬프트를 아무리 통제해도
LLM이 학습 잔재나 원문에서 민감 패턴을 되뱉을 가능성은 남는다.
'나가는 문' 하나를 지키는 것이 모든 경로를 개별 통제하는 것보다 확실하다.
"""
import re

_REDACT_PATTERNS = {
    "API_KEY": re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),      # OpenAI 계열 키 형태
    "EMAIL": re.compile(r"[\w.\-]+@[\w.\-]+\.\w+"),
    "KR_RRN": re.compile(r"\b\d{6}-\d{7}\b"),             # 주민등록번호
}


def redact(text: str) -> str:
    """민감 패턴을 '[라벨 마스킹]'으로 치환한 텍스트를 반환한다."""
    for label, pat in _REDACT_PATTERNS.items():
        text = pat.sub(f"[{label} 마스킹]", text)
    return text
