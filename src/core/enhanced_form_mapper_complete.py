#!/usr/bin/env python3
"""
Enhanced Form Mapper - Complete Implementation
Combines all mixins into the final EnhancedUniversalFormMapper class
"""

import time
from .enhanced_form_mapper import EnhancedUniversalFormMapper
from .pdf_processing_mixin import PDFProcessingMixin
from .field_processing_mixin import FieldProcessingMixin  
from .file_management_mixin import FileManagementMixin
import logging

logger = logging.getLogger(__name__)

# Create the complete class by combining all mixins
class CompleteEnhancedFormMapper(
    EnhancedUniversalFormMapper,
    PDFProcessingMixin,
    FieldProcessingMixin,
    FileManagementMixin
):
    """
    Complete Enhanced Universal Form Mapper with all capabilities:
    - AI text label extraction
    - PDF field processing
    - Caching and file management
    - Integration with existing python_form_filler3.py
    """
    pass

# For backward compatibility and easy importing
EnhancedUniversalFormMapper = CompleteEnhancedFormMapper

# Integration function for python_form_filler3.py
def replace_create_numbered_mapping_function(form_filler_instance):
    """
    Replace the create_numbered_mapping_for_form method in an existing 
    python_form_filler3.py instance with the enhanced AI version.
    
    Args:
        form_filler_instance: Instance of the form filler class
    """
    try:
        # Create enhanced mapper
        enhanced_mapper = EnhancedUniversalFormMapper()
        
        # Replace the method
        form_filler_instance.create_numbered_mapping_for_form = (
            enhanced_mapper.create_numbered_mapping_for_form_with_ai
        )
        
        logger.info("Successfully replaced form mapping function with AI-enhanced version")
        return True
        
    except Exception as e:
        logger.error(f"Failed to replace form mapping function: {e}")
        return False

if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python enhanced_form_mapper_complete.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    # Create enhanced mapper
    mapper = EnhancedUniversalFormMapper()
    
    # Process the form
    try:
        numbered_pdf, mapping_json, ai_labels_json, enhanced_mapping = (
            mapper.create_numbered_mapping_for_form_with_ai(pdf_path)
        )
        
        print(f"Enhanced mapping created:")
        print(f"  Numbered PDF: {numbered_pdf}")
        print(f"  Mapping JSON: {mapping_json}")
        print(f"  AI Labels JSON: {ai_labels_json}")
        print(f"  Total fields: {len(enhanced_mapping)}")
        
        # Show AI-enhanced fields
        ai_enhanced_count = sum(1 for info in enhanced_mapping.values() 
                              if info.get('ai_enhanced', False))
        print(f"  AI-enhanced fields: {ai_enhanced_count}")
        
    except Exception as e:
        print(f"Error processing form: {e}")
        sys.exit(1)
