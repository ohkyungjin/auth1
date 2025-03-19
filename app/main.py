from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import logging
from dotenv import load_dotenv

from app.api.routes import router as api_router
from app.utils.logging_config import setup_logging

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logger = setup_logging()

app = FastAPI(
    title="한국 주식시장 OHLCV 데이터 수집 API",
    description="한국투자증권 API를 이용한 KOSPI, KOSDAQ 주식 데이터 수집 서비스",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    logger.info("메인 페이지 접속")
    return {"message": "한국 주식시장 OHLCV 데이터 수집 API"}

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 이벤트"""
    logger.info("애플리케이션 시작됨")

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 이벤트"""
    logger.info("애플리케이션 종료됨")

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    logger.info(f"서버 시작: {host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=True) 