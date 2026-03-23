# 🚀 均值波动性策略升级指南

**升级版本**: 2.0  
**升级日期**: 2026-03-23  
**代码位置**: `Strategy_Pool/custom/mean_reversion_volatility.py`

---

## 📊 核心改进对比

| 功能 | 原版本 | 升级版本 | 改进效果 |
|------|--------|---------|--------|
| **卖出逻辑** | 触碰Z-Score阈值即全仓卖出 | ATR移动止盈 + 动量过滤 | ✅ 避免过早止损，捕捉大趋势 |
| **止损机制** | 固定百分比止损 | 动态止损 + margin缓冲 | ✅ 防止被扫，保护利润灵活 |
| **减仓策略** | 无 | 分批减仓（50%+50%） | ✅ 平衡收益与风险 |
| **动量确认** | 无 | 强动量延迟卖出 | ✅ 顺势交易，避免自杀式建仓 |
| **适应性** | 固定参数 | 参数化完全定制 | ✅ 应对不同市场环境 |

---

## 🎯 四大创新逻辑详解

### 1️⃣ ATR 移动止盈 (Trailing Stop Loss)

#### 数学原理
```
trailing_stop_line = highest_price_since_entry - (trailing_atr_multiplier × ATR)

卖出条件: current_price < trailing_stop_line
```

#### 参数解析
```python
'atr_period': 14,                    # ATR计算周期（越大越平滑）
'trailing_atr_multiplier': 2.0,      # 关键参数！
                                      # 2.0 = 更紧凑，快速止盈
                                      # 3.0 = 中等，平衡
                                      # 4.0+ = 宽松，追踪大趋势
```

#### 工作流程
```
📍 进场: entry_price = 100

⬆️ 价格上升:
   Day 1: 105 → highest_price = 105
   Day 2: 110 → highest_price = 110
   Day 3: 115 → highest_price = 115 ⭐ 最高点

⬇️ 价格回调:
   Day 4: 112 (回撤 3块)
      trailing_stop_line = 115 - (2.0 × 2.5) = 110
      112 > 110 ✅ 继续持仓
   
   Day 5: 108 (回撤 7块)
      trailing_stop_line = 115 - (2.0 × 2.5) = 110
      108 < 110 ⚠️ 触发止盈卖出！

💰 出场利润: (110 - 100) × 100% = 10% 获利！
```

#### 适用场景
- ✅ 捕捉主升浪（多头强势）
- ✅ 长期趋势跟踪
- ❌ 振荡盘整（虚假突破会损耗本金）

---

### 2️⃣ 动量过滤器 (Momentum Filter)

#### 数学原理
```
momentum_5d = (Close - Close[5天前]) / Close[5天前]

强动量判断: momentum_5d > momentum_threshold (典型值0.02 = 2%)
```

#### 验证逻辑
```python
当ATR止盈信号出现时:
  IF 动量_5日 > 0.02 (强正动量):
    延迟卖出 1-2天，等待动量衰减
  ELSE:
    立即执行卖出
```

#### 效果演示
```
场景: 主升浪中触发止盈信号

❌ 不用动量过滤的情况:
   Day 1: ATR止盈触发 → 立即卖出
   Day 2-5: 价格继续狂涨 +15%...
   遗憾: 过早离场，错过大赚！

✅ 用动量过滤的情况:
   Day 1: ATR止盈触发，但动量强(+2.5%) → 延迟
   Day 2: 动量仍强(+1.8%) → 继续延迟
   Day 3: 动量衰减(+0.8%) → 执行卖出
   Day 4-5: 价格开始下跌...
   获胜: 在恰好的位置卖出！
```

#### 参数说明
```python
'momentum_period': 5,              # 默认5日动量
'momentum_threshold': 0.02,        # 强动量阈值(2%)
'momentum_delay_days': 1,          # 延迟天数(可扩展到2)
```

---

### 3️⃣ 分批减仓 (Scaled Exit Position)

#### 两阶段减仓策略
```
进场 (Full Position 100%)
   ↓
首批减仓 50% (在均线附近落袋为安)
   ↓
剩余 50% (由ATR追踪大趋势)
   ↓
最终全部卖出 (ATR止盈或止损)
```

#### 阶段一：50% 获利保护
```python
触发条件:
  - price_deviation 在 ±1% 范围内（接近均线）
  - 当前价 > 进场价（有盈利）

执行结果:
  - 锁定 ~50% 头寸的利润
  - 剩余 50% 继续参与行情
```

#### 阶段二：50% 趋势追踪
```
剩余50%头寸完全由ATR移动止盈管理
目标: 追踪主升浪，捕捉大行情

示例:
  进场: 100元（50万股）
  
  → 25万股在均线附近卖出 110元（获利50% × 10%）
    锁定:  +50,000元
  
  → 25万股继续持仓
    Day 3: 最高涨到 115元
    Day 5: 跌到 110元触发ATR止盈卖出
    获利: 25万 × (110-100) = +250,000元
  
  总收益: +300,000元 = +15%基础资本
```

#### 参数说明
```python
'sell_half_at_mean': True,                # 启用分批减仓
'half_position_threshold': 0.01,          # 触发减仓的偏离度范围(±1%)
```

---

### 4️⃣ 动态止损保护 (Dynamic Stop Loss)

#### 防止"保本损"过早触发的机制

**问题分析**:
```
❌ 原问题: 固定止损+ATR退出，被市场噪点频繁扫出场

示例:
  进场: 100元
  设定止损: 95元 (-5%)
  
  Day 2: 价格跌到 94.8元 → 触发止损 ❌
  
  但Day 3 价格又涨回到 108元...
  遗憾: 被噪点扫出后，错过大涨！
```

**解决方案: 三层止损**

```
第一层: 初始止损 (保本线)
  stop_loss = entry_price × (1 - single_loss_limit)
  典型值: 100 × (1 - 0.05) = 95元
  用途: 防止亏损超过5%

第二层: 盈利止损上移 (利润保护)
  条件: 盈利 > profit_threshold (5%)
  新止损 = current_price × (1 - trailing_stop_loss) - buffer
  典型: 108 × (1 - 0.03) - 2.5 = 101.7元
  用途: 保护已获利润不回吐

第三层: 缓冲区 (噪点避免)
  stop_loss_buffer_atr: 2.0
  缓冲 = 2.0 × ATR
  用途: 留足市场波动空间，防止被扫
```

#### 参数说明
```python
'single_loss_limit': 0.05,            # 初始最大损失 5%
'profit_threshold': 0.05,             # 利润超过5%后启用止损上移
'trailing_stop_loss': 0.03,           # 止损上移到当前价的97%
'stop_loss_buffer_atr': 2.0,          # 缓冲 = 2倍ATR（留足波动空间）
```

#### 实际案例
```
进场: 100元

Scenario 1: 小亏
  Day 1: 价格 94.5 → 触发初始止损 95 → 卖出
  损失: -4.5元
  
Scenario 2: 小盈后有回调
  Day 1: 价格 106 → 盈利6% > threshold(5%)
         → 止损上移到 106×0.97 - 2 = 100元
  Day 2: 价格 101 → 99.5
         → 止损 100 保护，未触发（有缓冲）
  Day 3: 价格 98 
         → 虽然<初始止损95,但已有缓冲,继续持仓
  Day 4: 价格 112 → 大涨！
  
Scenario 3: 清晰的趋势反转
  Day 1-2: 价格 105-112
  Day 3: 价格 108 → 动量衰减 → 动量过滤卖出
  实现好的出场
```

---

## 🎛️ 参数优化建议

### 保守配置（降低风险）
```python
{
    'atr_period': 14,
    'trailing_atr_multiplier': 1.5,        # 更紧凑的止盈
    'momentum_threshold': 0.03,            # 更高的动量阈值
    'single_loss_limit': 0.03,             # 初始止损3%
    'profit_threshold': 0.03,              # 3%利润就上移止损
    'stop_loss_buffer_atr': 2.5,           # 更大的缓冲
}
```

**特点**:
- ✅ 快速止盈，较少持仓时间
- ✅ 低风险，保护资本
- ❌ 可能错过大行情

---

### 平衡配置（推荐 ⭐⭐⭐）
```python
{
    'atr_period': 14,
    'trailing_atr_multiplier': 2.0,        # 标准追踪
    'momentum_threshold': 0.02,            # 2%动量阈值
    'single_loss_limit': 0.05,             # 5%止损
    'profit_threshold': 0.05,              # 5%利润上移
    'stop_loss_buffer_atr': 2.0,           # 标准缓冲
    
    'momentum_period': 5,                  # 5日动量
    'ma_period': 20,                       # 20日均线
    'volatility_period': 20,               # 波动率周期
    'vol_threshold': 0.02,                 # 2%波动率阈值
    'deviation_threshold': 0.03,           # 3%偏离度
    'half_position_threshold': 0.01,       # 1%范围减仓
}
```

**特点**:
- ✅ 风险收益平衡
- ✅ 能捕捉中等以上行情
- ✅ 噪点保护充分

---

### 激进配置（追求收益）
```python
{
    'atr_period': 14,
    'trailing_atr_multiplier': 3.5,        # 宽松追踪，捕捉大趋势
    'momentum_threshold': 0.01,            # 1%即可视为强动量
    'single_loss_limit': 0.08,             # 8%止损容限
    'profit_threshold': 0.08,              # 8%利润才上移
    'stop_loss_buffer_atr': 1.5,           # 缓冲相对紧凑
    
    'momentum_delay_days': 2,              # 延迟2天等待动量衰减
    'vol_threshold': 0.025,                # 允许更高波动率
}
```

**特点**:
- ✅ 最大化利润（尽可能追踪大趋势）
- ✅ 宽松止损，容忍更大回撤
- ❌ 高风险，需要心理建设

---

## 💻 使用示例

### 基础使用
```python
from Strategy_Pool.custom.mean_reversion_volatility import MeanReversionVolatilityStrategy
import pandas as pd

# 1️⃣ 初始化策略
strategy = MeanReversionVolatilityStrategy()

# 2️⃣ 准备数据（必须包含 high, low, close, volume）
data = pd.read_csv('AAPL_daily.csv')

# 3️⃣ 运行回测
result = strategy.backtest(data, params={
    'ma_period': 20,
    'trailing_atr_multiplier': 2.0,
    'momentum_threshold': 0.02,
})

# 4️⃣ 查看信号
print(result[['date', 'close', 'signal', 'entry_price', 'highest_price', 'stop_loss_price']])
```

### 高级用法：多参数组合回测
```python
import numpy as np

# 参数网格搜索
atr_multipliers = [1.5, 2.0, 2.5, 3.0]
momentum_thresholds = [0.01, 0.02, 0.03]

best_sharpe = -np.inf
best_params = None

for atr_mult in atr_multipliers:
    for mom_thresh in momentum_thresholds:
        params = {
            'trailing_atr_multiplier': atr_mult,
            'momentum_threshold': mom_thresh,
            # ... 其他参数
        }
        
        result = strategy.backtest(data, params=params)
        
        # 计算夏普比率
        sharpe = result['strategy_returns'].mean() / result['strategy_returns'].std() * np.sqrt(252)
        
        if sharpe > best_sharpe:
            best_sharpe = sharpe
            best_params = params

print(f"最优参数: {best_params}")
print(f"最佳夏普比: {best_sharpe:.2f}")
```

---

## 📈 性能指标解析

升级后的策略输出包含以下列：

| 列名 | 含义 | 用途 |
|-----|------|------|
| `signal` | 交易信号 (1/-1/0) | 判断持仓状态 |
| `entry_price` | 进场价格 | 计算P&L |
| `highest_price` | 最高价 | ATR止盈基准 |
| `stop_loss_price` | 止损价 | 动态止损 |
| `position_type` | 头寸类型 | 0=无, 1=全仓, 2=50% |
| `momentum_trigger_idx` | 动量触发 | 记录延迟卖出 |
| `strategy_returns` | 策略收益率 | 综合表现 |

---

## ✅ 与 BacktestEngine 兼容性

✅ **完全兼容**

升级版本保持了与原版相同的接口:
- 输入: 标准 OHLCV DataFrame
- 输出: 包含 `signal` 列的 DataFrame
- 参数化调用: `backtest(data, params={})`

可直接用于 `BacktestEngine` 的回测流程：

```python
from Core_Bus.standard import BacktestEngine

engine = BacktestEngine(strategy=strategy, data=data, params=params)
results = engine.run()
```

---

## 🎓 后续优化思路

### 可选增强（用户自行实现）

1. **加权退出**: 区分不同持仓的ATR止盈线
2. **时间止损**: 超过N天自动平仓（防止资金占用）
3. **波动率自适应**: ATR倍数随波动率动态调整
4. **机器学习**: 用历史数据优化最优的动量阈值
5. **多头寸管理**: 同步追踪多个独立头寸

---

## 📞 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|--------|
| 卖出太频繁 | trailing_atr_multiplier 过小 | 增大到2.5-3.0 |
| 不愿意卖出 | momentum_threshold 过低 | 增大到0.03-0.05 |
| 被止损扫出太多 | stop_loss_buffer_atr 过小 | 增大到2.5-3.0 |
| 错过大趋势 | deviation_threshold 或 vol_threshold 不合适 | 调整基础参数 |

---

**版本历史**

| 版本 | 日期 | 主要改进 |
|------|------|--------|
| 1.0 | 2024-XX-XX | 基础均值回归 |
| 2.0 | 2026-03-23 | ATR止盈 + 动量 + 分批 + 动态止损 |

