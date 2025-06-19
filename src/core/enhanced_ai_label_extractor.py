#!/usr/bin/env python3
"""
Enhanced AI Text Label Extractor - Direct PDF Processing
Author: Assistant
Description: Enhanced version that processes PDFs directly with AI models,
             implements multi-pass analysis, and includes robust fallback strategies
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class ExtractedLabel:
    """Represents an AI-extracted text label for a form field"""
    field_number: str
    visible_text: str
    context: str
    confidence: float
    position: Dict[str, float]  # x, y, width, height (as percentages)
    field_type_hint: str  # text, choice, checkbox, etc.
    requirements: Optional[str] = None
    validation_notes: Optional[str] = None

@dataclass 
class ExtractionVerification:
    """Results of AI extraction verification"""
    coverage_score: float
    missing_fields: List[str]
    extra_fields: List[str]
    low_confidence_count: int
    needs_review: bool
    quality_score: float

@dataclass
class AILabelExtractionResult:
    """Complete result of AI label extraction process"""
    form_name: str
    total_fields: int
    extracted_labels: List[ExtractedLabel]
    extraction_confidence: float
    processing_time: float
    ai_model_used: str
    extraction_metadata: Dict
    verification: ExtractionVerification

class EnhancedAITextLabelExtractor:
    """
    Enhanced AI Text Label Extractor that processes PDFs directly and implements
    multi-pass analysis with robust fallback strategies for maximum accuracy.
    """
    
    def __init__(self, ai_provider: str = "openai", model: str = None, api_key: str = None):
        """
        Initialize the Enhanced AI Text Label Extractor
        
        Args:
            ai_provider: "openai", "anthropic", or "auto" for best available
            model: Specific model to use (defaults to best model for provider)
            api_key: API key for the provider (or None to use environment variable)
        """
        self.ai_provider = ai_provider.lower()
        self.api_key = api_key or self._get_api_key()
        self.model = model or self._get_default_model()
        
        # Available AI strategies
        self.ai_strategies = [
            ("openai", "gpt-4-turbo-preview"),
            ("anthropic", "claude-3-opus-20240229"), 
            ("openai", "gpt-4"),
            ("anthropic", "claude-3-sonnet-20240229"),
        ]
        
        # Initialize primary client
        self._init_ai_client()
    
    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment variables"""
        if self.ai_provider == "openai":
            return os.getenv("OPENAI_API_KEY")
        elif self.ai_provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        elif self.ai_provider == "auto":
            # Return first available
            return os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        return None
    
    def _get_default_model(self) -> str:
        """Get default model for the provider"""
        if self.ai_provider == "openai":
            return "gpt-4-turbo-preview"
        elif self.ai_provider == "anthropic":
            return "claude-3-opus-20240229"
        elif self.ai_provider == "auto":
            if os.getenv("OPENAI_API_KEY"):
                return "gpt-4-turbo-preview"
            elif os.getenv("ANTHROPIC_API_KEY"):
                return "claude-3-opus-20240229"
        return "gpt-4-turbo-preview"
    
    def _init_ai_client(self):
        """Initialize AI client based on provider"""
        try:
            if self.ai_provider in ["openai", "auto"] and os.getenv("OPENAI_API_KEY"):
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
                self.ai_provider = "openai"
            elif self.ai_provider in ["anthropic", "auto"] and os.getenv("ANTHROPIC_API_KEY"):
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.ai_provider = "anthropic"
            else:
                raise ValueError(f"No API key available for provider: {self.ai_provider}")
        except ImportError as e:
            raise ImportError(f"Required AI library not installed: {e}")
    
    def extract_ai_text_labels(self, numbered_pdf_path: Union[str, Path], 
                              field_mapping: Dict) -> AILabelExtractionResult:
        """
        Extract visible text labels from a numbered PDF using enhanced AI processing
        
        Args:
            numbered_pdf_path: Path to the numbered PDF (with "1", "2", "3" in fields)
            field_mapping: Basic field mapping from create_numbered_mapping_for_form
            
        Returns:
            AILabelExtractionResult with comprehensive label information
        """
        start_time = time.time()
        pdf_path = Path(numbered_pdf_path)
        
        logger.info(f"Starting enhanced AI text label extraction for {pdf_path.name}")
        
        # Try multiple extraction strategies for best results
        extraction_result = self._extract_with_fallback_strategies(pdf_path, field_mapping)
        
        # Verify extraction quality
        verification = self._verify_ai_extraction(extraction_result.extracted_labels, field_mapping)
        
        # Calculate processing metrics
        processing_time = time.time() - start_time
        
        # Create comprehensive result
        result = AILabelExtractionResult(
            form_name=pdf_path.stem,
            total_fields=len(field_mapping),
            extracted_labels=extraction_result.extracted_labels,
            extraction_confidence=extraction_result.extraction_confidence,
            processing_time=processing_time,
            ai_model_used=extraction_result.ai_model_used,
            extraction_metadata={
                "ai_provider": self.ai_provider,
                "extraction_strategy": extraction_result.extraction_metadata.get("strategy", "direct"),
                "labels_extracted": len(extraction_result.extracted_labels),
                "field_coverage": len(extraction_result.extracted_labels) / len(field_mapping) if field_mapping else 0,
                "fallback_used": extraction_result.extraction_metadata.get("fallback_used", False)
            },
            verification=verification
        )
        
        logger.info(f"Enhanced AI extraction completed: {len(extraction_result.extracted_labels)} labels in {processing_time:.2f}s")
        logger.info(f"Quality metrics - Coverage: {verification.coverage_score:.1%}, Quality: {verification.quality_score:.1%}")
        
        return result
    
    def _extract_with_fallback_strategies(self, pdf_path: Path, field_mapping: Dict) -> AILabelExtractionResult:
        """Try multiple AI providers and approaches for best results"""
        
        # Primary strategy: Direct PDF processing
        try:
            result = self._extract_direct_pdf(pdf_path, field_mapping)
            verification = self._verify_ai_extraction(result.extracted_labels, field_mapping)
            
            if verification.quality_score > 0.8:
                logger.info(f"Primary strategy successful with quality score: {verification.quality_score:.1%}")
                return result
        except Exception as e:
            logger.warning(f"Primary strategy failed: {e}")
        
        # Fallback strategies
        strategies = [
            ("multi_pass", "Multi-pass analysis"),
            ("enhanced_prompt", "Enhanced prompt strategy"), 
            ("ocr_assisted", "OCR-assisted analysis"),
        ]
        
        for strategy_name, strategy_desc in strategies:
            try:
                logger.info(f"Trying fallback strategy: {strategy_desc}")
                
                if strategy_name == "multi_pass":
                    result = self._multi_pass_extraction(pdf_path, field_mapping)
                elif strategy_name == "enhanced_prompt":
                    result = self._extract_with_enhanced_prompt(pdf_path, field_mapping)
                elif strategy_name == "ocr_assisted":
                    result = self._extract_with_ocr_assistance(pdf_path, field_mapping)
                
                verification = self._verify_ai_extraction(result.extracted_labels, field_mapping)
                
                if verification.quality_score > 0.7:
                    logger.info(f"Fallback strategy '{strategy_desc}' successful: {verification.quality_score:.1%}")
                    result.extraction_metadata["fallback_used"] = True
                    result.extraction_metadata["strategy"] = strategy_name
                    return result
                    
            except Exception as e:
                logger.warning(f"Fallback strategy '{strategy_desc}' failed: {e}")
                continue
        
        # Final fallback: Basic pattern matching
        logger.warning("All AI strategies failed, using pattern matching fallback")
        return self._pattern_matching_fallback(pdf_path, field_mapping)
    
    def _extract_direct_pdf(self, pdf_path: Path, field_mapping: Dict) -> AILabelExtractionResult:
        """Extract labels by sending PDF directly to AI"""
        
        # Create enhanced prompt for direct PDF processing
        prompt = self._create_enhanced_pdf_prompt(field_mapping)
        
        # Process PDF directly with AI
        if self.ai_provider == "openai":
            response = self._extract_with_openai_pdf(prompt, pdf_path)
        elif self.ai_provider == "anthropic":
            response = self._extract_with_anthropic_pdf(prompt, pdf_path)
        else:
            raise ValueError(f"Unsupported provider for direct PDF: {self.ai_provider}")
        
        # Parse AI response
        extracted_labels = self._parse_ai_response(response)
        
        # Calculate confidence
        avg_confidence = sum(label.confidence for label in extracted_labels) / len(extracted_labels) if extracted_labels else 0.0
        
        return AILabelExtractionResult(
            form_name=pdf_path.stem,
            total_fields=len(field_mapping),
            extracted_labels=extracted_labels,
            extraction_confidence=avg_confidence,
            processing_time=0.0,  # Will be set by caller
            ai_model_used=self.model,
            extraction_metadata={"strategy": "direct_pdf"},
            verification=None  # Will be set by caller
        )
    
    def _create_enhanced_pdf_prompt(self, field_mapping: Dict) -> str:
        """Create comprehensive prompt for direct PDF processing"""
        
        # Create field reference
        field_reference = self._format_field_reference(field_mapping)
        
        return f"""You are analyzing a PDF form with NUMBERED FIELDS for comprehensive data extraction mapping.

CRITICAL TASK: This PDF form has numbered fields (1, 2, 3, etc.) that need to be mapped to their visible labels and context.

NUMBERED FIELD ANALYSIS REQUIREMENTS:
1. LOCATE ALL NUMBERS: Find every "1", "2", "3", etc. that appears in or near form fields
2. IDENTIFY LABELS: For each number, determine the associated text label(s) that describe what should be entered
3. UNDERSTAND CONTEXT: Note any instructions, requirements, field types, or validation hints
4. ASSESS FIELD TYPES: Determine if each field is text input, dropdown, checkbox, date, signature, etc.
5. MAP RELATIONSHIPS: Connect numbers to their corresponding input areas and related text

EXPECTED NUMBERED FIELDS:
{field_reference}

ENHANCED ANALYSIS INSTRUCTIONS:
- Look for numbers in circles, boxes, or adjacent to input fields
- Include ALL text that helps understand what data belongs in each field
- Note required vs optional fields, formatting requirements, examples
- Identify field types (text, choice, checkbox, signature, date, currency)
- Pay attention to section headers and field groupings
- Include validation hints like "MM/DD/YYYY", "Required", "$", etc.

OUTPUT FORMAT (JSON):
{{
  "field_analysis": {{
    "total_numbers_found": 15,
    "extraction_notes": "Analysis approach and any issues encountered",
    "field_mappings": [
      {{
        "field_number": "1",
        "visible_text": "Petitioner's Full Legal Name",
        "context": "Enter the complete legal name of the person filing the petition",
        "field_type": "text_input",
        "requirements": "Required field, must match court records exactly",
        "position": {{"x": 0.1, "y": 0.15, "width": 0.4, "height": 0.03}},
        "confidence": 0.95,
        "validation_notes": "Full legal name as it appears on identification",
        "section": "Party Information"
      }},
      {{
        "field_number": "2", 
        "visible_text": "Date of Birth",
        "context": "Petitioner's date of birth in MM/DD/YYYY format",
        "field_type": "date_input",
        "requirements": "Required field, standard date format",
        "position": {{"x": 0.5, "y": 0.15, "width": 0.2, "height": 0.03}},
        "confidence": 0.92,
        "validation_notes": "Format: MM/DD/YYYY",
        "section": "Party Information"
      }}
    ]
  }}
}}

QUALITY REQUIREMENTS:
- Only include fields where you can clearly identify a number and its associated label
- Be conservative with confidence scores - if uncertain, mark confidence lower
- Include comprehensive context that would help someone understand what data to enter
- Group related fields by section when possible
- Note any ambiguities or unclear relationships in extraction_notes

ACCURACY FOCUS: It's better to have fewer high-confidence mappings than many uncertain ones."""
    
    def _format_field_reference(self, field_mapping: Dict) -> str:
        """Format field mapping reference for AI prompt"""
        field_info = []
        for num, info in field_mapping.items():
            field_name = info.get('full_field_name', 'Unknown')
            field_type = info.get('field_type', 'Unknown')
            short_name = info.get('short_name', '')
            field_info.append(f"  {num}: {field_name} ({field_type}) [{short_name}]")
        
        # Limit to first 25 fields to keep prompt manageable
        if len(field_info) > 25:
            field_info = field_info[:25] + [f"  ... and {len(field_info) - 25} more fields"]
        
        return "\n".join(field_info)
    
    def _extract_with_openai_pdf(self, prompt: str, pdf_path: Path) -> str:
        """Extract labels using OpenAI with direct PDF processing"""
        
        # Read PDF file
        with open(pdf_path, 'rb') as pdf_file:
            pdf_data = pdf_file.read()
        
        # Import and use llm_client for PDF processing
        try:
            import sys
            sys.path.append(str(Path.cwd()))
            import llm_client
            
            # Use llm_client's PDF processing capability
            response = llm_client.generate_with_openai(
                self.model, 
                prompt, 
                str(pdf_path),  # PDF path for direct processing
                None  # No mapping PDF needed since we're analyzing the numbered PDF directly
            )
            
            return response
            
        except ImportError:
            # Fallback to direct OpenAI API call
            import base64
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "text", 
                                "text": f"Please analyze the attached PDF file: {pdf_path.name}"
                            }
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            return response.choices[0].message.content
    
    def _extract_with_anthropic_pdf(self, prompt: str, pdf_path: Path) -> str:
        """Extract labels using Anthropic Claude with direct PDF processing"""
        
        try:
            import sys
            sys.path.append(str(Path.cwd()))
            import llm_client
            
            # Use llm_client's Claude PDF processing capability
            response = llm_client.generate_with_claude(
                self.model,
                prompt,
                str(pdf_path),  # PDF path for direct processing
                None  # No mapping PDF needed
            )
            
            return response
            
        except ImportError:
            # Fallback to direct Anthropic API call with PDF
            with open(pdf_path, 'rb') as pdf_file:
                pdf_data = pdf_file.read()
            
            import base64
            pdf_b64 = base64.b64encode(pdf_data).decode('utf-8')
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": pdf_b64
                                }
                            }
                        ]
                    }
                ]
            )
            
            return response.content[0].text
        missing_fields = list(expected_fields - extracted_fields)
        extra_fields = list(extracted_fields - expected_fields)
        
        # Coverage score
        coverage_score = len(extracted_fields & expected_fields) / len(expected_fields) if expected_fields else 0.0
        
        # Quality checks
        low_confidence_fields = [label for label in ai_labels if label.confidence < 0.7]
        high_confidence_fields = [label for label in ai_labels if label.confidence >= 0.9]
        
        # Overall quality score
        confidence_scores = [label.confidence for label in ai_labels]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        # Quality factors
        completeness_factor = coverage_score
        confidence_factor = avg_confidence
        consistency_factor = 1.0 - (len(low_confidence_fields) / len(ai_labels)) if ai_labels else 0.0
        
        quality_score = (completeness_factor * 0.4 + confidence_factor * 0.4 + consistency_factor * 0.2)
        
        # Determine if review is needed
        needs_review = (
            coverage_score < 0.8 or 
            len(low_confidence_fields) > len(ai_labels) * 0.3 or
            quality_score < 0.7
        )
        
        return ExtractionVerification(
            coverage_score=coverage_score,
            missing_fields=missing_fields,
            extra_fields=extra_fields,
            low_confidence_count=len(low_confidence_fields),
            needs_review=needs_review,
            quality_score=quality_score
        )
    
    def merge_ai_labels_with_mapping(self, field_mapping: Dict, ai_labels: List[ExtractedLabel]) -> Dict:
        """Merge AI-extracted labels with existing field mapping"""
        
        enhanced_mapping = {}
        
        # Create lookup for AI labels by field number
        ai_labels_dict = {label.field_number: label for label in ai_labels}
        
        for field_num, field_info in field_mapping.items():
            field_num_str = str(field_num)
            enhanced_info = field_info.copy()
            
            # Add AI enhancement if available
            if field_num_str in ai_labels_dict:
                ai_label = ai_labels_dict[field_num_str]
                
                enhanced_info.update({
                    'ai_enhanced': True,
                    'ai_visible_text': ai_label.visible_text,
                    'ai_context': ai_label.context,
                    'ai_confidence': ai_label.confidence,
                    'ai_field_type_hint': ai_label.field_type_hint,
                    'ai_requirements': ai_label.requirements,
                    'ai_validation_notes': ai_label.validation_notes,
                    'ai_position': ai_label.position,
                    'enhanced_description': f"{ai_label.visible_text}: {ai_label.context}"
                })
            else:
                # No AI enhancement available
                enhanced_info.update({
                    'ai_enhanced': False,
                    'ai_visible_text': field_info.get('short_name', field_info.get('full_field_name', 'Unknown')),
                    'ai_context': f"Technical field: {field_info.get('full_field_name', 'Unknown')}",
                    'ai_confidence': 0.5,
                    'enhanced_description': f"Field {field_num}: {field_info.get('short_name', 'Unknown')}"
                })
            
            enhanced_mapping[field_num] = enhanced_info
        
        return enhanced_mapping
    
    def save_enhanced_results(self, results: AILabelExtractionResult, 
                            mapping_json_path: Path, ai_labels_json_path: Path):
        """Save enhanced extraction results to files"""
        
        # Save AI labels
        ai_labels_data = {
            'extraction_metadata': asdict(results.extraction_metadata),
            'verification': asdict(results.verification),
            'extracted_labels': [asdict(label) for label in results.extracted_labels],
            'processing_summary': {
                'total_fields': results.total_fields,
                'labels_extracted': len(results.extracted_labels),
                'extraction_confidence': results.extraction_confidence,
                'processing_time': results.processing_time,
                'ai_model_used': results.ai_model_used,
                'quality_score': results.verification.quality_score,
                'coverage_score': results.verification.coverage_score
            }
        }
        
        with open(ai_labels_json_path, 'w', encoding='utf-8') as f:
            json.dump(ai_labels_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved enhanced AI extraction results to {ai_labels_json_path}")


# Integration function for backward compatibility
def enhance_numbered_mapping_with_ai(numbered_pdf_path: Union[str, Path], 
                                   field_mapping: Dict,
                                   ai_provider: str = "openai") -> Tuple[Dict, List[ExtractedLabel]]:
    """
    Enhance existing numbered mapping with AI-extracted text labels
    
    This function integrates with the existing create_numbered_mapping_for_form function
    to add AI-powered text label extraction capabilities.
    
    Args:
        numbered_pdf_path: Path to the numbered PDF
        field_mapping: Basic field mapping from pdftk
        ai_provider: AI provider to use ("openai", "anthropic", or "auto")
        
    Returns:
        Tuple of (enhanced_mapping, ai_labels)
    """
    try:
        # Initialize enhanced AI extractor
        extractor = EnhancedAITextLabelExtractor(ai_provider=ai_provider)
        
        # Extract AI labels using enhanced processing
        result = extractor.extract_ai_text_labels(numbered_pdf_path, field_mapping)
        
        # Merge with existing mapping
        enhanced_mapping = extractor.merge_ai_labels_with_mapping(field_mapping, result.extracted_labels)
        
        # Log results
        logger.info(f"Enhanced mapping completed:")
        logger.info(f"  Total fields: {len(enhanced_mapping)}")
        logger.info(f"  AI-enhanced fields: {len(result.extracted_labels)}")
        logger.info(f"  Coverage: {result.verification.coverage_score:.1%}")
        logger.info(f"  Quality score: {result.verification.quality_score:.1%}")
        
        if result.verification.needs_review:
            logger.warning("Extraction quality below threshold - manual review recommended")
        
        return enhanced_mapping, result.extracted_labels
        
    except Exception as e:
        logger.error(f"Enhanced AI extraction failed: {e}")
        # Fallback to basic mapping
        return field_mapping, []


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python enhanced_ai_label_extractor.py <numbered_pdf_path>")
        sys.exit(1)
    
    numbered_pdf_path = sys.argv[1]
    
    # Mock field mapping for testing
    test_field_mapping = {
        1: {'full_field_name': 'petitioner_name', 'short_name': 'Petitioner', 'field_type': 'Text'},
        2: {'full_field_name': 'respondent_name', 'short_name': 'Respondent', 'field_type': 'Text'},
        3: {'full_field_name': 'case_number', 'short_name': 'Case Number', 'field_type': 'Text'},
        4: {'full_field_name': 'court_county', 'short_name': 'County', 'field_type': 'Text'},
        5: {'full_field_name': 'attorney_name', 'short_name': 'Attorney', 'field_type': 'Text'}
    }
    
    # Test enhanced extraction
    try:
        extractor = EnhancedAITextLabelExtractor(ai_provider="auto")
        result = extractor.extract_ai_text_labels(numbered_pdf_path, test_field_mapping)
        
        print(f"\n🎯 Enhanced AI Extraction Results:")
        print(f"   Form: {result.form_name}")
        print(f"   Model: {result.ai_model_used}")
        print(f"   Processing time: {result.processing_time:.2f}s")
        print(f"   Labels extracted: {len(result.extracted_labels)}")
        print(f"   Coverage: {result.verification.coverage_score:.1%}")
        print(f"   Quality score: {result.verification.quality_score:.1%}")
        
        if result.verification.needs_review:
            print(f"   ⚠️  Manual review recommended")
        else:
            print(f"   ✅ Quality meets standards")
        
        print(f"\n📋 Extracted Labels:")
        for label in result.extracted_labels:
            print(f"   Field {label.field_number}: {label.visible_text}")
            print(f"      Context: {label.context}")
            print(f"      Confidence: {label.confidence:.1%}")
            print(f"      Type: {label.field_type_hint}")
            if label.requirements:
                print(f"      Requirements: {label.requirements}")
            print()
        
        # Test integration function
        enhanced_mapping, ai_labels = enhance_numbered_mapping_with_ai(
            numbered_pdf_path, test_field_mapping, "auto"
        )
        
        print(f"🔗 Integration Test Results:")
        print(f"   Enhanced fields: {len(enhanced_mapping)}")
        ai_enhanced_count = sum(1 for info in enhanced_mapping.values() 
                              if info.get('ai_enhanced', False))
        print(f"   AI-enhanced: {ai_enhanced_count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
