#!/usr/bin/env python3
"""
Fix the dotenv import issue
"""

def fix_dotenv_import():
    file_path = "pdf_form_filler1.py"
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix the dotenv import with try/except
    content = content.replace(
        'import dotenv',
        '''try:
    import dotenv
except ImportError:
    dotenv = None'''
    )
    
    # Write the fixed content
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed dotenv import")

if __name__ == "__main__":
    fix_dotenv_import()
