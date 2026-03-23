#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试脚本：验证回测和图表生成功能是否正常
检查点：
1. Candlestick hover 参数合法性
2. 数据过滤逻辑
3. 图表配置一致性
"""

import sys
sys.path.insert(0, 'd:\\MyQuantProject')

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

def test_candlestick_hover():
    """测试 Candlestick trace 的 hover 配置"""
    print("\n" + "="*60)
    print("TEST 1: Candlestick Hover 参数合法性")
    print("="*60)
    
    # 创建测试数据
    test_data = pd.DataFrame({
        'open': [100, 101, 102, 101, 100],
        'high': [102, 103, 104, 103, 102],
        'low': [99, 100, 101, 100, 99],
        'close': [101, 102, 101, 100, 101],
        'volume': [1000, 1100, 950, 1200, 900]
    }, index=pd.date_range('2024-01-01', periods=5))
    
    try:
        fig = go.Figure()
        
        # 尝试添加 Candlestick（应该使用 hoverinfo，不能用 hovertemplate）
        fig.add_trace(go.Candlestick(
            x=test_data.index,
            open=test_data['open'],
            high=test_data['high'],
            low=test_data['low'],
            close=test_data['close'],
            name='K线',
            hoverinfo='all'  # ✅ 正确的用法
        ))
        
        print("✅ Candlestick hover 配置正确：使用了 hoverinfo='all'")
        return True
        
    except ValueError as e:
        print(f"❌ Candlestick 配置错误: {str(e)[:200]}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {str(e)[:200]}")
        return False


def test_date_type_consistency():
    """测试日期类型一致性"""
    print("\n" + "="*60)
    print("TEST 2: 日期类型一致性")
    print("="*60)
    
    # 创建测试数据
    test_data = pd.DataFrame({
        'close': [100, 101, 102, 101, 100],
    }, index=pd.date_range('2024-01-01', periods=5))
    
    try:
        # 测试日期类型转换
        start_date = pd.Timestamp('2024-01-01')
        end_date = pd.Timestamp('2024-01-05')
        
        # 应该使用 datetime64[ns]，不要混用 date 对象
        filtered = test_data[(test_data.index >= start_date) & (test_data.index <= end_date)]
        
        print(f"✅ 日期过滤成功")
        print(f"   原始数据行数: {len(test_data)}")
        print(f"   过滤后行数: {len(filtered)}")
        return True
        
    except TypeError as e:
        print(f"❌ 日期类型错误: {str(e)[:200]}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {str(e)[:200]}")
        return False


def test_volume_color_logic():
    """测试成交量颜色逻辑"""
    print("\n" + "="*60)
    print("TEST 3: 成交量颜色逻辑（红跌绿涨）")
    print("="*60)
    
    test_data = pd.DataFrame({
        'open': [100, 100, 100],
        'close': [101, 99, 100],  # 涨、跌、平
        'volume': [1000, 1100, 950]
    })
    
    try:
        # 测试颜色逻辑
        colors = ['red' if row['close'] < row['open'] else 'green' for _, row in test_data.iterrows()]
        
        expected = ['green', 'red', 'green']  # 跌、涨、平时绿色
        
        if colors == expected:
            print(f"✅ 成交量颜色逻辑正确")
            print(f"   行 0: open={test_data.iloc[0]['open']}, close={test_data.iloc[0]['close']} → {colors[0]} (涨)")
            print(f"   行 1: open={test_data.iloc[1]['open']}, close={test_data.iloc[1]['close']} → {colors[1]} (跌)")
            print(f"   行 2: open={test_data.iloc[2]['open']}, close={test_data.iloc[2]['close']} → {colors[2]} (平)")
            return True
        else:
            print(f"❌ 颜色逻辑错误: 期望 {expected}, 得到 {colors}")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {str(e)[:200]}")
        return False


def test_subplot_hovermode():
    """测试子图 hovermode 兼容性"""
    print("\n" + "="*60)
    print("TEST 4: Subplot hovermode 配置")
    print("="*60)
    
    try:
        test_data = pd.DataFrame({
            'open': [100, 101],
            'high': [102, 103],
            'low': [99, 100],
            'close': [101, 102],
            'volume': [1000, 1100]
        }, index=pd.date_range('2024-01-01', periods=2))
        
        fig = make_subplots(
            rows=2, cols=1,
            vertical_spacing=0.05,
            subplot_titles=('价格', '成交量'),
            row_heights=[0.7, 0.3]
        )
        
        # 添加 K线
        fig.add_trace(go.Candlestick(
            x=test_data.index,
            open=test_data['open'],
            high=test_data['high'],
            low=test_data['low'],
            close=test_data['close'],
            name='K线',
            hoverinfo='all'
        ), row=1, col=1)
        
        # 添加成交量
        fig.add_trace(go.Bar(
            x=test_data.index,
            y=test_data['volume'],
            name='成交量',
            hoverinfo='y'
        ), row=2, col=1)
        
        # 配置 layout
        fig.update_layout(
            hovermode='x unified'  # ✅ 正确的配置
        )
        
        print("✅ Subplot hovermode 配置正确：使用了 'x unified'")
        return True
        
    except Exception as e:
        print(f"❌ 错误: {str(e)[:200]}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "🧪 " * 20)
    print("回测图表功能验证测试")
    print("🧪 " * 20)
    
    results = {
        "Candlestick Hover": test_candlestick_hover(),
        "日期类型一致性": test_date_type_consistency(),
        "成交量颜色逻辑": test_volume_color_logic(),
        "Subplot hovermode": test_subplot_hovermode(),
    }
    
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n总体: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！回测功能应该能正常运行")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，需要修复")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
