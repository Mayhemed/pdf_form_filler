#!/usr/bin/env python3
"""
Enhanced Form Mapper - Part 4: File Management Methods
"""

import json
import os
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class FileManagementMixin:
    """Mixin class containing file management methods"""
    
    def _save_enhanced_mapping(self, mapping_json: Path, ai_labels_json: Path, 
                             enhanced_mapping: Dict, ai_labels: List):
        """Save enhanced mapping and AI labels to files"""
        try:
            # Save enhanced mapping
            with open(mapping_json, 'w', encoding='utf-8') as f:
                json.dump(enhanced_mapping, f, indent=2, ensure_ascii=False)
            
            # Save AI labels
            if ai_labels:
                from dataclasses import asdict
                labels_data = {
                    "ai_labels": [asdict(label) for label in ai_labels],
                    "metadata": {
                        "total_labels": len(ai_labels),
                        "ai_provider": self.ai_provider
                    }
                }
                
                with open(ai_labels_json, 'w', encoding='utf-8') as f:
                    json.dump(labels_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved enhanced mapping with {len(ai_labels)} AI labels")
            
        except Exception as e:
            logger.error(f"Error saving enhanced mapping: {e}")
            raise
    
    def _create_field_reference(self, reference_path: Path, enhanced_mapping: Dict):
        """Create human-readable field reference file"""
        try:
            with open(reference_path, 'w', encoding='utf-8') as f:
                f.write("ENHANCED FIELD REFERENCE\n")
                f.write("=" * 50 + "\n\n")
                
                for field_num, field_info in enhanced_mapping.items():
                    f.write(f"Field {field_num}:\n")
                    f.write(f"  Full Name: {field_info.get('full_field_name', 'N/A')}\n")
                    f.write(f"  Type: {field_info.get('field_type', 'N/A')}\n")
                    
                    if field_info.get('ai_enhanced', False):
                        f.write(f"  AI Text: {field_info.get('ai_visible_text', 'N/A')}\n")
                        f.write(f"  AI Context: {field_info.get('ai_context', 'N/A')}\n")
                        f.write(f"  AI Confidence: {field_info.get('ai_confidence', 0):.1%}\n")
                    
                    f.write(f"  Description: {field_info.get('enhanced_description', 'N/A')}\n")
                    f.write("\n")
            
            logger.info(f"Created field reference: {reference_path}")
            
        except Exception as e:
            logger.error(f"Error creating field reference: {e}")
    
    def _cache_form_mapping(self, form_name: str, enhanced_mapping: Dict, ai_labels: List):
        """Cache form mapping for future use"""
        if not self.cache_enabled:
            return
        
        try:
            cache_file = self.cache_dir / f"{form_name}_cache.json"
            
            cache_data = {
                "form_name": form_name,
                "enhanced_mapping": enhanced_mapping,
                "ai_labels": [asdict(label) for label in ai_labels] if ai_labels else [],
                "cached_at": time.time(),
                "ai_provider": self.ai_provider
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Cached form mapping: {cache_file}")
            
        except Exception as e:
            logger.error(f"Error caching form mapping: {e}")
    
    def load_cached_form_mapping(self, form_name: str) -> Dict:
        """Load cached form mapping if available"""
        if not self.cache_enabled:
            return None
        
        try:
            cache_file = self.cache_dir / f"{form_name}_cache.json"
            
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            logger.info(f"Loaded cached form mapping for {form_name}")
            return cache_data
            
        except Exception as e:
            logger.error(f"Error loading cached form mapping: {e}")
            return None
