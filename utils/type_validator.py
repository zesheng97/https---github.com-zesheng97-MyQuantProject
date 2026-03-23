"""日期时间类型验证和转换工具"""
from datetime import datetime, date
import pandas as pd
from typing import Union, Optional


def to_datetime(dt_input: Union[datetime, date, pd.Timestamp, None]) -> Optional[datetime]:
    """
    统一转换任何日期对象为 datetime
    
    Args:
        dt_input: datetime, date, pd.Timestamp, 或 None
    
    Returns:
        datetime 对象或 None
    
    Raises:
        TypeError: 无法识别的类型
        
    Examples:
        >>> to_datetime(date(2026, 3, 23))
        datetime.datetime(2026, 3, 23, 0, 0)
        >>> to_datetime(None)
        None
    """
    if dt_input is None:
        return None
    
    if isinstance(dt_input, datetime):
        return dt_input
    
    if isinstance(dt_input, pd.Timestamp):
        return dt_input.to_pydatetime()
    
    if isinstance(dt_input, date):
        return datetime.combine(dt_input, datetime.min.time())
    
    raise TypeError(f"无法转换类型 {type(dt_input)} 为 datetime")


def ensure_datetime(dt_input) -> datetime:
    """
    同上，但不允许 None 返回
    
    Raises:
        ValueError: 如果输入为 None
        TypeError: 无法识别的类型
    """
    result = to_datetime(dt_input)
    if result is None:
        raise ValueError("输入不能为 None")
    return result


def date_range_valid(start: Union[date, datetime], 
                     end: Union[date, datetime]) -> bool:
    """
    验证日期范围有效性 (start < end)
    
    Args:
        start: 开始日期
        end: 结束日期
    
    Returns:
        True 如果 start < end，否则 False
    """
    try:
        start_dt = to_datetime(start)
        end_dt = to_datetime(end)
        
        if start_dt is None or end_dt is None:
            return False
        
        return start_dt < end_dt
    except (TypeError, ValueError):
        return False
