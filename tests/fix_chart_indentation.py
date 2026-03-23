#!/usr/bin/env python
# Dedent the chart and data code that's incorrectly nested

with open('GUI_Client/app_v2.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find lines starting at ~1230 with 12-space indentation and dedent them
# Stop when we reach lines with 4 spaces or less (back to top level)

# First, identify the range
start_idx = None
for i in range(1220, 1250):
    if '# 上图：账户净值曲线' in lines[i]:
        start_idx = i
        break

if start_idx:
    print(f"Found start at line {start_idx + 1}")
    
    # Now dedent from here until we find actual code that shouldn't be dedented
    # Look for where the simple mode block should end (before the default page)
    
    dedented = 0
    for i in range(start_idx, len(lines)):
        line = lines[i]
        
        # Stop if we reach another top-level structure
        if i > start_idx + 100 and (line.startswith('else:') or (line.startswith('st.') and not line.startswith('            '))):
            if line.startswith('else:'):
                break
        
        # Dedent lines that start with 12+ spaces
        if line.startswith('            ') and line.strip():  # 12+ spaces and non-empty
            lines[i] = line[4:]  # Remove 4 spaces
            dedented += 1
    
    with open('GUI_Client/app_v2.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"✅ Dedented {dedented} lines")
else:
    print("Could not find the section to fix")
