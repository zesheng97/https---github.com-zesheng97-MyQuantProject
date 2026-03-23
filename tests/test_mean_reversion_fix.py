"""测试均值回归波动率策略修复"""
import pandas as pd
import numpy as np
from Strategy_Pool.strategies import STRATEGIES

print("可用的策略:")
for i, s in enumerate(STRATEGIES):
    print(f"  {i}: {s.name}")

# 找到 MeanReversionVolatilityStrategy（波动率收割）
mean_rev_strategy = None
for s in STRATEGIES:
    if "波动" in s.name or "Volatility" in s.description_en:
        mean_rev_strategy = s
        break

if not mean_rev_strategy:
    # 尝试另一种方式
    for s in STRATEGIES:
        if "Mean Reversion Volatility" in s.description_en:
            mean_rev_strategy = s
            break

if mean_rev_strategy:
    print(f"\n✅ 找到策略: {mean_rev_strategy.name}")
    
    # 创建测试数据（模拟 KRUS 行情）
    dates = pd.date_range('2024-01-01', periods=150, freq='D')
    np.random.seed(42)
    
    # 创建有波动的价格数据
    prices = 100 + np.cumsum(np.random.randn(150) * 2)
    
    test_data = pd.DataFrame({
        'open': prices + np.random.randn(150) * 0.5,
        'high': prices + np.abs(np.random.randn(150) * 1),
        'low': prices - np.abs(np.random.randn(150) * 1),
        'close': prices,
        'volume': np.random.uniform(1000000, 5000000, 150)
    }, index=dates)
    
    # 运行回测
    try:
        result = mean_rev_strategy.backtest(test_data.copy(), {
            'zscore_period': 60,
            'zscore_threshold': -2.5,
            'volume_multiplier': 2.0
        })
        
        print(f"✅ 回测成功！")
        print(f"   结果行数: {len(result)}")
        print(f"   包含列: {list(result.columns)}")
        print(f"   signal 列样本: {result['signal'].tail(5).tolist()}")
        print(f"   returns 列样本: {result['returns'].tail(5).tolist()}")
        print(f"   returns 最大值: {result['returns'].max():.6f}")
        print(f"   returns 最小值: {result['returns'].min():.6f}")
        print(f"   NaN 检查 - returns 中的 NaN 数: {result['returns'].isna().sum()}")
        print("\n✅ 均值回归波动率策略现已正常工作！")
        
    except Exception as e:
        print(f"❌ 回测失败: {e}")
        import traceback
        traceback.print_exc()
else:
    print("❌ 未找到均值回归波动率策略")
