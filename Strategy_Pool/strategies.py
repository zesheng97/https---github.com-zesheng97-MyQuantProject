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


class DivergenceStrategy:
    """
    改进版分歧交易策略（基于高星量化项目优化）
    
    核心逻辑：
    1. 趋势过滤：只在明确趋势中交易
    2. 相对波幅：要求B日波幅 > A日波幅 * 比例
    3. 成交量确认：要求成交量支持
    4. 动态止损：基于ATR计算止损距离
    5. 延迟进场：等待虚假突破失败
    """
    
    def __init__(self):
        self.name = "分歧交易策略（改进版）"
        self.description_cn = "加强版分歧交易：趋势过滤 + 相对波幅 + 成交量确认 + 动态止损。在明确趋势中，当波幅扩大但收盘反向时交易。"
        self.description_en = "Enhanced divergence: Trend filter + Relative amplitude + Volume confirmation + Dynamic stop loss. Trade when price diverges in confirmed trend."

    def backtest(self, data, params=None):
        """
        参数化回测方法
        
        Args:
            data: OHLCV DataFrame（必须包含 high, low, close, volume 列）
            params: 策略参数字典
                - trend_ma: 趋势均线 (默认20)
                - amplitude_ratio: 波幅比例要求 (默认1.3)
                - volume_ratio: 成交量比例要求 (默认1.2)
                - atr_period: ATR周期 (默认14)
                - stop_loss_atr: 止损距离倍数 (默认2.0)
                - hold_days: 持有天数 (默认5)
            
        Returns:
            包含 'signal' 和 'returns' 列的 DataFrame
        """
        
        if params is None:
            params = {}
        
        # 参数提取
        trend_ma = params.get('trend_ma', 20)
        amplitude_ratio = params.get('amplitude_ratio', 1.3)
        volume_ratio = params.get('volume_ratio', 1.2)
        atr_period = params.get('atr_period', 14)
        stop_loss_atr = params.get('stop_loss_atr', 2.0)
        hold_days = params.get('hold_days', 5)
        
        # 数据准备
        data['signal'] = 0
        data['hold_until'] = -1  # 记录持有到第几行
        data['entry_price'] = 0.0
        data['stop_loss'] = 0.0
        
        # 计算技术指标
        # 1. 趋势均线
        data['trend_ma'] = data['close'].rolling(trend_ma).mean()
        
        # 2. ATR（真实波幅平均值），用于动态止损
        data['tr'] = self._calc_true_range(data)
        data['atr'] = data['tr'].rolling(atr_period).mean()
        
        # 3. 成交量均线（20日）
        data['vol_ma'] = data['volume'].rolling(20).mean()
        
        # 4. 波幅（日最高-最低）
        data['amplitude'] = data['high'] - data['low']
        data['amplitude_ma'] = data['amplitude'].rolling(5).mean()
        
        # 交易逻辑
        for i in range(2, len(data)):  # 从第3行开始（需要前N行的MA）
            # 如果已经持有，进行止损检查
            if data.loc[data.index[i], 'hold_until'] >= 0:
                current_signal = data.loc[data.index[i], 'signal']
                current_price = data.iloc[i]['close']
                stop_loss = data.loc[data.index[i], 'stop_loss']
                
                # 做多状态下的止损
                if current_signal == 1 and current_price < stop_loss:
                    data.loc[data.index[i], 'signal'] = 0
                    data.loc[data.index[i], 'hold_until'] = -1
                # 做空状态下的止损
                elif current_signal == -1 and current_price > stop_loss:
                    data.loc[data.index[i], 'signal'] = 0
                    data.loc[data.index[i], 'hold_until'] = -1
                continue
            
            # 获取前日(A日)和当日(B日)数据
            a_high = data.iloc[i-1]['high']
            a_low = data.iloc[i-1]['low']
            a_close = data.iloc[i-1]['close']
            a_amplitude = data.iloc[i-1]['amplitude']
            a_vol = data.iloc[i-1]['volume']
            
            b_high = data.iloc[i]['high']
            b_low = data.iloc[i]['low']
            b_close = data.iloc[i]['close']
            b_amplitude = data.iloc[i]['amplitude']
            b_vol = data.iloc[i]['volume']
            
            b_trend_ma = data.iloc[i]['trend_ma']
            b_atr = data.iloc[i]['atr']
            b_vol_ma = data.iloc[i]['vol_ma']
            
            # 检查分歧条件：B日高低点幅度扩大
            if b_high <= a_high or b_low >= a_low:
                continue  # 不满足高点高、低点低的条件
            
            # ✅ 条件1：相对波幅过滤（B日波幅 > A日波幅 * 1.3）
            if b_amplitude < a_amplitude * amplitude_ratio:
                continue
            
            # ✅ 条件2：成交量确认（B日成交量 > 20日均量 * 1.2）
            if b_vol_ma == 0 or b_vol < b_vol_ma * volume_ratio:
                continue
            
            # 生成交易信号
            if b_close > a_close:
                # B日收盘 > A日收盘，说明高开但收低，反转做空信号
                # ✅ 条件3：趋势过滤（在下降趋势中做空）
                if b_close < b_trend_ma:
                    data.loc[data.index[i], 'signal'] = -1
                    data.loc[data.index[i], 'entry_price'] = b_close
                    data.loc[data.index[i], 'stop_loss'] = b_close + b_atr * stop_loss_atr
                    data.loc[data.index[i], 'hold_until'] = min(i + hold_days, len(data) - 1)
                    
            elif b_close < a_close:
                # B日收盘 < A日收盘，说明低开但收高，反转做多信号
                # ✅ 条件3：趋势过滤（在上升趋势中做多）
                if b_close > b_trend_ma:
                    data.loc[data.index[i], 'signal'] = 1
                    data.loc[data.index[i], 'entry_price'] = b_close
                    data.loc[data.index[i], 'stop_loss'] = b_close - b_atr * stop_loss_atr
                    data.loc[data.index[i], 'hold_until'] = min(i + hold_days, len(data) - 1)
        
        # 清理持有标记
        for i in range(len(data)):
            if data.iloc[i]['hold_until'] >= 0 and i > data.iloc[i]['hold_until']:
                data.loc[data.index[i], 'signal'] = 0
        
        # 计算日收益率
        data['returns'] = data['signal'].shift(1) * data['close'].pct_change()
        
        # 清理临时列
        data.drop(['tr', 'hold_until', 'entry_price', 'stop_loss'], axis=1, inplace=True)
        
        return data
    
    def _calc_true_range(self, data):
        """计算真实波幅（True Range）"""
        tr = []
        for i in range(len(data)):
            if i == 0:
                tr.append(data.iloc[i]['high'] - data.iloc[i]['low'])
            else:
                high_low = data.iloc[i]['high'] - data.iloc[i]['low']
                high_close = abs(data.iloc[i]['high'] - data.iloc[i-1]['close'])
                low_close = abs(data.iloc[i]['low'] - data.iloc[i-1]['close'])
                tr.append(max(high_low, high_close, low_close))
        return tr

# --- 注册所有策略 ---
STRATEGIES = [
    MovingAverageCrossStrategy(),
    DivergenceStrategy()
]