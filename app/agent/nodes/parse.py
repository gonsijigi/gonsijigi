"""[노드] 질문 파싱 — 종목·키워드를 결정론적으로 추출하고, 무의미 입력은 되묻는다.

역할: 자연어 질문에서 '어느 종목·무슨 키워드'를 뽑아 뒤 노드들의 조회 범위를 좁힌다.
위치: 가드레일 다음(안전이 이해보다 먼저) — 여기 통과분만 도구 호출로 진행.
관련: 스모크 parse-* 4종이 지키는 불변.

[COST] 왜 LLM을 쓰지 않나 — 종목명 매칭은 사전 대조로 충분한 결정론 문제다.
LLM을 쓰면 토큰이 들고, 지연이 생기고, 환각(없는 종목 추출) 위험까지 생긴다.
이 노드는 발표 안정성과 비용을 동시에 잡는 '무LLM 추론' 지점이다.
"""
from __future__ import annotations
import re

from app.agent.state import AgentState
from app.tools import RISK_KEYWORDS
from app.tools.dart import load_corp_names

# 코퍼스 적재 키워드 + 위험 키워드 = 검색/의도에 쓰는 키워드 집합(중복 제거)
CORPUS_KEYWORDS = ["유상증자", "자기주식", "타법인", "무상증자", "자기주식취득", "자기주식처분"]
KEYWORDS = list(dict.fromkeys(CORPUS_KEYWORDS + RISK_KEYWORDS))

# corp_names.json 이 아직 없을 때의 최소 폴백(기본 관심종목)
_FALLBACK_NAMES = {"삼성전자": "005930", "에코프로비엠": "247540", "카카오": "035720"}

# 별칭 맵: 사용자 구어체·영문 약칭 → DART 정식 회사명(= corp_names.json 의 키).
# DART가 종목명을 제각각(한글 음차/영문/법인명)으로 저장해 exact 매칭이 놓치는 것들을 보완.
# 키는 소문자(비교가 소문자 기준). 데모 대상 종목은 여기에 추가해 확실히 잡히게 한다.
_ALIASES = {
    "삼성sds": "삼성에스디에스",
    "네이버": "NAVER",
    "현대차": "현대자동차",
    "기아차": "기아",
    "포스코": "POSCO홀딩스",
    "lg엔솔": "LG에너지솔루션",
    "엘지엔솔": "LG에너지솔루션",
    "lg에너지솔루션": "LG에너지솔루션",
}

_CODE_RE = re.compile(r"\d{6}")
# 2자 이상 한글/영문 낱말 = '의미 있는' 입력. 낱개 자모(ㅇㄹㅁ)나 단발 음절은 제외.
_MEANINGFUL_RE = re.compile(r"[가-힣]{2,}|[A-Za-z]{2,}")

CLARIFY_MSG = (
    "질문을 이해하지 못했어요. 종목명이나 '오늘 공시', '유상증자' 같은 키워드로 물어봐 주세요.\n"
    "예) \"삼성전자 공시 있어?\" / \"오늘 내 종목 공시 뭐 있었어?\""
)

_names_cache: dict | None = None


def _names() -> dict:
    """종목명→코드 사전(3,976개)을 1회만 로드해 캐시 — 질문마다 파일을 읽지 않는다."""
    global _names_cache
    if _names_cache is None:
        _names_cache = load_corp_names() or dict(_FALLBACK_NAMES)
    return _names_cache


def _match_stocks(q: str) -> list[dict]:
    """질문에서 종목을 추출 — 6자리 코드 + 전체 회사명(부분일치) 매칭.

    왜 '긴 이름 우선 + 구간 선점'인가 — 'SK하이닉스' 안에 'SK'가 들어 있어
    짧은 이름부터 매칭하면 오탐이 난다. 긴 이름이 글자 구간을 먼저 차지하면
    그 안의 짧은 이름은 자동으로 배제된다.
    """
    names = _names()
    ql = q.lower()                              # 대소문자 무시(SK/LG/KT 등 영문 이름)
    hits: list[dict] = []
    seen: set[str] = set()
    claimed: list[tuple[int, int]] = []         # 이미 매칭된 글자 구간

    def _overlaps(s: int, e: int) -> bool:
        return any(not (e <= cs or s >= ce) for cs, ce in claimed)

    for code in _CODE_RE.findall(q):            # ① 6자리 코드 직접 매칭
        if code not in seen:
            seen.add(code)
            hits.append({"code": code, "name": ""})
    # ② 회사명 매칭 — 첫 등장 위치를 찾고, '긴 이름 우선'으로 구간을 선점해
    #    짧은 이름이 긴 이름 안에 박혀 생기는 오탐(SK하이닉스 안의 '이닉스'·'SK')을 제거.
    found = []  # (조회에 쓸 DART정식명, start, end)
    for name in names:
        if len(name) < 2:
            continue
        idx = ql.find(name.lower())
        if idx >= 0:
            found.append((name, idx, idx + len(name)))
    # ②' 별칭 매칭 — 구어체·약칭을 DART 정식명으로 치환해 함께 후보에 넣는다.
    for alias, canon in _ALIASES.items():
        idx = ql.find(alias)
        if idx >= 0 and canon in names:
            found.append((canon, idx, idx + len(alias)))
    for name, s, e in sorted(found, key=lambda m: m[2] - m[1], reverse=True):
        if _overlaps(s, e):
            continue
        claimed.append((s, e))
        code = names[name]
        if code not in seen:
            seen.add(code)
            hits.append({"code": code, "name": name})
    return hits


def parse_node(state: AgentState) -> dict:
    """질문에서 종목·키워드를 추출하고, 무의미 입력이면 되묻기로 단락한다.

    Returns:
        parsed_stocks/parsed_keywords: 뒤 노드(fetch 조회 범위, interpret RAG 검색어)의 입력.
        clarify=True면 CLARIFY_MSG가 곧 응답 — route_parse가 그래프를 종료한다.
    """
    q = state.get("user_input") or ""
    stocks = _match_stocks(q)
    keywords = [k for k in KEYWORDS if k in q]
    # [ORCHESTRATION] 이해 판정.
    # 생각: 종목도 키워드도 없고 의미 있는 낱말(2자 이상)조차 없는가
    # 행동: 그렇다면 추측으로 진행하지 않고 되묻는다 — "모르면 모른다고 말한다"가
    #       엉뚱한 답변(아무 관심종목이나 해석)보다 낫다는 판단.
    # [COST] 이 단락으로 무의미 입력은 DART 호출·LLM 해석 비용을 전혀 쓰지 않는다.
    if not stocks and not keywords and not _MEANINGFUL_RE.search(q):
        return {"parsed_stocks": [], "parsed_keywords": [],
                "clarify": True, "response": CLARIFY_MSG}
    return {"parsed_stocks": stocks, "parsed_keywords": keywords, "clarify": False}
