#!/usr/bin/env python3
"""
Quick script to restore working PDF extraction method
"""

import re

def restore_pdf_extraction():
    """Restore the working PDF extraction method"""
    
    file_path = "pdf_form_filler1.py"
    
    # Read the current file
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        return False
    
    # The new working method
    new_method = '''    def _extract_from_file(self, file_path: str) -> str:
        """Extract text from various file types - RESTORED WORKING VERSION"""
        print(f"DEBUG: Extracting text from file: {file_path}")
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.pdf':
                # For PDFs, we need to extract text and also provide the file path for direct processing
                print(f"DEBUG: PDF file detected: {os.path.basename(file_path)}")
                file_name = os.path.basename(file_path)
                extracted_text = ""
                
                # Try to extract text from the PDF first
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as pdf_file:
                        reader = PyPDF2.PdfReader(pdf_file)
                        text_content = []
                        for page_num in range(len(reader.pages)):
                            page = reader.pages[page_num]
                            text_content.append(page.extract_text())
                        extracted_text = "\\n\\n".join(text_content)
                        print(f"DEBUG: Extracted {len(extracted_text)} chars of text from PDF")
                except Exception as e:
                    print(f"DEBUG: Error extracting text from PDF: {str(e)}")
                
                # Add context about what form is being filled
                form_context = ""
                if hasattr(self, 'current_pdf_path') and self.current_pdf_path:
                    form_name = os.path.basename(self.current_pdf_path)
                    form_context = f"\\n\\nCONTEXT: This data is being used to fill the form '{form_name}'"
                
                # For other providers, return the extracted text or a marker
                if extracted_text:
                    return f"{extracted_text}{form_context}"
                else:
                    return f"[PDF FILE: {file_name}] This is a PDF document that contains data to fill a form.{form_context}"
            
            elif ext in ['.txt', '.md', '.csv']:
                # Read text files directly
                with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                    text = file.read()
                    print(f"DEBUG: Read {len(text)} chars from text file")
                    return text
            
            elif ext == '.json':
                # Parse JSON and format it
                with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                    try:
                        data = json.load(file)
                        text = json.dumps(data, indent=2)
                        print(f"DEBUG: Parsed JSON with {len(text)} chars")
                        return text
                    except Exception as e:
                        # If JSON parsing fails, just return raw content
                        file.seek(0)
                        return file.read()
            
            else:
                return f"[Unsupported file type: {ext}]"
                
        except Exception as e:
            print(f"ERROR in _extract_text_from_file: {e}")
            import traceback
            print(traceback.format_exc())
            return f"[Error reading file: {str(e)}]"'''
    
    # Find the current method and replace it
    # Pattern to match the entire _extract_from_file method
    pattern = r'    def _extract_from_file\(self, file_path: str\) -> str:.*?(?=    def |\Z)'
    
    # Replace the method
    new_content = re.sub(pattern, new_method, content, flags=re.DOTALL)
    
    if new_content != content:
        # Create backup
        with open(file_path + ".backup2", 'w') as f:
            f.write(content)
        
        # Write the new content
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        print("✅ Successfully restored working PDF extraction method!")
        print("✅ Created backup: pdf_form_filler1.py.backup2")
        return True
    else:
        print("❌ Could not find method to replace")
        return False

if __name__ == "__main__":
    print("🔧 Restoring Working PDF Extraction Method")
    print("=" * 50)
    success = restore_pdf_extraction()
    
    if success:
        print("\n🎉 PDF extraction method restored!")
        print("Now test again: python3 pdf_form_filler1.py")
    else:
        print("\n❌ Failed to restore method")
        print("Please manually replace the _extract_from_file method")
