"""인메모리 HITL 대기 큐 — 프로세스 재시작 시 초기화됨(의도적).
실서비스에서는 Redis 또는 DB로 교체; 인터페이스(enqueue/list_queue/pop_by_id)는 유지.

큐 항목 스키마:
{
    "id":             str,   # UUID4 — 승인/반려 엔드포인트 식별자
    "corp_name":      str,
    "report_nm":      str,
    "rcept_no":       str,   # DART 원문 링크용
    "rcept_dt":       str,
    "interpretation": str,   # 승인 시 알림 카드 재사용
    "risk_keywords":  list,  # 어떤 키워드가 걸렸는지 화면 표시
    "queued_at":      str,   # "YYYY-MM-DD HH:MM:SS"
    "card":           str,   # build_notification 결과 — 승인 시 즉시 발송
}
"""
import uuid
from datetime import datetime

_queue: list[dict] = []


def enqueue(item: dict) -> None:
    item.setdefault("id", str(uuid.uuid4()))
    item.setdefault("queued_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    _queue.append(item)


def list_queue() -> list[dict]:
    return list(_queue)


def pop_by_id(item_id: str) -> dict | None:
    for i, item in enumerate(_queue):
        if item["id"] == item_id:
            return _queue.pop(i)
    return None
