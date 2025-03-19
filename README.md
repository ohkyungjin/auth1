# 한국 주식시장 OHLCV 데이터 수집 API

한국투자증권 API를 이용하여 KOSPI 및 KOSDAQ 주식 시장의 OHLCV(Open, High, Low, Close, Volume) 데이터를 수집하는 FastAPI 기반 서비스입니다.

## 기능

- KOSPI, KOSDAQ 종목 데이터 수집
- 종목 코드 관리 (조회 및 업데이트)
- 당일 데이터 수집 (오후 6시 자동 실행)
- 과거 데이터 수집 (기간 지정)
- 수집 데이터 병합 기능
- 텔레그램 알림 기능
- n8n 워크플로우를 통한 자동화
- 한국투자증권 API 토큰 자동 관리 (24시간 유효 토큰 캐싱)

## 수집 데이터

- 거래일
- 종목명
- 종목코드
- 시장 구분
- 시가 (Open)
- 고가 (High)
- 저가 (Low)
- 종가 (Close)
- 거래량 (Volume)

## 기술 스택

- Python 3.8+
- FastAPI
- Pydantic (데이터 검증)
- Gunicorn (WSGI 서버)
- 한국투자증권 API
- httpx (비동기 HTTP 클라이언트)
- pandas (데이터 처리)
- n8n (워크플로우 자동화)
- 텔레그램 봇

## 설치 방법

1. 저장소 클론
```bash
git clone <repository-url>
cd stock-data-collector
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 의존성 설치
```bash
pip install -r requirements.txt
```

4. 환경 변수 설정
`.env` 파일을 수정하여 필요한 API 키와 설정을 입력합니다:
```
# 한국투자증권 API 설정
KOREA_INV_APPKEY=your_app_key
KOREA_INV_APPSECRET=your_app_secret
KOREA_INV_ACCOUNT=your_account_number

# 텔레그램 봇 설정
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# 데이터 저장 경로
DATA_STORAGE_PATH=./data/stock_data

# API 설정
API_HOST=0.0.0.0
API_PORT=8000

# 종목 코드 설정
MAX_STOCK_ITEMS=1000  # 수집할 최대 종목 수 (0 = 무제한)

# 시간대 설정
TIMEZONE=Asia/Seoul
```

## 실행 방법

### 서버 시작
```bash
python run.py
```

또는 Gunicorn으로 실행 (Linux/Mac):
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

### API 문서
서버 실행 후 다음 URL로 API 문서에 접근할 수 있습니다:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API 엔드포인트

### 데이터 수집 관련
- `GET /`: API 홈
- `POST /api/collect/today`: 오늘의 데이터 수집
- `POST /api/collect/historical?from_date={YYYYMMDD}&to_date={YYYYMMDD}`: 과거 데이터 수집
- `POST /api/merge`: 수집된 데이터 병합

### 종목 코드 관리
- `POST /api/symbols/update`: 종목 코드 목록 업데이트
- `GET /api/symbols/{market}`: 특정 시장(KOSPI/KOSDAQ)의 종목 코드 목록 조회
- `GET /api/symbols`: 모든 종목 코드 목록 조회

### 스케줄러 관련
- `POST /api/scheduler/start`: 스케줄러 시작
- `POST /api/scheduler/stop`: 스케줄러 중지
- `GET /api/scheduler/status`: 스케줄러 상태 조회

## 주요 구현 사항

### 한국투자증권 API 토큰 관리
- 접근 토큰은 24시간 동안 유효하며, 만료 전까지 재사용합니다
- 토큰 만료 5분 전에 자동으로 갱신하여 API 호출 연속성 보장
- 토큰 상태를 로그로 기록하여 디버깅 용이

### 데이터 처리 흐름
1. 종목 코드 목록 업데이트: `/api/symbols/update`
2. 종목별 OHLCV 데이터 수집: `/api/collect/today` 또는 `/api/collect/historical`
3. 수집된 데이터 병합: `/api/merge`
4. 저장된 CSV 파일 활용

## n8n 워크플로우 설정

1. n8n 설치 및 실행
```bash
npm install n8n -g
n8n start
```

2. n8n 웹 인터페이스 접속 (`http://localhost:5678`)
3. `n8n/stock_data_workflow.json` 파일을 가져와 워크플로우 설정
4. 환경 변수 설정 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
5. 워크플로우 활성화

## 라이센스

MIT

## 개발자 정보

- 이메일: your.email@example.com 