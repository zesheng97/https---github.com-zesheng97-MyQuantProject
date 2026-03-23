"""安全数据访问工具 - 防止 None/IndexError 等异常"""
import pandas as pd
from typing import Any, Optional


def safe_get_first(lst, default=None):
    """
    安全获取列表第一个元素
    
    Args:
        lst: 任何可迭代对象或 None
        default: 如果无法获取时的默认值
    
    Returns:
        列表第一个元素，或 default
    
    Examples:
        >>> safe_get_first([1, 2, 3])
        1
        >>> safe_get_first([])
        None
        >>> safe_get_first(None)
        None
        >>> safe_get_first([], -1)
        -1
    """
    try:
        return lst[0] if lst else default
    except (IndexError, TypeError, KeyError):
        return default


def safe_divide(numerator: float, 
                denominator: float, 
                default: float = 0) -> float:
    """
    安全除法，处理 0 和 NaN
    
    Args:
        numerator: 被除数
        denominator: 除数
        default: 如果除数为 0 或 NaN 时的默认值
    
    Returns:
        除法结果，或 default
    
    Examples:
        >>> safe_divide(100, 5)
        20.0
        >>> safe_divide(100, 0)
        0
        >>> safe_divide(100, float('nan'))
        0
    """
    try:
        if denominator == 0:
            return default
        if pd.isna(denominator) or pd.isna(numerator):
            return default
        result = numerator / denominator
        return result if not pd.isna(result) else default
    except (TypeError, ZeroDivisionError, ValueError):
        return default


def safe_get(dictionary: dict, key: str, default=None):
    """
    安全字典访问
    
    Args:
        dictionary: 字典对象或 None
        key: 键名
        default: 默认值
    
    Returns:
        值或 default
    """
    try:
        return dictionary.get(key, default) if dictionary else default
    except (AttributeError, TypeError):
        return default


def validate_price(price) -> bool:
    """
    验证价格有效性 (必须为正数且非 NaN)
    
    Args:
        price: 价格值
    
    Returns:
        True 如果有效，False 否则
    
    Examples:
        >>> validate_price(100)
        True
        >>> validate_price(0)
        False
        >>> validate_price(None)
        False
    """
    if price is None:
        return False
    try:
        p = float(price)
        return not pd.isna(p) and p > 0
    except (ValueError, TypeError):
        return False


def safe_array_access(arr, index: int, default=None):
    """
    安全访问数组指定索引的元素
    
    Args:
        arr: 任何数组或 None
        index: 索引值
        default: 默认值
    
    Returns:
        元素或 default
    """
    try:
        return arr[index] if arr is not None and len(arr) > index else default
    except (IndexError, TypeError, AttributeError):
        return default
