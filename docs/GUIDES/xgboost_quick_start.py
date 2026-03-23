#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
XGBoost ML Strategy - 快速启动示例

演示如何：
1. 训练一个新的 XGBoost 模型
2. 查看历史模型排行
3. 加载和使用已训练的模型
"""

import pandas as pd
import os
import sys
from pathlib import Path

# 确保导入路径正确
project_root = Path(__file__).resolve().parents[0]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Strategy_Pool.custom.xgboost_ml_strategy import XGBoostMLStrategy, ModelRegistry


def main():
    """主函数"""
    
    # 获取项目路径
    project_root = Path(__file__).resolve().parents[0]
    storage_dir = project_root / "Data_Hub" / "storage"
    
    print("=" * 80)
    print("🚀 XGBoost ML Strategy - 快速启动示例")
    print("=" * 80)
    
    # ========== 步骤 1: 检查可用数据 ==========
    print("\n📊 步骤 1: 检查可用数据")
    print("-" * 80)
    
    if not storage_dir.exists():
        print(f"❌ 数据目录不存在: {storage_dir}")
        print("💡 请先运行 main.py 或 download_sp500_nasdaq100.py 下载数据")
        return
    
    available_files = [f for f in os.listdir(storage_dir) if f.endswith('.parquet')]
    if not available_files:
        print(f"❌ 数据目录为空: {storage_dir}")
        return
    
    available_symbols = [f.split('.')[0] for f in available_files[:5]]
    print(f"✅ 可用数据（示例）: {', '.join(available_symbols)}")
    
    # ========== 步骤 2: 选择数据 ==========
    print("\n📈 步骤 2: 选择用于演示的数据")
    print("-" * 80)
    
    demo_symbol = available_symbols[0]
    data_path = storage_dir / f"{demo_symbol}.parquet"
    
    print(f"正在加载: {demo_symbol}")
    df = pd.read_parquet(data_path)
    print(f"✅ 加载成功")
    print(f"   - 数据行数: {len(df)}")
    print(f"   - 时间范围: {df.index.min().date()} 至 {df.index.max().date()}")
    print(f"   - 列: {', '.join(df.columns.tolist())}")
    
    # ========== 步骤 3: 训练演示 ==========
    print("\n🤖 步骤 3: 训练 XGBoost 模型（演示模式）")
    print("-" * 80)
    print("⚠️  演示模式：使用前 500 个样本加快演示")
    
    df_demo = df.head(500)
    
    print("\n初始化策略...")
    strategy = XGBoostMLStrategy(
        model_id=None,           # 训练模式
        time_limit=60,           # 仅 60 秒用于演示
        target_limit=20          # 早停条件  
    )
    print("✅ 策略初始化完成")
    
    print("\n开始训练...")
    try:
        result_df = strategy.backtest(df_demo, params={})
        print("✅ 训练完成！")
        print(f"   - 返回信号数: {len(result_df)}")
        print(f"   - 信号列: {result_df['signal'].value_counts().to_dict()}")
    except Exception as e:
        print(f"❌ 训练失败: {e}")
        print("💡 确保已安装 xgboost: pip install xgboost")
        return
    
    # ========== 步骤 4: 查询模型排行 ==========
    print("\n🏆 步骤 4: 查询历史模型排行")
    print("-" * 80)
    
    top_models = ModelRegistry.get_ranked_models(top_n=5)
    
    if top_models.empty:
        print("❌ 注册中心为空")
    else:
        print("\n表现最好的 5 个模型：\n")
        display_cols = ['model_id', 'performance_score', 'validation_accuracy', 'features_count', 'training_time']
        available_cols = [c for c in display_cols if c in top_models.columns]
        
        for idx, row in top_models[available_cols].iterrows():
            print(f"{idx+1}. {row['model_id']}")
            print(f"   性能分数: {row.get('performance_score', 'N/A')}")
            print(f"   准确率: {row.get('validation_accuracy', 'N/A')}")
            print(f"   特征数: {row.get('features_count', 'N/A')}")
            print(f"   耗时: {row.get('training_time', 'N/A')}s\n")
    
    # ========== 步骤 5: 推理演示 ==========
    print("\n⚡ 步骤 5: 推理模式演示")
    print("-" * 80)
    
    if not top_models.empty:
        best_model_id = top_models.iloc[0]['model_id']
        print(f"加载最优模型: {best_model_id}")
        
        try:
            strategy_inference = XGBoostMLStrategy(
                model_id=best_model_id  # 推理模式
            )
            print("✅ 模型加载成功")
            
            # 演示推理
            df_test = df.tail(100)
            print(f"\n对 {len(df_test)} 个样本进行推理...")
            
            result_inference = strategy_inference.backtest(df_test, params={})
            print("✅ 推理完成")
            print(f"   - 买入信号: {(result_inference['signal'] == 1).sum()} 次")
            print(f"   - 卖出信号: {(result_inference['signal'] == -1).sum()} 次")
            
        except Exception as e:
            print(f"⚠️  推理失败: {e}")
    else:
        print("⚠️  无历史模型，跳过推理演示")
    
    # ========== 总结 ==========
    print("\n" + "=" * 80)
    print("✅ 演示完成！")
    print("=" * 80)
    print("\n📖 后续步骤：")
    print("1. 打开 Streamlit GUI:")
    print("   streamlit run GUI_Client/run_gui.py")
    print("\n2. 在 GUI 中：")
    print("   - 选择 XGBoost机器学习策略")
    print("   - 勾选'使用历史最优模型'")
    print("   - 选择排名第一的模型")
    print("   - 点击'运行回测'查看完整回测结果")
    print("\n3. 阅读完整文档:")
    print("   Strategy_Pool/custom/XGBOOST_ML_STRATEGY_GUIDE.md")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
