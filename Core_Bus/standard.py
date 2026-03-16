# 文件位置: Core_Bus/standard.py
import pandas as pd

def standardize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    核心总线标准：将任何外部数据源的 DataFrame 转换为系统标准格式。
    规范：列名全小写，必须包含 open, high, low, close, volume，索引必须是 datetime 类型且名为 date。
    """
    if df.empty:
        return df
        
    # yfinance 可能返回 MultiIndex 列 (Price, Ticker) 形式，这里简化为第一层列名
    if isinstance(df.columns, pd.MultiIndex):
        first_level = df.columns.get_level_values(0)
        df.columns = first_level

    # 强制统一列名为小写
    normalized_columns = []
    for col in df.columns:
        if isinstance(col, str):
            normalized_columns.append(col.lower())
        else:
            normalized_columns.append(str(col).lower())
    df.columns = normalized_columns
    
    # 确保必须的核心列存在
    core_columns = ['open', 'high', 'low', 'close', 'volume']
    for col in core_columns:
        if col not in df.columns:
            raise ValueError(f"数据缺失核心列: {col}")
            
    # 只保留核心列，剔除诸如 Dividends, Stock Splits 等无用列
    df = df[core_columns].copy()
    
    # 标准化索引名称
    df.index.name = 'date'
    
    return df