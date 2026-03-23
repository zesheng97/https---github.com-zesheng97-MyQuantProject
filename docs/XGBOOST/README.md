# 📚 XGBoost ML Strategy 文档中心

本文件夹包含 XGBoost 机器学习策略的完整文档。

## 📖 文档列表

### 核心文档
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - 快速参考卡片（命令、代码片段、转换表）
- **[XGBOOST_SYSTEM_SUMMARY.md](XGBOOST_SYSTEM_SUMMARY.md)** - 系统部署总结
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - 验收清单与检查清单

### 扩展资源
- **API 文档** - 见 `Strategy_Pool/custom/API_REFERENCE.md`
- **集成指南** - 见 `Strategy_Pool/custom/INTEGRATION_GUIDE.md`  
- **用户手册** - 见 `Strategy_Pool/custom/XGBOOST_ML_STRATEGY_GUIDE.md`

## 🚀 快速开始

1. 查看 [QUICK_REFERENCE.md](QUICK_REFERENCE.md) 了解命令
2. 运行 `tests/test_xgboost_system.py` 验证系统
3. 查看 [XGBOOST_SYSTEM_SUMMARY.md](XGBOOST_SYSTEM_SUMMARY.md) 了解整体架构

## 📂 文件组织

```
docs/XGBOOST/              ← 你在这里
├── README.md              ← 本文件
├── QUICK_REFERENCE.md     ← 速查卡片
├── XGBOOST_SYSTEM_SUMMARY.md
└── DEPLOYMENT_CHECKLIST.md

tests/                      ← 测试和示例
├── test_xgboost_system.py
└── xgboost_quick_start.py

Strategy_Pool/custom/       ← 核心实现
├── xgboost_ml_strategy.py
├── model_analytics.py
├── model_manager.py
├── API_REFERENCE.md
├── INTEGRATION_GUIDE.md
└── XGBOOST_ML_STRATEGY_GUIDE.md
```

---

**推荐查看顺序**：
1. 本 README
2. QUICK_REFERENCE.md
3. XGBOOST_SYSTEM_SUMMARY.md
4. Strategy_Pool/custom/API_REFERENCE.md

---

**版本**: 1.0  
**最后更新**: 2026-03-23
