# 文件位置: run_gui.py
# 描述: 简化 GUI 启动入口

import os
import subprocess

def main():
    print("🚀 启动 Personal Quant Lab GUI (参数化回测系统)...")
    gui_path = os.path.join(os.path.dirname(__file__), 'GUI_Client', 'app_v2.py')
    subprocess.run(['streamlit', 'run', gui_path])

if __name__ == "__main__":
    main()