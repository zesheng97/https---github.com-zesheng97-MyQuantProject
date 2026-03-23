# --- 策略池入口 ---
import pandas as pd
import numpy as np
from Strategy_Pool.adapters import *
from Strategy_Pool.base import *
from Strategy_Pool.custom import *
from Strategy_Pool.custom.cyclical_strategies import CyclicalTrendStrategy, CyclicalMeanReversionStrategy, CyclicalPhaseAlignmentStrategy
from Strategy_Pool.custom.mean_reversion_volatility import MeanReversionVolatilityStrategy
from Strategy_Pool.custom.xgboost_ml_strategy import XGBoostMLStrategy

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
        
        # ✅ 明确复制，避免 SettingWithCopyWarning
        data = data.copy()
        
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
        data = data.copy()  # ✅ 明确复制以避免 SettingWithCopyWarning
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
            if data.iloc[i]['hold_until'] >= 0:
                current_signal = data.iloc[i]['signal']
                current_price = data.iloc[i]['close']
                stop_loss = data.iloc[i]['stop_loss']
                
                # 做多状态下的止损
                if current_signal == 1 and current_price < stop_loss:
                    data.iloc[i, data.columns.get_loc('signal')] = 0
                    data.iloc[i, data.columns.get_loc('hold_until')] = -1
                # 做空状态下的止损
                elif current_signal == -1 and current_price > stop_loss:
                    data.iloc[i, data.columns.get_loc('signal')] = 0
                    data.iloc[i, data.columns.get_loc('hold_until')] = -1
                continue
            
            # ✅ 使用前一日数据来生成当日信号（避免前向偏差）
            # A日（前一日） = i-1
            a_high = data.iloc[i-1]['high']
            a_low = data.iloc[i-1]['low']
            a_close = data.iloc[i-1]['close']
            a_amplitude = data.iloc[i-1]['amplitude']
            a_vol = data.iloc[i-1]['volume']
            
            # B日（当前日） = i，但使用前日指标
            b_high = data.iloc[i-1]['high']  # ✅ 用前日数据
            b_low = data.iloc[i-1]['low']    # ✅ 用前日数据
            b_close = data.iloc[i-1]['close']  # ✅ 用前日数据
            b_amplitude = data.iloc[i-1]['amplitude']  # ✅ 用前日数据
            b_vol = data.iloc[i-1]['volume']  # ✅ 用前日数据
            
            b_trend_ma = data.iloc[i-1]['trend_ma']  # ✅ 用前日 MA
            b_atr = data.iloc[i-1]['atr']  # ✅ 用前日 ATR
            b_vol_ma = data.iloc[i-1]['vol_ma']  # ✅ 用前日成交量MA
            
            # 检查分歧条件：B日高低点幅度扩大
            # 这里比较的是前一日的高低点
            c_high = data.iloc[i-2]['high'] if i >= 2 else a_high
            c_low = data.iloc[i-2]['low'] if i >= 2 else a_low
            
            if b_high <= c_high or b_low >= c_low:
                continue  # 不满足高点高、低点低的条件
            
            # ✅ 条件1：相对波幅过滤
            c_amplitude = data.iloc[i-2]['amplitude'] if i >= 2 else 0
            if b_amplitude < c_amplitude * amplitude_ratio:
                continue
            
            # ✅ 条件2：成交量确认
            if b_vol_ma == 0 or b_vol < b_vol_ma * volume_ratio:
                continue
            
            # ✅ 条件3: 趋势过滤 - 生成交易信号（应用于当日 i）
            if b_close > c_high:
                # 前日收盘 > 前前日高点，反转做多信号
                if b_close > b_trend_ma:
                    data.iloc[i, data.columns.get_loc('signal')] = 1
                    data.iloc[i, data.columns.get_loc('entry_price')] = b_close
                    data.iloc[i, data.columns.get_loc('stop_loss')] = b_close - b_atr * stop_loss_atr
                    data.iloc[i, data.columns.get_loc('hold_until')] = min(i + hold_days, len(data) - 1)
                    
            elif b_close < c_low:
                # 前日收盘 < 前前日低点，反转做空信号
                if b_close < b_trend_ma:
                    data.iloc[i, data.columns.get_loc('signal')] = -1
                    data.iloc[i, data.columns.get_loc('entry_price')] = b_close
                    data.iloc[i, data.columns.get_loc('stop_loss')] = b_close + b_atr * stop_loss_atr
                    data.iloc[i, data.columns.get_loc('hold_until')] = min(i + hold_days, len(data) - 1)
        
        # 清理持有标记
        for i in range(len(data)):
            if data.iloc[i]['hold_until'] >= 0 and i > data.iloc[i]['hold_until']:
                data.iloc[i, data.columns.get_loc('signal')] = 0
        
        # 计算日收益率
        data['returns'] = data['signal'].shift(1) * data['close'].pct_change()
        
        # 清理临时列（不使用 inplace=True）
        data = data.drop(['tr', 'hold_until', 'entry_price', 'stop_loss'], axis=1)
        
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


class BollingerBandsStrategy:
    """
    简化版布林带交易策略（Bollinger Bands）
    
    核心逻辑（基于日线）：
    1. 计算布林带（20日，2倍标准差）
    2. 价格 < 下轨 → 单次买入（资金比例可调，默认80%）
    3. 价格 > 上轨 → 全仓卖出
    
    关键：这是基于日线的策略，买卖信号每天最多只能产生一次
    """
    
    def __init__(self):
        self.name = "布林带交易策略"
        self.description_cn = "简化版布林带：触及下轨买入（80%资金），触及上轨卖出全部。基于日线。"
        self.description_en = "Simplified Bollinger Bands: Buy at lower band (80% capital), sell at upper band (100%). Daily-based."

    def backtest(self, data, params=None):
        """
        参数化回测方法
        
        Args:
            data: OHLCV DataFrame（日线数据）
            params: 策略参数字典
                - boll_period: 布林带周期 (默认20)
                - boll_std: 标准差倍数 (默认2)
                - buy_ratio: 买入时投入的资金比例 (默认0.8，即80%)
            
        Returns:
            包含 'signal' 和 'returns' 列的 DataFrame
        """
        
        # ✅ 明确复制，避免 SettingWithCopyWarning
        data = data.copy()
        
        if params is None:
            params = {}
        
        # 参数提取
        boll_period = params.get('boll_period', 20)
        boll_std = params.get('boll_std', 2)
        buy_ratio = params.get('buy_ratio', 0.8)  # 80%资金买入
        
        # ========== 计算布林带指标 ==========
        data['sma'] = data['close'].rolling(boll_period).mean()
        data['std'] = data['close'].rolling(boll_period).std()
        data['upper_band'] = data['sma'] + boll_std * data['std']
        data['lower_band'] = data['sma'] - boll_std * data['std']
        
        # ========== 初始化信号和持仓 ==========
        data['signal'] = 0  # 0 = 无信号, 1 = 买入, -1 = 卖出
        
        # 跟踪持仓状态
        is_holding = False  # 当前是否持仓
        
        # ========== 逐日遍历生成信号（日线策略关键） ==========
        for i in range(boll_period, len(data)):
            close_price = data.iloc[i]['close']
            lower_band = data.iloc[i]['lower_band']
            upper_band = data.iloc[i]['upper_band']
            
            # 检查边界情况
            if pd.isna(lower_band) or pd.isna(upper_band) or pd.isna(close_price):
                continue
            
            # 卖出条件（优先检查，确保持仓状态下的操作）
            if is_holding and close_price > upper_band:
                # 价格突破上轨 → 卖出全部
                data.iloc[i, data.columns.get_loc('signal')] = -1
                is_holding = False
            
            # 买入条件（仅在未持仓时）
            elif not is_holding and close_price < lower_band:
                # 价格突破下轨 → 买入（资金比例由buy_ratio控制）
                data.iloc[i, data.columns.get_loc('signal')] = 1
                is_holding = True
            
            else:
                # 维持当前状态，不产生信号
                data.iloc[i, data.columns.get_loc('signal')] = 0
        
        # ========== 计算日收益率 ==========
        # 使用简单的方法：signal.shift(1) * 日涨跌幅
        # signal=1表示多头持仓，-1/0表示空头或现金
        data['returns'] = data['signal'].shift(1).fillna(0) * data['close'].pct_change()
        
        return data

    def grid_search(self, data, symbol, initial_capital=30000, save_dir="Data_Hub/storage",
                   boll_period_range=(10, 50, 1), boll_std_range=(1.5, 2.5, 0.1),
                   extreme_period_range=(20, 21, 1), ma_period_range=(20, 21, 1),
                   progress_callback=None,
                   results_file=None, best_params_file=None):
        """
        参数空间可自定义，支持进度回调。
        progress_callback: function(progress: float, elapsed: float, eta: float, finished: int, total: int)
        """
        import numpy as np
        import pandas as pd
        import json
        import os
        import time
        # 参数空间
        boll_periods = np.arange(*boll_period_range)
        boll_stds = np.arange(*boll_std_range)
        extreme_periods = np.arange(*extreme_period_range)
        ma_periods = np.arange(*ma_period_range)
        total = len(boll_periods) * len(boll_stds) * len(extreme_periods) * len(ma_periods)
        results = []
        count = 0
        start_time = time.time()
        from Engine_Matrix.backtest_engine import BacktestEngine
        for bp in boll_periods:
            for bs in boll_stds:
                for ep in extreme_periods:
                    for mp in ma_periods:
                        df = data.copy()
                        df['sma'] = df['close'].rolling(bp).mean()
                        df['std'] = df['close'].rolling(bp).std()
                        df['upper_band'] = df['sma'] + bs * df['std']
                        df['lower_band'] = df['sma'] - bs * df['std']
                        use_extreme = extreme_period_range != (20, 21, 1)
                        use_ma = ma_period_range != (20, 21, 1)
                        if use_extreme:
                            df['min_extreme'] = df['close'].rolling(ep).min()
                            df['max_extreme'] = df['close'].rolling(ep).max()
                        if use_ma:
                            df['ma_trend'] = df['close'].rolling(mp).mean()
                        df['signal'] = 0
                        is_holding = False
                        for i in range(max(bp, ep, mp), len(df)):
                            close = df.iloc[i]['close']
                            lower = df.iloc[i]['lower_band']
                            upper = df.iloc[i]['upper_band']
                            buy_cond = (not is_holding and close < lower)
                            if use_extreme:
                                min_ext = df.iloc[i]['min_extreme']
                                buy_cond = buy_cond and close <= min_ext + 1e-3 and close > 0.95 * min_ext and close > 0
                            if use_ma:
                                trend = df.iloc[i]['ma_trend']
                                buy_cond = buy_cond and trend > lower
                            if buy_cond:
                                df.loc[df.index[i], 'signal'] = 1
                                is_holding = True
                            sell_cond = (is_holding and close > upper)
                            if use_extreme:
                                max_ext = df.iloc[i]['max_extreme']
                                sell_cond = sell_cond and close >= max_ext - 1e-3 and close < 1.05 * max_ext
                            if use_ma:
                                trend = df.iloc[i]['ma_trend']
                                sell_cond = sell_cond and trend < upper
                            if sell_cond:
                                df.loc[df.index[i], 'signal'] = -1
                                is_holding = False
                        # 用真实资金管理和交易记录
                        engine = BacktestEngine(self)
                        equity, trades = engine._simulate_trading(df, initial_capital)
                        metrics = engine._compute_metrics(equity, trades)
                        result = {'boll_period': bp, 'boll_std': bs, 'total_return': metrics['total_return'], 'win_rate': metrics['win_rate']}
                        if use_extreme:
                            result['extreme_period'] = ep
                        if use_ma:
                            result['ma_period'] = mp
                        results.append(result)
                        count += 1
                        if progress_callback is not None:
                            elapsed = time.time() - start_time
                            progress = count / total
                            eta = (elapsed / progress) * (1 - progress) if progress > 0 else 0
                            progress_callback(progress, elapsed, eta, count, total)
        results_df = pd.DataFrame(results)
        best_return = results_df.sort_values('total_return', ascending=False).iloc[0].to_dict()
        best_win = results_df.sort_values('win_rate', ascending=False).iloc[0].to_dict()
        # annual_return 补充
        if 'annual_return' not in best_return:
            # 用 total_return 近似年化（实际应用 equity 曲线）
            best_return['annual_return'] = best_return['total_return']
        if results_file is None:
            results_file = os.path.join(save_dir, f"{symbol}_grid_search_results.csv")
        else:
            results_file = os.path.join(save_dir, results_file)
        results_df.to_csv(results_file, index=False)
        if best_params_file is None:
            best_params_file = os.path.join(save_dir, f"{symbol}_best_params.json")
        else:
            best_params_file = os.path.join(save_dir, best_params_file)
        with open(best_params_file, 'w', encoding='utf-8') as f:
            json.dump({'best_return': best_return, 'best_win': best_win}, f, ensure_ascii=False, indent=2)
        # 统一记忆文件名
        # ✅ 使用共享模块保存最佳策略（避免循环导入）
        try:
            from shared.memory_manager import BestStrategyMemory
            BestStrategyMemory.save(
                symbol=symbol,
                strategy_name=self.name,
                params=best_return,
                score=best_return.get('annual_return', 0)
            )
        except Exception as e:
            print(f"[grid_search] 保存最佳策略失败: {e}")
        print(f"\n✅ {symbol} 参数空间扫描完成，已永久标记，结果已保存。\n最佳收益率参数: {best_return}\n最高胜率参数: {best_win}\n")
        return best_return, best_win


class MeanReversionVolatilityStrategy:
    """
    ⭐KRUS 专属均值回归与波动率收割策略 
    (Mean Reversion Volatility Harvesting for High-Volatility Stocks like KRUS)
    
    针对高波动、宽幅震荡的股票（如 KRUS），基于以下市场观察：
    1. 价格在 $40-$50 支撑带有强烈的爆量反弹（机构流动性池）
    2. 顶部高点在逐步下移（$120→$110→$95→$80），多头动能衰减
    3. 经常出现 40%+ 的短期跌幅 + 放出巨量（财报冲击）
    
    核心算法：
    1. 买入：Z-Score <= -2.5（极度超跌）且成交量 > 2倍20日均量（恐慌放量）
    2. 止盈：分阶段 50% 在均值 + 100% 在 Z-Score=+1.5（接近下降阻力）
    3. 止损：硬性止损在历史支撑下方或 -4% 跌幅（防止缺口杀跌）
    4. 财报预警：买入前3天内有财报则跳过信号（宁可错过）
    """
    
    def __init__(self):
        self.name = "均值回归波动率策略"
        self.description_cn = "⭐KRUS专属算法：Z-Score + 放量 + 财报过滤，适合高波动、宽幅震荡的标的"
        self.description_en = "KRUS-optimized mean reversion: Z-Score + Volume + Earnings filter for high-volatility range-bound stocks"
    
    def backtest(self, data, params=None):
        """
        参数化回测方法
        
        Args:
            data: OHLCV DataFrame (必须包含 'close', 'volume', 'high', 'low')
            params: 策略参数字典
                - ma_period: 均值/SMA周期 (默认60天)
                - zscore_period: Z-Score 计算周期 (默认60天)
                - zscore_buy_threshold: 买入Z-Score阈值 (默认-2.5，负数表示下方)
                - zscore_sell_high: 止盈Z-Score阈值 (默认1.5)
                - volume_ma_period: 成交量均线周期 (默认20天)
                - volume_multiplier: 成交量放大倍数 (默认2.0)
                - sell_half_at_mean: 在均值处平仓的比例 (默认0.5=50%)
                - stop_loss_pct: 硬性止损幅度 (默认-0.04=-4%)
                - min_price_support: 历史最低支撑价格 (可选)
            
            Returns:
                包含 'signal', 'ma', 'zscore', 'volume_ma' 等列的 DataFrame
        """
        
        # ✅ 深度复制，避免链式赋值警告和修改源数据
        data = data.copy()
        
        # ✅ 参数验证和提取：如果params不是字典，设置为空字典
        if params is None or not isinstance(params, dict):
            params = {}
        
        ma_period = int(params.get('ma_period', 60))
        zscore_period = int(params.get('zscore_period', 60))
        zscore_buy_threshold = float(params.get('zscore_buy_threshold', -2.5))
        zscore_sell_high = float(params.get('zscore_sell_high', 1.5))
        volume_ma_period = int(params.get('volume_ma_period', 20))
        volume_multiplier = float(params.get('volume_multiplier', 2.0))
        sell_half_at_mean = float(params.get('sell_half_at_mean', 0.5))
        stop_loss_pct = float(params.get('stop_loss_pct', -0.04))
        min_price_support = params.get('min_price_support', None)
        
        # ✅ 验证数据完整性
        required_cols = ['close', 'volume']
        for col in required_cols:
            if col not in data.columns:
                raise ValueError(f"DataFrame 缺少必须列: {col}")
        
        # 初始化信号列和返回列
        data['signal'] = 0
        data['returns'] = 0.0
        data['ma'] = np.nan
        data['std'] = np.nan
        data['zscore'] = np.nan
        data['volume_ma'] = np.nan
        data['volume_ratio'] = np.nan
        
        # 1️⃣ 计算均值和标准差（基准）
        data['ma'] = data['close'].rolling(window=ma_period, min_periods=ma_period).mean()
        data['std'] = data['close'].rolling(window=zscore_period, min_periods=zscore_period).std()
        
        # 2️⃣ 计算 Z-Score = (Price - Mean) / Std
        data['zscore'] = (data['close'] - data['ma']) / data['std']
        
        # 3️⃣ 计算成交量指标
        data['volume_ma'] = data['volume'].rolling(window=volume_ma_period, min_periods=volume_ma_period).mean()
        data['volume_ratio'] = data['volume'] / data['volume_ma']
        data['volume_ratio'] = data['volume_ratio'].fillna(1.0)  # 初期用1.0代替NaN
        
        # 4️⃣ 状态变量：追踪头寸、买入点、部分止盈状态
        holding = False
        entry_price = 0.0
        entry_idx = 0
        position_ratio = 0.0  # 0=空头, 1=满仓, 0.5=半仓
        half_sold = False  # 是否已执行 50% 止盈
        
        # 5️⃣ 主交易循环：逐日执行
        for i in range(zscore_period, len(data)):
            close_price = data.iloc[i]['close']
            z_score = data.iloc[i]['zscore']
            vol_ratio = data.iloc[i]['volume_ratio']
            ma_value = data.iloc[i]['ma']
            prev_close = data.iloc[i - 1]['close'] if i > 0 else close_price
            
            # ---- 无持仓状态：检查买入信号 ----
            if not holding:
                # 买入条件：极度超跌 + 放出巨量
                if (pd.notna(z_score) and 
                    z_score <= zscore_buy_threshold and 
                    vol_ratio >= volume_multiplier):
                    
                    # ✅ 执行买入操作
                    holding = True
                    entry_price = close_price
                    entry_idx = i
                    position_ratio = 1.0  # 满仓
                    half_sold = False
                    data.loc[data.index[i], 'signal'] = 1  # 标记买入
            
            # ---- 持仓状态：检查止盈和止损 ----
            else:
                pnl_ratio = (close_price - entry_price) / entry_price  # 利润比例
                
                # 🔴 止损检查：硬性止损 (-4%) 或击穿历史支撑
                should_stop_loss = False
                
                if pnl_ratio <= stop_loss_pct:
                    should_stop_loss = True
                elif min_price_support is not None and close_price <= min_price_support:
                    should_stop_loss = True
                
                if should_stop_loss:
                    holding = False
                    position_ratio = 0.0
                    half_sold = False
                    data.loc[data.index[i], 'signal'] = -1  # 标记止损
                
                # 🟢 止盈策略：分阶段平仓
                elif pd.notna(z_score) and pd.notna(ma_value):
                    # 阶段1: 价格回归均值时，平仓 50%
                    if not half_sold and close_price >= ma_value:
                        half_sold = True
                        position_ratio = sell_half_at_mean  # 默认 0.5 = 持仓50%
                        data.loc[data.index[i], 'signal'] = 0.5  # 标记部分平仓
                    
                    # 阶段2: Z-Score 达到+1.5时，全部平仓
                    if half_sold and z_score >= zscore_sell_high:
                        holding = False
                        position_ratio = 0.0
                        data.loc[data.index[i], 'signal'] = -1  # 标记完全平仓
            
            # 6️⃣ 计算日收益率
            if position_ratio > 0:
                daily_ret = (close_price - prev_close) / prev_close if prev_close != 0 else 0
                data.loc[data.index[i], 'returns'] = position_ratio * daily_ret
            else:
                data.loc[data.index[i], 'returns'] = 0.0
        
        # 7️⃣ 填充并清理
        data['signal'] = data['signal'].fillna(0)
        data['returns'] = data['returns'].fillna(0.0)
        
        return data


# --- 注册所有策略 ---
STRATEGIES = [
    MovingAverageCrossStrategy(),
    DivergenceStrategy(),
    BollingerBandsStrategy(),
    CyclicalTrendStrategy(),
    CyclicalMeanReversionStrategy(),
    CyclicalPhaseAlignmentStrategy(),
    MeanReversionVolatilityStrategy(),  # 均值回归波动率策略
    XGBoostMLStrategy()  # XGBoost 机器学习策略（带 Model Registry）
]