"""
文件位置: Analytics/reporters/sharpe_rating.py
描述: 夏普比评级和可视化系统
功能: 5级评级 + 彩虹百分比图 + 详细优劣分析
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict
import plotly.graph_objects as go

class SharpeRating:
    """夏普比评级系统"""
    
    # 5级评级标准 - 使用从棕红色到绿色的梯度
    RATING_LEVELS = {
        '极好': {'range': (2.0, float('inf')), 'color': '#4CAF50', 'bg_color': '#E8F5E9', 'label': '极好', 'en': 'Excellent', 'emoji': '🟢'},
        '很好': {'range': (1.5, 2.0), 'color': '#66BB6A', 'bg_color': '#F1F8E9', 'label': '很好', 'en': 'Very Good', 'emoji': '🟢'},
        '良好': {'range': (1.0, 1.5), 'color': '#A1887F', 'bg_color': '#EFEBE9', 'label': '良好', 'en': 'Good', 'emoji': '🟡'},
        '一般': {'range': (0.5, 1.0), 'color': '#D7755F', 'bg_color': '#FFEBEE', 'label': '一般', 'en': 'Fair', 'emoji': '🟠'},
        '差':   {'range': (-float('inf'), 0.5), 'color': '#C62828', 'bg_color': '#FFCDD2', 'label': '差', 'en': 'Poor', 'emoji': '🔴'},
    }
    
    @classmethod
    def rate_sharpe(cls, sharpe_ratio: float) -> Dict:
        """
        评级单个夏普比
        
        Args:
            sharpe_ratio: 夏普比值
            
        Returns:
            {
                'rating': 评级,
                'color': 颜色,
                'label_cn': 中文标签,
                'label_en': 英文标签,
                'emoji': 表情符号,
                'percentile': 百分位，
                'description': 描述
            }
        """
        
        for rating, info in cls.RATING_LEVELS.items():
            min_val, max_val = info['range']
            if min_val <= sharpe_ratio < max_val:
                percentile = cls._calculate_percentile(sharpe_ratio, rating)
                description = cls._get_description(rating, sharpe_ratio)
                
                return {
                    'rating': rating,
                    'color': info['color'],
                    'bg_color': info['bg_color'],
                    'label_cn': info['label'],
                    'label_en': info['en'],
                    'emoji': info['emoji'],
                    'percentile': percentile,
                    'description': description,
                    'sharpe_ratio': round(sharpe_ratio, 4)
                }
        
        # 默认（不应该到达这里）
        return {
            'rating': '未知',
            'color': '#808080',
            'bg_color': '#F5F5F5',
            'label_cn': '未知',
            'label_en': 'Unknown',
            'emoji': '❓',
            'percentile': 0,
            'description': '无法评级',
            'sharpe_ratio': sharpe_ratio
        }
    
    @staticmethod
    def _calculate_percentile(sharpe_ratio: float, rating: str) -> int:
        """计算该评级内的百分位"""
        
        percentiles = {
            '极好': 95 + min((sharpe_ratio - 2.0) / 2.0 * 5, 5),  # 95-100
            '很好': 75 + (sharpe_ratio - 1.5) / 0.5 * 20,  # 75-95
            '良好': 50 + (sharpe_ratio - 1.0) / 0.5 * 25,  # 50-75
            '一般': 25 + (sharpe_ratio - 0.5) / 0.5 * 25,  # 25-50
            '差': (sharpe_ratio + 0.5) / 1.0 * 25  # 0-25
        }
        
        percentile = percentiles.get(rating, 50)
        return int(min(max(percentile, 0), 100))
    
    @staticmethod
    def _get_description(rating: str, sharpe_ratio: float) -> str:
        """获取评级描述"""
        
        descriptions = {
            '极好': f"夏普比为 {sharpe_ratio:.2f}，远超优秀水平。单位风险下收益最大化，风险调整后表现顶级。",
            '很好': f"夏普比为 {sharpe_ratio:.2f}，表现优秀。风险管理良好，收益与风险比例适当。",
            '良好': f"夏普比为 {sharpe_ratio:.2f}，风险收益比合理。策略可行但仍有较大改进空间。",
            '一般': f"夏普比为 {sharpe_ratio:.2f}，风险调整后收益一般。需要改进风险管理或策略参数。",
            '差': f"夏普比为 {sharpe_ratio:.2f}，风险调整后收益较差。强烈建议优化策略或更换思路。"
        }
        
        return descriptions.get(rating, "无法获取描述")
    
    @staticmethod
    def create_rainbow_chart(sharpe_ratio: float, symbol: str = "Strategy", height: int = 300) -> go.Figure:
        """
        创建彩虹百分比图
        
        Args:
            sharpe_ratio: 夏普比值
            symbol: 策略/标的名称
            height: 图表高度
            
        Returns:
            Plotly Figure
        """
        
        rating = SharpeRating.rate_sharpe(sharpe_ratio)
        
        # 创建仪表盘图
        fig = go.Figure(go.Indicator(
            mode="number+delta+gauge",
            value=sharpe_ratio,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': f"Sharpe Ratio | {symbol}"},
            gauge={
                'axis': {'range': [-1, 3]},
                'bar': {'color': rating['color'], 'thickness': 0.7},
                'steps': [
                    {'range': [-1, 0.5], 'color': '#FFCDD2'},      # 差 (浅红)
                    {'range': [0.5, 1.0], 'color': '#FFEBEE'},     # 一般 (更浅红)
                    {'range': [1.0, 1.5], 'color': '#EFEBE9'},     # 良好 (棕)
                    {'range': [1.5, 2.0], 'color': '#F1F8E9'},     # 很好 (浅绿)
                    {'range': [2.0, 3], 'color': '#E8F5E9'},       # 极好 (绿)
                ],
                'threshold': {
                    'line': {'color': 'black', 'width': 2},
                    'thickness': 0.75,
                    'value': sharpe_ratio
                }
            }
        ))
        
        # 添加评级标签
        fig.add_annotation(
            text=(f"<b>{rating['emoji']} {rating['label_cn']}</b>"
                  f"<br>{rating['label_en']}"
                  f"<br>百分位: {rating['percentile']}%"),
            x=0.5, y=-0.3,
            showarrow=False,
            font=dict(size=12, color=rating['color'])
        )
        
        # 更新布局
        fig.update_layout(
            height=height,
            template="plotly_dark",
            font=dict(size=12),
            margin=dict(l=50, r=50, t=80, b=80)
        )
        
        return fig
    
    @staticmethod
    def create_detailed_rating_card(sharpe_ratio: float, 
                                   symbol: str = "Strategy",
                                   additional_metrics: Dict = None) -> str:
        """
        创建详细评级卡片（HTML格式，简洁设计）
        
        Args:
            sharpe_ratio: 夏普比值
            symbol: 策略/标的名称
            additional_metrics: 额外指标 {'total_return': ..., 'win_rate': ...}
            
        Returns:
            HTML字符串
        """
        
        rating = SharpeRating.rate_sharpe(sharpe_ratio)
        
        # 基础卡片 - 简洁设计
        html = f"""
        <div style="
            background: {rating['bg_color']};
            border-left: 5px solid {rating['color']};
            border-radius: 4px;
            padding: 12px 16px;
            margin: 8px 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <h3 style="color: {rating['color']}; margin: 0; font-size: 16px;">
                    {rating['emoji']} {rating['label_cn']} ({rating['label_en']})
                </h3>
                <div style="text-align: right;">
                    <span style="font-size: 24px; font-weight: bold; color: {rating['color']};">{sharpe_ratio:.2f}</span>
                    <span style="color: #999; font-size: 12px; margin-left: 8px;">第 {rating['percentile']} 百分位</span>
                </div>
            </div>
            
            <p style="color: #555; font-size: 13px; margin: 0; line-height: 1.5;">
                {rating['description']}
            </p>
        """
        
        # 额外指标显示 - 更紧凑
        if additional_metrics:
            html += """
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px; font-size: 12px;">
            """
            
            metric_cn = {
                'total_return': '总收益率',
                'annual_return': '年化收益',
                'max_drawdown': '最大回撤',
                'win_rate': '胜率',
                'num_trades': '交易次数'
            }
            
            for metric_name, metric_value in list(additional_metrics.items())[:4]:  # 只显示前4个指标
                if isinstance(metric_value, (int, float)):
                    if 'return' in metric_name.lower() or 'rate' in metric_name.lower() or 'drawdown' in metric_name.lower():
                        display_value = f"{metric_value:.2%}"
                    else:
                        display_value = f"{metric_value:.0f}" if metric_name == 'num_trades' else f"{metric_value:.4f}"
                else:
                    display_value = str(metric_value)
                
                metric_label = metric_cn.get(metric_name, metric_name)
                html += f"""
                <div style="display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid rgba(0,0,0,0.1);">
                    <span style="color: #777;">{metric_label}</span>
                    <span style="color: #333; font-weight: 500;">{display_value}</span>
                </div>
                """
            
            html += "</div>"
        
        html += "</div>"
        
        return html


class SharpeRatingComparison:
    """夏普比对比分析"""
    
    @staticmethod
    def compare_strategies(strategies_sharpe: Dict[str, float]) -> pd.DataFrame:
        """
        对比多个策略的夏普比
        
        Args:
            strategies_sharpe: {'strategy_name': sharpe_ratio}
            
        Returns:
            DataFrame with ratings, colors, etc.
        """
        
        results = []
        for strategy_name, sharpe_ratio in sorted(strategies_sharpe.items(), 
                                                   key=lambda x: x[1], 
                                                   reverse=True):
            rating = SharpeRating.rate_sharpe(sharpe_ratio)
            results.append({
                '策略': strategy_name,
                '夏普比': sharpe_ratio,
                '评级': rating['label_cn'],
                '百分位': rating['percentile'],
                '颜色': rating['color']
            })
        
        return pd.DataFrame(results)
    
    @staticmethod
    def create_comparison_chart(strategies_sharpe: Dict[str, float]) -> go.Figure:
        """创建策略对比柱状图"""
        
        df = SharpeRatingComparison.compare_strategies(strategies_sharpe)
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df['策略'],
            y=df['夏普比'],
            marker=dict(
                color=df['颜色']
            ),
            text=[f"{v:.2f}" for v in df['夏普比']],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Sharpe Ratio: %{y:.4f}<extra></extra>',
            name='Sharpe Ratio'
        ))
        
        # 添加参考线
        fig.add_hline(y=2.0, line_dash="dash", line_color="green", annotation_text="极好 (2.0)")
        fig.add_hline(y=1.5, line_dash="dash", line_color="yellowgreen", annotation_text="很好 (1.5)")
        fig.add_hline(y=1.0, line_dash="dash", line_color="gold", annotation_text="良好 (1.0)")
        fig.add_hline(y=0.5, line_dash="dash", line_color="orange", annotation_text="一般 (0.5)")
        
        fig.update_layout(
            title="策略夏普比对比 | Strategy Sharpe Ratio Comparison",
            xaxis_title="策略 | Strategy",
            yaxis_title="夏普比 | Sharpe Ratio",
            template="plotly_dark",
            height=500,
            hovermode='x unified'
        )
        
        return fig
