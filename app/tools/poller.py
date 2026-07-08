"""[다이어그램 라벨: 공시 신규 게시 폴링] — 관심종목의 새 공시를 감지해 알림 파이프라인에 투입.

발표 안정성을 위해 '수동 트리거(B)'로 구현: /poll 호출 시 1회만 폴링한다.
5분 자동 루프(A)는 POLL_INTERVAL_SEC 상수만 두고 로드맵으로 남긴다.

규칙(HITL 게이트 유지):
- 새 공시 중 '일반'은 알림함으로 직행(deliver) → 홈 알림 패널에 바로 뜬다.
- '고위험'(유상증자·감사의견 등)은 검토 큐로(enqueue) → 관리자 승인 후에야 패널에 뜬다.
"""
from __future__ import annotations

from app.tools.dart import dart_search, RISK_KEYWORDS
from app.tools.notify_format import build_notification
from app.gateway.queue import deliver, enqueue
from app.gateway import watchlist

POLL_INTERVAL_SEC = 300          # (A) 자동 루프용 — 현재는 수동 트리거만 사용
_seen: set[str] = set()          # 이미 처리한 rcept_no — 폴링마다 재알림 방지


def _interpret_stub(corp_name: str, report_nm: str) -> str:
    """폴러 전용 경량 안내(무LLM). 상세 해석은 대화(/ask)에서 제공한다."""
    return f"{corp_name}의 '{report_nm}' 공시가 접수되었습니다. 원문에서 상세 내용을 확인하세요."


def poll_watchlist() -> dict:
    """관심종목의 새 공시를 1회 감지 → 일반은 알림함, 고위험은 검토 큐로 라우팅.

    Returns:
        {"new": 신규건수, "delivered": 알림함건수, "queued": 검토큐건수, "items": [...]}.
    """
    delivered = queued = 0
    items_out: list[dict] = []
    for it in watchlist.list_items():
        code = it.get("code", "")
        wl_name = it.get("name", "")
        for d in dart_search(code):
            rcept = d.get("rcept_no", "")
            if not rcept or rcept in _seen:          # 이미 본 공시는 건너뜀
                continue
            _seen.add(rcept)
            corp = d.get("corp_name") or wl_name
            report = d.get("report_nm", "")
            hits = [k for k in RISK_KEYWORDS if k in report]
            interp = _interpret_stub(corp, report)
            card = build_notification(corp, report, interp, rcept)
            if hits:                                  # 고위험 → 검토 큐(승인 후 발송)
                enqueue({
                    "corp_name": corp, "report_nm": report, "rcept_no": rcept,
                    "rcept_dt": d.get("rcept_dt", ""), "interpretation": interp,
                    "risk_keywords": hits, "card": card,
                })
                queued += 1
                items_out.append({"corp_name": corp, "report_nm": report, "route": "review"})
            else:                                     # 일반 → 알림함 직행
                deliver({"corp_name": corp, "report_nm": report, "rcept_no": rcept,
                         "interpretation": interp, "card": card})
                delivered += 1
                items_out.append({"corp_name": corp, "report_nm": report, "route": "alert"})
    return {"new": delivered + queued, "delivered": delivered,
            "queued": queued, "items": items_out}
