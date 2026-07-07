"""[아키텍처 박스: MCP 도구 서버] dart_search — 공시 조회.
프로토타입은 mock, 실제 DART OpenAPI 호출 코드는 아래 docstring 참고.
여유가 생기면 FastMCP 서버로 분리한다(수업 MCP 실습 패턴)."""
from datetime import datetime

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


def dart_search(stock_code: str) -> list[dict]:
    """당일 공시 목록 조회. (D1 작업: 아래 실제 호출로 교체)

    실제 구현 (DART OpenAPI — https://opendart.fss.or.kr):
    import requests, os
    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": os.environ["DART_API_KEY"],   # .env 로 관리, 절대 커밋 금지
        "corp_code": corp_code,                     # 종목코드 → 고유번호(corpCode.xml) 매핑 필요
        "bgn_de": datetime.now().strftime("%Y%m%d"),
        "end_de": datetime.now().strftime("%Y%m%d"),
    }
    return requests.get(url, params=params, timeout=10).json().get("list", [])
    """
    return MOCK_DISCLOSURES.get(stock_code, [])
