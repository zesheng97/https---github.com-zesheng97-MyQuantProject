import yfinance as yf
import pandas as pd
from Strategy_Pool.strategies import BollingerBandsStrategy

# 下载KRUS数据（从2020年开始，获得更完整的历史数据）
krus = yf.download('KRUS', start='2020-01-01', end='2024-01-01', progress=False)
krus.columns = ['open', 'high', 'low', 'close', 'volume']
krus = krus.dropna()

print("原始日期数（验证是否有缺失）:")
print(f"总共有 {len(krus)} 条数据")
print(f"日期范围: {krus.index[0].strftime('%Y-%m-%d')} 到 {krus.index[-1].strftime('%Y-%m-%d')}")
print("\n2023年4月的所有数据:")
print(krus.loc['2023-04'][['open', 'high', 'low', 'close', 'volume']])
print("\n")

# 运行Bollinger Bands策略
strategy = BollingerBandsStrategy()
result = strategy.backtest(krus, {'boll_period': 20, 'boll_std': 2, 'buy_ratio': 0.8})

# 显示关键日期的详细信息
print("布林带指标 - 2023年4月:")
cols = ['close', 'sma', 'lower_band', 'upper_band', 'signal']
print(result.loc['2023-04-01':'2023-04-15'][cols])
print("\n")

# 找出第一次买入和卖出
signals = result[result['signal'] != 0].copy()
print("所有交易信号：")
for idx, row in signals.iterrows():
    action = "买入" if row['signal'] == 1 else "卖出"
    print(f"{idx.strftime('%Y-%m-%d')} {action}: 价格=${row['close']:.2f}, 下轨=${row['lower_band']:.2f}, 中轨=${row['sma']:.2f}, 上轨=${row['upper_band']:.2f}")

print("\n" + "="*100 + "\n")

if len(signals) >= 2:
    buy_signal = signals[signals['signal'] == 1].iloc[0]
    sell_signals = signals[signals['signal'] == -1]
    
    print("第一次买入信号:")
    print(f"日期: {buy_signal.name.strftime('%Y-%m-%d')}")
    print(f"收盘价: ${buy_signal['close']:.2f}")
    print(f"下轨: ${buy_signal['lower_band']:.2f}")
    print(f"中轨: ${buy_signal['sma']:.2f}")
    print(f"上轨: ${buy_signal['upper_band']:.2f}")
    print(f"价格 < 下轨? {buy_signal['close']:.2f} < {buy_signal['lower_band']:.2f} = {buy_signal['close'] < buy_signal['lower_band']}")
    print()
    
    if len(sell_signals) > 0:
        sell_signal = sell_signals.iloc[0]
        print("第一次卖出信号:")
        print(f"日期: {sell_signal.name.strftime('%Y-%m-%d')}")
        print(f"收盘价: ${sell_signal['close']:.2f}")
        print(f"下轨: ${sell_signal['lower_band']:.2f}")
        print(f"中轨: ${sell_signal['sma']:.2f}")
        print(f"上轨: ${sell_signal['upper_band']:.2f}")
        print(f"价格 > 上轨? {sell_signal['close']:.2f} > {sell_signal['upper_band']:.2f} = {sell_signal['close'] > sell_signal['upper_band']}")
        if not (sell_signal['close'] > sell_signal['upper_band']):
            print(f"❌ ERROR: 价格没有超过上轨！")

