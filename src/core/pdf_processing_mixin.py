#!/usr/bin/env python3
"""
Enhanced Form Mapper - Part 2: PDF Processing Methods
"""

import subprocess
import tempfile
import os
import re
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

# Add methods to EnhancedUniversalFormMapper class
class PDFProcessingMixin:
    """Mixin class containing PDF processing methods"""
    
    def _should_use_cached_mapping(self, pdf_path: Path, mapping_json: Path, 
                                 ai_labels_json: Path) -> bool:
        """Check if cached mapping exists and is newer than source PDF"""
        if not self.cache_enabled:
            return False
        
        if not (mapping_json.exists() and ai_labels_json.exists()):
            return False
        
        pdf_mtime = pdf_path.stat().st_mtime
        mapping_mtime = mapping_json.stat().st_mtime
        
        return mapping_mtime > pdf_mtime
    
    def _load_cached_mapping(self, numbered_pdf: Path, mapping_json: Path, 
                           ai_labels_json: Path) -> tuple:
        """Load cached mapping from files"""
        try:
            import json
            with open(mapping_json, 'r', encoding='utf-8') as f:
                enhanced_mapping = json.load(f)
            
            return numbered_pdf, mapping_json, ai_labels_json, enhanced_mapping
            
        except Exception as e:
            logger.error(f"Error loading cached mapping: {e}")
            raise
    
    def _extract_form_fields(self, pdf_path: Path) -> List[Dict]:
        """Extract form fields using pdftk"""
        try:
            # Use pdftk to extract field information
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.fdf', delete=False) as temp_file:
                cmd = ['pdftk', str(pdf_path), 'generate_fdf', 'output', temp_file.name]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Parse FDF to get field information
                fields = self._parse_fdf_fields(temp_file.name)
                
                # Clean up
                os.unlink(temp_file.name)
                
                return fields
                
        except subprocess.CalledProcessError as e:
            logger.error(f"pdftk error: {e}")
            raise ValueError(f"Failed to extract fields from PDF: {e}")
        except FileNotFoundError:
            logger.error("pdftk not found")
            raise ValueError("pdftk is required but not installed")
    
    def _parse_fdf_fields(self, fdf_path: str) -> List[Dict]:
        """Parse FDF file to extract field information"""
        fields = []
        
        try:
            with open(fdf_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract field definitions (simplified parsing)
            field_pattern = r'/T\s*\(([^)]+)\)\s*/V\s*\(([^)]*)\)\s*/Ff\s*(\d+)'
            
            for match in re.finditer(field_pattern, content):
                field_name = match.group(1)
                field_value = match.group(2) 
                field_flags = int(match.group(3)) if match.group(3) else 0
                
                # Determine field type from flags
                field_type = self._determine_field_type(field_flags)
                
                fields.append({
                    'name': field_name,
                    'value': field_value,
                    'flags': field_flags,
                    'type': field_type
                })
            
            return fields
            
        except Exception as e:
            logger.error(f"Error parsing FDF: {e}")
            return []
    
    def _determine_field_type(self, flags: int) -> str:
        """Determine field type from PDF field flags"""
        # PDF field flag constants (simplified)
        if flags & 0x01000000:  # Choice field
            return "Choice"
        elif flags & 0x02000000:  # Combo box
            return "Choice"
        else:
            return "Text"
