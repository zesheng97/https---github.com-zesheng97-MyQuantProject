import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中（必须在导入前执行）
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Strategy_Pool.strategies import STRATEGIES

st.set_page_config(page_title="Personal Quant Lab", layout="wide")
st.title("🔬 个人量化实验室 - 数据观测台")

# --- 数据索引模块 ---
storage_dir = os.path.join(os.path.dirname(__file__), '..', 'Data_Hub', 'storage')
try:
    available_files = [f for f in os.listdir(storage_dir) if f.endswith('.parquet')]
    available_symbols = sorted([f.split('.')[0] for f in available_files])
except FileNotFoundError:
    st.error("❌ 未找到存储目录，请确保已运行 main.py 下载数据。")
    st.stop()

# --- 侧边栏控制 ---
st.sidebar.header("配置参数")
symbol = st.sidebar.selectbox("选择标的", available_symbols)
ma_short_val = st.sidebar.number_input("短期均线 (SMA)", value=20)
ma_long_val = st.sidebar.number_input("长期均线 (SMA)", value=60)

# --- 侧边栏策略选择 ---
st.sidebar.header("策略选择")
strategy = st.sidebar.selectbox(
    "选择策略 (Select Strategy)", 
    STRATEGIES,
    format_func=lambda s: f"{s.name} ({s.description_en})"
)

# --- 策略说明 ---
st.subheader("策略说明 (Strategy Description)")
st.write(f"**中文**: {strategy.description_cn}")
st.write(f"**English**: {strategy.description_en}")

# --- 加载与计算 ---
@st.cache_data # 缓存数据，切换参数时无需重复读取磁盘
def load_data(sym):
    path = os.path.join(storage_dir, f"{sym}.parquet")
    data = pd.read_parquet(path)
    # 计算均线
    data['sma_s'] = data['close'].rolling(ma_short_val).mean()
    data['sma_l'] = data['close'].rolling(ma_long_val).mean()
    # 计算日收益率
    data['returns'] = data['close'].pct_change()
    return data

df = load_data(symbol)

# --- 构建专业图表 (K线 + 成交量) ---
# 创建 2 行 1 列的子图，高度比例为 4:1
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.05, 
                    subplot_titles=(f'{symbol} 历史走势', '成交量'),
                    row_width=[0.2, 0.7])

# 1. 主图：K线
fig.add_trace(go.Candlestick(
    x=df.index, open=df['open'], high=df['high'],
    low=df['low'], close=df['close'], name="K线"
), row=1, col=1)

# 2. 主图：叠加均线
fig.add_trace(go.Scatter(x=df.index, y=df['sma_s'], line=dict(color='orange', width=1), name=f'SMA {ma_short_val}'), row=1, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['sma_l'], line=dict(color='cyan', width=1), name=f'SMA {ma_long_val}'), row=1, col=1)

# 3. 副图：成交量 (根据涨跌设置柱状图颜色)
colors = ['red' if row['close'] < row['open'] else 'green' for _, row in df.iterrows()]
fig.add_trace(go.Bar(x=df.index, y=df['volume'], marker_color=colors, name="成交量"), row=2, col=1)

# 布局美化
fig.update_layout(
    height=800,
    template="plotly_dark", # 深色模式更具极客感
    xaxis_rangeslider_visible=False,
    showlegend=True
)
# 针对金融数据的空隙处理（跳过周末）
fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])]) 

# --- 界面渲染 ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("最新价格", f"${df['close'].iloc[-1]:.2f}", f"{df['returns'].iloc[-1]*100:.2f}%")
with col2:
    st.metric("期间最大回撤", f"{((df['close'] / df['close'].cummax() - 1).min()*100):.2f}%")
with col3:
    st.metric("交易日数", len(df))

st.plotly_chart(fig, use_container_width=True)

if st.checkbox("显示原始数据"):
    st.write(df.tail(100))

# --- 策略回测 ---
st.subheader("回测结果 (Backtest Results)")
backtest_df = strategy.backtest(df.copy())
st.write(backtest_df.tail(100))

# --- 回测收益曲线 ---
st.subheader("收益曲线 (Cumulative Returns)")
backtest_df['cumulative_returns'] = (1 + backtest_df['returns']).cumprod()
st.line_chart(backtest_df['cumulative_returns'])