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
    test_parse_case_insensitive_stock(); print("PASS parse-case")
    print("SMOKE OK")
