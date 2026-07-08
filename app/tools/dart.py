"""[아키텍처 박스: MCP 도구 서버] dart_search — 공시 조회.
프로토타입은 mock, 실제 DART OpenAPI 호출 코드는 아래 docstring 참고.
여유가 생기면 FastMCP 서버로 분리한다(수업 MCP 실습 패턴)."""
from __future__ import annotations  # PEP604(str | None) 어노테이션을 3.9에서도 허용
from datetime import datetime
# --- corpCode 매핑: 종목코드(6자리) ↔ DART 고유번호(8자리) 전화번호부 ---
import io, json, os, zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
import requests

CORP_MAP_PATH = "data/corp_map.json"
CORP_NAMES_PATH = "data/corp_names.json"   # {회사명: 종목코드} — parse_node의 종목명 매칭용

def build_corp_map(api_key: str) -> dict[str, str]:
    """고유번호 전체 파일(zip 속 XML)을 내려받아 두 인덱스를 저장. 하루 1회면 충분.
    - corp_map.json:   {종목코드: 고유번호}  (DART 단일종목 조회용)
    - corp_names.json: {회사명: 종목코드}    (질문에서 종목명 파싱용)
    """
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    res = requests.get(url, params={"crtfc_key": api_key}, timeout=30)
    res.raise_for_status()                      # HTTP 오류면 즉시 예외로 알림
    with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
        xml_bytes = zf.read(zf.namelist()[0])   # zip 안의 CORPCODE.xml 한 장
    root = ET.fromstring(xml_bytes)
    mapping: dict[str, str] = {}
    names: dict[str, str] = {}
    for item in root.iter("list"):              # 회사 한 곳 = <list> 하나
        stock = (item.findtext("stock_code") or "").strip()
        if stock:                               # 비상장은 종목코드가 빈칸 → 건너뜀
            mapping[stock] = item.findtext("corp_code")
            name = (item.findtext("corp_name") or "").strip()
            if name:
                names[name] = stock             # 상장사 이름 → 종목코드
    os.makedirs("data", exist_ok=True)
    with open(CORP_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False)
    with open(CORP_NAMES_PATH, "w", encoding="utf-8") as f:
        json.dump(names, f, ensure_ascii=False)
    return mapping

def get_corp_code(stock_code: str) -> str | None:
    with open(CORP_MAP_PATH, encoding="utf-8") as f:
        return json.load(f).get(stock_code)

def load_corp_names() -> dict[str, str]:
    """{회사명: 종목코드} 반환. 파일이 없으면 빈 dict(파싱은 watchlist 이름으로 폴백)."""
    try:
        with open(CORP_NAMES_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
# 고위험 공시 키워드 — 위험도 판단 노드에서 사용 (보고서 6.6절)
RISK_KEYWORDS = ["유상증자", "감사의견", "거래정지", "불성실공시", "상장폐지", "회생절차"]

MOCK_DISCLOSURES = {
    "005930": [
        {"corp_name": "삼성전자", "report_nm": "기업설명회(IR) 개최(안내공시)",
         "rcept_no": "20260706800001", "rcept_dt": "20260706",
         "summary": "국내 기관투자자 대상 2분기 실적 관련 기업설명회 개최 안내."},
    ],
    "247540": [
        {"corp_name": "에코프로비엠", "report_nm": "유상증자결정",
         "rcept_no": "20260706800002", "rcept_dt": "20260706",
         "summary": "시설자금 확보를 위한 제3자배정 유상증자 결정. 발행 규모는 시가총액 대비 약 4% 수준, 조달 목적은 양극재 생산라인 증설로 명시."},
    ],
    "035720": [
        {"corp_name": "카카오", "report_nm": "타법인 주식 및 출자증권 취득결정",
         "rcept_no": "20260706800003", "rcept_dt": "20260706",
         "summary": "AI 스타트업 지분 인수. 취득 금액은 자기자본 대비 소규모."},
    ],
}


import re as _re
import warnings as _warnings
from bs4 import BeautifulSoup as _BS, XMLParsedAsHTMLWarning
_warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


def get_document_text(rcept_no: str) -> str:
    """공시 원문 XML → 읽기 좋은 평문 변환. 표는 '항목 | 값' 구조로 보존."""
    import OpenDartReader
    api_key = os.environ.get("DART_API_KEY")
    if not api_key:
        return ""
    dart = OpenDartReader(api_key)
    try:
        # OpenDartReader 0.1.6에는 document_all 이 없다 → document(단일 문서 문자열) 사용.
        raw = dart.document(rcept_no)
    except Exception as e:
        print(f"[경고] document 실패: {e.__class__.__name__}")
        return ""
    if not raw:
        return ""
    raw_docs = raw if isinstance(raw, list) else [raw]  # 문자열/리스트 모두 처리

    parts: list[str] = []
    for doc in raw_docs:
        if not isinstance(doc, str):
            doc = str(doc)
        soup = _BS(doc, "html.parser")
        # 표를 평문화한 뒤 원본에서 제거 → 나머지 텍스트와 분리 처리
        for table in soup.find_all("table"):
            rows: list[str] = []
            for tr in table.find_all("tr"):
                cells = [
                    " ".join((td.get_text() or "").split())
                    for td in tr.find_all(["td", "th"])
                ]
                if any(cells):
                    rows.append(" | ".join(cells))
            table.replace_with("\n" + "\n".join(rows) + "\n")
        text = soup.get_text("\n")
        # 과도한 공백·빈 줄 정리
        text = _re.sub(r"[ \t]+", " ", text)
        text = _re.sub(r"\n{3,}", "\n\n", text)
        parts.append(text.strip())

    return "\n\n".join(parts)


REPLAY_SAMPLE_PATH = Path(__file__).resolve().parents[2] / "data" / "replay_sample.json"
_replay_index: dict[str, int] = {}


def _replay_search(stock_code: str) -> list[dict]:
    """REPLAY_MODE=true 일 때 호출. replay_sample.json 에서 해당 종목 공시를
    호출마다 한 건씩 순서대로 반환한다. 끝까지 가면 처음으로 순환."""
    with open(REPLAY_SAMPLE_PATH, encoding="utf-8") as f:
        pool = json.load(f)
    items = [d for d in pool if d.get("stock_code") == stock_code]
    if not items:
        items = pool  # 종목 필터 매칭 없으면 전체를 순환
    idx = _replay_index.get(stock_code, 0) % len(items)
    _replay_index[stock_code] = idx + 1
    picked = items[idx]
    picked.pop("stock_code", None)  # 내부 필드 제거 후 반환
    print(f"[리플레이] {picked.get('corp_name')} — {picked.get('report_nm')}")
    return [picked]


def dart_search(stock_code: str, bgn_de: str | None = None, end_de: str | None = None) -> list[dict]:
    """공시 목록 조회 — DART list.json 실호출. 기본은 '오늘' 하루.
    키·매핑이 없거나 호출이 실패하면 mock으로 폴백해 데모가 죽지 않게 한다."""
    from app.core.config import REPLAY_MODE
    if REPLAY_MODE:
        return _replay_search(stock_code)

    api_key = os.environ.get("DART_API_KEY")
    try:
        corp_code = get_corp_code(stock_code)
    except FileNotFoundError:              # corp_map.json 아직 안 만든 경우
        corp_code = None
    if not api_key or not corp_code:
        print(f"[경고] DART 실호출 불가(키/매핑 없음) → mock 사용: {stock_code}")
        return MOCK_DISCLOSURES.get(stock_code, [])

    today = datetime.now().strftime("%Y%m%d")
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bgn_de": bgn_de or today,          # 날짜 파라미터를 열어둔 이유:
        "end_de": end_de or today,          # 테스트 + D2 '리플레이 모드'의 씨앗
        "page_count": 20,
    }
    try:
        data = requests.get("https://opendart.fss.or.kr/api/list.json",
                            params=params, timeout=10).json()
    except Exception as e:
        print(f"[경고] DART 호출 실패 → mock 폴백: {e.__class__.__name__}")
        return MOCK_DISCLOSURES.get(stock_code, [])

    if data.get("status") == "013":         # 013 = 그 기간 공시 없음(정상 상황)
        return []
    if data.get("status") != "000":         # 020 사용한도 초과 등 그 외 오류
        print(f"[경고] DART 응답 {data.get('status')}: {data.get('message')} → mock 폴백")
        return MOCK_DISCLOSURES.get(stock_code, [])

    return [
        {
            "corp_name": it["corp_name"],
            "report_nm": it["report_nm"],
            "rcept_no": it["rcept_no"],
            "rcept_dt": it["rcept_dt"],
            # 원문 API 연동 전까지의 임시 요약 — 해석의 주 근거는 보고서명(report_nm)
            "summary": f"{it['rcept_dt']} 접수 — 상세는 원문 링크 참고",
        }
        for it in data.get("list", [])
    ]
