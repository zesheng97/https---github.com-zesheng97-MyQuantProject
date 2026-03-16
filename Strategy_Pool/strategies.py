# --- 策略池入口 ---
from Strategy_Pool.adapters import *
from Strategy_Pool.base import *
from Strategy_Pool.custom import *

# 确保导入 MovingAverageCrossStrategy
class MovingAverageCrossStrategy:
    def __init__(self):
        self.name = "均线交叉策略"
        self.description_cn = "当短期均线向上穿越长期均线时买入，反之卖出。"
        self.description_en = "Buy when the short-term moving average crosses above the long-term moving average, and sell when it crosses below."

    def backtest(self, data, params=None):
        """
        参数化回测方法
        
        Args:
            data: OHLCV DataFrame
            params: 策略参数字典 {'ma_short': 20, 'ma_long': 60}
            
        Returns:
            包含 'signal' 列的 DataFrame
        """
        
        # 使用传入的参数，或默认值
        if params is None:
            params = {}
        
        ma_short = params.get('ma_short', 20)
        ma_long = params.get('ma_long', 60)
        
        # 计算均线
        data['sma_short'] = data['close'].rolling(ma_short).mean()
        data['sma_long'] = data['close'].rolling(ma_long).mean()
        
        # 生成交易信号：1=多头, -1=空头, 0=持币
        data['signal'] = 0
        data.loc[data['sma_short'] > data['sma_long'], 'signal'] = 1
        data.loc[data['sma_short'] <= data['sma_long'], 'signal'] = -1
        
        # 计算日收益率（策略收益）
        data['returns'] = data['signal'].shift(1) * data['close'].pct_change()
        
        return data

# --- 注册所有策略 ---
STRATEGIES = [
    MovingAverageCrossStrategy()
]