#!/usr/bin/env python3
"""
Test extraction specifically on the Rogers FL-120 file that should have real data
"""

import os
import sys

def test_rogers_fl120():
    """Test extraction on the Rogers FL-120 file"""
    
    print("🔍 Testing Rogers FL-120 File")
    print("=" * 50)
    
    rogers_file = "../../agentic_form_filler/client_data/Rogers/Rogers-FL120-signed.pdf"
    
    if not os.path.exists(rogers_file):
        print(f"❌ File not found: {rogers_file}")
        return
    
    print(f"✅ File found: {rogers_file}")
    print(f"   File size: {os.path.getsize(rogers_file)} bytes")
    
    # Test PyPDF2 extraction
    print(f"\n📖 Extracting with PyPDF2:")
    try:
        import PyPDF2
        with open(rogers_file, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            print(f"   Pages: {len(reader.pages)}")
            
            text_content = []
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                page_text = page.extract_text()
                text_content.append(page_text)
                print(f"   Page {page_num + 1}: {len(page_text)} chars")
            
            total_text = "\\n\\n".join(text_content)
            print(f"   ✅ Total extracted: {len(total_text)} chars")
            
            if len(total_text) > 100:
                print(f"   📝 Sample text:")
                # Look for specific data we expect
                lines = total_text.split('\\n')
                for i, line in enumerate(lines[:20]):  # First 20 lines
                    if line.strip():  # Non-empty lines
                        print(f"      Line {i+1}: {line.strip()}")
                
                # Look for key information
                if "TAHIRA" in total_text or "FRANCIS" in total_text:
                    print(f"   ✅ Found expected name data")
                if "SHAWN" in total_text or "ROGERS" in total_text:
                    print(f"   ✅ Found expected respondent data")
                if "24STFL" in total_text or "case" in total_text.lower():
                    print(f"   ✅ Found case number data")
            else:
                print(f"   ⚠️ Very little text extracted")
                
    except ImportError:
        print(f"   ❌ PyPDF2 not available")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_fl142_copy():
    """Test the fl142 copy file"""
    
    print(f"\n🔍 Testing FL-142 Copy File")
    print("=" * 50)
    
    fl142_file = "../../agentic_form_filler/client_data/Rogers/fl142 copy.pdf"
    
    if not os.path.exists(fl142_file):
        print(f"❌ File not found: {fl142_file}")
        return
    
    print(f"✅ File found: {fl142_file}")
    print(f"   File size: {os.path.getsize(fl142_file)} bytes")
    
    # Test PyPDF2 extraction
    print(f"\n📖 Extracting with PyPDF2:")
    try:
        import PyPDF2
        with open(fl142_file, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            print(f"   Pages: {len(reader.pages)}")
            
            text_content = []
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                page_text = page.extract_text()
                text_content.append(page_text)
                print(f"   Page {page_num + 1}: {len(page_text)} chars")
            
            total_text = "\\n\\n".join(text_content)
            print(f"   ✅ Total extracted: {len(total_text)} chars")
            
            if len(total_text) > 100:
                print(f"   📝 Sample text:")
                lines = total_text.split('\\n')
                for i, line in enumerate(lines[:20]):  # First 20 lines
                    if line.strip():  # Non-empty lines
                        print(f"      Line {i+1}: {line.strip()}")
            else:
                print(f"   ⚠️ Very little text extracted")
                
    except ImportError:
        print(f"   ❌ PyPDF2 not available")
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_rogers_fl120()
    test_fl142_copy()
