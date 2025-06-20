#!/usr/bin/env python3
"""
Debug PDF extraction to see what's going wrong
"""

import os
import sys
from pathlib import Path

def test_pdf_extraction_methods():
    """Test different PDF extraction methods to see what works"""
    
    print("🔍 Testing PDF Extraction Methods")
    print("=" * 50)
    
    # Look for PDF files in the current directory and common locations
    test_locations = [
        ".",
        "/Users/markpiesner/Arc Point Law Dropbox/Forms",
        "../../agentic_form_filler/Forms",
        "../../agentic_form_filler/client_data/Rogers"
    ]
    
    pdf_files = []
    for location in test_locations:
        if os.path.exists(location):
            for file in os.listdir(location):
                if file.lower().endswith('.pdf'):
                    full_path = os.path.join(location, file)
                    pdf_files.append(full_path)
                    print(f"   📄 Found: {full_path}")
    
    if not pdf_files:
        print("❌ No PDF files found to test")
        return
    
    # Test the first PDF file found
    test_file = pdf_files[0]
    print(f"\n🧪 Testing extraction on: {test_file}")
    print(f"   File size: {os.path.getsize(test_file)} bytes")
    
    # Method 1: PyPDF2
    print("\n📖 Method 1: PyPDF2")
    try:
        import PyPDF2
        with open(test_file, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            print(f"   Pages: {len(reader.pages)}")
            
            text_content = []
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                page_text = page.extract_text()
                text_content.append(page_text)
                print(f"   Page {page_num + 1}: {len(page_text)} chars")
            
            total_text = "\n\n".join(text_content)
            print(f"   ✅ Total extracted: {len(total_text)} chars")
            
            if len(total_text) > 0:
                print(f"   Sample text: {total_text[:200]}...")
            else:
                print("   ⚠️ No text extracted")
                
    except ImportError:
        print("   ❌ PyPDF2 not available")
    except Exception as e:
        print(f"   ❌ PyPDF2 error: {e}")
    
    # Method 2: pdfplumber
    print("\n📖 Method 2: pdfplumber")
    try:
        import pdfplumber
        with pdfplumber.open(test_file) as pdf:
            print(f"   Pages: {len(pdf.pages)}")
            
            text_content = []
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
                    print(f"   Page {page_num + 1}: {len(page_text)} chars")
                else:
                    print(f"   Page {page_num + 1}: No text")
            
            total_text = "\n\n".join(text_content)
            print(f"   ✅ Total extracted: {len(total_text)} chars")
            
            if len(total_text) > 0:
                print(f"   Sample text: {total_text[:200]}...")
            else:
                print("   ⚠️ No text extracted")
                
    except ImportError:
        print("   ❌ pdfplumber not available")
    except Exception as e:
        print(f"   ❌ pdfplumber error: {e}")
    
    # Method 3: Check if PDF has form fields with values
    print("\n📖 Method 3: pdftk form fields")
    try:
        import subprocess
        result = subprocess.run([
            'pdftk', test_file, 'dump_data_fields_utf8'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Count fields and values
            field_count = result.stdout.count('FieldName:')
            value_count = 0
            filled_values = []
            
            lines = result.stdout.split('\n')
            for line in lines:
                if line.startswith('FieldValue:') and line.strip() != 'FieldValue:':
                    value = line.replace('FieldValue:', '').strip()
                    if value:
                        value_count += 1
                        filled_values.append(value)
            
            print(f"   ✅ Form fields: {field_count}")
            print(f"   ✅ Filled fields: {value_count}")
            
            if filled_values:
                print("   Sample values:")
                for i, value in enumerate(filled_values[:5]):
                    print(f"     {i+1}. {value}")
            else:
                print("   ⚠️ No filled field values")
                
        else:
            print(f"   ❌ pdftk error: {result.stderr}")
            
    except Exception as e:
        print(f"   ❌ pdftk error: {e}")

def test_current_extraction_method():
    """Test the current extraction method in pdf_form_filler1.py"""
    
    print(f"\n🔍 Testing Current _extract_from_file Method")
    print("=" * 50)
    
    # Try to import and test the current method
    try:
        sys.path.insert(0, '.')
        
        # Read the current method
        with open('pdf_form_filler1.py', 'r') as f:
            content = f.read()
        
        # Check if the method looks correct
        if 'def _extract_from_file(' in content:
            print("   ✅ Method found in file")
            
            # Check for PyPDF2 usage
            if 'import PyPDF2' in content:
                print("   ✅ PyPDF2 import found")
            else:
                print("   ❌ PyPDF2 import missing")
            
            # Check for proper text extraction
            if 'page.extract_text()' in content:
                print("   ✅ Text extraction code found")
            else:
                print("   ❌ Text extraction code missing")
                
            # Check for proper joining
            if '.join(text_content)' in content:
                print("   ✅ Text joining code found")
            else:
                print("   ❌ Text joining code missing")
                
        else:
            print("   ❌ Method not found in file")
            
    except Exception as e:
        print(f"   ❌ Error checking method: {e}")

if __name__ == "__main__":
    test_pdf_extraction_methods()
    test_current_extraction_method()
    
    print(f"\n💡 Recommendations:")
    print("1. Check which extraction method works best for your PDFs")
    print("2. Verify PyPDF2 is installed: pip install PyPDF2")
    print("3. Try pdfplumber if PyPDF2 doesn't work: pip install pdfplumber")
    print("4. Check if your PDFs are text-based or image-based")
    print("5. Consider if PDFs have form fields with filled values")
