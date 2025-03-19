import json
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import logging
from pathlib import Path
import pytz
import random
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import os
import threading
import requests
import time

from app.core.config import (
    KOREA_INV_APPKEY,
    KOREA_INV_APPSECRET,
    KOREA_INV_ACCOUNT,
    TIMEZONE,
    DATA_STORAGE_PATH,
    MAX_STOCK_ITEMS
)

# 종목 코드 유틸리티 import
from app.utils.stock_symbols import get_stock_symbols

logger = logging.getLogger(__name__)

# API 관련 예외 클래스 정의
class KoreaInvestmentAPIError(Exception):
    """한국투자증권 API 관련 에러 기본 클래스"""
    pass

class TokenGenerationError(KoreaInvestmentAPIError):
    """토큰 생성 실패 에러"""
    pass

class APIResponseError(KoreaInvestmentAPIError):
    """API 응답 에러"""
    def __init__(self, status_code, message, response_data=None):
        self.status_code = status_code
        self.message = message
        self.response_data = response_data
        super().__init__(f"API 응답 오류 (상태 코드: {status_code}): {message}")

class KoreaInvestmentAPI:
    """한국투자증권 API 클라이언트"""
    
    BASE_URL = "https://openapi.koreainvestment.com:9443"
    
    # 싱글톤 패턴 및 토큰 관리용 클래스 변수
    _instance = None
    _access_token = None
    _token_expired_at = None
    _token_lock = threading.Lock()
    _token_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token_cache.json")
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KoreaInvestmentAPI, cls).__new__(cls)
            cls._load_token_from_cache()
        return cls._instance
    
    def __init__(self):
        self.app_key = KOREA_INV_APPKEY
        self.app_secret = KOREA_INV_APPSECRET
        self.account_no = KOREA_INV_ACCOUNT
        self.timezone = pytz.timezone(TIMEZONE)
        
    @classmethod
    def _load_token_from_cache(cls):
        """토큰 캐시 파일에서 토큰 정보 로드"""
        try:
            if os.path.exists(cls._token_file):
                with open(cls._token_file, 'r') as f:
                    token_data = json.load(f)
                    
                cls._access_token = token_data.get("access_token")
                expired_at_str = token_data.get("expired_at")
                
                if expired_at_str:
                    cls._token_expired_at = datetime.fromisoformat(expired_at_str)
                    
                    if datetime.now() < cls._token_expired_at:
                        logger.info(f"캐시된 토큰 로드됨 (만료 예정: {cls._token_expired_at.strftime('%Y-%m-%d %H:%M:%S')})")
                    else:
                        logger.info("캐시된 토큰이 만료되었습니다. 새 토큰을 발급받아야 합니다.")
                        cls._access_token = None
                        cls._token_expired_at = None
                else:
                    cls._access_token = None
                    cls._token_expired_at = None
        except Exception as e:
            logger.warning(f"토큰 캐시 로드 중 오류 발생: {str(e)}")
            cls._access_token = None
            cls._token_expired_at = None
    
    @classmethod
    def _save_token_to_cache(cls):
        """토큰 정보를 캐시 파일에 저장"""
        if not cls._access_token or not cls._token_expired_at:
            return
            
        try:
            token_data = {
                "access_token": cls._access_token,
                "expired_at": cls._token_expired_at.isoformat()
            }
            
            os.makedirs(os.path.dirname(cls._token_file), exist_ok=True)
            
            with open(cls._token_file, 'w') as f:
                json.dump(token_data, f)
                
            logger.info(f"토큰이 캐시 파일에 저장됨: {cls._token_file}")
        except Exception as e:
            logger.warning(f"토큰 캐시 저장 중 오류 발생: {str(e)}")
        
    def get_access_token(self):
        """API 접근 토큰 발급 (또는 캐시에서 가져오기)"""
        # 1. 기존 토큰이 유효한 경우 재사용
        if KoreaInvestmentAPI._access_token and KoreaInvestmentAPI._token_expired_at and datetime.now() < KoreaInvestmentAPI._token_expired_at:
            return KoreaInvestmentAPI._access_token
        
        # 2. 토큰 발급 (스레드 안전하게)
        with KoreaInvestmentAPI._token_lock:
            # 락 획득 후 한번 더 체크 (다른 스레드가 갱신했을 수 있음)
            if KoreaInvestmentAPI._access_token and KoreaInvestmentAPI._token_expired_at and datetime.now() < KoreaInvestmentAPI._token_expired_at:
                return KoreaInvestmentAPI._access_token
            
            logger.info("한국투자증권 API 토큰 발급 요청")
            
            # 3. API 호출로 새 토큰 발급
            try:
                url = f"{self.BASE_URL}/oauth2/tokenP"
                headers = {"content-type": "application/json"}
                body = {
                    "grant_type": "client_credentials",
                    "appkey": self.app_key,
                    "appsecret": self.app_secret
                }
                
                response = requests.post(url, headers=headers, json=body, timeout=10)
                
                if response.status_code != 200:
                    logger.error(f"토큰 발급 실패: {response.status_code} - {response.text}")
                    return KoreaInvestmentAPI._access_token  # 기존 토큰 반환 (있다면)
                
                result = response.json()
                KoreaInvestmentAPI._access_token = result.get("access_token")
                expires_in = result.get("expires_in", 86400)  # 기본값 24시간
                KoreaInvestmentAPI._token_expired_at = datetime.now() + timedelta(seconds=expires_in - 300)  # 만료 5분 전
                
                # 캐시에 저장
                self._save_token_to_cache()
                
                logger.info(f"새 토큰 발급 성공 (만료 예정: {KoreaInvestmentAPI._token_expired_at.strftime('%Y-%m-%d %H:%M:%S')})")
                return KoreaInvestmentAPI._access_token
                
            except Exception as e:
                logger.error(f"토큰 발급 중 오류: {str(e)}")
                return KoreaInvestmentAPI._access_token  # 기존 토큰 반환 (있다면)
    
    def _format_stock_code(self, code):
        """종목 코드를 6자리 문자열로 변환"""
        digits = ''.join(c for c in str(code) if c.isdigit())
        return digits.zfill(6)
    
    async def get_stock_item_list(self, market):
        """특정 시장(KOSPI, KOSDAQ)의 종목 리스트 조회"""
        logger.info(f"{market} 시장 종목 리스트 조회")
        
        # FinanceDataReader를 통해 종목 코드 가져오기
        df = get_stock_symbols(market)
        
        if df.empty:
            logger.warning(f"{market} 종목 리스트가 비어있음, 샘플 데이터 사용")
            return self._get_sample_stocks(market)
            
        stock_items = df.to_dict('records')
        logger.info(f"{market} 시장 종목 {len(stock_items)}개 조회 완료")
        return stock_items
            
    def _get_sample_stocks(self, market, count=10):
        """테스트용 샘플 종목 데이터"""
        if market == "KOSPI":
            codes = ["005930", "000660", "051910", "035420", "005380"]
            names = ["삼성전자", "SK하이닉스", "LG화학", "NAVER", "현대차"]
        else:  # KOSDAQ
            codes = ["247540", "035900", "086520", "277810", "068270"]
            names = ["에코프로비엠", "JYP Ent.", "에코프로", "레인보우로보틱스", "셀트리온제약"]
        
        result = []
        for i in range(min(count, len(codes))):
            result.append({
                "stock_code": codes[i],
                "stock_name": names[i],
                "market": market
            })
        return result
    
    def get_stock_ohlcv(self, stock_code, from_date, to_date=None):
        """특정 종목의 OHLCV 데이터 조회
        
        Args:
            stock_code: 종목 코드
            from_date: 조회 시작일(YYYYMMDD)
            to_date: 조회 종료일(YYYYMMDD), 없으면 오늘 날짜
        """
        if not to_date:
            to_date = datetime.now().strftime("%Y%m%d")
            
        # 동일한 날짜인 경우 로그 상세화 안함
        if from_date == to_date:
            logger.debug(f"종목 {stock_code} {from_date} 하루 데이터 조회")
            
        formatted_code = self._format_stock_code(stock_code)
        
        try:
            # 1. 토큰 가져오기
            token = self.get_access_token()
            if not token:
                logger.error(f"토큰이 없어 API 호출 불가 (종목: {formatted_code})")
                return []
            
            # 2. API 호출 준비
            url = f"{self.BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-price"
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "FHKST01010400"
            }
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": formatted_code,
                "fid_period_div_code": "D",
                "fid_org_adj_prc": "1",
                "fid_input_date_1": from_date,
                "fid_input_date_2": to_date
            }
            
            logger.debug(f"API 호출: 종목 {formatted_code}, 기간 {from_date}~{to_date}")
            
            # 3. API 요청 전송
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            # 4. 응답 처리
            if response.status_code != 200:
                logger.error(f"API 호출 실패 (종목: {formatted_code}): 상태코드 {response.status_code}, 응답: {response.text}")
                return []
            
            data = response.json()
            
            # API 응답 오류 확인
            if data.get("rt_cd") != "0":
                logger.error(f"API 오류 (종목: {formatted_code}): {data.get('msg1')}")
                return []
            
            # 5. 데이터 추출 (output1 또는 output2에 데이터가 있을 수 있음)
            output = []
            if "output1" in data and data["output1"]:
                output = data["output1"]
            elif "output2" in data and data["output2"]:
                output = data["output2"]
            elif "output" in data and data["output"]:
                output = data["output"]
            
            # 날짜 필터링 (API가 날짜 범위를 정확히 지키지 않는 경우 대비)
            filtered_output = []
            for item in output:
                date_field = "stck_bsop_date" if "stck_bsop_date" in item else "bass_dt"
                item_date = item.get(date_field, "")
                if from_date <= item_date <= to_date:
                    filtered_output.append(item)
                    
            output = filtered_output
            
            if output:
                # 로그 레벨을 debug로 변경하여 콘솔 출력을 줄임
                logger.debug(f"종목 {formatted_code} 데이터 {len(output)}개 수집")
            else:
                logger.warning(f"종목 {formatted_code} 데이터 없음")
            
            return output
            
        except Exception as e:
            logger.error(f"데이터 조회 오류 (종목: {formatted_code}): {str(e)}")
            return []
    
    async def collect_market_data(self, market, from_date, to_date=None):
        """특정 시장의 전체 종목 OHLCV 데이터 수집"""
        import asyncio
        
        if not to_date:
            to_date = datetime.now().strftime("%Y%m%d")
            
        logger.info(f"{market} 시장 데이터 수집 시작 (기간: {from_date} ~ {to_date})")
        
        try:
            # 1. 종목 리스트 조회
            stock_items = await self.get_stock_item_list(market)
            
            # 2. 종목 수 제한 적용
            if MAX_STOCK_ITEMS > 0:
                stock_items = stock_items[:MAX_STOCK_ITEMS]
                
            logger.info(f"{market} 시장 {len(stock_items)}개 종목 데이터 수집 예정")
            
            # 3. 데이터 수집 (배치 처리)
            all_data = []
            batch_size = 10  # 배치당 종목 수
            max_workers = 3  # 동시 처리 작업 수
            batches = [stock_items[i:i+batch_size] for i in range(0, len(stock_items), batch_size)]
            
            sem = asyncio.Semaphore(max_workers)
            
            async def collect_stock_data(item):
                """단일 종목 데이터 수집"""
                async with sem:
                    code = item["stock_code"]
                    name = item["stock_name"]
                    
                    # 동기 API 호출 (이벤트 루프 차단 방지)
                    data = await asyncio.to_thread(self.get_stock_ohlcv, code, from_date, to_date)
                    
                    stock_data = []
                    for row in data:
                        row_data = {
                            "거래일": row["stck_bsop_date"],
                            "종목코드": code,
                            "종목명": name,
                            "시장구분": market,
                            "시가": int(row["stck_oprc"]),
                            "고가": int(row["stck_hgpr"]),
                            "저가": int(row["stck_lwpr"]),
                            "종가": int(row["stck_clpr"]),
                            "거래량": int(row["acml_vol"])
                        }
                        stock_data.append(row_data)
                    
                    return stock_data
            
            for batch_idx, batch in enumerate(batches):
                logger.info(f"{market} 시장 배치 {batch_idx+1}/{len(batches)} 처리 중 ({len(batch)}개 종목)")
                
                # 배치 내 종목별 데이터 수집 (병렬)
                tasks = [collect_stock_data(item) for item in batch]
                results = await asyncio.gather(*tasks)
                
                # 결과 합치기
                for result in results:
                    if result:
                        all_data.extend(result)
                
                # 배치 간 딜레이 (API 호출 제한 방지)
                if batch_idx < len(batches) - 1:
                    await asyncio.sleep(1)
            
            # 4. 수집 데이터 처리
            if not all_data:
                logger.warning(f"{market} 시장 데이터가 없습니다.")
                return pd.DataFrame()
                
            # 5. 데이터프레임 변환 및 저장
            df = pd.DataFrame(all_data)
            
            # 파일 저장
            date_str = from_date if from_date == to_date else f"{from_date}_to_{to_date}"
            filename = f"{market}_OHLCV_{date_str}.csv"
            file_path = Path(DATA_STORAGE_PATH) / filename
            
            # 디렉토리 생성
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # CSV 저장
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            logger.info(f"{market} 시장 데이터 {len(df)}행 저장 완료: {file_path}")
            
            return df
            
        except Exception as e:
            logger.error(f"{market} 시장 데이터 수집 중 오류: {str(e)}")
            return pd.DataFrame()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, asyncio.TimeoutError, APIResponseError)),
        before_sleep=lambda retry_state: logger.warning(
            f"API 호출 재시도 중... (시도: {retry_state.attempt_number}/3, 에러: {retry_state.outcome.exception()})"
        )
    )
    async def _api_request(self, method, endpoint, headers=None, params=None, json_data=None):
        """API 요청 공통 메서드 (재시도 로직 포함)"""
        if headers is None:
            headers = {}
            
        url = f"{self.BASE_URL}{endpoint}"
        
        # 접근 토큰이 필요한 API인 경우 헤더에 추가
        if "authorization" not in {k.lower() for k in headers.keys()}:
            access_token = await self.get_access_token()
            headers["authorization"] = f"Bearer {access_token}"
            
        # 요청 정보 로깅
        request_id = random.randint(10000, 99999)  # 요청 추적용 임의 ID
        log_data = {
            "request_id": request_id,
            "method": method,
            "url": url,
            "params": params,
        }
        logger.debug(f"API 요청: {json.dumps(log_data)}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, params=params, json=json_data)
                else:
                    raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")
                
                # 응답 정보 로깅
                log_data = {
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "elapsed_ms": response.elapsed.total_seconds() * 1000,
                }
                logger.debug(f"API 응답: {json.dumps(log_data)}")
                
                # 응답 상태 코드 검증
                if 200 <= response.status_code < 300:
                    return response.json() if response.content else {}
                else:
                    # 오류 응답 상세 정보 로깅
                    response_data = response.json() if response.content and response.headers.get("content-type", "").startswith("application/json") else {}
                    error_msg = response_data.get("msg", "알 수 없는 오류")
                    
                    log_data = {
                        "request_id": request_id,
                        "status_code": response.status_code,
                        "error_message": error_msg,
                        "response_data": response_data,
                    }
                    logger.error(f"API 오류 응답: {json.dumps(log_data)}")
                    
                    raise APIResponseError(
                        status_code=response.status_code,
                        message=error_msg,
                        response_data=response_data
                    )
                    
        except (httpx.HTTPError, asyncio.TimeoutError) as e:
            log_data = {
                "request_id": request_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            logger.error(f"API 요청 네트워크 오류: {json.dumps(log_data)}")
            raise
        except Exception as e:
            log_data = {
                "request_id": request_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            }
            logger.error(f"API 요청 처리 중 예외 발생: {json.dumps(log_data)}", exc_info=True)
            raise 