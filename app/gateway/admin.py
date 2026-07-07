"""[아키텍처 박스: 컴플라이언스 검토(HITL)] 관리자 화면 — D3 구현 지점.
TODO(D3): 대기 큐 목록 + 승인/반려 버튼 → 승인 시 알림함으로 발송."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/admin")


@router.get("/", response_class=HTMLResponse)
async def review_queue():
    return "<h2>컴플라이언스 검토 큐</h2><p>D3에서 구현: 고위험 공시 대기 목록 · 승인/반려</p>"
