#!/usr/bin/env python3
"""
App.py Optimization Script
Reduces code length by removing verbose documentation while preserving functionality
"""

def optimize_app_py():
    """Systematically optimize app.py by removing verbose sections"""
    
    with open('app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    optimized_lines = []
    skip_until_end_docstring = False
    docstring_delimiter = None
    in_long_comment_block = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip very long docstrings (more than 5 lines)
        if '"""' in line or "'''" in line:
            if not skip_until_end_docstring:
                # Starting a docstring
                if line.count('"""') == 2 or line.count("'''") == 2:
                    # Single line docstring - keep it
                    optimized_lines.append(line)
                    continue
                else:
                    # Multi-line docstring starting
                    docstring_delimiter = '"""' if '"""' in line else "'''"
                    # Check if this is a very long docstring by looking ahead
                    docstring_lines = 1
                    for j in range(i+1, min(i+20, len(lines))):
                        if docstring_delimiter in lines[j]:
                            break
                        docstring_lines += 1
                    
                    if docstring_lines > 10:  # Long docstring, replace with short version
                        # Extract just the first line description
                        first_line = line.strip()
                        if first_line.startswith('"""') or first_line.startswith("'''"):
                            # Keep just the opening and add a simple description
                            optimized_lines.append('    """' + first_line[3:].strip() + '"""\n')
                        else:
                            optimized_lines.append(line)
                        skip_until_end_docstring = True
                        continue
                    else:
                        # Short docstring, keep as is
                        optimized_lines.append(line)
            else:
                # We're skipping until end of docstring
                if docstring_delimiter in line:
                    skip_until_end_docstring = False
                    docstring_delimiter = None
                continue
        
        # Skip long comment blocks explaining data structures
        if stripped.startswith('#') and any(keyword in stripped.lower() for keyword in [
            'data type', 'data structure', 'explanation:', 'rationale:', 'benefits:', 'trade-offs:'
        ]):
            in_long_comment_block = True
            continue
        
        if in_long_comment_block:
            if stripped.startswith('#') or stripped == '':
                continue
            else:
                in_long_comment_block = False
        
        # Skip very verbose single-line comments
        if stripped.startswith('#') and len(stripped) > 80:
            continue
            
        # Skip separator lines that are just decoration
        if stripped.startswith('#') and ('=' * 10 in stripped or '-' * 10 in stripped):
            continue
        
        # Keep the line if it's not in a skip block
        if not skip_until_end_docstring:
            optimized_lines.append(line)
    
    # Write optimized version
    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(optimized_lines)
    
    print(f"✓ Optimization complete")
    print(f"  Original lines: {len(lines)}")
    print(f"  Optimized lines: {len(optimized_lines)}")
    print(f"  Reduction: {len(lines) - len(optimized_lines)} lines ({((len(lines) - len(optimized_lines)) / len(lines) * 100):.1f}%)")

if __name__ == "__main__":
    optimize_app_py()