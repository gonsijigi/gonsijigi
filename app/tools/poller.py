"""[다이어그램 라벨: 공시 신규 게시 폴링] — 관심종목의 새 공시를 감지해 알림 파이프라인에 투입.

발표 안정성을 위해 '수동 트리거(B)'로 구현: /poll 호출 시 1회만 폴링한다.
5분 자동 루프(A)는 POLL_INTERVAL_SEC 상수만 두고 로드맵으로 남긴다.

규칙(HITL 게이트 유지):
- 새 공시 중 '일반'은 알림함으로 직행(deliver) → 홈 알림 패널에 바로 뜬다.
- '고위험'(유상증자·감사의견 등)은 검토 큐로(enqueue) → 관리자 승인 후에야 패널에 뜬다.
"""
from __future__ import annotations

from app.tools.dart import dart_search, get_document_text, RISK_KEYWORDS
from app.tools.categories import categorize, classify_purpose
from app.tools.notify_format import build_notification
from app.gateway.queue import deliver, enqueue
from app.gateway import watchlist

POLL_INTERVAL_SEC = 300          # (A) 자동 루프용 — 현재는 수동 트리거만 사용
_seen: set[str] = set()          # 이미 처리한 rcept_no — 폴링마다 재알림 방지


def _interpret_stub(corp_name: str, report_nm: str, purpose: str | None = None) -> str:
    """폴러 전용 경량 안내(무LLM). 상세 해석은 대화(/ask)에서 제공한다."""
    base = f"{corp_name}의 '{report_nm}' 공시가 접수되었습니다. 원문에서 상세 내용을 확인하세요."
    return f"{base}\n자금조달: {purpose}" if purpose else base


def poll_watchlist() -> dict:
    """관심종목의 새 공시를 1회 감지 → 일반은 알림함, 고위험은 검토 큐로 라우팅.

    Returns:
        {"new": 신규건수, "delivered": 알림함건수, "queued": 검토큐건수, "items": [...]}.
    """
    delivered = queued = skipped = 0
    items_out: list[dict] = []
    for it in watchlist.list_items():
        code = it.get("code", "")
        wl_name = it.get("name", "")
        for d in dart_search(code):
            rcept = d.get("rcept_no", "")
            if not rcept or rcept in _seen:          # 이미 본 공시는 건너뜀
                continue
            _seen.add(rcept)
            corp = (d.get("corp_name") or wl_name).strip()
            # DART report_nm엔 꼬리 공백이 그대로 옴 → pre-wrap 화면에서 가로 넘침 유발, 정리
            report = " ".join(d.get("report_nm", "").split())
            hits = [k for k in RISK_KEYWORDS if k in report]
            cat = categorize(report)
            # [ORCHESTRATION] 선별 판정 — 에이전트가 '알릴 가치'를 결정하는 지점.
            # 생각: 이 공시가 개인투자자 필수 5종(수주/유상증자/전환사채/내부자/실적)인가,
            #       혹은 고위험 키워드에 걸리는가.
            # 행동: 둘 다 아니면 알림 자체를 생략(skip) — 알림 피로를 막는다.
            #       고위험은 카테고리와 무관하게 항상 검토 큐로(안전이 선별보다 우선).
            # [COST] 여기서 걸러진 공시는 원문 조회도 해석도 하지 않는다 —
            #        '알릴 가치가 있는 것에만 비용을 쓴다'의 핵심 지점.
            if not hits and cat is None:
                skipped += 1
                continue
            # 뱃지: 5종 카테고리 우선, 없으면 걸린 위험 키워드(거래정지 등)를 뱃지로
            badge = cat or (hits[0] if hits else "")
            # 유상증자는 원문에서 자금 목적을 읽어 라벨 (실패 시 라벨 생략 — 지어내지 않음).
            # [SAFETY] 라벨은 "~목적 (일반적으로 ~로 해석되는 경우가 많음)"까지만 —
            #          호재/악재 단정은 라벨 정책(categories.classify_purpose)에서도 금지.
            # [COST] 원문 조회는 유상증자일 때만 — 전 건 원문 조회 대비 외부 호출을 크게 줄인다.
            purpose = None
            if cat == "유상증자":
                try:
                    purpose = classify_purpose(get_document_text(rcept))
                except Exception:
                    purpose = None
            interp = _interpret_stub(corp, report, purpose)
            card = build_notification(corp, report, interp, rcept)
            if hits:                                  # [SAFETY] 고위험 → 검토 큐(사람 승인 후에만 발송)
                enqueue({
                    "corp_name": corp, "report_nm": report, "rcept_no": rcept,
                    "rcept_dt": d.get("rcept_dt", ""), "interpretation": interp,
                    "risk_keywords": hits, "card": card,
                    "category": badge, "purpose": purpose or "",
                })
                queued += 1
                items_out.append({"corp_name": corp, "report_nm": report,
                                  "category": cat, "route": "review"})
            else:                                     # 일반(5종) → 알림함 직행
                deliver({"corp_name": corp, "report_nm": report, "rcept_no": rcept,
                         "interpretation": interp, "card": card,
                         "category": badge, "purpose": purpose or ""})
                delivered += 1
                items_out.append({"corp_name": corp, "report_nm": report,
                                  "category": cat, "route": "alert"})
    return {"new": delivered + queued, "delivered": delivered,
            "queued": queued, "skipped": skipped, "items": items_out}
