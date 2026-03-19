import os
import pandas as pd
from Data_Hub.fetchers.yf_downloader import YFinanceDownloader

# 标的列表（从存储目录自动获取）
storage_dir = "Data_Hub/storage"
parquet_files = [f for f in os.listdir(storage_dir) if f.endswith('.parquet')]
symbols = [f.replace('.parquet', '') for f in parquet_files]

# 下载器
downloader = YFinanceDownloader(storage_dir=storage_dir)

# 批量更新
for symbol in symbols:
    print(f"\n=== 更新 {symbol} ===")
    # 检查上市日期
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.info
        ipo_date = info.get('ipoDate') or info.get('startDate') or info.get('firstTradeDateEpoch')
        if ipo_date:
            if isinstance(ipo_date, int):
                # epoch时间戳
                ipo_date = pd.to_datetime(ipo_date, unit='s').strftime('%Y-%m-%d')
            elif isinstance(ipo_date, str):
                ipo_date = ipo_date[:10]
            else:
                ipo_date = '2019-01-01'
        else:
            ipo_date = '2019-01-01'
    except Exception as e:
        print(f"⚠️ 无法获取上市日期，默认2019-01-01: {e}")
        ipo_date = '2019-01-01'
    
    downloader.download_and_save(symbol, ipo_date, '2026-03-19')
print("\n✅ 所有标的已批量更新至2019-01-01或上市日！")
