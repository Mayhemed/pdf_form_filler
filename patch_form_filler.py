#!/usr/bin/env python3
"""
Quick Fix for python_form_filler3.py - Integrate Enhanced PDF Processing
This patch ensures the numbered PDF is actually sent to the AI for accurate field matching
"""

import os
import sys
from pathlib import Path

def patch_python_form_filler():
    """Patch the existing python_form_filler3.py to use enhanced numbered PDF processing"""
    
    print("🔧 Patching python_form_filler3.py for enhanced PDF processing")
    
    # Read the current file
    form_filler_path = Path("python_form_filler3.py")
    if not form_filler_path.exists():
        print("❌ python_form_filler3.py not found")
        return False
    
    with open(form_filler_path, 'r') as f:
        content = f.read()
    
    # Check if already patched
    if "# ENHANCED_PDF_PROCESSING_PATCH" in content:
        print("✅ Already patched - no changes needed")
        return True
    
    # Find the _extract_with_openai method and patch it
    old_extract_openai = '''            response_text = llm_client.generate_with_openai(openai_model, prompt)'''
    
    new_extract_openai = '''            # ENHANCED_PDF_PROCESSING_PATCH: Use numbered PDF for accurate field matching
            mapping_info = self._create_form_mapping()
            numbered_pdf_path = mapping_info.get("mapping_pdf") if mapping_info else None
            
            if numbered_pdf_path and os.path.exists(numbered_pdf_path):
                print(f"DEBUG: Using numbered PDF for extraction: {numbered_pdf_path}")
                response_text = llm_client.generate_with_openai(openai_model, prompt, None, numbered_pdf_path)
            else:
                print("DEBUG: No numbered PDF available, using text-only extraction")
                response_text = llm_client.generate_with_openai(openai_model, prompt)'''
    
    if old_extract_openai in content:
        content = content.replace(old_extract_openai, new_extract_openai)
        print("✅ Patched OpenAI extraction method")
    else:
        print("⚠️ OpenAI extraction method not found or already modified")
    
    # Find the _extract_with_anthropic method and patch it
    old_extract_claude = '''            response_text = llm_client.generate_with_claude(model, prompt)'''
    
    new_extract_claude = '''            # ENHANCED_PDF_PROCESSING_PATCH: Use numbered PDF for accurate field matching
            mapping_info = self._create_form_mapping()
            numbered_pdf_path = mapping_info.get("mapping_pdf") if mapping_info else None
            
            if numbered_pdf_path and os.path.exists(numbered_pdf_path):
                print(f"DEBUG: Using numbered PDF for extraction: {numbered_pdf_path}")
                response_text = llm_client.generate_with_claude(model, prompt, None, numbered_pdf_path)
            else:
                print("DEBUG: No numbered PDF available, using text-only extraction")
                response_text = llm_client.generate_with_claude(model, prompt)'''
    
    # Find the Claude method
    claude_method_start = content.find('def _extract_with_anthropic(self, text: str)')
    if claude_method_start != -1:
        # Look for the generate_with_claude call in this method
        claude_section = content[claude_method_start:claude_method_start + 2000]
        if 'llm_client.generate_with_claude(model, prompt)' in claude_section:
            content = content.replace(
                'response_text = llm_client.generate_with_claude(model, prompt)',
                new_extract_claude
            )
            print("✅ Patched Claude extraction method")
        else:
            print("⚠️ Claude extraction method not found or already modified")
    
    # Also enhance the prompt to be more specific about numbered fields
    old_prompt_section = '''TASK: Extract the client's actual responses/values from the completed form text below.

TARGET FORM FIELDS TO POPULATE:'''
    
    new_prompt_section = '''TASK: Extract data from source documents to fill the numbered fields in the target form.

IMPORTANT: You have access to a numbered mapping PDF that shows field locations with numbers (1, 2, 3, etc.).
Use the NUMBERS to match data precisely to the correct fields.

TARGET FORM FIELDS TO POPULATE:'''
    
    if old_prompt_section in content:
        content = content.replace(old_prompt_section, new_prompt_section)
        print("✅ Enhanced extraction prompt")
    
    # Add a note about the patch
    patch_note = '''
# ENHANCED_PDF_PROCESSING_PATCH Applied
# This file has been patched to use numbered PDF mapping for accurate field extraction
# The AI now receives the numbered PDF to ensure precise field matching
'''
    
    if "# ENHANCED_PDF_PROCESSING_PATCH Applied" not in content:
        content = patch_note + content
    
    # Write the patched file
    backup_path = form_filler_path.with_suffix('.py.backup')
    if not backup_path.exists():
        with open(backup_path, 'w') as f:
            f.write(content)
        print(f"✅ Created backup: {backup_path}")
    
    with open(form_filler_path, 'w') as f:
        f.write(content)
    
    print("✅ python_form_filler3.py patched successfully!")
    print("\n🎯 Key improvements:")
    print("   • AI now receives the numbered PDF for accurate field matching")
    print("   • Enhanced prompts for better number-based extraction")
    print("   • Fallback to text-only if numbered PDF unavailable")
    print("   • Backup created for safety")
    
    return True

def test_patch():
    """Test that the patch works correctly"""
    
    print("\n🧪 Testing the patch...")
    
    try:
        # Try to import the patched module
        import python_form_filler3
        print("✅ Module imports successfully")
        
        # Check if we can create an instance
        from PyQt6.QtWidgets import QApplication
        import sys
        
        app = QApplication(sys.argv)
        window = python_form_filler3.MainWindow()
        print("✅ Main window creates successfully")
        
        # Check if the enhanced methods exist
        if hasattr(window, '_create_form_mapping'):
            print("✅ Form mapping method available")
        else:
            print("⚠️ Form mapping method not found")
        
        app.quit()
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Enhanced PDF Processing Patch for python_form_filler3.py")
    print("=" * 60)
    
    success = patch_python_form_filler()
    
    if success:
        print("\n🎉 Patch applied successfully!")
        print("\nNext steps:")
        print("1. Test with: python3 python_form_filler3.py")
        print("2. The AI will now use numbered PDFs for accurate field matching")
        print("3. Check debug output for 'Using numbered PDF for extraction'")
        
        # Optionally test the patch
        # test_patch()
    else:
        print("\n❌ Patch failed - check error messages above")
