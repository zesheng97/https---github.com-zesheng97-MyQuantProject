# XGBoost 机器学习策略 - 完整指南

## 概述

这是一个围绕"算力零浪费"核心原则设计的机器学习量化策略。每次训练的模型、特征组合和性能评估都被自动沉淀、汇总、排序，并能在 Streamlit GUI 中随时无缝调用。

---

## 核心架构

### 1. Model Registry（模型注册中心）

位置：`Data_Hub/model_registry/`

文件结构：
```
Data_Hub/model_registry/
├── registry.csv                    # 训练日志总表
├── xgboost_20260323_120000.json   # 模型权重（XGBoost JSON格式）
├── features_20260323_120000.pkl   # 特征列表序列化
└── metadata_20260323_120000.json  # 训练元数据
```

**registry.csv 列结构：**
| 列名 | 类型 | 说明 |
|------|------|------|
| model_id | str | 唯一标识，格式：xgboost_{timestamp} |
| features_list | str | JSON格式的特征列表 |
| params_dict | str | 超参字典（JSON） |
| validation_accuracy | float | 验证集准确率 (0-1) |
| simulation_return | float | 模拟累积收益率 |
| performance_score | float | 性能综合评分 = 0.6*accuracy + 0.4*return |
| training_time | float | 训练耗时(秒) |
| timestamp | str | ISO格式时间戳 |

---

## 使用流程

### 场景 1️⃣：训练新模型（下班前挂机挖掘）

#### 步骤 1：打开 Streamlit GUI

```bash
streamlit run GUI_Client/run_gui.py
```

#### 步骤 2：配置训练参数

1. **策略选择** → 选择 `XGBoost机器学习策略`
2. **取消勾选**"使用历史最优模型"（进入训练模式）
3. **设置训练控制参数**：
   - **时间限制**：300秒（5分钟）或更长，防止训练卡死
   - **早停耐心度**：100（验证集表现连续100轮无改进则停止）

#### 步骤 3：点击"运行回测"

系统将：
1. 自动检测硬件（GPU/CPU）
2. 从数据构建 7 个经典特征（动量、RSI、布林带宽度等）
3. 进行 80/20 的训练/验证分割
4. 用超时和早停机制训练 XGBoost
5. 自动保存模型，追加记录到 `registry.csv`

**预期输出：**
```
✅ 模型已保存：xgboost_20260323_120000 (性能分数: 0.6234)
```

#### 步骤 4：循环训练更多模型

可以改变：
- 初始资金、时间区间
- 硬件参数（自动适配）
- 训练进度控制参数

每次训练都会产生新的 model_id，全部记录在 `registry.csv`

---

### 场景 2️⃣：回测历史最优模型（第二天上班）

#### 步骤 1：打开 Streamlit GUI

#### 步骤 2：配置参数

1. **策略选择** → 选择 `XGBoost机器学习策略`
2. **勾选**"🏆 使用历史最优模型"

#### 步骤 3：选择模型

系统自动调用 `ModelRegistry.get_ranked_models()`，展示：

```
xgboost_20260323_120000 | 性能:0.6234 | 特征:7
xgboost_20260323_091500 | 性能:0.6120 | 特征:7
xgboost_20260322_180000 | 性能:0.5987 | 特征:7
...
```

选择排名第一的模型。

#### 步骤 4：点击"运行回测"

策略进入**推理模式**：
- ⚡ **瞬间加载**预训练的模型（无需再次训练）
- 🎯 使用同样的特征组合和超参
- 📊 快速生成交易信号
- 💰 显示包含滑点和佣金的资金曲线

**全程耗时** < 10 秒（vs 训练模式的 5+ 分钟）

---

## 编程接口

### 1. 训练模式（创建新模型）

```python
from Strategy_Pool.custom.xgboost_ml_strategy import XGBoostMLStrategy

# 初始化策略（训练模式）
strategy = XGBoostMLStrategy(
    model_id=None,           # None = 训练模式
    time_limit=300,          # 5分钟超时
    target_limit=100         # 早停条件
)

# 回测/训练
result_df = strategy.backtest(historical_data, params={})
# 返回包含 ['signal', 'returns', ...] 的 DataFrame
# 同时自动保存模型到 Data_Hub/model_registry/
```

### 2. 推理模式（加载历史模型）

```python
from Strategy_Pool.custom.xgboost_ml_strategy import XGBoostMLStrategy

# 初始化策略（推理模式）
strategy = XGBoostMLStrategy(
    model_id="xgboost_20260323_120000"  # 指定model_id
)

# 推理（无训练）
result_df = strategy.backtest(new_data, params={})
# 直接返回预测信号，耗时毫秒级
```

### 3. 查询历史模型排行

```python
from Strategy_Pool.custom.xgboost_ml_strategy import ModelRegistry

# 获取表现最好的 10 个模型
best_models = ModelRegistry.get_ranked_models(top_n=10)

print(best_models[['model_id', 'performance_score', 'validation_accuracy']])
#   model_id                      performance_score  validation_accuracy
# 0 xgboost_20260323_120000                0.6234             0.6180
# 1 xgboost_20260323_091500                0.6120             0.5890
# ...
```

### 4. 手动加载和使用模型

```python
from Strategy_Pool.custom.xgboost_ml_strategy import ModelRegistry

registry = ModelRegistry()

# 加载模型
model, features_list, params = registry.load_model("xgboost_20260323_120000")

# 使用模型进行预测
import xgboost as xgb
X_new = data[features_list].values
dmatrix = xgb.DMatrix(X_new)
predictions = model.predict(dmatrix)
```

---

## 特征工程细节

自动构建的 7 个特征（FeatureEngineer.build_features()）：

1. **momentum_10**：10日动量
   - 公式：(close - close[10日前]) / close[10日前]
   - 用途：捕捉短期价格动能

2. **rsi_14**：14日相对强度指数
   - 公式：100 - (100 / (1 + RS))
   - 用途：识别超买/超卖区域

3. **bollinger_width**：布林带宽度
   - 公式：(upper_band - lower_band) / middle_band
   - 用途：波动率度量

4. **volume_surge**：成交量突变
   - 公式：当期成交量 / 20日成交量均值
   - 用途：异常成交量检测

5. **volatility**：20日波动率
   - 公式：close.pct_change().rolling(20).std()
   - 用途：风险度量

6. **price_position**：价格在高低点中的相对位置
   - 公式：(close - low) / (high - low)
   - 用途：K线内位置信息

7. **log_return**：对数收益率
   - 公式：ln(close[t]) - ln(close[t-1])
   - 用途：收益率计算

**标签（Target）**：下一期对数收益率方向
- 1 = 预测涨（next_log_return > 0）
- 0 = 预测跌（next_log_return <= 0）

⚠️ **防范未来函数**：标签使用 `shift(-1)` 严格防范

---

## 性能评分计算

```python
performance_score = 0.6 * validation_accuracy + 0.4 * max(0, simulation_return)
```

- **0.6 权重**：验证集准确率（分类性能）
- **0.4 权重**：模拟累积收益率（交易盈利能力）

得分范围：0 ~ 1.0（越高越好）

---

## 硬件自适应

HardwareDetector 自动检测硬件并调整参数：

| 硬件条件 | tree_method | max_depth | device |
|---------|-------------|-----------|--------|
| GPU ≥ 8GB | gpu_hist | 9 | cuda |
| GPU < 8GB | gpu_hist | 6 | cuda |
| 无 GPU | hist | 7 | cpu |

防止小容量 GPU 因过深树而 OOM。

---

## 常见问题

### Q1：为什么我的模型性能分数很低？

可能原因：
1. **特征相关性差**：市场环境变化，特征失效
2. **样本不足**：时间区间太短（< 500 个交易日）
3. **过拟合**：特征数量相对样本量过多

建议：
- 尝试扩大训练时间范围
- 增加 time_limit 让模型多训练几轮
- 观察不同时间段的模型表现差异

### Q2：训练太慢怎么办？

建议：
1. **检查硬件**：`HardwareDetector.detect_optimal_config()` 输出
2. **缩短时间限制**：`time_limit=120`（2分钟）
3. **增加早停耐心度**：不让模型浪费时间微调

### Q3：怎样追踪模型的历史变化？

查看 `Data_Hub/model_registry/registry.csv`：
```bash
# 按性能分数排序
sort -t',' -k6 -nr registry.csv | head -20
```

或在 Python 中：
```python
import pandas as pd
df = pd.read_csv('Data_Hub/model_registry/registry.csv')
df_sorted = df.sort_values('performance_score', ascending=False)
print(df_sorted.to_string())
```

### Q4：能否使用自定义特征？

目前 FeatureEngineer 固定为 7 个特征。扩展方式：

1. 编辑 `FeatureEngineer.build_features()`
2. 添加新特征计算逻辑
3. 追加到 `features_list`
4. 重新训练模型

---

## 完整工作流示例

```python
# ========== 下班前（Friday 17:00）==========
from Strategy_Pool.custom.xgboost_ml_strategy import XGBoostMLStrategy
import pandas as pd

# 1. 加载数据
df = pd.read_parquet('Data_Hub/storage/AAPL.parquet')

# 2. 创建并训练策略
strategy = XGBoostMLStrategy(
    model_id=None,
    time_limit=600,      # 允许 10 分钟训练
    target_limit=150
)

# 3. 回测（自动训练、保存、记录）
result = strategy.backtest(df, params={})

# 打印训练完成消息
print(f"✅ 训练完成，模型已保存")
print(f"性能分数：0.6234")

# ========== 第二天早上（Monday 09:00）==========
# GUI 自动查询 registry.csv，展示历史前 10 个最优模型
# 用户选择排名第一的模型
# 点击"运行回测" -> 推理模式瞬间完成
# 看到资金曲线、买卖点标记、关键指标
```

---

## 依赖和安装

### 自动依赖
```
xgboost >= 2.0.0
pandas >= 1.3.0
numpy >= 1.20.0
```

### 安装（如未包含在 requirements.txt）
```bash
pip install xgboost>=2.0.0
```

---

## 架构师设计说明

这套架构的核心创新在于 **MLOps + 量化交易** 的无缝结合：

1. **模型版本管理**：每个 model_id 唯一对应一个完整的训练快照（模型、特征、超参）
2. **性能追踪**：registry.csv 形成模型性能的完整审计日志
3. **即插即用**：GUI 可以直接从 CSV 读取排行，无需额外代码
4. **算力零浪费**：每次训练的收获都被永久保存，支持批量模型组对比
5. **推理加速**：训练和推理分离，生产环境只需加载模型，毫秒级响应

这使得量化交易的"模型生产线"可以高效运转。

---

## 贡献与扩展

如需扩展模型：
1. 派生 `XGBoostMLStrategy` 类
2. 重写 `_train_with_controls()` 或 `_generate_signals()`
3. 确保 registry 接口兼容

---

**最后更新**：2026-03-23  
**维护者**：Quant Lab Team
