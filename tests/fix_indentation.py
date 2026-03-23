#!/usr/bin/env python
# Fix indentation in app_v2.py

with open('GUI_Client/app_v2.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Based on grep output: line 1221 has "双图表展示", line 1478 has "默认页面"
# So we need to indent lines from 1220 (0-indexed) to 1477

start_line = 1220  # 0-indexed, so line 1221
end_line = 1478    # 0-indexed, so line 1479

print(f"Will indent lines {start_line + 1} to {end_line}")
print(f"Lines to indent: {end_line - start_line}")
print(f"Start line: {lines[start_line][:60]}")

# Indent all lines from start to end
for i in range(start_line, end_line):
    # Only indent non-empty lines that don't start with else or elif at column 0
    line = lines[i]
    if line.strip() and not (line.startswith(('else:', 'elif')) and line.index('else') == 0):
        # Add 4 spaces of indentation
        lines[i] = "    " + line

# Write back
with open('GUI_Client/app_v2.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ Indentation applied!")

