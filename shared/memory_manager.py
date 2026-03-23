"""全局最佳策略记忆管理 - 打破循环导入"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class BestStrategyMemory:
    """
    管理最佳策略记录，避免循环导入
    
    这个类将最佳策略的保存/加载从 GUI 中分离出来，
    使得 strategies.py 不需要导入 app_v2.py
    """
    
    _storage_path = Path("data/best_strategies.json")
    
    @classmethod
    def _ensure_storage(cls):
        """确保存储目录存在"""
        cls._storage_path.parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def save(cls, symbol: str, strategy_name: str, 
             params: Dict[str, Any], score: float):
        """
        保存最佳策略
        
        Args:
            symbol: 股票代码
            strategy_name: 策略名称
            params: 策略参数字典
            score: 评分 (如 Sharpe Ratio)
        """
        cls._ensure_storage()
        
        try:
            if cls._storage_path.exists():
                with open(cls._storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
            
            data[symbol] = {
                'strategy': strategy_name,
                'params': params,
                'score': float(score),
                'updated_at': datetime.now().isoformat()
            }
            
            with open(cls._storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[警告] 保存最佳策略失败: {e}")
    
    @classmethod
    def load(cls, symbol: str) -> Optional[Dict]:
        """
        加载最佳策略
        
        Args:
            symbol: 股票代码
        
        Returns:
            策略字典 (包含 strategy, params, score, updated_at)，或 None
        """
        try:
            if not cls._storage_path.exists():
                return None
            
            with open(cls._storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data.get(symbol)
        except Exception as e:
            print(f"[警告] 加载最佳策略失败: {e}")
            return None
    
    @classmethod
    def clear(cls, symbol: str):
        """
        清除指定股票的记录
        
        Args:
            symbol: 股票代码
        """
        cls._ensure_storage()
        try:
            if cls._storage_path.exists():
                with open(cls._storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if symbol in data:
                    del data[symbol]
                    
                    with open(cls._storage_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[警告] 清除最佳策略失败: {e}")
