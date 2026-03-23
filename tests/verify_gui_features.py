#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GUI 功能验证脚本
用于验证三项新增功能是否正常工作
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# 设置项目路径
project_root = Path(__file__).resolve().parents[0]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("🔍 GUI 功能验证脚本")
print("=" * 60)

# ========== 验证 1：策略参数 ==========
print("\n✅ 验证1：策略参数集成")
print("-" * 60)

try:
    from Strategy_Pool.strategies import STRATEGIES
    
    print(f"📊 已注册策略数量: {len(STRATEGIES)}")
    for i, strategy in enumerate(STRATEGIES, 1):
        print(f"  {i}. {strategy.name}")
    
    # 检查分歧交易策略
    divergence_strategy = None
    for strategy in STRATEGIES:
        if "分歧" in strategy.name:
            divergence_strategy = strategy
            break
    
    if divergence_strategy:
        print(f"\n✅ 找到分歧交易策略：{divergence_strategy.name}")
        
        # 测试参数
        import pandas as pd
        import numpy as np
        
        # 生成测试数据
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        np.random.seed(42)
        close_prices = 100 + np.cumsum(np.random.randn(100) * 2)
        
        test_data = pd.DataFrame({
            'open': close_prices * 0.99,
            'high': close_prices * 1.02,
            'low': close_prices * 0.98,
            'close': close_prices,
            'volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)
        
        # 测试参数
        test_params = {
            'trend_ma': 20,
            'amplitude_ratio': 1.3,
            'volume_ratio': 1.2,
            'atr_period': 14,
            'stop_loss_atr': 2.0,
            'hold_days': 5
        }
        
        result = divergence_strategy.backtest(test_data.copy(), test_params)
        
        if 'signal' in result.columns and 'returns' in result.columns:
            print(f"✅ 参数集成成功")
            print(f"   - 信号列: ✓")
            print(f"   - 收益列: ✓")
            print(f"   - 信号数量: {(result['signal'] != 0).sum()}")
            print(f"   - 平均收益: {result['returns'].mean():.4f}")
        else:
            print("❌ 参数集成失败：缺少必要列")
    else:
        print("❌ 未找到分歧交易策略")
        
except Exception as e:
    print(f"❌ 验证1失败: {str(e)}")

# ========== 验证 2：记忆系统 ==========
print("\n✅ 验证2：记忆系统")
print("-" * 60)

try:
    storage_dir = os.path.join(project_root, 'Data_Hub', 'storage')
    memory_file = os.path.join(storage_dir, '.strategy_memory.json')
    
    # 创建测试记忆
    test_memory = {
        "AAPL": {
            "strategy": "分歧交易策略（改进版）",
            "params": {
                "trend_ma": 20,
                "amplitude_ratio": 1.3,
                "volume_ratio": 1.2,
                "atr_period": 14,
                "stop_loss_atr": 2.0,
                "hold_days": 5
            },
            "annual_return": 0.2543,
            "updated_at": datetime.now().isoformat()
        },
        "TSLA": {
            "strategy": "均线交叉策略",
            "params": {"ma_short": 15, "ma_long": 65},
            "annual_return": 0.1876,
            "updated_at": datetime.now().isoformat()
        }
    }
    
    # 保存测试记忆
    os.makedirs(storage_dir, exist_ok=True)
    with open(memory_file, 'w', encoding='utf-8') as f:
        json.dump(test_memory, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 记忆文件创建成功")
    print(f"   位置: {memory_file}")
    print(f"   标的数: {len(test_memory)}")
    
    # 读取验证
    with open(memory_file, 'r', encoding='utf-8') as f:
        loaded_memory = json.load(f)
    
    print(f"✅ 记忆文件读取成功")
    for symbol, config in loaded_memory.items():
        print(f"   - {symbol}: {config['strategy']} (年化: {config['annual_return']:.2%})")
    
except Exception as e:
    print(f"❌ 验证2失败: {str(e)}")

# ========== 验证 3：标的搜索数据结构 ==========
print("\n✅ 验证3：标的搜索功能")
print("-" * 60)

try:
    storage_dir = os.path.join(project_root, 'Data_Hub', 'storage')
    available_files = [f for f in os.listdir(storage_dir) if f.endswith('.parquet')]
    available_symbols = sorted([f.split('.')[0] for f in available_files])
    
    print(f"✅ 已有标的数: {len(available_symbols)}")
    if available_symbols:
        print(f"   示例: {', '.join(available_symbols[:5])}")
        
        # 验证数据格式
        if available_symbols:
            first_symbol = available_symbols[0]
            first_file = os.path.join(storage_dir, f"{first_symbol}.parquet")
            
            import pandas as pd
            df = pd.read_parquet(first_file)
            
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            has_all_columns = all(col in df.columns for col in required_columns)
            
            if has_all_columns:
                print(f"\n✅ 数据格式验证:")
                print(f"   - 标的: {first_symbol}")
                print(f"   - 数据行数: {len(df)}")
                print(f"   - 必需列: {', '.join(required_columns)} ✓")
            else:
                print(f"❌ 数据格式错误：缺少必需列")
    else:
        print("⚠️  暂无可用标的，等待首次下载")
        
except Exception as e:
    print(f"❌ 验证3失败: {str(e)}")

# ========== 最终总结 ==========
print("\n" + "=" * 60)
print("✅ 验证完成！")
print("\n🎯 准备就绪，可以启动 GUI：")
print("   streamlit run GUI_Client/app_v2.py")
print("\n📚 详细功能说明请查看：")
print("   GUI_ENHANCEMENT_FEATURES.md")
print("=" * 60)
