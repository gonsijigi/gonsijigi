"""오프라인 스모크 테스트 — API 키 없이(폴백 모드) CI에서 그대로 돈다.
'무너지면 안 되는 3가지'(가드레일·출처 강제·마스킹)만 검증한다."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools import redact, build_notification
from app.agent import run_agent
from app.agent.nodes import risk_node, parse_node


def test_redact_masks_secrets():
    out = redact("키 sk-FAKE-TESTKEY123456 문의 hong@test.com")
    assert "[API_KEY 마스킹]" in out and "[EMAIL 마스킹]" in out
    # 주민번호 + 한글 조사 회귀 — 한글은 \w라 \b 경계가 안 생겨 마스킹이 새던 케이스
    assert "1234567" not in redact("주민번호 900101-1234567입니다")
    # 알림함 적재 경로 회귀 — HITL 승인분 해석 원문(interpretation)도 발송 직전 마스킹
    from app.gateway.queue import deliver, list_notifications
    deliver({"corp_name": "테스트", "interpretation": "문의 hong@test.com / 900101-1234567입니다"})
    boxed = list_notifications()[-1]["interpretation"]
    assert "hong@test.com" not in boxed and "1234567" not in boxed, "알림함 마스킹 우회"


def test_notification_has_source_and_disclaimer():
    msg = build_notification("가나전자", "유상증자결정", "해석 문장.", "20260706800002")
    assert "rcpNo=20260706800002" in msg, "원문 출처 링크 누락"
    assert "투자 판단" in msg, "면책 문구 누락"


def test_guardrail_blocks_trading_advice():
    out = run_agent("ci_guard", "그래서 지금 팔까?", ["005930"])
    assert "매수·매도 판단" in out, "가드레일 미동작"


def test_risk_picks_actual_high_risk_disclosure():
    """P1 회귀 방지: 고위험 공시가 첫 번째가 아니어도, 실제로 걸린 '그 공시'가
    HITL 검토 대상(review_disclosure)으로 선택돼야 한다. (엉뚱한 공시가 큐에 들어가면 안 됨)"""
    state = {"disclosures": [
        {"corp_name": "삼성전자", "report_nm": "주식등의대량보유상황보고서",
         "rcept_no": "1", "rcept_dt": "20260101", "summary": "-"},
        {"corp_name": "에코프로비엠", "report_nm": "유상증자결정",
         "rcept_no": "2", "rcept_dt": "20260101", "summary": "-"},
    ]}
    out = risk_node(state)
    assert out["risk_level"] == "high", "고위험 미탐지"
    assert out["review_disclosure"]["corp_name"] == "에코프로비엠", "엉뚱한 공시 선택"
    assert "유상증자" in out["risk_keywords"], "위험 키워드 누락"


def test_risk_normal_when_no_keyword():
    """일반 공시만 있으면 normal — HITL로 새지 않아야 한다."""
    state = {"disclosures": [
        {"corp_name": "카카오", "report_nm": "임원ㆍ주요주주특정증권등소유상황보고서",
         "rcept_no": "3", "rcept_dt": "20260101", "summary": "-"},
    ]}
    out = risk_node(state)
    assert out["risk_level"] == "normal" and out["review_disclosure"] is None


def test_parse_rejects_junk():
    """무의미 입력(자모·랜덤)은 clarify=True 로 되묻어야 한다."""
    out = parse_node({"user_input": "ㅇ러ㅏㅁ"})
    assert out["clarify"] is True, "쓰레기 입력을 못 걸렀다"


def test_parse_extracts_stock_and_keyword():
    """질문에서 종목명과 키워드를 결정론적으로 뽑아야 한다."""
    out = parse_node({"user_input": "삼성전자 유상증자 있었어?"})
    assert out["clarify"] is False
    assert any(s["name"] == "삼성전자" for s in out["parsed_stocks"]), "종목 추출 실패"
    assert "유상증자" in out["parsed_keywords"], "키워드 추출 실패"


def test_parse_passes_plain_question():
    """종목/키워드가 없어도 의미 있는 문장이면 통과(되묻지 않음)."""
    out = parse_node({"user_input": "오늘 내 종목 공시 뭐 있었어?"})
    assert out["clarify"] is False


def test_fetch_recent_window():
    """'최근' 류 질문은 7일 창(시작일 반환), 그 외엔 당일(None)이어야 한다."""
    from app.agent.nodes.fetch import _recent_window
    assert _recent_window("SK하이닉스 최근 공시 해석해줘") is not None, "'최근' 미인식"
    assert _recent_window("요즘 카카오 공시 있어?") is not None, "'요즘' 미인식"
    assert _recent_window("오늘 내 종목 공시 뭐 있었어?") is None, "당일 질문에 창이 열림"


def test_five_category_mapping():
    """필수 5종 분류 — 보고서명 → 카테고리, 그 외는 None(알림 제외)."""
    from app.tools.categories import categorize
    assert categorize("단일판매ㆍ공급계약체결") == "수주"
    assert categorize("[기재정정]주요사항보고서(유상증자결정)") == "유상증자"
    assert categorize("주요사항보고서(전환사채권발행결정)") == "전환사채"
    assert categorize("임원ㆍ주요주주특정증권등소유상황보고서") == "내부자"
    assert categorize("연결재무제표기준영업(잠정)실적(공정공시)") == "실적"
    assert categorize("기업설명회(IR)개최(안내공시)") is None


def test_purpose_classifier():
    """유상증자 목적 분류 — 우세 금액 필드 기준, 단정 표현 없이 조건부 라벨."""
    from app.tools.categories import classify_purpose
    growth = classify_purpose("4. 자금조달의 목적 | 시설자금 (원) 2,799,999,666 | 운영자금 (원) 1,000")
    assert growth and growth.startswith("시설자금") and "경우가 많음" in growth
    debt = classify_purpose("시설자금 (원) 0 | 채무상환자금 (원) 5,000,000,000")
    assert debt and debt.startswith("채무상환자금") and "재무 부담" in debt
    assert classify_purpose("금액 표기가 없는 문서") is None
    assert "호재" not in (growth + debt) and "악재" not in (growth + debt), "단정 표현 금지"
    # DART 실서식 회귀 — 미사용 필드는 '-' 표기: 줄을 넘어 다음 필드 금액을 훔쳐
    # 채무상환(재무 부담)이 성장 라벨로 뒤집히던 결함
    dash = classify_purpose("시설자금 (원) | -\n영업양수자금 (원) | -\n"
                            "운영자금 (원) | -\n채무상환자금 (원) | 5,000,000,000")
    assert dash and dash.startswith("채무상환자금"), "미사용(-) 필드가 다음 금액을 가로챔"
    # 연도 오탐 회귀 — 서술문의 '2026년'을 금액으로 읽어 라벨을 지어내던 결함
    assert classify_purpose("운영자금 조달을 위해 2026년 중 발행 예정") is None, "연도를 금액으로 오인"


def test_parse_case_insensitive_stock():
    """영문 포함 종목명은 대소문자 무시로 매칭돼야 한다(sk하이닉스=SK하이닉스).
    corp_names.json이 없으면 기본 3종목만 있어 스킵(폴백)."""
    from app.tools.dart import load_corp_names
    if "SK하이닉스" not in load_corp_names():
        return  # 이름 인덱스 없으면 검증 불가 — 스킵
    out = parse_node({"user_input": "sk하이닉스 오늘 공시 알려줘"})
    assert any(s["code"] == "000660" for s in out["parsed_stocks"]), "대소문자 매칭 실패"


if __name__ == "__main__":
    test_redact_masks_secrets(); print("PASS redact")
    test_notification_has_source_and_disclaimer(); print("PASS notification")
    test_guardrail_blocks_trading_advice(); print("PASS guardrail")
    test_risk_picks_actual_high_risk_disclosure(); print("PASS risk-select")
    test_risk_normal_when_no_keyword(); print("PASS risk-normal")
    test_parse_rejects_junk(); print("PASS parse-junk")
    test_parse_extracts_stock_and_keyword(); print("PASS parse-entity")
    test_parse_passes_plain_question(); print("PASS parse-plain")
    test_fetch_recent_window(); print("PASS fetch-recent")
    test_five_category_mapping(); print("PASS five-category")
    test_purpose_classifier(); print("PASS purpose-label")
    test_parse_case_insensitive_stock(); print("PASS parse-case")
    print("SMOKE OK")
