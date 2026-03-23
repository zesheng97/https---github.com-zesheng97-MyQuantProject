#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fix all remaining indentation in the else block (lines 1495-1656)"""

with open('GUI_Client/app_v2.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_lines = []

for i, line in enumerate(lines, 1):
    # Lines 1495-1656 should all be at 12+ spaces (inside else body at 8 spaces)
    if 1495 <= i <= 1656:
        if line.strip():  # Non-empty line
            # Count spaces
            spaces = len(line) - len(line.lstrip())
            
            # If at 4-space level or 8-space level (where it should be 12+)
            if spaces == 4:
                # Add 8 spaces (4 → 12)
                fixed_lines.append('        ' + line)
            elif spaces == 8:
                # Add 4 spaces (8 → 12)
                fixed_lines.append('    ' + line)
            elif spaces == 12:
                # Add 4 spaces (12 → 16, for nested blocks)
                fixed_lines.append('    ' + line)
            elif spaces == 16:
                # Add 4 spaces (16 → 20, for deeply nested)
                fixed_lines.append('    ' + line)
            else:
                # Keep as-is
                fixed_lines.append(line)
        else:
            # Blank line, keep as-is
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)

with open('GUI_Client/app_v2.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("✅ Fixed remaining indentation (lines 1495-1656)")
