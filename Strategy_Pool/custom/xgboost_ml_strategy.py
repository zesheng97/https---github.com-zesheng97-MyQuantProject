"""
XGBoost 机器学习策略 - MLOps 架构

核心原则：算力零浪费
- 每次训练的模型、特征和性能评估都被沉淀
- Model Registry 统一管理和排序所有训练结果
- 支持推理模式直接加载历史最优模型

文件结构说明：
├── Data_Hub/model_registry/
│   ├── registry.csv (训练日志：model_id, features, params, performance_score, timestamp)
│   ├── xgboost_{timestamp}.json (模型权重文件)
│   ├── features_{timestamp}.pkl (特征列表序列化)
│   └── metadata_{timestamp}.json (训练元数据：超参、耗时等)

Model Registry CSV 列结构：
  - model_id: str, 唯一标识 (xgboost_{timestamp})
  - features_list: str, JSON格式的特征列表 ["rsi_14", "bollinger_width", ...]
  - params_dict: str, JSON格式的超参
  - validation_accuracy: float, 验证集准确率
  - simulation_return: float, 模拟累积收益率
  - performance_score: float, 总体表现分数 (加权综合)
  - training_time: float, 训练耗时(秒)
  - timestamp: str, ISO格式时间戳
"""

import pandas as pd
import numpy as np
import json
import os
import pickle
import warnings
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any, Callable, TYPE_CHECKING
from pathlib import Path
from functools import lru_cache
import logging

# TYPE_CHECKING 块：仅在类型检查时导入（避免运行时错误）
# 这必须在条件导入之前，这样 Pylance 才能正确识别类型
if TYPE_CHECKING:
    import xgboost as xgb  # 类型检查器看到真实的 xgboost 模块

# 条件导入 xgboost（优雅降级）
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    xgb = None

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

warnings.filterwarnings('ignore', category=FutureWarning)

# 日志配置
logger = logging.getLogger(__name__)


class HardwareDetector:
    """智能硬件检测模块 - CUDA GPU / CPU 自适应"""
    
    @staticmethod
    def detect_optimal_config() -> Dict[str, Any]:
        """
        检测最优硬件配置
        
        Returns:
            配置字典，包含 tree_method, device, max_depth, n_jobs 等
        """
        config = {
            'tree_method': 'hist',  # 默认CPU
            'max_depth': 7,
            'n_jobs': -1,
            'device': 'cpu'
        }
        
        try:
            import torch
            if torch.cuda.is_available():
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                
                if gpu_memory >= 8:
                    # 大容量GPU (>=8GB)：允许更深的树
                    # XGBoost 3.1+ 使用 device 参数而非 gpu_hist，设置 device='cuda' 自动使用 GPU
                    config.update({
                        'tree_method': 'hist',  # XGBoost 3.1+ 支持的值，device 决定运行位置
                        'max_depth': 9,
                        'device': 'cuda'
                    })
                else:
                    # 小容量GPU (<8GB)：限制树深防OOM
                    logger.warning(f"GPU 内存 {gpu_memory:.1f}GB，限制 max_depth=6 防止 OOM")
                    config.update({
                        'tree_method': 'hist',  # XGBoost 3.1+ 支持的值，device 决定运行位置
                        'max_depth': 6,
                        'device': 'cuda'
                    })
        except (ImportError, RuntimeError) as e:
            logger.info(f"GPU 不可用，降级至 CPU: {e}")
        
        return config


class FeatureEngineer:
    """特征工程模块 - 自动构建经典技术指标特征"""
    
    @staticmethod
    def build_features(data: pd.DataFrame, lookback_window: int = 20) -> Tuple[pd.DataFrame, List[str]]:
        """
        从 OHLCV 自动构建特征集
        
        Args:
            data: OHLCV DataFrame，必须包含 ['open', 'high', 'low', 'close', 'volume']
            lookback_window: 回溯窗口大小 (默认20天)
        
        Returns:
            (特征DataFrame, 特征列表)
        
        特征列表（至少5个）：
            1. momentum_10: 10日动量 = (close - close[10天前]) / close[10天前]
            2. rsi_14: 14日相对强度指数
            3. bollinger_width: 拓本带宽度 = (upper - lower) / middle
            4. volume_surge: 成交量突变 = vol / vol_ma(20)
            5. volatility: 20日波动率 = close.pct_change().rolling(20).std()
        """
        df = data.copy()
        features_list = []
        
        # 1. 动量特征
        df['momentum_10'] = (df['close'] - df['close'].shift(10)) / df['close'].shift(10)
        features_list.append('momentum_10')
        
        # 2. RSI (相对强度指数)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi_14'] = 100 - (100 / (1 + rs))
        features_list.append('rsi_14')
        
        # 3. 布林带宽度
        sma_20 = df['close'].rolling(window=20).mean()
        std_20 = df['close'].rolling(window=20).std()
        upper_band = sma_20 + 2 * std_20
        lower_band = sma_20 - 2 * std_20
        df['bollinger_width'] = (upper_band - lower_band) / sma_20
        features_list.append('bollinger_width')
        
        # 4. 成交量突变
        vol_ma = df['volume'].rolling(window=20).mean()
        df['volume_surge'] = df['volume'] / vol_ma
        features_list.append('volume_surge')
        
        # 5. 波动率
        df['volatility'] = df['close'].pct_change().rolling(window=20).std()
        features_list.append('volatility')
        
        # 6. 价格位置 (高低差相对位置)
        df['price_position'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-8)
        features_list.append('price_position')
        
        # 7. 对数收益率
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        features_list.append('log_return')
        
        # 删除包含 NaN 的行
        df = df.dropna()
        
        return df, features_list
    
    @staticmethod
    def create_labels(data: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
        """
        为分类模型创建标签（严格防范未来函数）
        
        Args:
            data: 包含特征的 DataFrame
        
        Returns:
            (带标签的DataFrame, 标签列名)
        
        逻辑：
            - 使用 next period 的对数收益率
            - target = 1 if next_log_return > 0 else 0
            - 注意：最后一行会被删除（无未来标签）
        """
        df = data.copy()
        
        # 计算下一期对数收益率（防范未来函数）
        df['next_log_return'] = df['log_return'].shift(-1)
        
        # 标签：1 表示涨，0 表示跌
        df['target'] = (df['next_log_return'] > 0).astype(int)
        
        # 删除最后一行（无标签行）
        df = df.dropna(subset=['target'])
        
        return df, 'target'


class ModelRegistry:
    """Model Registry 管理中心 - 持久化、追踪、排序"""
    
    def __init__(self, registry_dir: str = None):
        """
        初始化注册中心
        
        Args:
            registry_dir: 注册中心目录，默认为 Data_Hub/model_registry/
        """
        if registry_dir is None:
            project_root = Path(__file__).resolve().parents[2]
            registry_dir = os.path.join(project_root, 'Data_Hub', 'model_registry')
        
        self.registry_dir = registry_dir
        self.registry_csv = os.path.join(registry_dir, 'registry.csv')
        
        # 确保目录存在
        os.makedirs(registry_dir, exist_ok=True)
        
        # 初始化 registry.csv（如果不存在）
        if not os.path.exists(self.registry_csv):
            self._init_registry_csv()
    
    def _init_registry_csv(self):
        """初始化空的 registry.csv"""
        columns = [
            'model_id',
            'features_list',
            'params_dict',
            'validation_accuracy',
            'simulation_return',
            'performance_score',
            'training_time',
            'timestamp'
        ]
        df = pd.DataFrame(columns=columns)
        df.to_csv(self.registry_csv, index=False)
    
    def save_model(
        self,
        model: Any,  # xgb.Booster
        features_list: List[str],
        params: Dict[str, Any],
        validation_accuracy: float,
        simulation_return: float,
        training_time: float
    ) -> str:
        """
        保存模型到注册中心
        
        Args:
            model: 训练完的 XGBoost 模型 (xgb.Booster)
            features_list: 使用的特征列表
            params: 超参字典
            validation_accuracy: 验证集准确率 (0-1)
            simulation_return: 模拟累积收益率
            training_time: 训练耗时 (秒)
        
        Returns:
            model_id (用于后续加载/推理)
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_id = f"xgboost_{timestamp}"
        
        # 1. 保存模型权重
        model_path = os.path.join(self.registry_dir, f"{model_id}.json")
        model.save_model(model_path)
        
        # 2. 保存特征列表
        features_path = os.path.join(self.registry_dir, f"features_{timestamp}.pkl")
        with open(features_path, 'wb') as f:
            pickle.dump(features_list, f)
        
        # 3. 保存元数据
        metadata = {
            'model_id': model_id,
            'features_list': features_list,
            'params': params,
            'validation_accuracy': validation_accuracy,
            'simulation_return': simulation_return,
            'training_time': training_time,
            'timestamp': datetime.now().isoformat()
        }
        metadata_path = os.path.join(self.registry_dir, f"metadata_{timestamp}.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # 4. 计算性能分数（加权综合）
        performance_score = 0.6 * validation_accuracy + 0.4 * max(0, simulation_return)
        
        # 5. 追加写入 registry.csv
        new_record = {
            'model_id': model_id,
            'features_list': json.dumps(features_list),
            'params_dict': json.dumps(params),
            'validation_accuracy': round(validation_accuracy, 4),
            'simulation_return': round(simulation_return, 4),
            'performance_score': round(performance_score, 4),
            'training_time': round(training_time, 2),
            'timestamp': datetime.now().isoformat()
        }
        
        df_existing = pd.read_csv(self.registry_csv)
        df_new = pd.DataFrame([new_record])
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined.to_csv(self.registry_csv, index=False)
        
        logger.info(f"✅ 模型已保存：{model_id} (性能分数: {performance_score:.4f})")
        return model_id
    
    def load_model(self, model_id: str) -> Tuple[Any, List[str], Dict[str, Any]]:  # returns (xgb.Booster, ...)
        """
        从注册中心加载模型（推理模式）
        
        Args:
            model_id: 模型ID (例如 "xgboost_20260323_120000")
        
        Returns:
            (模型, 特征列表, 超参字典)
        """
        # 1. 加载模型
        model_path = os.path.join(self.registry_dir, f"{model_id}.json")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在：{model_path}")
        
        model = xgb.Booster()
        model.load_model(model_path)
        
        # 2. 加载特征列表
        timestamp = model_id.replace('xgboost_', '')
        features_path = os.path.join(self.registry_dir, f"features_{timestamp}.pkl")
        with open(features_path, 'rb') as f:
            features_list = pickle.load(f)
        
        # 3. 加载元数据
        metadata_path = os.path.join(self.registry_dir, f"metadata_{timestamp}.json")
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        logger.info(f"✅ 模型已加载：{model_id}")
        return model, features_list, metadata['params']
    
    @staticmethod
    def get_ranked_models(top_n: int = 10, registry_dir: str = None) -> pd.DataFrame:
        """
        获取排名前 N 的最优模型（供 GUI 调用）
        
        Args:
            top_n: 返回数量 (默认10)
            registry_dir: 注册中心目录
        
        Returns:
            排序后的 DataFrame (按 performance_score 降序)
        
        用途：
            在 Streamlit GUI 中，可以这样调用：
            
            best_models = ModelRegistry.get_ranked_models(top_n=10)
            model_options = best_models['model_id'].tolist()
            selected_model = st.selectbox("选择 AI 模型", model_options)
            if st.button("使用这个模型回测"):
                strategy = XGBoostMLStrategy(model_id=selected_model)
        """
        if registry_dir is None:
            project_root = Path(__file__).resolve().parents[2]
            registry_dir = os.path.join(project_root, 'Data_Hub', 'model_registry')
        
        registry_csv = os.path.join(registry_dir, 'registry.csv')
        
        if not os.path.exists(registry_csv):
            logger.warning("注册文件不存在，返回空 DataFrame")
            return pd.DataFrame()
        
        df = pd.read_csv(registry_csv)
        
        if df.empty:
            logger.warning("注册中心为空")
            return df
        
        # 按性能分数降序排列
        df_sorted = df.sort_values('performance_score', ascending=False).head(top_n)
        
        # 反序列化 JSON 字段以便显示
        df_sorted = df_sorted.copy()
        df_sorted['features_count'] = df_sorted['features_list'].apply(lambda x: len(json.loads(x)))
        
        return df_sorted


class XGBoostMLStrategy:
    """
    XGBoost 机器学习策略 - 支持训练与推理双模式
    
    使用示例：
        # 训练模式
        strategy_train = XGBoostMLStrategy(
            model_id=None,  # 触发训练
            time_limit=300,  # 5分钟超时
            target_limit=100  # 100个样本早停
        )
        result = strategy_train.backtest(data, params={})
        
        # 推理模式
        strategy_inference = XGBoostMLStrategy(
            model_id="xgboost_20260323_120000"  # 直接加载历史模型
        )
        result = strategy_inference.backtest(data, params={})
    """
    
    def __init__(
        self,
        name: str = "XGBoost机器学习策略",
        description_cn: str = "使用 XGBoost 进行特征工程和二分类预测信号生成，支持 Model Registry 进行模型管理和复用",
        description_en: str = "XGBoost-based ML strategy with feature engineering and Model Registry for model persistence",
        model_id: Optional[str] = None,
        time_limit: Optional[int] = None,
        target_limit: Optional[int] = None,
        progress_callback: Optional[Callable] = None
    ):
        """
        初始化策略
        
        Args:
            name: 策略名称
            description_cn: 中文描述
            description_en: 英文描述
            model_id: 模型ID (推理模式)，为 None 则进入训练模式
            time_limit: 训练时间限制（秒），超时则保存当前最佳模型并终止
            target_limit: 早停样本数量，验证集表现 N 次未改进则停止
            progress_callback: 进度回调函数，签名为 progress_callback(current, total, message)
        """
        self.name = name
        self.description_cn = description_cn
        self.description_en = description_en
        self.model_id = model_id
        self.time_limit = time_limit
        self.target_limit = target_limit or 100
        self.progress_callback = progress_callback
        
        # 检查 XGBoost 依赖
        if not XGBOOST_AVAILABLE and model_id is None:
            raise ImportError(
                "❌ XGBoost 未安装。训练模式需要 XGBoost。\n"
                "请运行: pip install xgboost>=2.0.0\n"
                "或在 requirements.txt 中添加: xgboost>=2.0.0"
            )
        
        self.registry = ModelRegistry()
        self.hardware_config = HardwareDetector.detect_optimal_config()
        self.model = None
        self.features_list = None
        self.feature_engineer = FeatureEngineer()
        
        logger.info(f"策略初始化完成 | 硬件: {self.hardware_config['device'].upper()}")
    
    def backtest(
        self,
        data: pd.DataFrame,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        回测/训练主函数
        
        Args:
            data: OHLCV DataFrame
            params: 策略参数（目前保留供扩展）
        
        Returns:
            包含 signal 列的 DataFrame (简单模式)
        """
        params = params or {}
        
        if self.model_id:
            # ============ 推理模式 ============
            logger.info(f"进入推理模式，加载模型: {self.model_id}")
            return self._inference_mode(data)
        else:
            # ============ 训练模式 ============
            logger.info("进入训练模式，执行完整训练流程")
            return self._training_mode(data, params)
    
    def _training_mode(self, data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
        """
        训练模式：特征构建 -> 模型训练 -> 信号生成 -> 持久化
        """
        import time
        start_time = time.time()
        
        # Step 1: 特征工程
        if self.progress_callback:
            self.progress_callback(0, 5, "🔨 构建特征...")
        
        df_features, self.features_list = self.feature_engineer.build_features(data)
        logger.info(f"特征列: {self.features_list}")
        
        # Step 2: 创建标签
        if self.progress_callback:
            self.progress_callback(1, 5, "🏷️ 创建标签...")
        
        df_labeled, target_col = FeatureEngineer.create_labels(df_features)
        
        # Step 3: 数据分割 (80% train, 20% val)
        if self.progress_callback:
            self.progress_callback(2, 5, "✂️ 分割数据...")
        
        n = len(df_labeled)
        split_idx = int(0.8 * n)
        
        X_train = df_labeled[self.features_list].iloc[:split_idx].values
        y_train = df_labeled[target_col].iloc[:split_idx].values
        
        X_val = df_labeled[self.features_list].iloc[split_idx:].values
        y_val = df_labeled[target_col].iloc[split_idx:].values
        
        # Step 4: 模型训练（带超时和早停）
        if self.progress_callback:
            self.progress_callback(3, 5, "🚀 开始训练...")
        
        self.model = self._train_with_controls(X_train, y_train, X_val, y_val, start_time)
        
        # Step 5: 性能评估
        if self.progress_callback:
            self.progress_callback(4, 5, "📊 评估性能...")
        
        val_pred = self.model.predict(xgb.DMatrix(X_val))
        val_pred_binary = (val_pred > 0.5).astype(int)
        validation_accuracy = (val_pred_binary == y_val).mean()
        
        # 模拟累积收益
        df_val_copy = df_labeled.iloc[split_idx:].copy()
        df_val_copy['pred_signal'] = val_pred_binary
        df_val_copy['pred_return'] = df_val_copy['pred_signal'] * df_val_copy['next_log_return']
        simulation_return = np.exp(df_val_copy['pred_return'].sum()) - 1
        
        # Step 6: 持久化
        training_time = time.time() - start_time
        self.model_id = self.registry.save_model(
            self.model,
            self.features_list,
            params,
            validation_accuracy,
            simulation_return,
            training_time
        )
        
        if self.progress_callback:
            self.progress_callback(5, 5, f"✅ 训练完成！模型ID: {self.model_id}")
        
        # Step 7: 生成全量回测信号
        return self._generate_signals(df_labeled)
    
    def _train_with_controls(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        start_time: float
    ) -> Any:  # returns xgb.Booster
        """
        带超时和早停的训练控制（使用 XGBoost 原生 API）
        
        Args:
            X_train, y_train: 训练集
            X_val, y_val: 验证集
            start_time: 训练开始时间
        
        Returns:
            训练完的模型 (xgb.Booster)
        """
        import time
        
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dval = xgb.DMatrix(X_val, label=y_val)
        
        xgb_params = {
            'objective': 'binary:logistic',
            'eval_metric': 'logloss',
            'max_depth': self.hardware_config['max_depth'],
            'learning_rate': 0.05,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'tree_method': self.hardware_config['tree_method'],
            'device': self.hardware_config['device']  # 使用 device 而非 gpu_id (XGBoost 3.1+)
        }
        
        num_boost_round = 1000
        
        # 构建 XGBoost 回调
        callbacks = [xgb.callback.EarlyStopping(rounds=self.target_limit, save_best=True)]
        
        # 超时回调
        cb_start_time = start_time
        cb_time_limit = self.time_limit
        cb_progress = self.progress_callback
        
        class TimeoutAndProgress(xgb.callback.TrainingCallback):
            def after_iteration(self, model, epoch, evals_log):
                # 超时熔断
                if cb_time_limit and (time.time() - cb_start_time) > cb_time_limit:
                    logger.warning(f"⏱️ 超时熔断！已训练 {epoch} 轮")
                    return True  # True = stop training
                # 进度回调（每 20 轮）
                if cb_progress and epoch % 20 == 0:
                    pct = 3 + (1.4 * min(epoch / num_boost_round, 1.0))
                    cb_progress(pct, 5, f"🔄 训练进行中... (第 {epoch} 轮)")
                return False  # False = continue
        
        callbacks.append(TimeoutAndProgress())
        
        evals_result = {}
        
        model = xgb.train(
            xgb_params,
            dtrain,
            num_boost_round=num_boost_round,
            evals=[(dval, 'eval')],
            evals_result=evals_result,
            callbacks=callbacks,
            verbose_eval=False
        )
        
        actual_rounds = len(evals_result.get('eval', {}).get('logloss', []))
        logger.info(f"训练完成: {actual_rounds} 轮, 最佳 logloss: {min(evals_result.get('eval', {}).get('logloss', [float('inf')])):.4f}")
        
        return model
    
    def _inference_mode(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        推理模式：直接加载模型并生成信号
        """
        # 加载模型和特征列表
        self.model, self.features_list, params = self.registry.load_model(self.model_id)
        
        # 构建特征
        df_features, _ = self.feature_engineer.build_features(data)
        
        # 生成信号
        return self._generate_signals(df_features)
    
    def _generate_signals(self, df_features: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            df_features: 包含特征的 DataFrame
        
        Returns:
            包含 signal 列的 DataFrame
        """
        df_result = df_features.copy()
        
        # 获取特征列（处理缺失特征）
        available_features = [f for f in self.features_list if f in df_features.columns]
        
        if not available_features:
            logger.warning(f"⚠️ 缺失所有特征！使用默认信号")
            df_result['signal'] = 0
            return df_result
        
        X = df_features[available_features].values
        dmatrix = xgb.DMatrix(X)
        probs = self.model.predict(dmatrix)
        
        # 二分类：概率 > 0.5 -> 买入 (signal=1), 否则卖出 (signal=-1)
        df_result['signal'] = np.where(probs > 0.5, 1, -1)
        
        # 计算收益率
        df_result['returns'] = df_result['signal'].shift(1) * df_result['close'].pct_change()
        
        return df_result.dropna()
