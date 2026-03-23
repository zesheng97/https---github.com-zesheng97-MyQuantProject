#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复简单模式结果显示的缩进"""

with open('GUI_Client/app_v2.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到"else:"的行
else_line_idx = None
for i, line in enumerate(lines):
    if line.strip() == "else:" and i > 700:  # 在结果显示区域
        else_line_idx = i
        break

if else_line_idx is None:
    print("❌ 找不到else块")
    exit(1)

print(f"✓ 找到else块在第{else_line_idx+1}行")

# 从else_line_idx + 2开始（跳过注释行），找到第一个非空内容行
start_idx = else_line_idx + 2

# 找到else块的结束位置（下一个顶级elif/else或if）
indent_end = len(lines)
for i in range(start_idx, len(lines)):
    line = lines[i]
    # 检查是否是新的顶级语句（在缩进4格以内）
    if line.strip() and len(line) - len(line.lstrip()) <= 4:
        if line.lstrip().startswith(('if ', 'elif ', 'else', 'for ', 'with ')):
            if not line.lstrip().startswith(('#')):  # 不是注释
                indent_end = i
                break

print(f"✓ else块范围：{start_idx+1} - {indent_end}")

# 构建修复后的文件
fixed_lines = lines[:start_idx]

# 添加缩进到else块内的行
for i in range(start_idx, indent_end):
    line = lines[i]
    if line.strip():  # 非空行
        if not line.startswith('        '):  # 如果还没缩进到8个空格
            fixed_lines.append('    ' + line)
        else:
            fixed_lines.append(line)
    else:  # 空行
        fixed_lines.append(line)

# 添加剩余的行
fixed_lines.extend(lines[indent_end:])

with open('GUI_Client/app_v2.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("✅ 缩进修复完成")

