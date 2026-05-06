# Plan — FastAPI + LangGraph 백엔드 (API_SPEC_1.3 기반)

## Context

**왜 이 작업이 필요한가**
현재 [PreDev-Backend](README.md) 레포는 [solar.py](solar.py) / [gemini.py](gemini.py) / [client.py](client.py)로 구성된 단일 엔드포인트(`POST /generate`) stateless 프로토타입이다. 이는 시스템 프롬프트만 포함된 "LLM 응답 프록시" 수준이며, 실제 게임에 필요한 세션 관리·상태 머신·SSE 스트리밍·호감도 평가·이벤트/엔딩 트리거가 전혀 없다.

`C:/Users/Ashcircle/Documents/Personal/project/ASM_AI/.claude/API_SPEC_1.3.md`에서 정의한 v1.3 API 스펙은 Monogatari Full SPA 프론트와 통신하는 **상태 기반 게임 백엔드**를 요구한다. 본 작업의 목표는:

1. API_SPEC_1.3의 모든 엔드포인트(§2~§6)와 SSE 이벤트 스트림(§3.2)을 구현
2. §1.6에 정의된 룰 엔진(씬 전환 / 호감도 이벤트 / 엔딩) — LLM이 아닌 **BE가 결정**
3. LangGraph 기반 LLM 파이프라인: **가드레일(인젝션 탐지) → 호감도 평가 → 응답 생성** 3단계 노드 그래프
4. PostgreSQL(pgvector) 기반 세션·메시지 저장 및 **대화 로그 RAG**
5. 로컬 도커 컴포즈로 `app + db` 두 서비스 단일 명령 실행

## 핵심 설계 결정

| 영역 | 결정 |
|---|---|
| 프레임워크 | FastAPI (async), uvicorn |
| LLM | Solar API (`solar-pro3`) — OpenAI 호환 클라이언트로 streaming 호출 |
| 임베딩 | Solar `embedding-passage` / `embedding-query` (1024 dim) |
| 그래프 | LangGraph `StateGraph` — 노드 3개(guardrail → evaluate_affinity → generate_response) |
| DB ORM | SQLAlchemy 2.x async + asyncpg |
| Vector | pgvector `VECTOR(1024)` 컬럼, `ivfflat` 인덱스 |
| 마이그레이션 | Alembic (init 1개) |
| 의존성 | uv + pyproject.toml |
| 컨테이너 | Docker Compose (`app` + `db`) |
| 인증 | Cookie 기반 (`session_id`, HttpOnly, SameSite=Lax). 로컬에선 Secure=false |
| SSE | `EventSourceResponse` (sse-starlette), 의미 단위 청킹 |
| 로깅/설정 | Pydantic Settings + 구조적 로깅 (uvicorn 기본) |

## 디렉토리 구조 (신규)

```
PreDev-Backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, lifespan, CORS, 공통 에러 핸들러
│   ├── config.py               # Settings (env 로드)
│   ├── database.py             # AsyncEngine, AsyncSessionLocal, get_db
│   ├── deps.py                 # 쿠키→세션 의존성 (require_session)
│   ├── api/v1/
│   │   ├── __init__.py
│   │   ├── router.py           # APIRouter 결합
│   │   ├── sessions.py         # §2.1~2.4
│   │   ├── chat.py             # §3.2 SSE, §3.3 suggestions, §3.5 history
│   │   ├── scenes.py           # §4.1
│   │   ├── ending.py           # §5.1
│   │   └── health.py           # §6.1
│   ├── schemas/
│   │   ├── enums.py            # Emotion, SceneId, EventId, EndingId, MessageRole
│   │   ├── common.py           # ApiResponse[T], ApiError, ok()/err() 헬퍼
│   │   ├── game.py             # GameState, SceneInfo, IntroDialogue
│   │   └── chat.py             # ChatRequest, SSE event payloads
│   ├── models/
│   │   └── orm.py              # Session, Message, TriggeredEvent, MessageEmbedding
│   ├── services/
│   │   ├── session_service.py  # CRUD + cookie helpers
│   │   ├── trigger_engine.py   # §1.6 룰 엔진 (씬/이벤트/엔딩 결정)
│   │   ├── scene_config.py     # 씬 임계값 테이블 + 인트로 대사
│   │   ├── chat_service.py     # SSE 오케스트레이션 (그래프 호출, DB 저장, 트리거 발행)
│   │   ├── suggestion_service.py
│   │   └── vector_store.py     # pgvector 검색 (top-k 과거 대화)
│   ├── llm/
│   │   ├── solar_client.py     # AsyncOpenAI(base_url=Upstage), embeddings + streaming
│   │   ├── prompts.py          # SYSTEM_PROMPT(소마 페르소나) + 씬별 프롬프트 빌더
│   │   ├── nodes.py            # guardrail / evaluate_affinity / generate_response
│   │   └── graph.py            # StateGraph 정의 + compile()
│   └── utils/
│       └── sse.py              # event/data 직렬화 헬퍼
├── alembic/
│   ├── env.py
│   └── versions/0001_init.py   # sessions, messages, triggered_events, message_embeddings
├── alembic.ini
├── docker/
│   ├── Dockerfile              # python:3.12-slim + uv
│   └── postgres/
│       └── init.sql            # CREATE EXTENSION vector;
├── docker-compose.yml          # services: app, db
├── pyproject.toml              # uv 관리
├── .env.example
├── .dockerignore
└── README.md                   # 실행/개발 가이드 갱신
```

기존 [solar.py](solar.py), [gemini.py](gemini.py), [client.py](client.py) 는 삭제.
[solar.py](solar.py)의 `SYSTEM_PROMPT` 본문은 `app/llm/prompts.py`로 이전하여 그대로 활용한다 (Soma 페르소나).

## 데이터 모델 (PostgreSQL)

```
sessions
  id              UUID PK
  player_name     VARCHAR(20)  NULL until /sessions/me/start
  affinity        INT         DEFAULT 0
  chat_count      INT         DEFAULT 0
  chat_limit      INT         DEFAULT 50
  current_scene_id VARCHAR(64) DEFAULT 'SCENE_INTRO'
  emotion         VARCHAR(16)  DEFAULT 'NEUTRAL'
  is_started      BOOLEAN     DEFAULT false
  is_ended        BOOLEAN     DEFAULT false
  created_at      TIMESTAMPTZ
  updated_at      TIMESTAMPTZ
  last_active_at  TIMESTAMPTZ

messages
  id              UUID PK
  session_id      UUID FK
  role            VARCHAR(16)  -- USER/ASSISTANT/NARRATION/SYSTEM_EVENT
  content         TEXT
  emotion         VARCHAR(16) NULL
  scene_id        VARCHAR(64) NULL
  affinity_after  INT NULL
  created_at      TIMESTAMPTZ
  INDEX (session_id, created_at DESC)

triggered_events
  session_id      UUID FK
  event_id        VARCHAR(64)
  triggered_at    TIMESTAMPTZ
  PRIMARY KEY (session_id, event_id)   -- §1.6.2 1회성 보장

message_embeddings
  message_id      UUID PK FK→messages.id
  session_id      UUID FK
  embedding       VECTOR(1024)
  ivfflat 인덱스 on embedding vector_cosine_ops
```

## 핵심 모듈 설계

### `app/services/trigger_engine.py` — §1.6 룰 엔진
순수 함수 단일 진입점:
```python
def evaluate_triggers(prev_state, new_affinity, new_chat_count, fired_events: set[str]) -> TriggerResult
```
반환값: `TriggerResult(next_scene_id?: SceneId, event_id?: EventId, is_ending: bool)`.
§1.6.4의 우선순위(인터럽트 → 이벤트 → 엔딩 → 씬 전환)를 그대로 구현. 씬 임계값은 `scene_config.SCENE_THRESHOLDS` 딕셔너리로 관리 (§1.6.1 표).

### `app/llm/graph.py` — LangGraph
```
START → retrieve_context → guardrail → evaluate_affinity → generate_response → END
```

State (`TypedDict`):
```python
class ChatGraphState(TypedDict):
    user_message: str
    session: SessionSnapshot       # affinity/chat_count/scene_id/player_name/emotion
    retrieved_messages: list[dict] # vector_store top-k
    is_injection: bool
    affinity_delta: int            # 가드레일 결과로 -50/-100 가능
    new_emotion: str
    response_stream: AsyncIterator[str]  # generate_response 노드가 마지막에 채움
```

- **retrieve_context**: `vector_store.search(session_id, query=user_message, k=4)`
- **guardrail**: Solar 1회 호출(JSON 모드). 출력 `{is_injection: bool, severity: 0|1|2}`. severity 1=-50, 2=-100.
- **evaluate_affinity**: Solar 1회 호출(JSON 모드). 입력=대화 컨텍스트+페르소나, 출력 `{delta: int(-20..+20), new_emotion: Emotion}`. is_injection=true면 스킵하고 가드레일이 정한 delta 사용.
- **generate_response**: Solar streaming 호출, `delta` 토큰을 외부로 yield. SSE 레이어에서 의미 단위(2~10토큰)로 묶어 송출.

`chat_service.py`가 그래프를 `astream_events`로 실행하면서 SSE 이벤트를 순서대로 발행한다:
1. `meta` (scene_id + 그래프가 결정한 new_emotion 후보 — 실제로는 generate 직전에 확정되므로 evaluate_affinity 완료 시점에 발행)
2. `delta`×N (generate_response 스트림)
3. `state` (DB 커밋 후 최신 affinity/progress/chat_count/emotion)
4. `event_trigger` (조건부)
5. `scene_transition` (조건부)
6. `end`

### `app/api/v1/chat.py` — SSE 엔드포인트
```python
@router.post("/chat")
async def chat(req: ChatRequest, session: Session = Depends(require_session)):
    return EventSourceResponse(chat_service.stream(session, req.message))
```
입력 검증: `Field(min_length=1, max_length=300)` + 공백 trim. 빈 입력 400.
세션 미존재 401 (`SESSION_REQUIRED`), `is_ended=true`면 409 (`GAME_ALREADY_ENDED`).

### `app/services/chat_service.py` — 오케스트레이션
1. 사용자 메시지 DB 저장
2. 임베딩 비동기 생성 후 `message_embeddings` 저장 (백그라운드)
3. LangGraph 호출 → SSE 이벤트 스트림
4. 응답 텍스트 누적 후 ASSISTANT 메시지 DB 저장 (+ 임베딩)
5. `trigger_engine.evaluate_triggers()` 호출
6. 결과를 `event_trigger`/`scene_transition` SSE 이벤트로 변환
7. 세션 state 커밋 (`affinity`, `chat_count`, `current_scene_id`, `emotion`, `is_ended`)
8. 트리거된 event는 `triggered_events`에 기록 (1회성 보장)

### 인트로/엔딩 처리
- `SCENE_INTRO`는 §1.6.1 "LLM 미사용, 자동 인트로" — `scene_config.INTRO_DIALOGUES`에 정적 데이터로 저장. `/scenes/current`가 그대로 반환.
- 다른 씬도 `intro_dialogues`는 `scene_config`에 정적 정의(스펙 §4.1 예시 형식). LLM이 생성하지 않음.
- 엔딩 narrative는 `/game/ending` 호출 시 LLM 1회 호출로 생성하고 결과는 캐시(`sessions.ending_narrative` 컬럼 추가) — 재호출 시 동일 텍스트 반환.

## API 엔드포인트 매핑

| 스펙 § | 메서드 + 경로 | 핵심 로직 |
|---|---|---|
| §2.1 | `GET /api/v1/sessions/me` | 쿠키 없거나 세션 없으면 `has_session: false`. 있으면 GameState 일부 반환 |
| §2.2 | `POST /api/v1/sessions` | 신규 UUID 생성, `Set-Cookie: session_id=...`. 기존 세션 + `force_reset=false`면 409 |
| §2.3 | `POST /api/v1/sessions/me/start` | `player_name` 검증(1~20자), `is_started=true`, `current_scene_id=SCENE_INTRO` |
| §2.4 | `GET /api/v1/sessions/me/resume` | GameState + 현재 씬 정보 + 최근 N(default 6) 메시지 |
| §3.2 | `POST /api/v1/chat` | SSE — 위 chat_service 흐름 |
| §3.3 | `GET /api/v1/chat/suggestions` | `suggestion_service`: Solar 1회 호출(JSON 배열), 호감도 상승 방향만 |
| §3.5 | `GET /api/v1/chat/history` | 커서 페이지네이션 (`before=message_id`) |
| §4.1 | `GET /api/v1/scenes/current` | 세션의 `current_scene_id` → `scene_config`에서 메타 반환 |
| §5.1 | `GET /api/v1/game/ending` | `is_ended=false`면 425. true면 `ending_id` 산출 + narrative 캐시 |
| §6.1 | `GET /api/v1/health` | `{status, llm_provider, db}` — DB ping + Solar 헬스 체크(가벼운 모델 리스트) |

공통 응답 포맷 `{ok, data}` / `{ok, error: {code, message}}`은 `app/schemas/common.py`의 헬퍼(`ok(data)`, `err(code, message, status)`)로 통일. 전역 예외 핸들러로 `HTTPException` → `ok=false` 형태로 변환.

## 도커 구성

### `docker-compose.yml`
```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports: ["5432:5432"]
    healthcheck: pg_isready

  app:
    build: { context: ., dockerfile: docker/Dockerfile }
    env_file: .env
    depends_on:
      db: { condition: service_healthy }
    ports: ["8000:8000"]
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    volumes: [".:/app"]   # 개발 편의 (운영에서는 제거)

volumes:
  pgdata:
```

### `docker/Dockerfile`
```dockerfile
FROM python:3.12-slim
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev || uv sync
COPY . .
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `.env.example`
```
SOLAR_API_KEY=
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/somagame
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=somagame
SESSION_COOKIE_NAME=session_id
SESSION_COOKIE_SECURE=false
ALLOWED_ORIGINS=http://127.0.0.1:5500,http://localhost:5500
CHAT_LIMIT_DEFAULT=50
EMBEDDING_MODEL=embedding-passage
LLM_MODEL=solar-pro3
```

## 핵심 의존성 (`pyproject.toml`)

```
fastapi[standard]      # 0.115+
uvicorn[standard]
sse-starlette
pydantic[settings]     # 2.x
sqlalchemy[asyncio]    # 2.x
asyncpg
alembic
pgvector               # SQLAlchemy 어댑터
langgraph              # 0.2+
langchain-core
openai                 # Solar(OpenAI 호환) 호출용
httpx
python-dotenv
```

## 작업 단계 (구현 순서)

1. **clean-up + scaffolding**
   - 기존 [solar.py](solar.py)/[gemini.py](gemini.py)/[client.py](client.py) 삭제
   - `pyproject.toml` 작성, `.env.example`/`.dockerignore` 생성
   - `app/` 디렉토리 + 빈 모듈 골격 + `app/main.py` 최소 동작
2. **DB 레이어**
   - SQLAlchemy ORM 모델, `database.py`, Alembic 초기화 + 0001_init 마이그레이션 (pgvector 컬럼 포함)
3. **공통 스키마/유틸**
   - `schemas/enums.py` (스펙 §1.4 ENUM 1:1 옮기기)
   - `schemas/common.py` (`ok()`, `err()`, 전역 예외 핸들러)
   - `utils/sse.py`
4. **세션 API (§2.1~2.4)**
   - `session_service`, `deps.require_session`, 쿠키 발급/검증
5. **씬 설정 + 트리거 엔진**
   - `scene_config.py`(임계값+intro_dialogues), `trigger_engine.py` (단위 테스트 가능한 순수 함수)
6. **LLM 레이어**
   - `solar_client.py`, `prompts.py` (Soma 페르소나 + 씬 컨텍스트 빌더), `nodes.py`, `graph.py`
7. **Vector store**
   - `vector_store.py` (insert + cosine top-k)
8. **Chat SSE (§3.2)**
   - `chat_service.stream()` 제너레이터 + `chat.py` 엔드포인트
9. **나머지 API**
   - suggestions(§3.3), history(§3.5), scenes/current(§4.1), ending(§5.1), health(§6.1)
10. **Docker / 런타임**
    - `Dockerfile`, `docker-compose.yml`, `init.sql`, README 갱신

## Verification (E2E)

도커 환경 부팅:
```bash
cp .env.example .env   # SOLAR_API_KEY 채우기
docker compose up --build
```

수동 시나리오 (스펙 §8.1 따라가기):
```bash
# 1) 세션 없음 확인
curl -i http://localhost:8000/api/v1/sessions/me
# 기대: 200 {"ok":true,"data":{"has_session":false}}

# 2) 새 게임 시작
curl -i -c cookies.txt -X POST http://localhost:8000/api/v1/sessions \
     -H 'Content-Type: application/json' -d '{"force_reset":false}'

# 3) 이름 입력
curl -i -b cookies.txt -X POST http://localhost:8000/api/v1/sessions/me/start \
     -H 'Content-Type: application/json' -d '{"player_name":"민성"}'

# 4) 현재 씬
curl -b cookies.txt http://localhost:8000/api/v1/scenes/current

# 5) SSE 채팅
curl -N -b cookies.txt -X POST http://localhost:8000/api/v1/chat \
     -H 'Content-Type: application/json' \
     -H 'Accept: text/event-stream' \
     -d '{"message":"커널 디버깅 어떻게 하세요?"}'
# 기대: meta → delta×N → state → end (필요 시 event_trigger / scene_transition)

# 6) 헬스
curl http://localhost:8000/api/v1/health
# 기대: {"ok":true,"data":{"status":"healthy","llm_provider":"ok","db":"ok"}}
```

추가 검증:
- **SSE 이벤트 순서**: §1.6.4 우선순위에 따라 `event_trigger`가 `scene_transition`보다 먼저 나오는지(예: chat_count 임계값+호감도 임계값 동시 도달 시).
- **이벤트 1회성**: 같은 임계값 재통과 시 `event_trigger` 미발행 — `triggered_events` 테이블 확인.
- **인터럽트 엔딩**: 호감도가 -100에 도달하면 `SCENE_ENDING_INSTANT_BAD`로 즉시 전환되고, 이후 `/api/v1/chat` 호출 시 `GAME_ALREADY_ENDED` 반환.
- **이어하기**: 컨테이너 재시작 후 동일 쿠키로 `/sessions/me/resume` 호출 시 직전 상태 복원.
- **Alembic**: `docker compose run --rm app alembic current` 로 head 확인.
- **pgvector**: `docker compose exec db psql -U postgres -d somagame -c "SELECT extname FROM pg_extension;"` 에 `vector` 포함.

## 비범위 (이번 PR에서 다루지 않음)

- 단위/통합 테스트(pytest) — 별도 후속 PR
- Rate limit (`429 RATE_LIMITED`) 미들웨어 — 스펙에 코드만 정의, 본 PR은 헤더 자리만 마련하고 실제 구현은 후속
- 운영용 로깅/메트릭(prometheus 등)
- HTTPS/Secure 쿠키 (로컬 dev 기준이므로 비활성)
- FE 관련 매핑 테이블 (스펙 §9.2는 FE 책임)
