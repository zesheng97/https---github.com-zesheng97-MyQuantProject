"""
测试脚本：验证高级交易所模拟器的集成和功能
文件位置: test_advanced_simulator.py
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

# 添加项目根路径
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Engine_Matrix.advanced_simulator import AdvancedExchangeSimulator, ExchangeConfig
from Strategy_Pool.strategies import STRATEGIES

# ========== 第一步：生成测试数据 ==========
print("=" * 80)
print("🔬 高级交易所模拟器 - 集成测试")
print("=" * 80)

# 创建 150 天的模拟数据
np.random.seed(42)
dates = pd.date_range('2024-01-01', periods=150, freq='D')

# 模拟 OHLCV 数据
close_prices = 100 * np.exp(np.cumsum(np.random.randn(150) * 0.01))
open_prices = close_prices * (1 + np.random.randn(150) * 0.005)
high_prices = np.maximum(open_prices, close_prices) * (1 + np.abs(np.random.randn(150) * 0.005))
low_prices = np.minimum(open_prices, close_prices) * (1 - np.abs(np.random.randn(150) * 0.005))
volumes = 1000000 + np.random.randint(-200000, 200000, 150)

test_data = pd.DataFrame({
    'open': open_prices,
    'high': high_prices,
    'low': low_prices,
    'close': close_prices,
    'volume': volumes,
}, index=dates)

print(f"\n✅ 生成测试数据：{len(test_data)} 天")
print(f"   价格范围：${test_data['close'].min():.2f} - ${test_data['close'].max():.2f}")
print(f"   成交量范围：{test_data['volume'].min():,.0f} - {test_data['volume'].max():,.0f}")

# ========== 第二步：选择策略并生成信号 ==========
print(f"\n✅ 可用的策略列表 ({len(STRATEGIES)} 个):")
for i, strat in enumerate(STRATEGIES):
    print(f"   [{i}] {strat.name}")

# 选择布林带策略（index 0）
strategy = STRATEGIES[0]
print(f"\n✅ 选中策略：{strategy.name}")

# 生成回测信号
try:
    signal_data = strategy.backtest(test_data.copy(), {
        'boll_period': 20,
        'boll_std': 2,
        'buy_ratio': 0.5
    })
    print(f"✅ 策略信号生成成功，输出列：{list(signal_data.columns)}")
except Exception as e:
    print(f"❌ 策略信号生成失败: {e}")
    sys.exit(1)

# ========== 第三步：测试高级模拟器 ==========
print("\n" + "=" * 80)
print("🔬 高级模拟器参数配置")
print("=" * 80)

# 配置 1：保守配置
config1 = ExchangeConfig(
    commission_rate=0.0005,      # 0.05% 佣金
    impact_coefficient=0.5,       # 市场冲击系数
    max_order_ratio=0.05          # 最多 5% 成交占比
)

simulator1 = AdvancedExchangeSimulator(config1)
print(f"\n配置 1（保守）：")
print(f"  - 佣金费率：{config1.commission_rate*100:.3f}%")
print(f"  - 冲击系数：{config1.impact_coefficient:.2f}")
print(f"  - 最大成交占比：{config1.max_order_ratio*100:.1f}%")

# ========== 第四步：执行模拟回测 ==========
print(f"\n⏳ 执行高级模拟回测...")

try:
    result_advanced = simulator1.run(
        signal_data,
        initial_capital=30000,
        strategy_name=strategy.name
    )
    print(f"✅ 回测执行成功！")
    print(f"   输出行数：{len(result_advanced)}")
    print(f"   输出列：{list(result_advanced.columns)}")
except Exception as e:
    print(f"❌ 回测失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ========== 第五步：分析回测结果 ==========
print("\n" + "=" * 80)
print("📊 回测结果分析")
print("=" * 80)

# 基础指标
final_equity = result_advanced['equity'].iloc[-1]
initial_capital = 30000
total_return = (final_equity - initial_capital) / initial_capital

print(f"\n💰 资金变化：")
print(f"   初始资金：${initial_capital:,.2f}")
print(f"   最终资金：${final_equity:,.2f}")
print(f"   总收益：${final_equity - initial_capital:+,.2f}")
print(f"   总收益率：{total_return:+.2%}")

# 成本分析
total_commission = result_advanced['commission_cost'].sum()
total_impact = result_advanced['market_impact_cost'].sum()
total_cost = total_commission + total_impact

print(f"\n💳 交易成本：")
print(f"   总佣金成本：${total_commission:,.2f}")
print(f"   总冲击成本：${total_impact:,.2f}")
print(f"   总交易成本：${total_cost:,.2f}")
print(f"   成本占比：{total_cost/final_equity*100:.2f}% of final capital")

# 交易统计
trades = result_advanced[result_advanced['trade_log'] != ""]
num_trades = len(trades)

print(f"\n📈 交易统计：")
print(f"   交易次数：{num_trades}")
if num_trades > 0:
    print(f"\n   最近 5 笔交易：")
    for idx, (date, row) in enumerate(trades.tail(5).iterrows()):
        print(f"      {date.strftime('%Y-%m-%d')}: {row['trade_log']}")

# 风险指标
daily_returns = result_advanced['equity'].pct_change().dropna()
if len(daily_returns) > 1:
    sharpe_ratio = (daily_returns.mean() / daily_returns.std() * np.sqrt(252))
    
    # 最大回撤
    cumulative_max = result_advanced['equity'].cummax()
    drawdown = (result_advanced['equity'] - cumulative_max) / cumulative_max
    max_drawdown = drawdown.min()
    
    print(f"\n⚠️ 风险指标：")
    print(f"   日均收益：{daily_returns.mean()*100:.3f}%")
    print(f"   日均波动：{daily_returns.std()*100:.3f}%")
    print(f"   夏普比率：{sharpe_ratio:.2f}")
    print(f"   最大回撤：{max_drawdown:.2%}")

# ========== 第六步：对比两种配置 ==========
print("\n" + "=" * 80)
print("🔍 激进配置 vs 保守配置对比")
print("=" * 80)

# 激进配置
config2 = ExchangeConfig(
    commission_rate=0.001,        # 0.1% 佣金（更高）
    impact_coefficient=1.0,       # 更强的冲击
    max_order_ratio=0.10          # 最多 10% 成交占比
)

simulator2 = AdvancedExchangeSimulator(config2)
print(f"\n配置 2（激进）：")
print(f"  - 佣金费率：{config2.commission_rate*100:.3f}%")
print(f"  - 冲击系数：{config2.impact_coefficient:.2f}")
print(f"  - 最大成交占比：{config2.max_order_ratio*100:.1f}%")

print(f"\n⏳ 执行激进配置回测...")
try:
    result_aggressive = simulator2.run(
        signal_data,
        initial_capital=30000,
        strategy_name=strategy.name
    )
    
    final_equity_agg = result_aggressive['equity'].iloc[-1]
    total_return_agg = (final_equity_agg - initial_capital) / initial_capital
    total_cost_agg = result_aggressive['commission_cost'].sum() + result_aggressive['market_impact_cost'].sum()
    
    print(f"\n📊 对比结果：")
    print(f"\n   配置 1（保守）：")
    print(f"      最终资金：${final_equity:,.2f}")
    print(f"      总收益率：{total_return:+.2%}")
    print(f"      交易成本：${total_cost:,.2f}")
    
    print(f"\n   配置 2（激进）：")
    print(f"      最终资金：${final_equity_agg:,.2f}")
    print(f"      总收益率：{total_return_agg:+.2%}")
    print(f"      交易成本：${total_cost_agg:,.2f}")
    
    print(f"\n   差异：")
    print(f"      成本差异：${total_cost_agg - total_cost:+,.2f}")
    print(f"      收益差异：${final_equity_agg - final_equity:+,.2f}")
    
except Exception as e:
    print(f"❌ 激进配置回测失败: {e}")

# ========== 第七步：验证平方根冲击模型 ==========
print("\n" + "=" * 80)
print("🔬 平方根市场冲击模型 - 数学验证")
print("=" * 80)

# 找一次交易，验证冲击计算
trades_with_impact = result_advanced[result_advanced['market_impact_cost'] != 0]
if len(trades_with_impact) > 0:
    trade_row = trades_with_impact.iloc[0]
    trade_date = trades_with_impact.index[0]
    
    # 获取交易日期的数据
    day_volume = signal_data.loc[trade_date, 'volume']
    close_price = signal_data.loc[trade_date, 'close']
    
    print(f"\n第一笔计算冲击的交易（{trade_date.strftime('%Y-%m-%d')}）：")
    print(f"   当日收盘价：${close_price:.2f}")
    print(f"   当日成交量：{day_volume:,.0f}")
    print(f"   市场冲击成本：${trade_row['market_impact_cost']:.2f}")
    print(f"   执行价格：${trade_row['execution_price']:.2f}")
    print(f"   价格差异：{(trade_row['execution_price']/close_price - 1)*100:+.3f}%")

print("\n" + "=" * 80)
print("✅ 高级交易所模拟器集成测试完成！")
print("=" * 80)
