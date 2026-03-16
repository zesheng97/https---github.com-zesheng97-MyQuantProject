"""
文件位置: GUI_Client/app_v2.py
描述: 完整的参数化回测 GUI（集成 BacktestEngine）
功能: 支持自定义回测时间、资金、策略参数，显示关键指标和回测结果
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 确保项目根目录在 sys.path 中（必须在导入前执行）
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Strategy_Pool.strategies import STRATEGIES
from Engine_Matrix.backtest_engine import BacktestEngine, BacktestConfig
from Analytics.reporters.company_info_manager import CompanyInfoManager

# =========== 页面配置 ===========
st.set_page_config(page_title="Personal Quant Lab", layout="wide")
st.title("🔬 个人量化实验室 - 参数化回测系统")

# =========== 数据索引 ===========
storage_dir = os.path.join(os.path.dirname(__file__), '..', 'Data_Hub', 'storage')
try:
    available_files = [f for f in os.listdir(storage_dir) if f.endswith('.parquet')]
    available_symbols = sorted([f.split('.')[0] for f in available_files])
except FileNotFoundError:
    st.error("❌ 未找到存储目录，请确保已运行 main.py 下载数据。")
    st.stop()

# =========== 侧边栏：基本配置 ===========
st.sidebar.header("📊 基本配置")
symbol = st.sidebar.selectbox("选择标的 (Symbol)", available_symbols, index=0)

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
    
    # 当日交易数据
    col_open, col_change, col_change_pct = st.columns(3)
    with col_open:
        open_price = company_info.get('open_price', 'N/A')
        if isinstance(open_price, (int, float)):
            st.metric("开盘价", f"${open_price:.2f}")
        else:
            st.metric("开盘价", str(open_price))
    
    with col_change:
        day_change = company_info.get('day_change', 'N/A')
        if isinstance(day_change, (int, float)):
            change_color = "inverse" if day_change < 0 else "off"
            st.metric("涨跌", f"${day_change:.2f}", delta_color=change_color)
        else:
            st.metric("涨跌", str(day_change))
    
    with col_change_pct:
        day_change_pct = company_info.get('day_change_percent', 'N/A')
        if isinstance(day_change_pct, (int, float)):
            change_pct_color = "inverse" if day_change_pct < 0 else "off"
            st.metric("涨跌幅", f"{day_change_pct:.2f}%", delta_color=change_pct_color)
        else:
            st.metric("涨跌幅", str(day_change_pct))
    
    # 股票基本指标
    col_price1, col_price2, col_price3 = st.columns(3)
    with col_price1:
        st.metric("当前价格", f"${company_info.get('current_price', 'N/A')}")
    with col_price2:
        pe_ratio = company_info.get('pe_ratio', 'N/A')
        if isinstance(pe_ratio, (int, float)):
            pe_display = f"{pe_ratio:.1f}"
        else:
            pe_display = str(pe_ratio)
        st.metric("P/E 比率", pe_display)
    with col_price3:
        roe = company_info.get('roe', 'N/A')
        if isinstance(roe, (int, float)):
            roe_display = f"{roe*100:.1f}%"
        else:
            roe_display = str(roe)
        st.metric("ROE", roe_display)
    
    # 现金流指标
    fcf = company_info.get('fcf', 'N/A')
    if fcf and fcf != 'N/A':
        st.markdown(f"**自由现金流 (FCF)**: ${fcf:,.0f}")
    
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

st.sidebar.header("📅 回测时间")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input(
        "开始日期",
        value=datetime(2023, 1, 1),
        key="start_date_input"
    )
with col2:
    end_date = st.date_input(
        "结束日期",
        value=datetime.now(),
        key="end_date_input"
    )

# =========== 侧边栏：资金配置 ===========
st.sidebar.header("💰 资金配置")
initial_capital = st.sidebar.number_input(
    "初始资金 (USD)",
    value=30000.0,
    min_value=1000.0,
    step=10000.0,
    format="%.0f"
)

# =========== 侧边栏：策略选择 ===========
st.sidebar.header("🎯 策略选择")
strategy = st.sidebar.selectbox(
    "选择策略",
    STRATEGIES,
    format_func=lambda s: f"{s.name}"
)

# 显示策略说明
with st.sidebar.expander("📖 策略说明", expanded=False):
    st.markdown(f"**中文**: {strategy.description_cn}")
    st.markdown(f"**English**: {strategy.description_en}")

# =========== 侧边栏：策略参数 ===========
st.sidebar.header("⚙️ 策略参数")

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
else:
    st.sidebar.info("其他策略参数配置待实现")
    strategy_params = {}

# =========== 侧边栏：运行回测按钮 ===========
st.sidebar.header("🚀 执行")
run_backtest = st.sidebar.button("▶️ 运行回测", use_container_width=True)

# =========== 主区域：回测执行 ===========
if run_backtest:
    with st.spinner("⏳ 正在执行回测..."):
        try:
            # 创建回测配置
            config = BacktestConfig(
                symbol=symbol,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                initial_capital=initial_capital,
                strategy_params=strategy_params
            )
            
            # 执行回测
            engine = BacktestEngine(strategy, data_dir=storage_dir)
            result = engine.run(config)
            
            # 保存到会话状态（用于后续展示）
            st.session_state.backtest_result = result
            st.success("✅ 回测完成！")
            
        except Exception as e:
            st.error(f"❌ 回测失败: {str(e)}")
            st.session_state.backtest_result = None

# =========== 主区域：显示回测结果 ===========
if hasattr(st.session_state, 'backtest_result') and st.session_state.backtest_result:
    result = st.session_state.backtest_result
    
    # --- 关键指标卡片 ---
    st.header("📈 回测结果")
    
    # 初始资金和最终资金
    final_equity = result.equity_curve.iloc[-1] if len(result.equity_curve) > 0 else initial_capital
    
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.metric("初始资金", f"${initial_capital:,.2f}")
    with col_info2:
        st.metric(
            "最终资金",
            f"${final_equity:,.2f}",
            delta=f"${final_equity - initial_capital:+,.2f}"
        )
    st.divider()
    
    # 核心指标
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "总收益率",
            f"{result.metrics.get('total_return', 0):.2%}",
            delta=None
        )
    with col2:
        st.metric(
            "夏普比率",
            f"{result.metrics.get('sharpe_ratio', 0):.2f}",
            delta=None
        )
    with col3:
        st.metric(
            "最大回撤",
            f"{result.metrics.get('max_drawdown', 0):.2%}",
            delta=None
        )
    with col4:
        st.metric(
            "交易次数",
            f"{int(result.metrics.get('num_trades', 0))}",
            delta=None
        )
    
    col5, col6 = st.columns(2)
    with col5:
        st.metric(
            "胜率",
            f"{result.metrics.get('win_rate', 0):.2%}",
            delta=None
        )
    with col6:
        st.metric(
            "年化收益",
            f"{result.metrics.get('annual_return', 0):.2%}",
            delta=None
        )
    
    # --- 基准对比指标 ---
    st.divider()
    st.subheader("📊 与基准指数对比")
    
    # 计算基准收益率
    strategy_return = result.metrics.get('total_return', 0)
    
    benchmark_cols = st.columns(3)
    
    with benchmark_cols[0]:
        st.metric("策略收益率", f"{strategy_return:.2%}")
    
    # Nasdaq 收益率
    if result.benchmark_nasdaq is not None and not result.benchmark_nasdaq.empty:
        nasdaq_return = (result.benchmark_nasdaq.iloc[-1] - result.metrics.get('total_return', 0)) / result.config.initial_capital
        nasdaq_return = (result.benchmark_nasdaq.iloc[-1] / result.config.initial_capital) - 1
        with benchmark_cols[1]:
            st.metric(
                "Nasdaq 收益率",
                f"{nasdaq_return:.2%}",
                delta=f"{strategy_return - nasdaq_return:+.2%}",
                delta_color="inverse"
            )
    else:
        with benchmark_cols[1]:
            st.metric("Nasdaq 收益率", "N/A")
    
    # S&P 500 收益率
    if result.benchmark_sp500 is not None and not result.benchmark_sp500.empty:
        sp500_return = (result.benchmark_sp500.iloc[-1] / result.config.initial_capital) - 1
        with benchmark_cols[2]:
            st.metric(
                "S&P 500 收益率",
                f"{sp500_return:.2%}",
                delta=f"{strategy_return - sp500_return:+.2%}",
                delta_color="inverse"
            )
    else:
        with benchmark_cols[2]:
            st.metric("S&P 500 收益率", "N/A")
    # --- 双图表展示：账户净值 + 股票价格 ---
    st.subheader("📊 回测图表（买卖点标记）")
    
    # 准备买卖点数据
    buy_trades = result.trades[result.trades['action'] == 'BUY'] if not result.trades.empty else pd.DataFrame()
    sell_trades = result.trades[result.trades['action'] == 'SELL'] if not result.trades.empty else pd.DataFrame()
    
    # 上图：账户净值曲线（含买卖点 + 基准对比）
    fig_equity = go.Figure()
    
    # 策略净值线
    fig_equity.add_trace(go.Scatter(
        x=result.equity_curve.index,
        y=result.equity_curve,
        mode='lines',
        name='策略净值',
        line=dict(color='#00D9FF', width=2)
    ))
    
    # 基准对比线：Nasdaq
    if result.benchmark_nasdaq is not None and not result.benchmark_nasdaq.empty:
        fig_equity.add_trace(go.Scatter(
            x=result.benchmark_nasdaq.index,
            y=result.benchmark_nasdaq,
            mode='lines',
            name='Nasdaq 基准 (^IXIC)',
            line=dict(color='#FFA500', width=1.5, dash='dash')
        ))
    
    # 基准对比线：S&P 500
    if result.benchmark_sp500 is not None and not result.benchmark_sp500.empty:
        fig_equity.add_trace(go.Scatter(
            x=result.benchmark_sp500.index,
            y=result.benchmark_sp500,
            mode='lines',
            name='S&P 500 基准 (^GSPC)',
            line=dict(color='#00FF00', width=1.5, dash='dot')
        ))
    
    # 标记买点（红色星型）
    if not buy_trades.empty:
        buy_equity_values = []
        for buy_date in buy_trades['date']:
            if buy_date in result.equity_curve.index:
                buy_equity_values.append(result.equity_curve[buy_date])
        
        if buy_equity_values:
            fig_equity.add_trace(go.Scatter(
                x=buy_trades['date'],
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
        sell_equity_values = []
        for sell_date in sell_trades['date']:
            if sell_date in result.equity_curve.index:
                sell_equity_values.append(result.equity_curve[sell_date])
        
        if sell_equity_values:
            fig_equity.add_trace(go.Scatter(
                x=sell_trades['date'],
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
        xaxis_title="日期",
        yaxis_title="账户净值 (USD)",
        hovermode='x unified',
        title="💹 账户净值曲线（含基准对比）",
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
    )
    fig_equity.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    
    st.plotly_chart(fig_equity, use_container_width=True)
    
    # 下图：股票价格 K 线（含买卖点）
    st.subheader("📈 股票价格走势（含买卖点）")
    
    # 准备价格数据
    price_data = result.raw_data[['open', 'high', 'low', 'close', 'volume']].copy()
    
    fig_candle = go.Figure()
    
    # K线
    fig_candle.add_trace(go.Candlestick(
        x=price_data.index,
        open=price_data['open'],
        high=price_data['high'],
        low=price_data['low'],
        close=price_data['close'],
        name='K线'
    ))
    
    # 标记买点（红色向下箭头）
    if not buy_trades.empty:
        fig_candle.add_trace(go.Scatter(
            x=buy_trades['date'],
            y=buy_trades['price'],
            mode='markers+text',
            name='买点 (BUY)',
            marker=dict(color='red', size=12, symbol='arrow-up'),
            text=['BUY'] * len(buy_trades),
            textposition='bottom center',
            textfont=dict(color='red', size=10),
            showlegend=True
        ))
    
    # 标记卖点（绿色向下箭头）
    if not sell_trades.empty:
        fig_candle.add_trace(go.Scatter(
            x=sell_trades['date'],
            y=sell_trades['price'],
            mode='markers+text',
            name='卖点 (SELL)',
            marker=dict(color='green', size=12, symbol='arrow-down'),
            text=['SELL'] * len(sell_trades),
            textposition='top center',
            textfont=dict(color='green', size=10),
            showlegend=True
        ))
    
    fig_candle.update_layout(
        template="plotly_dark",
        height=500,
        xaxis_title="日期",
        yaxis_title="价格 (USD)",
        hovermode='x unified',
        title="📊 股票价格 K 线"
    )
    fig_candle.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    
    st.plotly_chart(fig_candle, use_container_width=True)
    
    # --- 交易记录表 ---
    st.subheader("📋 交易记录")
    if not result.trades.empty:
        st.dataframe(result.trades, use_container_width=True)
    else:
        st.info("暂无交易记录")
    
    # --- 原始信号数据 ---
    if st.checkbox("显示原始回测数据（最近100条）"):
        display_data = result.raw_data[['open', 'high', 'low', 'close', 'volume', 'sma_short', 'sma_long', 'signal', 'returns']].tail(100)
        st.dataframe(display_data, use_container_width=True)

else:
    # 默认页面：显示数据预览和最简单的走势
    st.header("📊 数据预览")
    st.info("👈 请在左侧侧边栏配置回测参数，然后点击「▶️ 运行回测」")
    
    # 加载并显示原始数据的K线图
    try:
        file_path = os.path.join(storage_dir, f"{symbol}.parquet")
        df = pd.read_parquet(file_path)
        
        # 取最最近的 500 天数据用于预览
        df_preview = df.tail(500)
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                           vertical_spacing=0.05,
                           subplot_titles=(f'{symbol} 历史走势', '成交量'),
                           row_heights=[0.7, 0.3])
        
        # K线
        fig.add_trace(go.Candlestick(
            x=df_preview.index,
            open=df_preview['open'],
            high=df_preview['high'],
            low=df_preview['low'],
            close=df_preview['close'],
            name="K线"
        ), row=1, col=1)
        
        # 成交量
        colors = ['red' if row['close'] < row['open'] else 'green' for _, row in df_preview.iterrows()]
        fig.add_trace(go.Bar(
            x=df_preview.index,
            y=df_preview['volume'],
            marker_color=colors,
            name="成交量"
        ), row=2, col=1)
        
        fig.update_layout(
            height=600,
            template="plotly_dark",
            xaxis_rangeslider_visible=False
        )
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.warning(f"数据加载失败: {e}")
