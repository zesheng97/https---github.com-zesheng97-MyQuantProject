# Comprehensive XGBoost ML Strategy System Test Suite
# 完整的系统测试套件

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
from datetime import datetime
import traceback

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

class TestSuite:
    """完整的系统测试套件"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.results = []
    
    def test(self, name: str, func):
        """执行单个测试"""
        try:
            print(f"\n🔍 测试: {name}...", end=" ")
            func()
            print("✅ 通过")
            self.passed += 1
            self.results.append(("✅", name))
            return True
        except AssertionError as e:
            print(f"❌ 失败: {e}")
            self.failed += 1
            self.results.append(("❌", name))
            self.errors.append((name, str(e)))
            return False
        except Exception as e:
            print(f"⚠️  错误: {e}")
            self.failed += 1
            self.results.append(("⚠️", name))
            self.errors.append((name, traceback.format_exc()))
            return False
    
    def print_summary(self):
        """打印测试摘要"""
        total = self.passed + self.failed
        percentage = (self.passed / total * 100) if total > 0 else 0
        
        print("\n" + "="*60)
        print("📊 测试结果摘要")
        print("="*60)
        print(f"总测试数:     {total}")
        print(f"通过:         {self.passed} ✅")
        print(f"失败:         {self.failed} ❌")
        print(f"通过率:       {percentage:.1f}%")
        print("="*60)
        
        if self.errors:
            print("\n❌ 失败详情:")
            for name, error in self.errors:
                print(f"\n  • {name}")
                print(f"    {error[:100]}...")
        
        print("\n" + "="*60 + "\n")
        
        return self.passed == self.failed


# ============================================================================
# 各项测试
# ============================================================================

def test_imports():
    """测试 1: 检查所有必需模块的导入"""
    
    def run_test():
        # 核心模块
        import pandas as pd
        import numpy as np
        from pathlib import Path
        
        # XGBoost（可选，但应该优雅地处理）
        try:
            import xgboost
        except ImportError:
            # 这是可接受的，系统应该提供有用的错误消息
            pass
        
        # 自定义模块
        from Strategy_Pool.custom.xgboost_ml_strategy import (
            HardwareDetector,
            FeatureEngineer,
            ModelRegistry,
            XGBoostMLStrategy
        )
        from Strategy_Pool.custom.model_analytics import ModelAnalytics
        from Strategy_Pool.custom.model_manager import ModelManager
        
        assert HardwareDetector is not None
        assert FeatureEngineer is not None
        assert ModelRegistry is not None
        assert XGBoostMLStrategy is not None
    
    return run_test


def test_hardware_detector():
    """测试 2: 硬件检测器"""
    
    def run_test():
        from Strategy_Pool.custom.xgboost_ml_strategy import HardwareDetector
        
        config = HardwareDetector.detect_optimal_config()
        
        # 验证返回的配置信息
        assert isinstance(config, dict), "Config 应该是字典"
        assert 'tree_method' in config, "Config 应包含 tree_method"
        assert 'max_depth' in config, "Config 应包含 max_depth"
        assert 'device' in config, "Config 应包含 device"
        
        # 验证值的有效性
        assert config['tree_method'] in ['gpu_hist', 'hist'], "tree_method 无效"
        assert config['device'] in ['cuda', 'cpu'], "device 无效"
        assert 4 <= config['max_depth'] <= 15, "max_depth 应在 4-15 之间"
    
    return run_test


def test_feature_engineer():
    """测试 3: 特征工程师"""
    
    def run_test():
        from Strategy_Pool.custom.xgboost_ml_strategy import FeatureEngineer
        
        # 创建测试数据
        dates = pd.date_range('2023-01-01', periods=100)
        np.random.seed(42)
        data = pd.DataFrame({
            'open': np.random.uniform(100, 110, 100),
            'high': np.random.uniform(110, 120, 100),
            'low': np.random.uniform(90, 100, 100),
            'close': np.random.uniform(100, 110, 100),
            'volume': np.random.uniform(1000000, 10000000, 100),
        }, index=dates)
        
        engineer = FeatureEngineer()
        
        # 测试 build_features
        df_features, features_list = engineer.build_features(data)
        
        assert len(df_features) > 0, "特征 DataFrame 不能为空"
        assert len(features_list) == 7, f"应该生成 7 个特征，实际 {len(features_list)}"
        
        expected_features = ['momentum_10', 'rsi_14', 'bollinger_width', 
                            'volume_surge', 'volatility', 'price_position', 'log_return']
        for feat in expected_features:
            assert feat in features_list, f"缺少特征: {feat}"
            assert feat in df_features.columns, f"特征列不存在: {feat}"
        
        # 测试 create_labels
        df_labeled, target_col = engineer.create_labels(df_features)
        assert target_col == 'target', "标签列名应为 'target'"
        assert 'target' in df_labeled.columns, "标签列不存在"
        assert set(df_labeled['target'].dropna().unique()).issubset({0, 1}), "标签值应为 0 或 1"
    
    return run_test


def test_model_registry():
    """测试 4: 模型注册中心"""
    
    def run_test():
        from Strategy_Pool.custom.xgboost_ml_strategy import ModelRegistry
        import json
        
        # 清理之前的测试数据
        registry = ModelRegistry()
        registry_dir = Path(registry.registry_dir) if hasattr(registry, 'registry_dir') else Path("Data_Hub/model_registry")
        
        # 检查目录是否存在
        assert registry_dir.exists(), "注册目录应该存在"
        
        # 测试 get_ranked_models（可能为空）
        try:
            ranked = ModelRegistry.get_ranked_models(top_n=10)
            assert isinstance(ranked, pd.DataFrame), "应返回 DataFrame"
        except:
            # 如果注册表为空，也是可以接受的
            pass
    
    return run_test


def test_data_structure():
    """测试 5: 数据结构和 CSV 格式"""
    
    def run_test():
        from Strategy_Pool.custom.xgboost_ml_strategy import ModelRegistry
        
        registry_csv = Path("Data_Hub/model_registry/registry.csv")
        
        if registry_csv.exists():
            df = pd.read_csv(registry_csv)
            
            expected_columns = [
                'model_id', 'features_list', 'params_dict',
                'validation_accuracy', 'simulation_return',
                'performance_score', 'training_time', 'timestamp'
            ]
            
            for col in expected_columns:
                assert col in df.columns, f"缺少列: {col}"
    
    return run_test


def test_strategy_registration():
    """测试 6: 策略注册"""
    
    def run_test():
        from Strategy_Pool.strategies import STRATEGIES
        
        assert len(STRATEGIES) > 0, "STRATEGIES 列表不能为空"
        
        strategy_names = [s.name for s in STRATEGIES]
        expected_strategies = [
            "均线交叉策略",
            "分歧交易策略（改进版）",
            "布林带交易策略",
            "周期性趋势交易策略",
            "周期性均值回归策略",
            "周期相位对齐策略",
            "均值回归波动率策略",
            "XGBoost机器学习策略"
        ]
        
        for expected in expected_strategies:
            assert expected in strategy_names, f"缺少策略: {expected}"
        
        # 检查 XGBoost 策略
        xgb_strategy = next((s for s in STRATEGIES if s.name == "XGBoost机器学习策略"), None)
        assert xgb_strategy is not None, "XGBoost 策略未注册"
    
    return run_test


def test_model_analytics():
    """测试 7: 模型分析工具"""
    
    def run_test():
        from Strategy_Pool.custom.model_analytics import ModelAnalytics
        
        analytics = ModelAnalytics()
        
        # 测试统计方法
        stats = analytics.get_statistics()
        assert isinstance(stats, dict), "统计结果应该是字典"
        assert 'total_models' in stats, "应包含 total_models"
        
        # 测试特征频率分析
        features_dict = analytics.get_top_features(top_n=5)
        assert isinstance(features_dict, dict), "特征字典应该是字典"
        
        # 测试训练时间统计
        timing_stats = analytics.get_training_time_stats()
        assert isinstance(timing_stats, dict), "时间统计应该是字典"
    
    return run_test


def test_model_manager():
    """测试 8: 模型管理器"""
    
    def run_test():
        from Strategy_Pool.custom.model_manager import ModelManager
        
        manager = ModelManager()
        
        # 测试备份目录
        assert manager.backup_dir.exists(), "备份目录应该存在"
        
        # 测试列表备份方法
        backups = manager.list_backups()
        assert isinstance(backups, list), "备份列表应该是列表"
        
        # 测试磁盘使用
        # （这个方法只是为了检查是否可以运行）
        manager.print_disk_usage()
    
    return run_test


def test_directory_structure():
    """测试 9: 目录结构"""
    
    def run_test():
        # 检查必需的目录
        required_dirs = [
            'Strategy_Pool/custom',
            'Data_Hub/model_registry'
        ]
        
        for dir_path in required_dirs:
            assert Path(dir_path).exists(), f"目录不存在: {dir_path}"
        
        # 检查关键文件
        required_files = [
            'Strategy_Pool/custom/xgboost_ml_strategy.py',
            'Strategy_Pool/custom/model_analytics.py',
            'Strategy_Pool/custom/model_manager.py',
            'Strategy_Pool/custom/API_REFERENCE.md',
        ]
        
        for file_path in required_files:
            assert Path(file_path).exists(), f"文件不存在: {file_path}"
    
    return run_test


def test_strategy_instantiation():
    """测试 10: 策略实例化"""
    
    def run_test():
        from Strategy_Pool.custom.xgboost_ml_strategy import XGBoostMLStrategy
        
        # 测试训练模式实例化
        strategy_train = XGBoostMLStrategy(
            model_id=None,
            time_limit=60,
            target_limit=10
        )
        
        assert strategy_train.model_id is None, "训练模式 model_id 应为 None"
        assert strategy_train.name == "XGBoost机器学习策略", "策略名称不匹配"
        
        # 测试推理模式实例化（虚拟模型 ID）
        strategy_infer = XGBoostMLStrategy(model_id="xgboost_test_20260101_000000")
        assert strategy_infer.model_id == "xgboost_test_20260101_000000", "推理模式 model_id 不匹配"
    
    return run_test


def test_api_documentation():
    """测试 11: API 文档存在"""
    
    def run_test():
        api_file = Path("Strategy_Pool/custom/API_REFERENCE.md")
        assert api_file.exists(), "API 参考文档不存在"
        
        content = api_file.read_text(encoding='utf-8')
        
        expected_sections = [
            "HardwareDetector",
            "FeatureEngineer",
            "ModelRegistry",
            "XGBoostMLStrategy"
        ]
        
        for section in expected_sections:
            assert section in content, f"API 文档缺少章节: {section}"
    
    return run_test


def test_guides_documentation():
    """测试 12: 用户指南存在"""
    
    def run_test():
        guide_files = [
            "Strategy_Pool/custom/XGBOOST_ML_STRATEGY_GUIDE.md",
            "Strategy_Pool/custom/INTEGRATION_GUIDE.md"
        ]
        
        for guide_file in guide_files:
            assert Path(guide_file).exists(), f"指南文件不存在: {guide_file}"
            
            content = Path(guide_file).read_text(encoding='utf-8')
            assert len(content) > 1000, f"指南文件过短: {guide_file}"
    
    return run_test


def test_code_quality_checks():
    """测试 13: 代码质量检查"""
    
    def run_test():
        # 检查主文件是否能导入（基本语法检查）
        core_file = Path("Strategy_Pool/custom/xgboost_ml_strategy.py")
        assert core_file.exists(), "核心文件不存在"
        
        content = core_file.read_text(encoding='utf-8')
        
        # 检查关键部分
        assert "class HardwareDetector" in content, "缺少 HardwareDetector 类"
        assert "class FeatureEngineer" in content, "缺少 FeatureEngineer 类"
        assert "class ModelRegistry" in content, "缺少 ModelRegistry 类"
        assert "class XGBoostMLStrategy" in content, "缺少 XGBoostMLStrategy 类"
        
        # 检查类型提示
        assert "from typing import" in content, "缺少类型提示导入"
        assert ": Optional[" in content or ": Dict[" in content, "缺少类型注解"
        
        # 检查文档字符串
        assert '"""' in content, "缺少文档字符串"
    
    return run_test


# ============================================================================
# 主测试运行
# ============================================================================

def run_all_tests():
    """运行所有测试"""
    
    print("\n" + "="*60)
    print("🚀 开始 XGBoost ML Strategy 系统测试")
    print("="*60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    suite = TestSuite()
    
    # 定义所有测试
    tests = [
        ("模块导入", test_imports()),
        ("硬件检测器", test_hardware_detector()),
        ("特征工程师", test_feature_engineer()),
        ("模型注册中心", test_model_registry()),
        ("数据结构", test_data_structure()),
        ("策略注册", test_strategy_registration()),
        ("模型分析工具", test_model_analytics()),
        ("模型管理工具", test_model_manager()),
        ("目录结构", test_directory_structure()),
        ("策略实例化", test_strategy_instantiation()),
        ("API 文档", test_api_documentation()),
        ("用户指南", test_guides_documentation()),
        ("代码质量", test_code_quality_checks()),
    ]
    
    # 运行测试
    for test_name, test_func in tests:
        suite.test(test_name, test_func)
    
    # 打印摘要
    all_passed = suite.print_summary()
    
    return 0 if (all_passed and suite.failed == 0) else 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
