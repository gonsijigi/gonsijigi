"""[다이어그램 라벨: 공시 신규 게시 5분 주기 폴링(cron)] — D3 구현 지점.
TODO(D3): asyncio 루프로 5분마다 dart_search 호출 → 새 rcept_no 감지 →
관심 종목 사용자에게 알림 파이프라인 투입. 리플레이 모드(과거 공시 재생)도 여기에."""
POLL_INTERVAL_SEC = 300
