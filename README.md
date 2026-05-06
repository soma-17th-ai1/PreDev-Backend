# PreDev-Backend

**커널을 좋아하는 옆자리의 그녀** — FastAPI + LangGraph 백엔드 (API_SPEC v1.3 구현체).

- 게임 상태 머신, SSE 스트리밍 채팅, 호감도/이벤트/엔딩 룰 엔진을 BE에서 결정
- LLM은 [Solar API](https://console.upstage.ai) (`solar-pro3`) — OpenAI 호환 클라이언트로 호출
- 세션·메시지·임베딩은 PostgreSQL + [pgvector](https://github.com/pgvector/pgvector)
- LangGraph 3-노드 파이프라인: `retrieve_context → guardrail → evaluate_affinity` 후 응답 스트리밍

## 빠른 시작 (Docker Compose)

1. 레포 루트에 `.env` 생성

   ```bash
   cp .env.example .env
   # .env 의 SOLAR_API_KEY 채우기
   ```

2. 컨테이너 부팅

   ```bash
   docker compose up --build
   ```

   - `db` (pgvector/pgvector:pg16) 가 먼저 healthy 상태가 되면
   - `app` 이 `alembic upgrade head` 후 `uvicorn` 으로 8000 포트에 서비스됩니다.

3. 헬스 체크

   ```bash
   curl http://localhost:8000/api/v1/health
   ```

## 디렉토리 구조

```
app/
├── main.py                 # FastAPI 진입점, 전역 예외 핸들러
├── config.py               # Pydantic Settings (.env 로드)
├── database.py             # AsyncEngine + SessionLocal
├── deps.py                 # require_session (쿠키→세션)
├── api/v1/                 # 엔드포인트 레이어
│   ├── sessions.py         # §2.1~§2.4
│   ├── chat.py             # §3.2 SSE / §3.3 / §3.5
│   ├── scenes.py           # §4.1
│   ├── ending.py           # §5.1
│   └── health.py           # §6.1
├── schemas/                # Pydantic ENUM·요청/응답 모델
├── models/orm.py           # SQLAlchemy ORM
├── services/
│   ├── session_service.py  # 세션 CRUD
│   ├── scene_config.py     # 씬 임계값 + intro_dialogues (§1.6.1, §4.1)
│   ├── trigger_engine.py   # §1.6 룰 엔진 (순수 함수)
│   ├── chat_service.py     # SSE 오케스트레이션
│   ├── suggestion_service.py
│   ├── ending_service.py
│   └── vector_store.py     # pgvector 임베딩 저장/검색
├── llm/
│   ├── solar_client.py     # Async Solar (OpenAI 호환) 래퍼
│   ├── prompts.py          # Soma 페르소나 + 컨텍스트 빌더
│   ├── nodes.py            # LangGraph 노드 3개
│   └── graph.py            # StateGraph 컴파일
└── utils/sse.py
alembic/                    # 0001_init: pgvector 포함 4 테이블
docker/                     # Dockerfile, init.sql
docker-compose.yml
pyproject.toml              # uv 관리
```

## 주요 엔드포인트 (API_SPEC v1.3)

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET`  | `/api/v1/sessions/me` | 세션 존재 여부 |
| `POST` | `/api/v1/sessions` | 신규 세션 (force_reset 지원) |
| `POST` | `/api/v1/sessions/me/start` | 이름 입력 → 인트로 진입 |
| `GET`  | `/api/v1/sessions/me/resume` | 이어 하기 |
| `POST` | `/api/v1/chat` | **SSE** — meta → delta → state → (event_trigger) → (scene_transition) → end |
| `GET`  | `/api/v1/chat/suggestions` | 호감도 상승 방향 예시 답안 |
| `GET`  | `/api/v1/chat/history` | 커서 페이지네이션 |
| `GET`  | `/api/v1/scenes/current` | 현재 씬 메타 |
| `GET`  | `/api/v1/game/ending` | 엔딩 콘텐츠 (LLM 1회 생성 후 캐시) |
| `GET`  | `/api/v1/health` | 헬스 체크 |

응답은 모두 `{"ok": true, "data": ...}` / `{"ok": false, "error": {"code", "message"}}` 형식입니다.

## 수동 검증 시나리오

```bash
# 1) 세션 없음 확인
curl -i http://localhost:8000/api/v1/sessions/me

# 2) 새 게임 시작 (쿠키 저장)
curl -i -c cookies.txt -X POST http://localhost:8000/api/v1/sessions \
     -H 'Content-Type: application/json' -d '{"force_reset":false}'

# 3) 이름 입력
curl -b cookies.txt -X POST http://localhost:8000/api/v1/sessions/me/start \
     -H 'Content-Type: application/json' -d '{"player_name":"민성"}'

# 4) 현재 씬
curl -b cookies.txt http://localhost:8000/api/v1/scenes/current

# 5) SSE 채팅
curl -N -b cookies.txt -X POST http://localhost:8000/api/v1/chat \
     -H 'Content-Type: application/json' -H 'Accept: text/event-stream' \
     -d '{"message":"커널 디버깅 어떻게 하세요?"}'
```

## 로컬 개발 (도커 없이)

```bash
uv sync
cp .env.example .env       # DATABASE_URL을 로컬 postgres에 맞게 수정
docker compose up -d db    # DB만 도커로 띄우는 것 추천
alembic upgrade head
uvicorn app.main:app --reload
```

## 룰 엔진 메모 (§1.6)

- **씬 전환** — `chat_count`가 다음 씬의 임계값에 도달하면 발생 (호감도 무관).
- **호감도 이벤트** — `affinity`가 ±30/±50/±70/+100을 **처음 통과**할 때 1회. 같은 임계값은 재발동되지 않음 (`triggered_events` PK).
- **엔딩** — `affinity ≤ -100` 즉시 인터럽트, 또는 `chat_count == chat_limit` 시 호감도 구간으로 6종 결정.
- LLM은 위 결정에 관여하지 않음. `evaluate_affinity` 노드는 단지 ±20 범위의 `delta`와 다음 감정만 반환.

## 변경 이력

- v0.1 (2026-05-07) — API_SPEC v1.3 기반 전면 재작성. 기존 `solar.py`/`gemini.py`/`client.py` 프로토타입 제거.
