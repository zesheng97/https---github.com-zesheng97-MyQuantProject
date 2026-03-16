# -*- coding: utf-8 -*-
"""
Created on Mon Mar 16 15:17:41 2026

@author: 12434
"""

import os

# 1. 定义我们之前推导出的模块化架构
directories = [
    "Core_Bus",
    "Data_Hub/fetchers",
    "Data_Hub/storage",
    "Data_Hub/cleaners",
    "Strategy_Pool/base",
    "Strategy_Pool/custom",
    "Strategy_Pool/adapters",
    "Engine_Matrix/simulators",
    "Engine_Matrix/external_wrappers",
    "Analytics/metrics",
    "Analytics/reporters",
    "GUI_Client"
]

# 2. 批量创建文件夹
for dir_path in directories:
    os.makedirs(dir_path, exist_ok=True)
    # 在每个文件夹下创建一个空的 __init__.py，让 Python 识别它们为模块包
    with open(os.path.join(dir_path, "__init__.py"), "w") as f:
        pass

print("✅ 量化框架骨架创建完毕！")