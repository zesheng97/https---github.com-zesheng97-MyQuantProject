# 快速开始 | Quick Start Guide

[中文](#中文) | [English](#english)

---

<a name="english"></a>

## Quick Start (English)

### Installation in 3 Steps

#### Step 1: Download and Install
```bash
# Clone the repository
git clone https://github.com/yourusername/personal-quant-lab.git
cd personal-quant-lab

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Step 2: Download Market Data (First Time Only)
```bash
# This downloads 48+ US stocks from Yahoo Finance
# Takes 2-5 minutes depending on your internet speed
python main.py

# Verify installation
python test_system.py
```

#### Step 3: Launch GUI
```bash
python run_gui.py
```

**That's it!** 🎉 Open http://localhost:8501 in your browser.

### Using the Web Interface

1. **Select a stock**: Choose from the dropdown (AAPL, MSFT, GOOGL, etc.)
2. **View company info**: Click the company card to expand details
3. **Set backtest parameters**:
   - Date range (start and end dates)
   - Initial capital (default: $30,000)
   - Strategy: Moving Average Crossover
   - Parameters: Short MA window & Long MA window
4. **Click "Run Backtest"**: Watch the results appear in real-time
5. **Analyze results**: View metrics, charts, and trade logs

### Common Commands

```bash
# Test the system
python test_system.py

# Test company info
python test_company_info.py

# Run GUI
python run_gui.py

# Download specific stock
python -c "from Data_Hub.fetchers.yf_downloader import YFinanceDownloader; \
    YFinanceDownloader().download_and_save('AAPL', '2020-01-01', '2025-12-31')"
```

### Troubleshooting

**"Module not found" error**
```bash
# Make sure you're in the project root directory
cd path/to/personal-quant-lab

# Reinstall dependencies
pip install -r requirements.txt
```

**Streamlit port already in use**
```bash
# Run on a different port
streamlit run GUI_Client/app_v2.py --server.port 8502
```

**Data not found error**
```bash
# Re-download the data
python main.py
```

### System Requirements

- Python 3.10 or later
- 2 GB RAM (4 GB recommended)
- 500 MB disk space
- Internet connection (for data download)

---

<a name="中文"></a>

## 快速开始 (中文)

### 三步安装

#### 第一步：下载并安装
```bash
# 克隆仓库
git clone https://github.com/yourusername/personal-quant-lab.git
cd personal-quant-lab

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows 系统：
venv\Scripts\activate
# macOS/Linux 系统：
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 第二步：下载市场数据（仅第一次需要）
```bash
# 从 Yahoo Finance 下载 48+ 只美股
# 根据网络速度，通常需要 2-5 分钟
python main.py

# 验证安装
python test_system.py
```

#### 第三步：启动 GUI
```bash
python run_gui.py
```

**完成！** 🎉 在浏览器中打开 http://localhost:8501

### 使用网页界面

1. **选择股票**：从下拉菜单选择（AAPL、MSFT、GOOGL 等）
2. **查看企业信息**：点击公司卡片展开详情
3. **设置回测参数**：
   - 日期范围（开始日期和结束日期）
   - 初始资金（默认：$30,000）
   - 策略：均线交叉
   - 参数：短期均线窗口 & 长期均线窗口
4. **点击"运行回测"**：实时查看结果
5. **分析结果**：查看指标、图表和交易日志

### 常用命令

```bash
# 测试系统
python test_system.py

# 测试企业信息
python test_company_info.py

# 运行 GUI
python run_gui.py

# 下载特定股票数据
python -c "from Data_Hub.fetchers.yf_downloader import YFinanceDownloader; \
    YFinanceDownloader().download_and_save('AAPL', '2020-01-01', '2025-12-31')"
```

### 常见问题排查

**"模块未找到"错误**
```bash
# 确保在项目根目录
cd path/to/personal-quant-lab

# 重新安装依赖
pip install -r requirements.txt
```

**Streamlit 端口已被占用**
```bash
# 在不同端口运行
streamlit run GUI_Client/app_v2.py --server.port 8502
```

**找不到数据错误**
```bash
# 重新下载数据
python main.py
```

### 系统要求

- Python 3.10 及以上版本
- 2 GB RAM（建议 4 GB）
- 500 MB 磁盘空间
- 互联网连接（用于数据下载）

---

## 更多信息 | More Information

- **完整文档**: 查看 [README.md](README.md)
- **贡献指南**: 查看 [CONTRIBUTING.md](CONTRIBUTING.md)
- **版本历史**: 查看 [CHANGELOG.md](CHANGELOG.md)
- **GitHub**: https://github.com/yourusername/personal-quant-lab

---

**祝你使用愉快！** 🚀 | **Happy backtesting!**
