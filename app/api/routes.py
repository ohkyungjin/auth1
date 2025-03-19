from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

from app.services.data_collector import DataCollector
from app.services.scheduler import StockDataScheduler
from app.utils.stock_symbols import update_stock_symbols, get_stock_symbols, get_all_stock_symbols

logger = logging.getLogger(__name__)

router = APIRouter()
scheduler = StockDataScheduler()

async def get_data_collector():
    return DataCollector()

@router.post("/collect/today", response_model=Dict[str, Any])
async def collect_today_data(
    background_tasks: BackgroundTasks,
    collector: DataCollector = Depends(get_data_collector)
):
    """오늘의 주식 데이터 수집"""
    try:
        background_tasks.add_task(collector.collect_today_data)
        return {"status": "success", "message": "오늘의 주식 데이터 수집 작업이 시작되었습니다."}
    except Exception as e:
        logger.error(f"데이터 수집 API 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"데이터 수집 중 오류가 발생했습니다: {str(e)}")

@router.post("/collect/historical", response_model=Dict[str, Any])
async def collect_historical_data(
    from_date: str,
    to_date: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    collector: DataCollector = Depends(get_data_collector)
):
    """과거 주식 데이터 수집"""
    try:
        # 날짜 형식 검증 (YYYYMMDD)
        datetime.strptime(from_date, "%Y%m%d")
        if to_date:
            datetime.strptime(to_date, "%Y%m%d")
            
        if background_tasks:
            background_tasks.add_task(collector.collect_historical_data, from_date, to_date)
            return {
                "status": "success", 
                "message": f"과거 주식 데이터 수집 작업이 시작되었습니다. (기간: {from_date} ~ {to_date or '현재'})"
            }
        else:
            results = await collector.collect_historical_data(from_date, to_date)
            return {
                "status": "success", 
                "message": "과거 주식 데이터 수집이 완료되었습니다.",
                "results": results
            }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"날짜 형식이 잘못되었습니다. YYYYMMDD 형식을 사용하세요.")
    except Exception as e:
        logger.error(f"데이터 수집 API 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"데이터 수집 중 오류가 발생했습니다: {str(e)}")

@router.post("/merge", response_model=Dict[str, Any])
async def merge_data(
    pattern: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    collector: DataCollector = Depends(get_data_collector)
):
    """수집된 데이터 병합"""
    try:
        if background_tasks:
            background_tasks.add_task(collector.merge_collected_data, pattern)
            return {
                "status": "success", 
                "message": "데이터 병합 작업이 시작되었습니다."
            }
        else:
            result = await collector.merge_collected_data(pattern)
            return {
                "status": "success" if result else "warning", 
                "message": "데이터 병합이 완료되었습니다." if result else "병합할 데이터가 없습니다.",
                "file_path": str(result) if result else None
            }
    except Exception as e:
        logger.error(f"데이터 병합 API 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"데이터 병합 중 오류가 발생했습니다: {str(e)}")

# 스케줄러 API 추가
@router.post("/scheduler/start", response_model=Dict[str, Any])
async def start_scheduler():
    """스케줄러 시작"""
    try:
        result = scheduler.start()
        if result:
            next_run = scheduler.get_next_run_time()
            return {
                "status": "success",
                "message": "스케줄러가 시작되었습니다.",
                "next_run": next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else None
            }
        else:
            return {
                "status": "warning",
                "message": "스케줄러가 이미 실행 중입니다."
            }
    except Exception as e:
        logger.error(f"스케줄러 시작 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"스케줄러 시작 중 오류가 발생했습니다: {str(e)}")

@router.post("/scheduler/stop", response_model=Dict[str, Any])
async def stop_scheduler():
    """스케줄러 중지"""
    try:
        result = scheduler.stop()
        if result:
            return {
                "status": "success",
                "message": "스케줄러가 중지되었습니다."
            }
        else:
            return {
                "status": "warning",
                "message": "스케줄러가 실행 중이 아닙니다."
            }
    except Exception as e:
        logger.error(f"스케줄러 중지 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"스케줄러 중지 중 오류가 발생했습니다: {str(e)}")

@router.get("/scheduler/status", response_model=Dict[str, Any])
async def get_scheduler_status():
    """스케줄러 상태 확인"""
    try:
        is_running = scheduler.is_running
        next_run = scheduler.get_next_run_time() if is_running else None
        
        return {
            "status": "success",
            "is_running": is_running,
            "next_run": next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else None
        }
    except Exception as e:
        logger.error(f"스케줄러 상태 확인 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"스케줄러 상태 확인 중 오류가 발생했습니다: {str(e)}")

# 종목 코드 API 추가
@router.post("/symbols/update", response_model=Dict[str, Any])
async def update_symbols():
    """종목 코드 목록 업데이트"""
    try:
        results = update_stock_symbols()
        return {
            "status": "success",
            "message": "종목 코드 목록이 업데이트되었습니다.",
            "results": results
        }
    except Exception as e:
        logger.error(f"종목 코드 업데이트 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"종목 코드 업데이트 중 오류가 발생했습니다: {str(e)}")

@router.get("/symbols/{market}", response_model=Dict[str, Any])
async def get_symbols(market: str):
    """특정 시장의 종목 코드 목록 조회"""
    try:
        if market.upper() not in ["KOSPI", "KOSDAQ"]:
            raise HTTPException(status_code=400, detail=f"유효하지 않은 시장입니다. KOSPI 또는 KOSDAQ를 사용하세요.")
            
        df = get_stock_symbols(market.upper())
        
        return {
            "status": "success",
            "market": market.upper(),
            "count": len(df),
            "symbols": df.to_dict('records')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"종목 코드 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"종목 코드 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/symbols", response_model=Dict[str, Any])
async def get_all_symbols():
    """모든 시장의 종목 코드 목록 조회"""
    try:
        df = get_all_stock_symbols()
        
        return {
            "status": "success",
            "count": len(df),
            "symbols": df.to_dict('records')
        }
    except Exception as e:
        logger.error(f"종목 코드 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"종목 코드 조회 중 오류가 발생했습니다: {str(e)}") 