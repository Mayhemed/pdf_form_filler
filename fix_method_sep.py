#!/usr/bin/env python3
"""
Fix the method separation issue
"""

def fix_method_separation():
    file_path = "pdf_form_filler1.py"
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix the missing newline between methods
    content = content.replace(
        'return f"[Error reading file: {str(e)}]"    def _extract_from_image(self, image_path: str) -> str:',
        'return f"[Error reading file: {str(e)}]"\n\n    def _extract_from_image(self, image_path: str) -> str:'
    )
    
    # Write the fixed content
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("✅ Fixed method separation")

if __name__ == "__main__":
    fix_method_separation()
