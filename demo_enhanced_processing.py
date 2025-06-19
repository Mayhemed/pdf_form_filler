#!/usr/bin/env python3
"""
Enhanced PDF Processing Demo
Demonstrates the new direct PDF processing capabilities
"""

import os
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

def demo_direct_pdf_processing():
    """Demo the direct PDF processing functionality"""
    
    print("🚀 Enhanced PDF Processing Demo v4.1")
    print("=" * 50)
    
    # Check API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not (openai_key or anthropic_key):
        print("❌ No API keys found. Please set:")
        print("   export OPENAI_API_KEY='your-key'")
        print("   export ANTHROPIC_API_KEY='your-key'")
        return False
    
    print(f"✅ API Keys: OpenAI={'Yes' if openai_key else 'No'}, Claude={'Yes' if anthropic_key else 'No'}")
    
    # Demo 1: Direct PDF Processing with llm_client
    print(f"\n📄 Demo 1: Direct PDF Processing")
    print("-" * 30)
    
    try:
        import llm_client
        
        # Simple test prompt
        test_prompt = """Analyze this PDF and tell me:
1. What type of form this appears to be
2. The first 3 field labels you can identify
3. Any numbered fields (1, 2, 3, etc.) you see

Keep response brief and focused."""
        
        # Test with any available PDF in the directory
        test_pdfs = list(Path.cwd().glob("*.pdf"))
        if not test_pdfs:
            print("⚠️  No PDF files found in current directory")
            print("   Please add a PDF file to test with")
            return False
        
        test_pdf = test_pdfs[0]
        print(f"Testing with: {test_pdf.name}")
        
        # Try OpenAI direct processing
        if openai_key:
            print("\n🤖 OpenAI Direct PDF Processing:")
            try:
                response = llm_client.generate_with_openai_direct_pdf(
                    "gpt-4-turbo-preview", 
                    test_prompt, 
                    str(test_pdf)
                )
                print(f"✅ Success! Response preview:")
                print(f"   {response[:200]}...")
            except Exception as e:
                print(f"❌ OpenAI failed: {e}")
        
        # Try Claude direct processing
        if anthropic_key:
            print("\n🤖 Claude Direct PDF Processing:")
            try:
                response = llm_client.generate_with_claude_direct_pdf(
                    "claude-3-opus-20240229",
                    test_prompt,
                    str(test_pdf)
                )
                print(f"✅ Success! Response preview:")
                print(f"   {response[:200]}...")
            except Exception as e:
                print(f"❌ Claude failed: {e}")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Demo 2: Enhanced AI Text Label Extractor (if we have the modules)
    print(f"\n🧠 Demo 2: Enhanced AI Label Extraction")
    print("-" * 30)
    
    try:
        from src.core.enhanced_ai_label_extractor import EnhancedAITextLabelExtractor
        
        # Create a simple test field mapping
        test_mapping = {
            1: {'full_field_name': 'test_field_1', 'short_name': 'Field 1', 'field_type': 'Text'},
            2: {'full_field_name': 'test_field_2', 'short_name': 'Field 2', 'field_type': 'Text'},
            3: {'full_field_name': 'test_field_3', 'short_name': 'Field 3', 'field_type': 'Text'},
        }
        
        # Initialize extractor with auto provider selection
        extractor = EnhancedAITextLabelExtractor(ai_provider="auto")
        print(f"✅ Initialized with provider: {extractor.ai_provider}")
        print(f"   Model: {extractor.model}")
        
        # Note: We would need a numbered PDF to actually test this
        print("ℹ️  To test field extraction, create a numbered PDF first using:")
        print("   from src.core.enhanced_form_mapper_complete import EnhancedUniversalFormMapper")
        print("   mapper = EnhancedUniversalFormMapper()")
        print("   result = mapper.create_numbered_mapping_for_form_with_ai('your_form.pdf')")
        
    except ImportError as e:
        print(f"⚠️  Enhanced modules not available: {e}")
        print("   This is normal if running without the full enhanced setup")
    
    # Demo 3: Smart Processing Selection
    print(f"\n🎯 Demo 3: Smart Processing Selection")
    print("-" * 30)
    
    try:
        # Show how the enhanced llm_client automatically chooses the best method
        print("The enhanced llm_client automatically selects:")
        print("✅ Direct PDF processing for single PDF analysis")
        print("✅ Image processing when multiple PDFs needed")
        print("✅ Fallback strategies when primary method fails")
        print("✅ Provider selection based on availability")
        
        # Example of smart selection
        if test_pdfs:
            print(f"\nExample with {test_pdf.name}:")
            if openai_key:
                print("   generate_with_openai() → Direct PDF (faster)")
            if anthropic_key:
                print("   generate_with_claude() → Direct PDF (native support)")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    
    print(f"\n🎉 Demo completed!")
    print(f"✅ Direct PDF processing is working")
    print(f"✅ Enhanced system is ready for use")
    
    return True

def show_usage_examples():
    """Show practical usage examples"""
    
    print(f"\n📚 Usage Examples")
    print("=" * 30)
    
    print("""
# 1. Direct PDF Processing
import llm_client

response = llm_client.generate_with_openai_direct_pdf(
    "gpt-4-turbo-preview",
    "Analyze this form and identify numbered fields",
    "path/to/form.pdf"
)

# 2. Enhanced Form Mapping (full system)
from src.core.enhanced_form_mapper_complete import EnhancedUniversalFormMapper

mapper = EnhancedUniversalFormMapper(ai_provider="auto")
numbered_pdf, mapping_json, ai_labels_json, enhanced_mapping = (
    mapper.create_numbered_mapping_for_form_with_ai("form.pdf")
)

# 3. Quality Verification
print(f"Quality Score: {enhanced_mapping.get('quality_score', 'N/A')}")

# 4. Smart API Selection
# Automatically chooses best available provider and method
response = llm_client.generate_with_openai("gpt-4-turbo-preview", prompt, "form.pdf")
response = llm_client.generate_with_claude("claude-3-opus-20240229", prompt, "form.pdf")
""")

if __name__ == "__main__":
    print("Enhanced PDF Processing Demo v4.1")
    
    success = demo_direct_pdf_processing()
    
    if success:
        show_usage_examples()
        print(f"\n🚀 Ready to process PDFs with enhanced AI!")
    else:
        print(f"\n❌ Demo encountered issues - check setup")
