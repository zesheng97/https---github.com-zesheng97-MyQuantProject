# 🔬 Personal Quant Lab | 个人量化实验室

**English** | [中文](#中文版本)

---

## English Version

### 🎯 Project Vision

**Personal Quant Lab** is a **Python-based mid-to-low frequency quantitative backtesting platform** designed for individual traders and researchers. It combines:

- 🎨 **User-Friendly Interface** — Interactive Streamlit GUI with real-time visualization
- 🌐 **Bilingual Support** — Seamless switching between English and Chinese (future feature)
- 📊 **Parameterized Backtesting** — Dynamic strategy testing with customizable parameters
- 💾 **Dynamic Data Management** — Persistent local caching and flexible data pipeline
- 🧩 **Modular Strategy Architecture** — Easy to add/remove strategy modules
- 🤖 **AI Integration Ready** — Future support for AI Agent-powered analysis (Gemini, ChatGPT)

### 🚀 Latest Updates (v2026.0.0)

| Feature | Status | Details |
|---------|--------|---------|
| Parameterized Backtest Engine | ✅ Complete | Support custom dates, capital, strategy parameters |
| Interactive Streamlit GUI | ✅ Complete | Real-time metrics, dual charts, trade logs |
| Company Info Management | ✅ Complete | Real-time data + local caching |
| Integer Share Trading Logic | ✅ Complete | Realistic position tracking |
| Benchmark Comparison (NASDAQ/S&P 500) | ✅ Complete | Alpha calculation vs baselines |
| Daily Trading Data Display | ✅ Complete | Open price, day change, change percentage |
| Bilingual Documentation | ✅ Complete | Full English + Chinese README |
| AI-Powered Research Agent | 🔜 Planned (v2026.2.0) | Integration with Gemini/ChatGPT for strategy optimization |

### 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Module Descriptions](#module-descriptions)
3. [Installation & Setup](#installation--setup)
4. [Quick Start](#quick-start)
5. [Project Structure](#project-structure)
6. [Data Pipeline](#data-pipeline)
7. [API Reference](#api-reference)
8. [Future Roadmap](#future-roadmap)

---

### 📐 Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    Personal Quant Lab                         │
└──────────────────────────────────────────────────────────────┘

    Data Layer          Core Engine           Interface Layer
    ┌──────────┐        ┌──────────┐        ┌──────────────┐
    │ Data_Hub │        │ Engine   │        │ GUI_Client   │
    │ - yf     │───────▶│ - Matrix │───────▶│ - Streamlit  │
    │ - Parquet│        │ - Config │        │ - Plotly     │
    └──────────┘        │ - Result │        └──────────────┘
                        └──────────┘
    Strategy                ▲
    ┌──────────┐           │
    │ Pool     │───────────┘
    │ - MA     │
    │ - Custom │
    └──────────┘

    Analysis            Infrastructure
    ┌──────────┐        ┌──────────────┐
    │Analytics │        │ Core_Bus     │
    │- Reports │        │ - Std Data   │
    │- InfoMgr │        │ - ValidationCoreLib
    └──────────┘        └──────────────┘
```

---

### 📦 Module Descriptions

#### 1. **Engine_Matrix** — Backtesting Core
- **File**: `Engine_Matrix/backtest_engine.py`
- **Main Classes**:
  - `BacktestConfig` — Configuration dataclass
  - `BacktestResult` — Results container with metrics
  - `BacktestEngine` — Main simulation engine
- **Key Methods**:
  - `run(config)` — Execute full backtest
  - `_simulate_trading()` — Daily position management (integer shares only)
  - `_compute_metrics()` — Calculate 7+ performance metrics (Sharpe, Drawdown, Win Rate, etc.)
  - `_get_benchmark_returns()` — Download NASDAQ & S&P 500 for comparison
- **Metrics Calculated**:
  - Total Return % | Annual Return % | Sharpe Ratio
  - Max Drawdown | Win Rate | Number of Trades
  - Risk-Adjusted Returns

#### 2. **Data_Hub** — Data Pipeline
- **File**: `Data_Hub/fetchers/yf_downloader.py`
- **Main Class**: `YFinanceDownloader`
- **Features**:
  - Batch download from Yahoo Finance (yfinance)
  - Optional HTTP proxy support
  - Automatic retry on failure
  - Save as Parquet format (compressed, fast read/write)
- **Database**: `Data_Hub/storage/{symbol}.parquet` (48+ US stocks)

#### 3. **Core_Bus** — Data Standardization
- **File**: `Core_Bus/standard.py`
- **Function**: `standardize_ohlcv(df)` 
- **Responsibilities**:
  - Flatten MultiIndex columns (yfinance raw format)
  - Normalize column names to [open, high, low, close, volume]
  - Validate required columns and data types
  - Set proper datetime index

#### 4. **Strategy_Pool** — Strategy Library
- **File**: `Strategy_Pool/strategies.py`
- **Built-in Strategies**:
  - `MovingAverageCrossStrategy` — SMA crossover (short & long windows)
- **Design Pattern**:
  - Strategy parameter injection at runtime
  - Signal generation: 1 (long), -1 (short), 0 (neutral)
  - Easy to extend with new strategies

#### 5. **Analytics** — Analysis Tools
- **File**: `Analytics/reporters/company_info_manager.py`
- **Main Class**: `CompanyInfoManager`
- **Features**:
  - Real-time company info via yfinance API
  - Local JSON caching in `Company_KnowledgeBase/`
  - Three-tier priority: Cache → API → Default
  - **Extracted Fields**:
    - Basic Info: Name, Sector, Industry, Website, CEO, Employees
    - Market Data: Current Price, Open, Day Change, Change %, Market Cap, P/E
    - Fundamentals: FCF, ROE
    - Descriptions: Business Summary (English + Chinese Beta)

#### 6. **GUI_Client** — Interactive Interface
- **File**: `GUI_Client/app_v2.py`
- **Framework**: Streamlit + Plotly
- **Components**:
  - Sidebar: Company info card + parameter controls
  - Main area: Metrics cards + dual charts + trade logs
  - Charts: Equity curve + K-line candlestick with buy/sell markers
  - Controls: Date range, initial capital, strategy params (sliders)

---

### 💾 Installation & Setup

#### Prerequisites
- Python 3.10+
- Anaconda (recommended) or pip virtualenv

#### Step 1: Clone & Initialize
```bash
cd d:\MyQuantProject
python create.py  # Initialize folder structure
```

#### Step 2: Install Dependencies
```bash
pip install pandas numpy yfinance plotly streamlit dataclasses-json
```

#### Step 3: Download Data
```bash
python main.py  # Fetch 48+ US stocks from Yahoo Finance
                # Stores in: Data_Hub/storage/*.parquet
```

#### Step 4: Verify Installation
```bash
python test_system.py        # Validate core modules
python test_company_info.py  # Test info manager
```

---

### 🎮 Quick Start

#### Launch GUI (Recommended)
```bash
python run_gui.py
# Opens: http://localhost:8501
# Streamlit dev server starts automatically
```

#### Manual GUI Launch
```bash
streamlit run GUI_Client/app_v2.py
```

#### Programmatic Usage
```python
from Engine_Matrix.backtest_engine import BacktestEngine, BacktestConfig
from Strategy_Pool.strategies import STRATEGIES

# Configure backtest
config = BacktestConfig(
    symbol="AAPL",
    start_date="2023-01-01",
    end_date="2025-12-31",
    initial_capital=30000,
    strategy_name="MovingAverageCrossStrategy",
    strategy_params={"ma_short": 20, "ma_long": 60}
)

# Run backtest
engine = BacktestEngine()
result = engine.run(config)

# Access results
print(f"Total Return: {result.metrics['total_return']:.2%}")
print(f"Sharpe Ratio: {result.metrics['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {result.metrics['max_drawdown']:.2%}")
```

---

### 📁 Project Structure

```
MyQuantProject/
├── README.md                          # This file
├── create.py                          # Project initialization
├── main.py                            # Data collection entry
├── run_gui.py                         # GUI launcher
├── test_system.py                     # System validation
├── test_company_info.py               # Info manager test
│
├── Core_Bus/                          # Data standardization
│   ├── __init__.py
│   └── standard.py                    # standardize_ohlcv()
│
├── Data_Hub/                          # Data pipeline
│   ├── fetchers/
│   │   ├── __init__.py
│   │   └── yf_downloader.py           # Yahoo Finance downloader
│   ├── storage/                       # Parquet files (auto-created)
│   │   ├── AAPL.parquet
│   │   ├── MSFT.parquet
│   │   └── ... (48+ stocks)
│   └── cleaners/
│       └── __init__.py
│
├── Engine_Matrix/                     # Backtesting core
│   ├── __init__.py
│   ├── backtest_engine.py             # Main engine
│   ├── configs.py
│   └── simulators/
│       └── __init__.py
│
├── Strategy_Pool/                     # Strategy library
│   ├── __init__.py
│   ├── base/
│   │   └── __init__.py
│   ├── custom/
│   │   └── __init__.py
│   └── strategies.py                  # Strategy implementations
│
├── Analytics/                         # Analysis tools
│   ├── metrics/
│   │   └── __init__.py
│   └── reporters/
│       ├── __init__.py
│       └── company_info_manager.py    # Company info fetcher
│
├── GUI_Client/                        # Streamlit interface
│   ├── __init__.py
│   ├── app.py                         # Original app
│   └── app_v2.py                      # Current main app
│
└── Company_KnowledgeBase/             # Local cache (auto-created)
    ├── AAPL.json
    ├── INTC.json
    └── ... (cached company info)
```

---

### 🔄 Data Pipeline

```
Input Data                Processing               Output
┌────────────────┐      ┌─────────────┐       ┌──────────────┐
│ Yahoo Finance  │──────▶ yf_downloader│───────▶│ Parquet DB  │
│ (OHLCV Raw)    │      │ (format)    │       │ (48+ stocks) │
└────────────────┘      └─────────────┘       └──────────────┘
                              │
                              ▼ (standardize_ohlcv)
                        ┌─────────────┐
                        │ Core_Bus    │
                        │ - Col names  │
                        │ - Types      │
                        │ - Index      │
                        └─────────────┘
                              │
                              ▼
                        ┌─────────────────┐
                        │ Backtest Engine │
                        │ + Strategy pool │
                        │ + Position mgmt │
                        └─────────────────┘
                              │
                              ▼
                        ┌──────────────┐
                        │ GUI Display  │
                        │ - Metrics    │
                        │ - Charts     │
                        │ - Trade logs │
                        └──────────────┘
```

---

### 🔧 API Reference

#### BacktestConfig
```python
@dataclass
class BacktestConfig:
    symbol: str                          # Stock symbol (e.g. "AAPL")
    start_date: str                      # "YYYY-MM-DD"
    end_date: str                        # "YYYY-MM-DD"
    initial_capital: float               # Starting balance ($)
    strategy_name: str = "MA"            # Strategy identifier
    strategy_params: Dict = None         # e.g. {"ma_short": 20, "ma_long": 60}
```

#### BacktestResult
```python
@dataclass
class BacktestResult:
    equity_curve: pd.Series              # Daily portfolio value
    trades: pd.DataFrame                 # Trade records (date, price, qty)
    metrics: Dict[str, float]            # Performance metrics
    raw_data: pd.DataFrame               # OHLCV + signals
    config: BacktestConfig               # Input configuration
    benchmark_nasdaq: pd.Series          # NASDAQ comparison curve
    benchmark_sp500: pd.Series           # S&P 500 comparison curve
```

#### BacktestEngine
```python
class BacktestEngine:
    def run(config: BacktestConfig) -> BacktestResult:
        """Execute full backtest cycle"""
    
    def load_data(config: BacktestConfig) -> pd.DataFrame:
        """Load and filter Parquet data"""
    
    def _compute_metrics(equity_curve, trades) -> Dict:
        """Calculate 7+ financial metrics"""
```

---

### 🌟 Key Features Explained

#### 1. **Integer Share Trading**
- Realistic trading: only whole shares allowed
- Buy logic: `shares = int(cash / price)`
- Prevents fractional position errors

#### 2. **Dynamic Parameter Control**
- Runtime strategy parameter injection
- Slider-based GUI adjustment
- No code recompilation needed

#### 3. **Dual Chart Visualization**
- **Equity Curve**: Portfolio value over time vs benchmarks
- **K-line**: OHLC candlestick with buy/sell markers

#### 4. **Benchmark Comparison**
- Automatic download of NASDAQ (^IXIC) and S&P 500 (^GSPC)
- Alpha calculation: strategy return - baseline return

#### 5. **Company Info Caching**
- First query: fetch from yfinance API (~2-5 sec)
- Subsequent queries: instant from `Company_KnowledgeBase/*.json`
- Force refresh: `force_refresh=True` parameter

---

### 🚀 Future Roadmap

#### Phase 1: Research Enhancement
- [ ] Markdown report generation
- [ ] PDF export of backtest results
- [ ] Performance decomposition analysis

#### Phase 2: AI Integration
- [ ] Gemini/ChatGPT-powered strategy analysis
- [ ] Automated research report generation
- [ ] Natural language strategy description

#### Phase 3: Real-Time Features
- [ ] Live order tracking (mid-frequency)
- [ ] Intraday K-line support
- [ ] WebSocket data streaming

#### Phase 4: Community & Persistence
- [ ] Strategy sharing marketplace
- [ ] User-contributed strategies
- [ ] Cloud-based result storage
- [ ] Collaborative research

#### Phase 5: Optimization
- [ ] Multi-asset portfolio support
- [ ] Options backtesting
- [ ] Machine learning-based feature engineering

---

### 📊 Performance Metrics Explained

| Metric | Formula | Interpretation |
|--------|---------|-----------------|
| **Total Return** | (Final_Value - Initial) / Initial | Overall performance |
| **Sharpe Ratio** | (Avg Daily Return) / (Daily Std Dev) × √252 | Risk-adjusted return |
| **Max Drawdown** | min((Value - Peak) / Peak) | Worst portfolio decline |
| **Annual Return** | Avg Daily Return × 252 | Annualized performance |
| **Win Rate** | Profitable Trades / Total Trades | % of winning trades |

---

### 🤝 Contributing

To add a new strategy:

1. Create class in `Strategy_Pool/strategies.py`
2. Implement `backtest(data, params)` method
3. Register in `STRATEGIES` list
4. Test with `test_system.py`

Example:
```python
class RSIStrategy(BaseStrategy):
    def backtest(self, data, params):
        rsi_window = params.get('rsi_window', 14)
        # Calculate RSI logic
        # Generate signal column
        return data
```

---

### 📝 License

MIT License — Feel free to use and modify for personal research.

---

### 📧 Contact & Support

- **Bug Reports**: Submit as GitHub issues
- **Feature Requests**: Contact via project repo
- **Questions**: Check the documentation or test files

---

---

## 中文版本

### 🎯 项目愿景

**个人量化实验室**（Personal Quant Lab）是一个**基于Python的中低频量化回测平台**，专为个人交易者和研究员设计。它融合了以下特点：

- 🎨 **用户友好界面** — 交互式 Streamlit GUI 及实时可视化
- 🌐 **双语支持** — 无缝切换中文和英文（未来功能）
- 📊 **参数化回测** — 动态策略测试支持自定义参数
- 💾 **灵活数据管理** — 本地缓存和可扩展的数据管道
- 🧩 **模块化策略架构** — 轻松新增/删除策略模块
- 🤖 **AI 集成就绪** — 未来支持 AI Agent 驱动的分析（Gemini、ChatGPT）

### 🚀 最新更新 (v2026.0.0)

| 功能 | 状态 | 说明 |
|------|------|------|
| 参数化回测引擎 | ✅ 完成 | 支持自定义日期、资金、策略参数 |
| 交互式 Streamlit GUI | ✅ 完成 | 实时指标、双图表、交易日志 |
| 企业信息管理 | ✅ 完成 | 实时数据 + 本地缓存 |
| 整数股交易逻辑 | ✅ 完成 | 真实仓位追踪 |
| 基准对比（纳指/标普） | ✅ 完成 | 相对基准的 Alpha 计算 |
| 当日交易数据显示 | ✅ 完成 | 开盘价、涨跌额、涨跌幅 |
| 双语文档 | ✅ 完成 | 完整的中英文 README |
| AI 驱动研究智能体 | 🔜 计划中 (v2026.2.0) | 与 Gemini/ChatGPT 集成用于策略优化 |

### 📋 目录

1. [架构概览](#架构概览)
2. [模块说明](#模块说明)
3. [安装配置](#安装配置)
4. [快速开始](#快速开始)
5. [项目结构](#项目结构)
6. [数据管道](#数据管道)
7. [API 参考](#api-参考)
8. [未来规划](#未来规划)

---

### 📐 架构概览

```
┌──────────────────────────────────────────────────────────────┐
│                  个人量化实验室 (v0.2)                        │
└──────────────────────────────────────────────────────────────┘

    数据层              核心引擎            界面层
    ┌──────────┐        ┌──────────┐        ┌──────────────┐
    │ 数据中心  │        │ 回测     │        │ GUI 客户端   │
    │ - yf     │───────▶│ - 矩阵   │───────▶│ - Streamlit  │
    │ - Parquet│        │ - 配置   │        │ - Plotly     │
    └──────────┘        │ - 结果   │        └──────────────┘
                        └──────────┘
    策略库                  ▲
    ┌──────────┐           │
    │ 策略池   │───────────┘
    │ - 双均线 │
    │ - 自定义 │
    └──────────┘

    分析模块            基础设施
    ┌──────────┐        ┌──────────────┐
    │研报分析  │        │ 核心总线     │
    │- 报告    │        │ - 数据标准化 │
    │- 信息管理│        │ - 验证检查   │
    └──────────┘        └──────────────┘
```

---

### 📦 模块说明

#### 1. **Engine_Matrix** — 回测核心引擎
- **文件**: `Engine_Matrix/backtest_engine.py`
- **主要类**:
  - `BacktestConfig` — 配置数据类
  - `BacktestResult` — 结果容器（含指标）
  - `BacktestEngine` — 主回测引擎
- **核心方法**:
  - `run(config)` — 执行完整回测
  - `_simulate_trading()` — 每日仓位管理（仅整数股）
  - `_compute_metrics()` — 计算 7+ 项性能指标
  - `_get_benchmark_returns()` — 下载纳指和标普500进行对比
- **计算指标**:
  - 总收益率 | 年化收益率 | 夏普比率
  - 最大回撤 | 胜率 | 交易次数

#### 2. **Data_Hub** — 数据管道
- **文件**: `Data_Hub/fetchers/yf_downloader.py`
- **主类**: `YFinanceDownloader`
- **功能**:
  - 从 Yahoo Finance 批量下载（yfinance 库）
  - 可选 HTTP 代理支持
  - 失败自动重试
  - 保存为高效 Parquet 格式
- **数据库**: `Data_Hub/storage/{symbol}.parquet`（48+ 美股）

#### 3. **Core_Bus** — 数据标准化
- **文件**: `Core_Bus/standard.py`
- **函数**: `standardize_ohlcv(df)` 
- **功能**:
  - 展平 MultiIndex 列（yfinance 原始格式）
  - 列名统一为 [open, high, low, close, volume]
  - 验证必需列和数据类型
  - 设置规范的日期时间索引

#### 4. **Strategy_Pool** — 策略库
- **文件**: `Strategy_Pool/strategies.py`
- **内置策略**:
  - `MovingAverageCrossStrategy` — SMA 均线交叉（短期&长期）
- **设计模式**:
  - 运行时参数注入
  - 信号生成：1（做多）、-1（做空）、0（中性）
  - 易扩展的架构

#### 5. **Analytics** — 分析工具
- **文件**: `Analytics/reporters/company_info_manager.py`
- **主类**: `CompanyInfoManager`
- **功能**:
  - 通过 yfinance API 实时获取企业信息
  - 本地 JSON 缓存（存储在 `Company_KnowledgeBase/`）
  - 三级优先级：缓存 → API → 默认值
  - **提取字段**:
    - 基本信息：名称、行业、官网、CEO、员工数
    - 市场数据：当前价、开盘价、涨跌额、涨跌幅、市值、P/E
    - 财务指标：自由现金流、股东权益回报率
    - 企业简介：英文+中文翻译（Beta）

#### 6. **GUI_Client** — 交互式界面
- **文件**: `GUI_Client/app_v2.py`
- **框架**: Streamlit + Plotly
- **组件**:
  - 侧边栏：企业信息卡 + 参数控制面板
  - 主区域：关键指标卡 + 双图表 + 交易日志
  - 图表：净值曲线 + K线蜡烛图（带买卖点标记）
  - 控制：日期范围、初始资金、策略参数（滑块）

---

### 💾 安装配置

#### 环境要求
- Python 3.10+
- Anaconda（推荐）或 pip 虚拟环境

#### 步骤 1：克隆和初始化
```bash
cd d:\MyQuantProject
python create.py  # 初始化文件夹结构
```

#### 步骤 2：安装依赖
```bash
pip install pandas numpy yfinance plotly streamlit
```

#### 步骤 3：下载数据
```bash
python main.py  # 从 Yahoo Finance 获取 48+ 美股数据
                # 存储位置：Data_Hub/storage/*.parquet
```

#### 步骤 4：验证安装
```bash
python test_system.py        # 验证核心模块
python test_company_info.py  # 测试信息管理器
```

---

### 🎮 快速开始

#### 启动 GUI（推荐方式）
```bash
python run_gui.py
# 自动打开：http://localhost:8501
# Streamlit 开发服务器自动启动
```

#### 手动启动 GUI
```bash
streamlit run GUI_Client/app_v2.py
```

#### 编程式使用
```python
from Engine_Matrix.backtest_engine import BacktestEngine, BacktestConfig

# 配置回测
config = BacktestConfig(
    symbol="AAPL",
    start_date="2023-01-01",
    end_date="2025-12-31",
    initial_capital=30000,
    strategy_params={"ma_short": 20, "ma_long": 60}
)

# 执行回测
engine = BacktestEngine()
result = engine.run(config)

# 获取结果
print(f"总收益率：{result.metrics['total_return']:.2%}")
print(f"夏普比率：{result.metrics['sharpe_ratio']:.2f}")
print(f"最大回撤：{result.metrics['max_drawdown']:.2%}")
```

---

### 📁 项目结构

```
MyQuantProject/
├── README.md                          # 本文件（双语）
├── create.py                          # 项目初始化脚本
├── main.py                            # 数据采集入口
├── run_gui.py                         # GUI 启动器
├── test_system.py                     # 系统验证脚本
├── test_company_info.py               # 信息管理器测试
│
├── Core_Bus/                          # 数据标准化总线
│   ├── __init__.py
│   └── standard.py                    # standardize_ohlcv()
│
├── Data_Hub/                          # 数据中心
│   ├── fetchers/
│   │   ├── __init__.py
│   │   └── yf_downloader.py           # Yahoo Finance 下载器
│   ├── storage/                       # Parquet 文件目录（自动创建）
│   │   ├── AAPL.parquet
│   │   ├── MSFT.parquet
│   │   └── ... (48+ 美股)
│   └── cleaners/
│       └── __init__.py
│
├── Engine_Matrix/                     # 回测引擎
│   ├── __init__.py
│   ├── backtest_engine.py             # 主引擎
│   ├── configs.py
│   └── simulators/
│       └── __init__.py
│
├── Strategy_Pool/                     # 策略库
│   ├── __init__.py
│   ├── base/
│   │   └── __init__.py
│   ├── custom/
│   │   └── __init__.py
│   └── strategies.py                  # 策略实现
│
├── Analytics/                         # 分析工具
│   ├── metrics/
│   │   └── __init__.py
│   └── reporters/
│       ├── __init__.py
│       └── company_info_manager.py    # 企业信息获取器
│
├── GUI_Client/                        # Streamlit 界面
│   ├── __init__.py
│   ├── app.py                         # 原始应用
│   └── app_v2.py                      # 当前主应用
│
└── Company_KnowledgeBase/             # 本地缓存目录（自动创建）
    ├── AAPL.json
    ├── INTC.json
    └── ... (缓存的企业信息)
```

---

### 🔄 数据管道

```
输入数据              处理流程              输出数据
┌────────────────┐   ┌─────────────┐   ┌──────────────┐
│ Yahoo Finance  │───▶ yf_downloader│───▶│ Parquet DB  │
│ (原始 OHLCV)   │   │ (格式转换)  │   │ (48+ 美股)  │
└────────────────┘   └─────────────┘   └──────────────┘
                          │
                          ▼ (standardize_ohlcv)
                    ┌─────────────┐
                    │ 核心总线    │
                    │ - 列名统一  │
                    │ - 类型检查  │
                    │ - 索引设置  │
                    └─────────────┘
                          │
                          ▼
                    ┌─────────────────┐
                    │ 回测引擎        │
                    │ + 策略池        │
                    │ + 仓位管理      │
                    └─────────────────┘
                          │
                          ▼
                    ┌──────────────┐
                    │ GUI 显示     │
                    │ - 关键指标   │
                    │ - 可视化图表 │
                    │ - 交易日志   │
                    └──────────────┘
```

---

### 🔧 API 参考

#### BacktestConfig（回测配置）
```python
@dataclass
class BacktestConfig:
    symbol: str                          # 股票代码（如 "AAPL"）
    start_date: str                      # "YYYY-MM-DD" 格式
    end_date: str                        # "YYYY-MM-DD" 格式
    initial_capital: float               # 初始资金（元）
    strategy_name: str = "MA"            # 策略名称
    strategy_params: Dict = None         # 如 {"ma_short": 20, "ma_long": 60}
```

#### BacktestResult（回测结果）
```python
@dataclass
class BacktestResult:
    equity_curve: pd.Series              # 每日投资组合价值
    trades: pd.DataFrame                 # 交易记录（日期、价格、数量）
    metrics: Dict[str, float]            # 性能指标
    raw_data: pd.DataFrame               # OHLCV + 信号数据
    config: BacktestConfig               # 输入配置
    benchmark_nasdaq: pd.Series          # 纳指对比曲线
    benchmark_sp500: pd.Series           # 标普500对比曲线
```

#### BacktestEngine（回测引擎）
```python
class BacktestEngine:
    def run(config: BacktestConfig) -> BacktestResult:
        """执行完整回测循环"""
    
    def load_data(config: BacktestConfig) -> pd.DataFrame:
        """加载和过滤 Parquet 数据"""
    
    def _compute_metrics(equity_curve, trades) -> Dict:
        """计算 7+ 项财务指标"""
```

---

### 🌟 核心功能详解

#### 1. **整数股交易**
- 仅支持真实交易（不允许分数股）
- 买入逻辑：`shares = int(cash / price)`
- 防止仓位小数点错误

#### 2. **动态参数控制**
- 运行时策略参数注入
- 滑块式 GUI 调整
- 无需重新编译代码

#### 3. **双图表可视化**
- **净值曲线**：投资组合价值对比基准
- **K线图表**：OHLC 蜡烛图带买卖点标记

#### 4. **基准对比**
- 自动下载纳指（^IXIC）和标普500（^GSPC）
- Alpha 计算：策略收益 - 基准收益

#### 5. **企业信息缓存**
- 首次查询：从 yfinance API 获取（~2-5秒）
- 后续查询：从 `Company_KnowledgeBase/*.json` 瞬间获取
- 强制刷新：`force_refresh=True` 参数

---

### 🚀 未来规划

#### 第一阶段：研究增强
- [ ] Markdown 报告生成
- [ ] 回测结果 PDF 导出
- [ ] 性能分解分析

#### 第二阶段：AI 集成
- [ ] Gemini/ChatGPT 驱动的策略分析
- [ ] 自动化研报生成
- [ ] 自然语言策略描述

#### 第三阶段：实时功能
- [ ] 实时订单追踪（中低频）
- [ ] 日内 K 线支持
- [ ] WebSocket 数据流

#### 第四阶段：社区与持久化
- [ ] 策略分享市场
- [ ] 用户贡献的策略库
- [ ] 云端结果存储
- [ ] 协作研究平台

#### 第五阶段：优化升级
- [ ] 多资产投资组合支持
- [ ] 期权回测功能
- [ ] 机器学习特征工程

---

### 📊 性能指标说明

| 指标 | 公式 | 解释 |
|------|------|------|
| **总收益率** | (最终价值 - 初始) / 初始 | 整体表现 |
| **夏普比率** | (日均收益) / (日收益标差) × √252 | 风险调整收益 |
| **最大回撤** | min((价值 - 峰值) / 峰值) | 最差回调幅度 |
| **年化收益** | 日均收益 × 252 | 年化表现 |
| **胜率** | 盈利交易 / 总交易数 | 获胜比例 |

---

### 🤝 贡献指南

如何添加新策略：

1. 在 `Strategy_Pool/strategies.py` 中创建类
2. 实现 `backtest(data, params)` 方法
3. 在 `STRATEGIES` 列表中注册
4. 运行 `test_system.py` 验证

示例：
```python
class RSIStrategy(BaseStrategy):
    def backtest(self, data, params):
        rsi_window = params.get('rsi_window', 14)
        # 计算 RSI 逻辑
        # 生成信号列
        return data
```

---

### 📝 许可证

MIT License — 欢迎用于个人研究和学习

---

### 📧 联系与支持

- **Bug 报告**: 通过项目仓库提交 Issue
- **功能请求**: 通过项目仓库联系
- **问题咨询**: 查看文档或测试文件

---

**最后更新**: 2026年3月16日 | Last Updated: March 16, 2026
**版本**: v2026.0.0 | Version: v2026.0.0
**许可证**: MIT License | GitHub: [personal-quant-lab](https://github.com/yourusername/personal-quant-lab)
