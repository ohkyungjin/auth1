import os
import pandas as pd
import logging
import FinanceDataReader as fdr
from pathlib import Path
from datetime import datetime

from app.core.config import DATA_STORAGE_PATH

logger = logging.getLogger(__name__)

# 종목 코드 파일 경로
STOCK_SYMBOLS_PATH = Path(DATA_STORAGE_PATH) / "stock_symbols"
KOSPI_SYMBOLS_FILE = STOCK_SYMBOLS_PATH / "kospi_symbols.csv"
KOSDAQ_SYMBOLS_FILE = STOCK_SYMBOLS_PATH / "kosdaq_symbols.csv"

def get_stock_symbols(market, force_update=False):
    """
    시장의 종목 코드와 종목명을 가져옵니다.
    
    Args:
        market (str): 'KOSPI' 또는 'KOSDAQ'
        force_update (bool): 강제로 업데이트할지 여부
        
    Returns:
        pd.DataFrame: 종목 코드와 종목명
    """
    # 디렉토리 생성
    STOCK_SYMBOLS_PATH.mkdir(parents=True, exist_ok=True)
    
    file_path = KOSPI_SYMBOLS_FILE if market == "KOSPI" else KOSDAQ_SYMBOLS_FILE
    
    # 파일이 존재하고, 강제 업데이트가 아니면 파일에서 로드
    if file_path.exists() and not force_update:
        # 파일이 오늘 생성된 것인지 확인
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        today = datetime.now().date()
        
        if file_mtime.date() == today:
            logger.info(f"{market} 종목 코드를 파일에서 로드합니다: {file_path}")
            return pd.read_csv(file_path)
    
    # 파일이 없거나 강제 업데이트면 FinanceDataReader에서 종목 정보 가져오기
    logger.info(f"{market} 종목 코드를 FinanceDataReader에서 가져옵니다.")
    try:
        # 최신 버전 FinanceDataReader는 다른 포맷 사용 ('KRX' 또는 'KOSPI'/'KOSDAQ')
        try:
            # 방법 1: 최신 버전 형식 시도
            if market == "KOSPI":
                df = fdr.StockListing('KOSPI')
            else:  # KOSDAQ
                df = fdr.StockListing('KOSDAQ')
                
            if df.empty:
                raise ValueError(f"{market} 데이터 비어있음")
                
        except Exception as inner_e:
            logger.warning(f"최신 형식으로 {market} 종목 코드 가져오기 실패: {str(inner_e)}")
            
            try:
                # 방법 2: 'KRX' 사용 후 필터링
                df = fdr.StockListing('KRX')
                
                # KRX 내에서 해당 시장만 필터링
                if market == "KOSPI":
                    df = df[df['Market'].str.contains('KOSPI', na=False)]
                else:  # KOSDAQ
                    df = df[df['Market'].str.contains('KOSDAQ', na=False)]
                
                if df.empty:
                    raise ValueError(f"KRX 필터링 후 {market} 데이터 비어있음")
                    
            except Exception as krx_e:
                logger.warning(f"KRX 목록에서 {market} 필터링 실패: {str(krx_e)}")
                raise ValueError(f"모든 종목 가져오기 방법 실패: {str(inner_e)}, KRX 시도: {str(krx_e)}")
        
        # 필요한 컬럼 확인 및 선택
        required_columns = {'Code', 'Name', 'Market'}
        if not all(col in df.columns for col in required_columns):
            logger.warning(f"필요한 컬럼이 없습니다. 현재 컬럼: {df.columns.tolist()}")
            
            # 컬럼명 매핑 (다양한 버전 지원)
            col_mapping = {}
            for col in df.columns:
                lower_col = col.lower()
                if 'code' in lower_col or 'symbol' in lower_col:
                    col_mapping['Code'] = col
                elif 'name' in lower_col or '종목명' in lower_col:
                    col_mapping['Name'] = col
                elif 'market' in lower_col or '시장' in lower_col:
                    col_mapping['Market'] = col
                    
            # 필요한 컬럼 없으면 오류
            for req_col in required_columns:
                if req_col not in col_mapping:
                    logger.error(f"매핑할 수 없는 필수 컬럼: {req_col}")
                    raise ValueError(f"필수 컬럼 '{req_col}'을 찾을 수 없습니다")
                    
            # 컬럼 이름 변경
            df = df.rename(columns=col_mapping)
        
        # 최소 필요 컬럼 선택
        df = df[['Code', 'Name', 'Market']]
        
        # 컬럼명 변경
        df = df.rename(columns={
            'Code': 'stock_code',
            'Name': 'stock_name',
            'Market': 'market_detail',
        })
        
        # 종목코드 형식 확인 및 수정 (앞에 A가 붙는 경우 등 처리)
        if df['stock_code'].dtype != 'object':
            df['stock_code'] = df['stock_code'].astype(str)
            
        # 숫자가 아닌 문자가 포함된 경우 (ex: 'A005930') 처리 및 6자리 맞추기
        logger.info("종목코드 형식 수정 중 (숫자만 추출 후 6자리로 변환)")
        
        def format_stock_code(code):
            # 숫자만 추출
            digits = ''.join(c for c in str(code) if c.isdigit())
            # 6자리로 맞추기 (앞에 0 채우기)
            return digits.zfill(6)
            
        df['stock_code'] = df['stock_code'].apply(format_stock_code)
        
        # 시장 정보 추가
        df['market'] = market
        
        # 파일로 저장
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        logger.info(f"{market} 종목 코드를 파일에 저장했습니다: {file_path} (총 {len(df)}개 종목)")
        
        return df
        
    except Exception as e:
        logger.error(f"{market} 종목 코드를 가져오는 중 오류 발생: {str(e)}")
        
        # 파일이 있으면 파일에서 로드
        if file_path.exists():
            logger.warning(f"기존 파일에서 {market} 종목 코드를 로드합니다: {file_path}")
            return pd.read_csv(file_path)
        
        # 빈 DataFrame 반환
        logger.warning(f"빈 {market} 종목 코드 목록을 반환합니다.")
        return pd.DataFrame(columns=['stock_code', 'stock_name', 'market', 'market_detail'])

def update_stock_symbols():
    """모든 시장의 종목 코드를 업데이트합니다."""
    logger.info("모든 시장의 종목 코드 업데이트를 시작합니다.")
    
    kospi_df = get_stock_symbols("KOSPI", force_update=True)
    kosdaq_df = get_stock_symbols("KOSDAQ", force_update=True)
    
    logger.info(f"종목 코드 업데이트 완료: KOSPI {len(kospi_df)}개, KOSDAQ {len(kosdaq_df)}개")
    
    return {
        "KOSPI": len(kospi_df),
        "KOSDAQ": len(kosdaq_df)
    }

def get_all_stock_symbols():
    """모든 시장의 종목 코드를 가져옵니다."""
    kospi_df = get_stock_symbols("KOSPI")
    kosdaq_df = get_stock_symbols("KOSDAQ")
    
    # 모든
    all_df = pd.concat([kospi_df, kosdaq_df], ignore_index=True)
    
    return all_df 