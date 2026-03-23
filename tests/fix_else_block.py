#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fix indentation for else block lines 1477-1656"""

with open('GUI_Client/app_v2.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_lines = []

for i, line in enumerate(lines, 1):
    # Lines 1478-1656 need 4 extra spaces (they're in the else: body)
    if 1478 <= i <= 1656:
        if line.startswith('    ') and not line.startswith('        '):
            # Line starts with exactly 4 spaces, needs to become 8
            fixed_lines.append('    ' + line)
        else:
            # Keep as-is (might be blank or already properly indented)
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)

with open('GUI_Client/app_v2.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("✅ Fixed else block indentation (lines 1478-1656)")
