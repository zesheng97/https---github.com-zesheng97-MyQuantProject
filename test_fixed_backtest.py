import yfinance as yf
import pandas as pd
from Strategy_Pool.strategies import BollingerBandsStrategy
from Engine_Matrix.backtest_engine import BacktestEngine, BacktestConfig

# 下载KRUS数据
krus = yf.download('KRUS', start='2023-01-01', end='2023-05-01', progress=False)
krus.columns = ['open', 'high', 'low', 'close', 'volume']
krus = krus.dropna()

# 运行完整回测（使用修复后的backtest_engine）
config = BacktestConfig(
    symbol='KRUS',
    start_date='2023-01-03',
    end_date='2023-04-28',
    initial_capital=10000.0,
    strategy_params={'boll_period': 20, 'boll_std': 2, 'buy_ratio': 0.8}
)

engine = BacktestEngine(BollingerBandsStrategy())
result = engine.run(config)

print("="*120)
print("修复后的交易记录:")
print("="*120)
if not result.trades.empty:
    for idx, trade in result.trades.iterrows():
        print(f"{trade['date'].strftime('%Y-%m-%d')} {trade['action']:4s}: 价格=${trade['price']:.2f}, 股数={trade['shares']}")
else:
    print("无交易")

print("\n" + "="*120)
print("对应日期的布林带指标:")
print("="*120)
april_data = result.raw_data.loc['2023-04'][['close', 'sma', 'lower_band', 'upper_band', 'signal']]
for idx, row in april_data.iterrows():
    date_str = idx.strftime('%Y-%m-%d')
    signal_str = "买入" if row['signal'] == 1 else ("卖出" if row['signal'] == -1 else "无")
    print(f"{date_str}: 收盘=${row['close']:7.2f} | 下轨=${row['lower_band']:7.2f} | 中轨=${row['sma']:7.2f} | 上轨=${row['upper_band']:7.2f} | 信号=[{signal_str}]")
