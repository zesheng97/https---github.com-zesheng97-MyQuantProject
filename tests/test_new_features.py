"""
文件位置: test_new_features.py
描述: 演示新增功能的测试脚本
功能: 展示周期性检测、夏普比评级、数据下载等功能
"""

import os
import sys
from pathlib import Path
import pandas as pd

# 处理编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 项目路径配置
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Analytics.reporters.periodicity_analyzer import PeriodicityAnalyzer
from Analytics.reporters.sharpe_rating import SharpeRating, SharpeRatingComparison

def test_periodicity_analysis():
    """测试周期性分析"""
    print("\n" + "="*80)
    print("🔄 周期性分析功能演示")
    print("="*80)
    
    try:
        storage_dir = os.path.join(project_root, 'Data_Hub', 'storage')
        
        # 加载几个样本股票
        sample_symbols = ['AAPL', 'MSFT', 'TSLA']
        
        for symbol in sample_symbols:
            file_path = os.path.join(storage_dir, f"{symbol}.parquet")
            if os.path.exists(file_path):
                df = pd.read_parquet(file_path)
                
                # 周期性分析
                analyzer = PeriodicityAnalyzer(threshold=0.7)
                result = analyzer.analyze(df['close'], name=symbol)
                
                print(f"\n📊 {symbol} 周期性分析结果：")
                print(f"   综合评分: {result['periodicity_score']:.4f}")
                print(f"   FFT分数: {result['fft_score']:.4f}")
                print(f"   小波分数: {result['wavelet_score']:.4f}")
                print(f"   KPSS分数: {result['kpss_score']:.4f}")
                print(f"   主周期(FFT): {result['dominant_period_fft']} 天")
                print(f"   主周期(小波): {result['dominant_period_wavelet']} 天")
                print(f"   是否强周期性: {'✅ 是' if result['is_periodic'] else '❌ 否'}")
        
        print("\n✅ 周期性分析测试完成！")
        
    except Exception as e:
        print(f"❌ 周期性分析测试失败: {e}")

def test_sharpe_rating():
    """测试夏普比评级"""
    print("\n" + "="*80)
    print("🎯 夏普比评级功能演示")
    print("="*80)
    
    # 测试不同级别的夏普比
    test_cases = [
        ("极优秀策略", 2.5),
        ("优秀策略", 1.8),
        ("良好策略", 1.2),
        ("一般策略", 0.8),
        ("较差策略", 0.3),
    ]
    
    print("\n评级示例：")
    print("-" * 80)
    
    for strategy_name, sharpe_ratio in test_cases:
        rating = SharpeRating.rate_sharpe(sharpe_ratio)
        print(f"\n{strategy_name}")
        print(f"  夏普比: {sharpe_ratio:.2f}")
        print(f"  评级: {rating['label_cn']} ({rating['label_en']})")
        print(f"  百分位: {rating['percentile']}%")
        print(f"  描述: {rating['description'][:50]}...")
    
    # 对比示例
    print("\n\n📊 策略对比示例：")
    print("-" * 80)
    
    strategies_data = {
        '布林带策略': 1.2,
        '均线交叉策略': 0.8,
        '周期性趋势交易': 1.6,
        '分歧交易策略': 1.1
    }
    
    df_comparison = SharpeRatingComparison.compare_strategies(strategies_data)
    print("\n排名（从高到低）:")
    for idx, row in df_comparison.iterrows():
        print(f"  {idx+1}. {row['策略']}: {row['夏普比']:.2f} ({row['评级']}, 百分位: {row['百分位']}%)")
    
    print("\n✅ 夏普比评级测试完成！")

def test_data_availability():
    """检查数据库」"""
    print("\n" + "="*80)
    print("📦 数据库状态检查")
    print("="*80)
    
    storage_dir = os.path.join(project_root, 'Data_Hub', 'storage')
    
    try:
        files = [f for f in os.listdir(storage_dir) if f.endswith('.parquet')]
        symbols = sorted([f.replace('.parquet', '') for f in files])
        
        print(f"\n✅ 数据库包含 {len(symbols)} 个标的")
        print(f"\n样本标的 (前20个):")
        for i, symbol in enumerate(symbols[:20], 1):
            file_path = os.path.join(storage_dir, f"{symbol}.parquet")
            df = pd.read_parquet(file_path)
            data_len = len(df)
            date_range = f"{df.index[0].date()} ~ {df.index[-1].date()}"
            print(f"  {i:2d}. {symbol:6s} - {data_len:6d} 条数据 ({date_range})")
        
        if len(symbols) > 20:
            print(f"\n  ... 还有 {len(symbols) - 20} 个标的")
        
    except Exception as e:
        print(f"❌ 检查数据库失败: {e}")

def show_feature_roadmap():
    """展示新增功能列表"""
    print("\n" + "="*80)
    print("🚀 本次更新的新增功能")
    print("="*80)
    
    features = {
        "1. 数据库扩展": [
            "✅ S&P 500成分股批量下载脚本 (download_sp500_nasdaq100.py)",
            "✅ Nasdaq 100成分股批量下载脚本",
            "✅ 智能增量下载（自动避免重复）",
            "✅ IPO日期作为下载起点"
        ],
        
        "2. 周期性检测模块": [
            "✅ FFT (快速傅里叶变换) 周期分析",
            "✅ 小波变换 (CWT) 周期分析",
            "✅ KPSS统计周期性测试",
            "✅ 综合评分系统 (0-1，>0.7为强周期性)",
            "✅ 主周期自动识别"
        ],
        
        "3. 周期性交易策略": [
            "✅ 周期性趋势交易策略",
            "  → 识别周期高低点，趋势跟踪",
            "✅ 周期性均值回归策略",
            "  → 周期内超买超卖交易",
            "✅ 周期相位对齐策略",
            "  → 基于周期相位的精准交易"
        ],
        
        "4. 夏普比评级与可视化": [
            "✅ 5级评级系统",
            "  → 极好(2.0+) / 很好(1.5-2.0) / 良好(1.0-1.5) / 一般(0.5-1.0) / 差(<0.5)",
            "✅ 彩虹仪表盘可视化图表",
            "✅ 详细评级卡片（带百分位信息）",
            "✅ 策略对比功能",
            "✅ Sharpe Ratio重点关注所有策略"
        ],
        
        "5. GUI增强": [
            "✅ 数据预览中的周期性分析显示",
            "✅ 回测结果中的Sharpe等级彩虹图",
            "✅ 所有策略的参数配置支持",
            "✅ 周期性策略的动态参数调整"
        ]
    }
    
    for category, items in features.items():
        print(f"\n{category}")
        for item in items:
            print(f"  {item}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    show_feature_roadmap()
    test_data_availability()
    test_periodicity_analysis()
    test_sharpe_rating()
    
    print("\n" + "="*80)
    print("✅ 所有测试完成！")
    print("="*80)
    print("\n📖 使用说明:")
    print("  1. 下载S&P 500 & Nasdaq 100: python download_sp500_nasdaq100.py")
    print("  2. 启动GUI: streamlit run run_gui.py")
    print("  3. 在GUI中选择策略并观察周期性分析和Sharpe评级")
    print("\n")
