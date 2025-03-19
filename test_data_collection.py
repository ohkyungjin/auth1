import pandas as pd
import datetime
import random
import os
from pathlib import Path

# 샘플 데이터 생성 함수
def generate_sample_data(market, date_str, num_stocks=30):
    # 주식 코드 및 이름 샘플
    stock_codes = [f"{i:06d}" for i in range(1, num_stocks + 1)]
    stock_names = [f"{market}샘플주식{i}" for i in range(1, num_stocks + 1)]
    
    data = []
    for i in range(num_stocks):
        base_price = random.randint(10000, 100000)
        change_rate = random.uniform(-0.05, 0.05)
        
        open_price = base_price
        close_price = int(base_price * (1 + change_rate))
        high_price = max(open_price, close_price) + random.randint(0, 2000)
        low_price = min(open_price, close_price) - random.randint(0, 2000)
        volume = random.randint(10000, 1000000)
        
        data.append({
            "거래일": date_str,
            "종목명": stock_names[i],
            "종목코드": stock_codes[i],
            "시장": market,
            "시가": open_price,
            "종가": close_price,
            "고가": high_price,
            "저가": low_price,
            "거래량": volume
        })
    
    return pd.DataFrame(data)

# 저장 경로 생성
save_path = Path("./data/stock_data")
save_path.mkdir(parents=True, exist_ok=True)

# 오늘 날짜
today = datetime.datetime.now().strftime("%Y%m%d")
today_formatted = datetime.datetime.now().strftime("%Y-%m-%d")

# KOSPI 데이터 생성 및 저장
kospi_df = generate_sample_data("KOSPI", today_formatted)
kospi_path = save_path / f"KOSPI_OHLCV_{today}.csv"
kospi_df.to_csv(kospi_path, index=False, encoding='utf-8-sig')
print(f"KOSPI 샘플 데이터 생성 완료: {kospi_path}")

# KOSDAQ 데이터 생성 및 저장
kosdaq_df = generate_sample_data("KOSDAQ", today_formatted)
kosdaq_path = save_path / f"KOSDAQ_OHLCV_{today}.csv"
kosdaq_df.to_csv(kosdaq_path, index=False, encoding='utf-8-sig')
print(f"KOSDAQ 샘플 데이터 생성 완료: {kosdaq_path}")

print(f"총 {len(kospi_df) + len(kosdaq_df)}개의 샘플 주식 데이터가 생성되었습니다.") 