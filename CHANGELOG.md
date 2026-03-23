# Changelog | 更新日志

所有重要的项目变更都会记录在此文件中。

All notable changes to this project will be documented in this file.

## [v3.0.0] - 2026-03-23

### 🎯 Major Fixes & Features | 主要修复和特性

#### 1. **XGBoost 子进程架构** (解决Streamlit断连)
- **问题**: GUI训练XGBoost时冻结、显示"Connection error"
- **方案**: 将XGBoost独立到子进程 + 文件系统轮询进度
  - `GUI_Client/xgboost_worker.py` (NEW): 独立训练器，通过JSON/pickle与GUI通信
  - `@st.fragment(run_every=3)`: GUI每3秒轮询进度，不阻塞主UI
  - **结果**: 训练独立运行，UI始终响应

#### 2. **XGBoost回测图表显示买卖点** (新功能)
- **问题**: XGBoost结果图表无买卖标记（trades为空）
- **方案**: 向worker添加股数级交易模拟
  - 基于signal的交易: signal=1（买入全部可买数量）, signal=-1（卖出全部）
  - 真实净值曲线: 现金+持仓价值（非synthetic returns）
  - Trades DataFrame: `{date, action, price, shares, cost/revenue, pnl, cash_after}`
  - 计算指标: annual_return, sharpe_ratio, max_drawdown, win_rate
- **结果**: 买卖点星号显示在K线图和净值曲线上

#### 3. **Streamlit API过期修复**
- 替换42处deprecated `use_container_width=True` → Streamlit 1.55.0标准 `width="stretch"`

#### 4. **XGBoost 3.1+ 兼容性**
- 移除deprecated参数: `gpu_id`
- 更新GPU配置: `gpu_hist` → `tree_method='hist'` + `device='cuda'`
- 改进训练循环: 原生callback API早停 + 超时控制

### 📁 文件变更 | Files Modified
- ✅ `GUI_Client/app_v2.py` (1763行): 子进程启动、fragment轮询、xgb结果加载
- ✅ `GUI_Client/xgboost_worker.py` (NEW 140行): 独立训练器 + 交易模拟
- ✅ `Strategy_Pool/custom/xgboost_ml_strategy.py` (NEW): XGBoost ML策略
- ✅ `Engine_Matrix/backtest_engine.py` (8行): 小型重构
- ⌚ `Analytics/reporters/company_info_manager.py` (9行): 工具更新

### 🗑️ 清理 | Cleanup
- 删除2500+行过期文档（GitHub指南、教程、旧版本发布说明）
- 移除debug/test脚本和临时数据

### ✅ 测试验证 | Testing
- 子进程单独测试: ✅ 2秒训练, 29.46%回报率
- Streamlit启动: ✅ 无警告, health check 200 OK
- 初始资金: ✅ 验证30000美元

### 📈 性能提升 | Performance
- **之前**: 训练30-60秒GUI冻结 → 用户看到Connection error
- **之后**: GUI全程响应，实时显示训练进度，图表显示买卖点

---

## [2026.0.0] - 2026-03-16

### ✨ Features | 新功能

#### 核心回测引擎 (Core Backtesting)
- ✅ 参数化回测系统 - 支持动态配置日期、资金、策略参数
- ✅ 整数股交易逻辑 - 真实的仓位管理（无分数股）
- ✅ 7+ 性能指标计算 - Sharpe Ratio, Max Drawdown, Win Rate, Annual Return, etc.
- ✅ 基准对比功能 - 自动下载 NASDAQ (^IXIC) 和 S&P 500 (^GSPC)

#### 用户界面 (GUI)
- ✅ 交互式 Streamlit 界面 - 实时参数调整和结果展示
- ✅ 双图表可视化 - 账户净值曲线 + K线蜡烛图
- ✅ 买卖点标记 - 交易信号在图表上直观显示
- ✅ 企业信息卡片 - 可扩展的公司基本面信息面板
- ✅ 交易日志表 - 详细的买卖记录和成本/收益跟踪

#### 数据管理 (Data Management)
- ✅ Yahoo Finance 数据采集 - 48+ 美股批量下载
- ✅ Parquet 格式存储 - 高效的列式数据库（相比 CSV 更快更压缩）
- ✅ 数据标准化管道 - 统一列名、验证数据类型、处理 MultiIndex
- ✅ 本地缓存机制 - 企业信息三级优先级（缓存 → API → 默认值）

#### 策略库 (Strategy Pool)
- ✅ 均线交叉策略 (MovingAverageCrossStrategy) - SMA 短期/长期均线
- ✅ 参数注入框架 - 运行时动态调整策略参数
- ✅ 易扩展设计 - 简便添加新策略的架构

#### 企业信息系统 (Company Info)
- ✅ 实时数据获取 - 从 yfinance 获取企业基本信息
- ✅ 多维度数据 - 名称、行业、官网、CEO、员工数、财务指标
- ✅ 当日交易数据 - 开盘价、涨跌额、涨跌幅实时显示
- ✅ 本地 JSON 缓存 - Company_KnowledgeBase 文件夹

#### 项目文档 (Documentation)
- ✅ 中英双语 README - 完整的项目文档和说明
- ✅ 架构文档 - 详细的模块说明和数据流程图
- ✅ API 参考 - BacktestConfig、BacktestResult、BacktestEngine 文档
- ✅ 快速开始指南 - 安装、配置、使用步骤

### 📊 Architecture | 架构

```
个人量化实验室 v2026.0.0
├── 数据层 (Data Layer)
│   ├── Data_Hub - Yahoo Finance 数据采集与 Parquet 存储
│   ├── Core_Bus - 数据标准化管道
│   └── Analytics - 企业信息管理和缓存
├── 核心引擎层 (Engine Layer)
│   ├── Engine_Matrix - 参数化回测引擎
│   ├── Strategy_Pool - 策略库（均线交叉、自定义扩展）
│   └── 性能指标计算 - Sharpe、Drawdown、Win Rate 等
└── 用户界面层 (GUI Layer)
    └── GUI_Client - Streamlit 交互式前端（Plotly 可视化）
```

### 🎯 Core Features | 核心特性

| 功能 | 说明 |
|------|------|
| 参数化回测 | 日期、资金、策略参数全动态 |
| 整数股交易 | 模拟真实的股票交易（无分数股） |
| K线+净值 | 双图表同步标记买卖点 |
| 基准对比 | 自动计算相对纳指/标普 Alpha |
| 企业信息 | 实时 + 本地缓存双层数据 |
| 中英界面 | 基础国际化框架已就位 |

### 🚀 Known Limitations | 已知限制

- 🔄 中文翻译暂时禁用（googletrans 4.0+ 异步兼容性问题）
- 🔜 AI 驱动分析尚未集成
- 🔜 实时数据流功能尚未实现
- 🔜 选项及衍生品回测暂不支持

---

## [Future Releases] | 后续计划

### Phase 1: Research Enhancement (2026.1.0)
- [ ] Markdown 报告自动生成
- [ ] PDF 导出回测结果
- [ ] 性能分解分析（因子贡献度）
- [ ] 中英文本翻译修复（新库或 API）

### Phase 2: AI Integration (2026.2.0)
- [ ] Gemini API 集成 - 策略优化建议
- [ ] ChatGPT 驱动 - 自动化研报生成
- [ ] 自然语言策略描述
- [ ] AI Agent 协作框架

### Phase 3: Real-Time Features (2026.3.0)
- [ ] 实时订单流追踪
- [ ] 日内 K线 (1min, 5min, 15min, 1h)
- [ ] WebSocket 数据流
- [ ] 警报和通知系统

### Phase 4: Community & Persistence (2026.4.0)
- [ ] 策略分享市场
- [ ] 用户贡献策略库
- [ ] 云端结果存储（AWS S3/Google Cloud）
- [ ] 版本控制和协作平台

### Phase 5: Advanced Features (2026.5.0)
- [ ] 多资产投资组合支持
- [ ] 期权挂钩 (Greeks 计算)
- [ ] 机器学习特征工程
- [ ] 风险对标 (VaR, CVaR)

---

## [2025.12.1] - Initial Development | 初期开发

### 初版功能
- 基础回测引擎原型
- 简单均线策略
- HTML 报告生成

---

## Version Numbering Scheme | 版本号方案

格式：`YYYY.MAJOR.MINOR`
- `YYYY` = 发布年份 (年份编号)
- `MAJOR` = 主要版本 (功能大更新：0=初版, 1+)
- `MINOR` = 小版本 (Bug 修复、微调：0=新版本发布, 1+)

示例：
- `2026.0.0` = 2026年首个大版本
- `2026.1.0` = 2026年第二个主版本
- `2026.1.1` = 2026年第二个主版本的首个补丁

---

## Contributing | 贡献指南

欢迎提交 Pull Request 和 Issues！

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## License | 许可证

See [LICENSE](LICENSE) file for details - MIT License
