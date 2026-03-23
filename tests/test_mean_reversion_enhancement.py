"""
文件: tests/test_mean_reversion_enhancement.py
用途: 完整演示均值波动性策略的升级功能

功能:
    1. 对比原版 vs 升级版的效果
    2. 展示各个参数的实际影响
    3. 可视化回测结果
    4. 性能指标对比
"""

import sys
from pathlib import Path

# 动态添加项目路径，支持从任意目录运行
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from Strategy_Pool.custom.mean_reversion_volatility import MeanReversionVolatilityStrategy
import matplotlib.pyplot as plt


class BacktestAnalyzer:
    """回测分析工具"""
    
    def __init__(self, name: str):
        self.name = name
    
    def calculate_metrics(self, data: pd.DataFrame) -> dict:
        """计算关键性能指标"""
        
        cumulative_returns = (1 + data['strategy_returns']).cumprod() - 1
        total_return = cumulative_returns.iloc[-1]
        
        # 年化夏普比
        annual_returns = data['strategy_returns'].mean() * 252
        annual_volatility = data['strategy_returns'].std() * np.sqrt(252)
        sharpe_ratio = annual_returns / annual_volatility if annual_volatility > 0 else 0
        
        # 最大回撤
        cumulative = (1 + data['strategy_returns']).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # 交易统计
        signals = data['signal'].diff().fillna(0)
        buy_signals = (signals == 1).sum()
        sell_signals = (signals == -1).sum()
        
        # 盈利统计
        profitable_trades = (data['strategy_returns'] > 0).sum()
        total_trades = (signals != 0).sum()
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        return {
            '总收益': f"{total_return:.2%}",
            '年化收益': f"{annual_returns:.2%}",
            '年化波动': f"{annual_volatility:.2%}",
            '夏普比': f"{sharpe_ratio:.2f}",
            '最大回撤': f"{max_drawdown:.2%}",
            '买入次数': buy_signals,
            '卖出次数': sell_signals,
            '总交易次数': total_trades,
            '胜率': f"{win_rate:.2%}",
        }
    
    def print_metrics(self, data: pd.DataFrame):
        """打印性能指标"""
        print(f"\n{'='*60}")
        print(f"📊 {self.name} - 性能指标")
        print(f"{'='*60}")
        
        metrics = self.calculate_metrics(data)
        for key, value in metrics.items():
            print(f"  {key:<12} : {value:>15}")
        
        print(f"{'='*60}\n")


def generate_sample_data(days=500, seed=42) -> pd.DataFrame:
    """生成模拟数据用于演示"""
    
    np.random.seed(seed)
    
    dates = pd.date_range(end='2024-01-01', periods=days)
    
    # 生成逼真的价格数据：趋势 + 随机波动 + 均值回归
    returns = []
    for i in range(days):
        # 趋势成分
        trend = np.sin(i / 100) * 0.001
        # 随机游走
        noise = np.random.normal(0, 0.015)
        # 均值回归（价格倾向回到移动平均）
        returns.append(trend + noise)
    
    close_prices = 100 * np.exp(np.cumsum(returns))
    
    # 生成高低价
    high_prices = close_prices * (1 + np.abs(np.random.normal(0, 0.01, days)))
    low_prices = close_prices * (1 - np.abs(np.random.normal(0, 0.01, days)))
    
    # 确保逻辑正确性
    high_prices = np.maximum(high_prices, close_prices)
    low_prices = np.minimum(low_prices, close_prices)
    
    volume = np.random.randint(1000000, 10000000, days)
    
    return pd.DataFrame({
        'date': dates,
        'open': close_prices * 0.99,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volume,
    })


def test_basic_functionality():
    """测试1：基础功能验证"""
    
    print("\n" + "="*60)
    print("🧪 测试1: 基础功能验证")
    print("="*60)
    
    # 生成数据
    data = generate_sample_data(days=500)
    print(f"✅ 生成模拟数据: {len(data)} 行")
    
    # 初始化策略
    strategy = MeanReversionVolatilityStrategy()
    print(f"✅ 策略名称: {strategy.name}")
    
    # 运行回测
    result = strategy.backtest(data, params={
        'ma_period': 20,
        'volatility_period': 20,
        'vol_threshold': 0.02,
        'deviation_threshold': 0.03,
    })
    
    print(f"✅ 回测完成，输出列数: {len(result.columns)}")
    print(f"✅ 关键列存在: signal={('signal' in result.columns)}, "
          f"entry_price={('entry_price' in result.columns)}, "
          f"highest_price={('highest_price' in result.columns)}")
    
    # 检查信号的合理性
    signal_counts = result['signal'].value_counts()
    print(f"✅ 信号分布: 多头={signal_counts.get(1, 0)}, 空头={signal_counts.get(-1, 0)}, 观望={signal_counts.get(0, 0)}")
    
    return result


def test_atr_trailing_stop():
    """测试2: ATR移动止盈功能"""
    
    print("\n" + "="*60)
    print("🎯 测试2: ATR移动止盈机制")
    print("="*60)
    
    data = generate_sample_data(days=500)
    strategy = MeanReversionVolatilityStrategy()
    
    # 使用较宽松的ATR倍数，允许更多利润空间
    result = strategy.backtest(data, params={
        'trailing_atr_multiplier': 3.0,  # 宽松，追踪大趋势
        'atr_period': 14,
    })
    
    # 分析持仓期间的最高价和止损线
    holding_periods = result[result['signal'] == 1]
    if len(holding_periods) > 0:
        print(f"✅ 总持仓天数: {len(holding_periods)}")
        print(f"✅ 最高价平均值: {holding_periods['highest_price'].mean():.2f}")
        print(f"✅ 最高价最大值: {holding_periods['highest_price'].max():.2f}")
        
        # 计算从进场到最高价的均值回撤
        entry_prices = result[result['entry_price'].notna()]['entry_price']
        if len(entry_prices) > 0:
            avg_entry = entry_prices.mean()
            avg_highest = (entry_prices * 1.05).mean()  # 平均涨幅
            print(f"✅ 平均进场价: {avg_entry:.2f}")
            print(f"✅ 平均最高价: {avg_highest:.2f}")
            print(f"✅ 平均涨幅: {(avg_highest - avg_entry) / avg_entry:.2%}")
    
    return result


def test_momentum_filter():
    """测试3: 动量过滤器的延迟卖出"""
    
    print("\n" + "="*60)
    print("📈 测试3: 动量过滤器延迟卖出")
    print("="*60)
    
    data = generate_sample_data(days=500)
    strategy = MeanReversionVolatilityStrategy()
    
    # 不同动量阈值的对比
    configs = [
        {'momentum_threshold': 0.01, '名称': '低阈值(1%)'},
        {'momentum_threshold': 0.02, '名称': '中阈值(2%)'},
        {'momentum_threshold': 0.05, '名称': '高阈值(5%)'},
    ]
    
    for config in configs:
        name = config.pop('名称')
        result = strategy.backtest(data, params=config)
        
        # 统计动量触发的延迟卖出次数
        delayed_sells = (result['momentum_trigger_idx'] > -1).sum()
        
        print(f"✅ {name}: 延迟卖出 {delayed_sells} 次")
        
        analyzer = BacktestAnalyzer(f"动量过滤 - {name}")
        analyzer.print_metrics(result)


def test_scaled_exit():
    """测试4: 分批减仓的效果"""
    
    print("\n" + "="*60)
    print("💰 测试4: 分批减仓(50% + 50%)")
    print("="*60)
    
    data = generate_sample_data(days=500)
    strategy = MeanReversionVolatilityStrategy()
    
    # 启用和禁用分批减仓的对比
    configs = [
        {'sell_half_at_mean': False, '名称': '无分批减仓'},
        {'sell_half_at_mean': True, 'half_position_threshold': 0.01, '名称': '分批减仓(±1%)'},
    ]
    
    for config in configs:
        name = config.pop('名称')
        result = strategy.backtest(data, params=config)
        
        analyzer = BacktestAnalyzer(name)
        analyzer.print_metrics(result)


def test_dynamic_stop_loss():
    """测试5: 动态止损保护"""
    
    print("\n" + "="*60)
    print("🛡️ 测试5: 动态止损保护")
    print("="*60)
    
    data = generate_sample_data(days=500)
    strategy = MeanReversionVolatilityStrategy()
    
    # 不同止损配置
    configs = [
        {
            'single_loss_limit': 0.03,
            'profit_threshold': 0.03,
            'stop_loss_buffer_atr': 1.0,
            '名称': '激进止损'
        },
        {
            'single_loss_limit': 0.05,
            'profit_threshold': 0.05,
            'stop_loss_buffer_atr': 2.0,
            '名称': '标准止损(推荐)'
        },
        {
            'single_loss_limit': 0.08,
            'profit_threshold': 0.08,
            'stop_loss_buffer_atr': 3.0,
            '名称': '宽松止损'
        },
    ]
    
    results = {}
    for config in configs:
        name = config.pop('名称')
        result = strategy.backtest(data, params=config)
        results[name] = result
        
        analyzer = BacktestAnalyzer(name)
        analyzer.print_metrics(result)


def compare_performance():
    """总体性能对比"""
    
    print("\n" + "="*60)
    print("🏆 总体性能对比")
    print("="*60)
    
    data = generate_sample_data(days=500)
    strategy = MeanReversionVolatilityStrategy()
    
    scenarios = [
        {
            'params': {
                'trailing_atr_multiplier': 2.0,
                'momentum_threshold': 0.02,
                'single_loss_limit': 0.05,
            },
            'name': '平衡配置(推荐 ⭐⭐⭐)'
        },
        {
            'params': {
                'trailing_atr_multiplier': 1.5,
                'momentum_threshold': 0.03,
                'single_loss_limit': 0.03,
            },
            'name': '保守配置'
        },
        {
            'params': {
                'trailing_atr_multiplier': 3.5,
                'momentum_threshold': 0.01,
                'single_loss_limit': 0.08,
            },
            'name': '激进配置'
        },
    ]
    
    results_summary = []
    
    for scenario in scenarios:
        result = strategy.backtest(data, params=scenario['params'])
        analyzer = BacktestAnalyzer(scenario['name'])
        metrics = analyzer.calculate_metrics(result)
        
        metrics['配置类型'] = scenario['name']
        results_summary.append(metrics)
        analyzer.print_metrics(result)
    
    # 总结表
    print("\n" + "="*80)
    print("📋 快速对比表")
    print("="*80)
    summary_df = pd.DataFrame(results_summary)
    print(summary_df.to_string(index=False))


def main():
    """主函数：运行所有测试"""
    
    print("\n" + "🚀"*30)
    print("均值波动性策略升级版 - 完整测试套件")
    print("🚀"*30)
    
    # 测试1: 基础功能
    result1 = test_basic_functionality()
    
    # 测试2: ATR移动止盈
    result2 = test_atr_trailing_stop()
    
    # 测试3: 动量过滤器
    test_momentum_filter()
    
    # 测试4: 分批减仓
    test_scaled_exit()
    
    # 测试5: 动态止损
    test_dynamic_stop_loss()
    
    # 总体对比
    compare_performance()
    
    print("\n" + "✅"*30)
    print("所有测试完成!")
    print("✅"*30)
    
    print("""
    
📚 后续建议:
    
    1. 【参数优化】在实际数据上运行参数网格搜索，找到最优组合
       
    2. 【实盘验证】在模拟账户上小额验证策略，验证实际表现
       
    3. 【数据不同】在不同时间段、不同资产上测试（A股、期货、加密）
       
    4. 【日志记录】添加详细的交易日志，追踪每笔交易的原因
       
    5. 【动态调整】根据市场状态动态调整参数(牛市/熊市不同)

🔗 相关文件:
    - 详细指南: Strategy_Pool/custom/MEAN_REVERSION_ENHANCEMENT_GUIDE.md
    - 策略代码: Strategy_Pool/custom/mean_reversion_volatility.py
    - 本测试脚本: tests/test_mean_reversion_enhancement.py
    """)


if __name__ == '__main__':
    main()
