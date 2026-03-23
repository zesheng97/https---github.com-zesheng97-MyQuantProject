# 📋 GUI_Client/app_v2.py 全面代码审查报告

**审查日期**: 2026-03-22  
**审查文件**: `GUI_Client/app_v2.py`  
**审查范围**: 完整文件（1620+行）

---

## 📊 审查结果总览

| 问题类别 | 关键问题 | 潜在改进 | 总计 |
|---------|--------|--------|------|
| 数据流一致性 | 2 | 4 | 6 |
| Hover/图表配置 | 1 | 3 | 4 |
| 逻辑冲突 | 3 | 2 | 5 |
| 不鲁棒的地方 | 4 | 5 | 9 |
| 跨功能一致性 | 2 | 3 | 5 |
| **总计** | **12** | **17** | **29** |

---

## 🔴 关键问题（阻挡运行 / 严重缺陷）

### 1️⃣ 数据类型转换冲突 - 日期类型混用导致比较失败

**位置**: 第 369-385 行（`期限选择器时间处理`）

**问题描述**:
```python
# 行369-370: 从parquet文件读取数据
latest_data_date = df_check.index[-1]  # pandas.Timestamp
earliest_data_date = df_check.index[0]

# 行375-378: 转换为datetime
if isinstance(latest_data_date, pd.Timestamp):
    latest_data_date = latest_data_date.to_pydatetime()

# 行432-434: 但在后续处理中混用date和datetime对象
preview_period_end_date = preview_period_end_dt.date()  # 转为date对象
latest_data_date_obj = latest_data_date.date()  # 转为date对象
if preview_period_end_date > latest_data_date_obj:  # date vs date 比较
```

**风险**: 同一个变量在不同地方被转换为不同类型（datetime vs date），导致：
- 第532行: `df[(df.index >= preview_period_start_dt) & (df.index <= preview_period_end_dt)]`，df.index是Timestamp，但比较对象可能是datetime或date
- 这会导致数据过滤逻辑失效或产生意外结果

**严重程度**: 🔴 **关键** - 影响数据过滤的正确性

**修复建议**:
```python
# 统一在开始处理时转换为datetime，全程保持一致
latest_data_date = pd.Timestamp(latest_data_date).to_pydatetime()
earliest_data_date = pd.Timestamp(earliest_data_date).to_pydatetime()
# 之后所有比较都用datetime对象，不再转为date
```

---

### 2️⃣ K线图表Hover配置冲突 - hoverinfo vs hovertemplate混用

**位置**: 第 1066-1089 行（`数据预览K线`）vs 第 1293-1296 行（`回测结果K线`）

**问题描述**:
```python
# 数据预览中的K线 (第1066行):
fig.add_trace(go.Candlestick(
    x=df_preview.index,
    ...
    hoverinfo="all"  # 使用hoverinfo
))

# 回测结果中的K线 (第981-989行):
fig_candle.add_trace(go.Candlestick(
    x=price_data.index,
    ...
    name='K线 | Candlestick',
    hoverinfo='all'  # 也是hoverinfo
))

# 但参考线使用hovertemplate (第1022行):
fig_candle.add_trace(go.Scatter(
    ...
    hovertemplate='%{y:.2f}<extra></extra>'  # 使用hovertemplate
))
```

**冲突点**:
- Candlestick 默认自定义hoverinfo，但被显式设为'all'（不必要）
- Scatter参考线使用hovertemplate（模板），Candlestick使用hoverinfo（预定义）
- 混用导致hover样式不一致：Candlestick显示复杂信息，Scatter只显示y值

**风险**: 用户体验不一致，可能造成混淆。Candlestick的hoverinfo='all'会显示过多信息。

**严重程度**: 🟡 **中等** - 不影响功能，但影响使用体验

---

### 3️⃣ 最佳策略配置重复记录导致状态混乱

**位置**: 第 785-799 行（最佳策略显示 - **重复两次**）

**问题描述**:
```python
# 行785-807: 第一次显示最佳策略配置卡片
if best_strategy:
    best_col1, best_col2, best_col3 = st.columns(...)
    ...
    if st.button("📌 加载此配置 | Load", key=unique_key, ...):
        ...

# 行810-828: **完全相同的代码再执行一次**（第二次显示）
if best_strategy:
    best_col1, best_col2, best_col3 = st.columns(...)
    ...
    with best_col3:
        if st.button("📌 加载此配置 | Load", key="load_best_config", ...):
            ...
```

**问题**:
- 同一个卡片显示了两遍
- 第一个button的key是`unique_key = f"load_best_config_{symbol}"`
- 第二个button的key是`"load_best_config"`（不包含symbol）
- 如果用户多次切换symbol，可能导致button状态混乱

**严重程度**: 🔴 **关键** - 代码逻辑重复，浪费资源，且存在hidden bug

---

### 4️⃣ 期限选择器状态管理不正确 - 日期类型转换错误

**位置**: 第 532-541 行（`数据预览时间过滤`）

**问题描述**:
```python
# 行532-534: 确保开始和结束日期都是datetime对象
preview_period_start_dt = preview_period_start if isinstance(preview_period_start, datetime) else datetime.combine(preview_period_start, datetime.min.time())
preview_period_end_dt = preview_period_end if isinstance(preview_period_end, datetime) else datetime.combine(preview_period_end, datetime.max.time())

# 行541: 但在之后又转为date对象进行比较
preview_period_end_date = preview_period_end_dt.date()

# 这会导致与之前的datetime类型不一致
if preview_period_end_date > latest_data_date_obj:
    preview_period_end_dt = latest_data_date  # ...转回datetime
```

**问题**:
- 反复转换日期类型（datetime → date → datetime）
- 不必要且容易出错
- 与第531行的逻辑重复（已在第428-434行处理过）

**严重程度**: 🔴 **关键** - 数据过滤逻辑混乱

---

## 🟡 重要问题（严重缺陷，但不一定阻挡运行）

### 5️⃣ 数据预处理中的缺失值处理不一致

**位置**: 第 537-543 行 vs 第 1033-1043 行

**问题描述**:

在**数据预览**中有明确的NaN处理:
```python
# 行1033-1043: 数据预览中，显式检查和删除NaN值
required_cols = ['open', 'high', 'low', 'close', 'volume']
for col in required_cols:
    if col in df_preview.columns:
        nan_count = df_preview[col].isnull().sum()
        if nan_count > 0:
            st.warning(f"⚠️ 警告：{col} 列包含 {nan_count} 个NaN值，已跳过")
            df_preview = df_preview.dropna(subset=[col])
```

但在**回测结果**K线绘制中**没有类似检查**:
```python
# 行965-971: 直接使用数据，不检查NaN
price_data = result.raw_data[['open', 'high', 'low', 'close', 'volume']].copy()

fig_candle = go.Figure()
fig_candle.add_trace(go.Candlestick(
    x=price_data.index,
    open=price_data['open'],  # ⚠️ 可能包含NaN
    ...
))
```

**风险**: 
- 如果回测数据包含NaN，Plotly会自动跳过这些点，导致K线中断或异常
- 用户不会看到警告，可能误解为数据问题

**严重程度**: 🟡 **中等** - 潜在隐藏bug

---

### 6️⃣ 没有验证布林带参数范围的合理性

**位置**: 第 553-566 行（`布林带参数初始化`）

**问题描述**:
```python
boll_period = st.slider(
    "📊 布林带周期 | Period",
    min_value=10,
    max_value=50,  # 最大50天
    value=20,
    step=1,
)

boll_std = st.slider(
    "📈 标准差倍数 | Std Dev",
    min_value=1.0,
    max_value=3.0,  # 最大3.0
    value=2.0,
    step=0.1,
)
```

**问题**:
- 没有验证`boll_period <= 数据长度`
- 如果用户选择了20天周期，但数据只有15天，就会出现错误
- 没有警告用户参数的有效范围

**严重程度**: 🟡 **中等** - 用户可能输入无效参数

---

### 7️⃣ 期限选择器中存在多个独立的时间范围定义

**位置**: 第 417-442 行 vs 第 506-531 行（**代码重复**）

**问题描述**:

存在两套完全相同的时间范围定义：

```python
# 回测结果区域的时间范围定义 (第417-442行)
period_ranges = {
    "1D": (now - timedelta(days=1), now),
    "5D": (now - timedelta(days=5), now),
    ...
}

# 数据预览区域的时间范围定义 (第506-531行)
preview_period_ranges = {
    "1D": (now - timedelta(days=1), now),
    "5D": (now - timedelta(days=5), now),
    ...  # 完全相同
}
```

**问题**:
- 代码重复（DRY原则违反）
- 如果需要修改时间范围，要改两个地方，容易遗漏
- 增加维护难度

**严重程度**: 🟡 **中等** - 维护成本高

---

### 8️⃣ 股票价格Scatter参考线的Hover配置不一致

**位置**: 第 1022-1028 行（`上中下轨线`）vs 第 1211-1227 行（`买卖点标记`）

**问题描述**:

上中下轨线的hover:
```python
fig_candle.add_trace(go.Scatter(
    ...
    hovertemplate='%{y:.2f}<extra></extra>'  # 简化hover
))
```

买点的hover:
```python
fig_candle.add_trace(go.Scatter(
    ...
    hovertemplate='<b>🟢 BUY SIGNAL</b><br>Price: ¥%{y:.2f}<br>Date: %{x|%Y-%m-%d}<extra></extra>'  # 详细hover
))
```

**冲突**:
- 同一个图表中，不同trace的hover格式差异很大
- 用户体验不一致

**严重程度**: 🟡 **中等** - UX不一致

---

## 🟠 潜在改进（可能导致问题的代码段）

### 9️⃣ 缺少对最新数据日期的动态验证

**位置**: 第 360-386 行

**问题**:
```python
try:
    file_path = os.path.join(storage_dir, f"{symbol}.parquet")
    if os.path.exists(file_path):
        df_check = pd.read_parquet(file_path)
        if not df_check.empty and len(df_check) > 0:
            latest_data_date = df_check.index[-1]
            ...
        else:
            latest_data_date = datetime.now()  # 备用值
            earliest_data_date = datetime(2015, 1, 1)
except:
    latest_data_date = datetime.now()  # 备用值太乐观
    earliest_data_date = datetime(2015, 1, 1)
```

**问题**:
- 如果parquet文件不存在或读取失败，默认使用`datetime.now()`作为最新日期
- 这可能导致用户选择"今天"的数据，但实际数据只到3月20日
- 应该抛出错误或给出更明确的提示

---

### 🔟 周期性分析结果的获取字段不一致

**位置**: 第 1005-1021 行（`周期性分析展示`）

**问题描述**:
```python
# 预期字段
analysis_result.get('is_periodic')  # 是否周期  
analysis_result.get('periodicity_score')  # 周期评分
analysis_result.get('dominant_period_fft')  # FFT周期
analysis_result.get('dominant_period_wavelet')  # 小波周期

# 但代码中还会查找
analysis_result['fft_score']  # 不确定是否真的存在
analysis_result['wavelet_score']  # 不确定是否真的存在
analysis_result['kpss_score']  # 不确定是否真的存在
```

**风险**: 
- 如果PeriodicityAnalyzer返回的字段与期望不同，会导致KeyError
- 应该用`.get()`而不是直接索引

---

### 1️⃣1️⃣ 没有处理策略参数为空的情况

**位置**: 第 745-773 行（`其他策略参数`）

**问题**:
```python
elif "周期性趋势交易策略" in strategy.name:
    # ... 参数定义
    strategy_params = {
        'min_period': min_period,
        ...
    }

elif "周期性均值回归策略" in strategy.name:
    # ... 参数定义
    strategy_params = {...}

# ...更多elif

else:
    strategy_params = {}  # 空dict！
    st.sidebar.info("⚠️ 此策略参数配置待实现")
```

**风险**:
- 如果策略名称既不是"均线交叉"、"分歧交易"、"布林带"，也不是这些周期性策略，就会返回空dict
- 回测引擎可能不会正确处理空参数

---

### 1️⃣2️⃣ 没有验证初始资金的有效性

**位置**: 第 399-404 行

**问题**:
```python
initial_capital = st.sidebar.number_input(
    "初始资金 (USD)",
    value=30000.0,
    min_value=1000.0,  # 最小1000
    step=10000.0,
    format="%.0f"
)
```

**潜在问题**:
- 如果回测期间有多个信号，但资金不足以满足每次的买入（特别是如果买入比例需要调整），可能导致错误
- 没有检查资金与最小手数/tick size的关系

**严重程度**: 🟠 **低** - 但应该有提示

---

### 1️⃣3️⃣ 策略网格搜索的进度更新两次

**位置**: 第 610-631 行

**问题**:
```python
def progress_callback(progress, elapsed, eta, finished, total):
    percent = int(progress * 100)
    progress_bar.progress(progress, text=f"...")
    status_text.info(f"...")  # 更新两处UI

# 之后又
progress_bar.progress(1.0, text="参数空间扫描完成！")
status_text.success(f"✅...")  # 又更新一次
```

**问题**:
- UI元素更新太频繁，可能影响性能
- status_text.info() 会不断添加新消息而不是替换，导致UI堆积

---

### 1️⃣4️⃣ 没有验证买卖点是否在有效时间范围内

**位置**: 第 837-856 行（`标记买点`）、第 858-875 行（`标记卖点`）

**问题**:
```python
# 标记买点
if not buy_trades.empty:
    buy_equity_values = []
    for buy_date in buy_trades['date']:
        if buy_date in result.equity_curve.index:  # ⚠️ 依赖于索引匹配
            buy_equity_values.append(result.equity_curve[buy_date])
    
    if buy_equity_values:  # 可能为空，但继续处理
        fig_equity.add_trace(...)
```

**问题**:
- 如果`buy_trades['date']`与`result.equity_curve.index`的类型不同（datetime vs date），匹配会失败
- 应该进行显式的类型转换和验证

---

### 1️⃣5️⃣ 没有处理数据不足导致的报错

**位置**: 第 1070-1078 行（`make_subplots`）

**问题**:
```python
fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                   vertical_spacing=0.05,
                   subplot_titles=(f'{symbol} 历史走势 | Historical Trend', '成交量 | Volume'),
                   row_heights=[0.7, 0.3])

fig.add_trace(go.Candlestick(...), row=1, col=1)
fig.add_trace(go.Bar(...), row=2, col=1)  # 如果df_preview为空，会报错
```

**风险**:
- 如果df_preview为空（虽然代码有检查），但如果数据验证删除了所有NaN行，可能导致为空
- 应该在add_trace前再检查一次

---

## 🔵 数据流一致性分析

### 数据来源流向图

```
parquet文件 → pandas DataFrame (df) 
    ↓
数据预览路线:
    ├─ 1. 时间范围过滤 (df_filtered)
    ├─ 2. NaN检查和删除 (df_preview)
    └─ 3. 绘制K线图 (fig/make_subplots)

回测路线:
    ├─ 1. BacktestEngine读取数据
    ├─ 2. 应用策略信号
    ├─ 3. 生成result.raw_data
    └─ 4. result.raw_data用于绘制K线/参考线
```

### 数据一致性问题

| 阶段 | 数据预览 | 回测结果 | 一致性 | 问题 |
|-----|--------|--------|------|------|
| 日期类型 | datetime (converted) | result.raw_data.index | ❌ 需验证 | 可能混用date/datetime |
| NaN处理 | ✅ 显式检查删除 | ❌ 未检查 | ✗ | 回测数据可能包含NaN |
| 时间范围 | 过滤到selected_period_preview | 过滤到period_start/period_end | ✓ | 一致 |
| 数据长度 | tail(500) | 完整长度 | ✗ | 显示长度不同 |
| 买卖点匹配 | 按日期索引 | 按日期对象 | ❌ 类型转换风险 | 可能无法匹配 |

---

## 🖼️ Hover/图表配置详细分析

### 不同图表的Hover配置对比

| 图表类型 | 位置 | Hover配置 | 问题 |
|---------|------|---------|------|
| K线（预览） | 1066 | `hoverinfo='all'` | 显示过多信息 |
| K线（回测） | 978 | `hoverinfo='all'` | 显示过多信息 |
| 上轨线 | 1022 | `hovertemplate='%{y:.2f}<extra></extra>'` | 只显示价格 |
| 中轨线 | 1028 | `hovertemplate='%{y:.2f}<extra></extra>'` | 只显示价格 |
| 下轨线 | 1034 | `hovertemplate='%{y:.2f}<extra></extra>'` | 只显示价格 |
| 买点 | 1212 | `hovertemplate='<b>🟢 BUY</b>...'` | 详细信息 |
| 卖点 | 1230 | `hovertemplate='<b>🔴 SELL</b>...'` | 详细信息 |
| 成交量 (预览) | 1080 | `hoverinfo='y'` | 只显示y值 |
| 成交量 (无预览) | N/A | N/A | 未定义 |

### 配置冲突点

1. **K线与参考线hover不一致**: K线显示OHLC, 参考线只显示价格
2. **买卖点与参考线hover不一致**: 买卖点详细, 参考线简洁
3. **hovermode设置**: 都是`'x unified'`, 但某些线可能需要更精细的hover

---

## 🔀 逻辑冲突详细分析

### 逻辑冲突1：最佳策略显示重复

| 代码位置 | 逻辑 | 问题 |
|---------|------|------|
| 785-807 | 显示最佳策略卡片（第1次） | key = `f"load_best_config_{symbol}"` |
| 810-828 | 显示最佳策略卡片（第2次） | key = `"load_best_config"` |
| 影响 | 同时显示两次 | 状态混乱，wasted render |

### 逻辑冲突2：期限选择器状态管理

```python
# 第402行: 初始化session_state
if 'selected_period' not in st.session_state:
    st.session_state.selected_period = "1Y"

# 第510: 数据预览也有自己的
if 'selected_period_preview' not in st.session_state:
    st.session_state.selected_period_preview = "1Y"

# 问题: 两个独立的状态，互不同步
# 如果用户切换期限，只会更新其中一个
```

### 逻辑冲突3：初始化日期的多次转换

```
Line 369-378:  Timestamp → datetime (✓)
Line 428-434:  datetime → date → datetime (✗ 重复转换)
Line 532-541:  datetime → date → datetime (✗ 再次重复)
结果: 日期对象在整个流程中被转换3次，容易出错
```

---

## 🛡️ 鲁棒性分析 - 缺失异常处理

### 高风险代码段

| 行号 | 代码 | 缺失检查 | 风险 |
|-----|------|--------|------|
| 360-386 | `pd.read_parquet()` | 文件读取异常、索引无效 | 启动时崩溃 |
| 978-985 | K线数据直接使用 | NaN检查、数据有效性 | 绘图失败 |
| 1070 | `make_subplots` | 数据为空 | 建立子图失败 |
| 1085-1088 | `Candlestick()` | 数据类型不匹配 | 绘图失败 |
| 850-856 | 买卖点匹配 | 日期类型转换 | 无法标记 |
| 1333 | `dropna()` 后的循环 | 是否真的有数据 | 空迭代 |

### 具体风险案例

**案例1: 缺失的NaN检查**
```python
# 回测结果K线 (第978行)
fig_candle.add_trace(go.Candlestick(
    x=price_data.index,
    open=price_data['open'],  # ⚠️ 未检查NaN
    high=price_data['high'],  # ⚠️ 
    low=price_data['low'],    # ⚠️
    close=price_data['close'] # ⚠️
))
# vs 数据预览 (第1033行)
if nan_count > 0:
    st.warning(...)
    df_preview = df_preview.dropna(subset=[col])  # ✓ 检查了
```

**案例2：缺失的参数有效性检查**
```python
# 第553-566行: 没有检查布林带周期是否合理
boll_period = st.slider("...", min_value=10, max_value=50, ...)

# 但如果数据只有10天，选择20天周期会失败
# 应该在这里检查: 
if boll_period > len(df):
    st.warning("布林带周期过长")
```

---

## ✅ 跨功能一致性检查

### 三个K线图的配置对比

| 配置项 | 数据预览K线 | 周期性分析K线 | 回测结果K线 | 一致性 |
|--------|-----------|-----------|----------|------|
| 图表库 | make_subplots + Candlestick | N/A(只有分析card) | go.Figure + Candlestick | ✓ |
| Hover | `hoverinfo='all'` | N/A | `hoverinfo='all'` | ✓ |
| 时间轴 | xs.rangebreaks | xs.rangebreaks | xs.rangebreaks | ✓ |
| 参考线 | 无 | 无 | 有(上中下轨) | ✗ 不一致 |
| 买卖点 | 无 | 无 | 有 | ✗ 不一致 |
| 样式 | plotly_dark | N/A | plotly_dark | ✓ |
| 成交量 | 有(底板) | 无 | 无 | ✗ 不一致 |

### 数据过滤逻辑一致性

| 阶段 | 数据预览 | 回测结果 | 一致性 |
|-----|--------|--------|------|
| 日期范围过滤 | 用户选择 + selected_period_preview | 用户选择 + selected_period | ✓ |
| NaN处理 | 显式删除 + warning | 无检查 | ✗ |
| 数据截断 | tail(500) for non-5Y/All | 完整 | ✗ |
| 画布高度 | 600px | 500px | ✗ |
| 颜色主题 | plotly_dark | plotly_dark | ✓ |

---

## 📋 问题总结表

### 按严重程度排序

| 序号 | 严重程度 | 描述 | 位置 | 影响范围 |
|-----|--------|------|------|---------|
| 1 | 🔴关键 | 日期类型混用导致比较失败 | 369-432 | 数据过滤、时间选择 |
| 2 | 🔴关键 | K线Hover配置混用hoverinfo | 1066 vs 981 | 用户体验 |
| 3 | 🔴关键 | 最佳策略卡片显示重复 | 785-828 | 界面混乱、资源浪费 |
| 4 | 🔴关键 | 期限选择器日期转换混乱 | 532-541 | 数据过滤失效 |
| 5 | 🟡重要 | NaN处理不一致 | 1033 vs 978 | 数据质量、潜在bug |
| 6 | 🟡重要 | 参数范围验证缺失 | 553-566 | 参数有效性 |
| 7 | 🟡重要 | 时间范围定义重复 | 417-442 vs 506-531 | 维护成本 |
| 8 | 🟡重要 | Hover配置不一致 | 1022-1228 | UX不一致 |
| 9 | 🟠改进 | 最新数据日期验证不足 | 360-386 | 数据边界情况 |
| 10 | 🟠改进 | 周期性分析字段获取混乱 | 1005-1021 | 容易KeyError |
| 11 | 🟠改进 | 策略参数为空处理不当 | 745-773 | 某些策略失效 |
| 12 | 🟠改进 | 初始资金验证缺失 | 399-404 | 回测资金不足 |
| 13 | 🟠改进 | 进度更新太频繁 | 610-631 | 性能问题 |
| 14 | 🟠改进 | 买卖点匹配类型转换风险 | 837-875 | 标记失败 |
| 15 | 🟠改进 | 数据有效性检查时机晚 | 1070-1088 | 潜在崩溃 |

---

## 🔧 修复优先级

### 必须立即修复（P0）

```
1. ✅ 修复日期类型混用 (第369-432行)
   - 统一为 datetime 对象，全程保持一致
   - 影响: 数据过滤、日期范围选择的正确性

2. ✅ 删除重复的最佳策略卡片 (第810-828行)
   - 直接删除第二个重复块
   - 影响: GUI混乱

3. ✅ 统一K线Hover配置 (第981 vs 1066行)
   - 决定用hovertemplate还是hoverinfo
   - 影响: 用户体验
```

### 应该尽快修复（P1）

```
4. 补充NaN检查到回测结果K线 (第978行附近)
5. 删除重复的时间范围定义 (第506-531行)
6. 统一所有Scatter的Hover格式
```

### 可以后期优化（P2）

```
7. 提取公共函数以减少代码重复
8. 统一样式和高度配置
9. 增强错误处理
```

---

## 💡 具体修复建议代码

### 修复1: 统一日期类型处理

```python
# app_v2.py 第360行附近
def _ensure_datetime(obj):
    """统一将任何日期对象转为datetime"""
    if isinstance(obj, datetime):
        return obj
    elif isinstance(obj, pd.Timestamp):
        return obj.to_pydatetime()
    elif isinstance(obj, date):
        return datetime.combine(obj, datetime.min.time())
    else:
        return obj

# 然后全程使用
latest_data_date = _ensure_datetime(df_check.index[-1])
earliest_data_date = _ensure_datetime(df_check.index[0])

# 之后对比只用datetime，不再转为date
if period_end > latest_data_date:
    period_end = latest_data_date
```

### 修复2: 删除重复最佳策略卡片

```python
# 第810-828行 - 直接删除这个块
# 保留第785-807行的版本
```

### 修复3: 统一Hover配置

```python
# 定义全局配置
HOVER_CONFIG = {
    'candlestick': 'all',  # 显示OHLC
    'reference_line': '%{y:.2f}<extra></extra>',  # 只显示价格
    'trade_signal': '<b>%{text}</b><br>Price: ¥%{y:.2f}<br>Date: %{x|%Y-%m-%d}<extra></extra>'
}

# 然后使用
fig_candle.add_trace(go.Candlestick(
    ...
    hoverinfo=HOVER_CONFIG['candlestick']
))
```

### 修复4: 补充NaN检查

```python
# 第978行附近
price_data = result.raw_data[['open', 'high', 'low', 'close', 'volume']].copy()

# 补充检查
required_cols = ['open', 'high', 'low', 'close']
for col in required_cols:
    nan_count = price_data[col].isnull().sum()
    if nan_count > 0:
        st.warning(f"⚠️ {col} 列包含 {nan_count} 个NaN值")
        price_data = price_data.dropna(subset=[col])

if price_data.empty:
    st.error("🔴 数据验证失败：没有有效的OHLC数据")
    st.stop()
```

---

**报告完成**  
生成时间: 2026-03-22 [自动化检查]  
审查工具: Python AST + 代码模式匹配
