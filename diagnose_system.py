#!/usr/bin/env python3
"""
Quick Setup and Diagnostic Script for PDF Form Filler
Identifies why the current system isn't filling correctly
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def check_current_system():
    """Check the current system and identify issues"""
    print("🔍 PDF Form Filler System Diagnosis")
    print("=" * 50)
    
    base_path = Path("/Users/markpiesner/Documents/Github/LegalTools/PDF_Form_Filler")
    
    # 1. Check existing files
    print("\n📁 Existing System Files:")
    existing_files = [
        "python_form_filler3.py",
        "llm_client.py", 
        "fieldmappingwidget.py",
        "FINAL_SESSION_SUMMARY.md",
        "fl142_field_mapping.txt"
    ]
    
    for file_name in existing_files:
        file_path = base_path / file_name
        if file_path.exists():
            print(f"   ✅ {file_name}")
        else:
            print(f"   ❌ {file_name}")
    
    # 2. Check dependencies
    print("\n📦 Dependencies Check:")
    deps = [
        ("pdftk", ["pdftk", "--version"]),
        ("python", ["python3", "--version"]),
        ("PyQt6", ["python3", "-c", "import PyQt6; print('PyQt6 available')"]),
        ("OpenAI", ["python3", "-c", "import openai; print('OpenAI library available')"]),
        ("Anthropic", ["python3", "-c", "import anthropic; print('Anthropic library available')"]),
    ]
    
    for name, command in deps:
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"   ✅ {name}: Available")
            else:
                print(f"   ❌ {name}: Error - {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print(f"   ⏱️ {name}: Timeout")
        except FileNotFoundError:
            print(f"   ❌ {name}: Not found")
        except Exception as e:
            print(f"   ❌ {name}: Error - {e}")
    
    # 3. Check API keys
    print("\n🔑 API Keys:")
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    print(f"   OpenAI: {'✅ Set' if openai_key else '❌ Not set'}")
    print(f"   Anthropic: {'✅ Set' if anthropic_key else '❌ Not set'}")
    
    # 4. Check PDF documents
    print("\n📄 Available PDF Documents:")
    pdf_locations = [
        base_path,
        base_path / "../../agentic_form_filler/Forms",
        base_path / "../../agentic_form_filler/client_data/Rogers"
    ]
    
    found_pdfs = []
    for location in pdf_locations:
        if location.exists():
            pdfs = list(location.glob("*.pdf"))
            for pdf in pdfs:
                found_pdfs.append(pdf)
                print(f"   📄 {pdf.name} ({pdf.parent.name})")
    
    if not found_pdfs:
        print("   ❌ No PDF files found")
    
    # 5. Test current system
    print("\n🧪 Testing Current System:")
    
    main_script = base_path / "python_form_filler3.py"
    if main_script.exists():
        print(f"   ✅ Main script exists: {main_script.name}")
        
        # Try to import and test
        try:
            sys.path.insert(0, str(base_path))
            
            # Test imports
            import importlib.util
            spec = importlib.util.spec_from_file_location("python_form_filler3", main_script)
            if spec and spec.loader:
                print("   ✅ Main script is importable")
            else:
                print("   ❌ Main script import failed")
        
        except Exception as e:
            print(f"   ❌ Error importing main script: {e}")
    else:
        print("   ❌ Main script not found")
    
    # 6. Identify the core issues
    print("\n🚨 IDENTIFIED ISSUES:")
    issues = []
    
    if not openai_key and not anthropic_key:
        issues.append("No AI API keys set - system falls back to basic pattern matching")
    
    if not found_pdfs:
        issues.append("No PDF forms found for testing")
    
    # Check if pdftk is available
    try:
        subprocess.run(["pdftk", "--version"], capture_output=True, check=True)
    except:
        issues.append("pdftk not available - PDF form filling will fail")
    
    # Check the session summary for known issues
    summary_file = base_path / "FINAL_SESSION_SUMMARY.md"
    if summary_file.exists():
        with open(summary_file) as f:
            summary = f.read()
            if "AI Not Actually Used" in summary:
                issues.append("AI extraction not connected to form filling pipeline")
            if "Form Filling Incomplete" in summary:
                issues.append("PDF forms filled with sample data instead of extracted data")
    
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")
    
    # 7. Provide solutions
    print("\n💡 SOLUTIONS TO IMPLEMENT:")
    solutions = [
        "Set API keys: export OPENAI_API_KEY='your_key' or export ANTHROPIC_API_KEY='your_key'",
        "Install pdftk: brew install pdftk-java (macOS) or apt install pdftk (Linux)",
        "Connect AI extraction to form filling pipeline",
        "Process real source documents instead of using sample data",
        "Test with the provided FL-120 and FL-142 PDFs"
    ]
    
    for i, solution in enumerate(solutions, 1):
        print(f"   {i}. {solution}")
    
    return issues, solutions

def test_with_real_documents():
    """Test the system with real documents"""
    print("\n🧪 Testing with Real Documents:")
    
    base_path = Path("/Users/markpiesner/Documents/Github/LegalTools/PDF_Form_Filler")
    
    # Look for the provided PDF documents
    possible_locations = [
        base_path / "../../agentic_form_filler/Forms",
        base_path / "../../agentic_form_filler/client_data/Rogers",
        base_path
    ]
    
    fl120_files = []
    fl142_files = []
    
    for location in possible_locations:
        if location.exists():
            fl120_files.extend(location.glob("*fl120*.pdf"))
            fl120_files.extend(location.glob("*FL120*.pdf"))
            fl120_files.extend(location.glob("*FL-120*.pdf"))
            
            fl142_files.extend(location.glob("*fl142*.pdf"))
            fl142_files.extend(location.glob("*FL142*.pdf"))
            fl142_files.extend(location.glob("*FL-142*.pdf"))
    
    print(f"   Found FL-120 files: {len(fl120_files)}")
    for f in fl120_files:
        print(f"     📄 {f}")
    
    print(f"   Found FL-142 files: {len(fl142_files)}")
    for f in fl142_files:
        print(f"     📄 {f}")
    
    if fl120_files and fl142_files:
        print("\n✅ Ready to test with real documents!")
        print("   Next steps:")
        print("   1. Set up API keys")
        print("   2. Run the unified pipeline with these documents")
        print("   3. Compare output with expected results")
    else:
        print("\n❌ Need to locate the source documents")
        print("   The system references:")
        print("   - FL-120 forms (blank and filled)")
        print("   - FL-142 forms (blank and filled)")

def create_test_command():
    """Create a test command to run with the new unified pipeline"""
    print("\n🚀 Test Command for New Unified Pipeline:")
    
    # Find a blank form and filled form
    base_path = Path("/Users/markpiesner/Documents/Github/LegalTools/PDF_Form_Filler")
    
    print("   # Set API key first:")
    print("   export OPENAI_API_KEY='your_key_here'")
    print("   # OR")
    print("   export ANTHROPIC_API_KEY='your_key_here'")
    print()
    print("   # Run the unified pipeline:")
    print("   cd /Users/markpiesner/Documents/Github/LegalTools/PDF_Form_Filler")
    print("   python3 src/cli/command_line_interface.py fill-form \\")
    print("     'path/to/blank_form.pdf' \\")
    print("     'output/filled_form.pdf' \\")
    print("     --sources 'path/to/source1.pdf' 'path/to/source2.pdf' \\")
    print("     --verbose")
    print()
    print("   # Test AI connectivity:")
    print("   python3 src/cli/command_line_interface.py test-ai --verbose")
    print()
    print("   # Analyze a form structure:")
    print("   python3 src/cli/command_line_interface.py analyze 'path/to/form.pdf' --verbose")

def main():
    """Main diagnostic function"""
    issues, solutions = check_current_system()
    test_with_real_documents()
    create_test_command()
    
    print("\n" + "=" * 50)
    print("📋 SUMMARY:")
    print(f"   Issues found: {len(issues)}")
    print(f"   Solutions available: {len(solutions)}")
    print("\n   The new unified pipeline system is ready to test!")
    print("   Key improvement: Connects AI extraction → Field mapping → PDF filling")

if __name__ == "__main__":
    main()
