# Personal Quant Lab

**Version**: 3.0.0 | **Python**: 3.10+ | **Status**: Production Ready

---

## Overview

Personal Quant Lab is a Python-based quantitative backtesting platform designed for individual traders and researchers. It provides a complete system for strategy development, testing, and analysis with a user-friendly interface.

**Key Features:**
- Parameterized backtesting with dynamic strategy configuration
- Real-time web interface (Streamlit + Plotly)
- Support for multiple strategies with easy extensibility
- Comprehensive performance metrics (Sharpe ratio, drawdown, win rate, etc.)
- Local data caching with Parquet format
- Company information management with real-time data

---

## Quick Start

### Installation

```bash
git clone https://github.com/your-username/MyQuantProject.git
cd MyQuantProject

pip install -r requirements.txt
python create.py  # Initialize project structure
```

### Launch GUI

```bash
python run_gui.py
# Streamlit app opens at http://localhost:8501
```

### Download Data

```bash
python download_sp500_nasdaq100.py
# Fetches ~100 stocks into Data_Hub/storage/
```

### Programmatic Usage

```python
from Engine_Matrix.backtest_engine import BacktestEngine, BacktestConfig
from Strategy_Pool.strategies import STRATEGIES

config = BacktestConfig(
    symbol="AAPL",
    start_date="2023-01-01",
    end_date="2025-12-31",
    initial_capital=30000,
    strategy_name="MovingAverageCrossStrategy",
    strategy_params={"ma_short": 20, "ma_long": 60}
)

engine = BacktestEngine()
result = engine.run(config)

print(f"Total Return: {result.metrics['total_return']:.2%}")
print(f"Sharpe Ratio: {result.metrics['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {result.metrics['max_drawdown']:.2%}")
```

---

## System Architecture

**Data Flow:**

```
Yahoo Finance → YFinanceDownloader → Parquet Storage
                                           ↓
                                    (standardize_ohlcv)
                                           ↓
Strategy Pool → BacktestEngine → Metrics + Charts
                   ↓
             Company Info Mgr → GUI (Streamlit)
```

**Core Modules:**

| Module | Purpose | Key Files |
|--------|---------|-----------|
| **Engine_Matrix** | Backtesting core with position management | `backtest_engine.py` |
| **Strategy_Pool** | Strategy implementations | `strategies.py`, `custom/` |
| **Data_Hub** | Data acquisition and storage | `fetchers/yf_downloader.py` |
| **Core_Bus** | Data standardization (OHLCV) | `standard.py` |
| **Analytics** | Company info & performance reporting | `reporters/company_info_manager.py` |
| **GUI_Client** | Web interface | `app_v2.py` (Streamlit) |

---

## Project Structure

```
MyQuantProject/
├── README.md
├── create.py                           # Initialize project
├── run_gui.py                          # GUI entry point
├── download_sp500_nasdaq100.py         # Download market data
│
├── Core_Bus/                           # Data standardization
│   └── standard.py
├── Data_Hub/                           # Data pipeline
│   ├── fetchers/yf_downloader.py
│   └── storage/                        # Parquet files
├── Engine_Matrix/                      # Backtesting engine
│   ├── backtest_engine.py
│   └── advanced_simulator.py
├── Strategy_Pool/                      # Strategy library
│   ├── strategies.py
│   └── custom/
│       ├── xgboost_ml_strategy.py
│       └── cyclical_strategies.py
├── Analytics/                          # Analysis & reporting
│   └── reporters/company_info_manager.py
└── GUI_Client/                         # Streamlit interface
    ├── app_v2.py
    └── xgboost_worker.py               # Async XGBoost trainer
```

---

## Core Components

### BacktestEngine

Executes trade simulation with share-level position management.

**Key Metrics Calculated:**
- Total Return, Annual Return
- Sharpe Ratio, Max Drawdown
- Win Rate, Number of Trades
- Risk-Adjusted Returns

**Core Method:**
```python
result = engine.run(config: BacktestConfig) -> BacktestResult
```

### Strategy Interface

All strategies inherit from base class with signal generation:

```python
class BaseStrategy:
    def backtest(self, df: DataFrame, params: dict) -> DataFrame
        # Returns DataFrame with columns: [close, signal, return, equity]
        # signal: 1 (buy), -1 (sell), 0 (neutral)
```

**Built-in Strategies:**
- `MovingAverageCrossStrategy`: SMA crossover (configurable periods)
- `XGBoostMLStrategy`: ML-based signal generation with GPU support

### GUI Features

**Sidebar:**
- Company information card
- Parameter controls (date range, capital, strategy params)

**Main Area:**
- Performance metrics summary
- Equity curve chart with buy/sell markers
- K-line candlestick chart with technical overlays
- Trade log with entry/exit prices

---

## API Reference

### BacktestConfig

Configuration dataclass for backtesting:

```python
@dataclass
class BacktestConfig:
    symbol: str                          # e.g., "AAPL"
    start_date: str                      # "YYYY-MM-DD"
    end_date: str
    initial_capital: float               # e.g., 30000
    strategy_name: str                   # Strategy identifier
    strategy_params: dict                # Strategy-specific params
```

### BacktestResult

Results container with full backtest data:

```python
@dataclass
class BacktestResult:
    equity_curve: Series                 # Daily portfolio value
    trades: DataFrame                    # Trade history with prices/PnL
    metrics: dict                        # Performance metrics
    raw_data: DataFrame                  # Signal & return data
    config: BacktestConfig
```

### Metrics Dictionary

```python
metrics = {
    'total_return': float,               # Overall return %
    'annual_return': float,              # Annualized return %
    'sharpe_ratio': float,               # Risk-adjusted return
    'max_drawdown': float,               # Peak-to-trough decline
    'win_rate': float,                   # % profitable trades
    'num_trades': int,                   # Total trades
}
```

---

## Performance Optimization (v3.0.0)

**XGBoost Subprocess Architecture:**
- Long-running XGBoost training moved to independent subprocess
- GUI remains responsive via `@st.fragment(run_every=3s)`
- Real-time progress polling via file system
- Trades with buy/sell markers automatically generated

**Improvements:**
- Before: 30-60s GUI freeze during training → "Connection error"
- After: Responsive UI throughout training with real-time feedback

---

## Data Management

### Data Source

Yahoo Finance via `yfinance` library. Default: 48+ US stocks in `Data_Hub/storage/` as Parquet files.

### Caching

**Company Information:**
- Cached locally in `Company_KnowledgeBase/{symbol}.json`
- Three-tier priority: Local → API → Default values
- Includes: name, sector, website, CEO, P/E ratio, market cap

---

## Configuration

### Streamlit Configuration

Edit `.streamlit/config.toml`:

```toml
[server]
maxUploadSize = 200
runOnSave = false

[browser]
gatherUsageStats = false

[theme]
base = "light"
primaryColor = "#0066cc"
```

### Environment Variables

Optional proxy configuration:
```bash
export HTTP_PROXY=your-proxy-url
export HTTPS_PROXY=your-proxy-url
```

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

**Current Version**: **v3.0.0** (March 23, 2026)
- XGBoost subprocess architecture (resolves GUI freezing)
- Share-level trading simulation with buy/sell visualization
- Streamlit 1.55.0 API compatibility
- XGBoost 3.1+ GPU support

---

## Development

### Adding a New Strategy

1. Create strategy class in `Strategy_Pool/custom/`:

```python
from Strategy_Pool.base import BaseStrategy

class MyStrategy(BaseStrategy):
    def backtest(self, df, params):
        # Generate signals
        df['signal'] = ...
        df['return'] = ...
        df['equity'] = ...
        return df
```

2. Register in `Strategy_Pool/strategies.py`:

```python
STRATEGIES['MyStrategy'] = MyStrategy
```

### Running Tests

```bash
python -c "
from Engine_Matrix.backtest_engine import BacktestEngine, BacktestConfig
config = BacktestConfig(symbol='AAPL', ...)
engine = BacktestEngine()
result = engine.run(config)
print(f'Success: {result.metrics[\"total_return\"]:.2%}')
"
```

---

## Requirements

- Python 3.10+
- pandas, numpy
- yfinance (data)
- plotly (charting)
- streamlit (GUI)
- xgboost (optional, for ML strategy)
- scikit-learn (optional, for preprocessing)

See `requirements.txt` for full list with versions.

---

## License

MIT License - See LICENSE file for details

---

## Support

For issues, feature requests, or documentation, visit:
- GitHub Issues: [Report a bug](https://github.com/your-username/MyQuantProject/issues)
- Documentation: [CHANGELOG.md](CHANGELOG.md), [RELEASE_v3_SUMMARY.md](RELEASE_v3_SUMMARY.md)

---

**Last Updated**: March 23, 2026 | v3.0.0
