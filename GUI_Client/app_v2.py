"""
文件位置: GUI_Client/app_v2.py
描述: 完整的参数化回测 GUI（集成 BacktestEngine）
功能: 支持自定义回测时间、资金、策略参数，显示关键指标和回测结果
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
import json
import pickle
import subprocess
import tempfile
import time
import yfinance as yf
from pathlib import Path
from datetime import datetime, timedelta, date

# 确保项目根目录在 sys.path 中（必须在导入前执行）
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Strategy_Pool.strategies import STRATEGIES
from Engine_Matrix.backtest_engine import BacktestEngine, BacktestConfig
from Engine_Matrix.advanced_simulator import AdvancedExchangeSimulator, ExchangeConfig
from Analytics.reporters.company_info_manager import CompanyInfoManager
from Analytics.reporters.macro_analyzer import (
    INDEX_MAP, RATE_MAP,
    fetch_index_data, get_margin_debt_series, compute_yoy_change,
    align_and_resample_monthly, compute_correlation_matrix,
    compute_rolling_correlation, detect_divergence_points, compute_lead_lag,
    detect_vix_spikes, classify_vix_phase,
    compute_vix_entry_signals, compute_phase_forward_returns,
    VIX_SPIKE_THRESHOLD, VIX_PEAK_THRESHOLD,
    MACRO_INDICATORS_MAP, fetch_multi_indicators,
)

# =========== 页面配置 ===========
st.set_page_config(page_title="Personal Quant Lab", layout="wide")
st.title("🔬 个人量化实验室 | Personal Quant Lab - Parameterized Backtest System")

# =========== 自动数据更新检查 ===========
from Analytics.reporters.macro_analyzer import should_update_data, set_data_update_date, get_us_eastern_date
if should_update_data():
    st.info(f"⏳ 检测到新的一天（{get_us_eastern_date()}），正在自动刷新所有数据...")
    # 标记force_refresh为True，这样会刷新所有缓存数据
    st.session_state['auto_refresh_all'] = True
    set_data_update_date()
else:
    st.session_state['auto_refresh_all'] = False

# =========== 记忆系统（保存最好的策略配置） ===========
memory_file = os.path.join(os.path.dirname(__file__), '..', 'Data_Hub', 'storage', '.strategy_memory.json')
vix_strategy_file = os.path.join(os.path.dirname(__file__), '..', 'Data_Hub', 'storage', '.vix_strategy_memory.json')


def load_json_store(file_path):
    """加载通用 JSON 存储"""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_json_store(file_path, payload):
    """保存通用 JSON 存储"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

def load_memory():
    """加载策略记忆"""
    return load_json_store(memory_file)

def save_memory(memory):
    """保存策略记忆"""
    save_json_store(memory_file, memory)

def update_best_strategy(symbol, strategy_name, params, annual_return):
    """更新某个标的的最好策略记录"""
    memory = load_memory()
    
    if symbol not in memory:
        memory[symbol] = {
            'strategy': strategy_name,
            'params': params,
            'annual_return': annual_return,
            'updated_at': datetime.now().isoformat()
        }
    else:
        # 只有当年化收益率更高时才更新
        if annual_return > memory[symbol].get('annual_return', -999):
            memory[symbol] = {
                'strategy': strategy_name,
                'params': params,
                'annual_return': annual_return,
                'updated_at': datetime.now().isoformat()
            }
    
    save_memory(memory)

def get_best_strategy(symbol):
    """获取某个标的的最好策略"""
    memory = load_memory()
    return memory.get(symbol, None)


def load_vix_strategy_memory():
    """加载 VIX 子界面的已保存结果"""
    data = load_json_store(vix_strategy_file)
    return data if isinstance(data, dict) else {}


def save_vix_strategy_memory(memory):
    """保存 VIX 子界面的结果库"""
    save_json_store(vix_strategy_file, memory)


def save_vix_backtest_result(result_name, payload):
    """保存单个 VIX 回测结果"""
    memory = load_vix_strategy_memory()
    memory[result_name] = payload
    save_vix_strategy_memory(memory)


def ensure_vix_session_defaults():
    """初始化 VIX 子界面的默认参数"""
    defaults = {
        "vix_spike_threshold": int(VIX_SPIKE_THRESHOLD),
        "vix_peak_threshold": int(VIX_PEAK_THRESHOLD),
        "vix_pullback_pct": 10,
        "vix_confirmation_days": 1,
        "vix_min_spike_duration": 0,
        "vix_min_peak_vix": int(VIX_PEAK_THRESHOLD),
        "vix_fwd": "21日",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_corr_pair_extremes(corr_matrix: pd.DataFrame):
    """提取相关性矩阵上三角中的极值及其对应标的对"""
    if corr_matrix is None or corr_matrix.empty or corr_matrix.shape[0] < 2:
        return None

    upper_triangle = corr_matrix.where(
        np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
    ).stack()
    if upper_triangle.empty:
        return None

    min_pair = upper_triangle.idxmin()
    max_pair = upper_triangle.idxmax()
    return {
        "average": float(upper_triangle.mean()),
        "max_value": float(upper_triangle.loc[max_pair]),
        "max_pair": max_pair,
        "min_value": float(upper_triangle.loc[min_pair]),
        "min_pair": min_pair,
    }


def build_vix_trade_plan(asset_label, params, signal_summary, best_phase_label=None):
    """生成可直接阅读的 VIX 交易战略摘要"""
    lines = [
        f"交易对象：{asset_label}",
        f"观察条件：VIX > {params['spike_threshold']:.0f} 进入高波动观察区。",
        f"峰值条件：VIX > {params['peak_threshold']:.0f} 视为极端恐慌。",
        (
            f"入场条件：VIX 从本轮峰值回落至少 {params['pullback_pct']}%，"
            f"并连续 {params['confirmation_days']} 个交易日确认后入场。"
        ),
        (
            f"样本过滤：事件至少持续 {params['min_spike_duration']} 天，"
            f"峰值 VIX 至少达到 {params['min_peak_vix']:.0f}。"
        ),
        f"持有计划：信号触发后持有 {params['forward_window_label']}（约 {params['forward_days']} 个交易日）。",
    ]

    if best_phase_label:
        lines.append(f"阶段偏好：当前参数下历史均值最优阶段为 {best_phase_label}。")

    if signal_summary.get("sample_count", 0) > 0:
        lines.append(
            f"历史统计：样本 {signal_summary['sample_count']} 次，"
            f"平均收益 {signal_summary['avg_return']:.2f}%，"
            f"胜率 {signal_summary['win_rate']:.1f}%。"
        )
        lines.append(
            f"尾部风险：该持有窗口历史最差单次结果为 {signal_summary['worst_return']:.2f}%。"
        )
    else:
        lines.append("历史统计：当前筛选条件下暂无足够样本，建议放宽过滤条件后再评估。")

    return "\n".join(lines)

# =========== 数据索引 ===========
storage_dir = os.path.join(os.path.dirname(__file__), '..', 'Data_Hub', 'storage')
try:
    available_files = [f for f in os.listdir(storage_dir) if f.endswith('.parquet')]
    available_symbols = sorted([f.split('.')[0] for f in available_files])
except FileNotFoundError:
    st.error("❌ 未找到存储目录，请确保已运行 main.py 下载数据。")
    st.stop()

# =========== 侧边栏：模式切换 ===========
st.sidebar.markdown("### 🧭 功能模式")
app_mode = st.sidebar.radio(
    "",
    ["📈 回测分析", "🌐 宏观分析"],
    key="app_mode",
    horizontal=False,
)
st.sidebar.divider()

# =========== 宏观分析面板 ===========
if app_mode == "🌐 宏观分析":
    # ---- 侧边栏控件（宏观模式） ----
    st.sidebar.header("🌐 宏观分析设置")

    # 全局指标选择（所有Tab共用）
    all_indicators = sorted(list(MACRO_INDICATORS_MAP.keys()) + ["FINRA 融资余额"])
    default_indicators = ["S&P 500", "NASDAQ 100", "VIX (恐慌指数)", "10Y美债收益率", "黄金(GLD)", "FINRA 融资余额"]
    default_selected = [i for i in default_indicators if i in all_indicators]
    
    st.sidebar.markdown("##### 📊 全局指标选择（所有分析Tab通用）")
    global_indicators = st.sidebar.multiselect(
        "选择用于所有分析的指标",
        all_indicators,
        default=default_selected,
        key="global_macro_indicators",
    )
    
    st.sidebar.divider()

    all_index_labels = list(INDEX_MAP.keys())
    all_rate_labels  = list(RATE_MAP.keys())
    selected_indices = st.sidebar.multiselect(
        "选择大盘指数",
        all_index_labels,
        default=["S&P 500", "NASDAQ 100", "NASDAQ Composite", "Dow Jones"],
        key="macro_indices",
    )
    selected_rates = st.sidebar.multiselect(
        "选择利率/汇率",
        all_rate_labels,
        default=["10Y国债收益率"],
        key="macro_rates",
    )
    macro_period = st.sidebar.selectbox(
        "历史数据周期",
        ["3y", "5y", "10y", "15y", "20y", "max"],
        index=2,
        key="macro_period",
    )
    rolling_window = st.sidebar.slider(
        "滚动相关窗口（月）",
        min_value=3, max_value=24, value=12, step=1,
        key="macro_rolling",
    )
    lag_max = st.sidebar.slider(
        "领先/滞后检测范围（月）",
        min_value=1, max_value=12, value=6, step=1,
        key="macro_lag",
    )
    show_margin_debt = st.sidebar.checkbox("显示 FINRA 融资余额", value=True, key="macro_margin")
    force_refresh_macro = st.sidebar.button("🔄 刷新数据", key="macro_refresh")
    
    # 如果系统检测到新的一天，自动刷新
    if st.session_state.get('auto_refresh_all', False):
        force_refresh_macro = True

    # ---- 主区域 ----
    st.title("🌐 宏观市场分析 | Macro Market Analysis")
    st.caption("数据源：Yahoo Finance（大盘指数/利率）+ FINRA（融资余额：内置2002-2024年关键节点）")

    if not selected_indices and not selected_rates:
        st.warning("请在左侧至少选择一个大盘指数或利率指标。")
        st.stop()

    tickers_to_fetch = [INDEX_MAP[l] for l in selected_indices] + [RATE_MAP[l] for l in selected_rates]
    ticker_label_map = {**{v: k for k, v in INDEX_MAP.items()}, **{v: k for k, v in RATE_MAP.items()}}

    with st.spinner("⏳ 正在加载宏观数据…"):
        raw_data = fetch_index_data(tickers_to_fetch, period=macro_period, force_refresh=force_refresh_macro)

    if not raw_data:
        st.error("❌ 数据加载失败，请检查网络连接或稍后重试。")
        st.stop()

    monthly_df = align_and_resample_monthly(raw_data)
    monthly_df.columns = [ticker_label_map.get(c, c) for c in monthly_df.columns]
    monthly_norm = monthly_df.div(monthly_df.iloc[0]) * 100

    # Tab 布局
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 大盘走势",
        "📉 融资余额 (Margin Debt)",
        "🔗 相关性矩阵",
        "⏱ 领先/滞后分析",
        "⚡ 差异性拐点",
        "🚨 VIX 入场策略",
    ])

    # ------------------------------------------------------------------
    # Tab 1：大盘走势（归一化 & 绝对价格）
    # ------------------------------------------------------------------
    with tab1:
        st.subheader("大盘指数走势（月度收盘，基期=100归一化）")

        if monthly_norm.empty:
            st.warning("无可用数据。")
        else:
            fig_norm = go.Figure()
            for col in monthly_norm.columns:
                fig_norm.add_trace(go.Scatter(
                    x=monthly_norm.index, y=monthly_norm[col],
                    mode="lines", name=col,
                ))
            fig_norm.update_layout(
                template="plotly_dark", height=480,
                hovermode="x unified",
                yaxis_title="归一化指数（基期=100）",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_norm, width="stretch")

            st.subheader("年化收益率对比（基于月度收盘价）")
            pct_change = monthly_df.pct_change().dropna()
            annual_returns = (((1 + pct_change).prod()) ** (12 / len(pct_change)) - 1) * 100
            fig_bar = go.Figure(go.Bar(
                x=annual_returns.index,
                y=annual_returns.values.round(2),
                marker_color=["green" if v >= 0 else "red" for v in annual_returns.values],
                text=[f"{v:.1f}%" for v in annual_returns.values],
                textposition="outside",
            ))
            fig_bar.update_layout(
                template="plotly_dark", height=350,
                yaxis_title="年化收益率 (%)",
                showlegend=False,
            )
            st.plotly_chart(fig_bar, width="stretch")

            with st.expander("📋 月度收盘数据", expanded=False):
                st.dataframe(
                    monthly_df.tail(36).sort_index(ascending=False).style.format("{:.2f}"),
                    height=350,
                )

    # ------------------------------------------------------------------
    # Tab 2：FINRA 融资余额
    # ------------------------------------------------------------------
    with tab2:
        st.subheader("FINRA Margin Debt — 美股整体融资余额")
        st.caption(
            "融资余额与大盘呈顺周期性：牛市加速阶段往往伴随抛物线式飙升；"
            "同比增速见顶回落是大型顶部结构的左侧预警信号；"
            "急剧去杠杆（Margin Call 连环平仓）是暴跌最陡峭阶段的核心催化剂。"
        )

        margin_series = get_margin_debt_series()
        yoy_series    = compute_yoy_change(margin_series)

        fig_md = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            subplot_titles=("融资余额（百万美元）", "同比变化率 YoY (%)"),
            vertical_spacing=0.12,
        )
        fig_md.add_trace(
            go.Scatter(x=margin_series.index, y=margin_series.values,
                       mode="lines+markers", name="Margin Debt",
                       line=dict(color="#EF6C00", width=2)),
            row=1, col=1,
        )
        # 叠加 SP500（若已选择）
        sp500_ticker = INDEX_MAP.get("S&P 500", "^GSPC")
        if sp500_ticker in raw_data:
            sp_monthly = raw_data[sp500_ticker]["close"].resample("ME").last()
            sp_norm = sp_monthly / sp_monthly.iloc[0] * margin_series.iloc[0]
            fig_md.add_trace(
                go.Scatter(x=sp_norm.index, y=sp_norm.values,
                           mode="lines", name="S&P 500（叠加，左轴等比）",
                           line=dict(color="#42A5F5", width=1.5, dash="dash")),
                row=1, col=1,
            )

        yoy_clean = yoy_series.dropna()
        colors_yoy = ["green" if v >= 0 else "red" for v in yoy_clean.values]
        fig_md.add_trace(
            go.Bar(x=yoy_clean.index, y=yoy_clean.values,
                   name="YoY %", marker_color=colors_yoy),
            row=2, col=1,
        )
        # 高风险区域参考线
        fig_md.add_hline(y=30, row=2, col=1,
                         line=dict(color="red", dash="dot"), annotation_text="高风险阈值 30%")
        fig_md.add_hline(y=-20, row=2, col=1,
                         line=dict(color="#66BB6A", dash="dot"), annotation_text="去杠杆区域 -20%")

        fig_md.update_layout(template="plotly_dark", height=600, hovermode="x unified")
        st.plotly_chart(fig_md, width="stretch")

        st.subheader("当前市场风险状态判断")
        latest_yoy = yoy_clean.dropna().iloc[-1] if not yoy_clean.empty else 0
        latest_debt = margin_series.iloc[-1]
        debt_90th = margin_series.quantile(0.90)
        if latest_yoy > 30 and latest_debt > debt_90th:
            st.error("🔴 **高风险状态**：融资余额同比 > 30% 且处于历史90分位以上，建议降低仓位/配置对冲。")
        elif latest_yoy < -20:
            st.success("🟢 **去杠杆后修复期**：融资余额同比降幅 > 20%，历史上对应底部区域，可关注反弹机会。")
        else:
            st.info(f"🟡 **中性状态**：融资余额同比 {latest_yoy:.1f}%，绝对值 ${latest_debt:,.0f}M，暂无极端信号。")

        with st.expander("📋 原始数据", expanded=False):
            df_md_display = pd.DataFrame({"Margin Debt (M USD)": margin_series, "YoY %": yoy_series.round(2)})
            st.dataframe(df_md_display.sort_index(ascending=False), height=350)

    # ------------------------------------------------------------------
    # Tab 3：n×n 相关性矩阵（灵活多指标）
    # ------------------------------------------------------------------
    with tab3:
        st.subheader("n×n 宏观指标相关性矩阵")
        st.caption(
            "选择任意数量的宏观指标（股票、债券、商品、汇率等），自动计算月度收益率的相关性矩阵。"
            "支持 25+ 常用指标、FINRA 融资余额、以及 Term Spread(10Y-2Y)。"
        )

        # ---- 侧边栏：指标多选 ----
        st.sidebar.markdown("##### 🔗 相关性矩阵指标选择")
        all_indicators = sorted(list(MACRO_INDICATORS_MAP.keys()) + ["FINRA 融资余额", "Term Spread(10Y-2Y)"])
        
        # 默认选中的指标
        default_indicators = [
            "S&P 500", "NASDAQ 100", "VIX (恐慌指数)", 
            "10Y美债收益率", "黄金(GLD)", "FINRA 融资余额"
        ]
        default_selected = [i for i in default_indicators if i in all_indicators]
        
        selected_corr_indicators = st.sidebar.multiselect(
            "选择指标（可选任意组合）",
            all_indicators,
            default=default_selected,
            key="corr_indicators",
        )

        if not selected_corr_indicators or len(selected_corr_indicators) < 2:
            st.warning("请选择至少 2 个指标以计算相关性矩阵。")
        else:
            # ---- 获取数据 ----
            with st.spinner(f"⏳ 正在加载 {len(selected_corr_indicators)} 个指标的数据..."):
                try:
                    corr_data = fetch_multi_indicators(
                        selected_corr_indicators,
                        period=macro_period,
                        force_refresh=force_refresh_macro,
                        daily_to_monthly=True,
                    )
                except Exception as e:
                    st.error(f"❌ 数据加载失败: {e}")
                    corr_data = None

            if corr_data is None or corr_data.empty:
                st.error("❌ 无法加载选定指标的数据，请检查网络连接或指标代码。")
            elif corr_data.shape[0] < 2:
                st.warning("⚠️ 数据不足（少于 2 个月份），无法计算相关性。")
            else:
                # ---- 相关系数方法选择 ----
                corr_method = st.radio(
                    "相关系数方法",
                    ["pearson", "spearman", "kendall"],
                    index=0, horizontal=True, key="corr_matrix_method"
                )

                # ---- 计算相关性矩阵 ----
                corr_matrix = compute_correlation_matrix(corr_data, method=corr_method)

                # ---- 显示热力图 ----
                st.markdown(f"##### {corr_method.capitalize()} 相关系数矩阵（{len(selected_corr_indicators)}×{len(selected_corr_indicators)}）")
                
                import plotly.express as px
                fig_heatmap = px.imshow(
                    corr_matrix,
                    text_auto=".2f",
                    color_continuous_scale="RdBu_r",
                    zmin=-1, zmax=1,
                    labels=dict(color="相关系数"),
                    title=f"{corr_method.capitalize()} 相关系数矩阵（基于月度收益率）",
                    aspect="auto",
                )
                fig_heatmap.update_layout(
                    template="plotly_dark",
                    height=max(400, 50 * len(selected_corr_indicators)),
                    width=None,
                    xaxis_tickangle=-45,
                )
                st.plotly_chart(fig_heatmap, width="stretch")

                # ---- 相关性统计摘要 ----
                st.markdown("##### 📊 相关性统计摘要")
                corr_summary = get_corr_pair_extremes(corr_matrix)
                col_stats1, col_stats2, col_stats3 = st.columns(3)
                if corr_summary is None:
                    with col_stats1:
                        st.metric("平均相关系数", "N/A")
                    with col_stats2:
                        st.metric("最大相关系数", "N/A")
                    with col_stats3:
                        st.metric("最小相关系数", "N/A")
                else:
                    with col_stats1:
                        st.metric("平均相关系数", f"{corr_summary['average']:.3f}")
                    with col_stats2:
                        st.metric("最大相关系数", f"{corr_summary['max_value']:.3f}")
                        st.caption(f"对应标的：{corr_summary['max_pair'][0]} ↔ {corr_summary['max_pair'][1]}")
                    with col_stats3:
                        st.metric("最小相关系数", f"{corr_summary['min_value']:.3f}")
                        st.caption(f"对应标的：{corr_summary['min_pair'][0]} ↔ {corr_summary['min_pair'][1]}")

                # ---- 两两滚动相关性深度分析 ----
                st.markdown("##### 🔍 两两指标：滚动相关性深度分析")
                if len(selected_corr_indicators) >= 2:
                    rc_col1, rc_col2 = st.columns(2)
                    with rc_col1:
                        roll_a = st.selectbox("指标 A", selected_corr_indicators, index=0, key="roll_a_flex")
                    with rc_col2:
                        roll_b = st.selectbox(
                            "指标 B",
                            selected_corr_indicators,
                            index=min(1, len(selected_corr_indicators) - 1),
                            key="roll_b_flex"
                        )

                    if roll_a != roll_b and roll_a in corr_data.columns and roll_b in corr_data.columns:
                        rc_series = compute_rolling_correlation(
                            corr_data[roll_a], corr_data[roll_b], window=rolling_window
                        )
                        if not rc_series.empty:
                            fig_rc = go.Figure()
                            fig_rc.add_trace(go.Scatter(
                                x=rc_series.index, y=rc_series.values,
                                mode="lines", name=f"滚动相关（{rolling_window}月）",
                                line=dict(color="#AB47BC", width=2),
                            ))
                            fig_rc.add_hline(y=0, line=dict(color="gray", dash="dot"))
                            fig_rc.add_hline(y=0.7, line=dict(color="#66BB6A", dash="dot"),
                                             annotation_text="强正相关 0.7")
                            fig_rc.add_hline(y=-0.7, line=dict(color="#EF5350", dash="dot"),
                                             annotation_text="强负相关 -0.7")
                            fig_rc.update_layout(
                                template="plotly_dark", height=380,
                                yaxis_title="相关系数", hovermode="x unified",
                                title=f"{roll_a} vs {roll_b} — 滚动{rolling_window}月相关性演化",
                            )
                            st.plotly_chart(fig_rc, width="stretch")

                # ---- 相关性矩阵数据表 ----
                with st.expander("📋 完整相关系数矩阵数据", expanded=False):
                    st.dataframe(corr_matrix.style.format("{:.4f}").highlight_max(color="lightgreen").highlight_min(color="lightcoral"), height=400)

    # ------------------------------------------------------------------
    # Tab 4：领先/滞后分析
    # ------------------------------------------------------------------
    with tab4:
        st.subheader("领先/滞后相关性分析（月度）")
        st.caption(
            "正 Lag = 指标A领先指标B；负 Lag = 指标A滞后指标B。"
            "峰值对应的 lag 即为两者之间的典型时间差（拐点先后顺序）。"
        )

        # 使用全局指标或传统月度数据
        use_global = st.radio("数据源选择", ["使用全局指标", "使用传统指数/利率"], horizontal=True, key="tab4_data_source")
        
        if use_global == "使用全局指标":
            if not global_indicators or len(global_indicators) < 2:
                st.warning("请先在全局指标选择中至少选择 2 个指标。")
            else:
                with st.spinner("⏳ 加载全局指标数据..."):
                    try:
                        ll_data = fetch_multi_indicators(global_indicators, period=macro_period, force_refresh=force_refresh_macro)
                    except Exception as e:
                        st.error(f"❌ 数据加载失败: {e}")
                        ll_data = None
                
                if ll_data is not None and not ll_data.empty:
                    ll_opts = list(ll_data.columns)
                    llc1, llc2 = st.columns(2)
                    with llc1:
                        ll_a = st.selectbox("指标 A（领先方向）", ll_opts, index=0, key="ll_a_global")
                    with llc2:
                        ll_b = st.selectbox("指标 B", ll_opts,
                                            index=min(1, len(ll_opts)-1), key="ll_b_global")

                    if ll_a != ll_b:
                        ll_df = compute_lead_lag(
                            ll_data[ll_a].dropna(),
                            ll_data[ll_b].dropna(),
                            max_lag=lag_max,
                        )
                        best_lag = ll_df.loc[ll_df["correlation"].abs().idxmax()]

                        fig_ll = go.Figure()
                        fig_ll.add_trace(go.Bar(
                            x=ll_df["lag_months"],
                            y=ll_df["correlation"],
                            marker_color=["#42A5F5" if v >= 0 else "#EF5350"
                                          for v in ll_df["correlation"].fillna(0)],
                            name="相关系数",
                        ))
                        fig_ll.update_layout(
                            template="plotly_dark", height=380,
                            xaxis_title="领先月数（正=A领先B）",
                            yaxis_title="相关系数",
                            title=f"{ll_a} vs {ll_b} 领先/滞后分析",
                        )
                        st.plotly_chart(fig_ll, width="stretch")

                        lag_val = int(best_lag["lag_months"])
                        corr_val = best_lag["correlation"]
                        if lag_val > 0:
                            st.success(f"📌 **{ll_a}** 领先 **{ll_b}** 约 **{lag_val} 个月**（峰值相关：{corr_val:.3f}）")
                        elif lag_val < 0:
                            st.success(f"📌 **{ll_a}** 滞后 **{ll_b}** 约 **{abs(lag_val)} 个月**（峰值相关：{corr_val:.3f}）")
                        else:
                            st.info(f"📌 **{ll_a}** 与 **{ll_b}** 无显著领先/滞后关系（峰值相关：{corr_val:.3f}，lag=0）")

                        with st.expander("📋 详细数据", expanded=False):
                            st.dataframe(ll_df.set_index("lag_months").style.format("{:.4f}"))
        
        else:  # 使用传统数据
            if monthly_df.shape[1] < 2:
                st.info("请选择至少 2 个指标。")
            else:
                ll_opts = list(monthly_df.columns)
                llc1, llc2 = st.columns(2)
                with llc1:
                    ll_a = st.selectbox("指标 A（领先方向）", ll_opts, index=0, key="ll_a")
                with llc2:
                    ll_b = st.selectbox("指标 B", ll_opts,
                                        index=min(1, len(ll_opts)-1), key="ll_b")

                if ll_a != ll_b:
                    ll_df = compute_lead_lag(
                        monthly_df[ll_a].resample("ME").last().dropna(),
                        monthly_df[ll_b].resample("ME").last().dropna(),
                        max_lag=lag_max,
                    )
                    best_lag = ll_df.loc[ll_df["correlation"].abs().idxmax()]

                    fig_ll = go.Figure()
                    fig_ll.add_trace(go.Bar(
                        x=ll_df["lag_months"],
                        y=ll_df["correlation"],
                        marker_color=["#42A5F5" if v >= 0 else "#EF5350"
                                      for v in ll_df["correlation"].fillna(0)],
                        name="相关系数",
                    ))
                    fig_ll.update_layout(
                        template="plotly_dark", height=380,
                        xaxis_title="领先月数（正=A领先B）",
                        yaxis_title="相关系数",
                        title=f"{ll_a} vs {ll_b} 领先/滞后分析",
                    )
                    st.plotly_chart(fig_ll, width="stretch")

                    lag_val = int(best_lag["lag_months"])
                    corr_val = best_lag["correlation"]
                    if lag_val > 0:
                        st.success(f"📌 **{ll_a}** 领先 **{ll_b}** 约 **{lag_val} 个月**（峰值相关：{corr_val:.3f}）")
                    elif lag_val < 0:
                        st.success(f"📌 **{ll_a}** 滞后 **{ll_b}** 约 **{abs(lag_val)} 个月**（峰值相关：{corr_val:.3f}）")
                    else:
                        st.info(f"📌 **{ll_a}** 与 **{ll_b}** 无显著领先/滞后关系（峰值相关：{corr_val:.3f}，lag=0）")

                    with st.expander("📋 详细数据", expanded=False):
                        st.dataframe(ll_df.set_index("lag_months").style.format("{:.4f}"))

    # ------------------------------------------------------------------
    # Tab 5：差异性拐点
    # ------------------------------------------------------------------
    with tab5:
        st.subheader("差异性拐点检测")
        st.caption(
            "当两个指标在同一时间窗口内运动方向相反时，视为一次差异性拐点。"
            "这些节点往往对应市场风格切换、风险偏好逆转或宏观政策转折。"
        )

        # 使用全局指标或传统月度数据
        use_global_div = st.radio("数据源选择", ["使用全局指标", "使用传统指数/利率"], horizontal=True, key="tab5_data_source")
        
        if use_global_div == "使用全局指标":
            if not global_indicators or len(global_indicators) < 2:
                st.warning("请先在全局指标选择中至少选择 2 个指标。")
            else:
                with st.spinner("⏳ 加载全局指标数据..."):
                    try:
                        div_data = fetch_multi_indicators(global_indicators, period=macro_period, force_refresh=force_refresh_macro)
                    except Exception as e:
                        st.error(f"❌ 数据加载失败: {e}")
                        div_data = None
                
                if div_data is not None and not div_data.empty:
                    div_opts = list(div_data.columns)
                    dc1, dc2, dc3 = st.columns(3)
                    with dc1:
                        div_a = st.selectbox("指标 A", div_opts, index=0, key="div_a_global")
                    with dc2:
                        div_b = st.selectbox("指标 B", div_opts,
                                            index=min(1, len(div_opts)-1), key="div_b_global")
                    with dc3:
                        div_win = st.slider("比较窗口（月）", 1, 6, 2, key="div_win_global")

                    if div_a != div_b:
                        div_df = detect_divergence_points(
                            div_data[div_a], div_data[div_b], window=div_win
                        )

                        if div_df.empty:
                            st.info("在选定参数下未检测到差异性拐点。")
                        else:
                            st.markdown(f"**检测到 {len(div_df)} 个差异性拐点：**")

                            fig_div = go.Figure()
                            for col in [div_a, div_b]:
                                norm_col = div_data[col] / div_data[col].iloc[0] * 100
                                fig_div.add_trace(go.Scatter(
                                    x=norm_col.index, y=norm_col.values,
                                    mode="lines", name=col,
                                ))
                            for dt in div_df.index:
                                fig_div.add_vline(
                                    x=dt, line=dict(color="yellow", width=1, dash="dot"),
                                )
                            fig_div.update_layout(
                                template="plotly_dark", height=400,
                                hovermode="x unified",
                                yaxis_title="归一化指数",
                                title=f"{div_a} vs {div_b} 差异性拐点（黄色竖线）",
                            )
                            st.plotly_chart(fig_div, width="stretch")

                            display_df = div_df.copy()
                            display_df["A_chg_pct"] = display_df["A_chg_pct"].apply(lambda x: f"{x:.2f}%")
                            display_df["B_chg_pct"] = display_df["B_chg_pct"].apply(lambda x: f"{x:.2f}%")
                            display_df.columns = [f"{div_a}方向", f"{div_a}变化", f"{div_b}方向", f"{div_b}变化"]
                            st.dataframe(display_df.sort_index(ascending=False), height=350)
        
        else:  # 使用传统数据
            if monthly_df.shape[1] < 2:
                st.info("请选择至少 2 个指标。")
            else:
                div_opts = list(monthly_df.columns)
                dc1, dc2, dc3 = st.columns(3)
                with dc1:
                    div_a = st.selectbox("指标 A", div_opts, index=0, key="div_a")
                with dc2:
                    div_b = st.selectbox("指标 B", div_opts,
                                         index=min(1, len(div_opts)-1), key="div_b")
                with dc3:
                    div_win = st.slider("比较窗口（月）", 1, 6, 2, key="div_win")

                if div_a != div_b:
                    div_df = detect_divergence_points(
                        monthly_df[div_a], monthly_df[div_b], window=div_win
                    )

                    if div_df.empty:
                        st.info("在选定参数下未检测到差异性拐点。")
                    else:
                        st.markdown(f"**检测到 {len(div_df)} 个差异性拐点：**")

                        fig_div = go.Figure()
                        for col in [div_a, div_b]:
                            norm_col = monthly_df[col] if col in monthly_df.columns else monthly_df[col]
                            fig_div.add_trace(go.Scatter(
                                x=norm_col.index, y=norm_col.values,
                                mode="lines", name=col,
                            ))
                        for dt in div_df.index:
                            fig_div.add_vline(
                                x=dt, line=dict(color="yellow", width=1, dash="dot"),
                            )
                        fig_div.update_layout(
                            template="plotly_dark", height=400,
                            hovermode="x unified",
                            yaxis_title="归一化指数",
                            title=f"{div_a} vs {div_b} 差异性拐点（黄色竖线）",
                        )
                        st.plotly_chart(fig_div, width="stretch")

                        display_df = div_df.copy()
                        display_df["A_chg_pct"] = display_df["A_chg_pct"].apply(lambda x: f"{x:.2f}%")
                        display_df["B_chg_pct"] = display_df["B_chg_pct"].apply(lambda x: f"{x:.2f}%")
                        display_df.columns = [f"{div_a}方向", f"{div_a}变化", f"{div_b}方向", f"{div_b}变化"]
                        st.dataframe(display_df.sort_index(ascending=False), height=350)
            with dc3:
                div_win = st.slider("比较窗口（月）", 1, 6, 2, key="div_win")

            if div_a != div_b:
                div_df = detect_divergence_points(
                    monthly_df[div_a], monthly_df[div_b], window=div_win
                )

                if div_df.empty:
                    st.info("在选定参数下未检测到差异性拐点。")
                else:
                    st.markdown(f"**检测到 {len(div_df)} 个差异性拐点：**")

                    # 在走势图上标注拐点
                    fig_div = go.Figure()
                    for col in [div_a, div_b]:
                        norm_col = monthly_norm[col] if col in monthly_norm.columns else monthly_df[col]
                        fig_div.add_trace(go.Scatter(
                            x=norm_col.index, y=norm_col.values,
                            mode="lines", name=col,
                        ))
                    # 标注拐点位置
                    for dt in div_df.index:
                        fig_div.add_vline(
                            x=dt, line=dict(color="yellow", width=1, dash="dot"),
                        )
                    fig_div.update_layout(
                        template="plotly_dark", height=400,
                        hovermode="x unified",
                        yaxis_title="归一化指数",
                        title=f"{div_a} vs {div_b} 差异性拐点（黄色竖线）",
                    )
                    st.plotly_chart(fig_div, width="stretch")

                    display_df = div_df.copy()
                    display_df["A_chg_pct"] = display_df["A_chg_pct"].apply(lambda x: f"{x:.2f}%")
                    display_df["B_chg_pct"] = display_df["B_chg_pct"].apply(lambda x: f"{x:.2f}%")
                    display_df.columns = [f"{div_a}方向", f"{div_a}变化", f"{div_b}方向", f"{div_b}变化"]
                    st.dataframe(display_df.sort_index(ascending=False), height=350)

    # ------------------------------------------------------------------
    # Tab 6：VIX 三阶段入场策略
    # ------------------------------------------------------------------
    with tab6:
        st.subheader("VIX 三阶段入场策略 — 量化逻辑与历史回测")
        st.caption(
            "VIX > 30 时进入高企观察期，分为前期（急速飙升）、中期（极度恐慌峰值）、"
            "后期（均值回归开始）三个阶段。统计显示后期（右侧）入场的胜率与夏普比率远优于前期（左侧）。"
        )

        ensure_vix_session_defaults()
        saved_vix_results = load_vix_strategy_memory()

        with st.expander("🗂️ VIX 回测结果库", expanded=False):
            if saved_vix_results:
                saved_names = sorted(saved_vix_results.keys(), reverse=True)
                selected_saved_name = st.selectbox(
                    "已保存方案",
                    saved_names,
                    key="vix_saved_result_name",
                )
                selected_saved_payload = saved_vix_results.get(selected_saved_name, {})
                selected_saved_summary = selected_saved_payload.get("summary", {})
                if selected_saved_summary:
                    st.caption(
                        f"最近保存：样本 {selected_saved_summary.get('sample_count', 0)} 次，"
                        f"平均收益 {selected_saved_summary.get('avg_return', 'N/A')}%，"
                        f"胜率 {selected_saved_summary.get('win_rate', 'N/A')}%。"
                    )

                if st.button("读取该方案", key="vix_load_result"):
                    params = selected_saved_payload.get("params", {})
                    asset_info = selected_saved_payload.get("asset", {})

                    st.session_state["vix_spike_threshold"] = int(params.get("spike_threshold", VIX_SPIKE_THRESHOLD))
                    st.session_state["vix_peak_threshold"] = int(params.get("peak_threshold", VIX_PEAK_THRESHOLD))
                    st.session_state["vix_pullback_pct"] = int(params.get("pullback_pct", 10))
                    st.session_state["vix_confirmation_days"] = int(params.get("confirmation_days", 1))
                    st.session_state["vix_min_spike_duration"] = int(params.get("min_spike_duration", 0))
                    st.session_state["vix_min_peak_vix"] = int(params.get("min_peak_vix", VIX_PEAK_THRESHOLD))
                    st.session_state["vix_fwd"] = params.get("forward_window_label", "21日")
                    st.session_state["vix_backtest_mode"] = asset_info.get("mode", "宏观指标")

                    saved_asset_label = asset_info.get("label")
                    if asset_info.get("mode") == "宏观指标":
                        if global_indicators and saved_asset_label in global_indicators:
                            st.session_state["vix_backtest_indicator"] = saved_asset_label
                        elif global_indicators:
                            st.session_state["vix_backtest_indicator"] = global_indicators[0]
                    elif saved_asset_label:
                        st.session_state["vix_backtest_custom"] = saved_asset_label

                    st.session_state["vix_loaded_result_notice"] = f"已读取方案：{selected_saved_name}"
                    st.rerun()
            else:
                st.info("当前还没有已保存的 VIX 回测结果。")

        if st.session_state.get("vix_loaded_result_notice"):
            st.success(st.session_state["vix_loaded_result_notice"])
            del st.session_state["vix_loaded_result_notice"]

        if global_indicators and st.session_state.get("vix_backtest_indicator") not in global_indicators:
            st.session_state["vix_backtest_indicator"] = global_indicators[0]

        if st.session_state.get("vix_fwd") not in ["5日", "10日", "21日", "63日"]:
            st.session_state["vix_fwd"] = "21日"

        st.markdown("##### VIX 参数调节")
        param_col1, param_col2, param_col3 = st.columns(3)
        with param_col1:
            vix_spike_threshold = st.slider(
                "Spike 阈值",
                min_value=20,
                max_value=50,
                value=int(st.session_state["vix_spike_threshold"]),
                key="vix_spike_threshold",
                help="VIX 超过该阈值后，系统认为市场进入高波动观察期。",
            )
            vix_pullback_pct = st.slider(
                "从峰值回落幅度(%)",
                min_value=5,
                max_value=30,
                value=int(st.session_state["vix_pullback_pct"]),
                key="vix_pullback_pct",
                help="例如选择 10%，表示 VIX 从本轮峰值回落 10% 后才允许触发后期入场。",
            )
        with param_col2:
            vix_peak_threshold = st.slider(
                "Peak 阈值",
                min_value=max(vix_spike_threshold + 1, 25),
                max_value=80,
                value=max(int(st.session_state["vix_peak_threshold"]), vix_spike_threshold + 1),
                key="vix_peak_threshold",
                help="VIX 超过该阈值后，系统把当前事件视为极端恐慌阶段。",
            )
            vix_confirmation_days = st.slider(
                "回落确认天数",
                min_value=1,
                max_value=5,
                value=int(st.session_state["vix_confirmation_days"]),
                key="vix_confirmation_days",
                help="信号不是只看一天，而是要求连续若干天满足回落条件，减少假突破。",
            )
        with param_col3:
            vix_min_spike_duration = st.slider(
                "最短事件持续天数",
                min_value=0,
                max_value=60,
                value=int(st.session_state["vix_min_spike_duration"]),
                key="vix_min_spike_duration",
                help="过滤掉持续时间过短的 VIX 噪声事件。",
            )
            vix_min_peak_vix = st.slider(
                "最低峰值 VIX 过滤",
                min_value=max(vix_peak_threshold, 30),
                max_value=90,
                value=max(int(st.session_state["vix_min_peak_vix"]), vix_peak_threshold),
                key="vix_min_peak_vix",
                help="只有峰值达到该水平的恐慌事件才计入回测样本。",
            )

        vix_pullback_ratio = 1 - (vix_pullback_pct / 100.0)

        # ---- 阶段说明表 ----
        st.markdown("##### 三阶段定义")
        phase_def = pd.DataFrame([
            {
                "阶段": "🔴 前期 (Spike)",
                "VIX 特征": f"VIX 急升并突破 {vix_spike_threshold}",
                "市场心理": "恐慌爆发，资金踩踏",
                "入场风险": "极高 — 左侧交易，账面浮亏可明显扩大",
            },
            {
                "阶段": "🔥 中期 (Peak)",
                "VIX 特征": f"VIX 继续上冲并超过 {vix_peak_threshold}",
                "市场心理": "极度绝望，强制平仓",
                "入场风险": "高波动/高潜力 — 可能先经历最后一跌",
            },
            {
                "阶段": "🟢 后期 (Cooldown)",
                "VIX 特征": f"VIX 从峰值回落至少 {vix_pullback_pct}% 且连续确认 {vix_confirmation_days} 日",
                "市场心理": "恐慌消退，机构回流",
                "入场风险": "相对最优 — 右侧确认后再参与，风险收益比更清晰",
            },
        ])
        st.dataframe(phase_def.set_index("阶段"), height=145)

        # ---- 获取 VIX 数据 ----
        vix_ticker = "^VIX"
        vix_raw    = fetch_index_data([vix_ticker], period=macro_period, force_refresh=force_refresh_macro)

        if vix_ticker not in vix_raw:
            st.warning("⚠️ 无法加载 VIX 数据，请检查网络连接。")
        else:
            vix_close = vix_raw[vix_ticker]["close"].squeeze()
            
            # ---- 选择回测标的 ----
            st.markdown("##### VIX 入场回测标的选择")
            backtest_asset_mode = st.radio(
                "回测资产类型",
                ["宏观指标", "个股符号"],
                horizontal=True,
                key="vix_backtest_mode"
            )
            
            if backtest_asset_mode == "宏观指标":
                if not global_indicators:
                    st.warning("请先在全局指标选择中至少选择 1 个指标。")
                    backtest_ticker = None
                    backtest_label = None
                else:
                    backtest_label = st.selectbox(
                        "选择宏观指标",
                        global_indicators,
                        index=global_indicators.index(st.session_state.get("vix_backtest_indicator", global_indicators[0])),
                        key="vix_backtest_indicator"
                    )
                    # 获取该指标的数据
                    backtest_data = fetch_multi_indicators([backtest_label], period=macro_period, force_refresh=False)
                    if backtest_data is None or backtest_data.empty:
                        st.error(f"❌ 无法加载 {backtest_label} 数据")
                        backtest_ticker = None
                    else:
                        backtest_ticker = backtest_data[backtest_label].squeeze()
            else:
                # 自定义个股符号
                backtest_label = st.text_input(
                    "输入个股符号（如 AAPL, MSFT）",
                    value="AAPL",
                    key="vix_backtest_custom",
                )
                if backtest_label:
                    try:
                        backtest_data_raw = fetch_index_data([backtest_label], period=macro_period, force_refresh=False)
                        if backtest_label in backtest_data_raw:
                            backtest_ticker = backtest_data_raw[backtest_label]["close"].squeeze()
                        else:
                            st.error(f"❌ 无法获取 {backtest_label} 数据，请检查符号是否正确")
                            backtest_ticker = None
                    except Exception as e:
                        st.error(f"❌ 获取 {backtest_label} 数据失败: {e}")
                        backtest_ticker = None
                else:
                    backtest_ticker = None
            
            # 也获取S&P 500作为默认对比
            sp_ticker  = "^GSPC"
            sp_raw     = fetch_index_data([sp_ticker],  period=macro_period, force_refresh=False)
            sp_close   = sp_raw[sp_ticker]["close"].squeeze() if sp_ticker in sp_raw else None

            # 校验回测数据并决定使用哪个价格序列
            if sp_close is None:
                st.warning("⚠️ 无法加载 S&P 500 数据，后续分析将被跳过。")
                st.stop()
            else:
                # 选择用于计算的价格序列：优先使用选定的回测标的，否则用S&P 500
                if backtest_ticker is not None and not backtest_ticker.empty:
                    price_for_calc = backtest_ticker
                    asset_label_for_display = backtest_label
                else:
                    price_for_calc = sp_close
                    asset_label_for_display = "S&P 500"
                    if backtest_ticker is None:
                        if backtest_asset_mode == "宏观指标":
                            st.info("🟡 未能加载选定的宏观指标，正使用 S&P 500 替代回测...")
                        else:
                            st.info(f"🟡 未能加载 {backtest_label}，正使用 S&P 500 替代回测...")

            phase_series = classify_vix_phase(
                vix_close,
                spike_threshold=vix_spike_threshold,
                peak_threshold=vix_peak_threshold,
                pullback_ratio=vix_pullback_ratio,
            )

            fig_vix = go.Figure()
            # 背景色块：spike=橙, peak=红, cooldown=绿
            phase_colors = {"spike": "rgba(255,165,0,0.15)", "peak": "rgba(220,50,50,0.20)", "cooldown": "rgba(50,200,80,0.15)"}
            # 按连续段生成矩形
            prev_ph, seg_start = None, None
            for dt, ph in phase_series.items():
                if ph != prev_ph:
                    if prev_ph and prev_ph != "normal" and seg_start is not None:
                        fig_vix.add_vrect(
                            x0=seg_start, x1=dt,
                            fillcolor=phase_colors.get(prev_ph, "rgba(0,0,0,0)"),
                            opacity=1, layer="below", line_width=0,
                        )
                    seg_start = dt
                    prev_ph = ph
            # 补最后一段
            if prev_ph and prev_ph != "normal" and seg_start is not None:
                fig_vix.add_vrect(
                    x0=seg_start, x1=vix_close.index[-1],
                    fillcolor=phase_colors.get(prev_ph, "rgba(0,0,0,0)"),
                    opacity=1, layer="below", line_width=0,
                )

            fig_vix.add_trace(go.Scatter(
                x=vix_close.index, y=vix_close.values,
                mode="lines", name="VIX",
                line=dict(color="#EF5350", width=1.5),
            ))
            fig_vix.add_hline(y=vix_spike_threshold, line=dict(color="orange", dash="dot"),
                              annotation_text=f"警戒线 {vix_spike_threshold}")
            fig_vix.add_hline(y=vix_peak_threshold,  line=dict(color="red",    dash="dot"),
                              annotation_text=f"极度恐慌 {vix_peak_threshold}")
            fig_vix.update_layout(
                template="plotly_dark", height=380,
                yaxis_title="VIX", hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_vix, width="stretch")

            # ---- 当前状态判断 ----
            latest_vix = vix_close.iloc[-1]
            latest_phase = phase_series.iloc[-1]

            # 找本轮高点（若处于 spike/peak）
            spikes_df = detect_vix_spikes(
                vix_close,
                spike_threshold=vix_spike_threshold,
                peak_threshold=vix_peak_threshold,
                cooldown_threshold=vix_spike_threshold,
            )
            current_spike_peak = None
            if not spikes_df.empty:
                last_spike = spikes_df.iloc[-1]
                if last_spike["end"] is None:  # 还在进行中
                    current_spike_peak = last_spike["peak_value"]

            st.markdown("##### 当前市场状态")
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.metric("当前 VIX", f"{latest_vix:.2f}",
                          delta=f"{latest_vix - vix_close.iloc[-2]:.2f}" if len(vix_close) > 1 else None)
            with col_s2:
                phase_label = {"normal": "🟦 正常", "spike": "🔴 前期(飙升)", "peak": "🔥 中期(峰值)", "cooldown": "🟢 后期(回落)"}
                st.metric("当前阶段", phase_label.get(latest_phase, latest_phase))
            with col_s3:
                if current_spike_peak:
                    trigger_level = current_spike_peak * vix_pullback_ratio
                    st.metric("后期信号触发点", f"VIX ≤ {trigger_level:.1f}",
                              help=f"本轮VIX峰值 {current_spike_peak:.1f} × {vix_pullback_ratio:.2f}")
                else:
                    st.metric("后期信号触发点", "N/A — 当前无活跃spike")

            if latest_phase == "cooldown":
                st.success("✅ **当前处于后期（Cooldown）阶段** — VIX 正在均值回归，历史数据显示此为系统性风险消退阶段，个股 Alpha 逐步恢复有效性。")
            elif latest_phase == "peak":
                st.error(f"🔥 **当前处于中期（Peak）阶段** — 极度恐慌区，Beta 主导一切。建议等待 VIX 从峰值回落至少 {vix_pullback_pct}% 后再考虑入场。")
            elif latest_phase == "spike":
                st.warning("⚠️ **当前处于前期（Spike）阶段** — VIX 正在飙升，系统性抛压最强，左侧入场需承受最大账面浮亏。")
            else:
                st.info("🟦 **当前 VIX 处于正常区间** — 系统性风险低，个股逻辑正常有效。")

            # ---- 历史入场信号表 ----
            st.markdown(f"##### 历史后期（Cooldown）入场信号 — {asset_label_for_display} 前瞻收益统计")
            with st.expander("ℹ️ 前瞻窗口定义", expanded=False):
                st.markdown(
                    """
前瞻窗口 = 从某一次入场信号触发当天开始，向后观察固定数量的交易日，并统计这段时间的收益表现。

- 5日：偏短线反弹验证，适合看恐慌后的快速修复。
- 10日：偏两周节奏，适合观察情绪修复是否延续。
- 21日：约 1 个月持有周期，适合中短线波段。
- 63日：约 1 个季度持有周期，适合验证更完整的风险偏好修复。

计算方式：

$$\text{前瞻收益} = \left(\frac{\text{未来价格}}{\text{入场价格}} - 1\right) \times 100\%$$
                    """
                )
            fwd_days_choice = st.radio(
                "前瞻窗口", ["5日", "10日", "21日", "63日"],
                index=["5日", "10日", "21日", "63日"].index(st.session_state["vix_fwd"]),
                horizontal=True,
                key="vix_fwd",
            )
            fwd_map = {"5日": 5, "10日": 10, "21日": 21, "63日": 63}
            fwd_d = fwd_map[fwd_days_choice]

            signals_df = compute_vix_entry_signals(
                vix_close, price_for_calc,
                spike_threshold=vix_spike_threshold,
                peak_threshold=vix_peak_threshold,
                pullback_ratio=vix_pullback_ratio,
                forward_windows=[5, 10, 21, 63],
                cooldown_confirmation_days=vix_confirmation_days,
                min_spike_duration_days=vix_min_spike_duration,
                min_peak_vix=vix_min_peak_vix,
            )

            signal_summary = {
                "sample_count": 0,
                "avg_return": None,
                "win_rate": None,
                "best_return": None,
                "worst_return": None,
            }

            if signals_df.empty:
                st.info("当前周期内无入场信号。")
            else:
                fwd_col = f"fwd_{fwd_d}d_return"
                display_sig = signals_df[[
                    "spike_start", "peak_date", "peak_vix",
                    "signal_date", "signal_vix", "entry_price", fwd_col
                ]].copy()
                display_sig.columns = [
                    "Spike开始", "VIX峰值日", "峰值VIX",
                    "入场信号日", "信号日VIX", f"{asset_label_for_display}入场价", f"{fwd_days_choice}前瞻收益(%)"
                ]
                ret_col = f"{fwd_days_choice}前瞻收益(%)"

                def _color_ret(val):
                    if val is None or (isinstance(val, float) and pd.isna(val)):
                        return ""
                    return "color: #66BB6A" if val > 0 else "color: #EF5350"

                styled = display_sig.style.applymap(_color_ret, subset=[ret_col])
                st.dataframe(styled, height=280)

                # 胜率摘要
                valid_rets = signals_df[fwd_col].dropna()
                if not valid_rets.empty:
                    win_rate = (valid_rets > 0).mean() * 100
                    avg_ret  = valid_rets.mean()
                    best_ret = valid_rets.max()
                    worst_ret = valid_rets.min()
                    signal_summary = {
                        "sample_count": int(len(valid_rets)),
                        "avg_return": float(avg_ret),
                        "win_rate": float(win_rate),
                        "best_return": float(best_ret),
                        "worst_return": float(worst_ret),
                    }

                    sc1, sc2, sc3, sc4 = st.columns(4)
                    sc1.metric(f"后期信号次数", len(valid_rets))
                    sc2.metric(f"{fwd_days_choice}平均收益", f"{avg_ret:.1f}%",
                               delta="正" if avg_ret > 0 else "负")
                    sc3.metric("胜率", f"{win_rate:.0f}%")
                    sc4.metric("最差单次结果", f"{worst_ret:.1f}%")

                    window_snapshot_rows = []
                    for win_label, win_days in fwd_map.items():
                        win_col = f"fwd_{win_days}d_return"
                        win_rets = signals_df[win_col].dropna()
                        window_snapshot_rows.append({
                            "持有窗口": win_label,
                            "样本数": int(len(win_rets)),
                            "平均收益(%)": round(win_rets.mean(), 2) if not win_rets.empty else None,
                            "胜率(%)": round((win_rets > 0).mean() * 100, 1) if not win_rets.empty else None,
                            "最佳结果(%)": round(win_rets.max(), 2) if not win_rets.empty else None,
                            "最差结果(%)": round(win_rets.min(), 2) if not win_rets.empty else None,
                        })

                    st.markdown("##### 不同持有窗口表现快照")
                    window_snapshot_df = pd.DataFrame(window_snapshot_rows)
                    st.dataframe(
                        window_snapshot_df.style.format(
                            {
                                "平均收益(%)": "{:.2f}",
                                "胜率(%)": "{:.1f}",
                                "最佳结果(%)": "{:.2f}",
                                "最差结果(%)": "{:.2f}",
                            }
                        ),
                        height=220,
                    )

            # ---- 三阶段收益对比 ----
            st.markdown("##### 三阶段买入的统计对比")
            phase_fwd_df = compute_phase_forward_returns(
                vix_close, price_for_calc,
                spike_threshold=vix_spike_threshold,
                peak_threshold=vix_peak_threshold,
                pullback_ratio=vix_pullback_ratio,
                forward_days=fwd_d,
            )
            best_phase_label = None
            if not phase_fwd_df.empty:
                phase_fwd_display = phase_fwd_df.copy()
                phase_fwd_display.index = [
                    {"spike": "🔴 前期 Spike", "peak": "🔥 中期 Peak", "cooldown": "🟢 后期 Cooldown"}.get(i, i)
                    for i in phase_fwd_display.index
                ]
                phase_fwd_display.columns = ["样本数", f"{fwd_days_choice}均值收益(%)", "胜率(%)", "最大亏损(%)"]
                valid_phase_returns = phase_fwd_df["mean_return"].dropna()
                if not valid_phase_returns.empty:
                    best_phase_key = valid_phase_returns.idxmax()
                    best_phase_label = {
                        "spike": "🔴 前期 Spike",
                        "peak": "🔥 中期 Peak",
                        "cooldown": "🟢 后期 Cooldown",
                    }.get(best_phase_key, best_phase_key)

                fig_phase = go.Figure()
                phases_ordered = ["🔴 前期 Spike", "🔥 中期 Peak", "🟢 后期 Cooldown"]
                phase_bar_colors = ["#EF5350", "#FF7043", "#66BB6A"]
                for ph, color in zip(phases_ordered, phase_bar_colors):
                    if ph in phase_fwd_display.index:
                        val = phase_fwd_display.loc[ph, f"{fwd_days_choice}均值收益(%)"]
                        fig_phase.add_trace(go.Bar(
                            name=ph, x=[ph], y=[val],
                            marker_color=color,
                            text=[f"{val:.1f}%"], textposition="outside",
                        ))
                fig_phase.add_hline(y=0, line=dict(color="gray", dash="dot"))
                fig_phase.update_layout(
                    template="plotly_dark", height=320,
                    yaxis_title=f"{fwd_days_choice}前瞻均值收益 (%)",
                    showlegend=False,
                    title=f"VIX 三阶段：{asset_label_for_display} 买入后 {fwd_days_choice} 均值收益对比",
                )
                st.plotly_chart(fig_phase, width="stretch")
                st.dataframe(phase_fwd_display.style.format(
                    {f"{fwd_days_choice}均值收益(%)": "{:.2f}", "胜率(%)": "{:.1f}", "最大亏损(%)": "{:.2f}"}
                ), height=160)

            strategy_params = {
                "spike_threshold": float(vix_spike_threshold),
                "peak_threshold": float(vix_peak_threshold),
                "pullback_pct": int(vix_pullback_pct),
                "confirmation_days": int(vix_confirmation_days),
                "min_spike_duration": int(vix_min_spike_duration),
                "min_peak_vix": float(vix_min_peak_vix),
                "forward_window_label": fwd_days_choice,
                "forward_days": int(fwd_d),
            }
            strategy_plan = build_vix_trade_plan(
                asset_label_for_display,
                strategy_params,
                signal_summary,
                best_phase_label=best_phase_label,
            )

            st.markdown("##### 建议交易战略")
            st.code(strategy_plan, language="text")

            save_col1, save_col2 = st.columns([2, 1])
            with save_col1:
                vix_result_name = st.text_input(
                    "保存当前结果名称",
                    value=f"{asset_label_for_display}_VIX_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    key="vix_result_name",
                )
            with save_col2:
                st.markdown("&nbsp;", unsafe_allow_html=True)
                if st.button("一键保存当前结果", key="vix_save_result"):
                    cleaned_result_name = vix_result_name.strip()
                    if not cleaned_result_name:
                        st.warning("请输入有效的保存名称。")
                    else:
                        phase_records = []
                        if not phase_fwd_df.empty:
                            phase_records = phase_fwd_df.reset_index().to_dict(orient="records")

                        save_payload = {
                            "saved_at": datetime.now().isoformat(),
                            "asset": {
                                "mode": backtest_asset_mode,
                                "label": asset_label_for_display,
                            },
                            "params": {
                                **strategy_params,
                                "pullback_ratio": round(vix_pullback_ratio, 4),
                            },
                            "summary": {
                                "sample_count": signal_summary["sample_count"],
                                "avg_return": round(signal_summary["avg_return"], 2) if signal_summary["avg_return"] is not None else None,
                                "win_rate": round(signal_summary["win_rate"], 1) if signal_summary["win_rate"] is not None else None,
                                "best_return": round(signal_summary["best_return"], 2) if signal_summary["best_return"] is not None else None,
                                "worst_return": round(signal_summary["worst_return"], 2) if signal_summary["worst_return"] is not None else None,
                                "latest_vix": round(float(latest_vix), 2),
                                "latest_phase": phase_label.get(latest_phase, latest_phase),
                                "best_phase": best_phase_label,
                            },
                            "phase_comparison": phase_records,
                            "strategy_text": strategy_plan,
                        }
                        save_vix_backtest_result(cleaned_result_name, save_payload)
                        st.success(f"已保存 VIX 回测结果：{cleaned_result_name}")

            # ---- 深度逻辑说明 ----
            with st.expander("📖 深度逻辑：为什么后期入场最优？", expanded=False):
                st.markdown("""
**1. 均值回归的确定性**

VIX 本质上是均值回归的。历史表明 VIX 很难长期维持在 30 以上（通常仅持续数周至数月）。
VIX 开始回落 ≈ 期权权利金缩水 ≈ 市场对未来波动率预期下降：

$$VIX \\propto \\text{Implied Volatility} \\propto \\text{Option Premium}$$

**2. 波动率溢价的回补**

高 VIX 时期，隐含波动率（IV）远高于实际波动率（RV），市场存在「过度恐慌溢价」。
恐慌峰值过去后，IV → RV 的收敛会带动估值快速修复。

**3. 历史数据支撑**

| 时期 | 代表事件 | 左侧买入代价 | 右侧后期入场 |
|------|----------|-------------|-------------|
| 2008 年金融危机 | VIX 峰值 ~80 | 2008/9 买入再跌 40% | 2009/3 VIX 回落后 1 年涨 ~60% |
| 2020 年疫情 | VIX 峰值 ~85 | 2/24 买入再跌 30% | 3/23 触底后 1 个月涨 ~30% |
| 2022 年加息 | VIX 峰值 ~38 | 1 月买入再跌 25% | 10 月底均值回归后 1 年涨 ~25% |

**4. 对个股的逻辑影响**

在高 VIX 阶段，系统性风险（Beta）主导一切——即使个股基本面优秀，
也会被市场的泥石流所淹没。**只有当 VIX 后期开始，个股的 Alpha 才会重新生效**。

**建议的回测入场过滤器：**
```
if VIX > 30:
    status = "高级观察状态"
    暂停个股信号执行
    if VIX < 0.90 * max(VIX_in_current_spike):
        status = "后期信号触发"
        允许执行个股入场逻辑
```
""")

    st.stop()  # 宏观模式下不渲染回测界面

# =========== 侧边栏：基本配置 ===========
st.sidebar.header("📊 基本配置 | Basic Configuration")

# 初始化最近下载的标的记录
if 'recently_downloaded' not in st.session_state:
    st.session_state.recently_downloaded = None

# 初始化日期选择的session_state
if 'selected_start_date' not in st.session_state:
    st.session_state.selected_start_date = None
if 'selected_end_date' not in st.session_state:
    st.session_state.selected_end_date = None

# 初始化价格图时间范围（独立控制）
if 'selected_price_start_date' not in st.session_state:
    st.session_state.selected_price_start_date = None
if 'selected_price_end_date' not in st.session_state:
    st.session_state.selected_price_end_date = None

# 初始化回测结果图时间范围（独立控制）
if 'selected_backtest_start_date' not in st.session_state:
    st.session_state.selected_backtest_start_date = None
if 'selected_backtest_end_date' not in st.session_state:
    st.session_state.selected_backtest_end_date = None

# =========== 统一的搜索/选择框：selectbox（保留瀑布式搜索） ===========
# 在选项列表中添加特殊选项 - 放在最上方
options_with_download = ["➕ 下载新标的"] + available_symbols

# 确定初始选择的索引
if st.session_state.recently_downloaded and st.session_state.recently_downloaded in available_symbols:
    # 如果有最近下载的标的，选择它
    initial_index = available_symbols.index(st.session_state.recently_downloaded) + 1
else:
    # 否则选择第一个真实标的
    initial_index = 1 if len(available_symbols) > 0 else 0

symbol = st.sidebar.selectbox(
    "🔍 搜索或选择标的",
    options_with_download,
    index=initial_index,
    key="unified_symbol_select",
    help="输入标的代码搜索，或选择'➕ 下载新标的'来添加新标的"
)

# 如果选择了非下载选项，清除最近下载标记
if symbol != "➕ 下载新标的":
    st.session_state.recently_downloaded = None

# 如果用户选择了"下载新标的"
if symbol == "➕ 下载新标的":
    new_symbol = st.sidebar.text_input(
        "输入标的代码",
        value="",
        key="new_symbol_input",
        placeholder="如: TSLA, NVDA, BTC-USD"
    ).upper().strip()
    
    if new_symbol and st.sidebar.button("📥 下载并保存", key="download_new", width="stretch"):
        if new_symbol not in available_symbols:
            try:
                with st.spinner(f"⏳ 正在下载 {new_symbol} 数据..."):
                    # 尝试下载数据
                    ticker = yf.Ticker(new_symbol)
                    historical_data = ticker.history(start="2015-01-01", end=datetime.now().date())
                    
                    if not historical_data.empty:
                        # 数据存在，保存为parquet格式
                        output_path = os.path.join(storage_dir, f"{new_symbol}.parquet")
                        
                        # 标准化列名 - 只保留需要的列
                        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                        data_to_save = historical_data[required_columns].copy()
                        data_to_save.columns = ['open', 'high', 'low', 'close', 'volume']
                        data_to_save.index.name = 'date'
                        
                        # 保存
                        data_to_save.to_parquet(output_path)
                        
                        st.sidebar.success(f"✅ {new_symbol} 数据下载成功！")
                        st.sidebar.info(f"📊 已获取 {len(historical_data)} 条数据")
                        
                        # 刷新可用符号列表
                        available_files = [f for f in os.listdir(storage_dir) if f.endswith('.parquet')]
                        available_symbols = sorted([f.split('.')[0] for f in available_files])
                        
                        # 记录新下载的标的到session_state
                        st.session_state.recently_downloaded = new_symbol
                        
                        st.rerun()
            except Exception as e:
                st.sidebar.error(f"❌ 下载失败：{str(e)}")
    
    # 如果用户选择了下载选项但没有输入symbol，提示并停止
    st.warning("⚠️ 请在上方输入标的代码，然后点击'下载并保存'")
    st.stop()

st.sidebar.divider()

# --- 企业信息卡片 ---
company_info_manager = CompanyInfoManager()
company_info = company_info_manager.get_company_info(symbol)

with st.sidebar.expander(f"ℹ️ {company_info.get('name', symbol)}", expanded=True):
    # 基本信息
    st.markdown(f"**代码**: {company_info.get('symbol', 'N/A')}")
    st.markdown(f"**行业**: {company_info.get('industry', 'N/A')}")
    st.markdown(f"**领域**: {company_info.get('sector', 'N/A')}")
    
    # 公司信息
    if company_info.get('website') and company_info.get('website') != 'N/A':
        st.markdown(f"**官网**: [{company_info.get('website')}]({company_info.get('website')})")
    
    if company_info.get('employees') and company_info.get('employees') != 'N/A':
        st.markdown(f"**员工数**: {company_info.get('employees'):,}")
    
    if company_info.get('ceo') and company_info.get('ceo') != 'N/A':
        st.markdown(f"**CEO**: {company_info.get('ceo', 'N/A')}")
    
    # 股票信息
    st.divider()
    
    # 当日交易数据 - 改用 markdown 避免省略号
    st.subheader("📊 当日数据 | Daily Data")
    col_open, col_change, col_change_pct = st.columns(3)
    
    with col_open:
        open_price = company_info.get('open_price', 'N/A')
        if isinstance(open_price, (int, float)):
            st.markdown(f"**开盘价**\n\n`${open_price:.2f}`")
        else:
            st.write(f"**开盘价**: {open_price}")
    
    with col_change:
        day_change = company_info.get('day_change', 'N/A')
        if isinstance(day_change, (int, float)):
            change_str = f"${day_change:+.2f}"
            color = "🔴" if day_change < 0 else "🟢"
            st.markdown(f"**涨跌** {color}\n\n`{change_str}`")
        else:
            st.write(f"**涨跌**: {day_change}")
    
    with col_change_pct:
        day_change_pct = company_info.get('day_change_percent', 'N/A')
        if isinstance(day_change_pct, (int, float)):
            change_pct_str = f"{day_change_pct:+.2f}%"
            color = "🔴" if day_change_pct < 0 else "🟢"
            st.markdown(f"**涨跌幅** {color}\n\n`{change_pct_str}`")
        else:
            st.write(f"**涨跌幅**: {day_change_pct}")
    
    # 股票基本指标
    st.subheader("📈 关键指标 | Key Metrics")
    col_price1, col_price2, col_price3 = st.columns(3)
    
    with col_price1:
        current_price = company_info.get('current_price', 'N/A')
        if isinstance(current_price, (int, float)):
            st.markdown(f"**当前价格**\n\n`${current_price:.2f}`")
        else:
            st.write(f"**当前价格**: {current_price}")
    
    with col_price2:
        pe_ratio = company_info.get('pe_ratio', 'N/A')
        if isinstance(pe_ratio, (int, float)):
            pe_display = f"{pe_ratio:.1f}"
        else:
            pe_display = str(pe_ratio)
        st.markdown(f"**P/E 比率**\n\n`{pe_display}`")
    
    with col_price3:
        roe = company_info.get('roe', 'N/A')
        if isinstance(roe, (int, float)):
            roe_display = f"{roe*100:.1f}%"
        else:
            roe_display = str(roe)
        st.markdown(f"**ROE**\n\n`{roe_display}`")
    
    # 现金流指标
    fcf = company_info.get('fcf', 'N/A')
    if fcf and fcf != 'N/A':
        fcf_in_millions = fcf / 1_000_000
        st.markdown(f"**自由现金流 (FCF)**: ${fcf_in_millions:,.1f}M")
    
    # 企业简介（中英双语）
    business_summary_cn = company_info.get('business_summary_cn', '')
    business_summary_en = company_info.get('business_summary_en', '')
    
    if business_summary_en:  # 只要有英文简介就显示
        st.divider()
        st.markdown("**企业简介**:")
        
        display_text = ""
        if business_summary_cn:
            display_text += f"🇨🇳 **中文** (Beta):\n{business_summary_cn}\n\n"
        
        display_text += f"🇺🇸 **English**:\n{business_summary_en}"
        st.caption(display_text)
    
    # 刷新按钮
    if st.button("🔄 刷新信息", key=f"refresh_{symbol}"):
        company_info = company_info_manager.get_company_info(symbol, force_refresh=True)
        st.rerun()

st.sidebar.divider()

# =========== 主区域：显示该标的的价格图表 ===========

# 加载该标的的全量数据（用于获取数据范围）
file_path = os.path.join(storage_dir, f"{symbol}.parquet")
df_full_data = None
data_earliest = None
data_latest = None

try:
    if os.path.exists(file_path):
        df_full_data = pd.read_parquet(file_path)
        if not df_full_data.empty:
            data_earliest = df_full_data.index.min()
            data_latest = df_full_data.index.max()
            if isinstance(data_earliest, pd.Timestamp):
                data_earliest = data_earliest.date()
            if isinstance(data_latest, pd.Timestamp):
                data_latest = data_latest.date()
except:
    pass

# 时间范围选择工具栏（显示在价格图表上方）
st.header(f"📊 {symbol} 价格走势 | Price Chart")
st.markdown("**⏰ 选择时间范围 | Select Time Range**")

col_price_time1, col_price_time2, col_price_time3, col_price_time4, col_price_time5 = st.columns(5)
today = datetime.now().date()

def update_price_range(start_offset_days, end_offset_days=0):
    """更新价格图的日期范围，但检查数据范围"""
    end_date_new = today - timedelta(days=end_offset_days) if end_offset_days > 0 else today
    start_date_new = end_date_new - timedelta(days=start_offset_days)
    
    # 检查是否在有效数据范围内
    if data_earliest and data_latest:
        start_date_new = max(start_date_new, data_earliest)
        end_date_new = min(end_date_new, data_latest)
        
        # 如果调整后的范围有效，才更新
        if start_date_new < end_date_new:
            st.session_state.selected_price_start_date = start_date_new
            st.session_state.selected_price_end_date = end_date_new
            st.rerun()

with col_price_time1:
    if st.button("1D", width="stretch", key="price_1d"):
        update_price_range(1)

with col_price_time2:
    if st.button("1W", width="stretch", key="price_1w"):
        update_price_range(7)

with col_price_time3:
    if st.button("1M", width="stretch", key="price_1m"):
        update_price_range(30)

with col_price_time4:
    if st.button("6M", width="stretch", key="price_6m"):
        update_price_range(180)

with col_price_time5:
    if st.button("1Y", width="stretch", key="price_1y"):
        update_price_range(365)

col_price_time6, col_price_time7, col_price_time8 = st.columns(3)

with col_price_time6:
    if st.button("5Y", width="stretch", key="price_5y"):
        update_price_range(365*5)

with col_price_time7:
    if st.button("All", width="stretch", key="price_all"):
        if data_earliest and data_latest:
            st.session_state.selected_price_start_date = data_earliest
            st.session_state.selected_price_end_date = data_latest
            st.rerun()

with col_price_time8:
    # 显示当前价格图的时间范围
    price_start = st.session_state.selected_price_start_date if st.session_state.selected_price_start_date else data_earliest
    price_end = st.session_state.selected_price_end_date if st.session_state.selected_price_end_date else data_latest
    st.markdown(f"**📅 {price_start} ~ {price_end}**")

# 显示价格图表
if df_full_data is not None and not df_full_data.empty:
    # 按时间范围筛选数据（使用价格图的独立时间范围）
    price_start_for_display = st.session_state.selected_price_start_date if st.session_state.selected_price_start_date else data_earliest
    price_end_for_display = st.session_state.selected_price_end_date if st.session_state.selected_price_end_date else data_latest
    
    start_ts = pd.Timestamp(price_start_for_display)
    end_ts = pd.Timestamp(price_end_for_display)
    mask = (df_full_data.index >= start_ts) & (df_full_data.index <= end_ts)
    df_display = df_full_data[mask]
    
    if not df_display.empty:
        fig_price = go.Figure()
        
        # K线图
        fig_price.add_trace(go.Candlestick(
            x=df_display.index,
            open=df_display['open'],
            high=df_display['high'],
            low=df_display['low'],
            close=df_display['close'],
            name='K线 | Candlestick'
        ))
        
        fig_price.update_layout(
            template="plotly_dark",
            height=500,
            title=f"📊 {symbol} 价格走势",
            xaxis_title="日期 | Date",
            yaxis_title="价格 (USD) | Price",
            hovermode='x unified'
        )
        fig_price.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
        
        st.plotly_chart(fig_price, width="stretch")
    else:
        st.warning("⚠️ 选定时间范围内无可用数据")
else:
    st.warning("⚠️ 无法加载该标的的数据")

st.divider()

st.sidebar.header("📅 回测时间 | Backtest Period")

# 🔄 从实际数据中动态获取回测开始日期（不使用硬编码的2023/01/01）
# 计算步骤：
# 1. 尝试加载该symbol的数据文件
# 2. 提取数据中最早的日期作为基准
# 3. 如果有IPO日期且晚于数据最早日期，使用IPO日期
# 4. 否则使用数据中最早的日期

default_start = None
file_path = os.path.join(storage_dir, f"{symbol}.parquet")

try:
    if os.path.exists(file_path):
        df_temp = pd.read_parquet(file_path)
        if not df_temp.empty:
            # 从数据中获取最早日期
            data_earliest = df_temp.index.min()
            if isinstance(data_earliest, pd.Timestamp):
                default_start = data_earliest.to_pydatetime()
            else:
                default_start = datetime.combine(data_earliest, datetime.min.time())
except:
    pass

# 如果无法从数据获取，回退到IPO日期或当前日期的5年前
if default_start is None:
    ipo_date_str = company_info.get('ipo_date', 'N/A')
    if ipo_date_str and ipo_date_str != 'N/A':
        try:
            default_start = datetime.strptime(ipo_date_str, '%Y-%m-%d')
        except:
            default_start = datetime.now() - timedelta(days=365*5)
    else:
        # 最后的回退：5年前的今天
        default_start = datetime.now() - timedelta(days=365*5)
    
    st.sidebar.info(f"ℹ️ 已根据最早可用数据或IPO日期自动设置回测开始日期")
else:
    # IPO日期检查：如果IPO日期晚于数据最早日期，使用IPO日期
    ipo_date_str = company_info.get('ipo_date', 'N/A')
    if ipo_date_str and ipo_date_str != 'N/A':
        try:
            ipo_date = datetime.strptime(ipo_date_str, '%Y-%m-%d')
            if ipo_date > default_start:
                default_start = ipo_date
                st.sidebar.info(f"ℹ️ {symbol} 上市于 {ipo_date_str}，已调整回测开始日期")
        except:
            pass

col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input(
        "开始日期",
        value=st.session_state.selected_start_date if st.session_state.selected_start_date else default_start,
        key="start_date_input"
    )
with col2:
    end_date = st.date_input(
        "结束日期",
        value=st.session_state.selected_end_date if st.session_state.selected_end_date else datetime.now(),
        key="end_date_input"
    )

# 更新session_state中的日期（用于快速选择之后的保存）
st.session_state.selected_start_date = start_date
st.session_state.selected_end_date = end_date

# =========== 侧边栏：资金配置 ===========
st.sidebar.header("💰 资金配置 | Capital Setup")
initial_capital = st.sidebar.number_input(
    "初始资金 (USD)",
    value=30000.0,
    min_value=1000.0,
    step=10000.0,
    format="%.0f"
)

# =========== 侧边栏：策略选择 ===========
st.sidebar.header("🎯 策略选择 | Strategy Selection")
strategy = st.sidebar.selectbox(
    "选择策略",
    STRATEGIES,
    format_func=lambda s: f"{s.name}"
)

# 显示策略说明
with st.sidebar.expander("📖 策略说明 | Strategy Description", expanded=False):
    st.markdown(f"**中文**: {strategy.description_cn}")
    st.markdown(f"**English**: {strategy.description_en}")

# =========== 侧边栏：策略参数 ===========
st.sidebar.header("⚙️ 策略参数 | Strategy Parameters")

if strategy.name == "均线交叉策略":
    ma_short = st.sidebar.slider(
        "短期均线 (SMA Short)",
        min_value=5,
        max_value=50,
        value=20,
        step=1
    )
    ma_long = st.sidebar.slider(
        "长期均线 (SMA Long)",
        min_value=30,
        max_value=200,
        value=60,
        step=1
    )
    strategy_params = {"ma_short": ma_short, "ma_long": ma_long}

elif strategy.name == "分歧交易策略（改进版）":
    # 分歧交易策略参数
    col_param1, col_param2 = st.sidebar.columns(2)
    
    with col_param1:
        trend_ma = st.slider(
            "📊 趋势均线周期",
            min_value=10,
            max_value=50,
            value=20,
            step=1,
            help="用于判断上升/下降趋势的均线周期"
        )
        amplitude_ratio = st.slider(
            "📈 波幅扩大倍数",
            min_value=1.1,
            max_value=2.0,
            value=1.3,
            step=0.1,
            help="B日波幅需要超过A日波幅的倍数"
        )
    
    with col_param2:
        volume_ratio = st.slider(
            "📢 成交量倍数",
            min_value=1.0,
            max_value=2.0,
            value=1.2,
            step=0.1,
            help="成交量需要超过20日均量的倍数"
        )
        atr_period = st.slider(
            "🎯 ATR周期",
            min_value=7,
            max_value=30,
            value=14,
            step=1,
            help="计算平均真实波幅的周期"
        )
    
    col_param3, col_param4 = st.sidebar.columns(2)
    
    with col_param3:
        stop_loss_atr = st.slider(
            "🛑 止损距离 (ATR倍数)",
            min_value=1.0,
            max_value=3.0,
            value=2.0,
            step=0.5,
            help="止损距离 = 进价 ± ATR × 此值"
        )
    
    with col_param4:
        hold_days = st.slider(
            "⏱️ 最大持有天数",
            min_value=1,
            max_value=20,
            value=5,
            step=1,
            help="超过此天数未平仓则强制平仓"
        )
    
    strategy_params = {
        "trend_ma": trend_ma,
        "amplitude_ratio": amplitude_ratio,
        "volume_ratio": volume_ratio,
        "atr_period": atr_period,
        "stop_loss_atr": stop_loss_atr,
        "hold_days": hold_days
    }

elif strategy.name == "布林带交易策略":
    # ========== 参数维度启用/禁用区块 ==========
    st.sidebar.subheader("⚙️ 扫描参数维度控制")
    enable_boll_period = st.sidebar.checkbox("启用Boll周期", value=True, key="enable_boll_period")
    enable_boll_std = st.sidebar.checkbox("启用Boll Std", value=True, key="enable_boll_std")
    enable_extreme_period = st.sidebar.checkbox("启用极值周期", value=False, key="enable_extreme_period")
    enable_ma_period = st.sidebar.checkbox("启用趋势均线周期", value=False, key="enable_ma_period")

    # ========== 已保存参数分析区块 ==========
    st.sidebar.subheader("📂 已保存参数文件分析")
    # 搜索所有 *_best_params.json 文件
    import glob
    import os
    best_param_files = glob.glob(os.path.join(storage_dir, '*_best_params.json'))
    file_titles = [os.path.basename(f).replace('_best_params.json','') for f in best_param_files]
    if file_titles:
        selected_file = st.sidebar.selectbox("选择分析标的", file_titles, key="select_best_param_file")
        if selected_file:
            file_path = os.path.join(storage_dir, f"{selected_file}_best_params.json")
            try:
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    params_data = json.load(f)
                st.write(f"### 标的: {selected_file}")
                st.write("**收益率最高参数:**")
                st.json(params_data.get('best_return', {}))
                st.write("**胜率最高参数:**")
                st.json(params_data.get('best_win', {}))
            except Exception as e:
                st.error(f"分析失败: {e}")
    else:
        st.sidebar.info("暂无已保存参数文件")

    # 布林带策略参数 - 分为基础参数和高阶参数
    st.sidebar.subheader("📊 布林带基础参数")
    # 简化版布林带策略 - 仅3个核心参数
    col_param1, col_param2, col_param3 = st.sidebar.columns(3)

    with col_param1:
        boll_period = st.slider(
            "📊 布林带周期 | Period",
            min_value=10,
            max_value=50,
            value=20,
            step=1,
            help="20日布林带 / 20-day Bollinger Bands"
        )

    with col_param2:
        boll_std = st.slider(
            "📈 标准差倍数 | Std Dev",
            min_value=1.0,
            max_value=3.0,
            value=2.0,
            step=0.1,
            help="上下轨 = 中轨 ± 标准差 × 此值 / Upper/Lower = Middle ± Std × Value"
        )

    with col_param3:
        buy_ratio = st.slider(
            "💰 买入资金比例 | Buy Ratio",
            min_value=0.1,
            max_value=1.0,
            value=0.8,
            step=0.1,
            help="触及下轨时投入的资金比例 / Capital ratio when lower band triggered"
        )

    # 策略说明
    st.sidebar.info(
        "**📌 简化版布林带 | Simplified Bollinger Bands**\n"
        "• 价格 < 下轨 → 买入(资金比例可调) / Price < Lower Band → BUY\n"
        "• 价格 > 上轨 → 卖出全部 / Price > Upper Band → SELL ALL\n"
        "• 基于日线 / Daily-based (20日 = 20 days)\n"
        "• 每天最多1个信号 / Max 1 signal per day"
    )


    # ========== 高级参数空间设置 ========== 
    with st.sidebar.expander("🛠️ 参数空间设置 (高级)", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            boll_period_min = st.number_input("Boll周期最小", min_value=5, max_value=100, value=10, step=1)
            boll_period_max = st.number_input("Boll周期最大", min_value=5, max_value=200, value=50, step=1)
            boll_period_step = st.number_input("Boll周期步长", min_value=1, max_value=50, value=5, step=1)
            extreme_period_min = st.number_input("极值周期最小", min_value=5, max_value=100, value=10, step=1)
            extreme_period_max = st.number_input("极值周期最大", min_value=5, max_value=200, value=50, step=1)
            extreme_period_step = st.number_input("极值周期步长", min_value=1, max_value=50, value=5, step=1)
        with col2:
            boll_std_min = st.number_input("Std最小", min_value=0.1, max_value=10.0, value=1.0, step=0.1, format="%.1f")
            boll_std_max = st.number_input("Std最大", min_value=0.1, max_value=10.0, value=3.0, step=0.1, format="%.1f")
            boll_std_step = st.number_input("Std步长", min_value=0.01, max_value=2.0, value=0.5, step=0.01, format="%.2f")
            ma_period_min = st.number_input("趋势均线最小", min_value=5, max_value=200, value=10, step=1)
            ma_period_max = st.number_input("趋势均线最大", min_value=5, max_value=300, value=100, step=1)
            ma_period_step = st.number_input("趋势均线步长", min_value=1, max_value=50, value=10, step=1)

    # 参数空间扫描按钮
    scan_result = None
    if st.sidebar.button("🔍 扫描Boll策略参数", key="scan_boll_params", width="stretch"):
        import time
        progress_bar = st.progress(0, text="参数空间扫描进度")
        status_text = st.empty()
        try:
            file_path = os.path.join(storage_dir, f"{symbol}.parquet")
            df = pd.read_parquet(file_path)
            boll_strategy = None
            for s in STRATEGIES:
                if getattr(s, 'name', None) == "布林带交易策略":
                    boll_strategy = s
                    break
            if boll_strategy is None:
                st.error("未找到布林带策略实例！")
            else:
                # 生成参数空间
                param_ranges = {}
                if enable_boll_period:
                    param_ranges['boll_period_range'] = (int(boll_period_min), int(boll_period_max)+1, int(boll_period_step))
                else:
                    param_ranges['boll_period_range'] = (20, 21, 1)  # 固定默认值
                if enable_boll_std:
                    param_ranges['boll_std_range'] = (float(boll_std_min), float(boll_std_max)+0.0001, float(boll_std_step))
                else:
                    param_ranges['boll_std_range'] = (2.0, 2.01, 0.01)
                if enable_extreme_period:
                    param_ranges['extreme_period_range'] = (int(extreme_period_min), int(extreme_period_max)+1, int(extreme_period_step))
                else:
                    param_ranges['extreme_period_range'] = (20, 21, 1)
                if enable_ma_period:
                    param_ranges['ma_period_range'] = (int(ma_period_min), int(ma_period_max)+1, int(ma_period_step))
                else:
                    param_ranges['ma_period_range'] = (20, 21, 1)

                # 扫描序号与日期
                import glob
                scan_files = glob.glob(os.path.join(storage_dir, f"{symbol}_grid_search_results_*.csv"))
                scan_idx = len(scan_files) + 1
                scan_date = time.strftime('%Y%m%d')
                results_file = f"{symbol}_grid_search_results_{scan_idx}_{scan_date}.csv"
                best_params_file = f"{symbol}_best_params_{scan_idx}_{scan_date}.json"

                def progress_callback(progress, elapsed, eta, finished, total):
                    percent = int(progress * 100)
                    progress_bar.progress(progress, text=f"进度: {percent}%  已用: {elapsed:.1f}s  预计剩余: {eta:.1f}s  ({finished}/{total})")
                    status_text.info(f"进度: {percent}%  已用: {elapsed:.1f}s  预计剩余: {eta:.1f}s  ({finished}/{total})")

                best_return, best_win = boll_strategy.grid_search(
                    df, symbol, initial_capital=initial_capital, save_dir=storage_dir,
                    progress_callback=progress_callback,
                    results_file=results_file,
                    best_params_file=best_params_file,
                    **param_ranges
                )
                progress_bar.progress(1.0, text="参数空间扫描完成！")
                status_text.success(f"✅ {symbol} 参数空间扫描完成，结果已保存到 {storage_dir}")
                st.write("**收益率最高参数:**")
                st.json(best_return)
                st.write("**胜率最高参数:**")
                st.json(best_win)
        except Exception as e:
            st.error(f"❌ 扫描失败: {e}")

    strategy_params = {
        "boll_period": boll_period,
        "boll_std": boll_std,
        "buy_ratio": buy_ratio
    }

elif strategy.name == "周期性趋势交易策略":
    col_ct1, col_ct2 = st.sidebar.columns(2)
    with col_ct1:
        ct_min_period = st.sidebar.slider("最短周期(天)", min_value=3, max_value=30, value=5, step=1, key="ct_min_period")
        ct_signal_strength = st.sidebar.slider("信号强度阈值", min_value=0.1, max_value=1.0, value=0.5, step=0.1, key="ct_signal")
        ct_atr_stop = st.sidebar.slider("ATR止损倍数", min_value=1.0, max_value=4.0, value=2.0, step=0.5, key="ct_atr")
    with col_ct2:
        ct_max_period = st.sidebar.slider("最长周期(天)", min_value=20, max_value=120, value=60, step=5, key="ct_max_period")
        ct_position_size = st.sidebar.slider("头寸规模", min_value=0.1, max_value=1.0, value=1.0, step=0.1, key="ct_pos")
    strategy_params = {
        "min_period": ct_min_period, "max_period": ct_max_period,
        "signal_strength": ct_signal_strength, "position_size": ct_position_size,
        "atr_stop_loss": ct_atr_stop
    }

elif strategy.name == "周期性均值回归策略":
    cmr_period = st.sidebar.slider("周期长度(天)", min_value=10, max_value=100, value=30, step=5, key="cmr_period")
    cmr_zscore = st.sidebar.slider("Z-score阈值", min_value=0.5, max_value=3.0, value=1.5, step=0.1, key="cmr_zscore",
                                    help="超买/超卖判定：Z-score超过此值触发信号")
    cmr_lookback = st.sidebar.slider("回看窗口(天)", min_value=20, max_value=200, value=60, step=10, key="cmr_lookback")
    strategy_params = {
        "period": cmr_period, "zscore_threshold": cmr_zscore, "lookback": cmr_lookback
    }

elif strategy.name == "周期相位对齐策略":
    cpa_period = st.sidebar.slider("主周期(天)", min_value=10, max_value=100, value=30, step=5, key="cpa_period")
    col_cp1, col_cp2 = st.sidebar.columns(2)
    with col_cp1:
        cpa_buy_start = st.sidebar.slider("买入相位起点", min_value=0.0, max_value=0.5, value=0.0, step=0.05, key="cpa_start",
                                           help="周期相位 0-1，0=周期底部")
    with col_cp2:
        cpa_buy_end = st.sidebar.slider("买入相位终点", min_value=0.1, max_value=0.8, value=0.3, step=0.05, key="cpa_end")
    cpa_reversion = st.sidebar.slider("最小回归系数", min_value=0.1, max_value=1.0, value=0.5, step=0.1, key="cpa_rev")
    strategy_params = {
        "period": cpa_period, "phase_buy_start": cpa_buy_start,
        "phase_buy_end": cpa_buy_end, "min_reversion": cpa_reversion
    }

elif strategy.name == "均值回归波动率策略":
    col_mv1, col_mv2 = st.sidebar.columns(2)
    with col_mv1:
        mv_zscore_period = st.sidebar.slider("Z-Score周期(天)", min_value=20, max_value=120, value=60, step=5, key="mv_zp")
        mv_zscore_thresh = st.sidebar.slider("Z-Score买入阈值", min_value=-4.0, max_value=-1.0, value=-2.5, step=0.1, format="%.1f", key="mv_zt",
                                              help="Z-Score低于此值时触发买入(负数)")
        mv_volume_mult = st.sidebar.slider("成交量倍数", min_value=1.0, max_value=4.0, value=2.0, step=0.5, key="mv_vm",
                                            help="成交量需超过均量的倍数")
        mv_stop_loss = st.sidebar.slider("止损幅度(%)", min_value=-0.10, max_value=-0.01, value=-0.04, step=0.01, format="%.2f", key="mv_sl")
    with col_mv2:
        mv_zscore_sell = st.sidebar.slider("止盈Z-Score", min_value=0.5, max_value=3.0, value=1.5, step=0.1, key="mv_zs",
                                            help="Z-Score高于此值时触发止盈")
        mv_vol_period = st.sidebar.slider("均量周期(天)", min_value=10, max_value=60, value=20, step=5, key="mv_vp")
        mv_sell_ratio = st.sidebar.slider("均值平仓比例", min_value=0.1, max_value=1.0, value=0.5, step=0.1, key="mv_sr",
                                           help="价格回到均值时平仓的比例")
    strategy_params = {
        "zscore_period": mv_zscore_period, "zscore_threshold": mv_zscore_thresh,
        "zscore_sell_high": mv_zscore_sell, "volume_multiplier": mv_volume_mult,
        "volume_period": mv_vol_period, "stop_loss_pct": mv_stop_loss,
        "sell_ratio_mean": mv_sell_ratio
    }

elif strategy.name == "XGBoost机器学习策略":
    st.sidebar.subheader("🤖 机器学习策略配置")
    
    # 检查是否要加载历史模型
    from Strategy_Pool.custom.xgboost_ml_strategy import ModelRegistry
    
    use_existing_model = st.sidebar.checkbox("🏆 使用历史最优模型", value=False, help="勾选后使用历史训练的模型进行推理")
    
    selected_model_id = None
    if use_existing_model:
        best_models = ModelRegistry.get_ranked_models(top_n=20)
        if not best_models.empty:
            # 构建显示标签
            model_labels = [
                f"{row['model_id']} | 性能:{row['performance_score']:.4f} | 特征:{row['features_count']}" 
                for _, row in best_models.iterrows()
            ]
            
            selected_label = st.sidebar.selectbox(
                "选择模型",
                model_labels,
                help="按性能分数排序，点击切换"
            )
            
            if selected_label:
                selected_model_id = selected_label.split(' | ')[0]
                st.sidebar.success(f"✅ 已选择模型：{selected_model_id}")
        else:
            st.sidebar.warning("⚠️ 暂无历史模型，将进入训练模式")
    
    # 训练模式参数
    if not use_existing_model or selected_model_id is None:
        st.sidebar.markdown("**⏱️ 训练控制参数**")
        col_ml1, col_ml2 = st.sidebar.columns(2)
        
        with col_ml1:
            time_limit = st.number_input(
                "时间限制 (秒)",
                min_value=30,
                max_value=3600,
                value=300,
                step=30,
                help="训练超时熔断时间"
            )
        
        with col_ml2:
            target_limit = st.number_input(
                "早停耐心度",
                min_value=10,
                max_value=500,
                value=100,
                step=10,
                help="验证集表现无改进的最大轮数"
            )
        
        strategy_params = {
            "time_limit": time_limit,
            "target_limit": target_limit,
            "model_id": None  # 训练模式
        }
    else:
        strategy_params = {
            "model_id": selected_model_id  # 推理模式
        }

else:
    st.sidebar.info("⚠️ 此策略参数配置待实现")
    strategy_params = {}

# =========== 侧边栏：高级交易所模拟器配置 ===========
st.sidebar.divider()
st.sidebar.header("🔬 高级交易所模拟器 | Advanced Mode")
enable_advanced_mode = st.sidebar.checkbox(
    "启用高级模式 | Enable Advanced Mode",
    value=False,
    help="使用市场冲击和逼真的交易成本进行回测"
)

advanced_simulator_config = None
if enable_advanced_mode:
    st.sidebar.subheader("交易成本参数 | Cost Parameters")
    col_a1, col_a2 = st.sidebar.columns(2)
    
    with col_a1:
        market_impact_lambda = st.number_input(
            "市场冲击系数 λ",
            min_value=0.1,
            max_value=2.0,
            value=0.8,
            step=0.1
        )
    
    with col_a2:
        commission_rate = st.number_input(
            "佣金率 (%)",
            min_value=0.0,
            max_value=1.0,
            value=0.1,
            step=0.01
        )
    
    advanced_simulator_config = ExchangeConfig(
        commission_rate=commission_rate / 100.0,
        impact_coefficient=market_impact_lambda
    )

# =========== 侧边栏：运行回测按钮 ===========
st.sidebar.header("🚀 执行 | Execute")
run_backtest = st.sidebar.button("▶️ 运行回测 | Run Backtest", width="stretch")

# =========== XGBoost 子进程辅助函数 ===========
def _read_progress(progress_file):
    """安全读取进度文件"""
    try:
        if os.path.exists(progress_file):
            with open(progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return None

def _launch_xgboost_worker(symbol, start_date, end_date, initial_capital, strategy_params, storage_dir):
    """启动 XGBoost 子进程，返回 (progress_file, result_file)"""
    # 创建临时目录存放通信文件
    work_dir = os.path.join(os.path.dirname(__file__), '..', 'Data_Hub', 'storage', '.xgb_worker')
    os.makedirs(work_dir, exist_ok=True)

    ts = int(time.time() * 1000)
    config_file = os.path.join(work_dir, f'config_{ts}.json')
    progress_file = os.path.join(work_dir, f'progress_{ts}.json')
    result_file = os.path.join(work_dir, f'result_{ts}.pkl')

    config_data = {
        'data_path': os.path.join(storage_dir, f'{symbol}.parquet'),
        'symbol': symbol,
        'start_date': start_date.isoformat() if hasattr(start_date, 'isoformat') else str(start_date),
        'end_date': end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date),
        'initial_capital': initial_capital,
        'model_id': strategy_params.get('model_id'),
        'time_limit': strategy_params.get('time_limit', 300),
        'target_limit': strategy_params.get('target_limit', 100),
        'strategy_params': strategy_params,
        'progress_file': progress_file,
        'result_file': result_file,
    }
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, ensure_ascii=False, default=str)

    worker_script = os.path.join(os.path.dirname(__file__), 'xgboost_worker.py')
    proc = subprocess.Popen(
        [sys.executable, worker_script, config_file],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
    )
    return proc.pid, progress_file, result_file, config_file

def _load_xgboost_result(result_file, symbol, start_date, end_date, initial_capital, strategy_params):
    """从子进程结果文件构建 BacktestResult"""
    with open(result_file, 'rb') as f:
        data = pickle.load(f)

    from Engine_Matrix.backtest_engine import BacktestResult, BacktestConfig
    config = BacktestConfig(
        symbol=symbol,
        start_date=start_date.isoformat() if hasattr(start_date, 'isoformat') else str(start_date),
        end_date=end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date),
        initial_capital=initial_capital,
        strategy_params=strategy_params,
    )
    return BacktestResult(
        equity_curve=data['equity_curve'],
        trades=data.get('trades', pd.DataFrame()),
        metrics={
            'total_return': data.get('total_return', 0.0),
            'annual_return': data.get('annual_return', 0.0),
            'sharpe_ratio': data.get('sharpe_ratio', 0.0),
            'max_drawdown': data.get('max_drawdown', 0.0),
            'win_rate': data.get('win_rate', 0.0),
            'num_trades': data.get('num_trades', 0),
        },
        raw_data=data['signal_result'],
        config=config,
    )

def _cleanup_worker_files(*files):
    """清理子进程临时文件"""
    for f in files:
        try:
            if f and os.path.exists(f):
                os.remove(f)
        except OSError:
            pass


# =========== XGBoost 子进程进度轮询 Fragment ===========
@st.fragment(run_every=3)
def _xgb_progress_fragment():
    """每 3 秒自动刷新，读取子进程进度文件并更新 UI"""
    xgb_state = st.session_state.get('xgb_worker')
    if not xgb_state:
        return

    progress_file = xgb_state['progress_file']
    result_file = xgb_state['result_file']
    config_file = xgb_state['config_file']

    progress = _read_progress(progress_file)

    if progress is None:
        st.info("🚀 XGBoost 子进程启动中...")
        return

    if not progress.get('done', False):
        # 仍在运行 — 显示进度
        step = progress.get('step', 0)
        total = progress.get('total', 5)
        msg = progress.get('message', '运行中...')
        pct = min(step / total, 0.99) if total > 0 else 0
        st.progress(pct, text=msg)
        elapsed = time.time() - xgb_state.get('start_time', time.time())
        st.caption(f"⏱️ 已运行 {elapsed:.0f} 秒")
    else:
        # 已完成
        error = progress.get('error')
        if error:
            st.error(f"❌ XGBoost 回测失败:\n```\n{error}\n```")
            st.session_state.pop('xgb_worker', None)
            _cleanup_worker_files(progress_file, result_file, config_file)
        elif os.path.exists(result_file):
            try:
                result = _load_xgboost_result(
                    result_file,
                    xgb_state['symbol'],
                    xgb_state['start_date'],
                    xgb_state['end_date'],
                    xgb_state['initial_capital'],
                    xgb_state['strategy_params'],
                )
                st.session_state.backtest_result = result
                st.session_state.enable_advanced_mode = False
                st.success("✅ XGBoost 回测完成！结果已加载。")
                st.session_state.pop('xgb_worker', None)
                _cleanup_worker_files(progress_file, result_file, config_file)
            except Exception as e:
                st.error(f"❌ 加载结果失败: {e}")
                st.session_state.pop('xgb_worker', None)
                _cleanup_worker_files(progress_file, result_file, config_file)
        else:
            st.warning("⚠️ 子进程已完成但未找到结果文件")
            st.session_state.pop('xgb_worker', None)
            _cleanup_worker_files(progress_file, config_file)


# =========== 主区域：回测执行 ===========
if run_backtest:
    is_xgboost = (strategy.name == "XGBoost机器学习策略")

    if is_xgboost and not enable_advanced_mode:
        # ====== XGBoost 策略：子进程模式（防止阻塞 Streamlit） ======
        pid, pf, rf, cf = _launch_xgboost_worker(
            symbol, start_date, end_date, initial_capital, strategy_params, storage_dir
        )
        st.session_state['xgb_worker'] = {
            'pid': pid,
            'progress_file': pf,
            'result_file': rf,
            'config_file': cf,
            'start_time': time.time(),
            'symbol': symbol,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': initial_capital,
            'strategy_params': strategy_params,
        }
        st.toast("🚀 XGBoost 子进程已启动！", icon="🤖")
    else:
        # ====== 常规策略 / 高级模式：直接执行 ======
        try:
            with st.spinner("⏳ 正在执行回测，请稍候..."):
                if enable_advanced_mode:
                    file_path = os.path.join(storage_dir, f"{symbol}.parquet")
                    df = pd.read_parquet(file_path)
                    start_ts = pd.Timestamp(start_date)
                    end_ts = pd.Timestamp(end_date)
                    mask = (df.index >= start_ts) & (df.index <= end_ts)
                    df_filtered = df[mask].copy()

                    if is_xgboost:
                        from Strategy_Pool.custom.xgboost_ml_strategy import XGBoostMLStrategy
                        model_id = strategy_params.get("model_id")
                        strategy_instance = XGBoostMLStrategy(
                            model_id=model_id,
                            time_limit=strategy_params.get("time_limit", 300) if model_id is None else None,
                            target_limit=strategy_params.get("target_limit", 100) if model_id is None else None,
                        )
                        signal_data = strategy_instance.backtest(df_filtered, {})
                    else:
                        signal_data = strategy.backtest(df_filtered, strategy_params)

                    simulator = AdvancedExchangeSimulator(advanced_simulator_config)
                    result = simulator.run(signal_data, initial_capital=initial_capital, strategy_name=strategy.name)
                else:
                    config = BacktestConfig(
                        symbol=symbol,
                        start_date=start_date.isoformat(),
                        end_date=end_date.isoformat(),
                        initial_capital=initial_capital,
                        strategy_params=strategy_params,
                    )
                    engine = BacktestEngine(strategy, data_dir=storage_dir)
                    result = engine.run(config)
                    annual_return = result.metrics.get('annual_return', -999)
                    update_best_strategy(symbol, strategy.name, strategy_params, annual_return)

            st.session_state.backtest_result = result
            st.session_state.enable_advanced_mode = enable_advanced_mode

            if not enable_advanced_mode:
                annual_return = result.metrics.get('annual_return', -999)
                update_best_strategy(symbol, strategy.name, strategy_params, annual_return)

            st.success("✅ 回测执行完成！")

        except Exception as e:
            import traceback
            st.error(f"❌ 回测失败: {str(e)}\n\n详细错误:\n{traceback.format_exc()}")
            st.session_state.backtest_result = None

# =========== XGBoost 进度显示区域（Fragment 自动刷新） ===========
if st.session_state.get('xgb_worker'):
    st.divider()
    st.subheader("🤖 XGBoost 训练进度")
    _xgb_progress_fragment()

# =========== 主区域：显示回测结果 ===========
if hasattr(st.session_state, 'backtest_result') and st.session_state.backtest_result is not None:
    result = st.session_state.backtest_result
    is_advanced_mode = st.session_state.get('enable_advanced_mode', False)
    
    st.header("📈 回测结果")
    
    # 获取回测数据的日期范围
    backtest_earliest = None
    backtest_latest = None
    
    if is_advanced_mode and isinstance(result, pd.DataFrame):
        if not result.empty:
            backtest_earliest = result.index.min().date() if isinstance(result.index.min(), pd.Timestamp) else result.index.min()
            backtest_latest = result.index.max().date() if isinstance(result.index.max(), pd.Timestamp) else result.index.max()
    
    # =========== 时间区间快速选择工具栏 ===========
    st.markdown("**⏰ 选择时间区间 | Select Time Range**")
    
    col_time1, col_time2, col_time3, col_time4, col_time5 = st.columns(5)
    today = datetime.now().date()
    
    def update_backtest_range(start_offset_days, end_offset_days=0):
        """更新回测结果图的时间范围，检查回测数据范围"""
        end_date_new = today - timedelta(days=end_offset_days) if end_offset_days > 0 else today
        start_date_new = end_date_new - timedelta(days=start_offset_days)
        
        # 检查是否在有效回测数据范围内
        if backtest_earliest and backtest_latest:
            start_date_new = max(start_date_new, backtest_earliest)
            end_date_new = min(end_date_new, backtest_latest)
            
            # 如果调整后的范围有效，才更新
            if start_date_new < end_date_new and (start_date_new != st.session_state.selected_backtest_start_date or end_date_new != st.session_state.selected_backtest_end_date):
                st.session_state.selected_backtest_start_date = start_date_new
                st.session_state.selected_backtest_end_date = end_date_new
                st.rerun()
    
    with col_time1:
        if st.button("1D", width="stretch", key="main_range_1d"):
            update_backtest_range(1)
    
    with col_time2:
        if st.button("1W", width="stretch", key="main_range_1w"):
            update_backtest_range(7)
    
    with col_time3:
        if st.button("1M", width="stretch", key="main_range_1m"):
            update_backtest_range(30)
    
    with col_time4:
        if st.button("6M", width="stretch", key="main_range_6m"):
            update_backtest_range(180)
    
    with col_time5:
        if st.button("1Y", width="stretch", key="main_range_1y"):
            update_backtest_range(365)
    
    col_time6, col_time7, col_time8, col_time9 = st.columns(4)
    
    with col_time6:
        if st.button("5Y", width="stretch", key="main_range_5y"):
            update_backtest_range(365*5)
    
    with col_time7:
        if st.button("YTD", width="stretch", key="main_range_ytd"):
            ytd_start = date(today.year, 1, 1)
            # 检查YTD范围是否有效
            if backtest_earliest and backtest_latest:
                ytd_start = max(ytd_start, backtest_earliest)
                if ytd_start < backtest_latest and (ytd_start != st.session_state.selected_backtest_start_date or today != st.session_state.selected_backtest_end_date):
                    st.session_state.selected_backtest_start_date = ytd_start
                    st.session_state.selected_backtest_end_date = today
                    st.rerun()
    
    with col_time8:
        if st.button("All", width="stretch", key="main_range_all"):
            if backtest_earliest and backtest_latest:
                if (backtest_earliest != st.session_state.selected_backtest_start_date or backtest_latest != st.session_state.selected_backtest_end_date):
                    st.session_state.selected_backtest_start_date = backtest_earliest
                    st.session_state.selected_backtest_end_date = backtest_latest
                    st.rerun()
    
    with col_time9:
        # 显示当前回测结果的时间范围
        backtest_start_display = st.session_state.selected_backtest_start_date if st.session_state.selected_backtest_start_date else backtest_earliest
        backtest_end_display = st.session_state.selected_backtest_end_date if st.session_state.selected_backtest_end_date else backtest_latest
        st.markdown(f"**📅 {backtest_start_display} ~ {backtest_end_display}**")
    
    st.divider()
    
    # 判断是否为高级模式
    if is_advanced_mode and isinstance(result, pd.DataFrame):
        # ===== 高级模式结果显示 =====
        st.info("🔬 高级模式：采用真实市场冲击和交易成本进行回测")
        
        if 'equity' in result.columns:
            final_equity_adv = result['equity'].iloc[-1]
            total_commission = result['commission_cost'].sum() if 'commission_cost' in result.columns else 0
            total_impact = result['market_impact_cost'].sum() if 'market_impact_cost' in result.columns else 0
            total_cost = total_commission + total_impact
            total_return_adv = (final_equity_adv - initial_capital) / initial_capital if initial_capital != 0 else 0
            
            # 资金变化
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**初始资金 | Initial Capital**\n\n`${initial_capital:,.2f}`")
            with col2:
                color_adv = "🟢" if final_equity_adv >= initial_capital else "🔴"
                st.markdown(f"**最终资金 | Final Capital** {color_adv}\n\n`${final_equity_adv:,.2f}`")
            st.markdown(f"**收益**: `{final_equity_adv - initial_capital:+,.2f}` ({total_return_adv:+.2%})")
            st.divider()
            
            # 成本分析
            col_c1, col_c2, col_c3, col_c4 = st.columns(4)
            with col_c1:
                st.markdown(f"**总收益率**\n\n`{total_return_adv:.2%}`")
            with col_c2:
                st.markdown(f"**总佣金**\n\n`${total_commission:,.2f}`")
            with col_c3:
                st.markdown(f"**总冲击成本**\n\n`${total_impact:,.2f}`")
            with col_c4:
                st.markdown(f"**总成本**\n\n`${total_cost:,.2f}`")
            st.divider()
            
            # 提取买卖点：signal 从 0→非0 或 从 非0→0 的变化点（在过滤前）
            adv_signal = result['signal']
            adv_signal_shift = adv_signal.shift(1).fillna(0)
            # 买入点：signal 变为 1（从 0 或 -1 变为 1）
            buy_mask = (adv_signal == 1) & (adv_signal_shift != 1)
            # 卖出点：signal 变为 -1 或 0（从 1 变为 非1）
            sell_mask = (adv_signal != 1) & (adv_signal_shift == 1)
            
            adv_buy_points = result[buy_mask]
            adv_sell_points = result[sell_mask]
            
            # ⏰ 高级模式：回测结果的时间范围选择工具栏
            adv_start_date = result.index.min().date() if isinstance(result.index.min(), pd.Timestamp) else result.index.min()
            adv_end_date = result.index.max().date() if isinstance(result.index.max(), pd.Timestamp) else result.index.max()
            
            # 初始化高级模式的时间范围选择变量
            if 'selected_adv_start_date' not in st.session_state:
                st.session_state.selected_adv_start_date = adv_start_date
            if 'selected_adv_end_date' not in st.session_state:
                st.session_state.selected_adv_end_date = adv_end_date
            
            st.markdown("**⏰ 调整图表时间范围 | Adjust Chart Time Range**")
            col_adv1, col_adv2, col_adv3, col_adv4, col_adv5, col_adv6, col_adv7, col_adv8 = st.columns(8)
            
            def update_adv_range(start_offset_days, end_offset_days=0):
                """更新高级模式回测结果显示的日期范围"""
                end_date = adv_end_date - timedelta(days=end_offset_days) if end_offset_days > 0 else adv_end_date
                start_date = end_date - timedelta(days=start_offset_days)
                
                # 确保不超出数据范围
                start_date = max(start_date, adv_start_date)
                end_date = min(end_date, adv_end_date)
                
                if start_date < end_date:
                    st.session_state.selected_adv_start_date = start_date
                    st.session_state.selected_adv_end_date = end_date
                    st.rerun()
            
            with col_adv1:
                if st.button("1D", width="stretch", key="adv_1d"):
                    update_adv_range(1)
            
            with col_adv2:
                if st.button("1W", width="stretch", key="adv_1w"):
                    update_adv_range(7)
            
            with col_adv3:
                if st.button("1M", width="stretch", key="adv_1m"):
                    update_adv_range(30)
            
            with col_adv4:
                if st.button("3M", width="stretch", key="adv_3m"):
                    update_adv_range(90)
            
            with col_adv5:
                if st.button("6M", width="stretch", key="adv_6m"):
                    update_adv_range(180)
            
            with col_adv6:
                if st.button("1Y", width="stretch", key="adv_1y"):
                    update_adv_range(365)
            
            with col_adv7:
                if st.button("All", width="stretch", key="adv_all"):
                    st.session_state.selected_adv_start_date = adv_start_date
                    st.session_state.selected_adv_end_date = adv_end_date
                    st.rerun()
            
            with col_adv8:
                adv_start_display = st.session_state.selected_adv_start_date
                adv_end_display = st.session_state.selected_adv_end_date
                st.markdown(f"**📅 {adv_start_display} ~ {adv_end_display}**")
            
            # 根据选择的范围过滤高级模式数据
            adv_start_ts = pd.Timestamp(st.session_state.selected_adv_start_date)
            adv_end_ts = pd.Timestamp(st.session_state.selected_adv_end_date)
            mask_adv = (result.index >= adv_start_ts) & (result.index <= adv_end_ts)
            result_filtered = result[mask_adv]
            
            # 对买卖点使用独立的时间范围过滤
            adv_buy_points_filtered = adv_buy_points.loc[(adv_buy_points.index >= adv_start_ts) & (adv_buy_points.index <= adv_end_ts)]
            adv_sell_points_filtered = adv_sell_points.loc[(adv_sell_points.index >= adv_start_ts) & (adv_sell_points.index <= adv_end_ts)]
            
            # ====== 第一幅图：股票价格走势图（K线 + 买卖点）======
            with st.container():
                st.subheader("📈 股票价格走势 | Stock Price Trend")
                
                fig_adv_candle = go.Figure()
                
                # K线图
                if all(c in result_filtered.columns for c in ['open', 'high', 'low', 'close']):
                    fig_adv_candle.add_trace(go.Candlestick(
                        x=result_filtered.index,
                        open=result_filtered['open'],
                        high=result_filtered['high'],
                        low=result_filtered['low'],
                        close=result_filtered['close'],
                        name='K线 | Candlestick'
                    ))
                
                # 标记买点（红色大星号）
                if not adv_buy_points_filtered.empty:
                    fig_adv_candle.add_trace(go.Scatter(
                        x=adv_buy_points_filtered.index,
                        y=adv_buy_points_filtered['close'],
                        mode='markers+text',
                        name='买点 | BUY',
                        marker=dict(color='red', size=16, symbol='star', line=dict(color='darkred', width=2)),
                        text=[f"BUY<br>${p:.2f}" for p in adv_buy_points_filtered['close']],
                        textposition='bottom center',
                        textfont=dict(color='red', size=10, family='Arial Black'),
                        showlegend=True,
                        hovertemplate='<b>🟢 BUY</b><br>Price: $%{y:.2f}<br>Date: %{x|%Y-%m-%d}<extra></extra>'
                    ))
                
                # 标记卖点（绿色大星号）
                if not adv_sell_points_filtered.empty:
                    fig_adv_candle.add_trace(go.Scatter(
                        x=adv_sell_points_filtered.index,
                        y=adv_sell_points_filtered['close'],
                        mode='markers+text',
                        name='卖点 | SELL',
                        marker=dict(color='lime', size=16, symbol='star', line=dict(color='darkgreen', width=2)),
                        text=[f"SELL<br>${p:.2f}" for p in adv_sell_points_filtered['close']],
                        textposition='top center',
                        textfont=dict(color='lime', size=10, family='Arial Black'),
                        showlegend=True,
                        hovertemplate='<b>🔴 SELL</b><br>Price: $%{y:.2f}<br>Date: %{x|%Y-%m-%d}<extra></extra>'
                    ))
                
                fig_adv_candle.update_layout(
                    template="plotly_dark",
                    height=600,
                    margin=dict(l=80, r=20, t=60, b=50),
                    xaxis_title="日期 | Date",
                    yaxis_title="价格 (USD) | Price",
                    hovermode='x unified',
                    title=f"📊 {strategy.name} - 高级模式 | {symbol}",
                    font=dict(size=10),
                    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, font=dict(size=9))
                )
                fig_adv_candle.update_xaxes(rangeslider_visible=False, rangebreaks=[dict(bounds=["sat", "mon"])])
                
                st.plotly_chart(fig_adv_candle, width="stretch")
            
            st.divider()
            
            # ====== 第二幅图：资金曲线（含买卖点）======
            with st.container():
                st.subheader("📈 资金曲线 | Equity Curve")
                fig_adv = go.Figure()
                fig_adv.add_trace(go.Scatter(
                    x=result_filtered.index,
                    y=result_filtered['equity'],
                    mode='lines',
                    name='账户净值 | Equity',
                    line=dict(color='#00D9FF', width=2)
                ))
                
                # 买卖点标记在净值曲线上
                if not adv_buy_points_filtered.empty:
                    fig_adv.add_trace(go.Scatter(
                        x=adv_buy_points_filtered.index,
                        y=adv_buy_points_filtered['equity'],
                        mode='markers+text',
                        name='买点 (BUY)',
                        marker=dict(color='red', size=12, symbol='star'),
                        text=['BUY'] * len(adv_buy_points_filtered),
                        textposition='top center',
                        textfont=dict(color='red', size=10),
                        showlegend=True
                    ))
                
                if not adv_sell_points_filtered.empty:
                    fig_adv.add_trace(go.Scatter(
                        x=adv_sell_points_filtered.index,
                        y=adv_sell_points_filtered['equity'],
                        mode='markers+text',
                        name='卖点 (SELL)',
                        marker=dict(color='green', size=12, symbol='star'),
                        text=['SELL'] * len(adv_sell_points_filtered),
                        textposition='top center',
                        textfont=dict(color='green', size=10),
                        showlegend=True
                    ))
                
                fig_adv.update_layout(
                    template="plotly_dark",
                    height=500,
                    margin=dict(l=80, r=20, t=50, b=50),
                    xaxis_title="日期 | Date",
                    yaxis_title="净值 (USD) | Equity",
                    title="📈 高级模式 - 资金曲线 | Advanced Mode Equity Curve",
                    hovermode='x unified'
                )
                st.plotly_chart(fig_adv, width="stretch")
            
            st.divider()
            
            # 显示交易详情
            if 'signal' in result.columns:
                trades_df = result[result['signal'] != 0].copy()
                if not trades_df.empty:
                    display_cols_adv = [c for c in ['close', 'signal', 'equity', 'commission_cost', 'market_impact_cost', 'trade_log'] if c in trades_df.columns]
                    display_trades = trades_df[display_cols_adv].copy()
                    
                    for col in ['close', 'commission_cost', 'market_impact_cost', 'equity']:
                        if col in display_trades.columns:
                            display_trades[col] = display_trades[col].apply(lambda x: f"${x:.2f}" if isinstance(x, (int, float)) else x)
                    
                    st.subheader("📋 交易详情 | Trades")
                    st.dataframe(display_trades, width="stretch", height=300)
    
    else:
        # ===== 简单模式结果显示 =====
        
        # 🧠 显示最佳策略记忆
        best_strategy = get_best_strategy(symbol)
        if best_strategy:
            best_col1, best_col2, best_col3 = st.columns([1, 3, 1])
            with best_col1:
                st.metric("💾 最佳策略 | Best", best_strategy['strategy'][:20])
            with best_col2:
                st.caption(f"年化收益 | Annual Return: **{best_strategy['annual_return']:.2%}** | 更新于 | Updated: {best_strategy['updated_at'][:10]}")
            with best_col3:
                if st.button("📌 加载此配置 | Load", key="load_best_config", width="stretch"):
                    st.success(f"✅ 已加载最佳配置 | Best Config Loaded!")
                    st.info(f"参数 | Params：{best_strategy['params']}")
            st.divider()
        
        # 初始资金和最终资金 - 改用 markdown 避免省略号
        final_equity = result.equity_curve.iloc[-1] if len(result.equity_curve) > 0 else initial_capital
        profit = final_equity - initial_capital
        profit_pct = profit / initial_capital * 100 if initial_capital != 0 else 0
        
        st.subheader("💰 资金变化 | Capital")
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.markdown(f"**初始资金**\n\n`${initial_capital:,.2f}`")
        with col_info2:
            color = "🟢" if profit >= 0 else "🔴"
            st.markdown(f"**最终资金** {color}\n\n`${final_equity:,.2f}`")
        
        st.markdown(f"**收益**: `{profit:+,.2f}` ({profit_pct:+.2f}%)")
        st.divider()
        
        # 核心指标 - 改用 markdown 避免省略号
        st.subheader("📊 关键指标 | Key Metrics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            ret = result.metrics.get('total_return', 0)
            st.markdown(f"**总收益率**\n\n`{ret:.2%}`")
        with col2:
            sharpe = result.metrics.get('sharpe_ratio', 0)
            st.markdown(f"**夏普比率**\n\n`{sharpe:.2f}`")
        with col3:
            drawdown = result.metrics.get('max_drawdown', 0)
            st.markdown(f"**最大回撤**\n\n`{drawdown:.2%}`")
        with col4:
            trades = int(result.metrics.get('num_trades', 0))
            st.markdown(f"**交易次数**\n\n`{trades}`")
        
        col5, col6 = st.columns(2)
        with col5:
            win_rate = result.metrics.get('win_rate', 0)
            st.markdown(f"**胜率**\n\n`{win_rate:.2%}`")
        with col6:
            annual_return = result.metrics.get('annual_return', 0)
            st.markdown(f"**年化收益**\n\n`{annual_return:.2%}`")
    
        # --- 基准对比指标 ---
        st.divider()
        st.subheader(f"📊 与基准指数对比 | Benchmark Comparison ({symbol})")

        # 计算基准收益率 - 改用 markdown 避免省略号
        strategy_return = result.metrics.get('total_return', 0)

        col_b1, col_b2, col_b3 = st.columns(3)

        with col_b1:
            st.markdown(f"**策略收益率**\n\n`{strategy_return:.2%}`")

        # Nasdaq 收益率
        if result.benchmark_nasdaq is not None and not result.benchmark_nasdaq.empty:
            nasdaq_return = (result.benchmark_nasdaq.iloc[-1] / result.config.initial_capital) - 1
            outperform = strategy_return - nasdaq_return
            color = "🟢" if outperform >= 0 else "🔴"
            with col_b2:
                st.markdown(f"**Nasdaq收益** {color}\n\n`{nasdaq_return:.2%}`\n\n超额: `{outperform:+.2%}`")
        else:
            with col_b2:
                st.markdown(f"**Nasdaq收益**\n\n`N/A`")

        # S&P 500 收益率
        if result.benchmark_sp500 is not None and not result.benchmark_sp500.empty:
            sp500_return = (result.benchmark_sp500.iloc[-1] / result.config.initial_capital) - 1
            outperform_sp = strategy_return - sp500_return
            color_sp = "🟢" if outperform_sp >= 0 else "🔴"
            with col_b3:
                st.markdown(f"**S&P500收益** {color_sp}\n\n`{sp500_return:.2%}`\n\n超额: `{outperform_sp:+.2%}`")
        else:
            with col_b3:
                st.markdown(f"**S&P500收益**\n\n`N/A`")
        # --- 双图表展示：股票价格 + 账户净值 ---
        st.subheader(f"📊 回测图表 | Backtest Charts ({symbol})")

        # 准备买卖点数据
        buy_trades = result.trades[result.trades['action'] == 'BUY'] if not result.trades.empty else pd.DataFrame()
        sell_trades = result.trades[result.trades['action'] == 'SELL'] if not result.trades.empty else pd.DataFrame()

        # 获取回测结果的时间范围（用于初始化）
        backtest_earliest = result.equity_curve.index.min().date() if isinstance(result.equity_curve.index.min(), pd.Timestamp) else result.equity_curve.index.min()
        backtest_latest = result.equity_curve.index.max().date() if isinstance(result.equity_curve.index.max(), pd.Timestamp) else result.equity_curve.index.max()

        # 如果尚未设置回测时间范围，初始化为全数据范围
        if not st.session_state.selected_backtest_start_date:
            st.session_state.selected_backtest_start_date = backtest_earliest
        if not st.session_state.selected_backtest_end_date:
            st.session_state.selected_backtest_end_date = backtest_latest

        # ⏰ 回测结果的时间范围选择工具栏（控制两张图的显示范围）
        st.markdown("**⏰ 调整图表时间范围 | Adjust Chart Time Range**")
        col_bt1, col_bt2, col_bt3, col_bt4, col_bt5, col_bt6, col_bt7, col_bt8 = st.columns(8)
        
        def update_backtest_range(start_offset_days, end_offset_days=0):
            """更新回测结果显示的日期范围"""
            end_date = backtest_latest - timedelta(days=end_offset_days) if end_offset_days > 0 else backtest_latest
            start_date = end_date - timedelta(days=start_offset_days)
            
            # 确保不超出数据范围
            start_date = max(start_date, backtest_earliest)
            end_date = min(end_date, backtest_latest)
            
            if start_date < end_date:
                st.session_state.selected_backtest_start_date = start_date
                st.session_state.selected_backtest_end_date = end_date
                st.rerun()
        
        with col_bt1:
            if st.button("1D", width="stretch", key="backtest_1d"):
                update_backtest_range(1)
        
        with col_bt2:
            if st.button("1W", width="stretch", key="backtest_1w"):
                update_backtest_range(7)
        
        with col_bt3:
            if st.button("1M", width="stretch", key="backtest_1m"):
                update_backtest_range(30)
        
        with col_bt4:
            if st.button("3M", width="stretch", key="backtest_3m"):
                update_backtest_range(90)
        
        with col_bt5:
            if st.button("6M", width="stretch", key="backtest_6m"):
                update_backtest_range(180)
        
        with col_bt6:
            if st.button("1Y", width="stretch", key="backtest_1y"):
                update_backtest_range(365)
        
        with col_bt7:
            if st.button("All", width="stretch", key="backtest_all"):
                st.session_state.selected_backtest_start_date = backtest_earliest
                st.session_state.selected_backtest_end_date = backtest_latest
                st.rerun()
        
        with col_bt8:
            # 显示当前回测图的时间范围
            backtest_start_display = st.session_state.selected_backtest_start_date
            backtest_end_display = st.session_state.selected_backtest_end_date
            st.markdown(f"**📅 {backtest_start_display} ~ {backtest_end_display}**")

        # 根据选择的范围过滤数据
        backtest_start = pd.Timestamp(st.session_state.selected_backtest_start_date)
        backtest_end = pd.Timestamp(st.session_state.selected_backtest_end_date)
        
        # 过滤 result.raw_data
        mask_raw = (result.raw_data.index >= backtest_start) & (result.raw_data.index <= backtest_end)
        
        # 过滤 equity_curve, benchmark 等
        mask_eq = (result.equity_curve.index >= backtest_start) & (result.equity_curve.index <= backtest_end)

        # ====== 第一幅图：股票价格 K 线（含买卖点和策略参考线）======
        with st.container():
            st.subheader("📈 股票价格走势 | Stock Price Trend")

            # 准备价格数据（根据时间范围过滤）
            price_data = result.raw_data[['open', 'high', 'low', 'close', 'volume']].copy()
            price_data = price_data[mask_raw]

            fig_candle = go.Figure()

            # K线
            fig_candle.add_trace(go.Candlestick(
                x=price_data.index,
                open=price_data['open'],
                high=price_data['high'],
                low=price_data['low'],
                close=price_data['close'],
                name='K线 | Candlestick'
            ))

            # 根据策略类型添加参考线
            strategy_name = strategy.name

            # 1️⃣ 布林带策略 - 添加上中下轨
            if strategy_name == "布林带交易策略":
                if 'upper_band' in result.raw_data.columns:
                    fig_candle.add_trace(go.Scatter(
                        x=result.raw_data[mask_raw].index,
                        y=result.raw_data[mask_raw]['upper_band'],
                        mode='lines',
                        name='上轨 | Upper Band',
                        line=dict(color='rgba(255,0,0,0.5)', width=1, dash='dash'),
                        hovertemplate='%{y:.2f}<extra></extra>'
                    ))

                if 'sma' in result.raw_data.columns:
                    fig_candle.add_trace(go.Scatter(
                        x=result.raw_data[mask_raw].index,
                        y=result.raw_data[mask_raw]['sma'],
                        mode='lines',
                        name='中轨 | Middle Band',
                        line=dict(color='rgba(255,255,0,0.7)', width=1.5, dash='solid'),
                        hovertemplate='%{y:.2f}<extra></extra>'
                    ))

                if 'lower_band' in result.raw_data.columns:
                    fig_candle.add_trace(go.Scatter(
                        x=result.raw_data[mask_raw].index,
                        y=result.raw_data[mask_raw]['lower_band'],
                        mode='lines',
                        name='下轨 | Lower Band',
                        line=dict(color='rgba(0,255,0,0.5)', width=1, dash='dash'),
                        hovertemplate='%{y:.2f}<extra></extra>'
                    ))

            # 2️⃣ 均线交叉策略 - 添加短期和长期均线
            elif strategy_name == "均线交叉策略":
                if 'sma_short' in result.raw_data.columns:
                    fig_candle.add_trace(go.Scatter(
                        x=result.raw_data[mask_raw].index,
                        y=result.raw_data[mask_raw]['sma_short'],
                        mode='lines',
                        name='短期均线 | Short MA',
                        line=dict(color='rgba(255,100,100,0.8)', width=1.5),
                        hovertemplate='%{y:.2f}<extra></extra>'
                    ))

                if 'sma_long' in result.raw_data.columns:
                    fig_candle.add_trace(go.Scatter(
                        x=result.raw_data[mask_raw].index,
                        y=result.raw_data[mask_raw]['sma_long'],
                        mode='lines',
                        name='长期均线 | Long MA',
                        line=dict(color='rgba(100,100,255,0.8)', width=1.5),
                        hovertemplate='%{y:.2f}<extra></extra>'
                    ))

            # 3️⃣ 分歧交易策略 - 添加趋势均线
            elif strategy_name == "分歧交易策略（改进版）":
                if 'trend_ma' in result.raw_data.columns:
                    fig_candle.add_trace(go.Scatter(
                        x=result.raw_data[mask_raw].index,
                        y=result.raw_data[mask_raw]['trend_ma'],
                        mode='lines',
                        name='趋势均线 | Trend MA',
                        line=dict(color='rgba(200,150,255,0.8)', width=1.5),
                        hovertemplate='%{y:.2f}<extra></extra>'
                    ))

            # 标记买点（红色大星号，显示价格）
            if not buy_trades.empty:
                # 根据回测结果时间范围过滤买点
                mask_buy = (buy_trades['date'] >= backtest_start) & (buy_trades['date'] <= backtest_end)
                buy_trades_filtered = buy_trades[mask_buy]
                
                fig_candle.add_trace(go.Scatter(
                    x=buy_trades_filtered['date'],
                    y=buy_trades_filtered['price'],
                    mode='markers+text',
                    name='买点 | BUY',
                    marker=dict(color='red', size=16, symbol='star', line=dict(color='darkred', width=2)),
                    text=[f"BUY<br>${price:.2f}" for price in buy_trades_filtered['price']],
                    textposition='bottom center',
                    textfont=dict(color='red', size=10, family='Arial Black'),
                    showlegend=True,
                    hovertemplate='<b>🟢 BUY SIGNAL</b><br>Price: $%{y:.2f}<br>Date: %{x|%Y-%m-%d}<extra></extra>'
                ))

            # 标记卖点（绿色大星号，显示价格）
            if not sell_trades.empty:
                # 根据回测结果时间范围过滤卖点
                mask_sell = (sell_trades['date'] >= backtest_start) & (sell_trades['date'] <= backtest_end)
                sell_trades_filtered = sell_trades[mask_sell]
                
                fig_candle.add_trace(go.Scatter(
                    x=sell_trades_filtered['date'],
                    y=sell_trades_filtered['price'],
                    mode='markers+text',
                    name='卖点 | SELL',
                    marker=dict(color='lime', size=16, symbol='star', line=dict(color='darkgreen', width=2)),
                    text=[f"SELL<br>${price:.2f}" for price in sell_trades_filtered['price']],
                    textposition='top center',
                    textfont=dict(color='lime', size=10, family='Arial Black'),
                    showlegend=True,
                    hovertemplate='<b>🔴 SELL SIGNAL</b><br>Price: $%{y:.2f}<br>Date: %{x|%Y-%m-%d}<extra></extra>'
                ))

            fig_candle.update_layout(
                template="plotly_dark",
                height=600,
                margin=dict(l=80, r=20, t=60, b=50),
                xaxis_title="日期 | Date",
                yaxis_title="价格 (USD) | Price (USD)",
                hovermode='x unified',
                title=f"📊 {strategy_name} | {symbol}",
                font=dict(size=10),
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, font=dict(size=9))
            )
            fig_candle.update_xaxes(rangeslider_visible=False, rangebreaks=[dict(bounds=["sat", "mon"])])

            st.plotly_chart(fig_candle, width="stretch")

        st.divider()

        # ====== 第二幅图：账户净值曲线（含买卖点 + 基准对比）======
        with st.container():
            st.subheader(f"💹 账户净值曲线 | Account Equity Curve ({symbol})")

            fig_equity = go.Figure()

            # 策略净值线（根据时间范围过滤）
            fig_equity.add_trace(go.Scatter(
                x=result.equity_curve[mask_eq].index,
                y=result.equity_curve[mask_eq],
                mode='lines',
                name='策略净值',
                line=dict(color='#00D9FF', width=2)
            ))

            # 基准对比线：Nasdaq
            if result.benchmark_nasdaq is not None and not result.benchmark_nasdaq.empty:
                mask_nasdaq = (result.benchmark_nasdaq.index >= backtest_start) & (result.benchmark_nasdaq.index <= backtest_end)
                fig_equity.add_trace(go.Scatter(
                    x=result.benchmark_nasdaq[mask_nasdaq].index,
                    y=result.benchmark_nasdaq[mask_nasdaq],
                    mode='lines',
                    name='Nasdaq 基准 (^IXIC)',
                    line=dict(color='#FFA500', width=1.5, dash='dash')
                ))

            # 基准对比线：S&P 500
            if result.benchmark_sp500 is not None and not result.benchmark_sp500.empty:
                mask_sp500 = (result.benchmark_sp500.index >= backtest_start) & (result.benchmark_sp500.index <= backtest_end)
                fig_equity.add_trace(go.Scatter(
                    x=result.benchmark_sp500[mask_sp500].index,
                    y=result.benchmark_sp500[mask_sp500],
                    mode='lines',
                    name='S&P 500 基准 (^GSPC)',
                    line=dict(color='#00FF00', width=1.5, dash='dot')
                ))

            # 标记买点（红色星型）
            if not buy_trades.empty:
                # 根据回测时间范围过滤买点
                mask_buy_equity = (buy_trades['date'] >= backtest_start) & (buy_trades['date'] <= backtest_end)
                buy_trades_filtered_equity = buy_trades[mask_buy_equity]
                
                buy_equity_values = []
                valid_dates = []
                for buy_date in buy_trades_filtered_equity['date']:
                    if buy_date in result.equity_curve.index:
                        buy_equity_values.append(result.equity_curve[buy_date])
                        valid_dates.append(buy_date)

                if buy_equity_values:
                    fig_equity.add_trace(go.Scatter(
                        x=valid_dates,
                        y=buy_equity_values,
                        mode='markers+text',
                        name='买点 (BUY)',
                        marker=dict(color='red', size=12, symbol='star'),
                        text=['BUY'] * len(buy_equity_values),
                        textposition='top center',
                        textfont=dict(color='red', size=10),
                        showlegend=True
                    ))

            # 标记卖点（绿色星型）
            if not sell_trades.empty:
                # 根据回测时间范围过滤卖点
                mask_sell_equity = (sell_trades['date'] >= backtest_start) & (sell_trades['date'] <= backtest_end)
                sell_trades_filtered_equity = sell_trades[mask_sell_equity]
                
                sell_equity_values = []
                valid_dates = []
                for sell_date in sell_trades_filtered_equity['date']:
                    if sell_date in result.equity_curve.index:
                        sell_equity_values.append(result.equity_curve[sell_date])
                        valid_dates.append(sell_date)

                if sell_equity_values:
                    fig_equity.add_trace(go.Scatter(
                        x=valid_dates,
                        y=sell_equity_values,
                        mode='markers+text',
                        name='卖点 (SELL)',
                        marker=dict(color='green', size=12, symbol='star'),
                        text=['SELL'] * len(sell_equity_values),
                        textposition='top center',
                        textfont=dict(color='green', size=10),
                        showlegend=True
                    ))

            fig_equity.update_layout(
                template="plotly_dark",
                height=500,
                margin=dict(l=80, r=20, t=50, b=50),
                xaxis_title="日期 | Date",
                yaxis_title="账户净值 (USD) | Account Equity",
                hovermode='x unified',
                title=f"💹 账户净值曲线 | Account Equity Curve ({symbol})",
                legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99),
                font=dict(size=10)
            )
            fig_equity.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])

            st.plotly_chart(fig_equity, width="stretch")

        # --- 交易记录表 ---
        st.subheader(f"📋 交易记录 | Trades ({symbol})")
        if not result.trades.empty:
            # 按时间倒序显示（最新的交易在最上面）
            trades_sorted = result.trades.iloc[::-1]
            st.dataframe(trades_sorted, width="stretch")
        else:
            st.info("暂无交易记录 | No trades yet")

        # --- 原始信号数据 ---
        if st.checkbox(f"显示原始回测数据 | Show Raw Backtest Data ({symbol})"):
            # 根据不同策略显示不同的列
            base_cols = ['open', 'high', 'low', 'close', 'volume', 'signal', 'returns']

            if strategy.name == "均线交叉策略":
                display_cols = base_cols + ['sma_short', 'sma_long']
            elif strategy.name == "分歧交易策略（改进版）":
                display_cols = base_cols + ['trend_ma', 'high_low']
            elif strategy.name == "布林带交易策略":
                display_cols = base_cols + ['sma', 'lower_band', 'upper_band']
            elif strategy.name == "周期性趋势交易策略":
                display_cols = base_cols + [col for col in ['atr'] if col in result.raw_data.columns]
            elif strategy.name == "周期性均值回归策略":
                display_cols = base_cols  # 此策略无特殊中间列
            elif strategy.name == "周期相位对齐策略":
                display_cols = base_cols  # 此策略无特殊中间列
            elif strategy.name == "均值回归波动率策略":
                display_cols = base_cols + [col for col in ['ma', 'zscore', 'volume_ratio'] if col in result.raw_data.columns]
            else:
                display_cols = base_cols

            # 仅显示存在的列
            available_cols = [col for col in display_cols if col in result.raw_data.columns]
            display_data = result.raw_data[available_cols].tail(100)
            # 按时间倒序显示（最新的数据在最上面）
            display_data = display_data.iloc[::-1]
            st.dataframe(display_data, width="stretch")

else:
    # 默认页面：显示数据预览和最简单的走势
    st.header(f"📊 数据预览 | Data Preview ({symbol})")
    st.info("👈 请在左侧侧边栏配置回测参数，然后点击「▶️ 运行回测」 | Configure parameters on the left and click \"▶️ Run Backtest\"")
    
    # 加载并显示原始数据的K线图
    try:
        file_path = os.path.join(storage_dir, f"{symbol}.parquet")
        df = pd.read_parquet(file_path)
        
        # 取最最近的 500 天数据用于预览
        df_preview = df.tail(500)
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                           vertical_spacing=0.05,
                           subplot_titles=(f'{symbol} 历史走势 | Historical Trend', '成交量 | Volume'),
                           row_heights=[0.7, 0.3])
        
        # K线
        fig.add_trace(go.Candlestick(
            x=df_preview.index,
            open=df_preview['open'],
            high=df_preview['high'],
            low=df_preview['low'],
            close=df_preview['close'],
            name="K线 | Candlestick"
        ), row=1, col=1)
        
        # 成交量
        colors = ['red' if row['close'] < row['open'] else 'green' for _, row in df_preview.iterrows()]
        fig.add_trace(go.Bar(
            x=df_preview.index,
            y=df_preview['volume'],
            marker_color=colors,
            name="成交量 | Volume"
        ), row=2, col=1)
        
        fig.update_layout(
            height=600,
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            font=dict(size=10)
        )
        fig.update_xaxes(title_text="日期 | Date", row=2, col=1)
        fig.update_yaxes(title_text="价格 (USD) | Price", row=1, col=1)
        fig.update_yaxes(title_text="成交量 | Volume", row=2, col=1)
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
        
        st.plotly_chart(fig, width="stretch")
        
    except Exception as e:
        st.warning(f"数据加载失败 | Data Loading Failed: {e}")
