# 📂 文件结构组织说明

**更新**: 测试文件、文档已统一管理，不再裸露在根目录。

## 📍 文件新位置

### ✅ 文档
```
docs/XGBOOST/                    ← XGBoost 相关文档中心
├── README.md                     ← 文档导航
├── QUICK_REFERENCE.md           ← 速查卡片 ⭐ 推荐首先阅读
├── XGBOOST_SYSTEM_SUMMARY.md    ← 系统架构总结
└── DEPLOYMENT_CHECKLIST.md      ← 验收清单
```

### ✅ 测试和示例
```
tests/
├── test_xgboost_system.py       ← 系统测试 (13 测试)
├── test_system.py                ← 其他测试
└── examples/
    └── xgboost_quick_start.py   ← XGBoost 示例脚本
```

### ✅ 核心文件（保持不变）
```
Strategy_Pool/custom/
├── xgboost_ml_strategy.py       ← 核心策略类
├── model_analytics.py            ← 性能分析工具
├── model_manager.py              ← 模型管理工具
├── API_REFERENCE.md              ← API 完整文档
├── INTEGRATION_GUIDE.md           ← 集成指南 (5个场景)
└── XGBOOST_ML_STRATEGY_GUIDE.md  ← 用户手册
```

---

## 🚀 快速开始

**验证系统**:
```bash
python tests/test_xgboost_system.py
```

**查看示例**:
```bash
python tests/examples/xgboost_quick_start.py
```

**启动 GUI**:
```bash
python run_gui.py
```

**速查文档**:
```
查看 docs/XGBOOST/QUICK_REFERENCE.md
```

---

## 📋 关键特性确认

✅ **GUI 集成** - 在 GUI 中可直接使用 XGBoost 策略  
✅ **训练模式** - time_limit 和 target_limit 参数可配  
✅ **推理模式** - 加载历史最优模型进行推理  
✅ **模型注册** - 自动保存和排序所有训练的模型  
✅ **性能分析** - 内置分析和管理工具  

---

**版本**: 1.0  
**最后更新**: 2026-03-23
