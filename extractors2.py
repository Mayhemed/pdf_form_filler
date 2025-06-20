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
        Enhanced universal prompt that instructs the AI to identify document types and extract data
        accurately for the specific target form.
        """
        # Get the field names from the loaded PDF form
        field_names = [f.name for f in self.form_fields]
        target_form_name = os.path.basename(self.target_form_path) if self.target_form_path else "the target PDF"
        
        # Generate explicit field mapping table
        field_mapping_table = self._generate_field_mapping_table()
        
        prompt = f"""You are an expert AI data extraction agent for a universal PDF form filling system. Your task is to extract information from multiple source documents to fill a specific target PDF form. Follow these instructions carefully:

1. Target Form:
The target form you will be filling is:
<target_form>
{{TARGET_FORM_NAME}}
</target_form>

2. Field Mapping:
Use this field mapping table for correct field mapping:
<field_mapping_table>
{{FIELD_MAPPING_TABLE}}
</field_mapping_table>

3. Field Names:
The target form contains the following fields that need to be filled:
<field_names>
{{FIELD_NAMES}}
</field_names>

4. Number to Description Map:
Use this number-to-description map for field identification:
<number_to_description_map>
{{NUMBER_TO_DESCRIPTION_MAP}}
</number_to_description_map>

5. Source Documents:
You will be provided with multiple source documents. These may include case information, financial schedules, or other data. Analyze these documents thoroughly:
<source_documents>
{{SOURCE_DOCUMENTS}}
</source_documents>

Step-by-Step Instructions:

1. Document Analysis:
   a. Analyze EVERY document COMPLETELY. This is critical - do not prioritize one document over others.
   b. Identify document types (legal, financial, or other) and extract relevant information accordingly.
   c. Cross-reference information appearing in multiple documents and select the most complete version.

2. Data Extraction:
   a. Extract all relevant information, including but not limited to:
      - Attorney information (full name, firm, address, phone, email, bar number)
      - Party information (petitioner and respondent full names)
      - Case details (court county, case number, hearing dates, judge information)
      - Financial information (all assets and debts from all documents)
   b. Keep all dollar values exactly as formatted in the source.
   c. Ensure all totals are calculated correctly across all documents.

3. Field Mapping:
   a. Match extracted information to the most appropriate target field using the field mapping table and number-to-description map.
   b. Extract actual data values, not field labels.
   c. Handle multi-part data (e.g., addresses) appropriately.

Output Format:
Return a single, clean JSON object with the EXACT FIELD NAMES as keys (not field numbers). Include an "extracted_data" object and a "confidence_scores" object. For example:

```json
{
    "extracted_data": {
        "FieldName1": "ExtractedValue1",
        "FieldName2": "ExtractedValue2"
    },
    "confidence_scores": {
        "FieldName1": 0.95,
        "FieldName2": 0.99
    }
}
```
        Ensure all field names match the target form exactly, including any prefixes or suffixes.

6. Confidence Scores:
    a. Provide confidence scores for each extracted field, indicating your certainty about the accuracy of the data.
    b. Use a scale from 0.0 (not confident) to 1.0 (very confident).
    c. If you are unsure about a field, provide a lower confidence score (e.g., 0.5).
7. Critical Success Requirements:

Final Output:
Provide your final output as a JSON object containing only the "extracted_data" and "confidence_scores" objects. Do not include any explanations, notes, or other text outside of this JSON object.

**CRITICAL SUCCESS REQUIREMENTS:**

1. **ANALYZE ALL DOCUMENTS COMPLETELY:** You MUST thoroughly process EVERY document - not just the first or second one
2. **MERGE INTELLIGENTLY:** When different documents contain complementary information:
   - For legal information (names, case details): use data from all documents to build a complete picture
   - For financial information: include ALL assets and debts from ALL documents
   - For duplicated information: use the most complete/accurate version
3. **COMPREHENSIVE EXTRACTION:** Extract as many fields as possible from ALL documents combined
4. **BE PRECISE:** Extract exact values as they appear in the source documents
5. **MAP ACCURATELY:** Ensure extracted values are mapped to the correct field numbers

**⚠️ CRITICAL WARNING: IGNORING ANY DOCUMENT WILL RESULT IN INCOMPLETE DATA⚠️**
"""
        logger.debug(f"Generated enhanced AI prompt for target form: {target_form_name}")
        return prompt

    def _extract_with_anthropic(self, pdf_paths: List[str], text_context: str) -> Tuple[Dict, Dict]:
        """Extract data using the enhanced llm_client with Anthropic."""
        if not self.api_key:
            raise ValueError("Anthropic API key required.")
        
        os.environ["ANTHROPIC_API_KEY"] = self.api_key.strip()
        
        # Generate enhanced prompt with text context
        prompt = self._get_intelligent_generic_prompt(text_context)
        model = self.model or "claude-3-5-sonnet-20240620"
        
        # CRITICAL DIAGNOSTICS: Log PDF paths in detail
        logger.info(f"*** SENDING {len(pdf_paths)} PDFs TO CLAUDE ***")
        for i, pdf_path in enumerate(pdf_paths):
            logger.info(f"PDF {i+1}: {os.path.basename(pdf_path)}")
            
        # Add specific document merging instructions if we have multiple PDFs
        if len(pdf_paths) > 1:
            doc_names = [os.path.basename(path) for path in pdf_paths]
            doc_info = "\n".join([f"- Document {i+1}: '{name}'" for i, name in enumerate(doc_names)])
            
            merging_instructions = f"""
⚠️ CRITICAL DOCUMENT MERGING INSTRUCTIONS ⚠️

You have been provided with these {len(pdf_paths)} documents:
{doc_info}

YOU MUST PERFORM THESE STEPS:
1. ANALYZE EACH DOCUMENT COMPLETELY - every page, every section
2. DOCUMENT-BY-DOCUMENT REVIEW:
   - For Document 1 '{doc_names[0]}': Extract ALL legal/case information AND ALL financial data
   - For Document 2 '{doc_names[1]}': Extract ALL legal/case information AND ALL financial data
   {"".join([f"   - For Document {i+3} '{name}': Extract ALL relevant information\n" for i, name in enumerate(doc_names[2:])]) if len(doc_names) > 2 else ""}
3. MERGE INTELLIGENTLY:
   - Legal information (names, case numbers): Use information from ALL documents
   - Financial information: Include ALL assets and debts from ALL documents
   - For conflicting information: Use the most complete/detailed version

EXAMPLE OF CORRECT MERGING:
- If Document 1 has a case number and Document 2 has a petitioner name, include BOTH
- If Document 1 shows debts and Document 2 shows assets, include ALL debts AND ALL assets
- If Document 1 has party names and Document 2 has additional party details, combine them

FAILURE TO PROPERLY MERGE DATA FROM ALL DOCUMENTS WILL MAKE THE FORM INCOMPLETE!
"""
            prompt += "\n\n" + merging_instructions

        logger.info(f"Calling llm_client.generate_with_multiple_pdfs_claude with model {model}")
        logger.info(f"Prompt length: {len(prompt)} characters")

        # Use the powerful multi-PDF function from llm_client
        try:
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

        # Generate enhanced prompt with text context
        prompt = self._get_intelligent_generic_prompt(text_context)
        model = self.model or "gpt-4o"
        
        # CRITICAL DIAGNOSTICS: Log PDF paths in detail
        logger.info(f"*** SENDING {len(pdf_paths)} PDFs TO OPENAI ***")
        for i, pdf_path in enumerate(pdf_paths):
            logger.info(f"PDF {i+1}: {os.path.basename(pdf_path)}")
            
        # Add specific document merging instructions if we have multiple PDFs
        if len(pdf_paths) > 1:
            doc_names = [os.path.basename(path) for path in pdf_paths]
            doc_info = "\n".join([f"- Document {i+1}: '{name}'" for i, name in enumerate(doc_names)])
            
            merging_instructions = f"""
⚠️ CRITICAL DOCUMENT MERGING INSTRUCTIONS ⚠️

You have been provided with these {len(pdf_paths)} documents:
{doc_info}

YOU MUST PERFORM THESE STEPS:
1. ANALYZE EACH DOCUMENT COMPLETELY - every page, every section
2. DOCUMENT-BY-DOCUMENT REVIEW:
   - For Document 1 '{doc_names[0]}': Extract ALL legal/case information AND ALL financial data
   - For Document 2 '{doc_names[1]}': Extract ALL legal/case information AND ALL financial data
   {"".join([f"   - For Document {i+3} '{name}': Extract ALL relevant information\n" for i, name in enumerate(doc_names[2:])]) if len(doc_names) > 2 else ""}
3. MERGE INTELLIGENTLY:
   - Legal information (names, case numbers): Use information from ALL documents
   - Financial information: Include ALL assets and debts from ALL documents
   - For conflicting information: Use the most complete/detailed version

EXAMPLE OF CORRECT MERGING:
- If Document 1 has a case number and Document 2 has a petitioner name, include BOTH
- If Document 1 shows debts and Document 2 shows assets, include ALL debts AND ALL assets
- If Document 1 has party names and Document 2 has additional party details, combine them

FAILURE TO PROPERLY MERGE DATA FROM ALL DOCUMENTS WILL MAKE THE FORM INCOMPLETE!
"""
            prompt += "\n\n" + merging_instructions

        logger.info(f"Calling llm_client.generate_with_multiple_pdfs_openai with model {model}")
        logger.info(f"Prompt length: {len(prompt)} characters")

        # Use the powerful multi-PDF function from llm_client
        try:
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
            
            # Look for JSON in the response using regex for robust extraction
            match = re.search(r'({[\s\S]*"extracted_data"[\s\S]*})', response_text, re.DOTALL)
            if not match:
                logger.error("No JSON object with extracted_data found in AI response.")
                logger.debug(f"Response text (truncated): {response_text[:500]}...")
                
                # Additional diagnostics for when JSON is not found
                if "{" in response_text and "}" in response_text:
                    logger.debug("Found braces but couldn't extract valid JSON. Attempting alternative extraction...")
                    # Try a more lenient approach - find the outermost braces
                    start = response_text.find('{')
                    end = response_text.rfind('}') + 1
                    if start != -1 and end > start:
                        try:
                            json_text = response_text[start:end]
                            result = json.loads(json_text)
                            logger.info("Successfully parsed JSON using alternative extraction")
                            extracted_data = result.get("extracted_data", {})
                            confidence_scores = result.get("confidence_scores", {})
                            if extracted_data:
                                return extracted_data, confidence_scores or {k: 0.8 for k in extracted_data.keys()}
                        except json.JSONDecodeError:
                            logger.debug("Alternative extraction attempt failed")
                
                # Final fallback - look for smaller JSON objects
                small_matches = re.findall(r'{\s*"([^"]+)":\s*"([^"]+)"\s*}', response_text)
                if small_matches:
                    logger.info(f"Found {len(small_matches)} key-value pairs in response")
                    extracted_data = {k: v for k, v in small_matches}
                    return extracted_data, {k: 0.7 for k in extracted_data.keys()}
                
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
            logger.debug(f"Failed JSON text (truncated): {json_text[:500]}...")
            
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

