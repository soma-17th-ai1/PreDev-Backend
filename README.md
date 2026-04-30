# PreDev-Backend

### FastAPI 기반 미연시 LLM Proxy 서버
- `solar.py`: Upstage Solar 모델(`solar-pro3`) 백엔드 서버
- `gemini.py`: Google Gemini 모델 백엔드 서버
- `client.py`: 콘솔에서 `/generate` API를 호출하는 테스트 클라이언트

서버에는 시스템 프롬프트가 포함되어 있고 stateless로 작동함 (이전 대화 기억 못함)

## 파일 설명

### `solar.py`
- FastAPI 서버를 `127.0.0.1:8000`에서 실행
- POST `/generate`로 사용자 입력을 받아 Solar API 응답 반환
- 필수 환경변수: `SOLAR_API_KEY`

### `gemini.py`
- FastAPI 서버를 `127.0.0.1:8000`에서 실행
- POST `/generate`로 사용자 입력을 받아 Gemini 응답 반환
- `google-genai` 클라이언트 사용
- 필수 환경변수: `GEMINI_API_KEY`

### `client.py`
- 기본 URL: `http://127.0.0.1:8000`
- 콘솔 입력을 받아 `/generate`에 요청 전송
- `exit` 또는 `quit` 입력 시 종료

## 실행 방법

1. 가상환경 활성화

```powershell
.\.venv\Scripts\Activate.ps1
```

2. 의존성 설치 (필요 시)

```powershell
pip install fastapi uvicorn python-dotenv requests openai google-genai
```

3. 서버 실행 (둘 중 하나 선택)

```powershell
python solar.py
```

또는

```powershell
python gemini.py
```

4. 클라이언트 실행

```powershell
python client.py
```

## `.env` 설정

프로젝트 루트에 `.env` 파일을 만들고 API 키를 넣어야 합니다.

```env
# Solar 서버 실행 시 필요
SOLAR_API_KEY=your_solar_api_key

# Gemini 서버 실행 시 필요
GEMINI_API_KEY=your_gemini_api_key
```
