# XGBoost ML Strategy - API 参考

## 类概览

### 1. HardwareDetector（硬件检测）

自动检测和配置最优硬件。

```python
from Strategy_Pool.custom.xgboost_ml_strategy import HardwareDetector

config = HardwareDetector.detect_optimal_config()
# 返回：{'tree_method': 'gpu_hist', 'gpu_id': 0, 'max_depth': 9, 'device': 'cuda', ...}
```

**返回字典结构：**
```python
{
    'tree_method': str,      # 'gpu_hist' 或 'hist'
    'gpu_id': int or None,   # GPU设备ID（如果可用）
    'max_depth': int,        # 树的最大深度 (6-9)
    'n_jobs': int,           # 并行工作数 (-1 = 全核)
    'device': str            # 'cuda' 或 'cpu'
}
```

---

### 2. FeatureEngineer（特征工程）

自动构建技术指标特征。

#### 方法：build_features()

```python
from Strategy_Pool.custom.xgboost_ml_strategy import FeatureEngineer

engineer = FeatureEngineer()

# 输入：OHLCV DataFrame
df_with_features, features_list = engineer.build_features(
    data=ohlcv_df,
    lookback_window=20  # 可选，默认20
)

# 返回：
#   - df_with_features: 包含原始列 + 新特征的 DataFrame
#   - features_list: ['momentum_10', 'rsi_14', 'bollinger_width', ...]
```

**特征列表（返回顺序）：**
1. momentum_10
2. rsi_14
3. bollinger_width
4. volume_surge
5. volatility
6. price_position
7. log_return

#### 方法：create_labels()

```python
df_labeled, target_col = engineer.create_labels(df_with_features)

# 返回：
#   - df_labeled: 新增 'target' 列 (0 或 1)
#   - target_col: 标签列名 ('target')
```

**标签规则：**
- 1 = 下一期对数收益率 > 0（预测涨）
- 0 = 下一期对数收益率 <= 0（预测跌）

---

### 3. ModelRegistry（模型注册中心）

处理模型持久化、加载和排序。

#### 初始化

```python
from Strategy_Pool.custom.xgboost_ml_strategy import ModelRegistry

# 默认目录：Data_Hub/model_registry/
registry = ModelRegistry()

# 或指定自定义目录
registry = ModelRegistry(registry_dir="/custom/path")
```

#### 方法：save_model()

```python
model_id = registry.save_model(
    model=trained_xgb_model,              # xgboost.Booster 对象
    features_list=['rsi_14', 'momentum_10', ...],
    params={'learning_rate': 0.05, ...},
    validation_accuracy=0.6234,            # float, 0-1
    simulation_return=0.1523,              # float, 可为负
    training_time=120.5                    # float, 秒
)
# 返回：'xgboost_20260323_120000' (model_id)
```

**保存的文件：**
- `xgboost_{timestamp}.json` → 模型权重
- `features_{timestamp}.pkl` → 特征列表
- `metadata_{timestamp}.json` → 元数据
- `registry.csv` → 追加新行

#### 方法：load_model()

```python
model, features_list, params = registry.load_model("xgboost_20260323_120000")

# 返回：
#   - model: xgboost.Booster 对象
#   - features_list: ['feature1', 'feature2', ...]
#   - params: {'param1': value1, ...}
```

#### 静态方法：get_ranked_models()

```python
top_models_df = ModelRegistry.get_ranked_models(top_n=10)

# 返回 DataFrame，按 performance_score 降序排列
# 列：model_id, features_list, params_dict, validation_accuracy, 
#     simulation_return, performance_score, training_time, timestamp
```

**用法示例：**

```python
best_models = ModelRegistry.get_ranked_models(top_n=5)

# 提取表现最佳的模型ID
best_model_id = best_models.iloc[0]['model_id']

# 在 GUI 中展示
for idx, row in best_models.iterrows():
    display_text = f"{row['model_id']} | 性能:{row['performance_score']:.4f}"
    print(display_text)
```

---

### 4. XGBoostMLStrategy（主策略类）

完整的 ML 策略实现，支持训练和推理双模式。

#### 初始化参数

```python
from Strategy_Pool.custom.xgboost_ml_strategy import XGBoostMLStrategy

strategy = XGBoostMLStrategy(
    name: str = "XGBoost机器学习策略",
    description_cn: str = "使用 XGBoost...",
    description_en: str = "XGBoost-based...",
    
    model_id: Optional[str] = None,           # 推理模式：指定model_id；训练模式：None
    time_limit: Optional[int] = None,         # 训练超时时间（秒）
    target_limit: Optional[int] = None,       # 早停耐心度（轮数），默认100
    progress_callback: Optional[Callable] = None  # 进度回调函数
)
```

**Mode 判断：**
- `model_id=None` → **训练模式**（完整训练流程）
- `model_id='xgboost_xxx'` → **推理模式**（加载并推理）

#### 主方法：backtest()

```python
result_df = strategy.backtest(
    data: pd.DataFrame,                  # OHLCV DataFrame
    params: Optional[Dict] = {}          # 策略参数（保留扩展）
)
```

**返回值：** DataFrame，包含列：
- `open, high, low, close, volume` → 原始OHLCV
- `signal` → 交易信号 (1=买入, -1=卖出)
- `returns` → 策略收益率
- 所有特征列 (momentum_10, rsi_14, ...)

**流程（训练模式）：**
1. 特征工程 → 7个特征
2. 标签创建 → 下期收益率方向
3. 80/20 分割
4. 训练（带超时和早停）
5. 性能评估
6. 模型持久化
7. 信号生成

**流程（推理模式）：**
1. 加载预训练模型
2. 特征工程（同样7个特征）
3. 信号生成（毫秒级）

#### 进度回调函数

可选的进度回调，用于 GUI 整合：

```python
def progress_callback(current: int, total: int, message: str):
    print(f"[{current}/{total}] {message}")

strategy = XGBoostMLStrategy(
    model_id=None,
    progress_callback=progress_callback
)
```

**消息示例：**
```
[0/5] 🔨 构建特征...
[1/5] 🏷️ 创建标签...
[2/5] ✂️ 分割数据...
[3/5] 🚀 开始训练...
[4/5] 📊 评估性能...
[5/5] ✅ 训练完成！模型ID: xgboost_20260323_120000
```

---

## 完整工作流代码示例

### 训练新模型

```python
import pandas as pd
from Strategy_Pool.custom.xgboost_ml_strategy import XGBoostMLStrategy

# 1. 加载数据
df = pd.read_parquet('Data_Hub/storage/AAPL.parquet')

# 2. 创建策略（训练模式）
strategy = XGBoostMLStrategy(
    model_id=None,
    time_limit=600,      # 10分钟
    target_limit=150
)

# 3. 回测（自动训练）
result = strategy.backtest(df, params={})

# 输出：✅ 模型已保存：xgboost_20260323_120000 (性能分数: 0.6234)
```

### 加载和使用最优模型

```python
from Strategy_Pool.custom.xgboost_ml_strategy import ModelRegistry, XGBoostMLStrategy

# 1. 查询最优模型
best_models = ModelRegistry.get_ranked_models(top_n=1)
best_model_id = best_models.iloc[0]['model_id']

# 2. 创建策略（推理模式）
strategy = XGBoostMLStrategy(model_id=best_model_id)

# 3. 推理
new_data = pd.read_parquet('Data_Hub/storage/AAPL.parquet')
result = strategy.backtest(new_data, params={})

# 输出：信号立即生成，无需训练
```

### 批量模型对比

```python
import pandas as pd
from Strategy_Pool.custom.xgboost_ml_strategy import ModelRegistry

# 获取表现好的模型
models_df = ModelRegistry.get_ranked_models(top_n=100)

# 分析
print(f"总模型数: {len(models_df)}")
print(f"平均性能分数: {models_df['performance_score'].mean():.4f}")
print(f"最高性能分数: {models_df['performance_score'].max():.4f}")

# 按性能分数分组
models_df['perf_tier'] = pd.cut(
    models_df['performance_score'],
    bins=[0, 0.5, 0.6, 0.7, 1.0],
    labels=['Poor', 'Average', 'Good', 'Excellent']
)

print(models_df.groupby('perf_tier').size())
```

### 在 Streamlit GUI 中集成

```python
import streamlit as st
from Strategy_Pool.custom.xgboost_ml_strategy import ModelRegistry, XGBoostMLStrategy

# 1. 显示模型选择
st.subheader("🏆 选择 AI 模型")

best_models = ModelRegistry.get_ranked_models(top_n=10)
model_options = [f"{r['model_id']} | {r['performance_score']:.4f}" 
                 for _, r in best_models.iterrows()]

selected = st.selectbox("选择模型", model_options)
selected_model_id = selected.split(' | ')[0]

# 2. 回测按钮
if st.button("运行回测"):
    strategy = XGBoostMLStrategy(model_id=selected_model_id)
    result = strategy.backtest(historical_data, {})
    st.success("✅ 回测完成")
    st.dataframe(result)
```

---

## 性能优化建议

1. **缩短训练时间**
   ```python
   strategy = XGBoostMLStrategy(time_limit=120)  # 2分钟
   ```

2. **增加样本量**
   - 使用更长的历史数据（最好3+ 年）

3. **监控 GPU 内存**
   ```python
   config = HardwareDetector.detect_optimal_config()
   print(config['device'])  # 查看使用的硬件
   ```

4. **定期清理旧模型**
   ```python
   import os
   # 手动删除 Data_Hub/model_registry/ 中的过期文件
   ```

---

## 错误处理

### 导入错误

```python
ImportError: XGBoost 未安装。请运行: pip install xgboost
```

**解决方案：**
```bash
pip install xgboost>=2.0.0
```

### 模型加载错误

```python
FileNotFoundError: 模型文件不存在：xgboost_xxx.json
```

**原因：** model_id 不存在或拼写错误  
**解决方案：**
```python
valid_models = ModelRegistry.get_ranked_models()
print(valid_models['model_id'].tolist())  # 查看所有有效ID
```

### OOM 错误

```python
RuntimeError: CUDA out of memory
```

**原因：** GPU 内存不足  
**解决方案：**
- HardwareDetector 会自动限制 max_depth（通常）
- 手动缩小样本数量或增加 time_limit (让模型更早停止)

---

## 文件结构参考

```
Data_Hub/model_registry/
├── registry.csv                           # CSV 日志
│   └── 行格式: model_id,features_list,params_dict,validation_accuracy,...
├── xgboost_20260323_120000.json          # 模型权重（XGBoost JSON）
├── features_20260323_120000.pkl          # 特征列表（Pickle）
├── metadata_20260323_120000.json         # 元数据（JSON）
├── xgboost_20260323_091500.json
├── features_20260323_091500.pkl
├── metadata_20260323_091500.json
└── ... (更多训练结果)
```

---

**版本**: 1.0  
**最后更新**: 2026-03-23
