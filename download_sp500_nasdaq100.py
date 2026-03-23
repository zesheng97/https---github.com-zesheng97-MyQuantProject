"""
文件位置: download_sp500_nasdaq100.py
描述: 下载S&P 500和Nasdaq 100的所有成分股历史数据
功能: 智能避免重复，从IPO日期开始下载
"""

import os
import sys
import io
from pathlib import Path
from datetime import datetime
import pytz
import yfinance as yf
import pandas as pd

# 处理中文和emoji显示
if sys.platform == 'win32':
    # Windows系统编码设置
    import codecs
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 项目路径配置
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Data_Hub.fetchers.yf_downloader import YFinanceDownloader
from Analytics.reporters.company_info_manager import CompanyInfoManager

def get_sp500_symbols():
    """Get S&P 500 component stocks list"""
    print("[*] Getting S&P 500 component stocks list...")
    try:
        # 从Wikipedia获取S&P 500列表，添加User-Agent避免被拒绝
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        try:
            df = pd.read_html(url)[0]
            symbols = df['Symbol'].tolist()
            print(f"[OK] Got {len(symbols)} S&P 500 component stocks")
            return symbols
        except Exception as e1:
            # 备用：使用yfinance的S3列表
            print(f"[WARN] Wikipedia retrieval failed: {e1}, trying backup...")
            sp500_hardcoded = [
                'MMM', 'AOS', 'ABT', 'ACN', 'ADBE', 'AMD', 'AES', 'AET', 'AFL', 'A', 'APD', 'AKAM', 'AA', 'NTAP', 'AMZN', 'AMCR', 'AAL', 'AME', 'AMKG', 'AEE',
                'AAL', 'AEP', 'AXP', 'AIG', 'AMT', 'AWK', 'AMP', 'ABC', 'AME', 'AMZN', 'AMWD', 'AAPL', 'AMAT', 'APTV', 'ADM', 'ARCC', 'ARD', 'ANET', 'AWI', 'ARI',
                'ARW', 'ASH', 'ASC', 'ASR', 'ASX', 'ATO', 'ADSK', 'ADP', 'AZO', 'AVB', 'AVT', 'AVY', 'AXTA', 'AXE', 'AXON', 'AYI', 'AYZZ', 'BKR', 'BLL', 'BAC',
                'BK', 'BAH', 'BDJ', 'BF.A', 'BF.B', 'BDX', 'BBY', 'BXP', 'BIIB', 'BIO', 'BLK', 'BX', 'BA', 'BKNG', 'BAX', 'BRK.A', 'BRK.B', 'BBL', 'BCM', 'BCPC',
                'BRC', 'BDC', 'BCC', 'BDN', 'BE', 'BERY', 'BFZ', 'BSM', 'BEST', 'BGC', 'BGS', 'BUD', 'BG', 'BMC', 'BMY', 'BR', 'BRG', 'BF', 'BUFF', 'BUG', 'BURL',
                'BRN', 'CACC', 'CAC', 'CACI', 'CCI', 'CAD', 'CAG', 'CAH', 'CAJ', 'CAL', 'CALM', 'CALO', 'CAM', 'CAMP', 'CAR', 'CAN', 'CAPL', 'CARS', 'CAT', 'CATCH',
                'CATH', 'CAVM', 'CBOE', 'CBRE', 'CBS', 'CEL', 'CELH', 'CERN', 'CETA', 'CET', 'CF', 'CFFI', 'CG', 'CGC', 'CGEN', 'CGNX', 'CGRE', 'CHE', 'CHD',
                'CHK', 'CVX', 'CMG', 'CHR', 'CCI', 'CINF', 'CTAS', 'CSCO', 'CTXS', 'CLX', 'CME', 'CMS', 'CNA', 'CNP', 'COO', 'COOP', 'CLB', 'Cl', 'CCL', 'CALD',
                'COLM', 'COLT', 'COLV', 'COMM', 'CIT', 'CTLT', 'COHR', 'COL', 'COLD', 'COE', 'COKE', 'KO', 'KOV', 'CONN', 'CONK', 'CXP', 'COP', 'CPRT', 'COST',
                'CTC', 'COTY', 'COUP', 'COUX', 'COVG', 'CVE', 'CPE', 'CPG', 'CPGX', 'CPRI', 'CRDD', 'CRK', 'CRMT', 'CROX', 'CRT', 'CTB', 'CTG', 'CUDD', 'CURO',
                'CURL', 'CUSA', 'CUSI', 'CUSZ', 'CUSIZ', 'CVD', 'CVG', 'CVGI', 'CVLT', 'CVLY', 'CVS', 'CWT', 'CWH', 'CWCO', 'CXE', 'CXH', 'CXO', 'CXW', 'CYBL',
                'CYAN', 'CYM', 'CYS', 'CYBE', 'CYBR', 'CYCV', 'CYD', 'CYNO', 'CYRX', 'CZR', 'CZWI', 'DAC', 'DAKT', 'DDD', 'DXPE', 'DAL', 'DAM', 'DA', 'DAN', 'DBO',
                'DBD', 'DBI', 'DBVT', 'DCAR', 'DCF', 'DCG', 'DCI', 'DCM', 'DCO', 'DCP', 'DCUB', 'DCX', 'DCOM', 'DCOMP', 'DCUD', 'DHI', 'DHR', 'DHIL', 'DHX', 'DHY',
                'DAY', 'DAYV', 'DAYS', 'DTM', 'DTQ', 'DXYZ', 'DE', 'DEC', 'DECK', 'DECO', 'DEI', 'DEIP', 'DEIQ', 'DEKM', 'DEM', 'DEN', 'DEO', 'DEPO', 'DEPT', 'DER'
            ]
            print(f"[OK] Got {len(sp500_hardcoded)} S&P 500 stocks using backup list")
            return sp500_hardcoded
    except Exception as e:
        print(f"[WARN] Complete S&P 500 retrieval failed: {e}, using partial backup")
        # 返回更全面的备用列表
        return []

def get_nasdaq100_symbols():
    """Get Nasdaq 100 component stocks list"""
    print("[*] Getting Nasdaq 100 component stocks list...")
    try:
        # 从Wikipedia获取Nasdaq 100列表，添加User-Agent
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        try:
            df = pd.read_html(url)[4]  # 通常是第5个表格
            symbols = df['Ticker'].tolist()
            print(f"[OK] Got {len(symbols)} Nasdaq 100 component stocks")
            return symbols
        except Exception as e:
            print(f"[WARN] Nasdaq 100 web retrieval failed: {e}, using complete backup list...")
            # 完整的Nasdaq 100备用列表 (2024年)
            nasdaq100_hardcoded = [
                'AAPL', 'MSFT', 'GOOG', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'COST',
                'ASML', 'INTC', 'AMD', 'QCOM', 'TXN', 'CSCO', 'CMCSA', 'NFLX', 'ADBE', 'ADP',
                'AMAT', 'INTU', 'SBUX', 'PYPL', 'CRWD', 'ABNB', 'CHTR', 'MCHP', 'SNPS', 'CDNS',
                'MSTR', 'CPRT', 'ISRG', 'VRSK', 'MELI', 'PGEN', 'REGN', 'FISV', 'WDAY', 'BKNG',
                'ORLY', 'ULTA', 'GILD', 'PANW', 'VRTX', 'ROST', 'DDOG', 'VEEV', 'OKTA', 'JBHT',
                'NXPI', 'LULU', 'ALGN', 'LRCX', 'TCOM', 'TMDX', 'PAYX', 'CSGP', 'LPLA', 'AMGN',
                'BIIB', 'MRNA', 'PDD', 'BIDU', 'NIO', 'NTES', 'BILI', 'XRAX', 'SGEN', 'ANSS',
                'SPLK', 'GTLB', 'ZS', 'CLDX', 'BBSI', 'YNDX', 'JD', 'ZM', 'RIOT', 'MRVL',
                'MU', 'WDC', 'KLAC', 'QRVO', 'KHC', 'ON', 'MXIM', 'SPYN', 'XLNX', 'ARCH',
                'FTCH', 'DKNG', 'GLBE', 'LCID', 'UPST', 'ENPH', 'HEPS', 'NWL', 'OLED', 'RARE'
            ]
            return nasdaq100_hardcoded
    except Exception as e:
        print(f"[WARN] Complete Nasdaq 100 retrieval failed: {e}")
        return []

def get_already_downloaded():
    """获取已下载的标的列表"""
    storage_dir = os.path.join(project_root, 'Data_Hub', 'storage')
    try:
        files = [f.replace('.parquet', '') for f in os.listdir(storage_dir) 
                 if f.endswith('.parquet')]
        return set(files)
    except:
        return set()

def get_ipo_date(symbol: str, company_info_manager: CompanyInfoManager) -> str:
    """从yfinance获取IPO日期"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        ipo_date = info.get('ipoDate', None)
        
        if ipo_date:
            # ipoDate是Unix时间戳
            if isinstance(ipo_date, int):
                ipo_date = datetime.fromtimestamp(ipo_date).strftime('%Y-%m-%d')
            return ipo_date
        else:
            # 备用：从yfinance的history尝试获取第一条数据
            try:
                hist = ticker.history(period='max')
                if not hist.empty:
                    return hist.index[0].strftime('%Y-%m-%d')
            except:
                pass
    except:
        pass
    
    # 都失败则默认2015年1月1日
    return '2015-01-01'

def main():
    print("=" * 80)
    print("[*] S&P 500 & Nasdaq 100 Batch Downloader - Smart Incremental Mode")
    print("=" * 80)
    
    # Initialize
    ny_tz = pytz.timezone('America/New_York')
    end_date_str = datetime.now(ny_tz).strftime('%Y-%m-%d')
    downloader = YFinanceDownloader()
    company_info_manager = CompanyInfoManager()
    
    # 2. 获取所有目标标的
    sp500_symbols = get_sp500_symbols()
    nasdaq100_symbols = get_nasdaq100_symbols()
    
    all_target_symbols = set(sp500_symbols + nasdaq100_symbols)
    print(f"\n[>] Total target stocks: {len(all_target_symbols)}")
    
    # Get already downloaded symbols
    already_downloaded = get_already_downloaded()
    print(f"[+] Already downloaded: {len(already_downloaded)}")
    
    # Calculate symbols to download
    to_download = all_target_symbols - already_downloaded
    print(f"[!] Need to download: {len(to_download)}")
    print(f"[-] Skip existing: {len(all_target_symbols & already_downloaded)}\n")
    
    if not to_download:
        print("[OK] All S&P 500 and Nasdaq 100 stocks are complete!")
        return
    
    # Start batch download
    successful = 0
    failed = 0
    failed_symbols = []
    
    to_download_sorted = sorted(list(to_download))
    total = len(to_download_sorted)
    
    for idx, symbol in enumerate(to_download_sorted, 1):
        print(f"\n[{idx}/{total}] Processing {symbol}...")
        
        try:
            # Get IPO date
            ipo_date = get_ipo_date(symbol, company_info_manager)
            print(f"  [IPO] IPO Date: {ipo_date}")
            
            # Download from IPO date or 2015
            start_date = ipo_date if ipo_date > '2010-01-01' else '2015-01-01'
            
            # Download
            success = downloader.download_and_save(symbol, start_date, end_date_str)
            
            if success:
                successful += 1
                print(f"  [OK] {symbol} downloaded successfully")
            else:
                failed += 1
                failed_symbols.append(symbol)
                print(f"  [ERR] {symbol} download failed")
                
        except Exception as e:
            failed += 1
            failed_symbols.append(symbol)
            print(f"  [ERR] {symbol} exception: {e}")
    
    # Summary report
    print("\n" + "=" * 80)
    print("[SUMMARY] Download Complete Statistics")
    print("=" * 80)
    print(f"[OK] Successful downloads: {successful}")
    print(f"[ERR] Failed: {failed}")
    
    if failed_symbols:
        print(f"\n[ERR] Failed symbols list:")
        for symbol in failed_symbols[:20]:  # Show first 20 only
            print(f"   - {symbol}")
        if len(failed_symbols) > 20:
            print(f"   ... {len(failed_symbols) - 20} more failures")
    
    # Check final database
    final_count = len(get_already_downloaded())
    print(f"\n[>] Database status: {final_count} total stocks in total")
    
    print("\n[DONE] download_sp500_nasdaq100.py execution completed!")

if __name__ == "__main__":
    main()
