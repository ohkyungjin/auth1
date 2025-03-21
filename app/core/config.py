import os
from dotenv import load_dotenv
from pathlib import Path

# 환경 변수 로드
load_dotenv()

# 한국투자증권 API 설정
KOREA_INV_APPKEY = os.getenv("KOREA_INV_APPKEY")
KOREA_INV_APPSECRET = os.getenv("KOREA_INV_APPSECRET")
KOREA_INV_ACCOUNT = os.getenv("KOREA_INV_ACCOUNT")

# 텔레그램 봇 설정
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 데이터 저장 경로
DATA_STORAGE_PATH = Path(os.getenv("DATA_STORAGE_PATH", "./data/stock_data"))

# API 설정
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))

# 타임존 설정
TIMEZONE = "Asia/Seoul"

# 스케줄링 설정 (평일 오후 6시)
SCHEDULE_TIME = "18:00"

# 마켓 정보
MARKETS = ["KOSPI", "KOSDAQ"]

# 수집할 필드 설정
FIELDS = ["거래일", "종목명", "종목코드", "시가", "종가", "저가", "고가", "거래량"]

# KOSPI 주요 종목 (시가총액 상위 50개)
KOSPI_TOP_STOCKS = [
    "005930", "000660", "051910", "035420", "005380", "006400", "000270", "005490", "035720", "012330",
    "066570", "055550", "068270", "003670", "034730", "207940", "000810", "009150", "018260", "096770",
    "050960", "105560", "028260", "015760", "011200", "005830", "138040", "323410", "010950", "009830",
    "024110", "028050", "316140", "010130", "011070", "036570", "003550", "032830", "090430", "086790",
    "012750", "000100", "047050", "071050", "004370", "017670", "034020", "021240", "051900", "034220"
]

# KOSDAQ 주요 종목 (시가총액 상위 50개)
KOSDAQ_TOP_STOCKS = [
    "247540", "035900", "086520", "277810", "068270", "058470", "263750", "096530", "091990", "028300",
    "293490", "020150", "145020", "005290", "141080", "403870", "214370", "240810", "041510", "357780",
    "039030", "095340", "067160", "048410", "196170", "112040", "035760", "214150", "078600", "108860",
    "000250", "240810", "195940", "298380", "140410", "025900", "035600", "093320", "189300", "237690",
    "095700", "122870", "005290", "078340", "064760", "068760", "365340", "036030", "032500", "060280"
]

# 종목 데이터 수집 최대 개수 (0은 제한 없음)
MAX_STOCK_ITEMS = 0  # 모든 종목 수집 