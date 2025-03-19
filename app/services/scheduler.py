import logging
import asyncio
import schedule
import time
import threading
from datetime import datetime, timedelta
import pytz

from app.services.data_collector import DataCollector
from app.core.config import TIMEZONE, SCHEDULE_TIME

logger = logging.getLogger(__name__)

class StockDataScheduler:
    """주식 데이터 수집 스케줄러"""
    
    def __init__(self):
        self.collector = DataCollector()
        self.timezone = pytz.timezone(TIMEZONE)
        self.is_running = False
        self.scheduler_thread = None
        
    def start(self):
        """스케줄러 시작"""
        if self.is_running:
            logger.warning("스케줄러가 이미 실행 중입니다.")
            return False
            
        logger.info("주식 데이터 수집 스케줄러 시작")
        
        # 평일 오후 6시에 실행 (월-금)
        schedule.every().monday.at(SCHEDULE_TIME).do(self._run_collect_job)
        schedule.every().tuesday.at(SCHEDULE_TIME).do(self._run_collect_job)
        schedule.every().wednesday.at(SCHEDULE_TIME).do(self._run_collect_job)
        schedule.every().thursday.at(SCHEDULE_TIME).do(self._run_collect_job)
        schedule.every().friday.at(SCHEDULE_TIME).do(self._run_collect_job)
        
        # 스케줄러 쓰레드 시작
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        logger.info(f"스케줄러가 설정되었습니다. 평일 {SCHEDULE_TIME}에 데이터 수집이 실행됩니다.")
        return True
        
    def stop(self):
        """스케줄러 중지"""
        if not self.is_running:
            logger.warning("스케줄러가 실행 중이 아닙니다.")
            return False
            
        logger.info("주식 데이터 수집 스케줄러 중지")
        self.is_running = False
        schedule.clear()
        
        # 스케줄러 쓰레드가 종료될 때까지 대기
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
            
        return True
        
    def _run_scheduler(self):
        """스케줄러 실행 루프"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 체크
            
    def _run_collect_job(self):
        """데이터 수집 작업 실행"""
        logger.info("스케줄된 데이터 수집 작업 시작")
        
        # 비동기 함수를 이벤트 루프에서 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            collect_result = loop.run_until_complete(self._collect_today_data())
            logger.info(f"스케줄된 데이터 수집 완료: {collect_result}")
            return True
        except Exception as e:
            logger.error(f"스케줄된 데이터 수집 실패: {str(e)}")
            return False
        finally:
            loop.close()
            
    async def _collect_today_data(self):
        """오늘의 데이터 수집 실행"""
        return await self.collector.collect_today_data()
        
    def get_next_run_time(self):
        """다음 실행 시간 조회"""
        if not self.is_running:
            return None
            
        now = datetime.now(self.timezone)
        today_schedule_time = datetime.strptime(SCHEDULE_TIME, "%H:%M").time()
        today_schedule_datetime = datetime.combine(now.date(), today_schedule_time)
        
        # 요일에 따라 다음 실행 날짜 계산
        weekday = now.weekday()  # 0=월요일, 6=일요일
        
        if weekday >= 5:  # 주말
            days_until_monday = 7 - weekday
            next_run_date = now.date() + timedelta(days=days_until_monday)
        elif now.time() >= today_schedule_time:  # 오늘 실행 시간 이후
            if weekday == 4:  # 금요일이면 다음 월요일
                next_run_date = now.date() + timedelta(days=3)
            else:  # 다음 날
                next_run_date = now.date() + timedelta(days=1)
        else:  # 오늘 실행 시간 이전
            next_run_date = now.date()
            
        next_run_datetime = datetime.combine(next_run_date, today_schedule_time)
        next_run_datetime = self.timezone.localize(next_run_datetime)
        
        return next_run_datetime 