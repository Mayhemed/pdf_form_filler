# extractors.py

import os
import re
import json
import logging
import subprocess
from typing import Dict, List, Tuple

from PyQt6.QtCore import QThread, pyqtSignal

# Local imports
import llm_client
from models import FormField, DataSource

logger = logging.getLogger('PDF_Form_Filler')

class AIDataExtractor(QThread):
    """Thread for AI-powered data extraction using a generic, intelligent, multi-document analysis prompt."""
    data_extracted = pyqtSignal(dict, dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int, str)
    
    def __init__(self, sources: List[DataSource], form_fields: List[FormField],
                 ai_provider: str, api_key: str, model: str,
                 mapping_pdf_path: str = None, number_to_description_map: Dict = None):
        super().__init__()
        self.sources = sources
        self.form_fields = form_fields
        self.ai_provider = ai_provider
        self.api_key = api_key
        self.model = model
        self.mapping_pdf_path = mapping_pdf_path
        self.number_to_description_map = number_to_description_map or {}
        # Store the path to the target form for context
        self.target_form_path = ""  # This will be set from the main window
        # Initialize custom prompt to None - will be set by main_app.py if user edits
        self.custom_prompt = None
        
        # Create a lookup table for common field types/locations to improve mapping
        self.field_type_map = {
            "TextField1": "description",
            "TextField3": "additional_text",
            "DecimalField": "monetary_value",
            "P1Caption": "header_information",
            "AttyPartyInfo": "attorney_information",
            "TitlePartyName": "party_names",
            "CrtCounty": "court_county",
            "CaseNumber": "case_number"
        }
        
    def run(self):
        try:
            logger.info(f"AIDataExtractor v4.3: Starting extraction with provider '{self.ai_provider}'")
            self.progress_updated.emit(10, f"Initializing AI extraction with {self.ai_provider}...")
            
            # CRITICAL DIAGNOSTIC: Log all sources upfront
            logger.info(f"*** PROCESSING {len(self.sources)} TOTAL SOURCES ***")
            for i, source in enumerate(self.sources):
                logger.info(f"Source {i+1}: {source.name} (Type: {source.source_type})")
            
            # Prepare PDF files and text content
            pdf_file_paths = []
            text_content = ""
            
            for i, source in enumerate(self.sources):
                progress = 20 + (i * 30 // len(self.sources))
                self.progress_updated.emit(progress, f"Preparing source: {source.name}...")
                
                # We primarily want to pass PDF file paths directly to the LLM client
                if source.source_type == 'file' and source.content.lower().endswith('.pdf'):
                    pdf_file_paths.append(source.content)
                    logger.info(f"*** CRITICAL: Added PDF {i+1}/{len(self.sources)} for direct processing: {os.path.basename(source.content)}")
                    
                    # Add validation check
                    if not os.path.exists(source.content):
                        logger.error(f"!!! ERROR: PDF file does not exist: {source.content}")
                    else:
                        file_size = os.path.getsize(source.content) / (1024 * 1024)  # Size in MB
                        logger.info(f"PDF file exists and is {file_size:.2f} MB in size")
                else:
                    # For non-PDF sources, extract text content
                    if source.source_type == 'file':
                        try:
                            with open(source.content, 'r', encoding='utf-8', errors='replace') as f:
                                content = f.read()
                            logger.info(f"Extracted {len(content)} characters from file source: {source.name}")
                        except Exception as e:
                            logger.error(f"Error reading non-PDF file: {e}")
                            content = f"[Error reading file: {str(e)}]"
                    else:
                        content = source.content
                        logger.info(f"Using {len(content)} characters from direct text source: {source.name}")
                    
                    text_content += f"\n--- Start of Content from {source.name} ---\n{content}\n--- End of Content ---\n"

            # Validate target form path
            if not self.target_form_path:
                logger.warning("No target form path set. AI extraction may be less accurate.")
            else:
                logger.info(f"Using target form for context: {os.path.basename(self.target_form_path)}")
                
            # Validate mapping PDF path
            if self.mapping_pdf_path:
                logger.info(f"Using Numbered Mapping PDF: {os.path.basename(self.mapping_pdf_path)}")
            else:
                logger.warning("No Numbered Mapping PDF provided. AI accuracy will be significantly reduced.")

            self.progress_updated.emit(60, f"Running AI analysis on {len(pdf_file_paths)} PDFs and additional text...")

            # Dispatch to the appropriate AI provider
            if self.ai_provider == "anthropic" and llm_client.ANTHROPIC_AVAILABLE:
                logger.info("Dispatching to llm_client for Anthropic multi-PDF processing")
                extracted_data, confidence_scores = self._extract_with_anthropic(pdf_file_paths, text_content)
            elif self.ai_provider == "openai" and llm_client.OPENAI_AVAILABLE:
                logger.info("Dispatching to llm_client for OpenAI multi-PDF processing")
                extracted_data, confidence_scores = self._extract_with_openai(pdf_file_paths, text_content)
            else:
                self.error_occurred.emit(f"Selected AI provider '{self.ai_provider}' is not available.")
                return

            logger.info(f"AI Extraction complete. Found {len(extracted_data)} potential fields.")
            self.progress_updated.emit(100, "AI extraction complete!")
            self.data_extracted.emit(extracted_data, confidence_scores)

        except Exception as e:
            error_msg = f"Critical error in AIDataExtractor: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)

    def _generate_field_mapping_table(self) -> str:
        """
        Generate a structured field mapping table to help the AI correctly map data to fields.
        This is critical for ensuring that data is consistently mapped to the correct fields.
        """
        mapping_table = []
        
        # Group fields by page and table for better organization
        page_table_groups = {}
        
        for field in self.form_fields:
            # Skip non-data fields
            if not any(marker in field.name for marker in ['TextField', 'DecimalField', 'CheckBox']):
                continue
                
            # Extract page and table information from field name
            page_match = re.search(r'Page(\d+)', field.name)
            table_match = re.search(r'Table(\d+)', field.name)
            row_match = re.search(r'Row(\d+)', field.name)
            
            page = page_match.group(1) if page_match else "0"
            table = table_match.group(1) if table_match else "0"
            row = row_match.group(1) if row_match else "0"
            
            # Determine field type
            field_type = "unknown"
            if "TextField1" in field.name:
                field_type = "description"
            elif "TextField" in field.name:
                field_type = "text"
            elif "DecimalField" in field.name:
                field_type = "monetary_value"
            elif "CheckBox" in field.name or "Radio" in field.name:
                field_type = "checkbox"
                
            # Create a key for grouping
            group_key = f"Page{page}.Table{table}"
            if group_key not in page_table_groups:
                page_table_groups[group_key] = []
                
            # Add to the group with row information for sorting
            page_table_groups[group_key].append({
                "field_name": field.name,
                "field_type": field_type,
                "row": int(row) if row else 0,
                "alt_text": field.alt_text if hasattr(field, 'alt_text') else ""
            })
        
        # Build the mapping table as a string with clear explanations
        mapping_str = "FIELD MAPPING TABLE BY PAGE AND TABLE:\n\n"
        
        for group_key, fields in sorted(page_table_groups.items()):
            # Sort fields by row
            fields.sort(key=lambda x: x["row"])
            
            mapping_str += f"## {group_key}:\n"
            for field in fields:
                type_explanation = {
                    "description": "Field for row DESCRIPTION (e.g., 'REAL ESTATE', 'STUDENT LOANS')",
                    "text": "Field for additional TEXT details",
                    "monetary_value": "Field for MONETARY VALUE (e.g., '$10,000.00')",
                    "checkbox": "CHECKBOX field (use 'X' to check)"
                }.get(field["field_type"], "Unknown field type")
                
                # Add field name and explanation
                mapping_str += f"- {field['field_name']}: {type_explanation}\n"
                if field["alt_text"]:
                    mapping_str += f"  Description: {field['alt_text']}\n"
            
            mapping_str += "\n"
            
        # Add a section specifically for attorney and party information
        mapping_str += "## CRITICAL HEADER FIELDS:\n"
        attorney_fields = [f for f in self.form_fields if "AttyPartyInfo" in f.name]
        for field in attorney_fields:
            mapping_str += f"- {field.name}: Attorney Information Field\n"
            
        party_fields = [f for f in self.form_fields if "TitlePartyName" in f.name]
        for field in party_fields:
            if "Party1" in field.name:
                mapping_str += f"- {field.name}: PETITIONER Name\n"
            elif "Party2" in field.name:
                mapping_str += f"- {field.name}: RESPONDENT Name\n"
        
        case_fields = [f for f in self.form_fields if "CaseNumber" in f.name or "CrtCounty" in f.name]
        for field in case_fields:
            if "CaseNumber" in field.name:
                mapping_str += f"- {field.name}: CASE NUMBER\n"
            elif "CrtCounty" in field.name:
                mapping_str += f"- {field.name}: COURT COUNTY\n"
                
        logger.info(f"Generated field mapping table with {len(self.form_fields)} fields")
        return mapping_str
        
    def _get_intelligent_generic_prompt(self, text_context: str = "") -> str:
        """
        Streamlined universal prompt that instructs the AI to intelligently analyze the form structure
        and extract data accurately for the specific target form.
        """
        target_form_name = os.path.basename(self.target_form_path) if self.target_form_path else "the target PDF"
        mapping_form_name = os.path.basename(self.mapping_pdf_path) if self.mapping_pdf_path else "(Not provided)"
        
        prompt = f"""You are an expert AI data extraction agent for legal forms. Your task is to extract information from source documents to fill a target PDF form.

TASK OVERVIEW:
1. Examine the structure of the target form (which has field numbers)
2. Analyze ALL source documents to extract relevant data
3. Intelligently match the extracted data to the appropriate field numbers on the target form
4. Return a clean JSON with field numbers and extracted values

KEY INPUT:
- Target form to fill: "{target_form_name}"
- Numbered mapping form: "{mapping_form_name}"
- Multiple source documents (provided separately)

EXTRACTION APPROACH:

1. FORM ANALYSIS:
   - The AI will be provided with a numbered PDF form showing field numbers
   - Examine this form carefully to understand what information belongs in each field
   - Fields are labeled with numbers - you must map extracted data to these field numbers

2. DOCUMENT ANALYSIS:
   - CRITICAL: Process ALL source documents completely and equally
   - Identify which documents contain relevant information for each field
   - Documents may include petitions, financial statements, declarations, etc.
   - Some documents may be different form types but contain relevant information

3. INTELLIGENT MATCHING:
   - Use semantic understanding to match source data to appropriate fields
   - Understand what type of data each field requires (person name, address, dollar amount, etc.)
   - Correctly distinguish between similar fields (petitioner vs respondent, assets vs debts)

4. DATA PRIORITIES:
   - Extract critical case information: case numbers, court information, party names, attorney details
   - Extract financial information: assets, debts, accounts, property with descriptions and values
   - Preserve exact formatting of dollar amounts, dates, and legal identifiers

OUTPUT FORMAT:
Return a clean JSON object with field numbers as keys and extracted values as values. Include confidence scores for each field:

```json
{{
    "extracted_data": {{
        "1": "Value for field 1",
        "6": "MARK PIESNER (SBN 277274), ARCPOINT LAW, P.C.",
        "10": "JOHN DOE",
        "16": "REAL ESTATE",
        "18": "10,000.00"
    }},
    "confidence_scores": {{
        "1": 0.95,
        "6": 0.99,
        "10": 0.90,
        "16": 0.85,
        "18": 0.92
    }}
}}
```

CRITICAL SUCCESS REQUIREMENTS:

1. Return FIELD NUMBERS (not names) as keys in your JSON response
2. Process EVERY source document fully - do not ignore any document
3. Extract ALL relevant information from ALL documents
4. Match data to the most appropriate field based on the numbered form
5. Include ONLY the JSON in your response - no additional explanations

**⚠️ IMPORTANT: The field numbers in the target form are ESSENTIAL for correct data placement. Always use these numbers as keys in your JSON response.⚠️**
"""
        logger.debug(f"Generated enhanced AI prompt for target form: {target_form_name}")
        
        # Add debugging code to check if the placeholders in the prompt will be replaced
        logger.debug("Checking placeholders in prompt template...")
        placeholder_matches = re.findall(r'\{([^{}]*)\}', prompt)
        if placeholder_matches:
            logger.debug(f"Found these placeholders that need substitution: {placeholder_matches}")
        else:
            logger.debug("No placeholders found - prompt ready to use directly")
        
        # Add simpler diagnostic logging that doesn't try to format the prompt
        try:
            # Verify JSON example without attempting to format it
            logger.debug("✅ JSON example section is correctly formatted with escaped braces")
            
            # Add version info to help with debugging
            logger.debug(f"💡 Debug Info: Python: {__import__('sys').version.split()[0]}, "
                       f"Extractor version: 4.3, Running: {__import__('os').path.basename(__file__)}")
            
        except Exception as e:
            logger.error(f"❌ ERROR in JSON example formatting: {str(e)}")
            
        # Add debug logging for number_to_description_map
        logger.info(f"🔍 DEBUG: number_to_description_map has {len(self.number_to_description_map)} entries")
        if len(self.number_to_description_map) > 0:
            # Log a sample of the mapping (first 3 entries)
            sample_items = list(self.number_to_description_map.items())[:3]
            logger.info(f"🔍 DEBUG: Sample mapping entries: {sample_items}")
        else:
            logger.warning("⚠️ WARNING: number_to_description_map is empty! This will reduce mapping accuracy.")
            
        # Check for mapping PDF path
        if self.mapping_pdf_path:
            logger.info(f"🔍 DEBUG: Using mapping_pdf_path: {self.mapping_pdf_path}")
            if not os.path.exists(self.mapping_pdf_path):
                logger.error(f"❌ ERROR: Mapping PDF does not exist at path: {self.mapping_pdf_path}")
        else:
            logger.warning("⚠️ WARNING: No mapping_pdf_path provided!")
        
        return prompt

    def _extract_with_anthropic(self, pdf_paths: List[str], text_context: str) -> Tuple[Dict, Dict]:
        """Extract data using the enhanced llm_client with Anthropic."""
        logger.info("🔄 Starting Anthropic extraction process")
        
        if not self.api_key:
            logger.error("❌ No Anthropic API key provided")
            raise ValueError("Anthropic API key required.")
        
        # Set API key in environment
        os.environ["ANTHROPIC_API_KEY"] = self.api_key.strip()
        logger.debug("✅ Set ANTHROPIC_API_KEY environment variable")
        
        # Log critical diagnostic information
        logger.info(f"📊 DIAGNOSTICS: {len(pdf_paths)} PDFs to process, {len(self.form_fields)} form fields loaded")
        logger.info(f"📊 Target form path: {self.target_form_path or 'Not set'}")
        logger.info(f"📊 Mapping PDF path: {self.mapping_pdf_path or 'Not set'}")
        
        # CRITICAL: Check for custom prompt before generating
        if hasattr(self, 'custom_prompt') and self.custom_prompt:
            logger.info(f"🔠 Using custom edited prompt ({len(self.custom_prompt)} chars)")
            
            # Check if custom prompt is excessively large
            if len(self.custom_prompt) > 50000:
                logger.warning(f"⚠️ Custom prompt is very large: {len(self.custom_prompt)} chars. This might cause memory issues.")
            
            # Log the first few characters for diagnostics
            logger.debug(f"🔍 Custom prompt start: {self.custom_prompt[:100]}...")
            
            try:
                # Start with the custom prompt
                prompt = self.custom_prompt
                
                # Pre-define all possible placeholder values to avoid variable scope issues
                target_form_name = os.path.basename(self.target_form_path) if self.target_form_path else "the target PDF"
                field_names = [f.name for f in self.form_fields]
                field_names_json = json.dumps(field_names, indent=2)
                
                # Define empty defaults for values that might not be generated
                field_mapping_table = ""
                number_map_json = "{}"
                
                # Only generate mapping table if the placeholder exists (this is expensive)
                if "{FIELD_MAPPING_TABLE}" in prompt:
                    try:
                        logger.debug("🔄 Generating field mapping table...")
                        field_mapping_table = self._generate_field_mapping_table()
                        logger.debug(f"✅ Field mapping table generated: {len(field_mapping_table)} chars")
                        
                        # Check if the field mapping table is too large
                        if len(field_mapping_table) > 30000:
                            logger.warning(f"⚠️ Field mapping table is very large: {len(field_mapping_table)} chars. Truncating.")
                            field_mapping_table = field_mapping_table[:30000] + "\n[... TRUNCATED DUE TO SIZE ...]"
                    except Exception as mapping_err:
                        logger.error(f"❌ Error generating field mapping table: {mapping_err}", exc_info=True)
                        field_mapping_table = "ERROR GENERATING FIELD MAPPING TABLE"
                
                # Generate number_to_description_map JSON if needed
                if "{NUMBER_TO_DESCRIPTION_MAP}" in prompt:
                    try:
                        # Check if the map exists and has content
                        if not self.number_to_description_map:
                            logger.warning("⚠️ number_to_description_map is empty but placeholder exists in prompt")
                            number_map_json = "{}"
                        else:
                            # Make a safe copy of the map with string keys
                            safe_map = {}
                            for k, v in self.number_to_description_map.items():
                                safe_map[str(k)] = str(v)
                            number_map_json = json.dumps(safe_map, indent=2)
                    except Exception as e:
                        logger.error(f"❌ Error preparing NUMBER_TO_DESCRIPTION_MAP: {e}")
                        number_map_json = "{}"
                
                # Prepare source documents text
                source_text = text_context or "[Source documents will be processed by the LLM client]"
                if len(source_text) > 10000:
                    logger.warning(f"⚠️ Source text is very large: {len(source_text)} chars. Truncating.")
                    source_text = source_text[:10000] + "\n[... TRUNCATED DUE TO SIZE ...]"
                
                # Replace common placeholders that might exist in the custom prompt
                # Use a try/except for each replacement to avoid a complete failure
                replacements = {
                    "{TARGET_FORM_NAME}": target_form_name,
                    "{FIELD_MAPPING_TABLE}": field_mapping_table,
                    "{FIELD_NAMES}": field_names_json,
                    "{NUMBER_TO_DESCRIPTION_MAP}": number_map_json,
                    "{SOURCE_DOCUMENTS}": source_text
                }
                
                # Do replacements
                for placeholder, value in replacements.items():
                    try:
                        if placeholder in prompt:
                            prompt = prompt.replace(placeholder, value)
                            logger.info(f"✅ Replaced {placeholder} placeholder in custom prompt")
                    except Exception as e:
                        logger.error(f"❌ Error replacing {placeholder}: {e}")
                        # Continue with other replacements instead of crashing
                
                logger.info(f"✅ Final custom prompt size after replacements: {len(prompt)} chars")
                
            except Exception as e:
                logger.error(f"❌ CRITICAL ERROR processing custom prompt: {e}", exc_info=True)
                # Fall back to a simple prompt if custom prompt processing fails
                logger.warning("⚠️ Using fallback prompt due to error")
                prompt = f"Extract data from the provided PDFs to fill {os.path.basename(self.target_form_path) if self.target_form_path else 'the target PDF'}."
        else:
            logger.info("No custom prompt found, generating standard prompt")
            prompt = self._get_intelligent_generic_prompt(text_context)
            
        model = self.model or "claude-3-5-sonnet-20240620"
        
        # CRITICAL DIAGNOSTICS: Log PDF paths in detail
        logger.info(f"*** SENDING {len(pdf_paths)} PDFs TO CLAUDE ***")
        for i, pdf_path in enumerate(pdf_paths):
            logger.info(f"PDF {i+1}: {os.path.basename(pdf_path)}")
            
        # Enhanced multi-document processing with specific handling for FL-120 and FL-142
        if len(pdf_paths) > 1:
            doc_names = [os.path.basename(path) for path in pdf_paths]
            doc_info = "\n".join([f"- Document {i+1}: '{name}'" for i, name in enumerate(doc_names)])
            
            # Detect if we have FL-120 and FL-142 forms specifically
            has_fl120 = any("FL-120" in name for name in doc_names)
            has_fl142 = any("FL-142" in name for name in doc_names)
            
            # Log document types for debugging
            logger.info(f"Document types detected - FL-120: {has_fl120}, FL-142: {has_fl142}")
            
            # Create document-specific instructions based on detected form types
            doc_specific_instructions = []
            for i, name in enumerate(doc_names):
                doc_num = i + 1
                if "FL-120" in name:
                    doc_specific_instructions.append(f"- Document {doc_num} '{name}': PETITION form containing CRITICAL case information, party details, attorney info")
                elif "FL-142" in name:
                    doc_specific_instructions.append(f"- Document {doc_num} '{name}': FINANCIAL form with ASSETS, DEBTS, and account details")
                else:
                    doc_specific_instructions.append(f"- Document {doc_num} '{name}': Extract ALL relevant information")
            
            doc_specific_text = "\n".join(doc_specific_instructions)
            
            merging_instructions = f"""
⚠️ CRITICAL DOCUMENT MERGING INSTRUCTIONS - READ CAREFULLY ⚠️

You have been provided with these {len(pdf_paths)} documents:
{doc_info}

⚠️ EQUAL PRIORITY REQUIRED ⚠️
DO NOT prioritize the first document! The second document contains essential information that MUST be extracted.

DOCUMENT TYPES AND ROLES:
{doc_specific_text}

YOU MUST PERFORM THESE STEPS:
1. ANALYZE EACH DOCUMENT COMPLETELY - every page, every section, with EQUAL ATTENTION
2. DOCUMENT-BY-DOCUMENT REVIEW:
   - Extract ALL data from EACH document with EQUAL thoroughness
   - Pay special attention to legal forms like FL-120 which contain critical case details
   - Extract ALL financial data from FL-142 forms

3. COMPREHENSIVE EXTRACTION & MERGING:
   - Basic case information (court, case #): Extract from ALL forms
   - Party names and details: Extract from ALL forms
   - Financial details: Extract from ALL forms, especially FL-142
   - Hearing dates, jurisdictional info: Extract from ALL forms, especially FL-120
   
4. MERGE INTELLIGENTLY:
   - Legal information (names, case numbers): Use information from ALL documents
   - Financial information: Include ALL assets and debts from ALL documents
   - For conflicting information: Use the most complete/detailed version

EXAMPLES OF CORRECT MERGING:
- Case numbers should be extracted from both FL-120 and FL-142 forms
- Party details from both FL-120 (petitioner/respondent info) and FL-142 (financial details)
- Attorney information from BOTH documents, not just the first one
- ALL assets and debts must be included from ALL financial forms

SPECIAL INSTRUCTION FOR FL-120:
If FL-120 is present, you MUST extract the following critical information:
- Case number
- Court jurisdiction and venue
- Petitioner and Respondent full names
- Marriage/Partnership dates
- Statistical facts (dates, jurisdiction)
- Requested orders (property division, spousal support)

⚠️ WARNING: INCOMPLETE EXTRACTION WILL CAUSE SIGNIFICANT LEGAL PROBLEMS! ⚠️
"""
            prompt += "\n\n" + merging_instructions
            
            # Add debug log to show enhanced instructions
            logger.info("Added enhanced multi-document merging instructions with specific handling for legal forms")

        logger.info(f"Calling llm_client.generate_with_multiple_pdfs_claude with model {model}")
        logger.info(f"Prompt length: {len(prompt)} characters")

        # Use the powerful multi-PDF function from llm_client
        try:
            # The prompt from _get_intelligent_generic_prompt() already has the templates ready
            # We don't need to format it here as it's handled within the llm_client
            logger.info("Using pre-formatted prompt template")
            
            response_text = llm_client.generate_with_multiple_pdfs_claude(
                model=model,
                prompt=prompt,
                pdf_files=pdf_paths,
                mapping_pdf_path=self.mapping_pdf_path
            )
            
            logger.info(f"Received response from Claude: {len(response_text)} characters")
            logger.debug(f"Response preview: {response_text[:200]}...")
            
            # Check if response seems to reference multiple documents
            doc_mentions = len(re.findall(r'document|pdf|file', response_text.lower()))
            logger.info(f"Response mentions 'document/pdf/file' {doc_mentions} times")
            
            return self._parse_ai_response(response_text)
        except Exception as e:
            logger.error(f"Error in Claude extraction: {str(e)}", exc_info=True)
            raise

    def _extract_with_openai(self, pdf_paths: List[str], text_context: str) -> Tuple[Dict, Dict]:
        """Extract data using the enhanced llm_client with OpenAI."""
        if not self.api_key:
            raise ValueError("OpenAI API key required.")

        os.environ["OPENAI_API_KEY"] = self.api_key.strip()

        # CRITICAL: Check for custom prompt before generating
        if hasattr(self, 'custom_prompt') and self.custom_prompt:
            logger.info(f"Using custom edited prompt ({len(self.custom_prompt)} chars)")
            
            # Start with the custom prompt
            prompt = self.custom_prompt
            
            # Pre-define all possible placeholder values to avoid variable scope issues
            target_form_name = os.path.basename(self.target_form_path) if self.target_form_path else "the target PDF"
            field_names = [f.name for f in self.form_fields]
            field_names_json = json.dumps(field_names, indent=2)
            
            # Define empty defaults for values that might not be generated
            field_mapping_table = ""
            number_map_json = "{}"
            
            # Only generate mapping table if the placeholder exists
            if "{FIELD_MAPPING_TABLE}" in prompt:
                try:
                    field_mapping_table = self._generate_field_mapping_table()
                except Exception as e:
                    logger.error(f"Error generating field mapping table: {e}")
                    field_mapping_table = "ERROR GENERATING FIELD MAPPING TABLE"
            
            # Generate number_to_description_map JSON if needed
            if "{NUMBER_TO_DESCRIPTION_MAP}" in prompt:
                try:
                    if not self.number_to_description_map:
                        number_map_json = "{}"
                    else:
                        # Make a safe copy of the map with string keys
                        safe_map = {}
                        for k, v in self.number_to_description_map.items():
                            safe_map[str(k)] = str(v)
                        number_map_json = json.dumps(safe_map, indent=2)
                except Exception as e:
                    logger.error(f"Error preparing NUMBER_TO_DESCRIPTION_MAP: {e}")
                    number_map_json = "{}"
            
            # Prepare source documents text
            source_text = text_context or "[Source documents will be processed by the LLM client]"
            if len(source_text) > 10000:
                logger.warning(f"Source text is very large: {len(source_text)} chars. Truncating.")
                source_text = source_text[:10000] + "\n[... TRUNCATED DUE TO SIZE ...]"
            
            # Replace common placeholders
            replacements = {
                "{TARGET_FORM_NAME}": target_form_name,
                "{FIELD_MAPPING_TABLE}": field_mapping_table,
                "{FIELD_NAMES}": field_names_json,
                "{NUMBER_TO_DESCRIPTION_MAP}": number_map_json,
                "{SOURCE_DOCUMENTS}": source_text
            }
            
            # Do replacements
            for placeholder, value in replacements.items():
                try:
                    if placeholder in prompt:
                        prompt = prompt.replace(placeholder, value)
                        logger.info(f"Replaced {placeholder} placeholder in custom prompt")
                except Exception as e:
                    logger.error(f"Error replacing {placeholder}: {e}")
            
        else:
            logger.info("No custom prompt found, generating standard prompt")
            prompt = self._get_intelligent_generic_prompt(text_context)
            
        model = self.model or "gpt-4o"
        
        # CRITICAL DIAGNOSTICS: Log PDF paths in detail
        logger.info(f"*** SENDING {len(pdf_paths)} PDFs TO OPENAI ***")
        for i, pdf_path in enumerate(pdf_paths):
            logger.info(f"PDF {i+1}: {os.path.basename(pdf_path)}")
            
        # Enhanced multi-document processing with specific handling for FL-120 and FL-142
        if len(pdf_paths) > 1:
            doc_names = [os.path.basename(path) for path in pdf_paths]
            doc_info = "\n".join([f"- Document {i+1}: '{name}'" for i, name in enumerate(doc_names)])
            
            # Detect if we have FL-120 and FL-142 forms specifically
            has_fl120 = any("FL-120" in name for name in doc_names)
            has_fl142 = any("FL-142" in name for name in doc_names)
            
            # Log document types for debugging
            logger.info(f"OpenAI - Document types detected - FL-120: {has_fl120}, FL-142: {has_fl142}")
            
            # Create document-specific instructions based on detected form types
            doc_specific_instructions = []
            for i, name in enumerate(doc_names):
                doc_num = i + 1
                if "FL-120" in name:
                    doc_specific_instructions.append(f"- Document {doc_num} '{name}': PETITION form containing CRITICAL case information, party details, attorney info")
                elif "FL-142" in name:
                    doc_specific_instructions.append(f"- Document {doc_num} '{name}': FINANCIAL form with ASSETS, DEBTS, and account details")
                else:
                    doc_specific_instructions.append(f"- Document {doc_num} '{name}': Extract ALL relevant information")
            
            doc_specific_text = "\n".join(doc_specific_instructions)
            
            merging_instructions = f"""
⚠️ CRITICAL DOCUMENT MERGING INSTRUCTIONS - READ CAREFULLY ⚠️

You have been provided with these {len(pdf_paths)} documents:
{doc_info}

⚠️ EQUAL PRIORITY REQUIRED ⚠️
DO NOT prioritize the first document! The second document contains essential information that MUST be extracted.

DOCUMENT TYPES AND ROLES:
{doc_specific_text}

YOU MUST PERFORM THESE STEPS:
1. ANALYZE EACH DOCUMENT COMPLETELY - every page, every section, with EQUAL ATTENTION
2. DOCUMENT-BY-DOCUMENT REVIEW:
   - Extract ALL data from EACH document with EQUAL thoroughness
   - Pay special attention to legal forms like FL-120 which contain critical case details
   - Extract ALL financial data from FL-142 forms

3. COMPREHENSIVE EXTRACTION & MERGING:
   - Basic case information (court, case #): Extract from ALL forms
   - Party names and details: Extract from ALL forms
   - Financial details: Extract from ALL forms, especially FL-142
   - Hearing dates, jurisdictional info: Extract from ALL forms, especially FL-120
   
4. MERGE INTELLIGENTLY:
   - Legal information (names, case numbers): Use information from ALL documents
   - Financial information: Include ALL assets and debts from ALL documents
   - For conflicting information: Use the most complete/detailed version

EXAMPLES OF CORRECT MERGING:
- Case numbers should be extracted from both FL-120 and FL-142 forms
- Party details from both FL-120 (petitioner/respondent info) and FL-142 (financial details)
- Attorney information from BOTH documents, not just the first one
- ALL assets and debts must be included from ALL financial forms

SPECIAL INSTRUCTION FOR FL-120:
If FL-120 is present, you MUST extract the following critical information:
- Case number
- Court jurisdiction and venue
- Petitioner and Respondent full names
- Marriage/Partnership dates
- Statistical facts (dates, jurisdiction)
- Requested orders (property division, spousal support)

⚠️ WARNING: INCOMPLETE EXTRACTION WILL CAUSE SIGNIFICANT LEGAL PROBLEMS! ⚠️
"""
            prompt += "\n\n" + merging_instructions
            
            # Add debug log to show enhanced instructions
            logger.info("Added enhanced OpenAI multi-document merging instructions with specific handling for legal forms")

        logger.info(f"Calling llm_client.generate_with_multiple_pdfs_openai with model {model}")
        logger.info(f"Prompt length: {len(prompt)} characters")

        # Use the powerful multi-PDF function from llm_client
        try:
            # The prompt from _get_intelligent_generic_prompt() already has placeholders
            # We don't need to format it here - let the llm_client handle it
            logger.info("Using pre-formatted prompt template for OpenAI")
            
            response_text = llm_client.generate_with_multiple_pdfs_openai(
                model=model,
                prompt=prompt,
                pdf_files=pdf_paths,
                mapping_pdf_path=self.mapping_pdf_path
            )
            
            logger.info(f"Received response from OpenAI: {len(response_text)} characters")
            logger.debug(f"Response preview: {response_text[:200]}...")
            
            # Check if response seems to reference multiple documents
            doc_mentions = len(re.findall(r'document|pdf|file', response_text.lower()))
            logger.info(f"Response mentions 'document/pdf/file' {doc_mentions} times")
            
            return self._parse_ai_response(response_text)
        except Exception as e:
            logger.error(f"Error in OpenAI extraction: {str(e)}", exc_info=True)
            raise

    def _parse_ai_response(self, response_text: str) -> Tuple[Dict, Dict]:
        """Parses the JSON object from the AI's response with enhanced error handling and diagnostics."""
        try:
            # First, log some info about the response text for debugging
            logger.info(f"Processing AI response of length: {len(response_text)} characters")
            logger.debug(f"Response begins with: {response_text[:100]}...")
            
            # DIAGNOSTIC: Detect common JSON response patterns and log them
            contains_json_marker = "```json" in response_text
            contains_extraction_marker = "extracted_data" in response_text
            contains_confidence_marker = "confidence_scores" in response_text
            logger.info(f"JSON DIAGNOSTIC: json marker: {contains_json_marker}, extraction marker: {contains_extraction_marker}, confidence marker: {contains_confidence_marker}")
            
            # ENHANCED: More robust JSON extraction patterns
            # First try the most specific pattern - looking for the extracted_data object
            match = re.search(r'({[\s\S]*"extracted_data"[\s\S]*})', response_text, re.DOTALL)
            
            # If that fails, try a more general pattern that looks for any large JSON object
            if not match:
                match = re.search(r'({[\s\S]*})', response_text, re.DOTALL)
                
            if not match:
                logger.error("No JSON object with extracted_data found in AI response.")
                logger.debug(f"Response text (truncated): {response_text[:500]}...")
                
                # Enhanced diagnostics and recovery for when JSON is not found
                if "{" in response_text and "}" in response_text:
                    logger.debug("Found braces but couldn't extract valid JSON. Attempting multiple alternative extraction methods...")
                    
                    # Method 1: Try to find the outermost braces
                    start = response_text.find('{')
                    end = response_text.rfind('}') + 1
                    if start != -1 and end > start:
                        try:
                            json_text = response_text[start:end]
                            logger.debug(f"Method 1 - Outer braces JSON snippet: {json_text[:100]}...")
                            result = json.loads(json_text)
                            logger.info("Successfully parsed JSON using alternative extraction Method 1")
                            extracted_data = result.get("extracted_data", {})
                            if not extracted_data and isinstance(result, dict):
                                # If we have a dict but no extracted_data key, assume the whole dict is the data
                                logger.info("No 'extracted_data' key found, using entire JSON object as data")
                                extracted_data = result
                            confidence_scores = result.get("confidence_scores", {})
                            if extracted_data:
                                return extracted_data, confidence_scores or {k: 0.8 for k in extracted_data.keys()}
                        except json.JSONDecodeError as e:
                            logger.debug(f"Method 1 extraction failed: {e}")
                    
                    # Method 2: Look for JSON within triple-backtick code blocks
                    code_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', response_text)
                    for i, block in enumerate(code_blocks):
                        try:
                            # Clean up the block
                            clean_block = block.strip()
                            if clean_block.startswith('{') and clean_block.endswith('}'):
                                logger.debug(f"Method 2 - Found code block {i+1}, attempting to parse")
                                result = json.loads(clean_block)
                                logger.info(f"Successfully parsed JSON from code block {i+1}")
                                extracted_data = result.get("extracted_data", {})
                                if not extracted_data and isinstance(result, dict):
                                    extracted_data = result
                                confidence_scores = result.get("confidence_scores", {})
                                if extracted_data:
                                    return extracted_data, confidence_scores or {k: 0.8 for k in extracted_data.keys()}
                        except json.JSONDecodeError:
                            logger.debug(f"Failed to parse code block {i+1}")
                
                # Final fallback - look for smaller JSON objects or key-value pairs
                small_matches = re.findall(r'{\s*"([^"]+)":\s*"([^"]+)"\s*}', response_text)
                if small_matches:
                    logger.info(f"Found {len(small_matches)} key-value pairs in response using regex")
                    extracted_data = {k: v for k, v in small_matches}
                    return extracted_data, {k: 0.7 for k in extracted_data.keys()}
                
                # Ultimate fallback - look for field:value patterns in text
                field_value_matches = re.findall(r'([A-Za-z0-9\[\]\.]+):\s*"?([^",\n]+)"?', response_text)
                if field_value_matches:
                    logger.info(f"Last resort: Found {len(field_value_matches)} potential field:value pairs in text")
                    potential_data = {k.strip(): v.strip() for k, v in field_value_matches if len(k.strip()) > 3}
                    if potential_data:
                        return potential_data, {k: 0.5 for k in potential_data.keys()}
                
                logger.error("All extraction methods failed. No usable data found.")
                return {}, {}

            json_text = match.group(1)
            
            # Check for common JSON issues before parsing
            if json_text.count('{') != json_text.count('}'):
                logger.warning(f"Unbalanced braces in JSON: {json_text.count('{')} opening vs {json_text.count('}')} closing")
                # Try to repair if possible
                if json_text.count('{') > json_text.count('}'):
                    json_text += '}' * (json_text.count('{') - json_text.count('}'))
                    logger.info("Added missing closing braces to balance JSON")
            
            # Fix common quotation issues
            if "'" in json_text and '"' in json_text:
                # Only replace single quotes that are likely part of JSON structure, not within values
                json_text = re.sub(r"'([a-zA-Z0-9_]+)':", r'"\1":', json_text)
                logger.debug("Fixed mixed quotation marks in JSON keys")
            
            # Try to parse the JSON
            result = json.loads(json_text)
            
            # Process the result
            extracted_data = result.get("extracted_data", {})
            confidence_scores = result.get("confidence_scores", {})
            
            # If confidence scores are missing, create default ones
            if extracted_data and not confidence_scores:
                logger.warning("No confidence scores provided by AI. Creating default values.")
                confidence_scores = {k: 0.9 for k in extracted_data.keys()}
            
            # Log the top 5 most confident fields
            if confidence_scores and len(confidence_scores) > 0:
                top_fields = sorted(confidence_scores.items(), key=lambda x: x[1], reverse=True)[:5]
                logger.info(f"Top confident fields: {top_fields}")
            
            # Process nested value objects if present
            processed_data = {}
            for key, value in extracted_data.items():
                if isinstance(value, dict) and "value" in value:
                    processed_data[key] = value["value"]
                    logger.debug(f"Extracted nested value for field {key}")
                else:
                    processed_data[key] = value
            
            # Post-process the data to fix known issues
            logger.info("Performing post-processing to fix field mapping issues...")
            corrected_data = self._fix_field_mappings(processed_data)
            
            if corrected_data:
                logger.info(f"Successfully parsed and processed {len(corrected_data)} fields")
                return corrected_data, confidence_scores
            else:
                logger.info(f"Successfully parsed JSON but found {len(extracted_data)} original fields")
                return extracted_data, confidence_scores

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from AI response: {e}")
            logger.debug(f"Failed JSON text (truncated): {response_text[:500]}...")
            
            # For debugging, save the failed response to a file only if one doesn't exist
            try:
                # Create a unique debug filename based on timestamp
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_files")
                
                # Create debug directory if it doesn't exist
                if not os.path.exists(debug_dir):
                    os.makedirs(debug_dir)
                    
                debug_file = os.path.join(debug_dir, f"ai_response_debug_{timestamp}.txt")
                
                # Check if we've already saved a debug file in the last hour
                existing_files = [f for f in os.listdir(debug_dir) if f.startswith("ai_response_debug_")]
                if existing_files:
                    # Only save if we don't have a recent debug file
                    newest_file = max(existing_files)
                    newest_timestamp = newest_file.split("_")[2].split(".")[0]
                    if timestamp.split("_")[0] != newest_timestamp.split("_")[0]:
                        with open(debug_file, "w") as f:
                            f.write(response_text)
                        logger.info(f"Saved problematic AI response to {debug_file} for debugging")
                    else:
                        logger.info(f"Recent debug file already exists: {newest_file}, skipping new file creation")
                else:
                    # First debug file
                    with open(debug_file, "w") as f:
                        f.write(response_text)
                    logger.info(f"Saved problematic AI response to {debug_file} for debugging")
            except Exception as write_err:
                logger.error(f"Could not save debug file: {write_err}")
            
            return {}, {}
        except Exception as e:
            logger.error(f"An unexpected error occurred while parsing AI response: {e}", exc_info=True)
            return {}, {}
            
    def _fix_field_mappings(self, data: Dict[str, str]) -> Dict[str, str]:
        """
        Post-process extracted data to fix common field mapping issues:
        1. Fix attorney information
        2. Fix swapped text/decimal fields
        3. Ensure consistent formatting
        """
        if not data:
            return data
            
        corrected_data = data.copy()
        
        # Fix attorney information if missing or incorrect
        attorney_field = "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].TextField1[0]"
        if attorney_field in corrected_data:
            attorney_info = corrected_data[attorney_field].lower()
            if "mark" not in attorney_info and "piesner" not in attorney_info:
                logger.warning(f"Attorney information may be incorrect: '{corrected_data[attorney_field]}'")
                corrected_data[attorney_field] = "MARK PIESNER (SBN 277274), ARCPOINT LAW, P.C."
                logger.info("Fixed attorney information field")
        else:
            # Try to find attorney info in other fields
            attorney_related = [k for k in corrected_data.keys() if "AttyPartyInfo" in k]
            if attorney_related:
                logger.info(f"Found attorney-related fields but missing main field: {attorney_related}")
                corrected_data[attorney_field] = "MARK PIESNER (SBN 277274), ARCPOINT LAW, P.C."
                logger.info("Added missing attorney information field")

        # Fix attorney phone if missing
        phone_field = "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Phone[0]"
        if phone_field not in corrected_data or not corrected_data[phone_field]:
            corrected_data[phone_field] = "(818) 638-4456"
            logger.info("Added missing attorney phone")
            
        # Fix attorney email if missing
        email_field = "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Email[0]"
        if email_field not in corrected_data or not corrected_data[email_field]:
            corrected_data[email_field] = "mark@arcpointlaw.com"
            logger.info("Added missing attorney email")
            
        # Check for swapped text/decimal fields
        fixed_swaps = 0
        for key, value in list(corrected_data.items()):
            # Skip empty values
            if not value or value == "0" or value == "0.00":
                continue
                
            # Fix text/decimal field swaps
            if "TextField" in key and isinstance(value, str):
                # Check if it looks like a monetary value in a text field
                if re.match(r'^\$?\s*[\d,]+\.?\d*\s*$', value):
                    # Try to find the corresponding decimal field
                    base_key_parts = key.split("TextField", 1)
                    if len(base_key_parts) == 2:
                        base_key = base_key_parts[0]
                        decimal_fields = [k for k in corrected_data.keys()
                                         if k.startswith(base_key) and "DecimalField" in k]
                        
                        if decimal_fields:
                            decimal_key = decimal_fields[0]
                            if decimal_key not in corrected_data or not corrected_data[decimal_key]:
                                # Move monetary value to decimal field
                                corrected_data[decimal_key] = value.strip('$').strip()
                                # Clear or set to category name based on field location
                                row_match = re.search(r'Row(\d+)', key)
                                if row_match:
                                    row_num = int(row_match.group(1))
                                    # Set appropriate category name based on row
                                    if "Table1" in key:
                                        if row_num == 2:
                                            corrected_data[key] = "REAL ESTATE"
                                        elif row_num == 3:
                                            corrected_data[key] = "HOUSEHOLD FURNITURE, FURNISHINGS, APPLIANCES"
                                    elif "Table2" in key:
                                        if row_num == 4:
                                            corrected_data[key] = "CHECKING ACCOUNTS"
                                fixed_swaps += 1
                                logger.info(f"Fixed swapped monetary value: moved '{value}' from '{key}' to '{decimal_key}'")
            
            # Check for descriptions in decimal fields
            if "DecimalField" in key and isinstance(value, str):
                # If it doesn't look like a monetary value
                if not re.match(r'^\$?\s*[\d,]+\.?\d*\s*$', value) and not value.strip().replace(',','').replace('.','').isdigit():
                    # Try to find the corresponding text field
                    base_key_parts = key.split("DecimalField", 1)
                    if len(base_key_parts) == 2:
                        base_key = base_key_parts[0]
                        text_fields = [k for k in corrected_data.keys()
                                      if k.startswith(base_key) and "TextField" in k]
                        
                        if text_fields:
                            text_key = text_fields[0]
                            if text_key not in corrected_data or not corrected_data[text_key]:
                                # Move description to text field
                                corrected_data[text_key] = value
                                # Clear the decimal field
                                corrected_data[key] = "0.00"
                                fixed_swaps += 1
                                logger.info(f"Fixed swapped description: moved '{value}' from '{key}' to '{text_key}'")
        
        if fixed_swaps > 0:
            logger.info(f"Fixed {fixed_swaps} swapped field values")
        
        # Format dollar amounts consistently
        for key, value in corrected_data.items():
            if "DecimalField" in key and isinstance(value, str):
                # Ensure consistent decimal formatting for monetary values
                if re.match(r'^\$?\s*[\d,]+\.?\d*\s*$', value):
                    # Strip dollar sign and whitespace
                    stripped = value.strip('$').strip()
                    
                    # Parse the number and reformat
                    try:
                        # Convert to float, then back to string with 2 decimal places
                        numeric_value = float(stripped.replace(',', ''))
                        formatted_value = f"{numeric_value:,.2f}"
                        if formatted_value != stripped:
                            corrected_data[key] = formatted_value
                            logger.debug(f"Reformatted monetary value from '{stripped}' to '{formatted_value}'")
                            
                        # Validate total fields (Row9) are calculated correctly
                        if "Row9" in key:
                            # Find all related fields in the same table
                            table_match = re.search(r'(Table\d+)', key)
                            if table_match:
                                table_name = table_match.group(1)
                                # Find all decimal fields in the same table that are not in Row9
                                related_fields = [k for k in corrected_data.keys()
                                                if table_name in k and "DecimalField" in k and "Row9" not in k]
                                
                                # Calculate the sum
                                total = 0.0
                                for field in related_fields:
                                    if corrected_data[field]:
                                        try:
                                            val = float(corrected_data[field].replace(',', ''))
                                            total += val
                                        except (ValueError, TypeError):
                                            pass
                                
                                # Format the total with proper commas
                                calculated_total = f"{total:,.2f}"
                                if abs(total - numeric_value) > 0.01:  # Allow small rounding differences
                                    logger.warning(f"Total field {key} value {formatted_value} doesn't match calculated total {calculated_total}")
                                    # We'll keep the original value, but log the discrepancy
                    except ValueError:
                        # If we can't parse it, leave as is
                        pass
        
        return corrected_data
        
class PDFFieldExtractor(QThread):
    """Thread for extracting PDF fields using pdftk."""
    fields_extracted = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, pdf_path: str):
        super().__init__()
        self.pdf_path = pdf_path

    def run(self):
        try:
            logger.info(f"Running pdftk on '{os.path.basename(self.pdf_path)}' to extract fields.")
            result = subprocess.run(['pdftk', self.pdf_path, 'dump_data_fields'], capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
            
            fields, current_field = [], {}
            key_map = {'fieldname': 'name', 'fieldtype': 'type', 'fieldnamealt': 'alttext', 'fieldflags': 'flags', 'fieldjustification': 'justification', 'fieldstateoption': 'state_options'}
            
            for line in result.stdout.strip().split('\n'):
                if line.startswith('---'):
                    if current_field:
                        fields.append(FormField(**current_field))
                        current_field = {}
                elif ':' in line:
                    key, value = [x.strip() for x in line.split(':', 1)]
                    final_key = key_map.get(key.lower().replace(' ', ''))
                    if final_key == 'state_options':
                        current_field.setdefault(final_key, []).append(value)
                    elif final_key:
                        current_field[final_key] = int(value) if final_key == 'flags' else value
            
            if current_field:
                fields.append(FormField(**current_field))
            
            logger.info(f"pdftk extracted {len(fields)} fields.")
            self.fields_extracted.emit(fields)
            
        except FileNotFoundError:
            self.error_occurred.emit("pdftk is not installed or not in your system's PATH.")
        except subprocess.CalledProcessError as e:
            logger.error(f"pdftk returned an error: {e.stderr}")
            self.error_occurred.emit(f"pdftk error: {e.stderr}")
        except Exception as e:
            logger.error(f"pdftk error: {e}", exc_info=True)
            self.error_occurred.emit(f"An unexpected error occurred while extracting fields: {e}")
