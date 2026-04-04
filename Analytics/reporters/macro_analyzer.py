"""
宏观分析器 | Macro Analyzer
功能：获取美股大盘指数、FINRA融资余额、Federal Reserve利率数据
       并计算各指标间的相关性（IC）和差异性拐点
"""

import os
import json
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path


# 本地缓存目录
MACRO_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'Data_Hub', 'storage', '.macro_cache')

# 美股主要大盘指数
INDEX_MAP = {
    "S&P 500":        "^GSPC",
    "NASDAQ Composite": "^IXIC",
    "NASDAQ 100":     "^NDX",
    "Dow Jones":      "^DJI",
    "VIX (恐慌指数)": "^VIX",
    "Russell 2000":   "^RUT",
}

# 利率相关标的
RATE_MAP = {
    "10Y国债收益率":  "^TNX",
    "2Y国债收益率":   "^IRX",
    "美元指数":       "DX-Y.NYB",
}

# ========== 综合宏观指标映射表 ==========
# 包含股票指数、波动率、利率、债券、大宗商品、汇率、资产配置等 25+ 常用指标
# 注意：部分指标如 FINRA Margin Debt (内置) 和 Term Spread (计算) 需特殊处理
MACRO_INDICATORS_MAP = {
    # ========== 股票指数 ==========
    "S&P 500":           "^GSPC",
    "NASDAQ Composite":  "^IXIC",
    "NASDAQ 100":        "^NDX",
    "Dow Jones":         "^DJI",
    "Russell 2000":      "^RUT",
    "纳斯达克100(QQQ)":  "QQQ",
    
    # ========== 波动率/风险 ==========
    "VIX (恐慌指数)":    "^VIX",
    
    # ========== 利率/债券 ==========
    "10Y美债收益率":     "^TNX",
    "2Y美债收益率":      "^IRX",
    "债券综合指数(AGG)": "AGG",
    "投资级债券(LQD)":   "LQD",
    "高收益债券(HYG)":   "HYG",
    "长期美债(TLT)":     "TLT",
    
    # ========== 大宗商品 ==========
    "黄金(GLD)":         "GLD",
    "白银(SLV)":         "SLV",
    "原油(CL=F)":        "CL=F",
    "天然气(NG=F)":      "NG=F",
    
    # ========== 汇率/美元 ==========
    "美元指数(DXY)":     "DXY",
    "欧元/美元(EURUSD)": "EURUSD=X",
    "日元/美元(JPY)":    "JPY=X",
    "英镑/美元(GBP)":    "GBPUSD=X",
    
    # ========== 资产配置 ==========
    "新兴市场(EEM)":     "EEM",
    "房地产REITs(VNQ)":  "VNQ",
    "金融板块(XLF)":     "XLF",
    "科技板块(XLK)":     "XLK",
    "公用事业(XLU)":     "XLU",
    "消费必需(XLP)":     "XLP",
    "医疗保健(XLV)":     "XLV",
    
    # ========== 加密资产 ==========
    "比特币(BTC)":       "BTC-USD",
    "以太坊(ETH)":       "ETH-USD",
}

# FINRA Margin Debt 历史数据（手工内置，来源FINRA官方统计，单位：百万美元）
# 数据截止到约2024年，后续月份可通过API补充。
FINRA_MARGIN_DEBT_BUILTIN = {
    "2002-01": 278530, "2002-06": 230647, "2002-12": 171636,
    "2003-06": 190682, "2003-12": 215400,
    "2004-06": 236120, "2004-12": 244671,
    "2005-06": 263745, "2005-12": 272691,
    "2006-06": 313437, "2006-12": 328390,
    "2007-06": 459894, "2007-07": 479954, "2007-12": 415688,
    "2008-06": 341500, "2008-12": 186400,
    "2009-06": 199800, "2009-12": 238652,
    "2010-06": 253834, "2010-12": 271800,
    "2011-06": 307726, "2011-12": 264979,
    "2012-06": 303280, "2012-12": 327272,
    "2013-06": 384319, "2013-12": 444931,
    "2014-06": 466100, "2014-12": 465719,
    "2015-06": 505893, "2015-12": 455526,
    "2016-06": 432600, "2016-12": 473132,
    "2017-06": 539361, "2017-12": 580976,
    "2018-06": 636300, "2018-12": 554285,
    "2019-06": 571900, "2019-12": 573980,
    "2020-03": 479307, "2020-06": 608700, "2020-12": 722100,
    "2021-03": 813000, "2021-06": 882142, "2021-10": 935983, "2021-12": 918679,
    "2022-01": 829650, "2022-06": 636400, "2022-12": 588000,
    "2023-03": 635082, "2023-06": 679965, "2023-12": 698530,
    "2024-03": 787200, "2024-06": 804300, "2024-09": 812560,
}


def _ensure_cache_dir():
    os.makedirs(MACRO_CACHE_DIR, exist_ok=True)


def _cache_path(key: str) -> str:
    _ensure_cache_dir()
    return os.path.join(MACRO_CACHE_DIR, f"{key}.parquet")


def _cache_meta_path() -> str:
    _ensure_cache_dir()
    return os.path.join(MACRO_CACHE_DIR, "meta.json")


def _load_meta() -> dict:
    p = _cache_meta_path()
    if os.path.exists(p):
        try:
            with open(p, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_meta(meta: dict):
    with open(_cache_meta_path(), 'w') as f:
        json.dump(meta, f)


def get_us_eastern_date() -> str:
    """获取美国东部时间的当前日期（YYYY-MM-DD）"""
    from pytz import timezone
    import datetime as dt
    et = timezone('America/New_York')
    return dt.datetime.now(et).strftime('%Y-%m-%d')


def get_data_last_update_date() -> str:
    """获取上次数据更新的日期标记"""
    meta = _load_meta()
    return meta.get("data_update_date", "")


def set_data_update_date():
    """设置当前日期为数据更新标记"""
    meta = _load_meta()
    meta["data_update_date"] = get_us_eastern_date()
    _save_meta(meta)


def should_update_data() -> bool:
    """
    判断是否需要更新数据。
    当当前日期与上次更新日期不同时，返回True。
    """
    current_date = get_us_eastern_date()
    last_update = get_data_last_update_date()
    return current_date != last_update


def _is_cache_fresh(key: str, max_hours: int = 12) -> bool:
    meta = _load_meta()
    ts = meta.get(key)
    if not ts:
        return False
    age = (datetime.now() - datetime.fromisoformat(ts)).total_seconds() / 3600
    return age < max_hours


def fetch_index_data(symbols: list, period: str = "10y", force_refresh: bool = False) -> dict:
    """
    获取大盘指数的历史OHLCV数据。

    Parameters
    ----------
    symbols : list  — yfinance tickers, e.g. ['^GSPC', '^IXIC']
    period  : str   — '1y','3y','5y','10y','20y','max'
    force_refresh : bool

    Returns
    -------
    dict  {ticker: pd.DataFrame(close, volume)}
    """
    result = {}
    meta = _load_meta()

    for ticker in symbols:
        cache_key = f"idx_{ticker.replace('^','').replace('-','_')}_{period}"
        cache_file = _cache_path(cache_key)

        if not force_refresh and _is_cache_fresh(cache_key, max_hours=12) and os.path.exists(cache_file):
            try:
                result[ticker] = pd.read_parquet(cache_file)
                continue
            except Exception:
                pass

        try:
            raw = yf.download(ticker, period=period, progress=False, auto_adjust=True)
            if raw.empty:
                continue
            # Flatten MultiIndex columns if present
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = [c[0].lower() for c in raw.columns]
            else:
                raw.columns = [c.lower() for c in raw.columns]
            df = raw[['close']].copy()
            if 'volume' in raw.columns:
                df['volume'] = raw['volume']
            df.index = pd.to_datetime(df.index)
            df.to_parquet(cache_file)
            meta[cache_key] = datetime.now().isoformat()
            _save_meta(meta)
            result[ticker] = df
        except Exception:
            pass

    return result


def get_margin_debt_series() -> pd.Series:
    """
    返回 FINRA Margin Debt 历史时间序列（月度，单位：百万美元）。
    数据来自内置字典（含2002-2024年关键月份）。
    """
    pairs = []
    for date_str, value in FINRA_MARGIN_DEBT_BUILTIN.items():
        pairs.append((pd.to_datetime(date_str + "-01"), value))
    s = pd.Series(dict(pairs), name="margin_debt_million_usd").sort_index()
    return s


def compute_yoy_change(series: pd.Series) -> pd.Series:
    """计算同比变化率（YoY %）"""
    shifted = series.shift(12)  # 月度数据向后移12期
    yoy = ((series - shifted) / shifted.abs()) * 100
    yoy.name = "yoy_pct"
    return yoy


def align_and_resample_monthly(df_dict: dict) -> pd.DataFrame:
    """
    将多个日频指数数据重采样为月末收盘价，
    对齐后返回宽格式 DataFrame。
    """
    frames = {}
    for ticker, df in df_dict.items():
        monthly = df['close'].resample('ME').last()
        frames[ticker] = monthly
    if not frames:
        return pd.DataFrame()
    combined = pd.DataFrame(frames)
    combined.dropna(how='all', inplace=True)
    return combined


def compute_correlation_matrix(df: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
    """计算各列之间的相关系数矩阵"""
    return df.pct_change().dropna().corr(method=method)


def compute_rolling_correlation(s1: pd.Series, s2: pd.Series, window: int = 12) -> pd.Series:
    """计算滚动相关系数（IC代理），窗口单位与序列频率一致"""
    combined = pd.concat([s1, s2], axis=1).dropna()
    if combined.empty or len(combined) < window:
        return pd.Series(dtype=float)
    pct = combined.pct_change().dropna()
    rolling_corr = pct.iloc[:, 0].rolling(window).corr(pct.iloc[:, 1])
    rolling_corr.name = f"rolling_corr_{window}p"
    return rolling_corr


def fetch_multi_indicators(
    indicator_names: list,
    period: str = "10y",
    force_refresh: bool = False,
    daily_to_monthly: bool = True,
) -> pd.DataFrame:
    """
    获取多个指标的数据并对齐为统一时间序列（默认月频）。
    
    支持特殊指标处理：
      - "FINRA 融资余额" 使用内置数据
      - "Term Spread(10Y-2Y)" 计算得来（需要同时获取 10Y 和 2Y 债券收益率）
    
    Parameters
    ----------
    indicator_names : list  所需指标名称，列表中每项必须在 MACRO_INDICATORS_MAP 中
    period : str  历史数据周期
    force_refresh : bool
    daily_to_monthly : bool  是否将日频数据重采样为月频（默认True）
    
    Returns
    -------
    pd.DataFrame  index=日期/月末, columns=指标名称（同输入顺序）
    """
    result_frames = {}
    tickers_to_fetch = []
    ticker_to_indicator = {}  # 映射：ticker -> indicator_name
    
    for name in indicator_names:
        if name == "FINRA 融资余额":
            # 内置数据特殊处理
            result_frames[name] = get_margin_debt_series()
        elif name == "Term Spread(10Y-2Y)":
            # 计算得来，需要10Y和2Y数据
            tickers_to_fetch.append("^TNX")
            ticker_to_indicator["^TNX"] = ("10Y_for_spread", name)
            tickers_to_fetch.append("^IRX")
            ticker_to_indicator["^IRX"] = ("2Y_for_spread", name)
        else:
            # 从 MACRO_INDICATORS_MAP 查询 ticker
            if name in MACRO_INDICATORS_MAP:
                ticker = MACRO_INDICATORS_MAP[name]
                tickers_to_fetch.append(ticker)
                ticker_to_indicator[ticker] = (ticker, name)
    
    # 一次性获取所有 ticker 数据
    if tickers_to_fetch:
        raw_data = fetch_index_data(list(set(tickers_to_fetch)), period=period, force_refresh=force_refresh)
        
        for ticker, (_, indicator_name) in ticker_to_indicator.items():
            if ticker in raw_data:
                series = raw_data[ticker]["close"].squeeze() if "close" in raw_data[ticker].columns else raw_data[ticker].iloc[:, 0]
                result_frames[indicator_name] = series
    
    if not result_frames:
        return pd.DataFrame()
    
    # 统一转换为日频 DataFrame
    daily_df = pd.DataFrame(result_frames)
    daily_df.index = pd.to_datetime(daily_df.index)
    
    # 处理 Term Spread（10Y - 2Y）
    if "Term Spread(10Y-2Y)" in indicator_names and "10Y_for_spread" in result_frames and "2Y_for_spread" in result_frames:
        daily_df["Term Spread(10Y-2Y)"] = result_frames.get("10Y_for_spread", pd.Series()) - result_frames.get("2Y_for_spread", pd.Series())
        # 删除临时列
        daily_df = daily_df[[c for c in daily_df.columns if not c.startswith(("10Y_for_spread", "2Y_for_spread"))]]
    
    # 可选：转换为月频
    if daily_to_monthly:
        monthly_df = daily_df.resample("ME").last()
        return monthly_df.dropna(how="all")
    else:
        return daily_df



def detect_divergence_points(s1: pd.Series, s2: pd.Series, window: int = 3) -> pd.DataFrame:
    """
    检测两序列之间的差异性拐点：
    - 一个序列上升而另一个下降（或反向）
    - 输出包含方向和时间信息的 DataFrame
    """
    combined = pd.concat([s1.rename("A"), s2.rename("B")], axis=1).dropna()
    if combined.empty:
        return pd.DataFrame()

    chg = combined.pct_change(window).dropna()
    # 拐点条件：A, B的同期变化方向相反
    divergence = chg[(chg["A"] * chg["B"] < 0)].copy()
    divergence["A_dir"] = divergence["A"].apply(lambda x: "↑" if x > 0 else "↓")
    divergence["B_dir"] = divergence["B"].apply(lambda x: "↑" if x > 0 else "↓")
    divergence["A_chg_pct"] = divergence["A"].round(4) * 100
    divergence["B_chg_pct"] = divergence["B"].round(4) * 100
    return divergence[["A_dir", "A_chg_pct", "B_dir", "B_chg_pct"]]


def compute_lead_lag(s1: pd.Series, s2: pd.Series, max_lag: int = 6) -> pd.DataFrame:
    """
    计算 s1 相对于 s2 的领先/滞后相关性（月度）。
    正 lag 表示 s1 领先 s2。
    """
    pct1 = s1.pct_change().dropna()
    pct2 = s2.pct_change().dropna()

    records = []
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            corr = pct1.shift(lag).corr(pct2)
        else:
            corr = pct1.corr(pct2.shift(-lag))
        records.append({"lag_months": lag, "correlation": round(corr, 4) if not np.isnan(corr) else None})
    return pd.DataFrame(records)


# ===========================================================================
# VIX 三阶段分析 & 入场信号
# ===========================================================================

VIX_SPIKE_THRESHOLD  = 30   # VIX > 30 进入高企观察期
VIX_PEAK_THRESHOLD   = 40   # VIX > 40 视为极度恐慌峰值区
VIX_PULLBACK_RATIO   = 0.90  # 从本轮高点回落 10% 触发信号


def detect_vix_spikes(
    vix_series: pd.Series,
    spike_threshold: float = VIX_SPIKE_THRESHOLD,
    peak_threshold: float  = VIX_PEAK_THRESHOLD,
    cooldown_threshold: float = VIX_SPIKE_THRESHOLD,
) -> pd.DataFrame:
    """
    识别 VIX 历史上每一次飙升事件，返回各事件的起始日、峰值日、峰值、结束日。

    阶段定义：
      - 前期 (spike_phase)  : VIX 首次突破 spike_threshold
      - 中期 (peak_phase)   : VIX > peak_threshold（最高恐慌区）
      - 后期 (cooldown)     : VIX 开始持续回落，直至回到 spike_threshold 以下

    Returns
    -------
    pd.DataFrame  columns: start, peak_date, peak_value, end, duration_days
    """
    if vix_series.empty:
        return pd.DataFrame()

    vix = vix_series.dropna().copy()
    in_spike = False
    records = []
    spike_start = None
    running_max = 0.0
    peak_date_local = None

    for dt, val in vix.items():
        if not in_spike:
            if val > spike_threshold:
                in_spike = True
                spike_start = dt
                running_max = val
                peak_date_local = dt
        else:
            if val > running_max:
                running_max = val
                peak_date_local = dt
            # 回到阈值以下 → 当前事件结束
            if val < cooldown_threshold:
                records.append({
                    "start":       spike_start,
                    "peak_date":   peak_date_local,
                    "peak_value":  round(running_max, 2),
                    "end":         dt,
                    "duration_days": (dt - spike_start).days,
                })
                in_spike = False
                spike_start = None
                running_max = 0.0
                peak_date_local = None

    # 若目前仍处于 spike 中（尚未结束）
    if in_spike and spike_start is not None:
        records.append({
            "start":       spike_start,
            "peak_date":   peak_date_local,
            "peak_value":  round(running_max, 2),
            "end":         None,
            "duration_days": (vix.index[-1] - spike_start).days,
        })

    return pd.DataFrame(records)


def classify_vix_phase(
    vix_series: pd.Series,
    spike_threshold: float = VIX_SPIKE_THRESHOLD,
    peak_threshold:  float = VIX_PEAK_THRESHOLD,
    pullback_ratio:  float = VIX_PULLBACK_RATIO,
) -> pd.Series:
    """
    对每个交易日打上 VIX 阶段标签：
      - 'normal'    : VIX <= spike_threshold
      - 'spike'     : 前期 — VIX 突破 spike_threshold 向上运动
      - 'peak'      : 中期 — VIX > peak_threshold（极度恐慌）
      - 'cooldown'  : 后期 — VIX 已从本轮峰值回落 > (1-pullback_ratio)

    Returns
    -------
    pd.Series  与 vix_series 索引对齐，值为阶段字符串
    """
    vix = vix_series.dropna().copy()
    phase = pd.Series("normal", index=vix.index)

    spikes_df = detect_vix_spikes(vix, spike_threshold, peak_threshold)
    if spikes_df.empty:
        return phase

    for _, row in spikes_df.iterrows():
        start = row["start"]
        end   = row["end"] if row["end"] is not None else vix.index[-1]
        peak_val = row["peak_value"]
        cooldown_trigger = peak_val * pullback_ratio  # 回落 10% 即进入后期

        window = vix.loc[start:end]
        found_peak = False

        for dt, val in window.items():
            if val > peak_threshold:
                found_peak = True

            if found_peak and val <= cooldown_trigger:
                # 从此日起到事件结束为后期
                phase.loc[dt:end] = "cooldown"
                break
            elif found_peak:
                phase.loc[dt] = "peak"
            else:
                phase.loc[dt] = "spike"

        # 补全：peak 之前（起始到第一个 peak 日） 标为 spike
        pre_peak = vix.loc[start:end]
        pre_peak = pre_peak[pre_peak <= peak_threshold]
        for dt in pre_peak.index:
            if phase.loc[dt] == "normal":
                phase.loc[dt] = "spike"

    return phase


def compute_vix_entry_signals(
    vix_series:  pd.Series,
    index_series: pd.Series,
    spike_threshold: float = VIX_SPIKE_THRESHOLD,
    peak_threshold:  float = VIX_PEAK_THRESHOLD,
    pullback_ratio:  float = VIX_PULLBACK_RATIO,
    forward_windows: list = None,
    cooldown_confirmation_days: int = 1,
    min_spike_duration_days: int = 0,
    min_peak_vix: float = None,
) -> pd.DataFrame:
    """
    在每个 VIX spike 事件中，识别「后期入场信号」和统计三阶段的
    前瞻收益分布（forward returns）。

    入场信号定义：VIX 从本轮峰值回落至  peak_value * pullback_ratio 时的日期。

    Parameters
    ----------
    vix_series    — 日频 VIX 数据
    index_series  — 对应大盘指数（如 S&P 500）日频收盘
    forward_windows — 前瞻窗口列表（交易日数），默认 [5, 10, 21, 63]
    cooldown_confirmation_days — 触发后期信号前，需要连续满足回落条件的交易日数量
    min_spike_duration_days — 仅保留持续时间不短于该阈值的 VIX 事件
    min_peak_vix — 仅保留峰值 VIX 不低于该阈值的事件

    Returns
    -------
    pd.DataFrame  每行一个 spike 事件, 含信号日期、入场价、各窗口前瞻收益
    """
    if forward_windows is None:
        forward_windows = [5, 10, 21, 63]

    spikes_df = detect_vix_spikes(vix_series, spike_threshold, peak_threshold)
    if spikes_df.empty:
        return pd.DataFrame()

    idx_aligned = index_series.reindex(vix_series.index).ffill()
    records = []

    for _, row in spikes_df.iterrows():
        start    = row["start"]
        end      = row["end"] if row["end"] is not None else vix_series.index[-1]
        peak_val = row["peak_value"]
        trigger  = peak_val * pullback_ratio

        if row.get("duration_days") is not None and row["duration_days"] < min_spike_duration_days:
            continue
        if min_peak_vix is not None and peak_val < min_peak_vix:
            continue

        # 找信号日：峰值日之后 VIX 首次下穿 trigger
        vix_window = vix_series.loc[row["peak_date"]:end]
        signal_date = None
        confirmation_count = 0
        for dt, val in vix_window.items():
            if val <= trigger:
                confirmation_count += 1
                if confirmation_count >= max(int(cooldown_confirmation_days), 1):
                    signal_date = dt
                    break
            else:
                confirmation_count = 0

        if signal_date is None:
            continue

        entry_price = idx_aligned.get(signal_date)
        if entry_price is None or np.isnan(entry_price):
            continue

        rec = {
            "spike_start":    start.date(),
            "peak_date":      row["peak_date"].date(),
            "peak_vix":       peak_val,
            "signal_date":    signal_date.date(),
            "signal_vix":     round(vix_series.get(signal_date), 2),
            "entry_price":    round(entry_price, 2),
        }
        # 前瞻收益
        for w in forward_windows:
            future_idx = idx_aligned.index.searchsorted(signal_date)
            future_idx_end = future_idx + w
            if future_idx_end < len(idx_aligned):
                future_price = idx_aligned.iloc[future_idx_end]
                ret = (future_price / entry_price - 1) * 100
                rec[f"fwd_{w}d_return"] = round(ret, 2)
            else:
                rec[f"fwd_{w}d_return"] = None
        records.append(rec)

    return pd.DataFrame(records)


def compute_phase_forward_returns(
    vix_series:   pd.Series,
    index_series: pd.Series,
    spike_threshold: float = VIX_SPIKE_THRESHOLD,
    peak_threshold:  float = VIX_PEAK_THRESHOLD,
    pullback_ratio:  float = VIX_PULLBACK_RATIO,
    forward_days: int = 21,
) -> pd.DataFrame:
    """
    统计「前期 / 中期 / 后期」三阶段买入的前瞻 N 日收益分布均值与胜率。

    Returns
    -------
    pd.DataFrame  index=['spike','peak','cooldown'], columns=['count','mean_return','win_rate','max_dd']
    """
    phase_series = classify_vix_phase(vix_series, spike_threshold, peak_threshold, pullback_ratio)
    idx_aligned  = index_series.reindex(vix_series.index).ffill()

    phase_returns = {"spike": [], "peak": [], "cooldown": []}

    dates = idx_aligned.index
    for i, dt in enumerate(dates):
        ph = phase_series.get(dt)
        if ph not in phase_returns:
            continue
        future_i = i + forward_days
        if future_i >= len(dates):
            continue
        entry  = idx_aligned.iloc[i]
        future = idx_aligned.iloc[future_i]
        if entry > 0:
            phase_returns[ph].append((future / entry - 1) * 100)

    rows = []
    for ph, rets in phase_returns.items():
        if not rets:
            rows.append({"phase": ph, "count": 0, "mean_return": None,
                         "win_rate": None, "max_dd": None})
            continue
        arr = np.array(rets)
        rows.append({
            "phase":       ph,
            "count":       len(arr),
            "mean_return": round(arr.mean(), 2),
            "win_rate":    round((arr > 0).mean() * 100, 1),
            "max_dd":      round(arr.min(), 2),
        })
    df = pd.DataFrame(rows).set_index("phase")
    # 按直觉排序
    return df.reindex(["spike", "peak", "cooldown"]).dropna(how="all")
