#!/usr/bin/env python3
"""
Enhanced Form Mapper - Part 3: Field Processing Methods
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class FieldProcessingMixin:
    """Mixin class containing field processing methods"""
    
    def _create_field_numbering(self, fields: List[Dict]) -> Tuple[Dict, Dict]:
        """Create numbered mapping for fields"""
        numbered_data = {}
        field_mapping = {}
        field_number = 1
        
        for field in fields:
            field_name = field['name']
            field_type = field.get('type', 'Text')
            
            # Only number fillable fields
            if field_type in ['Text', 'Choice']:
                # Create numbered entry for FDF filling
                numbered_data[field_name] = str(field_number)
                
                # Create mapping entry
                field_mapping[str(field_number)] = {
                    "full_field_name": field_name,
                    "field_type": field_type,
                    "short_name": self._create_short_name(field_name),
                    "description": field_name,  # Will be enhanced by AI
                }
                
                field_number += 1
        
        return numbered_data, field_mapping
    
    def _create_short_name(self, field_name: str) -> str:
        """Create a short name from the full field name"""
        # Remove common prefixes and clean up
        clean_name = field_name.replace('topmostSubform[0].', '')
        clean_name = clean_name.replace('[0]', '')
        clean_name = clean_name.replace('.', '_')
        
        # Take last part if it contains dots
        if '.' in clean_name:
            parts = clean_name.split('.')
            clean_name = parts[-1]
        
        return clean_name
    
    def _create_numbered_pdf(self, pdf_path: Path, output_path: Path, numbered_data: Dict):
        """Create numbered PDF by filling fields with numbers"""
        import subprocess
        import tempfile
        
        try:
            # Create FDF with numbered data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.fdf', delete=False) as fdf_file:
                self._write_fdf_file(fdf_file.name, numbered_data)
                
                # Fill PDF with numbered data
                cmd = [
                    'pdftk', str(pdf_path),
                    'fill_form', fdf_file.name,
                    'output', str(output_path),
                    'flatten'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Clean up
                os.unlink(fdf_file.name)
                
                logger.info(f"Created numbered PDF: {output_path}")
                
        except Exception as e:
            logger.error(f"Error creating numbered PDF: {e}")
            raise
    
    def _write_fdf_file(self, fdf_path: str, field_data: Dict):
        """Write FDF file with field data"""
        fdf_content = """%FDF-1.2
1 0 obj
<<
/FDF
<<
/Fields [
"""
        
        for field_name, value in field_data.items():
            fdf_content += f"<<\n/T ({field_name})\n/V ({value})\n>>\n"
        
        fdf_content += """]
>>
>>
endobj
trailer

<<
/Root 1 0 R
>>
%%EOF"""
        
        with open(fdf_path, 'w', encoding='utf-8') as f:
            f.write(fdf_content)
