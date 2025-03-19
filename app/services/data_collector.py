import asyncio
import logging
from datetime import datetime, timedelta
import pytz
import pandas as pd
from pathlib import Path
import concurrent.futures
from typing import List, Dict, Any, Optional
from functools import partial

from app.services.korea_investment_api import KoreaInvestmentAPI
from app.services.telegram_service import TelegramService
from app.core.config import TIMEZONE, MARKETS, DATA_STORAGE_PATH, MAX_STOCK_ITEMS

logger = logging.getLogger(__name__)

class DataCollector:
    """주식 데이터 수집 서비스"""
    
    def __init__(self):
        self.korea_api = KoreaInvestmentAPI()
        self.telegram = TelegramService()
        self.timezone = pytz.timezone(TIMEZONE)
        self.max_concurrent_workers = 5  # 동시 처리 워커 수
        
    async def collect_today_data(self):
        """오늘의 데이터 수집"""
        logger.info("오늘의 주식 데이터 수집 시작")
        
        # 현재 연도 확인
        current_year = datetime.now().year
        today_raw = datetime.now(self.timezone).strftime("%Y%m%d")
        
        # 잘못된 연도 수정 (시스템 연도가 잘못 설정된 경우)
        if int(today_raw[:4]) > current_year:
            today = today_raw.replace(today_raw[:4], str(current_year), 1)
            logger.warning(f"잘못된 연도 감지: {today_raw} → {today}로 수정")
        else:
            today = today_raw
            
        logger.info(f"오늘 날짜: {today}, 이 날짜의 데이터만 수집합니다.")
        results = {}
        
        try:
            tasks = []
            for market in MARKETS:
                # 동일한 날짜를 from_date와 to_date에 지정하여 오늘 데이터만 수집
                task = self._collect_market_data(market, today, today)
                tasks.append(task)
                
            # 비동기로 여러 시장 데이터 동시 수집
            market_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, market in enumerate(MARKETS):
                if isinstance(market_results[i], Exception):
                    logger.error(f"{market} 시장 데이터 수집 실패: {str(market_results[i])}")
                    await self.telegram.send_error_notification(f"{market} 시장 데이터 수집 실패: {str(market_results[i])}")
                else:
                    df, file_path = market_results[i]
                    if not df.empty:
                        count = len(df)
                        results[market] = count
                        
                        # 텔레그램 알림 전송
                        await self.telegram.send_data_collection_notification(
                            market=market,
                            data_count=count,
                            file_path=str(file_path)
                        )
                    
            return results
            
        except Exception as e:
            error_msg = f"오늘의 데이터 수집 중 오류 발생: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await self.telegram.send_error_notification(error_msg)
            raise
    
    async def collect_historical_data(self, from_date, to_date=None):
        """과거 데이터 수집"""
        logger.info(f"과거 주식 데이터 수집 시작 (기간: {from_date} ~ {to_date or '현재'})")
        
        # 날짜 포맷 검증 (YYYYMMDD)
        try:
            # 날짜 포맷 검증 및 변환
            from_date_obj = datetime.strptime(from_date, "%Y%m%d")
            current_year = datetime.now().year
            
            # 잘못된 연도 수정 (2025년은 2024년의 오타일 가능성이 높음)
            if from_date_obj.year > current_year:
                correct_from_date = from_date.replace(str(from_date_obj.year), str(current_year), 1)
                logger.warning(f"잘못된 연도 감지: {from_date} → {correct_from_date}로 수정")
                from_date = correct_from_date
                from_date_obj = datetime.strptime(from_date, "%Y%m%d")
            
            # to_date가 있는 경우 검증
            if to_date:
                to_date_obj = datetime.strptime(to_date, "%Y%m%d")
                if to_date_obj.year > current_year:
                    correct_to_date = to_date.replace(str(to_date_obj.year), str(current_year), 1)
                    logger.warning(f"잘못된 연도 감지: {to_date} → {correct_to_date}로 수정")
                    to_date = correct_to_date
            else:
                # 현재 날짜를 to_date로 사용
                to_date = datetime.now(self.timezone).strftime("%Y%m%d")
                
            logger.info(f"수정된 데이터 수집 기간: {from_date} ~ {to_date}")
        except ValueError as e:
            error_msg = f"잘못된 날짜 형식: {str(e)}"
            logger.error(error_msg)
            await self.telegram.send_error_notification(error_msg)
            raise ValueError(error_msg)
            
        results = {}
        
        try:
            tasks = []
            for market in MARKETS:
                task = self._collect_market_data(market, from_date, to_date)
                tasks.append(task)
                
            # 비동기로 여러 시장 데이터 동시 수집
            market_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, market in enumerate(MARKETS):
                if isinstance(market_results[i], Exception):
                    logger.error(f"{market} 시장 데이터 수집 실패: {str(market_results[i])}")
                    await self.telegram.send_error_notification(f"{market} 시장 데이터 수집 실패: {str(market_results[i])}")
                else:
                    df, file_path = market_results[i]
                    if not df.empty:
                        count = len(df)
                        results[market] = count
                        
                        # 텔레그램 알림 전송
                        await self.telegram.send_data_collection_notification(
                            market=market,
                            data_count=count,
                            file_path=str(file_path)
                        )
                    
            return results
            
        except Exception as e:
            error_msg = f"과거 데이터 수집 중 오류 발생: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await self.telegram.send_error_notification(error_msg)
            raise
            
    async def _collect_market_data(self, market, from_date, to_date):
        """특정 시장의 데이터 수집"""
        logger.info(f"{market} 시장 데이터 수집 시작 (기간: {from_date} ~ {to_date})")
        
        # 종목 리스트 가져오기
        stock_items = await self.korea_api.get_stock_item_list(market)
        
        if MAX_STOCK_ITEMS > 0 and len(stock_items) > MAX_STOCK_ITEMS:
            logger.info(f"종목 수 제한 적용: {len(stock_items)} -> {MAX_STOCK_ITEMS}")
            stock_items = stock_items[:MAX_STOCK_ITEMS]
            
        # 종목을 배치로 나누기
        batch_size = 50  # 배치 크기 조절 가능
        batches = [stock_items[i:i+batch_size] for i in range(0, len(stock_items), batch_size)]
        logger.info(f"{market} 시장 종목 {len(stock_items)}개를 {len(batches)}개 배치로 처리")
        
        # 각 배치별로 데이터 수집
        all_data = []
        for batch_idx, batch in enumerate(batches):
            progress = f"[{'=' * (batch_idx + 1)}{' ' * (len(batches) - batch_idx - 1)}] {batch_idx+1}/{len(batches)} ({(batch_idx+1)/len(batches)*100:.1f}%)"
            logger.info(f"{market} 시장 배치 진행: {progress}")
            batch_data = await self._collect_stock_data_batch(batch, from_date, to_date)
            all_data.extend(batch_data)
            
            # 프로그레스 업데이트: 10%마다 요약 정보 출력
            if (batch_idx + 1) % max(1, len(batches) // 10) == 0 or batch_idx == len(batches) - 1:
                logger.info(f"{market} 시장 데이터 수집 진행 중: {batch_idx+1}/{len(batches)} 배치 완료 ({len(all_data)}개 데이터)")
            
            # 배치 간 딜레이
            if batch_idx < len(batches) - 1:
                await asyncio.sleep(1)
                
        # 데이터프레임 변환
        if not all_data:
            logger.warning(f"{market} 시장 데이터가 없습니다.")
            return pd.DataFrame(), None
            
        df = pd.DataFrame(all_data)
        
        # 파일 저장
        date_str = from_date if from_date == to_date else f"{from_date}_to_{to_date}"
        file_name = f"{market}_OHLCV_{date_str}.csv"
        file_path = Path(DATA_STORAGE_PATH) / file_name
        
        # 디렉토리 생성
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 파일 저장 (BOM 추가 - 한글 깨짐 방지)
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        logger.info(f"{market} 시장 데이터 저장 완료: {file_path} (총 {len(df)}개 레코드)")
        
        return df, file_path
        
    async def _collect_stock_data_batch(self, stock_items: List[Dict[str, Any]], from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """종목 배치에 대한 데이터 수집"""
        loop = asyncio.get_event_loop()
        
        # 병렬 처리를 위한 함수
        collect_func = partial(self._collect_single_stock_data, from_date=from_date, to_date=to_date)
        
        # 워커 수 제한으로 토큰 요청 부하 최소화
        max_workers = min(3, self.max_concurrent_workers)  # 최대 3개의 워커로 제한
        
        # 배치 크기 축소로 동시 발생하는 토큰 요청 수 제한
        batch_size = 10  # 각 배치당 최대 10개 종목으로 제한
        batches = [stock_items[i:i+batch_size] for i in range(0, len(stock_items), batch_size)]
        logger.info(f"소규모 배치 {len(batches)}개로 분할, 워커 {max_workers}개 사용")
        
        all_data = []
        processed_count = 0
        
        # 각 작은 배치에 대해 순차적으로 처리
        for batch_idx, batch in enumerate(batches):
            progress = f"[{'=' * (batch_idx + 1)}{' ' * (len(batches) - batch_idx - 1)}] {batch_idx+1}/{len(batches)}"
            logger.info(f"소규모 배치 진행: {progress} (총 {processed_count}/{len(stock_items)} 종목)")
            
            # ThreadPoolExecutor를 사용한 병렬 처리
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 비동기로 실행할 함수 목록
                tasks = [
                    loop.run_in_executor(executor, collect_func, stock_item)
                    for stock_item in batch
                ]
                
                # 모든 작업이 완료될 때까지 대기
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 결과 처리
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"종목 데이터 수집 실패 (종목: {batch[i]['stock_code']}): {str(result)}")
                    elif result:
                        all_data.extend(result)
                        
                processed_count += len(batch)
            
            # 배치 간 딜레이 추가 (API 호출 제한 방지)
            if batch_idx < len(batches) - 1:
                delay_time = 2  # 2초 딜레이
                logger.debug(f"배치간 {delay_time}초 대기")
                await asyncio.sleep(delay_time)
                
        logger.info(f"배치 처리 완료: 총 {len(all_data)}개 데이터 수집")
        return all_data
        
    def _collect_single_stock_data(self, stock_item: Dict[str, Any], from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """단일 종목 데이터 수집 (ThreadPoolExecutor에서 실행)"""
        stock_code = stock_item["stock_code"]
        stock_name = stock_item["stock_name"]
        market = stock_item["market"]
        
        try:
            # 동기 API 호출 (스레드 풀에서 실행되므로 동기 호출 가능)
            data = self.korea_api.get_stock_ohlcv(stock_code, from_date, to_date)
            
            if not data:
                logger.warning(f"종목 데이터 없음: {stock_code} ({stock_name})")
                return []
                
            # 데이터 형식 변환
            formatted_data = []
            for item in data:
                try:
                    # 응답 필드 이름이 API 버전에 따라 다를 수 있음
                    # FHKST01010400 트랜잭션용 필드
                    if "stck_bsop_date" in item:
                        date_field = "stck_bsop_date"
                        open_field = "stck_oprc"
                        high_field = "stck_hgpr"
                        low_field = "stck_lwpr"
                        close_field = "stck_clpr"
                        volume_field = "acml_vol"
                    # FHKST03010100 트랜잭션용 필드 또는 다른 API 필드
                    elif "bass_dt" in item:
                        date_field = "bass_dt"
                        open_field = "mksc_opnprc" 
                        high_field = "mksc_hgprc"
                        low_field = "mksc_lwprc"
                        close_field = "mksc_clsprc"
                        volume_field = "acml_trqu"
                    else:
                        logger.warning(f"알 수 없는 API 응답 형식 (종목: {stock_code}): {item}")
                        continue
                        
                    row_data = {
                        "거래일": item[date_field],
                        "종목코드": stock_code,
                        "종목명": stock_name,
                        "시장구분": market,
                        "시가": int(item[open_field]),
                        "고가": int(item[high_field]),
                        "저가": int(item[low_field]),
                        "종가": int(item[close_field]),
                        "거래량": int(item[volume_field])
                    }
                    formatted_data.append(row_data)
                except (KeyError, ValueError) as e:
                    logger.error(f"데이터 변환 오류 (종목: {stock_code}): {str(e)}, 데이터: {item}")
                    continue
                
            logger.debug(f"종목 데이터 수집 완료: {stock_code} ({stock_name}), {len(formatted_data)}개 레코드")
            return formatted_data
            
        except Exception as e:
            logger.error(f"종목 데이터 수집 중 오류: {stock_code} ({stock_name}) - {str(e)}")
            return []
            
    async def merge_collected_data(self, pattern=None):
        """수집된 데이터를 하나의 파일로 병합"""
        logger.info("수집된 데이터 병합 시작")
        
        data_path = Path(DATA_STORAGE_PATH)
        if not pattern:
            pattern = "*.csv"
            
        csv_files = list(data_path.glob(pattern))
        
        if not csv_files:
            logger.warning(f"병합할 CSV 파일을 찾을 수 없습니다: {pattern}")
            return None
            
        total_records = 0
        
        # 병렬로 CSV 파일 로드
        dfs = await self._load_csv_files_parallel(csv_files)
        
        if not dfs:
            logger.warning("병합할 데이터가 없습니다.")
            return None
            
        # 데이터 병합
        merged_df = pd.concat(dfs, ignore_index=True)
        total_records = len(merged_df)
        
        # 중복 제거
        pre_dedup_count = len(merged_df)
        merged_df = merged_df.drop_duplicates(subset=["거래일", "종목코드"], keep="last")
        post_dedup_count = len(merged_df)
        
        if pre_dedup_count > post_dedup_count:
            logger.info(f"중복 데이터 제거: {pre_dedup_count - post_dedup_count}개 레코드 제거됨")
        
        # 정렬
        merged_df = merged_df.sort_values(by=["종목코드", "거래일"], ascending=[True, False])
        
        # 병합 파일 저장
        today_str = datetime.now(self.timezone).strftime("%Y%m%d")
        merged_file_name = f"merged_stock_data_{today_str}.csv"
        merged_file_path = data_path / merged_file_name
        
        merged_df.to_csv(merged_file_path, index=False, encoding='utf-8-sig')
        logger.info(f"데이터 병합 완료: {merged_file_path} (총 레코드 수: {len(merged_df)}, 원본 데이터: {total_records}개)")
        
        return merged_file_path
        
    async def _load_csv_files_parallel(self, csv_files):
        """CSV 파일을 병렬로 로드"""
        loop = asyncio.get_event_loop()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent_workers) as executor:
            tasks = [
                loop.run_in_executor(executor, self._load_single_csv, file)
                for file in csv_files
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
        dfs = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"파일 로드 실패: {csv_files[i].name} - {str(result)}")
            elif result is not None and not result.empty:
                dfs.append(result)
                logger.info(f"파일 로드 완료: {csv_files[i].name} (레코드 수: {len(result)})")
                
        return dfs
        
    def _load_single_csv(self, file_path):
        """단일 CSV 파일 로드 (ThreadPoolExecutor에서 실행)"""
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            return df
        except Exception as e:
            logger.error(f"CSV 파일 로드 실패: {file_path.name} - {str(e)}")
            raise 