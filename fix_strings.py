#!/usr/bin/env python3
"""
Fix the broken string literal in pdf_form_filler1.py
"""

def fix_string_literal():
    file_path = "pdf_form_filler1.py"
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix the broken string literal
    broken_line = 'extracted_text = "\n\n".join(text_content)'
    fixed_line = 'extracted_text = "\\n\\n".join(text_content)'
    
    # Also fix any other broken newline strings
    content = content.replace('extracted_text = "\n\n".join(text_content)', 'extracted_text = "\\n\\n".join(text_content)')
    content = content.replace('form_context = f"\n\nCONTEXT:', 'form_context = f"\\n\\nCONTEXT:')
    content = content.replace('return f"{extracted_text}\n\n[PDF_PATH:', 'return f"{extracted_text}\\n\\n[PDF_PATH:')
    
    # Write the fixed content
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed broken string literals")

if __name__ == "__main__":
    fix_string_literal()
