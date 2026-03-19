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
import yfinance as yf
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
    
    if new_symbol and st.sidebar.button("📥 下载并保存", key="download_new", use_container_width=True):
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

st.sidebar.header("📅 回测时间 | Backtest Period")

# 动态计算回测开始日期（基于上市日期）
default_start = datetime(2023, 1, 1)
ipo_date_str = company_info.get('ipo_date', 'N/A')

if ipo_date_str and ipo_date_str != 'N/A':
    try:
        ipo_date = datetime.strptime(ipo_date_str, '%Y-%m-%d')
        # 如果IPO日期晚于默认日期，使用IPO日期
        if ipo_date > default_start:
            default_start = ipo_date
            st.sidebar.info(f"ℹ️ {symbol} 上市于 {ipo_date_str}，已自动调整回测开始日期")
    except:
        pass

col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input(
        "开始日期",
        value=default_start,
        key="start_date_input"
    )
with col2:
    end_date = st.date_input(
        "结束日期",
        value=datetime.now(),
        key="end_date_input"
    )

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
    if st.sidebar.button("🔍 扫描Boll策略参数", key="scan_boll_params", use_container_width=True):
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

else:
    st.sidebar.info("⚠️ 此策略参数配置待实现")
    strategy_params = {}

# =========== 侧边栏：运行回测按钮 ===========
st.sidebar.header("🚀 执行 | Execute")
run_backtest = st.sidebar.button("▶️ 运行回测 | Run Backtest", use_container_width=True)

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
            
            # 🧠 更新记忆系统 - 如果年化收益率更高则保存
            annual_return = result.metrics.get('annual_return', -999)
            update_best_strategy(symbol, strategy.name, strategy_params, annual_return)
            
            st.success("✅ 回测完成！")
            
        except Exception as e:
            st.error(f"❌ 回测失败: {str(e)}")
            st.session_state.backtest_result = None

# =========== 主区域：显示回测结果 ===========
if hasattr(st.session_state, 'backtest_result') and st.session_state.backtest_result:
    result = st.session_state.backtest_result
    
    # --- 关键指标卡片 ---
    st.header("📈 回测结果")
    
    # 🧠 显示最佳策略记忆
    best_strategy = get_best_strategy(symbol)
    if best_strategy:
        best_col1, best_col2, best_col3 = st.columns([1, 3, 1])
        with best_col1:
            st.metric("💾 最佳策略 | Best", best_strategy['strategy'][:15])
        with best_col2:
            st.caption(f"年化收益 | Annual Return: **{best_strategy['annual_return']:.2%}** | 更新于 | Updated: {best_strategy['updated_at'][:10]}")
        with best_col3:
            if st.button("📌 加载此配置 | Load", key="load_best_config", use_container_width=True):
                # 直接应用最佳配置到参数
                st.success(f"✅ 已加载最佳配置 | Best Config Loaded!")
                st.info(f"参数 | Params：{best_strategy['params']}")
        st.divider()
    
    # 初始资金和最终资金
    final_equity = result.equity_curve.iloc[-1] if len(result.equity_curve) > 0 else initial_capital
    
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.metric("初始资金 | Initial Capital", f"${initial_capital:,.2f}")
    with col_info2:
        st.metric(
            "最终资金 | Final Capital",
            f"${final_equity:,.2f}",
            delta=f"${final_equity - initial_capital:+,.2f}"
        )
    st.divider()
    
    # 核心指标
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "总收益率 | Total Return",
            f"{result.metrics.get('total_return', 0):.2%}",
            delta=None
        )
    with col2:
        st.metric(
            "夏普比率 | Sharpe Ratio",
            f"{result.metrics.get('sharpe_ratio', 0):.2f}",
            delta=None
        )
    with col3:
        st.metric(
            "最大回撤 | Max Drawdown",
            f"{result.metrics.get('max_drawdown', 0):.2%}",
            delta=None
        )
    with col4:
        st.metric(
            "交易次数 | Num Trades",
            f"{int(result.metrics.get('num_trades', 0))}",
            delta=None
        )
    
    col5, col6 = st.columns(2)
    with col5:
        st.metric(
            "胜率 | Win Rate",
            f"{result.metrics.get('win_rate', 0):.2%}",
            delta=None
        )
    with col6:
        st.metric(
            "年化收益 | Annual Return",
            f"{result.metrics.get('annual_return', 0):.2%}",
            delta=None
        )
    
    # --- 基准对比指标 ---
    st.divider()
    st.subheader(f"📊 与基准指数对比 | Benchmark Comparison ({symbol})")
    
    # 计算基准收益率
    strategy_return = result.metrics.get('total_return', 0)
    
    benchmark_cols = st.columns(3)
    
    with benchmark_cols[0]:
        st.metric("策略收益率 | Strategy Return", f"{strategy_return:.2%}")
    
    # Nasdaq 收益率
    if result.benchmark_nasdaq is not None and not result.benchmark_nasdaq.empty:
        nasdaq_return = (result.benchmark_nasdaq.iloc[-1] - result.metrics.get('total_return', 0)) / result.config.initial_capital
        nasdaq_return = (result.benchmark_nasdaq.iloc[-1] / result.config.initial_capital) - 1
        with benchmark_cols[1]:
            st.metric(
                "Nasdaq 收益率 | Nasdaq Return",
                f"{nasdaq_return:.2%}",
                delta=f"{strategy_return - nasdaq_return:+.2%}",
                delta_color="inverse"
            )
    else:
        with benchmark_cols[1]:
            st.metric("Nasdaq 收益率 | Nasdaq Return", "N/A")
    
    # S&P 500 收益率
    if result.benchmark_sp500 is not None and not result.benchmark_sp500.empty:
        sp500_return = (result.benchmark_sp500.iloc[-1] / result.config.initial_capital) - 1
        with benchmark_cols[2]:
            st.metric(
                "S&P 500 收益率 | S&P 500 Return",
                f"{sp500_return:.2%}",
                delta=f"{strategy_return - sp500_return:+.2%}",
                delta_color="inverse"
            )
    else:
        with benchmark_cols[2]:
            st.metric("S&P 500 收益率 | S&P 500 Return", "N/A")
    # --- 双图表展示：账户净值 + 股票价格 ---
    st.subheader(f"📊 回测图表 | Backtest Charts ({symbol})")
    
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
        xaxis_title="日期 | Date",
        yaxis_title="账户净值 (USD) | Account Equity",
        hovermode='x unified',
        title=f"💹 账户净值曲线 | Account Equity Curve ({symbol})",
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99),
        font=dict(size=10)
    )
    fig_equity.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    
    st.plotly_chart(fig_equity, use_container_width=True)
    
    # 下图：股票价格 K 线（含买卖点和策略参考线）
    st.subheader("📈 股票价格走势 | Stock Price Trend")
    
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
        name='K线 | Candlestick'
    ))
    
    # 根据策略类型添加参考线
    strategy_name = strategy.name
    
    # 1️⃣ 布林带策略 - 添加上中下轨
    if strategy_name == "布林带交易策略":
        if 'upper_band' in result.raw_data.columns:
            fig_candle.add_trace(go.Scatter(
                x=result.raw_data.index,
                y=result.raw_data['upper_band'],
                mode='lines',
                name='上轨 | Upper Band',
                line=dict(color='rgba(255,0,0,0.5)', width=1, dash='dash'),
                hovertemplate='%{y:.2f}<extra></extra>'
            ))
        
        if 'sma' in result.raw_data.columns:
            fig_candle.add_trace(go.Scatter(
                x=result.raw_data.index,
                y=result.raw_data['sma'],
                mode='lines',
                name='中轨 | Middle Band',
                line=dict(color='rgba(255,255,0,0.7)', width=1.5, dash='solid'),
                hovertemplate='%{y:.2f}<extra></extra>'
            ))
        
        if 'lower_band' in result.raw_data.columns:
            fig_candle.add_trace(go.Scatter(
                x=result.raw_data.index,
                y=result.raw_data['lower_band'],
                mode='lines',
                name='下轨 | Lower Band',
                line=dict(color='rgba(0,255,0,0.5)', width=1, dash='dash'),
                hovertemplate='%{y:.2f}<extra></extra>'
            ))
    
    # 2️⃣ 均线交叉策略 - 添加短期和长期均线
    elif strategy_name == "均线交叉策略":
        if 'sma_short' in result.raw_data.columns:
            fig_candle.add_trace(go.Scatter(
                x=result.raw_data.index,
                y=result.raw_data['sma_short'],
                mode='lines',
                name='短期均线 | Short MA',
                line=dict(color='rgba(255,100,100,0.8)', width=1.5),
                hovertemplate='%{y:.2f}<extra></extra>'
            ))
        
        if 'sma_long' in result.raw_data.columns:
            fig_candle.add_trace(go.Scatter(
                x=result.raw_data.index,
                y=result.raw_data['sma_long'],
                mode='lines',
                name='长期均线 | Long MA',
                line=dict(color='rgba(100,100,255,0.8)', width=1.5),
                hovertemplate='%{y:.2f}<extra></extra>'
            ))
    
    # 3️⃣ 分歧交易策略 - 添加趋势均线
    elif strategy_name == "分歧交易策略（改进版）":
        if 'trend_ma' in result.raw_data.columns:
            fig_candle.add_trace(go.Scatter(
                x=result.raw_data.index,
                y=result.raw_data['trend_ma'],
                mode='lines',
                name='趋势均线 | Trend MA',
                line=dict(color='rgba(200,150,255,0.8)', width=1.5),
                hovertemplate='%{y:.2f}<extra></extra>'
            ))
    
    # 标记买点（红色大星号，显示价格）
    if not buy_trades.empty:
        fig_candle.add_trace(go.Scatter(
            x=buy_trades['date'],
            y=buy_trades['price'],
            mode='markers+text',
            name='买点 | BUY',
            marker=dict(color='red', size=16, symbol='star', line=dict(color='darkred', width=2)),
            text=[f"BUY<br>¥{price:.2f}" for price in buy_trades['price']],
            textposition='bottom center',
            textfont=dict(color='red', size=10, family='Arial Black'),
            showlegend=True,
            hovertemplate='<b>🟢 BUY SIGNAL</b><br>Price: ¥%{y:.2f}<br>Date: %{x|%Y-%m-%d}<extra></extra>'
        ))
    
    # 标记卖点（绿色大星号，显示价格）
    if not sell_trades.empty:
        fig_candle.add_trace(go.Scatter(
            x=sell_trades['date'],
            y=sell_trades['price'],
            mode='markers+text',
            name='卖点 | SELL',
            marker=dict(color='lime', size=16, symbol='star', line=dict(color='darkgreen', width=2)),
            text=[f"SELL<br>¥{price:.2f}" for price in sell_trades['price']],
            textposition='top center',
            textfont=dict(color='lime', size=10, family='Arial Black'),
            showlegend=True,
            hovertemplate='<b>🔴 SELL SIGNAL</b><br>Price: ¥%{y:.2f}<br>Date: %{x|%Y-%m-%d}<extra></extra>'
        ))
    
    fig_candle.update_layout(
        template="plotly_dark",
        height=500,
        xaxis_title="日期 | Date",
        yaxis_title="价格 (USD) | Price (USD)",
        hovermode='x unified',
        title=f"📊 {strategy_name} | {symbol}",
        font=dict(size=10),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, font=dict(size=9))
    )
    fig_candle.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    
    st.plotly_chart(fig_candle, use_container_width=True)
    
    # --- 交易记录表 ---
    st.subheader(f"📋 交易记录 | Trades ({symbol})")
    if not result.trades.empty:
        # 按时间倒序显示（最新的交易在最上面）
        trades_sorted = result.trades.iloc[::-1]
        st.dataframe(trades_sorted, use_container_width=True)
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
        else:
            display_cols = base_cols
        
        # 仅显示存在的列
        available_cols = [col for col in display_cols if col in result.raw_data.columns]
        display_data = result.raw_data[available_cols].tail(100)
        # 按时间倒序显示（最新的数据在最上面）
        display_data = display_data.iloc[::-1]
        st.dataframe(display_data, use_container_width=True)

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
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.warning(f"数据加载失败 | Data Loading Failed: {e}")
