"""오프라인 스모크 테스트 — API 키 없이(폴백 모드) CI에서 그대로 돈다.
'무너지면 안 되는 3가지'(가드레일·출처 강제·마스킹)만 검증한다."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools import redact, build_notification
from app.agent import run_agent


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


if __name__ == "__main__":
    test_redact_masks_secrets(); print("PASS redact")
    test_notification_has_source_and_disclaimer(); print("PASS notification")
    test_guardrail_blocks_trading_advice(); print("PASS guardrail")
    print("SMOKE OK")
