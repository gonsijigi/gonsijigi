# D2 인수인계 — 과거 유사 공시 RAG (pgvector)

> 대상: 오늘 D2 작업을 이어받는 팀원
> 목표: 각자 **로컬 환경**을 세팅하고, 오늘 추가된 RAG가 무엇을 하는지 이해한 뒤 바로 개발/시연을 이어갈 수 있게 하기
> 기준 커밋: `8765764 feat: pgvector 기반 과거 유사 공시 RAG 구현 (D2)`

⚠️ **비밀정보 규칙**: 이 저장소는 Public입니다. 실제 키 값(`DART_API_KEY` 등)은 **이 문서·코드·커밋에 절대 적지 않습니다.** 문서엔 "어떤 변수가 필요한지 + 어디서 발급받는지"만 적고, 실제 값은 **안전한 1:1 채널**(비밀번호 관리도구·직접 전달)로만 주고받습니다.

---

## 1. 오늘 완료한 것 (D2 요약)

**한 줄**: 지금 들어온 공시를 해석할 때, **과거의 비슷한 공시**를 벡터 검색으로 찾아 "근거"로 붙여준다. 근거에 없는 말은 하지 않는 **오픈북** 원칙.

전체 파이프라인(LangGraph) 안에서의 위치:

```
가드레일 → 조회(fetch) → [해석(interpret) ← RAG 결합] → 위험도(risk) → 알림 | HITL
```

D2에서 추가·변경된 핵심 파일:

| 파일 | 역할 |
|---|---|
| `app/rag/db.py` | **PGEngine 팩토리.** `.env`의 `POSTGRES_*` 값으로 `postgresql+psycopg://…` 연결 문자열을 만들어 반환. `ingest.py`·`retriever.py`가 공용으로 import. |
| `app/rag/ingest.py` | **적재 파이프라인 (CLI).** DART 공시 수집 → 원문 추출 → 재귀 청킹 → 임베딩(bge-m3) → pgvector 저장. 실행: `python -m app.rag.ingest [--clear]` |
| `app/rag/retriever.py` | **검색.** `search_similar(query, k=5, score_threshold=0.5)` — 벡터 유사도 검색 후 메타데이터와 함께 반환. 연결/검색 실패 시 **빈 리스트로 graceful 처리**(서비스가 죽지 않음). |
| `app/agent/nodes/interpret.py` | **RAG 결합 지점.** 현재 공시로 쿼리를 만들어 `search_similar(query, k=3)` 호출 → 결과를 `[참고: 과거 유사 공시]`로 컨텍스트에 주입한 뒤 LLM 해석 생성. |

세부 파라미터(코드 기준):
- 적재 대상 키워드: `유상증자`, `자기주식`, `타법인` — 최근 6개월에서 키워드별 최대 15건
- 청킹: `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)`
- 임베딩: Ollama **`bge-m3`** (벡터 차원 **1024**), 테이블명 `disclosure_corpus`
- 검색 점수 = **거리**(작을수록 유사), `score_threshold=0.5`보다 먼 결과는 제외

---

## 2. Getting Started — 각자 로컬에서 처음부터 세팅

### 2-0. 필요 사양 (먼저 확인)

| 항목 | 권장 |
|---|---|
| 여유 디스크 | **약 15~20GB** (모델 + Docker 이미지 + 볼륨) |
| RAM | **16GB 권장** (8GB는 gemma3n 구동에 빠듯) |
| 모델 용량 | `gemma3n:e4b` **7.5GB** + `bge-m3` **1.2GB** |
| Python | **3.13** (아래 4번 이유 참고) |

> 💡 **가벼운 노트북용 대안**: RAM/디스크가 부족한 팀원은 로컬 `gemma3n`을 받지 말고, LLM을 **수업용 vLLM**(`.env`의 `LLM_BASE_URL`)로 설정하면 됩니다. 그 경우 **`bge-m3`(1.2GB) + Docker만** 있으면 됩니다. (임베딩용 `bge-m3`는 어떤 경우든 **필수** — RAG 검색이 이걸로 돌아갑니다.)

### 2-1. pgvector 컨테이너 띄우기 (Docker)

Docker를 설치한 뒤, 저장소 루트에서:

```bash
docker compose -f infra/docker-compose.yml up -d db
```

- 이미지 `pgvector/pgvector:pg16`, 포트 `5432`, DB/유저 `gonsijigi`
- 비밀번호 기본값은 `devpass` (로컬 개발용 — 3번 '안전 전달' 참고)

### 2-2. Ollama 설치 + 모델 받기

Ollama는 **각자 컴퓨터에서 도는 로컬 서버**라 API 키가 없습니다 (`localhost:11434`로 바로 붙음).

```bash
ollama pull bge-m3        # 임베딩 — 필수 (1.2GB)
ollama pull gemma3n:e4b   # 로컬 LLM로 돌릴 때만 (7.5GB) — 가벼운 노트북은 생략 가능
```

### 2-3. Python 3.13 + 의존성 설치

```bash
# uv 사용 시
uv pip install -r requirements.txt

# 또는 표준 venv
python3.13 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2-4. `.env` 만들기

```bash
cp .env.example .env
```

그런 다음 아래 형태로 값을 채웁니다 (**실제 값은 3번 '안전 전달' 참고 — 여기 예시엔 진짜 키 없음**):

```dotenv
# LLM — ⓐ / ⓑ 중 택1
# ⓐ 로컬 Ollama (이 저장소 개발자 기본 세팅)
LLM_BASE_URL=http://localhost:11434/v1/
LLM_API_KEY=ollama
LLM_MODEL=gemma3n:e4b
# ⓑ 수업용 vLLM (가벼운 노트북 대안) — 위 3줄 대신 아래로
# LLM_BASE_URL=http://<수업용-vLLM-주소>/v1/
# LLM_API_KEY=<수업용-API-KEY>
# LLM_MODEL=gemma-4-e4b-it

# DART — 실제 값은 안전 채널로 전달받아 채우기
DART_API_KEY=<opendart 발급 키>

# PostgreSQL + pgvector (docker-compose db 서비스 기준)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=gonsijigi
POSTGRES_USER=gonsijigi
POSTGRES_PASSWORD=devpass
```

### 2-5. 코퍼스 적재

pgvector 컨테이너 + Ollama(`bge-m3`) + `DART_API_KEY`가 모두 준비된 상태에서:

```bash
python -m app.rag.ingest --clear
```

- `--clear`는 기존 테이블을 지우고 새로 적재합니다.
- ⚠️ 이 명령은 **DART를 실시간 호출**합니다 → 실행 시점에 따라 수집되는 공시가 달라질 수 있습니다(정상). "유형별 확보 건수 / 총 청크 수 / 적재 완료" 로그가 찍히면 성공.

### 2-6. 실행 / 스모크 테스트

```bash
python tests/test_smoke.py     # → 마지막 줄에 "SMOKE OK"
```

앱 실행 & 콘솔 데모:

```bash
uvicorn app.main:app --reload  # 웹 (/, /admin)
python -m app.agent.graph      # 콘솔 데모 (질문 2건 자동 실행)
```

> ℹ️ **스모크 테스트는 오프라인에서 통과**합니다(Docker/Ollama/키 없이도 OK). CI가 이렇게 돕니다. 즉 세팅 도중이라도 스모크는 먼저 돌려볼 수 있고, **RAG의 실제 근거 주입은 pgvector+Ollama가 떠 있는 전체 흐름에서만** 확인됩니다.

---

## 3. 안전 전달 — 값이 아니라 '목록'만

| 변수 | 어디서 / 어떻게 | 문서 기재 |
|---|---|---|
| `DART_API_KEY` | opendart.fss.or.kr 에서 발급(이메일 인증) | **값 미기재** — 실제 값은 안전 채널로 별도 전달 |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | ⓐ 로컬 Ollama: `http://localhost:11434/v1/` · `ollama` · `gemma3n:e4b` (Ollama는 키 없음) <br> ⓑ 수업 vLLM: 수업에서 안내받은 주소·키 · `gemma-4-e4b-it` | ⓐ는 그대로 사용 가능 / ⓑ의 실제 주소·키는 안전 채널 |
| `POSTGRES_PASSWORD` | docker-compose 로컬 기본값 `devpass` | 로컬은 기본값 사용 · **운영 시 반드시 변경** |

> `.env`는 `.gitignore`에 포함되어 커밋되지 않습니다. 그래도 화면 공유·복붙 시 값이 새지 않도록 주의하세요.

---

## 4. 알아둘 함정 / 주의 (실제로 겪은 것)

- **CI는 Python 3.13이어야 함** — `opendartreader`가 3.13+를 요구합니다 (커밋 `3aa88f0`). 로컬도 3.13으로 맞추세요.
- **`data/replay_sample.json`의 접수번호는 더미**(미래 날짜)입니다 → 원문 추출이 불가하므로 **요약(summary)으로 처리**됩니다. 리플레이 모드는 발표 시각에 새 공시가 없을 때를 위한 재생 스위치(`REPLAY_MODE=true`).
- **RAG 점수는 '거리'** — 작을수록 유사합니다. 임계값 `0.5`로 무관한 결과를 걸러냅니다. 관련 없는 질문이면 근거가 **빈 리스트**로 나오는 게 정상입니다.
- **임베딩은 `bge-m3`(1024차원)로 고정**되어 있습니다(`ingest.py`·`retriever.py`). 다른 임베딩 모델로 바꾸면 벡터 차원이 달라지므로 **테이블을 `--clear`로 재생성**해야 합니다.
- **`ingest`는 외부 의존이 많습니다** — `DART_API_KEY` + 네트워크 + Ollama(`bge-m3`) + pgvector가 **모두 떠 있어야** 동작합니다. 실시간 수집이라 코퍼스 내용이 실행 시점마다 달라집니다.
- **`data/corp_map.json`은 `.gitignore` 대상**(DART 생성물)입니다. 이 파일은 **실시간 단일 종목 조회**(종목코드↔고유번호 매핑)에 필요하고, **D2 적재에는 불필요**합니다. 필요 시 `app/tools/dart.py`의 `build_corp_map()`로 생성합니다. 없으면 조회는 mock으로 폴백합니다.
- **main 직접 커밋 금지 → 항상 `feat/*` 브랜치 → PR → CI 초록불 → 머지.** 배경과 재발 방지 규칙은 `docs/발표_QA노트.md` 참고 (초반 한 차례 위반 사고 기록).

---

## 5. 아직 안 된 것 / 다음 할 일

- **`app/tools/poller.py`** — 5분 주기 폴링 루프(asyncio)가 아직 상수(`POLL_INTERVAL_SEC=300`)만 있고 TODO 상태. 새 `rcept_no` 감지 → 관심 종목 사용자 알림 파이프라인 투입.
- **`app/gateway/routes.py`** — 지금은 고정 포트폴리오(`KIM_GAEMI_PORTFOLIO`)입니다. **관심종목 등록 화면·알림함**이 다음 작업(PLAN.md의 D3).
- **발표 준비(D4)** — 리허설, 백업 시연 영상 녹화.
- **구현 금지(로드맵)** — BM25 앙상블·멀티쿼리, 웹푸시·알림톡, K8s 실배포, JWT 인증 등은 이번 스프린트 범위 밖(`docs/PLAN.md`·`CLAUDE.md` 참고).

> 상세 일자별 계획은 `docs/PLAN.md`, 데모 5장면은 `docs/demo_scenario.md` / `README.md` 참고.
