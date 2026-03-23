#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Smart indentation fixer for GUI_Client/app_v2.py
Fixes indentation levels for nested for/if statements and their bodies
"""

import re

def smart_fix_indents(filepath):
    """Fix indentation intelligently, considering Python's block structure"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Check if line starts with exactly 12 spaces followed by non-whitespace
        if line.startswith('            ') and not line.startswith('             '):
            # Count leading spaces
            match = re.match(r'^(\s+)', line)
            if match:
                spaces = match.group(1)
                
                # Check if this is the body of a for/if statement
                if i > 0:
                    prev_line = lines[i-1].rstrip('\n')
                    prev_match = re.match(r'^(\s+)', prev_line)
                    
                    if prev_match:
                        prev_spaces = len(prev_match.group(1))
                        prev_content = prev_line.lstrip()
                        
                        # If previous line is a for:/if: at same or less indentation
                        # and this line has 12 spaces, it should be 16 spaces
                        if (prev_content.endswith(':') and 
                            (prev_spaces <= 12) and 
                            len(spaces) == 12):
                            # This is a body line - needs to be indented to 16
                            new_line = '    ' + line
                            fixed_lines.append(new_line)
                            continue
                
                # Otherwise, convert 12 spaces to 8 spaces (normal dedent)
                if len(spaces) == 12:
                    new_line = '        ' + line[12:]
                    fixed_lines.append(new_line)
                    continue
        
        fixed_lines.append(line)
    
    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print("✅ Smart indentation fix complete")

if __name__ == '__main__':
    smart_fix_indents('GUI_Client/app_v2.py')
