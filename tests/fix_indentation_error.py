#!/usr/bin/env python
# Fix the incorrectly indented chart section

with open('GUI_Client/app_v2.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find line 1219 (0-indexed) which has the incorrectly indented "# --- 双图表展示"
# and dedent from there until we find the "else:" for the main block again

start_fix = None
for i in range(1210, 1230):
    if '# --- 双图表展示' in lines[i] and lines[i].startswith('            '):
        start_fix = i
        print(f"Found incorrectly indented section at line {i+1}: {lines[i][:60]}")
        print(f"Current indentation: {len(lines[i]) - len(lines[i].lstrip())} spaces")
        break

if start_fix:
    # Find where this incorrectly indented section ends
    # It should end when we reach the main "else:" for the default page
    # Look for lines starting with "else:" at column 0 and having "# 默认页面"
    
    end_fix = None
    for i in range(start_fix, len(lines)):
        if lines[i].startswith("else:") and "# 默认页面" in lines[i]:
            end_fix = i
            print(f"Found section end at line {i+1}")
            break
    
    if end_fix:
        # Dedent all lines from start_fix to end_fix by 4 spaces
        for i in range(start_fix, end_fix):
            if lines[i].startswith('            '):  # Lines with 12+ spaces
                lines[i] = lines[i][4:]  # Remove 4 spaces
        
        # Write back
        with open('GUI_Client/app_v2.py', 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"✅ Dedented {end_fix - start_fix} lines")
        print("File saved!")
    else:
        print("❌ Could not find section end")
else:
    print("❌ Could not find section start")
