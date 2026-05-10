# 커널을 좋아하는 옆자리의 그녀 — API 명세서

FE(Monogatari SPA) ↔ BE(FastAPI) 통신 규격 v1.3

> **v1.3 변경점**
>
> *Monogatari Full SPA 구조 반영 — 리소스·상태 관리 책임을 FE로 이전, 불필요한 API·필드 제거*
>
> **ENUM 변경**
> - `Costume` ENUM 제거 (복장 기능 제거)
> - `BackgroundId`, `BgmId`, `SfxId` ENUM 제거 (FE가 Monogatari 내에서 자체 관리)
> - `TransitionType` ENUM 제거 (씬 전환 연출을 FE가 자체 결정)
> - `CgId` ENUM → `EventId` ENUM으로 대체 (`EVENT_LIKE_P*` / `EVENT_DISLIKE_M*` 형식)
> - `EndingId` 확장: 4종 → 6종 (`INSTANT_BAD`, `BAD`, `NORMAL_NO_CONTACT`, `NORMAL_CONTACT`, `HAPPY`, `MARRIAGE`)
> - `SceneId` 전면 교체: 소마 실제 일정 기반 씬으로 재정의 (빌드업 2 + 소마일정 6 + 엔딩 6)
> - `EventId`에서 `EVENT_DISLIKE_M100` 제거 (affinity ≤ -100은 이벤트 없이 즉시 베드엔딩 인터럽트)
>
> **API 제거**
> - `GET /api/v1/game/state` 제거 (`GET /api/v1/sessions/me/resume`으로 대체)
> - `GET /api/v1/events/{event_id}` 제거 (이벤트 상세는 FE Monogatari 씬에 내장)
>
> **응답 필드 정리**
> - `GameState.session_id` 제거 (쿠키 인증 방식에서 FE 미사용)
> - `GameState.ending_id` 제거 (`current_scene_id`가 `SCENE_ENDING_*`이면 파생 가능)
> - `POST /api/v1/sessions/me/start` 응답의 `first_scene_id` 제거 (`state.current_scene_id`와 중복)
> - SSE `meta` 이벤트의 `progress` 제거 (`state` 이벤트에만 유지)
> - SSE `scene_transition`의 `transition_type` 제거 (FE 자체 결정)
> - 씬 응답(`GET /api/v1/scenes/current`)에서 `background_id`, `bgm_id`, `ambient_sfx_ids`, `costume` 제거
> - 이벤트 응답에서 `bgm_id` 제거
> - 엔딩 응답에서 `bgm_id` 제거
>
> **이벤트 구조 변경**
> - 호감도 이벤트가 씬 전환 없이 `event_id`만으로 처리: FE가 `event_id`로 Monogatari 이벤트 씬을 직접 재생 후 이전 씬 복귀. BE `current_scene_id` 불변.
>
> **씬 설계 변경**
> - `LAUNCH_CEREMONY` 씬 내 대화 수 감소: 10회 → 5회 (진입 임계값 하위 씬 일부 조정)
> - §1.6.1 표에 씬 내 대화 수 컬럼 추가
>
> **v1.2 변경점**
> - **트리거 로직 명시화** (§1.6 신설): 씬 전환 / 이벤트 / 엔딩이 각각 어떤 조건으로 발생하는지 분리하여 정의.
> - `progress` vs `chat_count` 의미 구분 명확화.
>
> **v1.1 변경점**
> - 모든 리소스 URL을 ENUM(`*_id`)으로 변경. FE가 ENUM ↔ 경로 매핑 테이블 보유.
> - 문서 최상단에 전체 엔드포인트 요약표 추가.

---

## 0. API 엔드포인트 한눈에 보기

| # | Method | Path | 용도 | 응답 형태 |
|---|---|---|---|---|
| **세션 / 메인 메뉴** ||||
| 2.1 | `GET`  | `/api/v1/sessions/me` | 세션 존재/시작 여부 확인 (메인 화면 진입) | JSON |
| 2.2 | `POST` | `/api/v1/sessions` | 새 게임 시작 (세션 생성/초기화) | JSON |
| 2.3 | `POST` | `/api/v1/sessions/me/start` | 플레이어 이름 입력 → 인트로 진입 | JSON |
| 2.4 | `GET`  | `/api/v1/sessions/me/resume` | 이어 하기 (씬 + 직전 메시지 복원) | JSON |
| **게임 진행 / 채팅** ||||
| 3.2 | `POST` | `/api/v1/chat` | 채팅 전송 (메인 루프) | **SSE** |
| 3.3 | `GET`  | `/api/v1/chat/suggestions` | 예시 답안 조회 | JSON |
| 3.5 | `GET`  | `/api/v1/chat/history` | 대화 로그 조회 (페이지네이션) | JSON |
| **씬 / 리소스** ||||
| 4.1 | `GET`  | `/api/v1/scenes/current` | 현재 씬 메타 (씬ID, intro_dialogues) | JSON |
| **엔딩** ||||
| 5.1 | `GET`  | `/api/v1/game/ending` | 엔딩 콘텐츠 조회 | JSON |
| **운영** ||||
| 6.1 | `GET`  | `/api/v1/health` | Health Check | JSON |

> 인증: 모든 엔드포인트는 `session_id` 쿠키로 인증 (HttpOnly, Secure, SameSite=Lax). `/health` 제외.

---

## 1. 개요

### 1.1 Base URL

```
https://api.<domain>/api/v1
```

### 1.2 인증

- **Cookie 기반 세션 인증**: 최초 접속 시 `session_id` 쿠키 발급
- 모든 API 요청은 자동으로 쿠키를 포함하여 사용자 식별
- 유저 1명당 1개의 세션(=1개의 저장 슬롯)만 유지

### 1.3 공통 응답 포맷

성공:
```json
{ "ok": true, "data": { ... } }
```

실패:
```json
{ "ok": false, "error": { "code": "SESSION_NOT_FOUND", "message": "..." } }
```

### 1.4 ENUM 정의 (FE-BE 공유)

> **원칙**: BE는 리소스 경로(URL)를 절대 응답에 포함하지 않는다. ENUM 키만 전달하고, FE가 자체 매핑 테이블로 실제 에셋 경로를 결정한다.

#### 1.4.1 `Emotion` — 캐릭터 감정
```
NEUTRAL    // 평온
HAPPY      // 행복
EXCITED    // 흥분
SHY        // 수줍음
SAD        // 슬픔
ANGRY      // 화남
DISGUSTED  // 혐오
FURIOUS    // 대노
```

#### 1.4.2 `SceneId` — 씬 식별자
```
// 1. 빌드업
SCENE_INTRO                       // 인트로 (이름 입력 직후 ~ S룸 첫 만남 전)
SCENE_FIRST_MEET                  // S룸에서 첫 대화

// 2. 소마 일정 (시간의 흐름)
SCENE_PROJECT_PLAN_EVALUATION     // 팀빌딩 이후 기획 심의
SCENE_LAUNCH_CEREMONY             // 발대식
SCENE_MID_EVALUATION              // 중간평가
SCENE_DEEP_DEV                    // 만나서 새벽 개발
SCENE_FINAL_EVALUATION            // 최종평가
SCENE_GRADUATION_BUSAN            // 수료식 부산 (5턴, 엔딩 직전)

// 3. 엔딩 씬
SCENE_ENDING_INSTANT_BAD          // 즉시 베드엔딩 (호감도 -100, 소마 중퇴 통보)
SCENE_ENDING_BAD                  // 일반 배드엔딩
SCENE_ENDING_NORMAL_NO_CONTACT    // 노멀엔딩 1 (연락 끊김)
SCENE_ENDING_NORMAL_CONTACT       // 노멀엔딩 2 (가끔 연락)
SCENE_ENDING_HAPPY                // 해피엔딩 (썸 타는 관계)
SCENE_ENDING_MARRIAGE             // 결혼 해피엔딩
```

#### 1.4.3 `EventId` — 호감도 이벤트 식별자
```
// 양수 이벤트
EVENT_LIKE_P30     // 호감도 +30: 마음이 열림 (1대1로 밥먹음)
EVENT_LIKE_P50     // 호감도 +50: 친밀해짐 (1대1로 술마심)
EVENT_LIKE_P70     // 호감도 +70: 호감 표현 (깜짝 선물)
EVENT_LIKE_P100    // 호감도 +100: 고백 (한강 야경 데이트)

// 음수 이벤트
EVENT_DISLIKE_M30  // 호감도 -30: 거리감 (대화가 줄어듦)
EVENT_DISLIKE_M50  // 호감도 -50: 차가워짐 (협업 거부)
EVENT_DISLIKE_M70  // 호감도 -70: 노골적 회피 (S룸 자리 이동)
// affinity ≤ -100 은 이벤트 없이 즉시 베드엔딩 인터럽트 (§1.6.2 참조)
```

#### 1.4.4 `EndingId` — 엔딩
```
ENDING_INSTANT_BAD          // 즉시 베드엔딩 (호감도 -100 인터럽트)
ENDING_BAD                  // 일반 배드엔딩 (채팅 한도 소진 + 호감도 ≤ -30)
ENDING_NORMAL_NO_CONTACT    // 노멀엔딩 1     (채팅 한도 소진 + -29 ≤ 호감도 ≤ 0)
ENDING_NORMAL_CONTACT       // 노멀엔딩 2     (채팅 한도 소진 + 1 ≤ 호감도 ≤ 29)
ENDING_HAPPY                // 해피엔딩       (채팅 한도 소진 + 30 ≤ 호감도 ≤ 99)
ENDING_MARRIAGE             // 결혼 해피엔딩  (채팅 한도 소진 + 호감도 ≥ 100)
```

#### 1.4.5 `MessageRole` — 대화 로그 역할
```
USER
ASSISTANT
NARRATION
SYSTEM_EVENT
```

### 1.5 공통 데이터 모델

#### `GameState`
| 필드 | 타입 | 설명 | 트리거 역할 |
|---|---|---|---|
| `player_name` | string | 플레이어 이름 (최대 20자) | — |
| `affinity` | int | 호감도 (시작값 0). 매 채팅마다 변동. | **이벤트 발동** & **베드엔딩 인터럽트** & **엔딩 종류 결정** |
| `chat_count` | int | 누적 사용자 채팅 수. 매 채팅마다 +1 (단조 증가). | **스토리 씬 전환** & **정상 엔딩 진입** |
| `chat_limit` | int | 엔딩 도달까지 최대 채팅 수 (예: 50). 게임 시작 시 고정. | 엔딩 트리거 임계값 |
| `progress` | int | `chat_count / chat_limit * 100` (0~100). UI 진행도 바 표시 전용 (파생 값). | UI 표시용 (트리거 아님) |
| `current_scene_id` | `SceneId` | 현재 씬 | — |
| `emotion` | `Emotion` | 현재 캐릭터 감정 | — |
| `is_ended` | bool | 엔딩 도달 여부 (`current_scene_id`가 `SCENE_ENDING_*`이면 true) | — |

> 핵심 구분: **`chat_count`는 스토리를 진행시키고**, **`affinity`는 관계를 변화시킨다**. `progress`는 단순히 `chat_count`의 백분율 표현일 뿐 트리거에 사용되지 않는다.

---

### 1.6 트리거 로직 (State Machine)

> 게임 내에서 발생하는 모든 자동 전환은 **BE의 룰 엔진**이 결정한다. LLM은 트리거를 결정하지 않으며, 단지 현재 씬·상태에 맞는 대사만 생성한다.

#### 1.6.1 스토리 씬 전환 — `chat_count` 기반 (결정론적)

각 씬은 진입 `chat_count` 임계값을 가진다. 사용자 채팅이 누적되어 다음 씬의 임계값에 도달하면 자동 전환되며, 호감도는 영향을 주지 않는다.

| 씬 | 진입 `chat_count` | 씬 내 대화 수 | 비고 |
|---|---|---|---|
| `SCENE_INTRO` | 0 | — | LLM 미사용, 자동 인트로 |
| `SCENE_FIRST_MEET` | 1 | 4회 | S룸 첫 대화 |
| `SCENE_PROJECT_PLAN_EVALUATION` | 5 | 7회 | |
| `SCENE_LAUNCH_CEREMONY` | 12 | 5회 | |
| `SCENE_MID_EVALUATION` | 17 | 11회 | |
| `SCENE_DEEP_DEV` | 28 | 9회 | |
| `SCENE_FINAL_EVALUATION` | 37 | 8회 | |
| `SCENE_GRADUATION_BUSAN` | 45 | 5회 | 엔딩 직전 |
| `SCENE_ENDING_*` | 50 또는 `affinity ≤ -100` | — | 엔딩 진입 (§1.6.3 참조) |

> 위 수치는 **밸런싱 기본값**이며 BE 설정 파일로 관리. 필요 시 게임 진행 중 변경 가능 (단, 진행 중 세션에는 영향 없음).

#### 1.6.2 호감도 이벤트 발동 — `affinity` 임계값 기반 (반응적, 1회성)

호감도가 특정 임계값을 **처음 통과(crossing)** 할 때 1회만 발동.

| 임계값 통과 | 발동 이벤트 |
|---|---|
| `affinity ≥ +30` | `EVENT_LIKE_P30` |
| `affinity ≥ +50` | `EVENT_LIKE_P50` |
| `affinity ≥ +70` | `EVENT_LIKE_P70` |
| `affinity ≥ +100` | `EVENT_LIKE_P100` |
| `affinity ≤ -30` | `EVENT_DISLIKE_M30` |
| `affinity ≤ -50` | `EVENT_DISLIKE_M50` |
| `affinity ≤ -70` | `EVENT_DISLIKE_M70` |
| `affinity ≤ -100` | 이벤트 없이 **즉시 베드엔딩 인터럽트** |

규칙:
- 한 번 발동된 임계값은 호감도가 다시 등락해도 **재발동되지 않음** (BE에서 발동 이력 저장).
- 이벤트는 씬과 독립적이다 — 어느 씬에서든 임계값 통과 시 발동.
- FE는 `event_id`로 해당 Monogatari 이벤트 씬을 직접 재생하고, 완료 후 이전 스토리 씬으로 복귀한다. BE의 `current_scene_id`는 이벤트 동안 변경되지 않는다.

#### 1.6.3 엔딩 진입 — 두 가지 조건

| 조건 | 결과 |
|---|---|
| `affinity ≤ -100` | **인터럽트**: 즉시 `SCENE_ENDING_INSTANT_BAD` + `ENDING_INSTANT_BAD` |
| `chat_count == chat_limit` | **정상 종료**: 호감도 기반 `SCENE_ENDING_*` + `ENDING_*` 결정 (§5.1 표 참조) |

정상 종료 시 `ending_id` 결정 로직은 §5.1 표 참조.

#### 1.6.4 한 채팅 내 평가 우선순위

한 번의 `POST /api/v1/chat` 응답 안에서 여러 트리거가 동시에 성립할 수 있다. 평가 순서는 다음과 같다:

```
1. 채팅 처리 완료 (LLM 응답 + affinity, chat_count 갱신)
2. affinity ≤ -100  → 베드엔딩 인터럽트 (이하 단계 모두 스킵)
3. 호감도 이벤트 임계값 통과 검사  → event_trigger 발행
4. chat_count == chat_limit  → 정상 엔딩 진입
5. (4가 아니면) chat_count가 다음 씬 임계값 도달  → scene_transition 발행
```

> **이벤트 + 씬 전환 동시 발생**: SSE에서 `event_trigger`를 먼저 발행한 뒤 `scene_transition`을 발행. FE는 Monogatari 이벤트를 먼저 재생한 후 씬 전환을 수행한다.

#### 1.6.5 LLM은 무엇을 결정하지 않는가

명확히 하자면, LLM은 다음을 결정하지 **않는다**:
- 씬 전환 시점
- 이벤트 발동 여부
- 엔딩 진입 여부
- `affinity` 변동량 (BE의 별도 평가 로직이 결정)
- `current_scene_id` 등 게임 상태

LLM이 결정하는 것은 오직: **현재 상태(씬·호감도·감정·맥락)를 입력받아 캐릭터의 다음 대사를 생성**하는 것뿐이다.

---

## 2. 세션 / 메인 메뉴 API

### 2.1 세션 상태 확인

메인 화면 진입 시 호출. 이어하기 버튼 활성화 여부를 결정.

```
GET /api/v1/sessions/me
```

**Response 200**
```json
{
  "ok": true,
  "data": {
    "has_session": true,
    "is_started": true,
    "current_scene_id": "SCENE_MID_EVALUATION",
    "progress": 35,
    "is_ended": false
  }
}
```

세션이 없으면 `has_session: false`만 반환.

---

### 2.2 새 게임 시작

"새로 하기" 버튼 클릭 시 호출. 기존 세션 있으면 초기화 후 새로 생성.

```
POST /api/v1/sessions
```

**Request Body**
```json
{ "force_reset": false }
```

- `force_reset`: 기존 세션이 있을 때 강제 초기화 여부. `false`인데 세션이 존재하면 409 반환 → FE에서 확인 모달 표시 후 `true`로 재요청.

**Response 200**
```json
{
  "ok": true,
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2025-05-05T10:00:00Z"
  }
}
```

**Response 409** — 기존 세션 존재
```json
{
  "ok": false,
  "error": {
    "code": "SESSION_ALREADY_EXISTS",
    "message": "이전 기록이 있습니다. 초기화하시겠습니까?"
  }
}
```

---

### 2.3 플레이어 이름 입력 → 게임 시작

이름 입력창에서 이름 제출 시 호출. 인트로 씬 진입.

```
POST /api/v1/sessions/me/start
```

**Request Body**
```json
{ "player_name": "민성" }
```

**Response 200**
```json
{
  "ok": true,
  "data": {
    "state": { /* GameState */ }
  }
}
```

---

### 2.4 이어 하기

"이어 하기" 버튼 클릭 시 호출. 현재 씬 상태와 직전 대화 N개를 함께 반환.

```
GET /api/v1/sessions/me/resume
```

**Response 200**
```json
{
  "ok": true,
  "data": {
    "state": { /* GameState */ },
    "scene": { /* SceneInfo - §4.1 참조 */ },
    "recent_messages": [
      {
        "role": "USER",
        "content": "역시 github보단 gitlab이지",
        "timestamp": "2025-05-05T10:15:00Z"
      },
      {
        "role": "ASSISTANT",
        "content": "캬 역시 너도 이해하는구나...",
        "emotion": "HAPPY",
        "timestamp": "2025-05-05T10:15:03Z"
      }
    ]
  }
}
```

**Response 404**
```json
{
  "ok": false,
  "error": { "code": "SESSION_NOT_FOUND", "message": "이전 기록이 없습니다." }
}
```

---

## 3. 게임 진행 / 채팅 API

### 3.2 채팅 전송 (SSE 스트리밍)

핵심 API. 사용자 입력을 보내고 SSE로 실시간 응답을 수신.

```
POST /api/v1/chat
Accept: text/event-stream
```

**Request Body**
```json
{ "message": "역시 github보단 gitlab이지" }
```

**제약**
- `message`: 1자 이상 300자 이하
- 빈 문자열, 공백만 있는 입력은 400 반환

**Response: SSE Stream**

응답은 `text/event-stream`으로, 다음과 같은 순서의 이벤트로 구성됨.

#### Event 1: `meta` — 메타데이터 (스트림 시작 직후)
```
event: meta
data: {
  "scene_id": "SCENE_MID_EVALUATION",
  "emotion": "HAPPY"
}
```

> FE는 이 시점에 화면(배경/스프라이트/감정)을 미리 준비. 본문 텍스트는 아직 출력하지 않음.

#### Event 2..N: `delta` — 응답 텍스트 청크
```
event: delta
data: {"text":"캬 역시 너도 "}

event: delta
data: {"text":"이해하는구나. "}
```

> FE는 청크를 누적하여 대화창에 점진적으로 출력. 3문장 이상이면 2줄(문장 단위)씩 끊어서 출력.

#### Event N+1: `state` — 채팅 결과 반영된 상태
```
event: state
data: {
  "affinity": 20,
  "affinity_delta": 20,
  "progress": 36,
  "chat_count": 11,
  "emotion": "HAPPY"
}
```

#### Event N+2: `event_trigger` — 이벤트 발동 (조건부)

**발동 조건**: 호감도가 임계값(`±30, ±50, ±70, +100`)을 처음 통과할 때 1회. 상세는 §1.6.2 참조.

```
event: event_trigger
data: {
  "event_id": "EVENT_LIKE_P30",
  "blocking": true
}
```

- `blocking: true`: FE는 `event_id`로 Monogatari 이벤트 씬을 재생한 후 다음 입력을 받아야 함.

#### Event N+3: `scene_transition` — 씬 전환 (조건부)

**발동 조건**: `chat_count`가 다음 씬의 진입 임계값에 도달했을 때, 또는 엔딩 진입 시. 상세는 §1.6.1 / §1.6.3 참조.

```
event: scene_transition
data: {
  "next_scene_id": "SCENE_DEEP_DEV"
}
```

> FE는 `next_scene_id`를 수신 후 §4.1을 호출하여 새 씬 메타를 로드. 전환 연출(로딩창 등)은 FE가 씬 종류에 따라 자체 결정.

#### Event 마지막: `end` — 스트림 종료
```
event: end
data: {"finish_reason":"complete"}
```

#### Event: `error` — 에러 발생
```
event: error
data: {"code":"LLM_ERROR","message":"응답 생성에 실패했습니다."}
```

> 인젝션 시도 등으로 인한 호감도 최대 감소가 발생한 경우는 `error`가 아닌 정상 흐름. `affinity_delta`만 큰 음수일 뿐. `error`는 서버 내부 오류 시에만 사용.

---

### 3.3 예시 답안 조회

채팅 입력창 위에 표시할 예시 답안. 현재 호감도 컨텍스트 기반으로 호감도를 **올리는 방향**으로만 생성 (인젝션 방어).

```
GET /api/v1/chat/suggestions
```

**Response 200**
```json
{
  "ok": true,
  "data": {
    "suggestions": [
      "Arch 후드 멋있다, 직접 빌드하셨어요?",
      "혹시 커널 디버깅 어떻게 하세요?",
      "GitLab CI 파이프라인 같이 짜볼래요?"
    ]
  }
}
```

- 보통 2~3개 반환
- 매 채팅 후 호감도 변화를 반영하여 갱신

---

### 3.5 대화 로그 조회

"로그" 버튼 / "뒤로가기" 시 사용. 페이지네이션 지원.

```
GET /api/v1/chat/history?limit=50&before=<message_id>
```

**Query Params**
- `limit`: 1 ~ 100 (기본 50)
- `before`: 특정 메시지 ID 이전을 조회 (커서 페이지네이션)

**Response 200**
```json
{
  "ok": true,
  "data": {
    "messages": [
      {
        "message_id": "msg_001",
        "role": "NARRATION",
        "content": "[4월 13일 월요일, 화창한 아침]",
        "timestamp": "2025-05-05T10:00:00Z"
      },
      {
        "message_id": "msg_002",
        "role": "USER",
        "content": "안녕 세라야",
        "timestamp": "2025-05-05T10:01:00Z"
      },
      {
        "message_id": "msg_003",
        "role": "ASSISTANT",
        "content": "응! 안녕, 나는 세라야",
        "emotion": "NEUTRAL",
        "scene_id": "SCENE_FIRST_MEET",
        "timestamp": "2025-05-05T10:01:03Z"
      }
    ],
    "next_cursor": "msg_001"
  }
}
```

---

## 4. 씬 API

### 4.1 현재 씬 정보 조회

씬 전환 시 호출 (FE는 `scene_transition` 이벤트 수신 후 이 API로 새 씬의 메타데이터를 로드).

```
GET /api/v1/scenes/current
```

**Response 200**
```json
{
  "ok": true,
  "data": {
    "scene_id": "SCENE_DEEP_DEV",
    "title": "새벽 개발",
    "intro_dialogues": [
      { "type": "narration", "text": "워크숍 둘째 날이 밝았다." },
      {
        "type": "character",
        "name": "이세라",
        "emotion": "NEUTRAL",
        "text": "어, 일찍 오셨네요?"
      }
    ]
  }
}
```

- `intro_dialogues`: 씬 진입 시 자동 재생되는 나레이션/대사 (사용자 입력 전)

> **스프라이트 처리**: FE는 `state.emotion`으로 자체 매핑 테이블에서 스프라이트를 결정. 별도 메타 API 불필요.

---

## 5. 엔딩 API

### 5.1 엔딩 콘텐츠 조회

채팅 한도 소진 또는 호감도 -100 도달 시 SSE의 `scene_transition` 이벤트가 `next_scene_id: SCENE_ENDING_*`을 반환. FE는 이 API로 엔딩 콘텐츠를 조회.

```
GET /api/v1/game/ending
```

**Response 200**
```json
{
  "ok": true,
  "data": {
    "ending_id": "ENDING_HAPPY",
    "title": "해피엔딩",
    "narrative": "LLM이 생성한 엔딩 서사 텍스트... (호감도 75로 도달한 행복한 엔딩)",
    "final_affinity": 75,
    "stats": {
      "total_chats": 50,
      "max_affinity": 80,
      "min_affinity": -10,
      "events_triggered": [
        "EVENT_LIKE_P30",
        "EVENT_LIKE_P50",
        "EVENT_LIKE_P70"
      ]
    }
  }
}
```

> **엔딩 이미지**: `ending_id` ENUM에서 FE가 자체 매핑으로 결정 (별도 image_id 불필요).

**`ending_id` 결정 로직**

| 값 | 조건 |
|---|---|
| `ENDING_INSTANT_BAD` | 호감도 ≤ -100 도달 (인터럽트) |
| `ENDING_BAD` | 채팅 한도 소진 + 호감도 ≤ -30 |
| `ENDING_NORMAL_NO_CONTACT` | 채팅 한도 소진 + -29 ≤ 호감도 ≤ 0 |
| `ENDING_NORMAL_CONTACT` | 채팅 한도 소진 + 1 ≤ 호감도 ≤ 29 |
| `ENDING_HAPPY` | 채팅 한도 소진 + 30 ≤ 호감도 ≤ 99 |
| `ENDING_MARRIAGE` | 채팅 한도 소진 + 호감도 ≥ 100 |

**Response 425** — 아직 엔딩 도달 전
```json
{
  "ok": false,
  "error": { "code": "GAME_NOT_ENDED", "message": "아직 게임이 진행 중입니다." }
}
```

---

## 6. 헬스체크

### 6.1 Health Check
```
GET /api/v1/health
```

**Response 200**
```json
{
  "ok": true,
  "data": { "status": "healthy", "llm_provider": "ok", "db": "ok" }
}
```

---

## 7. 에러 코드 모음

| HTTP | code | 설명 |
|---|---|---|
| 400 | `INVALID_INPUT` | 메시지 길이 초과/빈 입력 등 |
| 401 | `SESSION_REQUIRED` | 쿠키 없음 / 세션 미생성 |
| 404 | `SESSION_NOT_FOUND` | 이어하기 시 세션 없음 |
| 404 | `SCENE_NOT_FOUND` | 잘못된 씬 ID |
| 409 | `SESSION_ALREADY_EXISTS` | 새 게임 시도 시 기존 세션 존재 |
| 409 | `GAME_ALREADY_ENDED` | 엔딩 후 채팅 시도 |
| 425 | `GAME_NOT_ENDED` | 엔딩 미도달 상태에서 엔딩 조회 |
| 429 | `RATE_LIMITED` | 너무 빠른 채팅 연사 |
| 500 | `LLM_ERROR` | LLM API 호출 실패 |
| 503 | `SERVICE_UNAVAILABLE` | 서버 다운/점검 |

---

## 8. 전형적인 호출 시퀀스

### 8.1 신규 유저 — 새 게임

```
1. GET  /api/v1/sessions/me            → has_session: false
2. POST /api/v1/sessions                → session_id 발급, 쿠키 저장
3. (FE) 인트로 영상 재생 + 이름 입력 모달
4. POST /api/v1/sessions/me/start       → state
5. GET  /api/v1/scenes/current          → 씬 메타 (scene_id, intro_dialogues, ...)
6. (FE) 인트로 대사 자동 재생 → 사용자 입력 대기
7. GET  /api/v1/chat/suggestions        → 예시 답안 표시
8. POST /api/v1/chat (SSE)              → 채팅 시작
   → meta → delta×N → state → end
9. GET  /api/v1/chat/suggestions        → 다음 예시 답안 갱신
10. (반복 8~9)
```

### 8.2 씬 전환

```
8. POST /api/v1/chat (SSE)
   → meta → delta×N → state → scene_transition(next_scene_id="SCENE_DEEP_DEV") → end
9. (FE) 씬 전환 연출 후 GET /api/v1/scenes/current → 새 씬 메타
10. (FE) 새 씬 진입 + 자동 대사 재생 → 사용자 입력 대기
```

### 8.3 이벤트 발생

```
8. POST /api/v1/chat (SSE)
   → meta → delta×N → state(affinity=30) → event_trigger(event_id="EVENT_LIKE_P30", blocking=true) → end
9. (FE) event_id로 Monogatari 이벤트 씬 직접 재생 → 완료 후 이전 씬 복귀 → 사용자 입력 대기
```

### 8.4 엔딩

```
8. POST /api/v1/chat (SSE)
   → meta → delta×N → state(chat_count=50) → scene_transition(next_scene_id="SCENE_ENDING_HAPPY") → end
9. GET /api/v1/game/ending              → ending_id, narrative
10. (FE) ending_id 매핑 → 엔딩 이미지 + 서사 출력
```

### 8.5 베드 엔딩 인터럽트

```
8. POST /api/v1/chat (SSE)
   → meta → delta×N → state(affinity=-100) → scene_transition("SCENE_ENDING_INSTANT_BAD") → end
9. GET /api/v1/game/ending              → ending_id: "ENDING_INSTANT_BAD"
```

---

## 9. 구현 노트

### 9.1 BE
- **상태 변경 단일 책임**: 호감도/진행도/씬 변경은 `POST /api/v1/chat` 에서만 발생. 다른 GET API는 read-only.
- **컨텍스트 주입 시점**: 씬 진입 시 BE는 LangGraph에 `(이전 씬 요약 + 새 씬 배경지식)`을 새 그래프 상태로 초기화.
- **호감도 변동 한도**: 한 채팅당 ±20 (인젝션/문맥 이탈 시 -50, 최대 -100까지).
- **인젝션 탐지**: 별도 LangGraph 노드(가드레일)에서 처리 후 호감도 패널티 결정 → 그 다음 응답 생성 노드.
- **스트림 백프레셔**: SSE 청크는 토큰 단위가 아닌 의미 단위(2~10토큰)로 묶어 전송 권장.
- **세션 만료**: 마지막 활동 후 24시간 무활동 시 만료. 단, DB의 대화 기록은 보존(이어하기용).

### 9.2 FE
- **ENUM ↔ 경로 매핑 테이블**: BE는 ENUM만 보내므로, FE는 다음 매핑들을 자체 보유:
  - `EventId` → Monogatari 이벤트 씬 레이블 (FE 내부 매핑)
  - `EndingId` → `/static/ending/*.png`
  - `Emotion` → `/static/char/serah/*.png` (스프라이트)
  - `Emotion` → `/static/char/serah/live2d/*.json` (Live2D 모델)
- **에셋 추가 시**: ENUM 추가는 FE/BE 동시 배포 필요. 따라서 ENUM은 별도 공유 스키마(JSON Schema 또는 OpenAPI components)로 관리 권장.

---

## 10. 변경 이력

| 버전 | 일자 | 내용 |
|---|---|---|
| v1.0 | 2025-05-05 | 초안 작성 |
| v1.1 | 2025-05-05 | 모든 리소스 URL을 ENUM으로 치환, 엔드포인트 요약표 추가 |
| v1.2 | 2025-05-05 | 트리거 로직 섹션(§1.6) 신설 — 씬 전환은 `chat_count`, 이벤트는 `affinity`, 엔딩은 두 조건 분리 |
| v1.3 | 2026-05-06 | Monogatari Full SPA 반영 — 리소스 ENUM 제거, 이벤트·씬·엔딩 구조 전면 재설계, 불필요 API·필드 정리 |
