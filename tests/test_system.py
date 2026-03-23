"""
快速测试脚本：验证数据结构和模块导入
"""

import sys
from pathlib import Path
import pandas as pd

# 确保导入路径
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 测试 1：检查数据结构
print("=" * 60)
print("测试 1: 检查数据结构")
print("=" * 60)

storage_dir = project_root / "Data_Hub" / "storage"
test_file = storage_dir / "AAPL.parquet"

if test_file.exists():
    df = pd.read_parquet(test_file)
    print(f"✅ 数据文件存在: {test_file}")
    print(f"  索引类型: {type(df.index)}")
    print(f"  索引名称: {df.index.name}")
    print(f"  数据形状: {df.shape}")
    print(f"  列名: {list(df.columns)}")
    print(f"  前 3 行:")
    print(df.head(3))
else:
    print(f"❌ 数据文件不存在: {test_file}")

# 测试 2：导入模块
print("\n" + "=" * 60)
print("测试 2: 导入模块")
print("=" * 60)

try:
    from Engine_Matrix.backtest_engine import BacktestEngine, BacktestConfig
    print("✅ BacktestEngine 导入成功")
except Exception as e:
    print(f"❌ BacktestEngine 导入失败: {e}")

try:
    from Strategy_Pool.strategies import STRATEGIES
    print(f"✅ STRATEGIES 导入成功，共 {len(STRATEGIES)} 个策略")
    for s in STRATEGIES:
        print(f"   - {s.name}")
except Exception as e:
    print(f"❌ STRATEGIES 导入失败: {e}")

# 测试 3：运行最小回测
print("\n" + "=" * 60)
print("测试 3: 运行最小回测")
print("=" * 60)

try:
    from Engine_Matrix.backtest_engine import BacktestEngine, BacktestConfig
    from Strategy_Pool.strategies import STRATEGIES
    
    strategy = STRATEGIES[0]
    engine = BacktestEngine(strategy, data_dir=str(storage_dir))
    
    config = BacktestConfig(
        symbol="AAPL",
        start_date="2020-01-01",
        end_date="2023-12-31",
        initial_capital=100000.0,
        strategy_params={"ma_short": 20, "ma_long": 60}
    )
    
    result = engine.run(config)
    
    print("✅ 回测成功！")
    print(f"   总收益率: {result.metrics['total_return']:.2%}")
    print(f"   夏普比率: {result.metrics['sharpe_ratio']:.2f}")
    print(f"   最大回撤: {result.metrics['max_drawdown']:.2%}")
    print(f"   交易次数: {result.metrics['num_trades']}")
    
except Exception as e:
    print(f"❌ 回测失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("所有测试完成")
print("=" * 60)
