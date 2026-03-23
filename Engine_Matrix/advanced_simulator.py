"""
高级交易所模拟器 (Advanced Exchange Simulator)
文件位置: Engine_Matrix/advanced_simulator.py

核心功能：
1. 双边佣金扣除 (Bid-Ask Commission)
2. 基于成交量的平方根市场冲击模型 (Square Root Market Impact Model)
3. 真实滑点计算 (实际成交价 ≠ 下单价)
4. 逐笔交易复现，生成完整的资金曲线

平方根冲击模型数学原理：
  当策略下单量占该日总成交量的比例过高时，会对市场价造成冲击。
  
  设：
    - Q_i = 策略在第i天的下单量
    - V_i = 第i天标的的真实市场成交量
    - r_i = Q_i / V_i (下单量占比)
    - λ  = 市场冲击系数 (Impact Coefficient, 通常 0.1~1.0)
  
  平方根冲击模型假设：
    impact_i = λ * sqrt(r_i)
    
  即冲击程度按对数增长，符合真实交易场景的实验观察。
  
  最终成交价格：
    成交价 = 原定价格 ± impact_i * 原定价格
    
  例：原价 $100，下单量占比 1%，λ=0.5：
    impact = 0.5 * sqrt(0.01) = 0.5 * 0.1 = 0.05 (5%)
    买入时成交价 = 100 * (1 + 0.05) = $105
    卖出时成交价 = 100 * (1 - 0.05) = $95
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExchangeConfig:
    """交易所配置参数"""
    commission_rate: float = 0.0005  # 双边佣金（各一次）
    impact_coefficient: float = 0.5  # 平方根冲击系数
    max_order_ratio: float = 0.05  # 单笔订单最大占日成交量比例 (5%)
    min_price: float = 0.01  # 最小价格（防止负数）


class AdvancedExchangeSimulator:
    """
    高级交易所模拟器
    
    特点：
    - 双边佣金（买入时 -commission，卖出时 -commission）
    - 平方根市场冲击（大单自动滑点放大）
    - 成交量监控（警告过度交易）
    - 详细的交易执行记录
    """
    
    def __init__(self, config: Optional[ExchangeConfig] = None):
        """
        初始化模拟器
        
        Args:
            config: 交易所配置对象。若为 None，使用默认配置
        """
        self.config = config or ExchangeConfig()
        self.trades = []  # 交易记录
        self.execution_prices = []  # 成交价格序列
    
    def calculate_market_impact(self, order_size: float, daily_volume: float) -> float:
        """
        计算平方根市场冲击
        
        Args:
            order_size: 下单量（股数）
            daily_volume: 该日市场成交量（股数）
        
        Returns:
            冲击幅度（百分比，如 0.05 表示 5%）
        
        数学模型：
            impact = λ * sqrt(order_size / daily_volume)
            
        安全检查：
            - 若 daily_volume ≤ 0，返回默认最大冲击
            - 若下单占比 > max_order_ratio，发出警告并使用最大占比计算
        """
        
        if daily_volume <= 0:
            # 没有成交量，使用保守默认值（10%）
            return 0.10
        
        order_ratio = order_size / daily_volume
        
        # 超过最大允许占比时的处理
        if order_ratio > self.config.max_order_ratio:
            print(f"⚠️ 警告：下单占比 {order_ratio*100:.2f}% > 最大允许 {self.config.max_order_ratio*100:.1f}%")
            order_ratio = self.config.max_order_ratio
        
        # 平方根冲击计算
        impact = self.config.impact_coefficient * np.sqrt(order_ratio)
        
        return impact
    
    def execute_buy(self, price: float, shares: int, daily_volume: float) -> Tuple[float, float]:
        """
        执行买入订单
        
        Args:
            price: 计划买入价格
            shares: 买入股数
            daily_volume: 该日市场成交量
        
        Returns:
            (实际成交价格, 实际成本) = (已计算冲击和佣金的价格, 支付的总金额)
        """
        
        # 计算市场冲击
        impact = self.calculate_market_impact(shares, daily_volume)
        
        # 买入时：原价 + 冲击 + 佣金
        # 冲击使买价上升，佣金在买价的基础上再加
        execution_price = price * (1 + impact) * (1 + self.config.commission_rate)
        execution_price = max(execution_price, self.config.min_price)  # 防止负数
        
        total_cost = execution_price * shares
        
        return execution_price, total_cost
    
    def execute_sell(self, price: float, shares: int, daily_volume: float) -> Tuple[float, float]:
        """
        执行卖出订单
        
        Args:
            price: 计划卖出价格
            shares: 卖出股数
            daily_volume: 该日市场成交量
        
        Returns:
            (实际成交价格, 实际收入) = (已计算冲击和佣金的价格, 卖出的总金额)
        """
        
        # 计算市场冲击
        impact = self.calculate_market_impact(shares, daily_volume)
        
        # 卖出时：原价 - 冲击 - 佣金
        # 冲击使卖价下降，佣金在卖价的基础上再扣
        execution_price = price * (1 - impact) * (1 - self.config.commission_rate)
        execution_price = max(execution_price, self.config.min_price)  # 防止负数
        
        total_revenue = execution_price * shares
        
        return execution_price, total_revenue
    
    def run(self, 
            data: pd.DataFrame,
            initial_capital: float = 30000,
            strategy_name: str = "Strategy") -> pd.DataFrame:
        """
        执行高级模拟回测
        
        Args:
            data: OHLCV 数据（必须包含 'close', 'signal', 'volume' 列）
                  signal: 1=持仓, -1=空仓
            initial_capital: 初始资金
            strategy_name: 策略名称（用于日志）
        
        Returns:
            包含以下列的 DataFrame：
            - original_signal: 策略原始信号
            - execution_price: 实际成交价格
            - cash: 可用现金
            - position: 持仓股数
            - equity: 当日账户净值 (cash + position*price)
            - cumulative_return: 累计收益率
            - market_impact_cost: 当日市场冲击成本（元）
            - commission_cost: 当日佣金成本（元）
        """
        
        result = data.copy()
        
        # 初始化输出列（显式使用 dtype='float64' 避免类型转换警告）
        result['execution_price'] = 0.0
        result['cash'] = 0.0
        result['position'] = 0.0  # 使用 float64 而不是 int64
        result['equity'] = initial_capital
        result['cumulative_return'] = 0.0
        result['market_impact_cost'] = 0.0
        result['commission_cost'] = 0.0
        result['trade_log'] = ""  # 交易日志
        
        # 状态变量
        cash = initial_capital
        position = 0  # 持仓股数（整数）
        previous_equity = initial_capital
        
        # ========== 主逻辑：逐日执行，模拟真实交易 ==========
        for idx in range(len(data)):
            current_date = data.index[idx]
            current_price = data.iloc[idx]['close']
            current_signal = data.iloc[idx]['signal']
            current_volume = data.iloc[idx]['volume']  # 该日总成交量
            
            execution_price = current_price
            market_impact = 0.0
            commission = 0.0
            trade_log = ""
            
            # 根据信号执行交易（从无仓位进入有仓位，或从有仓位平仓）
            
            # ✅ 买入条件：信号 = 1 且当前无仓位
            if current_signal == 1 and position == 0:
                # 用所有现金购买
                if cash > 0 and current_price > 0:
                    buy_shares = int(cash / current_price)
                    
                    if buy_shares > 0:
                        execution_price, total_cost = self.execute_buy(
                            current_price, buy_shares, current_volume
                        )
                        
                        # 计算冲击成本和佣金
                        ideal_cost = current_price * buy_shares
                        actual_cost = total_cost
                        market_impact = (execution_price - current_price) * buy_shares
                        commission = ideal_cost * self.config.commission_rate
                        
                        # 更新账户
                        cash -= actual_cost
                        position = buy_shares
                        
                        trade_log = f"BUY {buy_shares} @ {execution_price:.2f} (理想价: ${current_price:.2f})"
            
            # ✅ 卖出条件：信号 = -1 且当前有仓位
            elif current_signal == -1 and position > 0:
                execution_price, total_revenue = self.execute_sell(
                    current_price, position, current_volume
                )
                
                # 计算冲击成本和佣金
                ideal_revenue = current_price * position
                actual_revenue = total_revenue
                market_impact = -(current_price - execution_price) * position
                commission = ideal_revenue * self.config.commission_rate
                
                # 更新账户
                cash += actual_revenue
                position = 0
                
                trade_log = f"SELL {position} @ {execution_price:.2f} (理想价: ${current_price:.2f})"
            
            # ========== 计算账户净值 ==========
            position_value = position * current_price  # 持仓按当日收盘价估值
            equity = cash + position_value
            daily_return = (equity - previous_equity) / previous_equity if previous_equity != 0 else 0
            cumulative_return = (equity - initial_capital) / initial_capital
            
            # ========== 保存输出 ==========
            result.loc[result.index[idx], 'execution_price'] = float(execution_price)
            result.loc[result.index[idx], 'cash'] = float(cash)
            result.loc[result.index[idx], 'position'] = int(position)
            result.loc[result.index[idx], 'equity'] = float(equity)
            result.loc[result.index[idx], 'cumulative_return'] = float(cumulative_return)
            result.loc[result.index[idx], 'market_impact_cost'] = float(market_impact)
            result.loc[result.index[idx], 'commission_cost'] = float(commission)
            result.loc[result.index[idx], 'trade_log'] = str(trade_log)
            
            previous_equity = equity
        
        return result
