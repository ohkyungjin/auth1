import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import os
import sys

# 테스트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.abspath("."))

from app.main import app

client = TestClient(app)

def test_root_endpoint():
    """루트 엔드포인트 테스트"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert "한국 주식시장 OHLCV 데이터 수집 API" in response.json()["message"]

def test_collect_today_endpoint():
    """오늘 데이터 수집 엔드포인트 테스트"""
    response = client.post("/api/collect/today")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_collect_historical_endpoint():
    """과거 데이터 수집 엔드포인트 테스트 - 유효한 날짜"""
    # 30일 전 날짜
    from_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    response = client.post(f"/api/collect/historical?from_date={from_date}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_collect_historical_invalid_date():
    """과거 데이터 수집 엔드포인트 테스트 - 잘못된 날짜 형식"""
    response = client.post("/api/collect/historical?from_date=invalid_date")
    assert response.status_code == 400
    assert "날짜 형식이 잘못되었습니다" in response.json()["detail"]

def test_scheduler_endpoints():
    """스케줄러 엔드포인트 테스트"""
    # 상태 확인
    status_resp = client.get("/api/scheduler/status")
    assert status_resp.status_code == 200
    assert "is_running" in status_resp.json()
    
    # 시작
    start_resp = client.post("/api/scheduler/start")
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] in ["success", "warning"]
    
    # 상태 확인 (시작 후)
    status_after_resp = client.get("/api/scheduler/status")
    assert status_after_resp.status_code == 200
    assert "is_running" in status_after_resp.json()
    
    # 중지
    stop_resp = client.post("/api/scheduler/stop")
    assert stop_resp.status_code == 200
    assert stop_resp.json()["status"] in ["success", "warning"] 