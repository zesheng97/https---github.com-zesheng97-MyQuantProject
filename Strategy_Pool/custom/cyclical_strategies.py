"""
文件位置: Strategy_Pool/strategies.py (补充) - 周期性策略
描述: 基于周期性特征的交易策略
功能: 利用FFT/小波检测的周期信息进行智能交易
"""

import numpy as np
import pandas as pd
from scipy import signal, fft
from datetime import datetime

class CyclicalTrendStrategy:
    """
    周期性趋势交易策略
    
    核心逻辑：
    1. 检测价格周期
    2. 识别周期的高点和低点
    3. 在预期低点买入，预期高点卖出
    4. 支持自适应止损
    """
    
    def __init__(self):
        self.name = "周期性趋势交易策略"
        self.description_cn = "基于FFT周期检测的趋势跟踪策略。在周期低点买入，周期高点卖出，自适应风险管理。"
        self.description_en = "Cyclical trend strategy using FFT period detection. Buy at cycle lows, sell at cycle highs with adaptive risk management."
    
    def backtest(self, data, params=None):
        """
        参数化回测
        
        Args:
            data: OHLCV DataFrame
            params: {
                'min_period': 最短周期(天),
                'max_period': 最长周期(天),
                'signal_strength': 信号强度阈值(0-1),
                'position_size': 头寸规模(0-1),
                'atr_stop_loss': ATR止损倍数
            }
            
        Returns:
            带signal列的DataFrame
        """
        
        if params is None:
            params = {}
        
        min_period = params.get('min_period', 5)
        max_period = params.get('max_period', 60)
        signal_strength = params.get('signal_strength', 0.5)
        position_size = params.get('position_size', 1.0)
        atr_stop_loss = params.get('atr_stop_loss', 2.0)
        
        data = data.copy()
        close = data['close'].values
        high = data['high'].values
        low = data['low'].values
        
        # 1. 计算ATR用于止损
        data['tr'] = np.maximum(
            np.maximum(high - low, np.abs(high - np.roll(close, 1))),
            np.abs(low - np.roll(close, 1))
        )
        data['atr'] = data['tr'].rolling(14).mean()
        
        # 2. 周期检测（FFT）
        n = len(close)
        if n < max_period * 2:
            data['signal'] = 0
            data['returns'] = data['close'].pct_change()
            return data
        
        try:
            # FFT分析
            fft_vals = np.abs(fft.fft(close - close.mean()))
            fft_vals = fft_vals[:n // 2]
            
            # 找主周期
            if len(fft_vals) > 1:
                fft_vals[0] = 0
                candidates_freq = []
                for freq_idx in range(1, len(fft_vals)):
                    period = n / (freq_idx + 1)
                    if min_period <= period <= max_period:
                        candidates_freq.append((freq_idx, period, fft_vals[freq_idx]))
                
                if candidates_freq:
                    # 选择能量最高的周期
                    best_freq_idx, dominant_period, peak_power = max(candidates_freq, key=lambda x: x[2])
                else:
                    dominant_period = (min_period + max_period) / 2
            else:
                dominant_period = (min_period + max_period) / 2
            
            dominant_period = int(max(dominant_period, min_period))
            
        except:
            dominant_period = int((min_period + max_period) / 2)
        
        # 3. 周期内的相对位置（0-1表示周期中的进度）
        day_in_cycle = np.arange(n) % dominant_period
        cycle_progress = day_in_cycle / dominant_period
        
        # 4. 局部最低点和最高点检测
        window = max(int(dominant_period / 4), 3)
        
        local_max = signal.argrelextrema(close, np.greater, order=window)[0]
        local_min = signal.argrelextrema(close, np.less, order=window)[0]
        
        # 5. 生成交易信号
        signal_array = np.zeros(n)
        
        for i in range(window, n):
            # 在本周期的前25%（接近低点时）
            if 0.0 <= cycle_progress[i] < 0.25:
                # 检查是否确实是本地最低点
                recent_min_idx = local_min[(local_min >= i - window) & (local_min <= i)]
                if len(recent_min_idx) > 0:
                    signal_array[i] = 1  # 买入信号
            
            # 在本周期的75-100%（接近高点时）
            elif 0.75 <= cycle_progress[i] <= 1.0:
                # 检查是否确实是本地最高点
                recent_max_idx = local_max[(local_max >= i - window) & (local_max <= i)]
                if len(recent_max_idx) > 0:
                    signal_array[i] = -1  # 卖出信号
        
        data['signal'] = signal_array
        data['returns'] = data['signal'].shift(1) * data['close'].pct_change()
        
        return data


class CyclicalMeanReversionStrategy:
    """
    周期性均值回归策略
    
    核心逻辑：
    1. 识别周期性运动
    2. 当价格偏离周期中线时进行交易
    3. 期望回归到周期中线
    """
    
    def __init__(self):
        self.name = "周期性均值回归策略"
        self.description_cn = "基于周期性特征的均值回归。在周期内价格超买时卖出，超卖时买入。"
        self.description_en = "Mean reversion strategy using cyclical features. Sell when overbought in cycle, buy when oversold."
    
    def backtest(self, data, params=None):
        """
        参数化回测
        
        Args:
            data: OHLCV DataFrame
            params: {
                'period': 周期长度(天),
                'zscore_threshold': Z-score阈值(超买超卖判定),
                'lookback': 回看窗口
            }
        """
        
        if params is None:
            params = {}
        
        period = params.get('period', 30)
        zscore_threshold = params.get('zscore_threshold', 1.5)
        lookback = params.get('lookback', 60)
        
        data = data.copy()
        close = data['close'].values
        
        # 1. 计算周期性成分（使用简单的高通滤波）
        # 移除低频趋势，保留高频周期
        try:
            # Detrend
            x = np.arange(len(close))
            z = np.polyfit(x, close, 2)
            p = np.poly1d(z)
            trend = p(x)
            detrended = close - trend
            
            # 周期性分量 = 局部平均和当前值的差
            rolling_mean = pd.Series(detrended).rolling(period).mean().values
            cyclical = detrended - rolling_mean
            
            # 2. 计算Z-score
            rolling_std = pd.Series(cyclical).rolling(period).std().values
            z_scores = np.zeros(len(cyclical))
            
            for i in range(lookback, len(cyclical)):
                if rolling_std[i] > 0:
                    z_scores[i] = cyclical[i] / rolling_std[i]
            
            # 3. 生成信号
            signal_array = np.zeros(len(close))
            for i in range(lookback, len(close)):
                if z_scores[i] < -zscore_threshold:  # 超卖
                    signal_array[i] = 1  # 买入
                elif z_scores[i] > zscore_threshold:  # 超买
                    signal_array[i] = -1  # 卖出
            
            data['signal'] = signal_array
            
        except:
            data['signal'] = 0
        
        data['returns'] = data['signal'].shift(1) * data['close'].pct_change()
        
        return data


class CyclicalPhaseAlignmentStrategy:
    """
    周期相位对齐策略
    
    核心逻辑：
    1. 识别主周期
    2. 计算当前相位
    3. 在特定相位时交易（例如上升沿）
    4. 避免在下降沿交易
    """
    
    def __init__(self):
        self.name = "周期相位对齐策略"
        self.description_cn = "基于周期相位的精准交易。在周期上升沿买入，下降沿卖出。"
        self.description_en = "Phase-aligned cyclical trading. Buy on rising phase, sell on falling phase."
    
    def backtest(self, data, params=None):
        """
        参数化回测
        
        Args:
            data: OHLCV DataFrame
            params: {
                'period': 主周期(天),
                'phase_buy_start': 买入相位起点(0-1),
                'phase_buy_end': 买入相位终点,
                'min_reversion': 最小回归系数
            }
        """
        
        if params is None:
            params = {}
        
        period = params.get('period', 30)
        phase_buy_start = params.get('phase_buy_start', 0.0)
        phase_buy_end = params.get('phase_buy_end', 0.3)
        min_reversion = params.get('min_reversion', 0.5)
        
        data = data.copy()
        close = data['close'].values
        n = len(close)
        
        if n < period * 2:
            data['signal'] = 0
            data['returns'] = data['close'].pct_change()
            return data
        
        # 1. 计算周期成分
        try:
            fft_vals = np.abs(fft.fft(close - close.mean()))
            fft_vals[:n // 2]
            
            # 简化：假设检测到的周期
            detected_period = period
            
        except:
            detected_period = period
        
        # 2. 计算每个时间点的相位
        phase = (np.arange(n) % detected_period) / detected_period
        
        # 3. 计算价格相对于周期均值的偏离
        price_rel = np.zeros(n)
        for i in range(n):
            start_idx = max(0, i - detected_period)
            end_idx = min(n, i + 1)
            local_mean = np.mean(close[start_idx:end_idx])
            price_rel[i] = (close[i] - local_mean) / (local_mean + 1e-8)
        
        # 4. 相位微分（速度）
        phase_velocity = np.gradient(phase)
        
        # 5. 生成信号
        signal_array = np.zeros(n)
        
        for i in range(detected_period, n):
            # 在买入相位且价格偏低时买入
            if phase_buy_start <= phase[i] <= phase_buy_end:
                if price_rel[i] < -min_reversion and phase_velocity[i] > 0:
                    signal_array[i] = 1
            
            # 在卖出相位且价格偏高时卖出
            elif (0.6 <= phase[i] <= 0.9) or (phase[i] < 0.1 and i > 0 and phase[i-1] > 0.9):
                if price_rel[i] > min_reversion and phase_velocity[i] < 0:
                    signal_array[i] = -1
        
        data['signal'] = signal_array
        data['returns'] = data['signal'].shift(1) * data['close'].pct_change()
        
        return data
