"""공시지기 진입점.  실행: uvicorn app.main:app --host 0.0.0.0 --port 8000
폴더 구조는 docs/architecture.png 의 박스와 1:1 대응한다 — README 매핑표 참고."""
from fastapi import FastAPI

from app.gateway.routes import router as gateway_router
from app.gateway.admin import router as admin_router

app = FastAPI(title="공시지기 MVP")
app.include_router(gateway_router)
app.include_router(admin_router)
# D3: app.tools.poller 의 5분 폴링 루프를 startup 이벤트로 연결
