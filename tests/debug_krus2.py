import yfinance as yf
import pandas as pd
from Strategy_Pool.strategies import BollingerBandsStrategy

# 下载KRUS数据
krus = yf.download('KRUS', start='2020-01-01', end='2024-01-01', progress=False)
krus.columns = ['open', 'high', 'low', 'close', 'volume']
krus = krus.dropna()

# 运行Bollinger Bands策略
strategy = BollingerBandsStrategy()
result = strategy.backtest(krus, {'boll_period': 20, 'boll_std': 2, 'buy_ratio': 0.8})

# 显示4月份的布林带数据
print("="*120)
print("2023年4月布林带完整数据:")
print("="*120)
april_data = result.loc['2023-04'][['open', 'close', 'sma', 'lower_band', 'upper_band', 'signal']]
for idx, row in april_data.iterrows():
    date_str = idx.strftime('%Y-%m-%d')
    signal_str = "买入" if row['signal'] == 1 else ("卖出" if row['signal'] == -1 else "无")
    print(f"{date_str}: 收盘=${row['close']:7.2f} | 下轨=${row['lower_band']:7.2f} | 中轨=${row['sma']:7.2f} | 上轨=${row['upper_band']:7.2f} | 信号=[{signal_str}]")

print("\n" + "="*120)
print("交易信号分析:")
print("="*120)
signals = result[result['signal'] != 0]
for i, (idx, row) in enumerate(signals.iterrows(), 1):
    date_str = idx.strftime('%Y-%m-%d')
    action = "买入" if row['signal'] == 1 else "卖出"
    print(f"{i}. {date_str} {action}: 收盘=${row['close']:.2f} | 下轨=${row['lower_band']:.2f} | 中轨=${row['sma']:.2f} | 上轨=${row['upper_band']:.2f}")
    
    if row['signal'] == 1:
        check = f"< 下轨? {row['close']:.2f} < {row['lower_band']:.2f} = {row['close'] < row['lower_band']}"
    else:
        check = f"> 上轨? {row['close']:.2f} > {row['upper_band']:.2f} = {row['close'] > row['upper_band']}"
    print(f"   验证: {check}")
    print()
