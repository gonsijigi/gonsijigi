"""오프라인 스모크 테스트 — API 키 없이(폴백 모드) CI에서 그대로 돈다.
'무너지면 안 되는 3가지'(가드레일·출처 강제·마스킹)만 검증한다."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools import redact, build_notification
from app.agent import run_agent
from app.agent.nodes import risk_node


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


if __name__ == "__main__":
    test_redact_masks_secrets(); print("PASS redact")
    test_notification_has_source_and_disclaimer(); print("PASS notification")
    test_guardrail_blocks_trading_advice(); print("PASS guardrail")
    test_risk_picks_actual_high_risk_disclosure(); print("PASS risk-select")
    test_risk_normal_when_no_keyword(); print("PASS risk-normal")
    print("SMOKE OK")
