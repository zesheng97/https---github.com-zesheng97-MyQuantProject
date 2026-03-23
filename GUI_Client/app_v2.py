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

# =========== 页面配置 ===========
st.set_page_config(page_title="Personal Quant Lab", layout="wide")
st.title("🔬 个人量化实验室 | Personal Quant Lab - Parameterized Backtest System")

# =========== 记忆系统（保存最好的策略配置） ===========
memory_file = os.path.join(os.path.dirname(__file__), '..', 'Data_Hub', 'storage', '.strategy_memory.json')

def load_memory():
    """加载策略记忆"""
    if os.path.exists(memory_file):
        try:
            with open(memory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_memory(memory):
    """保存策略记忆"""
    os.makedirs(os.path.dirname(memory_file), exist_ok=True)
    with open(memory_file, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

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

# =========== 数据索引 ===========
storage_dir = os.path.join(os.path.dirname(__file__), '..', 'Data_Hub', 'storage')
try:
    available_files = [f for f in os.listdir(storage_dir) if f.endswith('.parquet')]
    available_symbols = sorted([f.split('.')[0] for f in available_files])
except FileNotFoundError:
    st.error("❌ 未找到存储目录，请确保已运行 main.py 下载数据。")
    st.stop()

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
