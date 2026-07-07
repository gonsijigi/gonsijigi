"""[아키텍처 박스: vLLM 추론 서버] 의 클라이언트.
수업용 vLLM(OpenAI 호환)을 호출하며, 서버가 없어도 폴백으로 데모가 죽지 않는다."""
from openai import OpenAI

from app.core.config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


def llm(prompt: str, fallback: str) -> str:
    """LLM 호출. 실패 시 폴백 문자열 반환 — 가드레일은 키워드 필터가 최후 방어선."""
    try:
        res = client.chat.completions.create(
            model=LLM_MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0.2, timeout=60,
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        print(f"[경고] LLM 호출 실패 → 폴백 사용: {e.__class__.__name__}")
        return fallback
