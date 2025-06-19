#!/usr/bin/env python3
"""
Enhanced Form Mapper - Updated with Direct PDF Processing
Integrates the new EnhancedAITextLabelExtractor for better accuracy and performance
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import logging

logger = logging.getLogger(__name__)

class EnhancedUniversalFormMapper:
    """
    Enhanced Universal Form Mapper that integrates direct PDF processing
    with AI text label extraction for complete field understanding.
    """
    
    def __init__(self, ai_provider: str = "auto", cache_enabled: bool = True):
        """
        Initialize the Enhanced Universal Form Mapper
        
        Args:
            ai_provider: AI provider for text extraction ("openai", "anthropic", "auto")
            cache_enabled: Whether to use caching for form mappings
        """
        self.ai_provider = ai_provider
        self.cache_enabled = cache_enabled
        
        # Import enhanced AI extractor
        from .enhanced_ai_label_extractor import EnhancedAITextLabelExtractor
        self.ai_extractor = EnhancedAITextLabelExtractor(ai_provider=ai_provider)
        
        # Setup cache directory
        self.cache_dir = Path.cwd() / "cache" / "form_mappings"
        if cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def create_numbered_mapping_for_form_with_ai(self, pdf_path: Union[str, Path]) -> Tuple[Path, Path, Path, Dict]:
        """
        Enhanced version with direct PDF processing and improved AI analysis
        
        This replaces the function in python_form_filler3.py with AI-powered enhancement.
        
        Args:
            pdf_path: Path to the PDF form to analyze
            
        Returns:
            Tuple of (numbered_pdf_path, mapping_json_path, ai_labels_json_path, enhanced_mapping)
        """
        pdf_path = Path(pdf_path)
        form_name = pdf_path.stem
        base_dir = pdf_path.parent
        
        # Define output paths
        numbered_pdf = base_dir / f"{form_name}_numbered_mapping.pdf"
        mapping_json = base_dir / f"{form_name}_ai_mapping.json"
        ai_labels_json = base_dir / f"{form_name}_ai_labels.json"
        reference_txt = base_dir / f"{form_name}_field_reference.txt"
        
        logger.info(f"Creating enhanced numbered mapping for {form_name}")
        
        # STEP 1: Check if cached mapping exists and is current
        if self._should_use_cached_mapping(pdf_path, mapping_json, ai_labels_json):
            logger.info("Using cached enhanced mapping")
            return self._load_cached_mapping(numbered_pdf, mapping_json, ai_labels_json)
        
        # STEP 2: Extract form fields using pdftk
        logger.info("Extracting form fields with pdftk")
        fields = self._extract_form_fields(pdf_path)
        
        if not fields:
            raise ValueError(f"No fillable fields found in {pdf_path}")
        
        # STEP 3: Create numbered mapping
        logger.info(f"Creating numbered mapping for {len(fields)} fields")
        numbered_data, field_mapping = self._create_field_numbering(fields)
        
        # STEP 4: Generate the numbered PDF
        logger.info("Generating numbered PDF")
        self._create_numbered_pdf(pdf_path, numbered_pdf, numbered_data)
        
        # STEP 5: Extract AI text labels using enhanced direct PDF processing
        logger.info("Extracting AI text labels using enhanced direct PDF processing")
        try:
            result = self.ai_extractor.extract_ai_text_labels(numbered_pdf, field_mapping)
            enhanced_mapping = self.ai_extractor.merge_ai_labels_with_mapping(field_mapping, result.extracted_labels)
            
            # Log enhanced results
            logger.info(f"Enhanced AI extraction completed:")
            logger.info(f"  Labels extracted: {len(result.extracted_labels)}")
            logger.info(f"  Coverage: {result.verification.coverage_score:.1%}")
            logger.info(f"  Quality score: {result.verification.quality_score:.1%}")
            logger.info(f"  Processing time: {result.processing_time:.2f}s")
            logger.info(f"  Model used: {result.ai_model_used}")
            
            if result.verification.needs_review:
                logger.warning("⚠️  Extraction quality below threshold - recommend manual review")
                logger.warning(f"   Missing fields: {len(result.verification.missing_fields)}")
                logger.warning(f"   Low confidence fields: {result.verification.low_confidence_count}")
            
        except Exception as e:
            logger.warning(f"Enhanced AI label extraction failed: {e}, using basic mapping")
            enhanced_mapping = field_mapping
            result = None
        
        # STEP 6: Save enhanced mapping and AI labels
        self._save_enhanced_mapping(mapping_json, ai_labels_json, enhanced_mapping, result)
        
        # STEP 7: Create human-readable reference
        self._create_field_reference(reference_txt, enhanced_mapping)
        
        # STEP 8: Cache the results if caching is enabled
        if self.cache_enabled and result:
            self._cache_form_mapping(form_name, enhanced_mapping, result.extracted_labels)
        
        ai_enhanced_count = sum(1 for info in enhanced_mapping.values() 
                              if info.get('ai_enhanced', False))
        
        logger.info(f"Enhanced mapping created: {ai_enhanced_count}/{len(enhanced_mapping)} fields AI-enhanced")
        return numbered_pdf, mapping_json, ai_labels_json, enhanced_mapping
    
    def _should_use_cached_mapping(self, pdf_path: Path, mapping_json: Path, ai_labels_json: Path) -> bool:
        """Check if cached mapping exists and is current"""
        if not self.cache_enabled:
            return False
        
        try:
            if not (mapping_json.exists() and ai_labels_json.exists()):
                return False
            
            # Check if cache is newer than PDF
            pdf_mtime = pdf_path.stat().st_mtime
            mapping_mtime = mapping_json.stat().st_mtime
            labels_mtime = ai_labels_json.stat().st_mtime
            
            cache_valid = mapping_mtime > pdf_mtime and labels_mtime > pdf_mtime
            
            # Check cache age (max 30 days)
            current_time = time.time()
            cache_age_days = (current_time - mapping_mtime) / (24 * 3600)
            
            return cache_valid and cache_age_days < 30
            
        except Exception as e:
            logger.warning(f"Error checking cache validity: {e}")
            return False
    
    def _load_cached_mapping(self, numbered_pdf: Path, mapping_json: Path, ai_labels_json: Path) -> Tuple[Path, Path, Path, Dict]:
        """Load cached enhanced mapping"""
        try:
            with open(mapping_json, 'r', encoding='utf-8') as f:
                enhanced_mapping = json.load(f)
            
            logger.info(f"Loaded cached mapping with {len(enhanced_mapping)} fields")
            return numbered_pdf, mapping_json, ai_labels_json, enhanced_mapping
            
        except Exception as e:
            logger.error(f"Error loading cached mapping: {e}")
            raise
    
    def _save_enhanced_mapping(self, mapping_json: Path, ai_labels_json: Path, 
                             enhanced_mapping: Dict, result: Optional[object]):
        """Save enhanced mapping and AI extraction results"""
        
        # Save enhanced mapping
        with open(mapping_json, 'w', encoding='utf-8') as f:
            json.dump(enhanced_mapping, f, indent=2, ensure_ascii=False)
        
        # Save AI extraction results if available
        if result:
            self.ai_extractor.save_enhanced_results(result, mapping_json, ai_labels_json)
        else:
            # Save basic fallback data
            fallback_data = {
                'extraction_metadata': {'strategy': 'fallback', 'ai_enhanced': False},
                'extracted_labels': [],
                'processing_summary': {
                    'total_fields': len(enhanced_mapping),
                    'labels_extracted': 0,
                    'extraction_confidence': 0.5,
                    'ai_model_used': 'fallback'
                }
            }
            with open(ai_labels_json, 'w', encoding='utf-8') as f:
                json.dump(fallback_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved enhanced mapping to {mapping_json}")
        logger.info(f"Saved AI labels to {ai_labels_json}")
    
    def _create_field_reference(self, reference_txt: Path, enhanced_mapping: Dict):
        """Create human-readable field reference"""
        
        lines = [
            "PDF Form Field Reference",
            "=" * 50,
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total fields: {len(enhanced_mapping)}",
            ""
        ]
        
        ai_enhanced_count = sum(1 for info in enhanced_mapping.values() 
                              if info.get('ai_enhanced', False))
        
        lines.extend([
            f"AI-enhanced fields: {ai_enhanced_count}",
            f"Enhancement coverage: {ai_enhanced_count/len(enhanced_mapping)*100:.1f}%",
            "",
            "Field Mappings:",
            "-" * 30
        ])
        
        for field_num in sorted(enhanced_mapping.keys(), key=lambda x: int(x) if str(x).isdigit() else float('inf')):
            info = enhanced_mapping[field_num]
            
            lines.append(f"\nField {field_num}:")
            lines.append(f"  Technical name: {info.get('full_field_name', 'Unknown')}")
            
            if info.get('ai_enhanced'):
                lines.append(f"  ✅ Visible text: {info.get('ai_visible_text', 'N/A')}")
                lines.append(f"  Context: {info.get('ai_context', 'N/A')}")
                lines.append(f"  Confidence: {info.get('ai_confidence', 0.0):.1%}")
                lines.append(f"  Type: {info.get('ai_field_type_hint', 'Unknown')}")
                if info.get('ai_requirements'):
                    lines.append(f"  Requirements: {info.get('ai_requirements')}")
            else:
                lines.append(f"  ⚠️  Basic mapping: {info.get('short_name', 'Unknown')}")
                lines.append(f"  Type: {info.get('field_type', 'Unknown')}")
        
        with open(reference_txt, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        logger.info(f"Created field reference: {reference_txt}")
    
    def _cache_form_mapping(self, form_name: str, enhanced_mapping: Dict, ai_labels: List):
        """Cache form mapping for future use"""
        if not self.cache_enabled:
            return
        
        try:
            cache_file = self.cache_dir / f"{form_name}_cache.json"
            
            cache_data = {
                'timestamp': time.time(),
                'form_name': form_name,
                'enhanced_mapping': enhanced_mapping,
                'ai_labels_count': len(ai_labels),
                'ai_provider': self.ai_provider,
                'cache_version': '2.0'
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Cached form mapping: {cache_file}")
            
        except Exception as e:
            logger.warning(f"Failed to cache form mapping: {e}")
