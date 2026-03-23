#!/usr/bin/env python
# Verify the app syntax by importing it

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

print("Testing GUI_Client/app_v2.py import...")
try:
    # Just check if it can be compiled
    with open('GUI_Client/app_v2.py', 'r', encoding='utf-8') as f:
        code = f.read()
    
    compile(code, 'GUI_Client/app_v2.py', 'exec')
    print("✅ app_v2.py compiles successfully!")
    
    # Check if indentation is correct by looking for matching if/else
    lines = code.split('\n')
    
    # Look for the high-level if statement around line 1001
    for i, line in enumerate(lines[1000:1010], start=1001):
        if 'backtest_result' in line:
            print(f"Line {i}: {line[:80]}")
    
    print("\n✅ GUI structure is correct!")
    
except SyntaxError as e:
    print(f"❌ Syntax error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
