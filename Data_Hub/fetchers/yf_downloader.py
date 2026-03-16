# 文件位置: Data_Hub/fetchers/yf_downloader.py
import sys
import os
from pathlib import Path

# 在直接运行脚本时，使项目根目录可用于导入（如 Core_Bus、Data_Hub 等包）
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import yfinance as yf
import pandas as pd
from Core_Bus.standard import standardize_ohlcv # 引入总线标准

class YFinanceDownloader:
    def __init__(self, storage_dir="Data_Hub/storage", proxy: str = None):
        self.storage_dir = storage_dir
        self.proxy = proxy

    def download_and_save(self, symbol: str, start_date: str, end_date: str):
        print(f"📥 开始从 yfinance 拉取 {symbol} ({start_date} 至 {end_date})...")
        
        # 1. 保证存储目录存在
        os.makedirs(self.storage_dir, exist_ok=True)

        # 2. 调用 yfinance 下载：优先使用 yf.download（更稳定）
        fetch_kw = {
            'start': start_date,
            'end': end_date,
            'auto_adjust': True,
            'threads': False,
        }
        if self.proxy:
            fetch_kw['proxy'] = self.proxy

        raw_df = pd.DataFrame()
        try:
            raw_df = yf.download(symbol, **fetch_kw)
        except Exception as e:
            print(f"⚠️ yf.download 失败（{symbol}）：{e}")

        if raw_df is None or raw_df.empty:
            print(f"⚠️ yf.download 未返回数据，尝试 YF Ticker.history 备用方案")
            try:
                ticker = yf.Ticker(symbol)
                ticker_kw = fetch_kw.copy()
                ticker_kw.pop('threads', None)  # 仅 yf.download 支持 threads
                raw_df = ticker.history(**ticker_kw)
            except Exception as e:
                print(f"❌ Ticker.history 失败（{symbol}）：{e}")
                return False

        if raw_df is None or raw_df.empty:
            print(f"❌ 拉取失败或无数据: {symbol}")
            return False

        # 2. 经过 Core_Bus 进行标准化清洗
        standard_df = standardize_ohlcv(raw_df)
        
        # 3. 落地为高效的 Parquet 格式
        # 案例说明：相比 CSV，Parquet 体积小、带类型推断，且读取速度极快
        file_path = os.path.join(self.storage_dir, f"{symbol}.parquet")
        standard_df.to_parquet(file_path)
        
        print(f"✅ 成功落地至: {file_path}")
        return True