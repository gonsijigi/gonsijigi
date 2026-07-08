"""관심종목 저장소 — 단일 사용자(김개미) 전제, data/watchlist.json 에 보존.
프로세스가 죽어도 유지되도록 파일 기반(인메모리 큐와 달리 등록 기능에 적합).
실서비스에서는 사용자별 DB로 교체; 인터페이스(list_items/add_item/remove_item)는 유지.

항목 스키마: {"code": "005930", "name": "삼성전자"}  # code = 6자리 종목코드
동시성은 단일 사용자 데모 전제로 신경 쓰지 않는다.
"""
from __future__ import annotations  # PEP604 어노테이션을 3.9에서도 허용
import json
import os
import re
from pathlib import Path

WATCHLIST_PATH = Path(__file__).resolve().parents[2] / "data" / "watchlist.json"

# 파일이 없을 때의 초기값 — 기존 하드코딩 관심종목(홈 화면 텍스트와 동일)
DEFAULT_ITEMS: list[dict] = [
    {"code": "005930", "name": "삼성전자"},
    {"code": "247540", "name": "에코프로비엠"},
    {"code": "035720", "name": "카카오"},
]

_CODE_RE = re.compile(r"^\d{6}$")  # 종목코드 = 숫자 6자리


def _save(items: list[dict]) -> None:
    os.makedirs(WATCHLIST_PATH.parent, exist_ok=True)
    with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def _load() -> list[dict]:
    """파일을 읽어 반환. 없으면 기본값으로 초기 생성 후 반환."""
    if not WATCHLIST_PATH.exists():
        seed = [dict(x) for x in DEFAULT_ITEMS]
        _save(seed)
        return seed
    with open(WATCHLIST_PATH, encoding="utf-8") as f:
        return json.load(f)


def list_items() -> list[dict]:
    """현재 관심종목 목록 — [{code, name}, ...]."""
    return _load()


def add_item(code: str, name: str) -> bool:
    """관심종목 추가. 6자리 숫자코드가 아니거나 중복이면 False(무시)."""
    code = (code or "").strip()
    name = (name or "").strip()
    if not _CODE_RE.match(code):
        return False
    items = _load()
    if any(it["code"] == code for it in items):  # 중복 코드는 무시
        return False
    items.append({"code": code, "name": name})
    _save(items)
    return True


def remove_item(code: str) -> bool:
    """관심종목 삭제. 해당 코드가 있으면 제거 후 True, 없으면 False."""
    code = (code or "").strip()
    items = _load()
    kept = [it for it in items if it["code"] != code]
    if len(kept) == len(items):  # 삭제된 게 없음
        return False
    _save(kept)
    return True
