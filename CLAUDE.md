# 공시지기 — Claude Code 작업 규칙

## 한 줄 소개
개인투자자용 공시 알림·해석 AI Agent. 게시 5분 내 근거(원문 링크) 붙은 해석. 매매 판단은 안 함(가드레일).

## 현재 상태
- 완료: DART 실연동+corpCode 매핑(app/tools/dart.py), 로컬 Ollama gemma3n:e4b 연결(.env)
- 남은 것: docs/PLAN.md 의 Day 1 B트랙(관심종목 등록·알림함·/admin), Day 2(리플레이 모드·HITL 연결·리허설)

## 절대 규칙
- .env·API 키를 코드/커밋에 넣지 않는다
- 출처·면책·마스킹은 notify_format.py / redact.py 코드가 강제 — 프롬프트로 옮기지 말 것
- 로드맵 항목(웹푸시·알림톡, 앙상블·멀티쿼리, K8s 실배포, MCP 분리, A2A/Handoff, 마이데이터) 구현 금지
- main 직접 push 금지(브랜치→PR), 변경 후 python tests/test_smoke.py 통과 필수
- 구조 원칙: docs/architecture.png 의 박스 = 폴더 (README 매핑표)

## 팀 규칙 (반드시 지킬 것)
- 브랜치: main 직접 커밋 금지. feat/* 브랜치 → PR → CI 초록불 → 머지
- 비밀정보: API 키·토큰은 .env로만 관리. 코드·커밋·이 파일에 절대 쓰지 않기
- 테스트: 코드 수정 후 python tests/test_smoke.py 로 SMOKE OK 확인
- 구현 경계: 카카오톡 알림, MyData, KIND 거래정지, JWT 인증, Redis, K8s 실배포는
  이번 스프린트 구현 금지 (로드맵 선언만 — docs/PLAN.md 참고)
- pgvector는 타임박스 2시간, 실패 시 인메모리 전환 후 번복 금지
- 답변은 한국어로. 파일을 고치기 전에 계획을 먼저 설명하고 승인받을 것