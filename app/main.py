"""공시지기 진입점 — FastAPI 앱 조립.

실행: uvicorn app.main:app --port 8010  (리플레이: REPLAY_MODE=true 를 앞에)
구조: 라우터 3개(사용자 홈·관리자 검토·관심종목)를 조립만 한다 — 로직은 각 모듈에.
폴더 구조는 docs/architecture.png 의 박스와 1:1 대응 — README 매핑표 참고.
"""
from fastapi import FastAPI

from app.gateway.routes import router as gateway_router
from app.gateway.admin import router as admin_router
from app.gateway.watchlist_routes import router as watchlist_router

app = FastAPI(title="공시지기 MVP")
app.include_router(gateway_router)
app.include_router(admin_router)
app.include_router(watchlist_router)
# D3: app.tools.poller 의 5분 폴링 루프를 startup 이벤트로 연결
