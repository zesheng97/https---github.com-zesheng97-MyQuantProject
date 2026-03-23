#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Comprehensive indentation fixer - fixes all indentation errors in one pass"""

import re

def fix_all_indentation(filepath):
    """Fix all indentation issues by analyzing statement structure"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if current line ends with a colon (for/if/try/else/elif/with:)
        stripped = line.rstrip('\n').rstrip()
        if stripped.endswith(':'):
            fixed_lines.append(line)
            i += 1
            
            # Look ahead for the body lines
            body_indent = None
            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.rstrip('\n').rstrip()
                
                # Skip blank lines
                if not next_stripped:
                    fixed_lines.append(next_line)
                    i += 1
                    continue
                
                # Get indentation
                next_spaces = len(next_line) - len(next_line.lstrip())
                curr_spaces = len(line) - len(line.lstrip())
                
                # First non-blank line is body
                if body_indent is None:
                    body_indent = next_spaces
                    # Check if it's properly indented (should be curr_spaces + 4)
                    if next_spaces <= curr_spaces:
                        # Fix it - add 4 spaces
                        fixed_lines.append('    ' + next_line)
                    else:
                        fixed_lines.append(next_line)
                    i += 1
                    continue
                
                # Subsequent lines
                if next_spaces < curr_spaces:
                    # Back to outer scope
                    break
                elif next_spaces <= curr_spaces:
                    # Check if this should be in body or at outer level
                    if next_spaces == curr_spaces and next_stripped.endswith(':'):
                        # New statement at same level
                        break
                    elif next_spaces < body_indent:
                        # Dedented - probably error
                        if next_spaces == curr_spaces and next_stripped.startswith(('if ', 'elif ', 'else:', 'except:', 'finally:', 'for ', 'while ', 'with ', 'try:')):
                            break
                        # Otherwise might be part of body that wasn't indented enough
                        if next_spaces == curr_spaces and 'elif ' not in next_stripped:
                            fixed_lines.append('    ' + next_line)
                            i += 1
                            continue
                    
                fixed_lines.append(next_line)
                i += 1
        else:
            fixed_lines.append(line)
            i += 1
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    return len(fixed_lines)

if __name__ == '__main__':
    count = fix_all_indentation('GUI_Client/app_v2.py')
    print(f"✅ Processed {count} lines")
