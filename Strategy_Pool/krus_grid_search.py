import pandas as pd
import numpy as np
import yfinance as yf
from Strategy_Pool.strategies import BollingerBandsStrategy
from Core_Bus.standard import standardize_ohlcv

# 下载并备份KRUS数据
symbol = 'KRUS'
start_date = '2019-01-01'
end_date = '2026-03-19'
raw_df = yf.download(symbol, start=start_date, end=end_date, auto_adjust=True, threads=False)
data = standardize_ohlcv(raw_df)
data = data.dropna()

# 参数空间
boll_periods = np.arange(10, 51, 5)         # 10, 15, ..., 50
boll_stds = np.arange(1.0, 3.1, 0.5)       # 1.0, 1.5, ..., 3.0
extreme_periods = np.arange(10, 51, 5)     # 高低点参考周期
ma_periods = np.arange(10, 101, 10)        # 趋势确认MA周期

results = []

for bp in boll_periods:
    for bs in boll_stds:
        for ep in extreme_periods:
            for mp in ma_periods:
                # 策略逻辑：结合布林带、极值、趋势
                df = data.copy()
                df['sma'] = df['close'].rolling(bp).mean()
                df['std'] = df['close'].rolling(bp).std()
                df['upper_band'] = df['sma'] + bs * df['std']
                df['lower_band'] = df['sma'] - bs * df['std']
                df['ma_trend'] = df['close'].rolling(mp).mean()
                df['min_extreme'] = df['close'].rolling(ep).min()
                df['max_extreme'] = df['close'].rolling(ep).max()
                df['signal'] = 0
                is_holding = False
                for i in range(max(bp, ep, mp), len(df)):
                    close = df.iloc[i]['close']
                    lower = df.iloc[i]['lower_band']
                    upper = df.iloc[i]['upper_band']
                    min_ext = df.iloc[i]['min_extreme']
                    max_ext = df.iloc[i]['max_extreme']
                    trend = df.iloc[i]['ma_trend']
                    # 买入：收盘价等于极小值且在下轨附近，且趋势向上
                    if not is_holding and close <= min_ext + 1e-3 and close < lower and close > 0.95 * min_ext and close > 0 and trend > lower:
                        df.loc[df.index[i], 'signal'] = 1
                        is_holding = True
                    # 卖出：收盘价等于极大值且在上轨附近，且趋势向下
                    elif is_holding and close >= max_ext - 1e-3 and close > upper and close < 1.05 * max_ext and trend < upper:
                        df.loc[df.index[i], 'signal'] = -1
                        is_holding = False
                df['returns'] = df['signal'].shift(1).fillna(0) * df['close'].pct_change()
                equity = 30000 * (1 + df['returns']).cumprod()
                total_return = (equity.iloc[-1] - 30000) / 30000
                win_trades = df[df['signal'] == 1]['returns'] > 0
                win_rate = win_trades.sum() / max(1, len(df[df['signal'] == 1]))
                results.append({
                    'boll_period': bp,
                    'boll_std': bs,
                    'extreme_period': ep,
                    'ma_period': mp,
                    'total_return': total_return,
                    'win_rate': win_rate
                })

# 汇总结果
results_df = pd.DataFrame(results)
best_return = results_df.sort_values('total_return', ascending=False).iloc[0]
best_win = results_df.sort_values('win_rate', ascending=False).iloc[0]
print("最佳收益率参数:")
print(best_return)
print("\n最高胜率参数:")
print(best_win)
results_df.to_csv('krus_grid_search_results.csv', index=False)
print("\n全部结果已保存到 krus_grid_search_results.csv")
