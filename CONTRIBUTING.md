# Contributing to Personal Quant Lab | 贡献指南

感谢你有兴趣为个人量化实验室做出贡献！

Thank you for your interest in contributing to Personal Quant Lab!

## 📋 如何贡献 (How to Contribute)

### 报告 Bug | Report Bugs
请在 [GitHub Issues](https://github.com/yourusername/personal-quant-lab/issues) 中提交 Bug 报告，包含：
- Bug 描述和复现步骤
- 你的环境（Python 版本、OS、关键依赖版本）
- 错误日志或截图

### 提议新功能 | Suggest Features
在 Issues 中创建功能请求（Feature Request），描述：
- 功能的目的和用例
- 预期的行为
- 可能的替代方案

### 提交代码 | Submit Code

#### 1. Fork 仓库
```bash
git clone https://github.com/yourusername/personal-quant-lab.git
cd personal-quant-lab
git checkout -b feature/your-feature-name
```

#### 2. 创建开发环境
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
pip install pytest black flake8 mypy
```

#### 3. 编写代码
- 遵循 PEP 8 风格指南
- 为新功能编写单元测试
- 运行测试确保不破坏现有功能

```bash
# 代码格式化
black .

# 代码检查
flake8 .

# 类型检查
mypy .

# 运行测试
pytest
```

#### 4. 提交 Pull Request
- 创建清晰的提交消息 (commit message)
- 在 PR 描述中解释改动目的和影响

#### 5. 代码审查
- 维护者会审查你的代码
- 根据反馈进行修改
- PR 合并后，你会被添加到贡献者名单

---

## 🎯 开发优先级 (Development Priorities)

### 高优先级 (High Priority)
- 🐛 Bug 修复
- 📊 性能优化
- 🔒 安全性改进

### 中优先级 (Medium Priority)
- 📚 文档改进
- ✨ UI/UX 增强
- 🧪 测试覆盖

### 低优先级 (Low Priority)
- 🎨 代码风格优化
- 💬 注释改进

---

## 🏗️ 架构指南 (Architecture Guidelines)

### 添加新策略 (Adding Strategy)

在 `Strategy_Pool/strategies.py` 中：

```python
class MyStrategy(BaseStrategy):
    """
    策略说明
    
    参数:
    - param1: 说明
    - param2: 说明
    """
    
    def backtest(self, data, params):
        """
        实现回测逻辑
        
        Args:
            data: DataFrame with OHLCV columns
            params: Dict of strategy parameters
            
        Returns:
            DataFrame with 'signal' column added
        """
        # 你的逻辑
        data['signal'] = ...
        return data

# 在 STRATEGIES 列表中注册
STRATEGIES.append(MyStrategy())
```

### 添加新指标 (Adding Metrics)

在 `Engine_Matrix/backtest_engine.py` 中的 `_compute_metrics()` 方法里：

```python
def _compute_metrics(self, equity_curve, trades):
    metrics = {
        ...existing metrics...
        'your_metric': self._calculate_your_metric(equity_curve, trades),
    }
    return metrics
```

### 扩展企业信息 (Extending Company Info)

在 `Analytics/reporters/company_info_manager.py` 中的 `_fetch_from_yfinance()` 方法里：

```python
company_data = {
    ...existing fields...
    'new_field': info.get('yfinance_key', 'N/A'),
}
```

---

## 📝 代码风格 (Code Style)

### Python PEP 8 规范
```python
# 好的示例
def calculate_sharpe_ratio(returns, risk_free_rate=0.02):
    """Calculate Sharpe ratio with proper docstring."""
    excess_returns = returns - risk_free_rate
    return excess_returns.mean() / excess_returns.std()

# 避免
def calc_sharpe(r,rfr=0.02):
    return (r-rfr).mean()/(r-rfr).std()
```

### 类型提示 (Type Hints)
```python
from typing import Dict, List, Tuple
import pandas as pd

def load_data(symbol: str) -> pd.DataFrame:
    """Load market data for a given symbol."""
    ...

def compute_metrics(equity_curve: pd.Series) -> Dict[str, float]:
    """Compute performance metrics."""
    ...
```

### 文档字符串 (Docstrings)
```python
def backtest_strategy(config: BacktestConfig) -> BacktestResult:
    """
    Execute strategy backtest with given configuration.
    
    Args:
        config: BacktestConfig object with symbol, dates, capital, params
        
    Returns:
        BacktestResult containing equity curve, trades, metrics
        
    Raises:
        ValueError: If symbol not found in data
        
    Example:
        >>> config = BacktestConfig(symbol="AAPL", ...)
        >>> result = backtest_strategy(config)
        >>> print(result.metrics['sharpe_ratio'])
    """
    ...
```

---

## 🧪 测试 (Testing)

### 编写测试
```python
# tests/test_backtest_engine.py
import pytest
from Engine_Matrix.backtest_engine import BacktestEngine, BacktestConfig

def test_backtest_basic():
    """Test basic backtest execution."""
    config = BacktestConfig(
        symbol="AAPL",
        start_date="2023-01-01",
        end_date="2023-12-31",
        initial_capital=10000,
    )
    engine = BacktestEngine()
    result = engine.run(config)
    
    assert result is not None
    assert result.metrics['total_return'] is not None
    assert result.equity_curve is not None
```

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_backtest_engine.py::test_backtest_basic

# 显示覆盖率
pytest --cov=Engine_Matrix --cov=Data_Hub --cov-report=html
```

---

## 📦 版本号规则 (Versioning)

遵循 `YYYY.MAJOR.MINOR` 格式：
- `YYYY` = 发布年份
- `MAJOR` = 主要版本（功能大更新）
- `MINOR` = 小版本（Bug 修复）

示例：`2026.0.0` → `2026.1.0` → `2026.1.1`

---

## 📝 提交消息规范 (Commit Messages)

```
[类型] 简短描述 (不超过50字符)

详细描述（如果需要）
- 关键点 1
- 关键点 2

Fixes #issue_number
```

类型：
- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档
- `style:` 代码格式
- `refactor:` 代码重构
- `test:` 测试
- `chore:` 构建或依赖

示例：
```
feat: Add RSI strategy to Strategy_Pool

- Implement RSIStrategy class with configurable window
- Add unit tests for RSI calculation
- Update README with strategy instructions

Fixes #42
```

---

## 📮 联系方式 (Contact)

- **GitHub Issues**: 用于 Bug 和功能请求
- **Discussions**: 用于一般讨论和问题
- **Email**: zesheng@kth.se

---

## 🙏 致谢 (Acknowledgments)

感谢所有为这个项目做出贡献的开发者！  
Thanks to all contributors for making this project better!

---

## License

By contributing to Personal Quant Lab, you agree that your contributions 
will be licensed under its MIT License.
