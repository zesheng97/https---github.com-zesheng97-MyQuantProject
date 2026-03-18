"""
文件位置: Engine_Matrix/backtest_engine.py
描述: 参数化回测引擎核心模块
功能: 支持自定义时间段、初始资金、策略参数的回测与指标计算
"""

import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime
import yfinance as yf

# 确保导入路径正确
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@dataclass
class BacktestConfig:
    """回测配置数据类"""
    symbol: str
    start_date: str  # 格式: 'YYYY-MM-DD'
    end_date: str    # 格式: 'YYYY-MM-DD'
    initial_capital: float
    strategy_params: Dict[str, any]  # 例如 {"ma_short": 20, "ma_long": 60}


@dataclass
class BacktestResult:
    """回测结果的标准输出格式"""
    equity_curve: pd.Series           # 每日账户净值
    trades: pd.DataFrame               # 交易记录表
    metrics: Dict[str, float]          # 夏普、回撤等指标
    raw_data: pd.DataFrame            # 原始 OHLCV + 信号数据
    config: BacktestConfig            # 回测配置信息
    benchmark_nasdaq: pd.Series = None  # Nasdaq 基准曲线（可选）
    benchmark_sp500: pd.Series = None   # S&P 500 基准曲线（可选）


class BacktestEngine:
    """
    核心参数化回测引擎
    
    输入：BacktestConfig（包含标的、时间、资金、策略参数）
    输出：BacktestResult（包含资金曲线、交易记录、关键指标）
    """
    
    def __init__(self, strategy, data_dir: str = "Data_Hub/storage"):
        """
        初始化回测引擎
        
        Args:
            strategy: 策略类实例（需含 backtest(data, params) 方法）
            data_dir: Parquet 数据存储目录
        """
        self.strategy = strategy
        self.data_dir = Path(data_dir)
    
    def load_data(self, config: BacktestConfig) -> pd.DataFrame:
        """
        从 Parquet 加载历史数据，并按时间区间过滤
        
        Args:
            config: 回测配置
            
        Returns:
            含有 open, high, low, close, volume 的 DataFrame（按时间排序）
        """
        file_path = self.data_dir / f"{config.symbol}.parquet"
        
        if not file_path.exists():
            raise FileNotFoundError(f"数据文件不存在: {file_path}")
        
        data = pd.read_parquet(file_path)
        
        # 按时间过滤（支持 DatetimeIndex）
        start_dt = pd.to_datetime(config.start_date)
        end_dt = pd.to_datetime(config.end_date)
        
        if isinstance(data.index, pd.DatetimeIndex):
            # 移除时区信息以避免时区比较错误
            if data.index.tz is not None:
                data.index = data.index.tz_localize(None)
            if start_dt.tz is not None:
                start_dt = start_dt.tz_localize(None)
            if end_dt.tz is not None:
                end_dt = end_dt.tz_localize(None)
            data = data[(data.index >= start_dt) & (data.index <= end_dt)]
        else:
            raise ValueError("数据必须有 DatetimeIndex（列名为 'date'）")
        
        if data.empty:
            raise ValueError(f"时间区间内无数据: {config.start_date} 至 {config.end_date}")
        
        return data.sort_index()
    
    def run(self, config: BacktestConfig) -> BacktestResult:
        """
        主回测循环
        
        Args:
            config: 回测配置
            
        Returns:
            BacktestResult 包含资金曲线、交易记录和指标
        """
        # 1. 加载数据
        data = self.load_data(config)
        
        # 2. 执行策略逻辑（生成交易信号）
        signal_data = self.strategy.backtest(data.copy(), config.strategy_params)
        
        # 3. 逐日撮合与账户更新
        equity_curve, trades = self._simulate_trading(signal_data, config.initial_capital)
        
        # 4. 计算核心指标
        metrics = self._compute_metrics(equity_curve, trades)
        
        # 5. 计算基准收益（Nasdaq 和 S&P 500）
        benchmark_nasdaq = self._get_benchmark_returns(config, '^IXIC')
        benchmark_sp500 = self._get_benchmark_returns(config, '^GSPC')
        
        return BacktestResult(
            equity_curve=equity_curve,
            trades=trades,
            metrics=metrics,
            raw_data=signal_data,
            config=config,
            benchmark_nasdaq=benchmark_nasdaq,
            benchmark_sp500=benchmark_sp500
        )
    
    def _simulate_trading(self, data: pd.DataFrame, initial_capital: float) -> Tuple[pd.Series, pd.DataFrame]:
        """
        逐日撮合逻辑（整数股交易：按信号全仓买卖，无杠杆、无滑点）
        
        Args:
            data: 包含 signal 列的数据（1=多头, -1=空头, 0=持币）
            initial_capital: 初始资金
            
        Returns:
            (资金曲线 Series, 交易记录 DataFrame)
        """
        
        # 确保有 signal 列
        if 'signal' not in data.columns:
            raise ValueError("数据必须包含 'signal' 列（来自策略的交易信号）")
        
        cash = initial_capital  # 可用现金
        shares = 0  # 当前持仓股数（整数）
        equity = [initial_capital]  # 账户净值序列
        trades = []  # 交易记录
        
        for idx in range(1, len(data)):
            current_signal = data.iloc[idx]['signal']
            prev_signal = data.iloc[idx-1]['signal']
            current_price = data.iloc[idx]['close']
            current_date = data.index[idx]
            
            # 信号变化时触发交易
            if current_signal != prev_signal:
                if current_signal == 1 and shares == 0:
                    # 买入信号：用所有现金买入尽可能多的整数股
                    buy_shares = int(cash / current_price)
                    if buy_shares > 0:
                        cost = buy_shares * current_price
                        shares = buy_shares
                        cash -= cost
                        trades.append({
                            'date': current_date,
                            'action': 'BUY',
                            'price': current_price,
                            'shares': buy_shares,
                            'cost': cost,
                            'cash_after': cash
                        })
                
                elif current_signal != 1 and shares > 0:
                    # 卖出信号：卖出全部持仓
                    revenue = shares * current_price
                    cost_basis = trades[-1]['cost'] if trades and trades[-1]['action'] == 'BUY' else 0
                    pnl = revenue - cost_basis
                    cash += revenue
                    trades.append({
                        'date': current_date,
                        'action': 'SELL',
                        'price': current_price,
                        'shares': shares,
                        'revenue': revenue,
                        'pnl': pnl,
                        'cash_after': cash
                    })
                    shares = 0
            
            # 计算当日账户净值（现金 + 持仓市值）
            current_equity = cash + shares * current_price
            equity.append(current_equity)
        
        # 转换为 DataFrame 和 Series
        equity_series = pd.Series(equity[1:], index=data.index[1:], name='equity')
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        
        return equity_series, trades_df
    
    def _compute_metrics(self, equity_curve: pd.Series, trades: pd.DataFrame) -> Dict[str, float]:
        """
        计算回测核心指标
        
        Args:
            equity_curve: 每日账户净值序列
            trades: 交易记录表
            
        Returns:
            指标字典 {sharpe_ratio, max_drawdown, win_rate, total_return, ...}
        """
        
        metrics = {}
        
        # 1. 总收益率
        if len(equity_curve) > 0:
            total_return = (equity_curve.iloc[-1] - equity_curve.iloc[0]) / equity_curve.iloc[0]
            metrics['total_return'] = total_return
        else:
            metrics['total_return'] = 0.0
        
        # 2. 日收益率序列
        daily_returns = equity_curve.pct_change().dropna()
        
        # 3. 夏普比率 (假设无风险利率为 0)
        if len(daily_returns) > 0 and daily_returns.std() > 0:
            sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252)
            metrics['sharpe_ratio'] = sharpe_ratio
        else:
            metrics['sharpe_ratio'] = 0.0
        
        # 4. 最大回撤
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max
        max_drawdown = drawdown.min()
        metrics['max_drawdown'] = max_drawdown
        
        # 5. 胜率（正收益交易占比）
        if len(trades) > 0 and 'pnl' in trades.columns:
            winning_trades = len(trades[trades['pnl'] > 0])
            metrics['win_rate'] = winning_trades / len(trades)
        else:
            metrics['win_rate'] = 0.0
        
        # 6. 年化收益率（简化：日均回报 * 252）
        if len(daily_returns) > 0:
            annual_return = daily_returns.mean() * 252
            metrics['annual_return'] = annual_return
        else:
            metrics['annual_return'] = 0.0
        
        # 7. 交易次数
        metrics['num_trades'] = len(trades)
        
        return metrics
    
    def _get_benchmark_returns(self, config: BacktestConfig, benchmark_ticker: str) -> Optional[pd.Series]:
        """
        计算基准指数的收益曲线（用于对比）
        
        Args:
            config: 回测配置
            benchmark_ticker: 基准指数代码 (^IXIC=Nasdaq, ^GSPC=S&P 500)
            
        Returns:
            基准净值曲线 Series（与策略曲线同长度）
        """
        try:
            # 从 yfinance 下载基准指数数据
            start_dt = pd.to_datetime(config.start_date)
            end_dt = pd.to_datetime(config.end_date)
            
            benchmark_data = yf.download(
                benchmark_ticker,
                start=start_dt.strftime('%Y-%m-%d'),
                end=end_dt.strftime('%Y-%m-%d'),
                progress=False,
                auto_adjust=True
            )
            
            if benchmark_data.empty:
                return None
            
            # 获取 close 价格
            if isinstance(benchmark_data.columns, pd.MultiIndex):
                benchmark_close = benchmark_data['Close', benchmark_ticker]
            else:
                benchmark_close = benchmark_data['Close']
            
            # 计算日收益率
            benchmark_returns = benchmark_close.pct_change()
            
            # 计算累积收益曲线（初始资金为 config.initial_capital）
            cumulative_returns = (1 + benchmark_returns).cumprod()
            benchmark_curve = config.initial_capital * cumulative_returns
            
            # 确保索引与股票数据对齐
            benchmark_curve.index.name = 'date'
            
            return benchmark_curve
            
        except Exception as e:
            # 如果下载失败，返回 None（不中断回测）
            print(f"⚠️ 基准指数 {benchmark_ticker} 下载失败: {e}")
            return None
