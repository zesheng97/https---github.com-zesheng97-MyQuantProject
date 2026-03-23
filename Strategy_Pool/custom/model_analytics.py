# Model Registry Analysis Tools
# 模型注册中心分析工具

import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple
import json
from datetime import datetime
import warnings

class ModelAnalytics:
    """模型性能分析工具"""
    
    def __init__(self, registry_path: str = "Data_Hub/model_registry"):
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self.registry_csv = self.registry_path / "registry.csv"
        
    def _load_registry(self) -> pd.DataFrame:
        """加载注册表 CSV"""
        if not self.registry_csv.exists():
            return pd.DataFrame()
        return pd.read_csv(self.registry_csv)
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        df = self._load_registry()
        
        if df.empty:
            return {
                'total_models': 0,
                'avg_accuracy': None,
                'avg_return': None,
                'avg_performance_score': None,
                'avg_training_time': None
            }
        
        return {
            'total_models': len(df),
            'avg_accuracy': df['validation_accuracy'].mean(),
            'avg_return': df['simulation_return'].mean(),
            'avg_performance_score': df['performance_score'].mean(),
            'avg_training_time': df['training_time'].mean(),
            'max_accuracy': df['validation_accuracy'].max(),
            'max_return': df['simulation_return'].max(),
            'max_performance_score': df['performance_score'].max()
        }
    
    def print_summary(self):
        """打印统计摘要"""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("📊 XGBoost 模型注册中心 - 统计摘要")
        print("="*60)
        
        if stats['total_models'] == 0:
            print("❌ 尚无训练的模型")
            return
        
        print(f"✅ 总模型数:          {stats['total_models']}")
        print(f"📈 平均验证准确率:    {stats['avg_accuracy']:.4f}")
        print(f"📊 平均模拟收益率:    {stats['avg_return']:.4f}")
        print(f"⭐ 平均性能分数:      {stats['avg_performance_score']:.4f}")
        print(f"⏱️  平均训练时间:      {stats['avg_training_time']:.1f}s")
        print()
        print(f"🏆 最高验证准确率:    {stats['max_accuracy']:.4f}")
        print(f"🚀 最高模拟收益率:    {stats['max_return']:.4f}")
        print(f"⭐ 最高性能分数:      {stats['max_performance_score']:.4f}")
        print("="*60 + "\n")
    
    def get_model_perf_distribution(self, bins: int = 5) -> Dict:
        """获取性能分数分布"""
        df = self._load_registry()
        
        if df.empty:
            return {}
        
        counts, bin_edges = np.histogram(df['performance_score'], bins=bins)
        
        distribution = {}
        for i in range(len(counts)):
            key = f"{bin_edges[i]:.2f}-{bin_edges[i+1]:.2f}"
            distribution[key] = int(counts[i])
        
        return distribution
    
    def plot_text_distribution(self):
        """文本形式展示性能分布（不依赖 matplotlib）"""
        distribution = self.get_model_perf_distribution(bins=10)
        
        if not distribution:
            print("❌ 无数据")
            return
        
        print("\n📊 性能分数分布 (文本直方图)")
        print("-" * 50)
        
        max_count = max(distribution.values()) if distribution else 1
        
        for range_label, count in distribution.items():
            bar_length = int((count / max_count) * 30) if max_count > 0 else 0
            bar = "█" * bar_length
            print(f"{range_label} | {bar} ({count})")
        
        print("-" * 50 + "\n")
    
    def get_top_features(self, top_n: int = 5) -> Dict:
        """获取最常使用的特征组合"""
        df = self._load_registry()
        
        if df.empty:
            return {}
        
        feature_freq = defaultdict(int)
        
        for features_str in df['features_list']:
            try:
                features = eval(features_str)  # 解析列表字符串
                for feat in features:
                    feature_freq[feat] += 1
            except:
                pass
        
        # 按频率排序
        top_features = sorted(
            feature_freq.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        return dict(top_features)
    
    def print_top_features(self, top_n: int = 10):
        """打印热门特征"""
        features = self.get_top_features(top_n)
        
        if not features:
            print("❌ 无数据")
            return
        
        print("\n🔥 最常使用的特征（频次排序）")
        print("-" * 40)
        
        max_freq = max(features.values()) if features else 1
        
        for feat, freq in features.items():
            bar_length = int((freq / max_freq) * 20) if max_freq > 0 else 0
            bar = "▓" * bar_length
            print(f"{feat:20s} | {bar} ({freq})")
        
        print("-" * 40 + "\n")
    
    def get_training_time_stats(self) -> Dict:
        """获取训练时间统计"""
        df = self._load_registry()
        
        if df.empty:
            return {}
        
        return {
            'median': df['training_time'].median(),
            'mean': df['training_time'].mean(),
            'min': df['training_time'].min(),
            'max': df['training_time'].max(),
            'std': df['training_time'].std()
        }
    
    def print_timing_analysis(self):
        """打印训练时间分析"""
        stats = self.get_training_time_stats()
        
        if not stats:
            print("❌ 无数据")
            return
        
        print("\n⏱️  训练时间分析")
        print("-" * 40)
        print(f"平均时间:    {stats['mean']:.1f}s")
        print(f"中位数:      {stats['median']:.1f}s")
        print(f"范围:        {stats['min']:.1f}s - {stats['max']:.1f}s")
        print(f"标准差:      {stats['std']:.1f}s")
        print("-" * 40 + "\n")
    
    def export_html_report(self, output_path: str = "model_report.html"):
        """导出 HTML 报告"""
        stats = self.get_statistics()
        df = self._load_registry()
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>XGBoost 模型分析报告</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #34495e;
                    margin-top: 30px;
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin: 20px 0;
                }}
                .stat-card {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                }}
                .stat-value {{
                    font-size: 24px;
                    font-weight: bold;
                    margin: 10px 0;
                }}
                .stat-label {{
                    font-size: 12px;
                    opacity: 0.9;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th {{
                    background-color: #3498db;
                    color: white;
                    padding: 12px;
                    text-align: left;
                }}
                td {{
                    padding: 10px 12px;
                    border-bottom: 1px solid #ddd;
                }}
                tr:hover {{
                    background-color: #f9f9f9;
                }}
                .footer {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 XGBoost 模型分析报告</h1>
                <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <h2>📈 关键指标</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-label">总模型数</div>
                        <div class="stat-value">{stats.get('total_models', 0)}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">平均性能分数</div>
                        <div class="stat-value">{stats.get('avg_performance_score', 0):.4f}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">平均验证准确率</div>
                        <div class="stat-value">{stats.get('avg_accuracy', 0):.4f}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">平均训练时间</div>
                        <div class="stat-value">{stats.get('avg_training_time', 0):.1f}s</div>
                    </div>
                </div>
                
                <h2>📋 最近训练的模型</h2>
                <table>
                    <tr>
                        <th>模型 ID</th>
                        <th>性能分数</th>
                        <th>验证准确率</th>
                        <th>模拟收益率</th>
                        <th>训练时间</th>
                        <th>时间戳</th>
                    </tr>
        """
        
        for idx, row in df.tail(20).iterrows():
            html_content += f"""
                    <tr>
                        <td><code>{row['model_id']}</code></td>
                        <td>{row['performance_score']:.4f}</td>
                        <td>{row['validation_accuracy']:.4f}</td>
                        <td>{row['simulation_return']:.4f}</td>
                        <td>{row['training_time']:.1f}s</td>
                        <td>{row['timestamp']}</td>
                    </tr>
            """
        
        html_content += """
                </table>
                
                <div class="footer">
                    <p>此报告由 XGBoost ML Strategy 自动生成</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ 报告已导出: {output_path}")
    
    def detect_outliers(self, threshold_std: float = 2.0) -> pd.DataFrame:
        """检测异常模型"""
        df = self._load_registry()
        
        if df.empty:
            return pd.DataFrame()
        
        # 计算性能分数的异常值
        mean = df['performance_score'].mean()
        std = df['performance_score'].std()
        
        outliers = df[
            (df['performance_score'] > mean + threshold_std * std) |
            (df['performance_score'] < mean - threshold_std * std)
        ][['model_id', 'performance_score', 'validation_accuracy', 'training_time']]
        
        return outliers
    
    def print_outlier_detection(self):
        """打印异常模型分析"""
        outliers = self.detect_outliers()
        
        if outliers.empty:
            print("✅ 未检测到异常模型")
            return
        
        print("\n⚠️  检测到异常模型")
        print("-" * 60)
        for idx, row in outliers.iterrows():
            print(f"  {row['model_id']} | 性能分数: {row['performance_score']:.4f} | 准确率: {row['validation_accuracy']:.4f}")
        print("-" * 60 + "\n")


def run_full_analysis():
    """运行完整分析"""
    analytics = ModelAnalytics()
    
    print("\n" + "🔍 开始模型分析...\n")
    
    analytics.print_summary()
    analytics.plot_text_distribution()
    analytics.print_top_features(top_n=7)
    analytics.print_timing_analysis()
    analytics.print_outlier_detection()
    
    # 导出 HTML 报告
    analytics.export_html_report("model_analysis_report.html")
    
    print("📊 分析完成！\n")


if __name__ == "__main__":
    run_full_analysis()
