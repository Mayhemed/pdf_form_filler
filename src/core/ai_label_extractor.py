#!/usr/bin/env python3
"""
AI Text Label Extractor - Enhanced Field Mapping with Vision Models
Author: Assistant
Description: Uses AI vision models to extract visible text labels from numbered PDF forms
"""

import json
import os
import base64
import tempfile
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
    position: Dict[str, float]  # x, y, width, height
    field_type_hint: str  # text, choice, checkbox, etc.

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

class AITextLabelExtractor:
    """
    Enhanced text label extractor using AI vision models to analyze numbered PDF forms
    and extract comprehensive field information including visible labels, context, and relationships.
    """
    
    def __init__(self, ai_provider: str = "openai", model: str = None, api_key: str = None):
        """
        Initialize the AI Text Label Extractor
        
        Args:
            ai_provider: "openai", "anthropic", or "local"
            model: Specific model to use (defaults to best vision model for provider)
            api_key: API key for the provider (or None to use environment variable)
        """
        self.ai_provider = ai_provider.lower()
        self.api_key = api_key or self._get_api_key()
        self.model = model or self._get_default_model()
        
        # Import appropriate client
        if self.ai_provider == "openai":
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
        elif self.ai_provider == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            raise ValueError(f"Unsupported AI provider: {ai_provider}")
    
    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment variables"""
        if self.ai_provider == "openai":
            return os.getenv("OPENAI_API_KEY")
        elif self.ai_provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY")
        return None
    
    def _get_default_model(self) -> str:
        """Get default vision model for the provider"""
        if self.ai_provider == "openai":
            return "gpt-4-vision-preview"
        elif self.ai_provider == "anthropic":
            return "claude-3-opus-20240229"
        return "gpt-4-vision-preview"
    
    def extract_ai_text_labels(self, numbered_pdf_path: Union[str, Path], 
                              field_mapping: Dict) -> AILabelExtractionResult:
        """
        Extract visible text labels from a numbered PDF using AI vision models
        
        Args:
            numbered_pdf_path: Path to the numbered PDF (with "1", "2", "3" in fields)
            field_mapping: Basic field mapping from create_numbered_mapping_for_form
            
        Returns:
            AILabelExtractionResult with comprehensive label information
        """
        import time
        start_time = time.time()
        
        logger.info(f"Starting AI text label extraction for {numbered_pdf_path}")
        
        # Convert PDF to images for AI processing
        pdf_images = self._convert_pdf_to_images(numbered_pdf_path)
        
        # Extract labels using AI vision
        extracted_labels = []
        total_confidence = 0.0
        
        for page_num, image_data in enumerate(pdf_images):
            page_labels = self._extract_labels_from_image(
                image_data, field_mapping, page_num
            )
            extracted_labels.extend(page_labels)
            
            # Calculate average confidence
            if page_labels:
                page_confidence = sum(label.confidence for label in page_labels) / len(page_labels)
                total_confidence += page_confidence
        
        # Calculate overall confidence
        avg_confidence = total_confidence / len(pdf_images) if pdf_images else 0.0
        processing_time = time.time() - start_time
        
        # Create result
        result = AILabelExtractionResult(
            form_name=Path(numbered_pdf_path).stem,
            total_fields=len(field_mapping),
            extracted_labels=extracted_labels,
            extraction_confidence=avg_confidence,
            processing_time=processing_time,
            ai_model_used=self.model,
            extraction_metadata={
                "ai_provider": self.ai_provider,
                "pages_processed": len(pdf_images),
                "labels_extracted": len(extracted_labels),
                "field_coverage": len(extracted_labels) / len(field_mapping) if field_mapping else 0
            }
        )
        
        logger.info(f"AI extraction completed: {len(extracted_labels)} labels in {processing_time:.2f}s")
        return result
    
    def _convert_pdf_to_images(self, pdf_path: Union[str, Path]) -> List[bytes]:
        """
        Convert PDF pages to images for AI processing
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of image data as bytes
        """
        try:
            # Try using pdf2image (preferred method)
            from pdf2image import convert_from_path
            
            # Convert PDF to PIL Images
            pil_images = convert_from_path(str(pdf_path), dpi=200)
            
            # Convert PIL Images to bytes
            image_data_list = []
            for pil_image in pil_images:
                import io
                img_byte_arr = io.BytesIO()
                pil_image.save(img_byte_arr, format='PNG')
                image_data_list.append(img_byte_arr.getvalue())
            
            return image_data_list
            
        except ImportError:
            logger.warning("pdf2image not available, trying alternative method")
            return self._convert_pdf_with_pypdf(pdf_path)
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            return []
    
    def _convert_pdf_with_pypdf(self, pdf_path: Union[str, Path]) -> List[bytes]:
        """Fallback PDF to image conversion using PyPDF2 + Pillow"""
        # This would require additional implementation for image extraction from PDF
        # For now, return empty list as fallback
        logger.warning("Alternative PDF conversion not implemented")
        return []
    
    def _extract_labels_from_image(self, image_data: bytes, field_mapping: Dict, 
                                 page_num: int) -> List[ExtractedLabel]:
        """
        Extract text labels from a single page image using AI vision
        
        Args:
            image_data: Image data as bytes
            field_mapping: Field mapping with field numbers
            page_num: Page number for context
            
        Returns:
            List of extracted labels for this page
        """
        # Create the AI vision prompt
        prompt = self._create_label_extraction_prompt(field_mapping, page_num)
        
        # Encode image to base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        try:
            if self.ai_provider == "openai":
                response = self._extract_with_openai(prompt, image_b64)
            elif self.ai_provider == "anthropic":
                response = self._extract_with_anthropic(prompt, image_b64)
            else:
                raise ValueError(f"Unsupported provider: {self.ai_provider}")
            
            # Parse the AI response into ExtractedLabel objects
            return self._parse_ai_response(response, page_num)
            
        except Exception as e:
            logger.error(f"Error extracting labels from page {page_num}: {e}")
            return []
    
    def _create_label_extraction_prompt(self, field_mapping: Dict, page_num: int) -> str:
        """
        Create a comprehensive prompt for AI label extraction
        
        Args:
            field_mapping: Field mapping with numbered fields
            page_num: Current page number
            
        Returns:
            Detailed prompt for AI vision model
        """
        field_info = []
        for num, info in field_mapping.items():
            field_info.append(f"  {num}: {info.get('full_field_name', 'Unknown')} ({info.get('field_type', 'Unknown')})")
        
        field_list = "\n".join(field_info[:20])  # Limit to first 20 for prompt size
        
        return f"""You are an expert form analysis AI. Analyze this PDF form page and extract comprehensive information about each numbered field.

TASK: For each visible number (1, 2, 3, etc.) in the form fields, identify:
1. The visible text label(s) associated with that field
2. Any instructions or context text near the field  
3. The type of field (text input, checkbox, dropdown, etc.)
4. The approximate position on the page
5. Any validation hints or formatting requirements

FIELD REFERENCE (Page {page_num + 1}):
{field_list}

ANALYSIS REQUIREMENTS:
- Look for numbers "1", "2", "3", etc. that appear in form fields
- For each number, find the closest text labels that describe what should be entered
- Include context like "Required", "Optional", date formats, etc.
- Note field types: text, choice/dropdown, checkbox, signature, date, etc.
- Estimate position as percentages (x, y, width, height) from top-left

OUTPUT FORMAT (JSON):
{{
  "extracted_labels": [
    {{
      "field_number": "1",
      "visible_text": "First Name",
      "context": "Required field for applicant's first name",
      "confidence": 0.95,
      "position": {{"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05}},
      "field_type_hint": "text"
    }},
    {{
      "field_number": "2", 
      "visible_text": "Date of Birth",
      "context": "Enter as MM/DD/YYYY format",
      "confidence": 0.92,
      "position": {{"x": 0.5, "y": 0.2, "width": 0.2, "height": 0.05}},
      "field_type_hint": "date"
    }}
  ]
}}

IMPORTANT:
- Only include fields where you can clearly see a number in the form field
- Focus on accuracy - if unsure about a label, mark confidence lower
- Include ALL visible text that helps understand what the field is for
- Look for subtle text like "(optional)", formatting hints, examples, etc.
"""
    
    def _extract_with_openai(self, prompt: str, image_b64: str) -> str:
        """Extract labels using OpenAI GPT-4 Vision"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096,
                temperature=0.1
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def _extract_with_anthropic(self, prompt: str, image_b64: str) -> str:
        """Extract labels using Anthropic Claude Vision"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_b64
                                }
                            },
                            {"type": "text", "text": prompt}
                        ]
                    }
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    def _parse_ai_response(self, response: str, page_num: int) -> List[ExtractedLabel]:
        """
        Parse AI response into ExtractedLabel objects
        
        Args:
            response: Raw AI response text
            page_num: Page number for context
            
        Returns:
            List of parsed ExtractedLabel objects
        """
        try:
            # Extract JSON from response (handle cases where AI adds extra text)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning(f"No JSON found in AI response for page {page_num}")
                return []
            
            json_text = response[json_start:json_end]
            parsed_data = json.loads(json_text)
            
            extracted_labels = []
            for label_data in parsed_data.get("extracted_labels", []):
                try:
                    label = ExtractedLabel(
                        field_number=str(label_data.get("field_number", "")),
                        visible_text=label_data.get("visible_text", ""),
                        context=label_data.get("context", ""),
                        confidence=float(label_data.get("confidence", 0.0)),
                        position=label_data.get("position", {}),
                        field_type_hint=label_data.get("field_type_hint", "text")
                    )
                    extracted_labels.append(label)
                except Exception as e:
                    logger.warning(f"Error parsing label data: {e}")
                    continue
            
            return extracted_labels
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.debug(f"Raw response: {response}")
            return []
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return []
    
    def merge_ai_labels_with_mapping(self, field_mapping: Dict, 
                                   ai_labels: List[ExtractedLabel]) -> Dict:
        """
        Merge AI-extracted labels with basic field mapping to create enhanced mapping
        
        Args:
            field_mapping: Basic field mapping from pdftk
            ai_labels: AI-extracted label information
            
        Returns:
            Enhanced field mapping with AI-extracted information
        """
        enhanced_mapping = {}
        
        # Create lookup for AI labels
        ai_label_lookup = {label.field_number: label for label in ai_labels}
        
        for field_num, field_info in field_mapping.items():
            enhanced_info = field_info.copy()
            
            # Add AI-extracted information if available
            if field_num in ai_label_lookup:
                ai_label = ai_label_lookup[field_num]
                
                enhanced_info.update({
                    "ai_visible_text": ai_label.visible_text,
                    "ai_context": ai_label.context,
                    "ai_confidence": ai_label.confidence,
                    "ai_position": ai_label.position,
                    "ai_field_type_hint": ai_label.field_type_hint,
                    "enhanced_description": self._create_enhanced_description(field_info, ai_label),
                    "ai_enhanced": True
                })
            else:
                enhanced_info.update({
                    "ai_visible_text": "",
                    "ai_context": "",
                    "ai_confidence": 0.0,
                    "ai_position": {},
                    "ai_field_type_hint": "unknown",
                    "enhanced_description": field_info.get('full_field_name', ''),
                    "ai_enhanced": False
                })
            
            enhanced_mapping[field_num] = enhanced_info
        
        return enhanced_mapping
    
    def _create_enhanced_description(self, field_info: Dict, ai_label: ExtractedLabel) -> str:
        """
        Create an enhanced field description combining pdftk info and AI analysis
        
        Args:
            field_info: Basic field information from pdftk
            ai_label: AI-extracted label information
            
        Returns:
            Enhanced field description
        """
        base_name = field_info.get('full_field_name', '')
        visible_text = ai_label.visible_text
        context = ai_label.context
        
        # Combine information intelligently
        if visible_text and context:
            if context.lower() != visible_text.lower():
                return f"{visible_text} - {context}"
            else:
                return visible_text
        elif visible_text:
            return visible_text
        elif context:
            return context
        else:
            return base_name
    
    def save_ai_labels(self, labels_path: Union[str, Path], 
                      ai_labels: List[ExtractedLabel]) -> None:
        """
        Save AI-extracted labels to JSON file
        
        Args:
            labels_path: Path to save the labels JSON file
            ai_labels: List of extracted labels to save
        """
        labels_data = {
            "extracted_labels": [asdict(label) for label in ai_labels],
            "metadata": {
                "total_labels": len(ai_labels),
                "extraction_time": getattr(self, '_last_extraction_time', None),
                "ai_provider": self.ai_provider,
                "model": self.model
            }
        }
        
        with open(labels_path, 'w', encoding='utf-8') as f:
            json.dump(labels_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(ai_labels)} AI-extracted labels to {labels_path}")


# Integration function for use with existing python_form_filler3.py
def enhance_numbered_mapping_with_ai(pdf_path: Union[str, Path], 
                                   field_mapping: Dict,
                                   ai_provider: str = "openai") -> Tuple[Dict, List[ExtractedLabel]]:
    """
    Enhance existing numbered mapping with AI-extracted text labels
    
    This function integrates with the existing create_numbered_mapping_for_form function
    to add AI-powered text label extraction capabilities.
    
    Args:
        pdf_path: Path to the numbered PDF
        field_mapping: Basic field mapping from pdftk
        ai_provider: AI provider to use ("openai" or "anthropic")
        
    Returns:
        Tuple of (enhanced_mapping, ai_labels)
    """
    try:
        # Initialize AI extractor
        extractor = AITextLabelExtractor(ai_provider=ai_provider)
        
        # Extract AI labels
        result = extractor.extract_ai_text_labels(pdf_path, field_mapping)
        
        # Merge with existing mapping
        enhanced_mapping = extractor.merge_ai_labels_with_mapping(
            field_mapping, result.extracted_labels
        )
        
        logger.info(f"Enhanced mapping created with {len(result.extracted_labels)} AI labels")
        return enhanced_mapping, result.extracted_labels
        
    except Exception as e:
        logger.error(f"AI enhancement failed: {e}")
        # Return original mapping if AI enhancement fails
        return field_mapping, []


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python ai_label_extractor.py <numbered_pdf_path> <field_mapping_json>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    mapping_path = sys.argv[2]
    
    # Load field mapping
    with open(mapping_path, 'r') as f:
        field_mapping = json.load(f)
    
    # Extract AI labels
    extractor = AITextLabelExtractor()
    result = extractor.extract_ai_text_labels(pdf_path, field_mapping)
    
    # Print results
    print(f"Extracted {len(result.extracted_labels)} labels with {result.extraction_confidence:.1%} confidence")
    for label in result.extracted_labels:
        print(f"  {label.field_number}: {label.visible_text} ({label.confidence:.1%})")
