#!/usr/bin/env python3
"""
Integration Test for Enhanced AI Label Extraction
Tests the complete pipeline with the existing python_form_filler3.py
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

def test_ai_label_extraction():
    """Test the AI label extraction with existing form filler"""
    
    print("🧪 Testing Enhanced AI Label Extraction Integration")
    print("=" * 50)
    
    # Import the enhanced components
    try:
        from src.core.enhanced_form_mapper_complete import EnhancedUniversalFormMapper
        print("✅ Successfully imported EnhancedUniversalFormMapper")
    except ImportError as e:
        print(f"❌ Failed to import enhanced components: {e}")
        return False
    
    # Test with a sample PDF (use any PDF in the project)
    test_pdfs = [
        project_root / "test_data" / "FL-142.pdf",
        project_root / "FL-142.pdf", 
        project_root / "FL-120.pdf"
    ]
    
    test_pdf = None
    for pdf_path in test_pdfs:
        if pdf_path.exists():
            test_pdf = pdf_path
            break
    
    if not test_pdf:
        print("❌ No test PDF found")
        return False
    
    print(f"📄 Using test PDF: {test_pdf.name}")
    
    # Create enhanced mapper
    try:
        mapper = EnhancedUniversalFormMapper(ai_provider="openai", cache_enabled=True)
        print("✅ Created enhanced form mapper")
    except Exception as e:
        print(f"❌ Failed to create mapper: {e}")
        return False
    
    # Test the enhanced mapping
    try:
        print("\n🔄 Running enhanced numbered mapping...")
        
        numbered_pdf, mapping_json, ai_labels_json, enhanced_mapping = (
            mapper.create_numbered_mapping_for_form_with_ai(test_pdf)
        )
        
        print(f"✅ Enhanced mapping completed!")
        print(f"   📋 Numbered PDF: {numbered_pdf.name}")
        print(f"   📊 Mapping JSON: {mapping_json.name}")
        print(f"   🤖 AI Labels JSON: {ai_labels_json.name}")
        print(f"   📈 Total fields mapped: {len(enhanced_mapping)}")
        
        # Count AI-enhanced fields
        ai_enhanced_count = sum(1 for info in enhanced_mapping.values() 
                              if info.get('ai_enhanced', False))
        
        print(f"   🧠 AI-enhanced fields: {ai_enhanced_count}")
        print(f"   📊 Enhancement rate: {ai_enhanced_count/len(enhanced_mapping)*100:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced mapping failed: {e}")
        print(f"   This is expected if API keys are not set")
        return False

if __name__ == "__main__":
    success = test_ai_label_extraction()
    sys.exit(0 if success else 1)
