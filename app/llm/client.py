"""[아키텍처 박스: vLLM 추론 서버]의 클라이언트 — LLM 호출 단일 창구.

역할: 모든 LLM 호출(가드레일 판정·해석 생성)이 이 함수 하나를 지난다.
관련: 데모 장면 ⑤(폴백) · README "모델 선택과 토큰 비용 전략".

[COST] 왜 OpenAI '호환' 클라이언트인가 — 로컬 Ollama(gemma3n)와 수업 vLLM이
같은 표준을 쓰므로 .env 세 줄로 서로 교체된다. 기본은 로컬 Ollama:
외부 API 토큰 과금 0원 + 공시·관심종목 데이터가 기기 밖으로 나가지 않는다.
단일 창구라 추후 '질문 난이도별 모델 라우팅' 같은 확장도 이 파일만 고치면 된다.
"""
from openai import OpenAI

from app.core.config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


def llm(prompt: str, fallback: str) -> str:
    """LLM 1회 호출. 실패하면 호출자가 정한 폴백 문자열을 반환한다.

    Args:
        prompt: 완성된 프롬프트(스포트라이팅 경계 포함은 호출자 책임).
        fallback: 실패 시 대체 응답 — 호출자마다 다르다(가드레일은 "PASS",
            해석은 원문 요약). '어떻게 실패할지'를 호출자가 설계하게 한 것.
    실패·폴백: [SAFETY] 어떤 예외에도 raise하지 않는다 — LLM이 죽어도
        서비스는 산다(데모 장면 ⑤). 가드레일은 키워드 필터가 최후 방어선.
    왜 timeout 60초인가 — 로컬 소형 모델(gemma3n)의 콜드스타트+긴 해석 생성이
        30초를 넘는 경우가 실측에서 확인돼, 성급한 폴백(멀쩡한 답변 버림)을
        막기 위해 여유를 줬다. 대기 UX는 프런트 로딩 팝업이 담당.
    """
    try:
        res = client.chat.completions.create(
            model=LLM_MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0.2, timeout=60,
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        print(f"[경고] LLM 호출 실패 → 폴백 사용: {e.__class__.__name__}")
        return fallback
