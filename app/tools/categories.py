"""[아키텍처 박스: MCP 도구 서버] 개인투자자 필수 5종 공시 분류 + 유상증자 자금목적 분류.
'무엇이 중요한 공시인가'를 프롬프트가 아니라 코드로 고정한다 — 근거: docs/공시_도메인_한장.md §2.

5종: ①수주(단일판매·공급계약) ②유상증자 ③전환사채·BW ④내부자 매매(임원·주요주주) ⑤실적(잠정·공정공시)
선정 근거: docs/공시_도메인_한장.md §2 (주가 영향·법정 공시 기준으로 추림).

[SAFETY] 라벨 정책 — '호재/악재' 단정 금지. "~목적 (일반적으로 ~로 해석되는
경우가 많음)"까지만 말한다. 단정은 투자 권유의 경계를 넘는다(가드레일과 동일 원칙).
[COST] 분류는 전부 결정론(키워드·정규식) — LLM 없이 0토큰으로 동작한다."""
from __future__ import annotations
import re

# 보고서명 키워드 → 카테고리 (위에서부터 우선 매칭)
CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("수주",     ("단일판매", "공급계약")),
    ("유상증자", ("유상증자",)),
    ("전환사채", ("전환사채", "신주인수권")),
    ("내부자",   ("임원ㆍ주요주주", "임원·주요주주")),
    ("실적",     ("잠정실적", "잠정)실적", "공정공시", "영업실적")),
]


def categorize(report_nm: str) -> str | None:
    """보고서명 → 5종 카테고리. 해당 없으면 None(알림 대상 아님)."""
    for cat, kws in CATEGORY_RULES:
        if any(k in report_nm for k in kws):
            return cat
    return None


# ── 유상증자 자금조달 목적 분류 ─────────────────────────────────────────
# 주요사항보고서(유상증자결정) 서식의 목적 필드들. 금액이 가장 큰 필드 = 우세 목적.
_PURPOSE_FIELDS = ("시설자금", "영업양수자금", "운영자금", "채무상환자금",
                   "타법인 증권취득자금", "타법인증권취득자금", "기타자금")
_GROWTH = {"시설자금", "영업양수자금", "타법인 증권취득자금", "타법인증권취득자금"}


def classify_purpose(doc_text: str) -> str | None:
    """유상증자 원문에서 목적별 금액을 읽어 우세 목적을 라벨링(결정론·무LLM).

    Returns:
        "시설자금 목적 (일반적으로 성장 투자로 해석되는 경우가 많음)" 류 문자열.
        금액을 못 읽으면 None(라벨 생략 — 지어내지 않음).
    """
    if not doc_text:
        return None
    amounts: dict[str, int] = {}
    for field in _PURPOSE_FIELDS:
        # 예: '시설자금 (원) | 2,799,999,666' — 필드명 뒤 같은 줄 40자 내 콤마 형식 금액.
        # [SAFETY] 줄바꿈(\n) 통과 금지 — DART 서식은 미사용 필드를 '-'로 채우는데,
        #          줄을 넘어가면 다음 필드의 금액을 훔쳐와 정반대 라벨이 나온다.
        #          콤마 자릿수 형식(1,000 단위) 강제 — '2026년' 같은 연도 오탐 차단.
        m = re.search(re.escape(field) + r"[^\d\n]{0,40}(\d{1,3}(?:,\d{3})+)", doc_text)
        if m:
            try:
                amounts[field] = int(m.group(1).replace(",", ""))
            except ValueError:
                pass
    if not amounts:
        return None
    top = max(amounts, key=lambda k: amounts[k])
    if amounts[top] <= 0:
        return None
    if top in _GROWTH:
        return f"{top} 목적 (일반적으로 성장 투자로 해석되는 경우가 많음)"
    return f"{top} 목적 (일반적으로 재무 부담 신호로 해석되는 경우가 많음)"
