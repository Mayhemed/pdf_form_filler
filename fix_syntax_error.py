#!/usr/bin/env python3
"""
Quick fix for the syntax error in the try block
"""

def fix_try_block_syntax():
    """Fix the broken try block syntax"""
    
    file_path = "pdf_form_filler1.py"
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Create backup
    with open(file_path + ".backup_syntax_fix", 'w') as f:
        f.write(content)
    print("✅ Created backup: pdf_form_filler1.py.backup_syntax_fix")
    
    # Fix the broken prompt placement - move it inside the try block
    # Find the problematic line and fix indentation
    content = content.replace(
        '            # Generic prompt for any form type\n            # CROSS-DOCUMENT INTELLIGENT FIELD MAPPING PROMPT\n        prompt = f"""',
        '            # CROSS-DOCUMENT INTELLIGENT FIELD MAPPING PROMPT\n            prompt = f"""'
    )
    
    # Write the fixed content
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed try block syntax error")

if __name__ == "__main__":
    print("🔧 Fixing Try Block Syntax Error")
    print("=" * 40)
    fix_try_block_syntax()
    print("✅ Syntax error fixed!")
