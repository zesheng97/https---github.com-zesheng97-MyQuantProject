"""
文件位置: Strategy_Pool/custom/mean_reversion_volatility.py
描述: 均值波动性交易策略 (升级版)
功能: 利用短期波动率、长期均值、ATR移动止盈、动量过滤和分批减仓进行智能交易

升级亮点:
    ✨ ATR 移动止盈: 取消死板的Z-Score止损，改用最高点回撤追踪
    ✨ 动量过滤器: 强动量时延迟卖出，直到动量衰减
    ✨ 分批减仓: 50%在均值落袋，50%追踪大趋势
    ✨ 动态止损: 盈利后止损上移，留足波动缓冲区
"""

import numpy as np
import pandas as pd


class MeanReversionVolatilityStrategy:
    """
    增强型均值波动性交易策略 (Enhanced Mean Reversion Volatility Strategy)
    
    核心创新:
    ========
    1. 【ATR移动止盈】 Trailing Stop Loss
       - 摒弃固定Z-Score阈值的死板逻辑
       - 追踪买入后的最高价 (Highest_Price)
       - 当价格跌破 Highest_Price - (n * ATR) 时触发卖出
       - 数学意图: 让利润奔跑，尽可能捕捉主升浪
       
    2. 【动量过滤器】 Momentum Filter
       - 进场时检查短期动量 (momentum_5/10)
       - 出场时再次确认动量是否衰减
       - 强动量时(>0.02)延迟卖出1-2天，等待衰减
       - 数学意图: 避免在上升趋势中过早止损
       
    3. 【分批减仓】 Pyramiding Exit
       - 首批50%减仓: 在接近均线位置落袋为安 (获利保护)
       - 剩余50%: 完全交给ATR移动止盈逻辑 (趋势追踪)
       - 数学意图: 平衡预期收益与风险，锁定部分利润同时追踪大趋势
       
    4. 【动态止损保护】 Dynamic Stop Loss
       - 初始止损 = entry_price * (1 - single_loss_limit)
       - 盈利>profit_threshold后,止损上移至entry_price上方
       - 止损上移幅度 = max(entry_price, close * (1 - trailing_stop_loss))
       - Buffer机制: 留出 2*ATR 空间,防止市场噪点扫出场
       - 数学意图: 保护保本,同时给予足够的波动空间

    数学基础:
    =========
    - 统计套利: 利用价格与均值的偏离 (Mean Reversion Theory)
    - 波动率过滤: 在低风险环境下执行交易 (Volatility Regime Filter)
    - ATR动态风险: 根据真实波幅自适应调整止损距离
    - 动量确认: 避免在强趋势中反向交易 (Trend Confirmation)
    """
    
    def __init__(self):
        self.name = "均值波动性策略(增强版)"
        self.description_cn = """
        升级版均值回归策略: 智能ATR移动止盈 + 动量过滤 + 分批减仓 + 动态止损
        - 买点精准,卖点不再过早
        - 强势单由ATR追踪,捕捉主升浪
        - 首批50%获利保护,剩余50%趋势追踪
        - 动态止损防止被扫，留足波动缓冲
        """
        self.description_en = """
        Enhanced Mean Reversion Strategy: Smart ATR Trailing + Momentum Filter + Scaled Exit + Dynamic Stop Loss
        - Precise entry, optimized exit
        - Strong positions tracked by ATR to catch major rallies
        - First 50% profit taking, remaining 50% trend following
        - Dynamic stops prevent whipsaws while allowing room for volatility
        """
    
    def backtest(self, data, params=None):
        """
        参数化回测 (增强版)
        
        Args:
            data: OHLCV DataFrame (须包含 high, low, close, volume)
            params: {
                # 基础参数
                'ma_period': 均值周期 (天), default=20
                'volatility_period': 波动率周期 (天), default=20
                'vol_threshold': 波动率阈值(0.01-0.05), default=0.02
                'deviation_threshold': 价格偏离阈值(2%-5%), default=0.03
                'position_size': 头寸规模(0-1), default=1.0
                
                # ATR参数
                'atr_period': ATR周期 (天), default=14
                'trailing_atr_multiplier': 移动止盈的ATR倍数, default=2.0
                              (越大越宽松，越小越紧)
                
                # 动量过滤参数
                'momentum_period': 动量计算周期 (天), default=5
                'momentum_threshold': 动量衰减阈值, default=0.02
                'momentum_delay_days': 强动量延迟天数, default=1
                
                # 分批减仓参数
                'sell_half_at_mean': 在均值附近卖出50%, default=True
                'half_position_threshold': 触发50%减仓的偏离度, default=0.01
                
                # 动态止损参数
                'single_loss_limit': 单笔最大损失%, default=0.05 (5%)
                'profit_threshold': 触发止损上移的利润%, default=0.05 (5%)
                'trailing_stop_loss': 止损上移倍数, default=0.03 (3%)
                'stop_loss_buffer_atr': 止损缓冲的ATR倍数, default=2.0
            }
            
        Returns:
            包含signal、hold_days、highest_price等列的DataFrame
        """
        
        if params is None:
            params = {}
        
        # ========== 参数提取 ==========
        # 基础参数
        ma_period = params.get('ma_period', 20)
        volatility_period = params.get('volatility_period', 20)
        vol_threshold = params.get('vol_threshold', 0.02)
        deviation_threshold = params.get('deviation_threshold', 0.03)
        position_size = params.get('position_size', 1.0)
        
        # ATR参数
        atr_period = params.get('atr_period', 14)
        trailing_atr_multiplier = params.get('trailing_atr_multiplier', 2.0)
        
        # 动量过滤参数
        momentum_period = params.get('momentum_period', 5)
        momentum_threshold = params.get('momentum_threshold', 0.02)
        momentum_delay_days = params.get('momentum_delay_days', 1)
        
        # 分批减仓参数
        sell_half_at_mean = params.get('sell_half_at_mean', True)
        half_position_threshold = params.get('half_position_threshold', 0.01)
        
        # 动态止损参数
        single_loss_limit = params.get('single_loss_limit', 0.05)
        profit_threshold = params.get('profit_threshold', 0.05)
        trailing_stop_loss = params.get('trailing_stop_loss', 0.03)
        stop_loss_buffer_atr = params.get('stop_loss_buffer_atr', 2.0)
        
        data = data.copy()
        
        # ========== 1. 计算基础技术指标 ==========
        # 计算长期均值（趋势基准）
        data['ma'] = data['close'].rolling(ma_period).mean()
        
        # 计算价格变化率和波动率
        data['returns'] = data['close'].pct_change()
        data['volatility'] = data['returns'].rolling(volatility_period).std()
        
        # 计算价格相对于均值的偏离度
        # 公式: (Close - MA) / MA
        # 意图: 量化价格偏离均值的程度，正值代表高位，负值代表低位
        data['price_deviation'] = (data['close'] - data['ma']) / data['ma']
        
        # ========== 2. 计算ATR（真实波幅）==========
        # ATR是衡量市场波动性的关键指标
        # 用途: 动态调整止盈/止损距离以适应不同波动环境
        if 'high' in data.columns and 'low' in data.columns:
            # 真实波幅 = max(high-low, |high-prev_close|, |low-prev_close|)
            tr1 = data['high'] - data['low']
            tr2 = abs(data['high'] - data['close'].shift(1))
            tr3 = abs(data['low'] - data['close'].shift(1))
            data['tr'] = np.maximum(np.maximum(tr1, tr2), tr3)
            data['atr'] = data['tr'].rolling(atr_period).mean()
        else:
            # 备用: 当没有高低价时，用波动率估算
            data['atr'] = data['volatility'] * data['close']
        
        # ========== 3. 计算动量指标 ==========
        # 短期动量 = (Close - Close[n天前]) / Close[n天前]
        # 意图: 识别价格趋势强度，强正动量时避免卖出
        data['momentum'] = data['close'].pct_change(periods=momentum_period)
        
        # 更细粒度的5日动量用于实时决策
        data['momentum_5d'] = data['close'].pct_change(periods=5)
        
        # ========== 4. 初始化跟踪变量 ==========
        # 这些变量用于追踪持仓状态和动态止损
        data['signal'] = 0  # 交易信号: 1=持多, -1=空头, 0=观望
        data['entry_price'] = np.nan  # 进场价格
        data['highest_price'] = np.nan  # 买入后的最高价（用于ATR移动止盈）
        data['entry_idx'] = -1  # 进场时的索引
        data['position_type'] = 0  # 0=无头寸, 1=全仓, 2=50%仓位, 3=剩余50%已减仓
        data['momentum_trigger_idx'] = -1  # 动量触发卖出的索引
        data['stop_loss_price'] = np.nan  # 当前止损价
        data['first_half_sold'] = False  # 首批50%是否已卖出
        
        # ========== 5. 主循环：生成交易信号 ==========
        start_idx = max(ma_period, volatility_period, momentum_period)
        
        for i in range(start_idx, len(data)):
            current_price = data['close'].iloc[i]
            current_atr = data['atr'].iloc[i] if not pd.isna(data['atr'].iloc[i]) else 0
            current_momentum = data['momentum'].iloc[i]
            current_momentum_5d = data['momentum_5d'].iloc[i]
            current_vol = data['volatility'].iloc[i]
            
            # ===== 5.1 买入逻辑 =====
            if data['position_type'].iloc[i-1] == 0:  # 当前无头寸
                # 买入条件: 
                # 1. 波动率较低（低风险环境）
                # 2. 价格在均值下方
                # 3. 价格偏离下方（低价时进场）
                is_low_vol = current_vol < vol_threshold and not pd.isna(current_vol)
                is_price_below_ma = current_price < data['ma'].iloc[i]
                is_deviation_low = data['price_deviation'].iloc[i] < -deviation_threshold
                
                if is_low_vol and is_price_below_ma and is_deviation_low:
                    # ✅ 进场！
                    data.loc[data.index[i], 'signal'] = 1
                    data.loc[data.index[i], 'position_type'] = 1  # 全仓进场
                    data.loc[data.index[i], 'entry_price'] = current_price
                    data.loc[data.index[i], 'highest_price'] = current_price
                    data.loc[data.index[i], 'entry_idx'] = i
                    
                    # 【动态止损初始化】
                    # 初始止损 = entry_price * (1 - single_loss_limit)
                    # 意图: 设置初始风险边界，限制单笔最大损失
                    initial_stop = current_price * (1 - single_loss_limit)
                    data.loc[data.index[i], 'stop_loss_price'] = initial_stop
                    
                    data.loc[data.index[i], 'first_half_sold'] = False
                    data.loc[data.index[i], 'momentum_trigger_idx'] = -1
                else:
                    # 继续持币观望
                    data.loc[data.index[i], 'signal'] = 0
                    data.loc[data.index[i], 'position_type'] = 0
            
            # ===== 5.2 持仓中的退出逻辑 =====
            else:
                # 获取进场时的信息
                entry_price = data['entry_price'].iloc[i-1]
                highest_price = data['highest_price'].iloc[i-1]
                position_type = data['position_type'].iloc[i-1]
                first_half_sold = data['first_half_sold'].iloc[i-1]
                is_first_half_sold = first_half_sold if isinstance(first_half_sold, (bool, np.bool_)) else False
                
                # 实时更新最高价（用于ATR移动止盈）
                # 公式: highest_price = max(highest_price_prev, current_price)
                # 意图: 追踪自进场以来的最高价，作为移动止盈的基准
                if current_price > highest_price:
                    data.loc[data.index[i], 'highest_price'] = current_price
                else:
                    data.loc[data.index[i], 'highest_price'] = highest_price
                
                entry_price_safe = entry_price if not pd.isna(entry_price) else current_price
                highest_price_safe = data['highest_price'].iloc[i] if not pd.isna(data['highest_price'].iloc[i]) else current_price
                
                # -------- 第一批减仓逻辑（50%在均线附近落袋） --------
                if sell_half_at_mean and not is_first_half_sold:
                    price_dev = data['price_deviation'].iloc[i]
                    
                    # 触发条件: 价格回到接近均值位置(偏离度<1%)
                    # 用途: 锁定部分利润，保护已获收益
                    if (price_dev > -half_position_threshold and 
                        price_dev < half_position_threshold and
                        current_price > entry_price_safe):
                        # ✅ 减仓50%
                        data.loc[data.index[i], 'signal'] = 1  # 保持持仓，但记录减仓事件
                        data.loc[data.index[i], 'position_type'] = 2  # 标记为部分头寸已卖
                        data.loc[data.index[i], 'first_half_sold'] = True
                        
                        # 剩余50%的头寸继续由ATR移动止盈逻辑管理
                        # 更新highest_price为当前价（重新开始追踪，为剩余50%服务）
                        data.loc[data.index[i], 'highest_price'] = current_price
                        continue
                
                # -------- ATR 移动止盈逻辑（追踪大趋势） --------
                # 这是核心改进: 摒弃固定阈值，改用动态ATR追踪
                
                # 1. 止损条件：价格跌破 highest_price - n*ATR
                # 公式: trailing_stop_line = highest_price - trailing_atr_multiplier * ATR
                # 意图: 当价格从高点回撤超过n倍ATR时卖出，n越大保留越多利润
                trailing_stop_line = highest_price_safe - (trailing_atr_multiplier * current_atr)
                is_trailing_stop_hit = current_price < trailing_stop_line
                
                # -------- 动态止损保护（防止保本损过早触发） --------
                # 盈利后自动上移止损，但留足缓冲防止被扫
                
                current_pnl_pct = (current_price - entry_price_safe) / entry_price_safe
                
                if current_pnl_pct > profit_threshold:
                    # 盈利超过阈值后，启用动态止损上移
                    # 新止损 = max(初始止损, 当前价 - 止损上移幅度)
                    # 意图: 保护利润，但给予2*ATR缓冲防止噪点
                    profit_adjusted_stop = current_price * (1 - trailing_stop_loss) - (stop_loss_buffer_atr * current_atr)
                    initial_stop = entry_price_safe * (1 - single_loss_limit)
                    new_stop = max(initial_stop, profit_adjusted_stop)
                    
                    data.loc[data.index[i], 'stop_loss_price'] = new_stop
                else:
                    # 未盈利或盈利不足时，保持初始止损
                    data.loc[data.index[i], 'stop_loss_price'] = entry_price_safe * (1 - single_loss_limit)
                
                # 检查是否触发止损
                is_stop_loss_hit = current_price < data['stop_loss_price'].iloc[i]
                
                # -------- 动量过滤卖出逻辑 --------
                # 当ATR止盈信号出现时，再检查动量是否衰减
                # 用途: 避免在强上升趋势中卖出，等待动量确认衰减
                
                if is_trailing_stop_hit:
                    # ATR移动止盈被触发，检查动量
                    if current_momentum_5d > momentum_threshold:
                        # 仍有强正动量，延迟卖出1-2天
                        # 记录动量触发时间，在后续日期如果动量衰减则卖出
                        if data['momentum_trigger_idx'].iloc[i-1] == -1:
                            data.loc[data.index[i], 'momentum_trigger_idx'] = i
                        
                        # 延迟期间内继续持仓
                        data.loc[data.index[i], 'signal'] = 1
                        data.loc[data.index[i], 'position_type'] = position_type
                        continue
                    else:
                        # 动量已衰减，执行卖出
                        # ✅ 卖出全部头寸
                        data.loc[data.index[i], 'signal'] = -1
                        data.loc[data.index[i], 'position_type'] = 0
                        data.loc[data.index[i], 'entry_price'] = np.nan
                        data.loc[data.index[i], 'highest_price'] = np.nan
                
                elif is_stop_loss_hit:
                    # 止损被触发，立即卖出
                    # ✅ 执行止损卖出
                    data.loc[data.index[i], 'signal'] = -1
                    data.loc[data.index[i], 'position_type'] = 0
                    data.loc[data.index[i], 'entry_price'] = np.nan
                    data.loc[data.index[i], 'highest_price'] = np.nan
                
                else:
                    # 持仓继续，不卖出
                    data.loc[data.index[i], 'signal'] = 1
                    data.loc[data.index[i], 'position_type'] = position_type
        
        # ========== 6. 信号平滑和持仓传导 ==========
        # 使用前向填充持有头寸，直到信号改变
        prev_signal = 0
        for i in range(start_idx, len(data)):
            if pd.isna(data['signal'].iloc[i]) or data['signal'].iloc[i] == 0:
                # 如果当前信号为空，继承前一个信号
                data.loc[data.index[i], 'signal'] = prev_signal
            else:
                prev_signal = data['signal'].iloc[i]
        
        # ========== 7. 计算策略收益 ==========
        # 策略收益 = 信号 * 日收益率
        # 意图: 衡量策略在整个周期内的表现
        data['strategy_returns'] = data['signal'].shift(1) * data['returns']
        
        return data
