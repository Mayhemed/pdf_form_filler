#!/usr/bin/env python3
"""
Unified Pipeline Controller - Orchestrates the entire form filling process
Connects AI extraction → Field mapping → PDF filling
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ProcessingStage(Enum):
    """Pipeline processing stages"""
    INITIALIZATION = "initialization"
    AI_EXTRACTION = "ai_extraction"
    FIELD_MAPPING = "field_mapping"
    DATA_VALIDATION = "data_validation"
    PDF_FILLING = "pdf_filling"
    COMPLETION = "completion"

@dataclass
class ProcessingResult:
    """Result of a pipeline stage"""
    stage: ProcessingStage
    success: bool
    data: Dict[str, Any]
    errors: List[str]
    confidence_scores: Dict[str, float]
    processing_time: float

class UnifiedPipeline:
    """
    Main controller that orchestrates the entire form filling process.
    This is the heart of the generic system that can handle any form type.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the unified pipeline with configuration"""
        self.config = self._load_config(config_path)
        self.processing_history: List[ProcessingResult] = []
        self.current_stage = ProcessingStage.INITIALIZATION
        
        # Initialize components
        self.ai_extractor = None
        self.field_mapper = None
        self.pdf_processor = None
        self.validator = None
        
        self._initialize_components()
    
    def process_form(self, 
                    target_form_path: str,
                    source_documents: List[str],
                    output_path: str) -> ProcessingResult:
        """
        Main entry point: Process a form with source documents
        
        Args:
            target_form_path: Path to the blank PDF form to fill
            source_documents: List of paths to source documents containing data
            output_path: Where to save the filled PDF
            
        Returns:
            ProcessingResult with success status and extracted data
        """
        logger.info(f"Starting form processing pipeline")
        logger.info(f"Target form: {target_form_path}")
        logger.info(f"Source documents: {len(source_documents)} files")
        logger.info(f"Output path: {output_path}")
        
        try:
            # Stage 1: AI Extraction
            extraction_result = self._stage_ai_extraction(source_documents)
            if not extraction_result.success:
                return extraction_result
            
            # Stage 2: Field Mapping
            mapping_result = self._stage_field_mapping(
                target_form_path, extraction_result.data
            )
            if not mapping_result.success:
                return mapping_result
            
            # Stage 3: Data Validation
            validation_result = self._stage_data_validation(mapping_result.data)
            if not validation_result.success:
                return validation_result
            
            # Stage 4: PDF Filling
            filling_result = self._stage_pdf_filling(
                target_form_path, validation_result.data, output_path
            )
            
            # Final result
            final_result = ProcessingResult(
                stage=ProcessingStage.COMPLETION,
                success=filling_result.success,
                data={
                    "output_path": output_path,
                    "fields_filled": len(validation_result.data),
                    "processing_stages": len(self.processing_history)
                },
                errors=filling_result.errors,
                confidence_scores=validation_result.confidence_scores,
                processing_time=sum(r.processing_time for r in self.processing_history)
            )
            
            self.processing_history.append(final_result)
            return final_result
            
        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}")
            return ProcessingResult(
                stage=self.current_stage,
                success=False,
                data={},
                errors=[str(e)],
                confidence_scores={},
                processing_time=0.0
            )
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load system configuration"""
        default_config = {
            "ai_providers": {
                "openai": {
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "model": "gpt-4-vision-preview",
                    "max_tokens": 4000
                },
                "anthropic": {
                    "api_key": os.getenv("ANTHROPIC_API_KEY"),
                    "model": "claude-3-opus-20240229",
                    "max_tokens": 4000
                }
            },
            "processing": {
                "field_coverage_target": 0.95,
                "confidence_threshold": 0.8,
                "fallback_enabled": True,
                "parallel_processing": False
            }
        }
        return default_config
    
    def _initialize_components(self):
        """Initialize all pipeline components"""
        # Use existing components from the current system
        try:
            # Import existing working components
            import sys
            sys.path.append('/Users/markpiesner/Documents/Github/LegalTools/PDF_Form_Filler')
            
            from llm_client import generate_with_openai, generate_with_claude
            
            # Create simple wrapper components
            self.ai_extractor = SimpleAIExtractor(self.config["ai_providers"])
            self.field_mapper = SimpleFieldMapper()
            self.pdf_processor = SimplePDFProcessor()
            self.validator = SimpleValidator()
            
            logger.info("Pipeline components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    def _stage_ai_extraction(self, source_documents: List[str]) -> ProcessingResult:
        """Stage 1: Extract data from source documents using AI"""
        import time
        start_time = time.time()
        
        self.current_stage = ProcessingStage.AI_EXTRACTION
        logger.info(f"Stage 1: AI Extraction from {len(source_documents)} documents")
        
        try:
            extracted_data, confidence_scores = self.ai_extractor.extract_from_documents(
                source_documents
            )
            
            result = ProcessingResult(
                stage=ProcessingStage.AI_EXTRACTION,
                success=True,
                data=extracted_data,
                errors=[],
                confidence_scores=confidence_scores,
                processing_time=time.time() - start_time
            )
            
            self.processing_history.append(result)
            logger.info(f"AI extraction completed: {len(extracted_data)} data points extracted")
            return result
            
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            result = ProcessingResult(
                stage=ProcessingStage.AI_EXTRACTION,
                success=False,
                data={},
                errors=[str(e)],
                confidence_scores={},
                processing_time=time.time() - start_time
            )
            self.processing_history.append(result)
            return result
    
    def _stage_field_mapping(self, target_form_path: str, extracted_data: Dict[str, Any]) -> ProcessingResult:
        """Stage 2: Map extracted data to form fields"""
        import time
        start_time = time.time()
        
        self.current_stage = ProcessingStage.FIELD_MAPPING
        logger.info(f"Stage 2: Field mapping for form {os.path.basename(target_form_path)}")
        
        try:
            mapped_fields, confidence_scores = self.field_mapper.map_data_to_form(
                target_form_path, extracted_data
            )
            
            result = ProcessingResult(
                stage=ProcessingStage.FIELD_MAPPING,
                success=True,
                data=mapped_fields,
                errors=[],
                confidence_scores=confidence_scores,
                processing_time=time.time() - start_time
            )
            
            self.processing_history.append(result)
            logger.info(f"Field mapping completed: {len(mapped_fields)} fields mapped")
            return result
            
        except Exception as e:
            logger.error(f"Field mapping failed: {e}")
            result = ProcessingResult(
                stage=ProcessingStage.FIELD_MAPPING,
                success=False,
                data={},
                errors=[str(e)],
                confidence_scores={},
                processing_time=time.time() - start_time
            )
            self.processing_history.append(result)
            return result
    
    def _stage_data_validation(self, mapped_data: Dict[str, Any]) -> ProcessingResult:
        """Stage 3: Validate and enrich mapped data"""
        import time
        start_time = time.time()
        
        self.current_stage = ProcessingStage.DATA_VALIDATION
        logger.info(f"Stage 3: Data validation for {len(mapped_data)} fields")
        
        try:
            validated_data, confidence_scores = self.validator.validate_and_enrich(mapped_data)
            
            result = ProcessingResult(
                stage=ProcessingStage.DATA_VALIDATION,
                success=True,
                data=validated_data,
                errors=[],
                confidence_scores=confidence_scores,
                processing_time=time.time() - start_time
            )
            
            self.processing_history.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            result = ProcessingResult(
                stage=ProcessingStage.DATA_VALIDATION,
                success=False,
                data=mapped_data,
                errors=[str(e)],
                confidence_scores={},
                processing_time=time.time() - start_time
            )
            self.processing_history.append(result)
            return result
    
    def _stage_pdf_filling(self, target_form_path: str, validated_data: Dict[str, Any], output_path: str) -> ProcessingResult:
        """Stage 4: Fill the PDF form with validated data"""
        import time
        start_time = time.time()
        
        self.current_stage = ProcessingStage.PDF_FILLING
        logger.info(f"Stage 4: PDF filling to {output_path}")
        
        try:
            success = self.pdf_processor.fill_form(target_form_path, validated_data, output_path)
            
            result = ProcessingResult(
                stage=ProcessingStage.PDF_FILLING,
                success=success,
                data={"output_path": output_path, "fields_written": len(validated_data)},
                errors=[],
                confidence_scores={},
                processing_time=time.time() - start_time
            )
            
            self.processing_history.append(result)
            return result
            
        except Exception as e:
            logger.error(f"PDF filling failed: {e}")
            result = ProcessingResult(
                stage=ProcessingStage.PDF_FILLING,
                success=False,
                data={},
                errors=[str(e)],
                confidence_scores={},
                processing_time=time.time() - start_time
            )
            self.processing_history.append(result)
            return result


# Simple component implementations using existing code
class SimpleAIExtractor:
    """Wrapper around existing LLM client for AI extraction"""
    
    def __init__(self, ai_config: Dict[str, Any]):
        self.ai_config = ai_config
    
    def extract_from_documents(self, source_documents: List[str]) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """Extract data from source documents using AI"""
        try:
            from llm_client import generate_with_openai, generate_with_claude
            
            # Check which AI provider is available
            if self.ai_config["openai"]["api_key"]:
                response = self._extract_with_openai(source_documents)
            elif self.ai_config["anthropic"]["api_key"]:
                response = self._extract_with_claude(source_documents)
            else:
                return self._extract_with_patterns(source_documents)
            
            return self._parse_ai_response(response)
            
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            return {}, {}
    
    def _extract_with_openai(self, source_documents: List[str]) -> str:
        """Extract using OpenAI"""
        from llm_client import generate_with_multiple_pdfs_openai
        
        prompt = """Extract all relevant data from these documents for form filling.
        Focus on:
        - Names (people, entities, attorneys)
        - Case numbers and legal identifiers
        - Financial amounts and account details
        - Addresses and contact information
        - Dates and legal information
        
        Return JSON format:
        {
            "extracted_data": {"field_type": "value"},
            "confidence_scores": {"field_type": 0.95}
        }"""
        
        model = self.ai_config["openai"]["model"]
        return generate_with_multiple_pdfs_openai(model, prompt, source_documents)
    
    def _extract_with_claude(self, source_documents: List[str]) -> str:
        """Extract using Claude"""
        from llm_client import generate_with_multiple_pdfs_claude
        
        prompt = """Extract all relevant data from these documents for form filling.
        Focus on:
        - Names (people, entities, attorneys)
        - Case numbers and legal identifiers
        - Financial amounts and account details
        - Addresses and contact information
        - Dates and legal information
        
        Return JSON format:
        {
            "extracted_data": {"field_type": "value"},
            "confidence_scores": {"field_type": 0.95}
        }"""
        
        model = self.ai_config["anthropic"]["model"]
        return generate_with_multiple_pdfs_claude(model, prompt, source_documents)
    
    def _extract_with_patterns(self, source_documents: List[str]) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """Fallback pattern-based extraction"""
        from llm_client import enhanced_pattern_extraction
        
        # Read text from documents
        all_text = ""
        for doc_path in source_documents:
            try:
                if doc_path.endswith('.pdf'):
                    # Simple PDF text extraction
                    import subprocess
                    result = subprocess.run(['pdftotext', doc_path, '-'], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        all_text += f"\n\n=== {os.path.basename(doc_path)} ===\n{result.stdout}"
                else:
                    with open(doc_path, 'r', encoding='utf-8') as f:
                        all_text += f"\n\n=== {os.path.basename(doc_path)} ===\n{f.read()}"
            except Exception as e:
                logger.warning(f"Failed to read {doc_path}: {e}")
        
        # Use pattern extraction
        field_names = ["petitioner", "respondent", "case_number", "attorney", "phone", "address"]
        field_descriptions = ["Petitioner name", "Respondent name", "Case number", "Attorney name", "Phone number", "Address"]
        
        return enhanced_pattern_extraction(all_text, field_names, field_descriptions)
    
    def _parse_ai_response(self, response: str) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """Parse AI response to extract data and confidence scores"""
        try:
            # Find JSON in response
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_text = response[start:end]
                result = json.loads(json_text)
                
                extracted_data = result.get("extracted_data", {})
                confidence_scores = result.get("confidence_scores", {})
                
                # If missing confidence scores, generate defaults
                if extracted_data and not confidence_scores:
                    confidence_scores = {key: 0.8 for key in extracted_data.keys()}
                    
                return extracted_data, confidence_scores
            else:
                logger.warning("No valid JSON found in AI response")
                return {}, {}
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return {}, {}


class SimpleFieldMapper:
    """Simple field mapper that uses form field analysis"""
    
    def map_data_to_form(self, target_form_path: str, extracted_data: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Map extracted data to specific form fields"""
        try:
            # Extract form fields using pdftk
            form_fields = self._get_form_fields(target_form_path)
            
            # Map data to fields using semantic matching
            mapped_fields = {}
            confidence_scores = {}
            
            for field in form_fields:
                field_name = field.get('FieldName', '')
                field_alt = field.get('FieldNameAlt', '')
                
                # Try to find matching data
                best_match = self._find_best_match(field_name, field_alt, extracted_data)
                if best_match:
                    mapped_fields[field_name] = best_match['value']
                    confidence_scores[field_name] = best_match['confidence']
            
            return mapped_fields, confidence_scores
            
        except Exception as e:
            logger.error(f"Field mapping failed: {e}")
            return {}, {}
    
    def _get_form_fields(self, form_path: str) -> List[Dict[str, str]]:
        """Extract form fields using pdftk"""
        try:
            import subprocess
            result = subprocess.run(['pdftk', form_path, 'dump_data_fields'], 
                                  capture_output=True, text=True, check=True)
            
            fields = []
            current_field = {}
            
            for line in result.stdout.strip().split('\n'):
                if line.startswith('---'):
                    if current_field:
                        fields.append(current_field)
                        current_field = {}
                elif ':' in line:
                    key, value = line.split(':', 1)
                    current_field[key.strip()] = value.strip()
            
            if current_field:
                fields.append(current_field)
                
            return fields
            
        except Exception as e:
            logger.error(f"Failed to extract form fields: {e}")
            return []
    
    def _find_best_match(self, field_name: str, field_alt: str, extracted_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find best matching extracted data for a form field"""
        field_text = f"{field_name} {field_alt}".lower()
        
        # Simple keyword matching
        matches = []
        for data_key, data_value in extracted_data.items():
            data_key_lower = data_key.lower()
            
            # Calculate match score
            score = 0
            if any(keyword in field_text for keyword in data_key_lower.split('_')):
                score += 0.8
            if any(keyword in data_key_lower for keyword in ['name', 'petitioner', 'respondent'] if keyword in field_text):
                score += 0.9
            if any(keyword in data_key_lower for keyword in ['case', 'number'] if keyword in field_text):
                score += 0.9
            
            if score > 0.5:
                matches.append({
                    'value': str(data_value),
                    'confidence': score,
                    'source_key': data_key
                })
        
        # Return best match
        if matches:
            return max(matches, key=lambda x: x['confidence'])
        return None


class SimpleValidator:
    """Simple data validator"""
    
    def validate_and_enrich(self, mapped_data: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Validate and enrich mapped data"""
        validated_data = {}
        confidence_scores = {}
        
        for field_name, value in mapped_data.items():
            # Basic validation and formatting
            if value and str(value).strip():
                validated_value = str(value).strip()
                
                # Apply basic formatting
                if 'phone' in field_name.lower():
                    validated_value = self._format_phone(validated_value)
                elif 'date' in field_name.lower():
                    validated_value = self._format_date(validated_value)
                elif any(keyword in field_name.lower() for keyword in ['amount', 'value', 'balance']):
                    validated_value = self._format_currency(validated_value)
                
                validated_data[field_name] = validated_value
                confidence_scores[field_name] = 0.85
        
        return validated_data, confidence_scores
    
    def _format_phone(self, phone: str) -> str:
        """Format phone number"""
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        return phone
    
    def _format_date(self, date: str) -> str:
        """Format date"""
        # Simple date formatting - can be enhanced
        return date
    
    def _format_currency(self, amount: str) -> str:
        """Format currency amount"""
        try:
            # Remove currency symbols and commas
            clean_amount = ''.join(c for c in amount if c.isdigit() or c == '.')
            if clean_amount:
                return f"{float(clean_amount):.2f}"
        except:
            pass
        return amount


class SimplePDFProcessor:
    """Simple PDF form processor using pdftk"""
    
    def fill_form(self, form_path: str, field_data: Dict[str, str], output_path: str) -> bool:
        """Fill PDF form with data"""
        try:
            # Create FDF file
            fdf_content = self._create_fdf(field_data)
            
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.fdf', delete=False) as fdf_file:
                fdf_file.write(fdf_content)
                fdf_path = fdf_file.name
            
            try:
                # Fill form using pdftk
                import subprocess
                subprocess.run([
                    'pdftk', form_path, 'fill_form', fdf_path,
                    'output', output_path
                ], check=True)
                
                logger.info(f"Successfully filled PDF: {output_path}")
                return True
                
            finally:
                # Clean up temporary FDF file
                os.unlink(fdf_path)
                
        except Exception as e:
            logger.error(f"PDF filling failed: {e}")
            return False
    
    def _create_fdf(self, field_data: Dict[str, str]) -> str:
        """Create FDF content for form filling"""
        fdf_header = """%FDF-1.2
1 0 obj
<<
/FDF
<<
/Fields ["""

        fdf_fields = []
        for field_name, field_value in field_data.items():
            if field_value:  # Only include non-empty fields
                escaped_value = field_value.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
                fdf_fields.append(f"""<<
/T ({field_name})
/V ({escaped_value})
>>""")

        fdf_footer = """]
>>
>>
endobj
trailer

<<
/Root 1 0 R
>>
%%EOF"""

        return fdf_header + '\n' + '\n'.join(fdf_fields) + '\n' + fdf_footer


# Command Line Interface
def main():
    """Command line interface for the unified pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Universal PDF Form Filler")
    parser.add_argument("target_form", help="Path to blank PDF form to fill")
    parser.add_argument("output_path", help="Path for filled PDF output")
    parser.add_argument("--sources", nargs="+", required=True, help="Source documents containing data")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize and run pipeline
    pipeline = UnifiedPipeline(config_path=args.config)
    result = pipeline.process_form(
        target_form_path=args.target_form,
        source_documents=args.sources,
        output_path=args.output_path
    )
    
    # Print results
    if result.success:
        print(f"✅ Form processing completed successfully!")
        print(f"📄 Output saved to: {result.data.get('output_path')}")
        print(f"📊 Fields filled: {result.data.get('fields_filled', 0)}")
    else:
        print(f"❌ Form processing failed:")
        for error in result.errors:
            print(f"   - {error}")


if __name__ == "__main__":
    main()
