#!/usr/bin/env python3
"""
Universal Form Mapper - Works with ANY PDF Form
Uses AI to intelligently map data to any form fields automatically
"""

import sys
import json
import re
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

# Import existing components
try:
    from generic_ai_extractor import GenericAIFormExtractor
except ImportError:
    GenericAIFormExtractor = None

try:
    from enhanced_llm_client import EnhancedLLMClient
except ImportError:
    try:
        import llm_client
        EnhancedLLMClient = llm_client
    except ImportError:
        EnhancedLLMClient = None

try:
    from fieldmappingwidget import FormField
except ImportError:
    # Define basic FormField class if not available
    from dataclasses import dataclass
    from typing import List as TypeList
    
    @dataclass
    class FormField:
        name: str
        field_type: str
        value: str = ""
        alt_text: str = ""
        flags: int = 0
        justification: str = "Left"
        state_options: TypeList[str] = None
        
        def __post_init__(self):
            if self.state_options is None:
                self.state_options = []

@dataclass
class UniversalMappingResult:
    """Result from universal mapping process"""
    mapped_fields: Dict[str, str]  # field_name -> value
    confidence_scores: Dict[str, float]  # field_name -> confidence
    mapping_strategy: str  # AI, pattern, hybrid
    form_analysis: Dict[str, Any]  # Analysis of the form
    extraction_log: List[str]  # Log of mapping decisions

class UniversalFormMapper:
    """Universal form mapper that works with any PDF form"""
    
    def __init__(self, api_key=None, provider="auto"):
        """
        Initialize universal mapper
        
        Args:
            api_key: OpenAI or Anthropic API key
            provider: 'openai', 'anthropic', 'pattern', or 'auto'
        """
        self.api_key = api_key
        self.provider = provider
        self.ai_available = bool(api_key)
        self.extraction_log = []
        self.mapping_cache = {}
        
        # Initialize AI client if available
        self.ai_client = None
        if self.ai_available and EnhancedLLMClient:
            try:
                if hasattr(EnhancedLLMClient, '__call__'):
                    self.ai_client = EnhancedLLMClient()
                else:
                    self.ai_client = EnhancedLLMClient
                self.log("✅ AI client initialized")
            except Exception as e:
                self.ai_available = False
                self.log(f"⚠️ AI client failed, using pattern fallback: {e}")
        
        # Initialize generic extractor if available
        self.generic_extractor = None
        if GenericAIFormExtractor:
            try:
                self.generic_extractor = GenericAIFormExtractor(
                    ai_provider="openai" if self.ai_available else "pattern",
                    api_key=api_key
                )
            except Exception as e:
                self.log(f"⚠️ Generic extractor failed: {e}")
    
    def create_numbered_mapping_for_form(self, pdf_path):
        """
        Create numbered mapping for any PDF form with intelligent caching
        
        Args:
            pdf_path: Path to the target PDF form
            
        Returns:
            Tuple of (numbered_pdf_path, mapping_json_path, reference_text_path)
        """
        try:
            import subprocess
            import json
            import tempfile
            
            # Get form identifier
            form_name = Path(pdf_path).stem
            base_dir = Path(pdf_path).parent
            
            # Check if mapping already exists on disk
            numbered_pdf = base_dir / f"{form_name}_numbered_mapping.pdf"
            mapping_json = base_dir / f"{form_name}_ai_mapping.json"
            reference_txt = base_dir / f"{form_name}_field_mapping.txt"
            
            # Check if all files exist and are newer than source PDF
            pdf_mtime = os.path.getmtime(pdf_path)
            files_exist = all(f.exists() for f in [numbered_pdf, mapping_json, reference_txt])
            
            if files_exist:
                # Check if files are newer than source PDF
                mapping_mtime = min(os.path.getmtime(f) for f in [numbered_pdf, mapping_json, reference_txt])
                if mapping_mtime > pdf_mtime:
                    self.log(f"✅ Found existing mapping for {form_name} - reusing!")
                    result = (str(numbered_pdf), str(mapping_json), str(reference_txt))
                    
                    # Cache result for memory efficiency
                    cache_key = f"{pdf_path}_{pdf_mtime}"
                    self.mapping_cache[cache_key] = result
                    return result
            
            # Check memory cache
            cache_key = f"{pdf_path}_{pdf_mtime}"
            if cache_key in self.mapping_cache:
                self.log(f"Using memory cached mapping for {form_name}")
                return self.mapping_cache[cache_key]
            
            self.log(f"🔄 Creating new numbered mapping for form: {form_name}")
            
            # Extract form fields using pdftk
            fields = self._extract_form_fields(pdf_path)
            if not fields:
                raise ValueError(f"No form fields found in {pdf_path}")
                
            self.log(f"Found {len(fields)} fields in form")
            
            # Create numbered mapping
            numbered_data, field_mapping = self._create_field_numbering(fields)
            
            # Generate numbered PDF
            self._create_numbered_pdf(pdf_path, numbered_pdf, numbered_data)
            
            # Save mapping files
            self._save_mapping_json(mapping_json, field_mapping)
            self._save_reference_txt(reference_txt, field_mapping)
            
            # Cache result
            result = (str(numbered_pdf), str(mapping_json), str(reference_txt))
            self.mapping_cache[cache_key] = result
            
            self.log(f"✅ Successfully created mapping for {form_name}")
            return result
            
        except Exception as e:
            self.log(f"Error creating numbered mapping: {e}")
            raise
    
    def _extract_form_fields(self, pdf_path):
        """Extract form field information using pdftk"""
        try:
            import subprocess
            
            # Use pdftk to dump form field data
            cmd = ['pdftk', pdf_path, 'dump_data_fields']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse pdftk output
            fields = []
            current_field = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('---'):
                    if current_field:
                        fields.append(current_field)
                        current_field = {}
                elif ': ' in line:
                    key, value = line.split(': ', 1)
                    current_field[key] = value
            
            # Add last field
            if current_field:
                fields.append(current_field)
                
            return fields
            
        except subprocess.CalledProcessError as e:
            self.log(f"pdftk command failed: {e}")
            raise
        except Exception as e:
            self.log(f"Error extracting form fields: {e}")
            raise
    
    def _create_field_numbering(self, fields):
        """Create numbered mapping for form fields"""
        numbered_data = {}
        field_mapping = {}
        
        field_number = 1
        
        for field in fields:
            field_name = field.get('FieldName', '')
            field_type = field.get('FieldType', '')
            field_tooltip = field.get('FieldNameAlt', '')
            
            # Skip non-fillable fields
            if field_type in ['Button'] and 'Choice' not in field_name:
                continue
                
            # Only number text fields and choice fields
            if field_type in ['Text', 'Choice'] or 'TextField' in field_name or 'DecimalField' in field_name:
                # Create FDF entry for numbered filling
                numbered_data[field_name] = str(field_number)
                
                # Create mapping entry
                field_mapping[str(field_number)] = {
                    "full_field_name": field_name,
                    "short_name": field_name.split('.')[-1] if '.' in field_name else field_name,
                    "description": field_tooltip or field_name,
                    "field_type": field_type
                }
                
                field_number += 1
        
        return numbered_data, field_mapping
    
    def _create_numbered_pdf(self, source_pdf, output_pdf, numbered_data):
        """Create PDF with numbered fields using pdftk"""
        try:
            import subprocess
            import tempfile
            
            # Create FDF file with numbered data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.fdf', delete=False) as fdf_file:
                fdf_content = self._create_fdf_content(numbered_data)
                fdf_file.write(fdf_content)
                fdf_path = fdf_file.name
            
            try:
                # Fill PDF with numbered data
                cmd = ['pdftk', source_pdf, 'fill_form', fdf_path, 'output', output_pdf]
                subprocess.run(cmd, check=True, capture_output=True)
                self.log(f"Created numbered PDF: {output_pdf}")
                
            finally:
                # Clean up temporary FDF file
                if os.path.exists(fdf_path):
                    os.unlink(fdf_path)
                    
        except Exception as e:
            self.log(f"Error creating numbered PDF: {e}")
            raise
    
    def _create_fdf_content(self, data):
        """Create FDF content for form filling"""
        fdf_content = """%FDF-1.2
1 0 obj
<<
/FDF
<<
/Fields [
"""
        
        for field_name, value in data.items():
            escaped_name = field_name.replace('(', '\\(').replace(')', '\\)')
            escaped_value = str(value).replace('(', '\\(').replace(')', '\\)')
            fdf_content += f"<< /T ({escaped_name}) /V ({escaped_value}) >>\n"
        
        fdf_content += """]
>>
>>
endobj
trailer

<<
/Root 1 0 R
>>
%%EOF"""
        
        return fdf_content
    
    def _save_mapping_json(self, json_path, field_mapping):
        """Save field mapping as JSON"""
        try:
            import json
            with open(json_path, 'w') as f:
                json.dump(field_mapping, f, indent=2)
            self.log(f"Saved mapping JSON: {json_path}")
        except Exception as e:
            self.log(f"Error saving mapping JSON: {e}")
            raise
    
    def _save_reference_txt(self, txt_path, field_mapping):
        """Save human-readable field reference"""
        try:
            form_name = Path(txt_path).stem.replace('_field_mapping', '')
            
            with open(txt_path, 'w') as f:
                f.write(f"{form_name.upper()} FIELD MAPPING REFERENCE\n")
                f.write("=" * 50 + "\n\n")
                f.write("This file shows the correspondence between numbers on the form and field names.\n\n")
                f.write("TEXT FIELDS (numbered):\n")
                f.write("-" * 30 + "\n")
                
                for num, info in sorted(field_mapping.items(), key=lambda x: int(x[0])):
                    f.write(f"{num:3}. {info['short_name']}\n")
                    f.write(f"     Description: {info['description']}\n")
                    f.write(f"     Full name: {info['full_field_name']}\n\n")
                    
            self.log(f"Saved reference text: {txt_path}")
        except Exception as e:
            self.log(f"Error saving reference text: {e}")
            raise
    
    def log(self, message: str):
        """Add to extraction log"""
        self.extraction_log.append(message)
        print(message)
    
    def map_any_form(self, 
                     form_fields: List[FormField], 
                     source_documents: Dict[str, str],
                     form_pdf_path: str = None) -> UniversalMappingResult:
        """
        Map data to ANY form automatically
        
        Args:
            form_fields: List of FormField objects from PDF extraction
            source_documents: Dict of source document contents
            form_pdf_path: Optional path to original PDF for context
        
        Returns:
            UniversalMappingResult with mapped fields and metadata
        """
        self.extraction_log = []
        self.log("🌍 Universal Form Mapper - ANY FORM SUPPORT")
        self.log("=" * 50)
        
        # Step 1: Analyze the form structure
        form_analysis = self._analyze_form_structure(form_fields, form_pdf_path)
        self.log(f"📋 Form Analysis: {form_analysis['form_type']} ({form_analysis['complexity']} complexity)")
        
        # Step 2: Choose best mapping strategy
        strategy = self._choose_mapping_strategy(form_analysis, source_documents)
        self.log(f"🧠 Strategy: {strategy}")
        
        # Step 3: Execute mapping based on strategy
        if strategy == "ai_intelligent":
            mapped_fields, confidence_scores = self._ai_intelligent_mapping(
                form_fields, source_documents, form_analysis
            )
        elif strategy == "ai_semantic":
            mapped_fields, confidence_scores = self._ai_semantic_mapping(
                form_fields, source_documents, form_analysis
            )
        elif strategy == "hybrid":
            mapped_fields, confidence_scores = self._hybrid_mapping(
                form_fields, source_documents, form_analysis
            )
        else:  # enhanced relationship mapping for better accuracy
            mapped_fields, confidence_scores = self._enhanced_relationship_mapping(
                form_fields, source_documents, form_analysis
            )
        
        # Step 4: Post-process and validate
        validated_fields, final_confidence = self._validate_and_enhance_mapping(
            mapped_fields, confidence_scores, form_fields, source_documents
        )
        
        result = UniversalMappingResult(
            mapped_fields=validated_fields,
            confidence_scores=final_confidence,
            mapping_strategy=strategy,
            form_analysis=form_analysis,
            extraction_log=self.extraction_log.copy()
        )
        
        self.log(f"✅ Mapped {len(validated_fields)} fields with {strategy} strategy")
        return result
    
    def _analyze_form_structure(self, form_fields: List[FormField], pdf_path: str = None) -> Dict[str, Any]:
        """Analyze form structure to understand what type of form this is"""
        
        # Collect all field information
        field_names = [f.name for f in form_fields]
        field_descriptions = [f.alt_text or "" for f in form_fields]
        all_text = " ".join(field_names + field_descriptions).lower()
        
        analysis = {
            "total_fields": len(form_fields),
            "text_fields": len([f for f in form_fields if f.field_type == "Text"]),
            "button_fields": len([f for f in form_fields if f.field_type == "Button"]),
            "form_type": "unknown",
            "domain": "general",
            "complexity": "simple",
            "key_patterns": [],
            "field_categories": {}
        }
        
        # Detect form type using intelligent pattern matching
        form_indicators = {
            "legal": ["petitioner", "respondent", "case", "court", "attorney", "plaintiff", "defendant"],
            "financial": ["asset", "debt", "income", "balance", "loan", "account", "value", "amount"],
            "tax": ["tax", "irs", "deduction", "schedule", "filing", "w2", "1099"],
            "medical": ["patient", "medical", "insurance", "diagnosis", "treatment", "doctor"],
            "business": ["business", "company", "entity", "registration", "license", "employer"],
            "government": ["agency", "department", "permit", "application", "license", "registration"]
        }
        
        max_matches = 0
        detected_type = "general"
        
        for form_type, indicators in form_indicators.items():
            matches = sum(1 for indicator in indicators if indicator in all_text)
            if matches > max_matches:
                max_matches = matches
                detected_type = form_type
                analysis["key_patterns"] = [ind for ind in indicators if ind in all_text]
        
        analysis["form_type"] = detected_type
        
        # Determine complexity
        if analysis["total_fields"] > 100:
            analysis["complexity"] = "complex"
        elif analysis["total_fields"] > 30:
            analysis["complexity"] = "moderate"
        else:
            analysis["complexity"] = "simple"
        
        # Categorize fields by type
        categories = {
            "personal_info": [],
            "financial": [],
            "dates": [],
            "addresses": [],
            "amounts": [],
            "descriptions": [],
            "checkboxes": [],
            "other": []
        }
        
        for field in form_fields:
            field_text = (field.name + " " + (field.alt_text or "")).lower()
            
            if any(word in field_text for word in ["name", "first", "last", "middle"]):
                categories["personal_info"].append(field.name)
            elif any(word in field_text for word in ["address", "street", "city", "state", "zip"]):
                categories["addresses"].append(field.name)
            elif any(word in field_text for word in ["date", "when", "time"]):
                categories["dates"].append(field.name)
            elif any(word in field_text for word in ["amount", "value", "balance", "total", "$", "dollar"]):
                categories["amounts"].append(field.name)
            elif any(word in field_text for word in ["description", "detail", "specify", "explain"]):
                categories["descriptions"].append(field.name)
            elif field.field_type == "Button":
                categories["checkboxes"].append(field.name)
            else:
                categories["other"].append(field.name)
        
        analysis["field_categories"] = categories
        
        return analysis
    
    def _choose_mapping_strategy(self, form_analysis: Dict, source_documents: Dict) -> str:
        """Choose the best mapping strategy based on available resources and form complexity"""
        
        # If no AI available, use pattern matching
        if not self.ai_available:
            return "pattern_fallback"
        
        # If complex form with lots of data, use full AI intelligence
        if (form_analysis["complexity"] == "complex" and 
            len(source_documents) > 0 and 
            sum(len(doc) for doc in source_documents.values()) > 1000):
            return "ai_intelligent"
        
        # If moderate complexity, use semantic matching
        if form_analysis["complexity"] in ["moderate", "complex"]:
            return "ai_semantic"
        
        # If simple form, use hybrid approach
        return "hybrid"
    
    def _ai_intelligent_mapping(self, form_fields: List[FormField], 
                               source_documents: Dict[str, str], 
                               form_analysis: Dict) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Full AI-powered intelligent mapping with relationship understanding"""
        self.log("🧠 Using AI Intelligent Mapping with Relationship Analysis")
        
        mapped_fields = {}
        confidence_scores = {}
        
        if not self.ai_available or not self.ai_client:
            return self._enhanced_relationship_mapping(form_fields, source_documents, form_analysis)
        
        try:
            # Create comprehensive prompt for AI that focuses on relationships
            prompt = self._create_relationship_aware_prompt(form_fields, source_documents, form_analysis)
            
            # Get AI response using available client
            if hasattr(self.ai_client, 'generate_with_fallback'):
                response = self.ai_client.generate_with_fallback(prompt)
            elif hasattr(self.ai_client, 'generate_with_openai'):
                response = self.ai_client.generate_with_openai("gpt-4", prompt)
            elif hasattr(self.ai_client, 'generate_with_claude'):
                response = self.ai_client.generate_with_claude("claude-3-sonnet-20240229", prompt)
            else:
                raise Exception("No compatible AI method found")
            
            # Parse AI response into field mappings
            parsed_mappings = self._parse_ai_mapping_response(response, form_fields)
            
            for field_name, data in parsed_mappings.items():
                mapped_fields[field_name] = data.get("value", "")
                confidence_scores[field_name] = data.get("confidence", 0.7)
            
            self.log(f"✅ AI mapped {len(mapped_fields)} fields with relationship awareness")
            
        except Exception as e:
            self.log(f"❌ AI intelligent mapping failed: {e}")
            return self._enhanced_relationship_mapping(form_fields, source_documents, form_analysis)
        
        return mapped_fields, confidence_scores
    
    def _ai_semantic_mapping(self, form_fields: List[FormField], 
                            source_documents: Dict[str, str], 
                            form_analysis: Dict) -> Tuple[Dict[str, str], Dict[str, float]]:
        """AI-powered semantic field matching"""
        self.log("🔗 Using AI Semantic Mapping")
        
        mapped_fields = {}
        confidence_scores = {}
        
        # Extract entities from source documents first
        all_source_text = "\n".join(source_documents.values())
        entities = self._extract_entities_from_text(all_source_text)
        
        # For each field, find the best semantic match
        for field in form_fields:
            if field.field_type == "Text":
                field_intent = self._determine_field_intent(field)
                best_match, confidence = self._find_best_entity_match(field_intent, entities, field)
                
                if best_match and confidence > 0.5:
                    mapped_fields[field.name] = best_match
                    confidence_scores[field.name] = confidence
        
        self.log(f"✅ Semantically mapped {len(mapped_fields)} fields")
        return mapped_fields, confidence_scores
    
    def _hybrid_mapping(self, form_fields: List[FormField], 
                       source_documents: Dict[str, str], 
                       form_analysis: Dict) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Hybrid approach combining AI and pattern matching"""
        self.log("🔀 Using Hybrid Mapping")
        
        # Start with pattern-based mapping
        pattern_fields, pattern_confidence = self._pattern_fallback_mapping(
            form_fields, source_documents, form_analysis
        )
        
        # Enhance with AI where possible
        if self.ai_available:
            try:
                # Use AI to improve low-confidence mappings
                low_confidence_fields = [
                    field for field in form_fields 
                    if field.name not in pattern_fields or pattern_confidence.get(field.name, 0) < 0.7
                ]
                
                if low_confidence_fields:
                    ai_fields, ai_confidence = self._ai_semantic_mapping(
                        low_confidence_fields, source_documents, form_analysis
                    )
                    
                    # Merge results, preferring AI for improved fields
                    for field_name, value in ai_fields.items():
                        if ai_confidence.get(field_name, 0) > pattern_confidence.get(field_name, 0):
                            pattern_fields[field_name] = value
                            pattern_confidence[field_name] = ai_confidence[field_name]
                
                self.log(f"✅ Hybrid enhanced {len(low_confidence_fields)} fields with AI")
                
            except Exception as e:
                self.log(f"⚠️ AI enhancement failed, using pattern results: {e}")
        
        return pattern_fields, pattern_confidence
    
    def _pattern_fallback_mapping(self, form_fields: List[FormField], 
                                 source_documents: Dict[str, str], 
                                 form_analysis: Dict) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Pattern-based fallback mapping that works without AI"""
        self.log("🔍 Using Pattern Fallback Mapping")
        
        mapped_fields = {}
        confidence_scores = {}
        
        # Combine all source text
        all_source_text = "\n".join(source_documents.values())
        
        # Pattern matching rules based on form analysis
        for field in form_fields:
            if field.field_type != "Text":
                continue
                
            field_text = (field.name + " " + (field.alt_text or "")).lower()
            value, confidence = self._pattern_match_field(field_text, all_source_text, field)
            
            if value and confidence > 0.3:
                mapped_fields[field.name] = value
                confidence_scores[field.name] = confidence
        
        self.log(f"✅ Pattern matched {len(mapped_fields)} fields")
        return mapped_fields, confidence_scores
    
    def _pattern_match_field(self, field_text: str, source_text: str, field: FormField) -> Tuple[str, float]:
        """Pattern match a single field"""
        
        # Common patterns
        patterns = {
            # Names
            r'case.*?number.*?(\d+[A-Z]*\d*\w*)': ("case number", 0.9),
            r'petitioner.*?name.*?([A-Z][A-Z\s]+)': ("petitioner name", 0.8),
            r'respondent.*?name.*?([A-Z][A-Z\s]+)': ("respondent name", 0.8),
            r'attorney.*?name.*?([A-Z][A-Z\s]+)': ("attorney name", 0.8),
            
            # Financial amounts
            r'\$?([\d,]+\.?\d*)': ("amount", 0.7),
            r'student.*?loan.*?\$?([\d,]+\.?\d*)': ("student loan", 0.9),
            r'credit.*?card.*?\$?([\d,]+\.?\d*)': ("credit card", 0.9),
            
            # Addresses
            r'(\d+.*?(?:street|st|avenue|ave|road|rd|boulevard|blvd).*?)': ("address", 0.8),
            
            # Phone numbers
            r'\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})': ("phone", 0.9),
            
            # Dates
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})': ("date", 0.8),
            r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}': ("date", 0.8),
        }
        
        # Try to match patterns
        for pattern, (pattern_type, base_confidence) in patterns.items():
            matches = re.finditer(pattern, source_text, re.IGNORECASE)
            for match in matches:
                # Check if this pattern type matches the field intent
                field_intent_score = self._calculate_field_intent_match(field_text, pattern_type)
                if field_intent_score > 0.5:
                    confidence = base_confidence * field_intent_score
                    value = match.group(1) if match.groups() else match.group(0)
                    return value.strip(), confidence
        
        return "", 0.0
    
    def _calculate_field_intent_match(self, field_text: str, pattern_type: str) -> float:
        """Calculate how well a pattern type matches field intent"""
        
        intent_keywords = {
            "case number": ["case", "number", "num"],
            "petitioner name": ["petitioner", "name", "plaintiff"],
            "respondent name": ["respondent", "name", "defendant"],
            "attorney name": ["attorney", "lawyer", "counsel", "name"],
            "amount": ["amount", "value", "total", "balance", "$", "dollar"],
            "student loan": ["student", "loan", "education"],
            "credit card": ["credit", "card", "charge"],
            "address": ["address", "street", "location"],
            "phone": ["phone", "telephone", "number"],
            "date": ["date", "when", "time", "on"]
        }
        
        if pattern_type not in intent_keywords:
            return 0.0
        
        keywords = intent_keywords[pattern_type]
        matches = sum(1 for keyword in keywords if keyword in field_text)
        return min(matches / len(keywords), 1.0)
    
    def _extract_entities_from_text(self, text: str) -> Dict[str, List[str]]:
        """Extract common entities from text"""
        
        entities = {
            "names": [],
            "amounts": [],
            "dates": [],
            "addresses": [],
            "phones": [],
            "case_numbers": [],
            "descriptions": []
        }
        
        # Extract using regex patterns
        patterns = {
            "names": r'\b[A-Z][a-z]+(?: [A-Z][a-z]+)+\b',
            "amounts": r'\$?[\d,]+\.?\d*',
            "dates": r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            "phones": r'\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})',
            "case_numbers": r'\b\d+[A-Z]*\d*\w*\b',
        }
        
        for entity_type, pattern in patterns.items():
            matches = re.findall(pattern, text)
            entities[entity_type] = list(set(matches))  # Remove duplicates
        
        return entities
    
    def _determine_field_intent(self, field: FormField) -> str:
        """Determine what kind of data a field is looking for"""
        
        field_text = (field.name + " " + (field.alt_text or "")).lower()
        
        intent_patterns = {
            "name": ["name", "person", "individual"],
            "amount": ["amount", "value", "total", "balance", "$", "dollar"],
            "date": ["date", "when", "time"],
            "address": ["address", "street", "location"],
            "phone": ["phone", "telephone"],
            "case_number": ["case", "number", "num"],
            "description": ["description", "detail", "specify", "explain"]
        }
        
        best_intent = "general"
        max_score = 0
        
        for intent, keywords in intent_patterns.items():
            score = sum(1 for keyword in keywords if keyword in field_text)
            if score > max_score:
                max_score = score
                best_intent = intent
        
        return best_intent
    
    def _find_best_entity_match(self, field_intent: str, entities: Dict, field: FormField) -> Tuple[str, float]:
        """Find best entity match for a field"""
        
        if field_intent in entities and entities[field_intent]:
            # Return first match with high confidence if intent matches
            return entities[field_intent][0], 0.8
        
        # Try related entity types
        related_mapping = {
            "name": ["names"],
            "amount": ["amounts"],
            "date": ["dates"],
            "address": ["addresses"],
            "phone": ["phones"],
            "case_number": ["case_numbers"]
        }
        
        if field_intent in related_mapping:
            for entity_type in related_mapping[field_intent]:
                if entity_type in entities and entities[entity_type]:
                    return entities[entity_type][0], 0.6
        
        return "", 0.0
    
    def _validate_and_enhance_mapping(self, mapped_fields: Dict[str, str], 
                                     confidence_scores: Dict[str, float],
                                     form_fields: List[FormField], 
                                     source_documents: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Validate and enhance the mapping results"""
        
        self.log("🔍 Validating and enhancing mappings")
        
        validated_fields = {}
        final_confidence = {}
        
        for field_name, value in mapped_fields.items():
            if value and value.strip():
                # Basic validation
                cleaned_value = self._clean_field_value(value)
                if cleaned_value:
                    validated_fields[field_name] = cleaned_value
                    # Boost confidence for clean values
                    original_confidence = confidence_scores.get(field_name, 0.5)
                    final_confidence[field_name] = min(original_confidence + 0.1, 1.0)
        
        self.log(f"✅ Validated {len(validated_fields)} field mappings")
        return validated_fields, final_confidence
    
    def _clean_field_value(self, value: str) -> str:
        """Clean and format field values"""
        if not value:
            return ""
        
        # Basic cleaning
        cleaned = value.strip()
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Clean up common formatting issues
        cleaned = cleaned.replace('\\n', ' ').replace('\\t', ' ')
        
        return cleaned
    
    def _create_intelligent_mapping_prompt(self, form_fields: List[FormField], 
                                          source_documents: Dict[str, str], 
                                          form_analysis: Dict) -> str:
        """Create comprehensive AI prompt for intelligent mapping"""
        
        prompt = f"""
I need you to intelligently map data from source documents to PDF form fields.

FORM ANALYSIS:
- Type: {form_analysis['form_type']}
- Domain: {form_analysis['domain']}  
- Complexity: {form_analysis['complexity']}
- Total Fields: {form_analysis['total_fields']}

FORM FIELDS (first 20):
"""
        
        for i, field in enumerate(form_fields[:20]):
            prompt += f"{i+1}. Field: {field.name}\n"
            prompt += f"   Description: {field.alt_text or 'No description'}\n"
            prompt += f"   Type: {field.field_type}\n\n"
        
        prompt += "\nSOURCE DOCUMENTS:\n"
        for doc_name, content in source_documents.items():
            prompt += f"\n--- {doc_name} ---\n{content[:1000]}...\n"
        
        prompt += """

Please analyze the source documents and map appropriate data to each form field. 
Return a JSON object with this structure:
{
  "field_name": {
    "value": "extracted_value",
    "confidence": 0.95,
    "reasoning": "why this mapping makes sense"
  }
}

Focus on accuracy and only map fields where you have high confidence in the match.
"""
        
        return prompt
    
    def _parse_ai_mapping_response(self, response: str, form_fields: List[FormField]) -> Dict[str, Dict]:
        """Parse AI response into field mappings"""
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except:
            pass
        
        # Fallback parsing if JSON fails
        parsed = {}
        valid_field_names = [f.name for f in form_fields]
        
        for line in response.split('\n'):
            if ':' in line and any(field_name in line for field_name in valid_field_names):
                # Basic line parsing as fallback
                for field_name in valid_field_names:
                    if field_name in line:
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            value = parts[1].strip().strip('"')
                            parsed[field_name] = {
                                "value": value,
                                "confidence": 0.6,
                                "reasoning": "parsed from text"
                            }
        
        return parsed
    
    def _enhanced_relationship_mapping(self, form_fields: List[FormField], 
                                      source_documents: Dict[str, str], 
                                      form_analysis: Dict) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Enhanced pattern mapping that understands relationships between people"""
        self.log("🔗 Using Enhanced Relationship Mapping")
        
        mapped_fields = {}
        confidence_scores = {}
        
        # Combine all source text
        all_source_text = "\n".join(source_documents.values())
        
        # First, identify key people and their roles
        people_analysis = self._analyze_people_and_roles(all_source_text)
        
        # Enhanced field mapping with role awareness
        for field in form_fields:
            if field.field_type != "Text":
                continue
                
            field_text = (field.name + " " + (field.alt_text or "")).lower()
            value, confidence = self._smart_field_mapping(field_text, all_source_text, field, people_analysis)
            
            if value and confidence > 0.3:
                mapped_fields[field.name] = value
                confidence_scores[field.name] = confidence
        
        self.log(f"✅ Enhanced relationship mapping completed: {len(mapped_fields)} fields")
        return mapped_fields, confidence_scores
    
    def _analyze_people_and_roles(self, text: str) -> Dict[str, Dict]:
        """Analyze text to identify people and their roles"""
        people = {}
        
        # Enhanced patterns for identifying roles
        role_patterns = {
            "attorney": [
                r'attorney.*?([A-Z][a-z]+ [A-Z][a-z]+)',
                r'counsel.*?([A-Z][a-z]+ [A-Z][a-z]+)',
                r'([A-Z][a-z]+ [A-Z][a-z]+).*?attorney',
                r'([A-Z][a-z]+ [A-Z][a-z]+).*?state bar',
                r'([A-Z][a-z]+ [A-Z][a-z]+).*?esq'
            ],
            "petitioner": [
                r'petitioner.*?([A-Z][a-z]+ [A-Z][a-z]+)',
                r'petitioner:\s*([A-Z\s]+)',
                r'plaintiff.*?([A-Z][a-z]+ [A-Z][a-z]+)'
            ],
            "respondent": [
                r'respondent.*?([A-Z][a-z]+ [A-Z][a-z]+)',
                r'respondent:\s*([A-Z\s]+)',
                r'defendant.*?([A-Z][a-z]+ [A-Z][a-z]+)'
            ],
            "client": [
                r'client.*?([A-Z][a-z]+ [A-Z][a-z]+)',
                r'on behalf of.*?([A-Z][a-z]+ [A-Z][a-z]+)'
            ]
        }
        
        # Extract people by role
        for role, patterns in role_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    name = match.group(1).strip().upper()
                    if len(name.split()) >= 2:  # At least first and last name
                        if name not in people:
                            people[name] = {"roles": [], "confidence": 0}
                        people[name]["roles"].append(role)
                        people[name]["confidence"] += 0.3
        
        # Identify phone numbers, addresses, and other identifying info
        contact_patterns = {
            "phone": r'\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})',
            "email": r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
            "address": r'\d+\s+[A-Za-z\s]+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Place|Pl)',
            "state_bar": r'state bar.*?(\d+)',
        }
        
        # Add contact info to people analysis
        for info_type, pattern in contact_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Try to associate with nearby names
                context_start = max(0, match.start() - 100)
                context_end = min(len(text), match.end() + 100)
                context = text[context_start:context_end]
                
                for person_name in people.keys():
                    if person_name.lower() in context.lower():
                        if info_type not in people[person_name]:
                            people[person_name][info_type] = []
                        if isinstance(match.groups(), tuple) and len(match.groups()) >= 3:
                            if info_type == "phone":
                                phone_value = f"({match.group(1)}) {match.group(2)}-{match.group(3)}"
                                people[person_name][info_type].append(phone_value)
                        else:
                            people[person_name][info_type].append(match.group(0))
        
        self.log(f"📋 Identified {len(people)} people with roles: {list(people.keys())}")
        return people
    
    def _smart_field_mapping(self, field_text: str, source_text: str, field: FormField, people_analysis: Dict) -> Tuple[str, float]:
        """Smart field mapping that considers people and their roles"""
        
        # Enhanced mapping logic based on field intent and people analysis
        field_intent = self._determine_field_intent(field)
        
        # Attorney-specific fields
        if any(word in field_text for word in ["attorney", "counsel", "lawyer"]):
            for person, info in people_analysis.items():
                if "attorney" in info.get("roles", []):
                    if "name" in field_intent or "attorney" in field_intent:
                        return person, 0.95
                    elif "phone" in field_intent and "phone" in info:
                        return info["phone"][0] if info["phone"] else "", 0.90
                    elif "email" in field_intent and "email" in info:
                        return info["email"][0] if info["email"] else "", 0.90
        
        # Petitioner-specific fields
        elif any(word in field_text for word in ["petitioner", "plaintiff"]):
            for person, info in people_analysis.items():
                if "petitioner" in info.get("roles", []):
                    return person, 0.95
        
        # Respondent-specific fields
        elif any(word in field_text for word in ["respondent", "defendant"]):
            for person, info in people_analysis.items():
                if "respondent" in info.get("roles", []):
                    return person, 0.95
        
        # Case number
        elif "case" in field_text and "number" in field_text:
            pattern = r'\b(\d{2}[A-Z]{2,4}\d{5,8})\b'
            match = re.search(pattern, source_text)
            if match:
                return match.group(1), 0.95
        
        # Court/county
        elif "court" in field_text or "county" in field_text:
            patterns = [
                r'superior court.*?county of\s+([A-Z\s]+)',
                r'county of\s+([A-Z\s]+)',
                r'([A-Z\s]+)\s+county'
            ]
            for pattern in patterns:
                match = re.search(pattern, source_text, re.IGNORECASE)
                if match:
                    county = match.group(1).strip().upper()
                    return county, 0.90
        
        # Financial amounts
        elif any(word in field_text for word in ["amount", "total", "debt", "loan", "balance"]):
            # Look for monetary amounts
            money_patterns = [
                r'\$\s*([1-9]\d{0,2}(?:,\d{3})*(?:\.\d{2})?)',
                r'([1-9]\d{0,2}(?:,\d{3})*(?:\.\d{2})?)\s*dollars?'
            ]
            
            # Special handling for specific debt types
            if "student" in field_text:
                student_pattern = r'student.*?loan.*?\$?\s*([1-9]\d{0,2}(?:,\d{3})*(?:\.\d{2})?)'
                match = re.search(student_pattern, source_text, re.IGNORECASE)
                if match:
                    return match.group(1), 0.90
            
            elif "credit" in field_text:
                credit_pattern = r'credit.*?card.*?\$?\s*([1-9]\d{0,2}(?:,\d{3})*(?:\.\d{2})?)'
                match = re.search(credit_pattern, source_text, re.IGNORECASE)
                if match:
                    return match.group(1), 0.90
            
            elif "total" in field_text:
                total_patterns = [
                    r'total.*?debt.*?\$?\s*([1-9]\d{0,2}(?:,\d{3})*(?:\.\d{2})?)',
                    r'total.*?\$?\s*([1-9]\d{0,2}(?:,\d{3})*(?:\.\d{2})?)'
                ]
                for pattern in total_patterns:
                    match = re.search(pattern, source_text, re.IGNORECASE)
                    if match:
                        return match.group(1), 0.85
            
            # General money pattern
            for pattern in money_patterns:
                match = re.search(pattern, source_text)
                if match:
                    return match.group(1), 0.70
        
        # Dates
        elif "date" in field_text or "sign" in field_text:
            date_patterns = [
                r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b',
                r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\b'
            ]
            for pattern in date_patterns:
                match = re.search(pattern, source_text, re.IGNORECASE)
                if match:
                    return match.group(0), 0.80
        
        # Fallback to original pattern matching
        return self._pattern_match_field(field_text, source_text, field)
    
    def _create_relationship_aware_prompt(self, form_fields: List[FormField], 
                                         source_documents: Dict[str, str], 
                                         form_analysis: Dict) -> str:
        """Create AI prompt that focuses on understanding relationships"""
        
        prompt = f"""
You are an expert legal document analyst. I need you to intelligently map data from source documents to form fields, 
with special attention to understanding WHO is WHO and their RELATIONSHIPS.

FORM ANALYSIS:
- Type: {form_analysis['form_type']}
- Domain: {form_analysis['domain']}  
- Complexity: {form_analysis['complexity']}

CRITICAL: Pay careful attention to ROLES and RELATIONSHIPS:
- Who is the ATTORNEY/COUNSEL (represents someone else)
- Who is the PETITIONER/PLAINTIFF (person filing)
- Who is the RESPONDENT/DEFENDANT (person being sued)
- Who is the CLIENT (person being represented)

FORM FIELDS TO FILL (first 15):
"""
        
        for i, field in enumerate(form_fields[:15]):
            prompt += f"{i+1}. Field: {field.name}\n"
            prompt += f"   Purpose: {field.alt_text or 'No description'}\n"
            prompt += f"   Type: {field.field_type}\n\n"
        
        prompt += "\nSOURCE DOCUMENTS:\n"
        for doc_name, content in source_documents.items():
            prompt += f"\n--- {doc_name} ---\n{content[:2000]}...\n"
        
        prompt += """

MAPPING INSTRUCTIONS:
1. IDENTIFY PEOPLE AND ROLES first:
   - Find who is the attorney (look for "attorney", "counsel", "state bar", "esq")
   - Find who is the petitioner/plaintiff 
   - Find who is the respondent/defendant
   - Understand who represents whom

2. MAP FIELDS BASED ON ROLES:
   - Attorney fields should get attorney information (NOT client information)
   - Petitioner fields should get petitioner information  
   - Respondent fields should get respondent information
   - Party-neutral fields (case number, court) can use any source

3. SPECIAL ATTENTION TO:
   - Don't confuse attorney with client
   - Don't mix up petitioner and respondent
   - Case numbers, court names are shared across parties
   - Financial information usually belongs to the person filing

Return JSON:
{
  "field_name": {
    "value": "extracted_value",
    "confidence": 0.95,
    "reasoning": "why this person/value is correct for this field"
  }
}

FOCUS on accuracy over completeness. Only map fields where you're confident about the relationship.
"""
        
        return prompt


def main():
    """Test the universal form mapper"""
    print("🌍 Universal Form Mapper Test")
    print("=" * 50)
    
    # Initialize mapper
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    mapper = UniversalFormMapper(api_key=api_key)
    
    # Test with sample form fields (would come from PDF extraction)
    sample_fields = [
        FormField(name="Text1", field_type="Text", alt_text="Attorney Name"),
        FormField(name="Text2", field_type="Text", alt_text="Case Number"),
        FormField(name="Text3", field_type="Text", alt_text="Petitioner Name"),
        FormField(name="Text4", field_type="Text", alt_text="Total Amount Owed"),
        FormField(name="Button1", field_type="Button", alt_text="Respondent Checkbox")
    ]
    
    # Sample source documents
    sample_docs = {
        "legal_document": """
        Case Number: 24STFL00615
        Petitioner: TAHIRA FRANCIS
        Respondent: SHAWN ROGERS
        Attorney: Mark Piesner
        Total Debts: $64,225.81
        """
    }
    
    # Test mapping
    result = mapper.map_any_form(sample_fields, sample_docs)
    
    print(f"\n📊 MAPPING RESULTS:")
    print(f"Strategy Used: {result.mapping_strategy}")
    print(f"Fields Mapped: {len(result.mapped_fields)}")
    
    for field_name, value in result.mapped_fields.items():
        confidence = result.confidence_scores.get(field_name, 0.0)
        print(f"  {field_name}: {value} (confidence: {confidence:.2f})")
    
    print(f"\n📋 Form Analysis:")
    for key, value in result.form_analysis.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()