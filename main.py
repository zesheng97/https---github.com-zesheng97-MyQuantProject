# 文件位置: main.py (项目根目录)
from Data_Hub.fetchers.yf_downloader import YFinanceDownloader
from datetime import datetime
import pytz

def main():
    print("🚀 中低频量化回测框架启动...\n")
    
    # 1. 精准时间戳处理：锁定纳斯达克所在的北美东部时间
    ny_tz = pytz.timezone('America/New_York')
    # 动态获取美东时间的今天作为截止日期
    end_date_str = datetime.now(ny_tz).strftime('%Y-%m-%d')
    start_date_str = '2020-01-01' # 起始时间依然可以设定为一个固定锚点，或设为 end_date 往前推 N 年
    
    print(f"🕒 设定数据区间: {start_date_str} 至 {end_date_str} (美东时间)")
    
    # 2. 初始化下载器
    downloader = YFinanceDownloader()
    
    # 3. 批量下载测试标的
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 
                    'TSLA', 'NVDA', 'INTC', 'CSCO', 'ADBE', 'PYPL', 'NFLX', 
                    'CRM', 'ORCL', 'IBM', 'QCOM', 'AVGO', 'TXN', 'AMD', 'INTU', 'AMAT', 
                    'SBUX', 'GILD', 'FISV', 'BKNG', 'ADP', 
                    'LRCX', 'MU', 'MDLZ', 'ISRG', 'AAOI', 'CTAS', 'ANSS', 'CDNS', 'MCHP', 'WBA',
                    'VRTX', 'ALGN', 'ASML', 'KHC', 'BIIB', 'EXC', 'EA', 'SNPS', 'LULU', 'ROST', 
                    'MAR', 'SIRI', 'DLTR', 'EBAY', 'JD', 'BIDU', 'PDD', 'TME']
    
    for symbol in test_symbols:
        downloader.download_and_save(symbol, start_date_str, end_date_str)
        
    print("\n🎉 第一阶段：数据采集与标准化模块 测试完成！")

if __name__ == "__main__":
    main()