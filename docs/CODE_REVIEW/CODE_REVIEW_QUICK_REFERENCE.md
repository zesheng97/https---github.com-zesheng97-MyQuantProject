# 代码审查 - 快速参考卡片

## 🔴 Top 5 Critical Fixes (本周内必须修复)

### 1️⃣ datetime/date 类型混用
```python
# ❌ 当前问题
latest_data_date = latest_data_date.to_pydatetime()  # 可能是datetime
start_date = st.date_input(..., value=default_start.date(), ...)  # 返回date对象

# ✅ 解决方案
def normalize_to_datetime(dt_input):
    if isinstance(dt_input, pd.Timestamp):
        return dt_input.to_pydatetime()
    elif isinstance(dt_input, date):
        return datetime.combine(dt_input, datetime.min.time())
    return dt_input
```
**位置**: GUI_Client/app_v2.py ~290-310  
**预估时间**: 1.5小时

---

### 2️⃣ 数据泄露预防
```python
# ❌ 当前: 使用当日数据预计算信号
for i in range(2, len(data)):
    b_trend_ma = data.iloc[i]['trend_ma']  # 当日数据！
    data.loc[data.index[i], 'signal'] = value  # 当日信号
    
# ✅ 解决方案: 所有指标加 shift(1)
data['signal'] = data['signal'].shift(1)  # 前一日信号才用
```
**位置**: Strategy_Pool/strategies.py (DivergenceStrategy)  
**预估时间**: 2小时  
**风险**: 可能改变回测结果 5-25%

---

### 3️⃣ 循环导入
```python
# ❌ 当前循环
# app_v2.py: from strategies import STRATEGIES
# strategies.py: from app_v2 import update_best_strategy

# ✅ 方案 1: 延迟导入
def save_result():
    from GUI_Client.app_v2 import update_best_strategy  # 函数内导入
    
# ✅ 方案 2: 新建共享模块 (推荐)
# shared/memory_manager.py (独立的内存管理)
```
**位置**: strategies.py ~400-410行  
**预估时间**: 2.5小时

---

### 4️⃣ None/异常检查
```python
# ❌ 当前
'ceo': info.get('companyOfficers', [{}])[0].get('name', 'N/A')
# 如果 companyOfficers=[] 会 IndexError!

# ✅ 安全方案
def safe_get_first(lst, default=None):
    try:
        return lst[0] if lst else default
    except (IndexError, TypeError):
        return default

'ceo': safe_get_first(info.get('companyOfficers', []),'N/A')
```
**位置**: Analytics/reporters/company_info_manager.py  
**预估时间**: 2小时

---

### 5️⃣ Pandas SettingWithCopyWarning
```python
# ❌ 当前
data['signal'] = 0  # 可能是视图
data.drop([...], axis=1, inplace=True)  # 危险

# ✅ 安全做法
data = data.copy()  # 明确复制
data['signal'] = 0
data = data.drop([...], axis=1)  # 链式，不用 inplace
```
**位置**: Strategy_Pool/strategies.py (多处)  
**预估时间**: 1.5小时

---

## 📋 检查清单

### 第1天 (4小时)
- [ ] 创建 `utils/type_validator.py` 统一类型转换
- [ ] 修复所有 datetime/date 混用
- [ ] 添加日期类型检查单元测试

### 第2天 (4小时)
- [ ] 检查数据泄露风险
- [ ] 在所有策略中添加 shift(1)
- [ ] 验证回测结果变化 (应该是负向)

### 第3天 (4小时)
- [ ] 创建 `shared/memory_manager.py`
- [ ] 移除循环导入
- [ ] 重新测试导入链

### 第4-5天 (4-5小时)
- [ ] 为所有可能为 None 的值添加检查
- [ ] 创建异常处理标准库
- [ ] 添加单元测试

### 第6-7天 (4-5小时)
- [ ] 修复所有 Pandas 警告
- [ ] 性能基准测试 (修复前/后)
- [ ] 代码审查和合并

---

## 🟠 Major Issues Quick Fix (下周进行)

| # | 问题 | 快速修复 | 时间 |
|----|------|--------|------|
| 6 | 类型注解缺失 | 使用 pyright 扫描，逐个添加 | 3h |
| 7 | 配置分散 | 创建 config/settings.py | 2h |
| 8 | 状态管理 | 实现 LRU 缓存替代文件I/O | 2h |
| 9 | 错误处理 | 创建 utils/logger.py 和 exceptions.py | 2h |
| 10 | 数据验证 | 添加 validate_ohlcv() 函数 | 1.5h |

---

## 📊 进度追踪表

```
优先级1 (Critical) ████████░░ 80% → 完成目标: 本周 ✅
├─ 类型修复      ██████░░░░ 60%
├─ 数据泄露防护  ████░░░░░░ 40%
├─ 循环导入      ██░░░░░░░░ 20%
├─ 异常检查      ████████░░ 80%
└─ Pandas警告    ██████░░░░ 60%

优先级2 (Major)   ░░░░░░░░░░ 0% → 计划开始: 下周一
优先级3 (Minor)   ░░░░░░░░░░ 0% → 计划开始: 2周后
```

---

## 🛠️ 建议的工具/库

```python
# 类型检查
pip install pyright

# 日志
pip install python-json-logger

# 数据验证
pip install pydantic

# 配置管理
pip install python-dotenv pyyaml

# 测试
pip install pytest pytest-cov pytest-xdist

# 性能分析
pip install py-spy memory-profiler line-profiler
```

---

## 📞 相关文档

- 完整审查报告: `CODE_REVIEW_COMPREHENSIVE_v3.md`
- 框架设计建议: 详见报告第7-8节
- 改进行动计划: 详见报告最后部分

---

**生成日期**: 2026-03-22  
**优先级**: 在修复这些问题后，考虑进行结构化测试和性能基准  
**联系**: 查阅详细报告获取完整技术细节
