# 🚀 快速参考指南 | Quick Reference Guide

## 三句话总结本次更新

> 🎯 **从66个标的扩展到700+** | **自动检测周期性** | **Sharpe等级一目了然**

---

## 📦 新增功能快速列表

| 功能 | 脚本/模块 | 说明 |
|------|---------|------|
| **S&P 500下载** | `download_sp500_nasdaq100.py` | 一键下载500+标的，避免重复 |
| **Nasdaq 100下载** | `download_sp500_nasdaq100.py` | 一键下载100+标的 |
| **周期性检测** | `Analytics/reporters/periodicity_analyzer.py` | FFT+小波+统计，0.7阈值 |
| **周期性趋势交易** | `Strategy_Pool/custom/cyclical_strategies.py` | 周期高低点交易 |
| **周期性均值回归** | `Strategy_Pool/custom/cyclical_strategies.py` | 超买超卖回归交易 |
| **周期相位对齐** | `Strategy_Pool/custom/cyclical_strategies.py` | 相位精准交易 |
| **Sharpe 5级评级** | `Analytics/reporters/sharpe_rating.py` | 极好/很好/良好/一般/差 |
| **彩虹仪表盘** | `Analytics/reporters/sharpe_rating.py` | 交互式Sharpe可视化 |
| **GUI集成** | `GUI_Client/app_v2.py` | 数据预览+周期分析+Sharpe等级 |

---

## ⚡ 5分钟快速开始

### 1. 扩展数据库 (10-60分钟)
```bash
python download_sp500_nasdaq100.py
# 输出: 数据库从66 → 700+ 标的
```

### 2. 启动GUI (30秒)
```bash
streamlit run run_gui.py
# 开浏览器: http://localhost:8501
```

### 3. 体验新功能 (2分钟)
```
1. 选择标的 (如AAPL)
2. 自动看到周期性分析 [✅ 强周期/❌ 弱周期]
3. 选择周期性策略
4. 调参并回测
5. 看Sharpe等级 [彩虹仪表盘]
```

---

## 🔍 周期性检测一览

### 快速判断

| 周期性评分 | 含义 | 推荐策略 |
|----------|------|--------|
| **>0.80** | 🟢 强周期 | 周期性趋势交易/周期相位对齐 |
| **0.70-0.80** | 🟡 明显周期 | 周期性均值回归/周期交易 |
| **0.50-0.70** | 🟠 较弱周期 | 可搭配其他策略 |
| **<0.50** | 🔴 弱周期/趋势 | 使用趋势跟踪/均值回归 |

### 三种检测方法对比

```
FFT         : 快速、全局、容易过拟合
小波        : 时间-频率分离、捕捉变化
KPSS统计    : 自相关、严谨但较慢

最终评分 = 0.4×FFT + 0.4×小波 + 0.2×KPSS
```

---

## 📊 Sharpe评级速查表

| 等级 | 范围 | 百分位 | 评价 | 颜色 |
|------|------|--------|------|------|
| 🟢 极好 | ≥2.0 | 95-100% | 专业基金水准 | 绿 |
| 🟢 很好 | 1.5-2.0 | 75-95% | 优秀策略 | 浅绿 |
| 🟡 良好 | 1.0-1.5 | 50-75% | 可行方案 | 黄 |
| 🟠 一般 | 0.5-1.0 | 25-50% | 需要改进 | 橙 |
| 🔴 差 | <0.5 | 0-25% | 不推荐 | 红 |

---

## 🎛️ 周期性策略参数速查

### 周期性趋势交易

```
min_period        = 5        # 最短周期(天)
max_period        = 60       # 最长周期(天)
signal_strength   = 0.5      # 信号强度(0-1)
position_size     = 1.0      # 头寸规模(0-1)
```

**适用**: 强周期性股票，趋势明显

### 周期性均值回归

```
period            = 30       # 周期长度(天)
zscore_threshold  = 1.5      # Z-score超买超卖阈值
lookback          = 60       # 回看窗口(天)
```

**适用**: 周期振荡股票

### 周期相位对齐

```
period            = 30       # 主周期(天)
phase_buy_start   = 0.0      # 买入相位起点(0-1)
phase_buy_end     = 0.3      # 买入相位终点(0-1)
min_reversion     = 0.5      # 最小回归系数(0-1)
```

**适用**: 相位规律明显的股票

---

## 🔗 文件导航

### 核心代码

```
📁 项目根目录
├── download_sp500_nasdaq100.py          ← 数据下载
├── test_new_features.py                 ← 功能演示
├── GUI_Client/app_v2.py                 ← GUI主程序 [修改]
├── Strategy_Pool/strategies.py          ← 策略注册 [修改]
├── Strategy_Pool/custom/
│   └── cyclical_strategies.py           ← 周期性策略 [新增]
└── Analytics/reporters/
    ├── periodicity_analyzer.py          ← 周期检测 [新增]
    └── sharpe_rating.py                 ← Sharpe评级 [新增]
```

### 文档

```
📄 RELEASE_FEATURES_v2.1.0.md            ← 详细发布说明 [本文档]
📄 QUICK_REFERENCE.md                    ← 本快速指南
```

---

## 💻 代码示例

### 示例1: 检测股票周期性

```python
from Analytics.reporters.periodicity_analyzer import PeriodicityAnalyzer
import pandas as pd

# 加载数据
df = pd.read_parquet('Data_Hub/storage/AAPL.parquet')

# 分析
analyzer = PeriodicityAnalyzer(threshold=0.7)
result = analyzer.analyze(df['close'], name='AAPL')

# 结果
if result['is_periodic']:
    print(f"✅ {result['symbol']} 强周期性")
    print(f"   评分: {result['periodicity_score']:.2%}")
    print(f"   主周期: {result['dominant_period_fft']} 天")
else:
    print(f"❌ {result['symbol']} 弱周期性")
```

### 示例2: Sharpe评级

```python
from Analytics.reporters.sharpe_rating import SharpeRating

sharpe = 1.75
rating = SharpeRating.rate_sharpe(sharpe)

print(f"评级: {rating['label_cn']}")  # 很好
print(f"百分位: {rating['percentile']}%")  # 82%

# 生成图表
fig = SharpeRating.create_rainbow_chart(sharpe, "MyStrategy")
fig.show()  # 或在Streamlit中: st.plotly_chart(fig)
```

### 示例3: 策略对比

```python
from Analytics.reporters.sharpe_rating import SharpeRatingComparison

strategies = {
    '布林带': 1.2,
    '周期趋势': 1.6,
    '均值回归': 0.9
}

df = SharpeRatingComparison.compare_strategies(strategies)
print(df)  # 排序后的对比表
```

---

## ⚙️ 常见操作

### Q: 如何只下载特定的股票?

**A:** 修改 `download_sp500_nasdaq100.py` 的目标列表

```python
# 第50行左右
target_symbols = ['AAPL', 'MSFT', 'GOOGL']  # 自定义

for symbol in target_symbols:
    downloader.download_and_save(symbol, start_date, end_date)
```

### Q: 如何调整周期性阈值?

**A:** 修改分析器初始化

```python
# 更严格: 0.8
analyzer = PeriodicityAnalyzer(threshold=0.8)

# 更宽松: 0.6
analyzer = PeriodicityAnalyzer(threshold=0.6)
```

### Q: 如何在GUI中使用周期性策略?

**A:** 
1. 在策略选择器中选择 "周期性趋势交易策略"
2. 左侧自动显示参数配置
3. 调整参数 (min_period, max_period等)
4. 点击"运行回测"

### Q: Sharpe评级低怎么办?

**A:** 按优先级:
1. 调整策略参数 (grid_search)
2. 更换周期性检测的策略类型
3. 检查是否存在周期性 (查看周期性分析)
4. 考虑加入止损/风险管理

---

## 📈 预期收益

| 指标 | 当前 | 预期 |
|------|------|------|
| 数据库标的数 | 66 | 700+ |
| 策略数量 | 3 | 6 |
| 周期性检测覆盖 | 否 | 是 |
| Sharpe可视化 | 否 | 是 |
| 自动周期性识别 | 否 | 是 |

---

## 🐛 故障排除

| 问题 | 解决方案 |
|------|--------|
| 下载速度慢 | 网络问题，建议夜间运行 |
| 周期性分析为0 | 数据太短或无周期性，检查数据长度 |
| Sharpe图表未显示 | Plotly库版本，运行 `pip install -U plotly` |
| GUI显示周期性失败 | 检查 `Data_Hub/storage/` 中是否有parquet文件 |
| 策略参数不生效 | 确保关闭之前的session，重新刷新页面 |

---

## 📞 更新日志

**v2.1.0** (2026-03-22)
- ✨ 新增S&P 500 & Nasdaq 100批量下载
- ✨ 新增周期性检测模块 (FFT+小波+统计)
- ✨ 新增3个周期性交易策略
- ✨ 新增Sharpe 5级评级系统
- ✨ GUI集成周期性分析和Sharpe可视化
- 🔧 优化时间周期选择器 (数据预览)

---

**Happy Backtesting! 🚀**

*Keep it simple. Keep it real. Keep it profitable.*

---

## 快捷命令

```bash
# 一键运行所有新功能演示
python test_new_features.py

# 下载完整数据库 (可能需要1小时)
python download_sp500_nasdaq100.py

# 启动GUI
streamlit run run_gui.py

# 验证环境
python -c "import scipy, pandas, plotly; print('✅ All dependencies ok')"
```

---

**Created**: 2026-03-22  
**Version**: v2.1.0  
**Status**: ✅ Ready for Production
