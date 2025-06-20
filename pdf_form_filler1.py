#!/usr/bin/env python3
"""
AI-Powered PDF Form Filler v3 - FIXED VERSION
Author: Assistant
Description: A PyQt6 GUI application for filling any fillable PDF form with AI-powered data extraction
"""

import sys
import json
import subprocess
import tempfile
import os
import re
import base64
import logging
import llm_client
import traceback
try:
    import dotenv
except ImportError:
    dotenv = None
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict

# Set up logging
logging.basicConfig(
    filename='pdf_form_filler_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('PDF_Form_Filler')
logger.info("Application starting")

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QLabel, QLineEdit, QTextEdit, QSplitter, QTabWidget,
    QMessageBox, QProgressBar, QGroupBox, QScrollArea,
    QGridLayout, QComboBox, QSpinBox, QCheckBox, QListWidget,
    QListWidgetItem, QPlainTextEdit, QFrame, QSizePolicy, QRadioButton,
    QInputDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QTimer
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor, QPixmap

# Import field mapping widget
try:
    from fieldmappingwidget import FieldMappingWidget, FormField
    FIELD_MAPPING_AVAILABLE = True
except ImportError:
    FIELD_MAPPING_AVAILABLE = False
    print("⚠️ FieldMappingWidget not available - creating placeholder")
    
    # Create placeholder classes
    @dataclass
    class FormField:
        name: str
        field_type: str = "Text"
        alt_text: str = ""
        flags: int = 0
        justification: str = "Left"
        state_options: List[str] = None
        
        def __post_init__(self):
            if self.state_options is None:
                self.state_options = []
    
    class FieldMappingWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.fields = []
            self.init_ui()
        
        def init_ui(self):
            layout = QVBoxLayout()
            layout.addWidget(QLabel("Field Mapping Widget (Placeholder)"))
            self.setLayout(layout)
        
        def set_fields(self, fields):
            self.fields = fields
        
        def get_field_data(self):
            return {}
        
        def set_field_data(self, data):
            pass

# AI/ML Imports with error handling
try:
    import openai
    OPENAI_AVAILABLE = True
    print("✅ OpenAI library available")
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI library not available")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
    print("✅ Anthropic library available")
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️ Anthropic library not available")

# Optional imports
try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import requests
    from bs4 import BeautifulSoup
    WEB_SCRAPING_AVAILABLE = True
except ImportError:
    WEB_SCRAPING_AVAILABLE = False

try:
    import PyPDF2
    import pdfplumber
    PDF_TEXT_AVAILABLE = True
except ImportError:
    PDF_TEXT_AVAILABLE = False

@dataclass
class DataSource:
    """Represents a data source for AI extraction"""
    name: str
    source_type: str  # 'file', 'text', 'url', 'image'
    content: str
    extracted_data: Dict[str, Any] = None
    confidence_scores: Dict[str, float] = None

    def __post_init__(self):
        if self.extracted_data is None:
            self.extracted_data = {}
        if self.confidence_scores is None:
            self.confidence_scores = {}

class AIDataExtractor(QThread):
    """
    Thread for AI-powered data extraction from various sources.
    This version is ENHANCED to use the advanced llm_client.py for multi-document processing.
    """
    data_extracted = pyqtSignal(dict, dict)  # extracted_data, confidence_scores
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int, str)  # progress, status_message
    show_message = pyqtSignal(str, str)  # title, message for safe UI thread display

    def __init__(self, sources: List[DataSource], form_fields: List[FormField],
                 ai_provider: str = "openai", api_key: str = "", model: str = "",
                 mapping_pdf_path: str = None, fieldname_to_number_map: Dict = None):
        super().__init__()
        self.sources = sources
        self.form_fields = form_fields
        self.ai_provider = ai_provider
        self.api_key = api_key
        self.model = model
        # Store the path to the target form for context
        self.target_form_path = "" # This should be set from the main window
        
        # Add the missing attributes
        self.mapping_pdf_path = mapping_pdf_path
        self.fieldname_to_number_map = fieldname_to_number_map or {}
        
    def run(self):
        try:
            logger.info(f"AIDataExtractor v4.2: Starting extraction with {self.ai_provider}")
            self.progress_updated.emit(10, f"Initializing AI extraction with {self.ai_provider}...")
            
            extracted_data = {}
            confidence_scores = {}
            
            # --- Key Change: Prepare file paths for the llm_client ---
            pdf_file_paths = []
            source_text_content = ""
            for i, source in enumerate(self.sources):
                progress = 20 + (i * 30 // len(self.sources))
                self.progress_updated.emit(progress, f"Preparing source: {source.name}...")
                
                # We primarily want to pass PDF file paths directly to the new client
                if source.source_type == 'file' and source.content.lower().endswith('.pdf'):
                    pdf_file_paths.append(source.content)
                    logger.info(f"Added PDF source for direct processing: {source.content}")
                else:
                    # For non-PDF sources, extract text as before
                    if source.source_type == "file": text = self._extract_from_file(source.content)
                    elif source.source_type == "image": text = self._extract_from_image(source.content)
                    elif source.source_type == "url": text = self._extract_from_url(source.content)
                    else: text = source.content
                    source_text_content += f"\n--- Start of Content from {source.name} ---\n{text}\n--- End of Content ---\n"

            if not self.target_form_path:
                logger.warning("No target form path set. AI extraction may be less accurate.")
                
            if len(pdf_file_paths) > 0:
                logger.info(f"Processing {len(pdf_file_paths)} PDF sources directly")
            else:
                logger.warning("No PDF sources found. AI extraction may be less accurate.")

            self.progress_updated.emit(60, f"Running AI analysis on {len(pdf_file_paths)} PDFs and additional text...")

            if self.ai_provider == "openai" and OPENAI_AVAILABLE:
                logger.info("Dispatching to llm_client for OpenAI multi-PDF processing")
                extracted_data, confidence_scores = self._extract_with_openai_multi_doc(pdf_file_paths, source_text_content)
            
            elif self.ai_provider == "anthropic" and ANTHROPIC_AVAILABLE:
                logger.info("Dispatching to llm_client for Anthropic multi-PDF processing")
                extracted_data, confidence_scores = self._extract_with_anthropic_multi_doc(pdf_file_paths, source_text_content)
            
            else: # Fallback to pattern matching
                logger.info("Falling back to pattern matching")
                extracted_data, confidence_scores = self._extract_with_patterns(source_text_content)
            
            logger.info(f"Extraction complete. Found {len(extracted_data)} fields.")
            self.progress_updated.emit(100, "AI extraction complete!")
            self.data_extracted.emit(extracted_data, confidence_scores)

        except Exception as e:
            error_msg = f"AI extraction error in AIDataExtractor: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)

    def _build_universal_prompt(self, additional_text_context: str) -> str:
        """Builds the prompt for the AI based on the target form's fields."""
        
        # Get the field names from the loaded PDF form
        field_names = [f.name for f in self.form_fields]
        target_form_name = os.path.basename(self.target_form_path) if self.target_form_path else "the target PDF"

        prompt = f"""
You are an expert AI data extraction agent for a universal PDF form filling system. Your task is to extract information from multiple source documents to fill a target PDF form.

**Target Form:** `{target_form_name}`
**Source Documents:** You will be provided with {len(self.sources)} source documents. These may include case information, financial schedules, or other data.

**CRITICAL INSTRUCTIONS:**
1.  **ANALYZE ALL SOURCES:** You MUST comprehensively analyze ALL source documents provided. Do not stop after finding information in the first document.
2.  **EXTRACT FOR TARGET FIELDS:** Your goal is to find the correct values for the following fields in the target form. Extract the actual data (e.g., "$22,000.00", "Mark Piesner"), not the field labels.
3.  **INTELLIGENT MERGING:** If different documents contain data for the same concept (e.g., an address), select the most complete and relevant one for the target field.
4.  **BE PRECISE:** Extract data exactly as it appears. For addresses, decide if it's better to extract the full block or individual components based on the target fields provided.
5.  **HANDLE FINANCIALS AND ATTORNEY INFO:** Pay special attention to financial data (like from an FL-142) and attorney/case information (like from an FL-120 or Case Information Statement).

**TARGET FIELDS TO EXTRACT:**
```json
{json.dumps(field_names, indent=2)}
```

**FIELD TO NUMBER REFERENCE MAP:**
This JSON object shows you the valid field numbers you can use as keys in your output.
```json
{json.dumps(self.fieldname_to_number_map, indent=2)}
```

ADDITIONAL TEXT CONTEXT (from non-PDF sources):
{additional_text_context[:8000]}

OUTPUT FORMAT:
Return a single, clean JSON object containing the extracted data and confidence scores. Do not include any other text or explanations.

{{
"extracted_data": {{
"field_name_or_number": "The Extracted Value",
"another_field": "another value"
}},
"confidence_scores": {{
"field_name_or_number": 0.95,
"another_field": 0.88
}}
}}
"""
        logger.debug(f"Generated AI prompt with {len(field_names)} target fields")
        return prompt
    
    def _extract_with_anthropic_multi_doc(self, pdf_paths: List[str], text_context: str) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Extract data using the enhanced llm_client with Anthropic."""
        if not self.api_key:
            raise ValueError("Anthropic API key required.")
        
        os.environ["ANTHROPIC_API_KEY"] = self.api_key.strip()
        
        prompt = self._build_universal_prompt(text_context)
        model = self.model or "claude-3-5-sonnet-20240620"
        logger.info(f"Calling llm_client.generate_with_multiple_pdfs_claude with {len(pdf_paths)} PDFs and model {model}")

        # Use the powerful multi-PDF function from your llm_client
        response_text = llm_client.generate_with_multiple_pdfs_claude(
            model=model,
            prompt=prompt,
            pdf_files=pdf_paths,
            mapping_pdf_path=self.mapping_pdf_path # Pass the map
        )
        
        logger.debug(f"Received response from Claude: {len(response_text)} characters")
        return self._parse_ai_response(response_text)

    def _extract_with_openai_multi_doc(self, pdf_paths: List[str], text_context: str) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Extract data using the enhanced llm_client with OpenAI."""
        if not self.api_key:
            raise ValueError("OpenAI API key required.")

        os.environ["OPENAI_API_KEY"] = self.api_key.strip()

        prompt = self._build_universal_prompt(text_context)
        model = self.model or "gpt-4o"
        logger.info(f"Calling llm_client.generate_with_multiple_pdfs_openai with {len(pdf_paths)} PDFs and model {model}")

        # Use the powerful multi-PDF function from your llm_client
        response_text = llm_client.generate_with_multiple_pdfs_openai(
            model=model,
            prompt=prompt,
            pdf_files=pdf_paths,
            mapping_pdf_path=self.mapping_pdf_path # Pass the map
        )
        
        logger.debug(f"Received response from OpenAI: {len(response_text)} characters")
        return self._parse_ai_response(response_text)
        
    def _parse_ai_response(self, response_text: str) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Parses the JSON object from the AI's response with enhanced error handling and diagnostics."""
        try:
            # First, log some info about the response text for debugging
            logger.info(f"Processing AI response of length: {len(response_text)} characters")
            logger.debug(f"Response begins with: {response_text[:100]}...")
            
            # Find the JSON block in the response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start == -1 or end == 0:
                logger.error("No JSON object found in AI response.")
                logger.debug(f"Response text (truncated): {response_text[:500]}...")
                
                # Additional diagnostics for when JSON is not found
                if "{" in response_text:
                    logger.debug("Found { character but couldn't extract valid JSON. Attempting to find smaller JSON blocks...")
                    # Look for smaller complete JSON blocks
                    match = re.search(r'(\{[^{]*"extracted_data"[^}]*\})', response_text)
                    if match:
                        logger.info("Found potential partial JSON with extracted_data key")
                        json_text = match.group(1)
                        try:
                            # Try to fix common JSON issues
                            fixed_json = json_text.replace("'", '"').replace("\\", "\\\\")
                            result = json.loads(fixed_json)
                            logger.info("Successfully parsed partial JSON block after fixes")
                            extracted_data = result.get("extracted_data", {})
                            confidence_scores = {k: 0.7 for k in extracted_data.keys()}  # Lower confidence due to repairs
                            return extracted_data, confidence_scores
                        except json.JSONDecodeError:
                            logger.debug("Attempted fix of partial JSON failed")
                
                return {}, {}

            json_text = response_text[start:end]
            
            # Check for common JSON issues before parsing
            if json_text.count('{') != json_text.count('}'):
                logger.warning(f"Unbalanced braces in JSON: {json_text.count('{')} opening vs {json_text.count('}')} closing")
            
            # Try to parse the JSON
            result = json.loads(json_text)
            
            # Process the result
            extracted_data = result.get("extracted_data", {})
            confidence_scores = result.get("confidence_scores", {})
            
            # If confidence scores are missing, create default ones.
            if extracted_data and not confidence_scores:
                logger.warning("No confidence scores provided by AI. Creating default values.")
                confidence_scores = {k: 0.9 for k in extracted_data.keys()}
            
            # Log successful extraction with detailed field information
            logger.info(f"Successfully parsed JSON with {len(extracted_data)} fields.")
            
            # Log the top 5 most confident fields
            if confidence_scores:
                top_fields = sorted(confidence_scores.items(), key=lambda x: x[1], reverse=True)[:5]
                logger.info(f"Top confident fields: {top_fields}")
            
            # Log field names for debugging
            logger.debug(f"Extracted fields: {list(extracted_data.keys())[:10]}{'...' if len(extracted_data) > 10 else ''}")
            
            # Validate number of fields vs form fields
            if len(extracted_data) < len(self.form_fields) * 0.2:  # Less than 20% of fields filled
                logger.warning(f"Only extracted {len(extracted_data)} fields out of {len(self.form_fields)} form fields ({len(extracted_data)/len(self.form_fields):.1%})")
            else:
                logger.info(f"Extracted {len(extracted_data)}/{len(self.form_fields)} fields ({len(extracted_data)/len(self.form_fields):.1%})")
            
            return extracted_data, confidence_scores

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from AI response: {e}")
            logger.debug(f"Failed JSON text (truncated): {response_text[:500]}...")
            
            # For debugging, save the failed response to a file
            try:
                debug_file = "ai_response_debug.txt"
                with open(debug_file, "w") as f:
                    f.write(response_text)
                logger.info(f"Saved problematic AI response to {debug_file} for debugging")
            except Exception as write_err:
                logger.error(f"Could not save debug file: {write_err}")
                
            self.show_message.emit("JSON Parsing Error", f"The AI returned a response that could not be parsed correctly. See logs for details.")
            return {}, {}
        except Exception as e:
            logger.error(f"An unexpected error occurred while parsing AI response: {e}", exc_info=True)
            return {}, {}

    # Keep the old _extract_from_file, _extract_with_patterns, etc. methods here
    # as they are still used for non-PDF files and as fallbacks.
    # (The following methods are unchanged from your original file)

    def _extract_from_file(self, file_path: str) -> str:
        """Extract text from various file types - RESTORED WORKING VERSION"""
        print(f"DEBUG: Extracting text from file: {file_path}")
        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.txt', '.md', '.csv']:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                    return file.read()
            elif ext == '.json':
                with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                    return json.dumps(json.load(file), indent=2)
            else:
                # For PDFs or other types, extract text if possible
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as pdf_file:
                        reader = PyPDF2.PdfReader(pdf_file)
                        return "\n".join(page.extract_text() for page in reader.pages)
                except Exception:
                    return f"[Unsupported file type: {ext}]"
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return f"[Error reading file: {str(e)}]"

    def _extract_from_image(self, image_path: str) -> str:
        if not OCR_AVAILABLE: return "OCR not available."
        try: return pytesseract.image_to_string(Image.open(image_path))
        except Exception as e: return f"OCR error: {str(e)}"

    def _extract_from_url(self, url: str) -> str:
        if not WEB_SCRAPING_AVAILABLE: return "Web scraping not available."
        try:
            soup = BeautifulSoup(requests.get(url, timeout=30).content, 'html.parser')
            for script in soup(["script", "style"]): script.decompose()
            text = ' '.join(t.strip() for t in soup.get_text().split() if t.strip())
            return text
        except Exception as e: return f"Web scraping error: {str(e)}"

    def _extract_with_patterns(self, text: str) -> Tuple[Dict[str, str], Dict[str, float]]:
        print("🔍 Using pattern matching extraction")
        extracted_data = {}
        confidence_scores = {}
        patterns = {
            'attorney_name': r'attorney.*?([A-Z][a-z]+ [A-Z][a-z]+)', 'petitioner_name': r'petitioner.*?([A-Z][a-z]+ [A-Z][a-z]+)',
            'respondent_name': r'respondent.*?([A-Z][a-z]+ [A-Z][a-z]+)', 'case_number': r'case.*?number.*?([A-Z0-9]+)',
            'court_county': r'county of\s+([A-Z\s]+)', 'student_loan': r'student.*?loan.*?\$?\s*([0-9,]+\.?[0-9]*)',
            'credit_card': r'credit.*?card.*?\$?\s*([0-9,]+\.?[0-9]*)', 'total_debt': r'total.*?debt.*?\$?\s*([0-9,]+\.?[0-9]*)',
            'phone': r'\((\d{3})\)\s*(\d{3})-(\d{4})', 'address': r'(\d+\s+[A-Za-z\s]+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr))',
        }
        for field in self.form_fields:
            field_text = (field.name + " " + (field.alt_text or "")).lower()
            for pattern_type, pattern in patterns.items():
                if any(word in field_text for word in pattern_type.split('_')):
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        value = f"({match.group(1)}) {match.group(2)}-{match.group(3)}" if pattern_type == 'phone' else match.group(1).strip()
                        extracted_data[field.name] = value
                        confidence_scores[field.name] = 0.80
                        break
        return extracted_data, confidence_scores



class PDFFieldExtractor(QThread):
    """Thread for extracting PDF fields using pdftk"""
    fields_extracted = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)

    def __init__(self, pdf_path: str):
        super().__init__()
        self.pdf_path = pdf_path

    def run(self):
        try:
            self.progress_updated.emit(20)
            
            # Check if pdftk is available
            try:
                subprocess.run(['pdftk', '--version'], 
                              capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.error_occurred.emit(
                    "pdftk not found. Please install pdftk:\n"
                    "macOS: brew install pdftk-java\n"
                    "Ubuntu: sudo apt install pdftk\n"
                    "Windows: Download from pdftk.org"
                )
                return

            self.progress_updated.emit(50)

            # Extract fields using pdftk
            result = subprocess.run([
                'pdftk', self.pdf_path, 'dump_data_fields'
            ], capture_output=True, text=True, check=True)

            self.progress_updated.emit(80)

            # Parse the output
            fields = self._parse_pdftk_output(result.stdout)
            
            self.progress_updated.emit(100)
            self.fields_extracted.emit(fields)

        except subprocess.CalledProcessError as e:
            self.error_occurred.emit(f"Error extracting fields: {e}")
        except Exception as e:
            self.error_occurred.emit(f"Unexpected error: {str(e)}")

    def _parse_pdftk_output(self, output: str) -> List[FormField]:
        """Parse pdftk dump_data_fields output"""
        fields = []
        current_field = {}
        
        for line in output.strip().split('\n'):
            if line.startswith('---'):
                if current_field:
                    field = FormField(
                        name=current_field.get('FieldName', ''),
                        field_type=current_field.get('FieldType', 'Text'),
                        alt_text=current_field.get('FieldNameAlt', ''),
                        flags=int(current_field.get('FieldFlags', 0)),
                        justification=current_field.get('FieldJustification', 'Left'),
                        state_options=current_field.get('FieldStateOption', [])
                    )
                    fields.append(field)
                current_field = {}
            elif ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if key == 'FieldStateOption':
                    if key not in current_field:
                        current_field[key] = []
                    current_field[key].append(value)
                else:
                    current_field[key] = value

        # Add the last field
        if current_field:
            field = FormField(
                name=current_field.get('FieldName', ''),
                field_type=current_field.get('FieldType', 'Text'),
                alt_text=current_field.get('FieldNameAlt', ''),
                flags=int(current_field.get('FieldFlags', 0)),
                justification=current_field.get('FieldJustification', 'Left'),
                state_options=current_field.get('FieldStateOption', [])
            )
            fields.append(field)

        return fields

class PDFFormFiller(QThread):
    """Thread for filling PDF forms"""
    form_filled = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)

    def __init__(self, pdf_path: str, field_data: Dict[str, str], output_path: str):
        super().__init__()
        self.pdf_path = pdf_path
        self.field_data = field_data
        self.output_path = output_path

    def run(self):
        try:
            self.progress_updated.emit(20)

            # Create FDF file
            fdf_content = self._create_fdf(self.field_data)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.fdf', delete=False) as fdf_file:
                fdf_file.write(fdf_content)
                fdf_path = fdf_file.name

            self.progress_updated.emit(50)

            try:
                # Fill the form using pdftk
                subprocess.run([
                    'pdftk', self.pdf_path, 'fill_form', fdf_path,
                    'output', self.output_path
                ], check=True)

                self.progress_updated.emit(100)
                self.form_filled.emit(self.output_path)

            finally:
                # Clean up temporary FDF file
                os.unlink(fdf_path)

        except Exception as e:
            self.error_occurred.emit(f"Error filling form: {str(e)}")

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

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.current_pdf_path = ""
        self.settings = QSettings("PDFFormFiller", "FormMappings")
        self.form_fields = []
        self.ai_data_sources = []
        self.paths_history = {}  # Store recently used file paths
        self.load_paths_history()  # Load previously saved paths
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        self.setWindowTitle("PDF Form Filler - Universal Fillable PDF Tool")
        self.setGeometry(100, 100, 1200, 800)

        # Central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("PDF File:"))
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        file_layout.addWidget(self.file_path_edit)
        
        self.browse_btn = QPushButton("Browse PDF")
        self.browse_btn.clicked.connect(self.browse_pdf)
        file_layout.addWidget(self.browse_btn)
        
        layout.addLayout(file_layout)
        
        # Recent PDFs dropdown
        recent_files_layout = QHBoxLayout()
        recent_files_layout.addWidget(QLabel("Recent PDFs:"))
        self.recent_pdfs_combo = QComboBox()
        self.recent_pdfs_combo.setMinimumWidth(300)
        self.populate_recent_pdfs_combo()
        self.recent_pdfs_combo.currentIndexChanged.connect(self.load_selected_pdf)
        recent_files_layout.addWidget(self.recent_pdfs_combo)
        
        # Save/Load paths buttons
        self.save_paths_btn = QPushButton("Save Current Paths")
        self.save_paths_btn.clicked.connect(self.save_paths_history)
        recent_files_layout.addWidget(self.save_paths_btn)
        
        layout.addLayout(recent_files_layout)
        
        # Mapping PDF layout
        mapping_file_layout = QHBoxLayout()
        mapping_file_layout.addWidget(QLabel("Numbered Map PDF:"))
        self.mapping_pdf_path_edit = QLineEdit()
        self.mapping_pdf_path_edit.setReadOnly(True)
        self.mapping_pdf_path_edit.setPlaceholderText("Optional: Select a PDF where fields are numbered")
        mapping_file_layout.addWidget(self.mapping_pdf_path_edit)

        self.browse_mapping_pdf_btn = QPushButton("Browse Map")
        self.browse_mapping_pdf_btn.clicked.connect(self.browse_mapping_pdf)
        mapping_file_layout.addWidget(self.browse_mapping_pdf_btn)
        
        # Recent mapping PDFs dropdown
        self.recent_maps_combo = QComboBox()
        self.recent_maps_combo.setMinimumWidth(150)
        self.populate_recent_maps_combo()
        self.recent_maps_combo.currentIndexChanged.connect(self.load_selected_map)
        mapping_file_layout.addWidget(self.recent_maps_combo)

        layout.addLayout(mapping_file_layout)
        # --- END OF ADDITION ---
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Field mapping tab
        self.field_mapping_widget = FieldMappingWidget()
        self.tab_widget.addTab(self.field_mapping_widget, "Field Mapping")

        # AI extraction tab
        self.create_ai_extraction_tab()

        # Data management tab
        self.create_data_management_tab()

        # Action buttons
        button_layout = QHBoxLayout()
        
        self.load_data_btn = QPushButton("Load Mapping")
        self.load_data_btn.clicked.connect(self.load_mapping)
        button_layout.addWidget(self.load_data_btn)
        
        self.save_data_btn = QPushButton("Save Mapping")
        self.save_data_btn.clicked.connect(self.save_mapping)
        button_layout.addWidget(self.save_data_btn)
        
        button_layout.addStretch()
        
        self.fill_form_btn = QPushButton("Fill PDF Form")
        self.fill_form_btn.clicked.connect(self.fill_form)
        self.fill_form_btn.setEnabled(False)
        button_layout.addWidget(self.fill_form_btn)
        
        layout.addLayout(button_layout)

        # Status
        self.status_label = QLabel("Ready - Select a PDF file to begin")
        layout.addWidget(self.status_label)

    def browse_mapping_pdf(self):
        """Browse for the numbered mapping PDF file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Numbered Mapping PDF", "", "PDF Files (*.pdf)"
        )
        if file_path:
            self.mapping_pdf_path_edit.setText(file_path)
            self.status_label.setText("Numbered mapping PDF loaded.")
            
            # Add to recent maps
            if file_path not in self.paths_history.get("recent_maps", []):
                if "recent_maps" not in self.paths_history:
                    self.paths_history["recent_maps"] = []
                self.paths_history["recent_maps"].insert(0, file_path)
                self.paths_history["recent_maps"] = self.paths_history["recent_maps"][:10]
                self.populate_recent_maps_combo()
    
    def create_ai_extraction_tab(self):
        """Create AI extraction tab with improved error handling"""
        ai_tab = QWidget()
        ai_layout = QVBoxLayout(ai_tab)
        
        # AI Provider Selection
        provider_group = QGroupBox("AI Provider")
        provider_layout = QVBoxLayout()
        
        self.ai_provider_radio_pattern = QRadioButton("Pattern Matching (Free, No API Key Required)")
        self.ai_provider_radio_pattern.setChecked(True)
        provider_layout.addWidget(self.ai_provider_radio_pattern)
        
        self.ai_provider_radio_openai = QRadioButton("OpenAI (API Key Required)")
        provider_layout.addWidget(self.ai_provider_radio_openai)
        
        self.ai_provider_radio_anthropic = QRadioButton("Anthropic Claude (API Key Required)")
        provider_layout.addWidget(self.ai_provider_radio_anthropic)
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.ai_model_combo = QComboBox()
        self.ai_model_combo.addItems(["Default Model"])
        model_layout.addWidget(self.ai_model_combo)
        provider_layout.addLayout(model_layout)
        
        # API Key field
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("API Key:"))
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Enter API key (only needed for OpenAI/Claude)")
        key_layout.addWidget(self.api_key_edit)
        provider_layout.addLayout(key_layout)
        
        # Connect radio buttons to update model list
        self.ai_provider_radio_pattern.toggled.connect(self._update_ai_model_list)
        self.ai_provider_radio_openai.toggled.connect(self._update_ai_model_list)
        self.ai_provider_radio_anthropic.toggled.connect(self._update_ai_model_list)
        
        provider_group.setLayout(provider_layout)
        ai_layout.addWidget(provider_group)
        
        # Data Sources
        sources_group = QGroupBox("Data Sources")
        sources_layout = QVBoxLayout()
        
        # Source management buttons
        source_buttons = QHBoxLayout()
        
        self.add_file_btn = QPushButton("Add File")
        self.add_file_btn.clicked.connect(self.add_ai_file_source)
        source_buttons.addWidget(self.add_file_btn)
        
        # Recent data sources button
        self.load_recent_sources_btn = QPushButton("Load Recent Sources")
        self.load_recent_sources_btn.clicked.connect(self.show_recent_data_sources)
        source_buttons.addWidget(self.load_recent_sources_btn)
        
        self.add_text_btn = QPushButton("Add Text")
        self.add_text_btn.clicked.connect(self.add_ai_text_source)
        source_buttons.addWidget(self.add_text_btn)
        
        self.add_url_btn = QPushButton("Add URL")
        self.add_url_btn.clicked.connect(self.add_ai_url_source)
        source_buttons.addWidget(self.add_url_btn)
        
        self.add_image_btn = QPushButton("Add Image (OCR)")
        self.add_image_btn.clicked.connect(self.add_ai_image_source)
        source_buttons.addWidget(self.add_image_btn)
        
        source_buttons.addStretch()
        
        self.clear_sources_btn = QPushButton("Clear All")
        self.clear_sources_btn.clicked.connect(self.clear_ai_sources)
        source_buttons.addWidget(self.clear_sources_btn)
        
        sources_layout.addLayout(source_buttons)
        
        # Sources list
        self.sources_list = QListWidget()
        self.sources_list.setMaximumHeight(150)
        sources_layout.addWidget(self.sources_list)
        
        sources_group.setLayout(sources_layout)
        ai_layout.addWidget(sources_group)
        
        # Text Input
        text_group = QGroupBox("Direct Text Input")
        text_layout = QVBoxLayout()
        
        self.ai_text_input = QPlainTextEdit()
        self.ai_text_input.setPlaceholderText(
            "Paste any text here for AI analysis:\n"
            "- Court documents\n"
            "- Case information\n"
            "- Client details\n"
            "- Financial data\n"
            "- Any relevant information"
        )
        self.ai_text_input.setMaximumHeight(150)
        text_layout.addWidget(self.ai_text_input)
        
        text_group.setLayout(text_layout)
        ai_layout.addWidget(text_group)
        
        # Extract Button
        extract_layout = QHBoxLayout()
        
        self.ai_extract_btn = QPushButton("Extract Data")
        self.ai_extract_btn.clicked.connect(self.extract_with_ai)
        extract_layout.addWidget(self.ai_extract_btn)
        
        self.ai_progress = QProgressBar()
        self.ai_progress.setVisible(False)
        extract_layout.addWidget(self.ai_progress)
        
        ai_layout.addLayout(extract_layout)
        
        # Results
        results_group = QGroupBox("Extraction Results")
        results_layout = QVBoxLayout()
        
        self.ai_results = QTextEdit()
        self.ai_results.setReadOnly(True)
        self.ai_results.setPlaceholderText("Results will appear here...")
        results_layout.addWidget(self.ai_results)
        
        results_group.setLayout(results_layout)
        ai_layout.addWidget(results_group)
        
        # Add to tabs
        self.tab_widget.addTab(ai_tab, "AI Data Extraction")

    def create_data_management_tab(self):
        """Create the data management tab"""
        data_widget = QWidget()
        layout = QVBoxLayout()
        
        # Quick data entry
        group = QGroupBox("Quick Data Entry (JSON)")
        group_layout = QVBoxLayout()
        
        self.data_text_edit = QTextEdit()
        self.data_text_edit.setPlaceholderText(
            'Enter field data as JSON:\n'
            '{\n'
            '  "field_name_1": "value1",\n'
            '  "field_name_2": "value2"\n'
            '}'
        )
        group_layout.addWidget(self.data_text_edit)
        
        json_buttons = QHBoxLayout()
        
        apply_json_btn = QPushButton("Apply JSON Data")
        apply_json_btn.clicked.connect(self.apply_json_data)
        json_buttons.addWidget(apply_json_btn)
        
        export_json_btn = QPushButton("Export to JSON")
        export_json_btn.clicked.connect(self.export_to_json)
        json_buttons.addWidget(export_json_btn)
        
        group_layout.addLayout(json_buttons)
        group.setLayout(group_layout)
        layout.addWidget(group)
        
        data_widget.setLayout(layout)
        self.tab_widget.addTab(data_widget, "Data Management")

    def apply_theme(self):
        """Apply a modern theme to the application"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin: 10px 0px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 6px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #2196F3;
                color: white;
            }
        """)

    def browse_pdf(self):
        """Browse for PDF file"""
        print("DEBUG: Browse PDF button clicked")
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF File", "", "PDF Files (*.pdf)"
        )
        
        if file_path:
            print(f"DEBUG: Selected PDF: {file_path}")
            self.current_pdf_path = file_path
            self.file_path_edit.setText(file_path)
            
            # Add to recent PDFs
            if file_path not in self.paths_history.get("recent_pdfs", []):
                if "recent_pdfs" not in self.paths_history:
                    self.paths_history["recent_pdfs"] = []
                self.paths_history["recent_pdfs"].insert(0, file_path)
                self.paths_history["recent_pdfs"] = self.paths_history["recent_pdfs"][:10]
                self.populate_recent_pdfs_combo()
                
            self.extract_fields()
        else:
            print("DEBUG: No PDF file selected")

    def extract_fields(self):
        """Extract fields from the selected PDF"""
        if not self.current_pdf_path:
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Extracting form fields...")
        
        self.extractor_thread = PDFFieldExtractor(self.current_pdf_path)
        self.extractor_thread.fields_extracted.connect(self.on_fields_extracted)
        self.extractor_thread.error_occurred.connect(self.on_extraction_error)
        self.extractor_thread.progress_updated.connect(self.progress_bar.setValue)
        self.extractor_thread.start()

    def on_fields_extracted(self, fields: List[FormField]):
        """Handle successful field extraction and create number maps."""
        self.progress_bar.setVisible(False)
        self.field_mapping_widget.set_fields(fields)
        self.form_fields = fields

        # --- ADD THIS LOGIC to create the maps ---
        self.fieldname_to_number_map = {field.name: i + 1 for i, field in enumerate(self.form_fields)}
        self.number_to_fieldname_map = {i + 1: field.name for i, field in enumerate(self.form_fields)}
        logger.info(f"Created number map for {len(fields)} fields.")
        self.fill_form_btn.setEnabled(True)
        self.status_label.setText(f"Ready - Found {len(fields)} form fields")

    def on_extraction_error(self, error_message: str):
        """Handle field extraction error"""
        self.progress_bar.setVisible(False)
        self.status_label.setText("Error extracting fields")
        QMessageBox.critical(self, "Error", error_message)

    # AI Data Source Management Methods
    def add_ai_file_source(self):
        """Add a file as data source for AI analysis"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Data File", "",
                "All Supported (*.pdf *.txt *.json *.csv *.md);;PDF Files (*.pdf);;Text Files (*.txt);;JSON Files (*.json);;CSV Files (*.csv)"
            )
            
            if file_path:
                file_name = os.path.basename(file_path)
                self.sources_list.addItem(f"File: {file_name}")
                self.ai_data_sources.append(('file', str(file_path)))
                print(f"Added file source: {file_name}")
                
                # Add to recent data sources if it's a file
                data_source = {"type": "file", "path": file_path}
                if "recent_data_sources" not in self.paths_history:
                    self.paths_history["recent_data_sources"] = []
                
                # Check if already exists
                exists = False
                for ds in self.paths_history["recent_data_sources"]:
                    if ds.get("path") == file_path:
                        exists = True
                        break
                
                if not exists:
                    self.paths_history["recent_data_sources"].insert(0, data_source)
                    self.paths_history["recent_data_sources"] = self.paths_history["recent_data_sources"][:20]
                
        except Exception as e:
            print(f"Error adding file source: {e}")
            QMessageBox.warning(self, "Error", f"Error adding file: {str(e)}")
    
    def add_ai_text_source(self):
        """Add text input as data source for AI analysis"""
        try:
            text = self.ai_text_input.toPlainText().strip()
            if text:
                self.sources_list.addItem(f"Text: {len(text)} chars")
                
                # Truncate very long text to avoid memory issues
                max_len = 5000
                if len(text) > max_len:
                    truncated = text[:max_len] + "... (truncated)"
                    self.ai_data_sources.append(('text', truncated))
                else:
                    self.ai_data_sources.append(('text', text))
                    
                self.ai_text_input.clear()
                print("Added text source")
        except Exception as e:
            print(f"Error adding text source: {e}")
    
    def add_ai_url_source(self):
        """Add URL as data source for AI analysis"""
        try:
            url, ok = QInputDialog.getText(
                self, "Add URL Source",
                "Enter URL to scrape for data:",
                QLineEdit.EchoMode.Normal,
                "https://"
            )
            
            if ok and url:
                display_url = url[:50] + "..." if len(url) > 50 else url
                self.sources_list.addItem(f"URL: {display_url}")
                self.ai_data_sources.append(('url', url))
                print(f"Added URL source: {url}")
        except Exception as e:
            print(f"Error adding URL source: {e}")
    
    def add_ai_image_source(self):
        """Add image for OCR as data source for AI analysis"""
        try:
            if not OCR_AVAILABLE:
                QMessageBox.warning(
                    self, "OCR Not Available",
                    "OCR functionality requires pytesseract and Pillow.\n"
                    "Install with: pip install pytesseract Pillow"
                )
                return
            
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Image File", "",
                "Image Files (*.png *.jpg *.jpeg *.tiff *.bmp *.gif)"
            )
            
            if file_path:
                file_name = os.path.basename(file_path)
                self.sources_list.addItem(f"Image: {file_name}")
                self.ai_data_sources.append(('image', str(file_path)))
                print(f"Added image source: {file_name}")
        except Exception as e:
            print(f"Error adding image source: {e}")

    def clear_ai_sources(self):
        """Clear all AI data sources"""
        try:
            self.sources_list.clear()
            self.ai_data_sources = []
            print("AI sources cleared")
        except Exception as e:
            print(f"Error clearing sources: {e}")

    def _update_ai_model_list(self):
        """Update the model list based on selected provider"""
        try:
            self.ai_model_combo.clear()
            
            if self.ai_provider_radio_openai.isChecked():
                openai_models = [
                    "gpt-4o",
                    "gpt-4-turbo",
                    "gpt-4",
                    "gpt-3.5-turbo"
                ]
                self.ai_model_combo.addItems(openai_models)
                
            elif self.ai_provider_radio_anthropic.isChecked():
                claude_models = [
                    "claude-3-5-sonnet-20240620",
                    "claude-3-opus-20240229",
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307"
                ]
                self.ai_model_combo.addItems(claude_models)
                
            else:
                # Pattern matching has no model selection
                self.ai_model_combo.addItem("Pattern Matching (No Model)")
                
        except Exception as e:
            print(f"Error updating model list: {e}")

    def extract_with_ai(self):
        """Extract data using AI with improved error handling"""
        try:
            # Check if form fields are available
            if not self.form_fields:
                QMessageBox.warning(self, "No Form Fields",
                                   "Please load a PDF form first to define extraction fields.")
                return
                
            # Check if we have any data sources
            has_text = bool(self.ai_text_input.toPlainText().strip())
            has_sources = bool(self.ai_data_sources)
            
            if not has_text and not has_sources:
                QMessageBox.warning(self, "No Input",
                                   "Please enter some text or add data sources to analyze.")
                return
                
            # Determine AI provider
            if self.ai_provider_radio_openai.isChecked():
                provider = "openai"
                if not self.api_key_edit.text().strip():
                    QMessageBox.warning(self, "API Key Required",
                                      "Please enter an OpenAI API key.")
                    return
            elif self.ai_provider_radio_anthropic.isChecked():
                provider = "anthropic"
                if not self.api_key_edit.text().strip():
                    QMessageBox.warning(self, "API Key Required",
                                      "Please enter an Anthropic API key.")
                    return
            else:
                provider = "pattern"
                
            # Show progress
            self.ai_progress.setVisible(True)
            self.ai_progress.setValue(10)
            self.ai_extract_btn.setEnabled(False)
            self.status_label.setText("Extracting data...")
            
            # Create data sources
            sources = []
            
            # Add text input as source
            if has_text:
                text_content = self.ai_text_input.toPlainText().strip()
                sources.append(DataSource("Direct Text Input", "text", text_content))
            
            # Add file/URL/image sources
            for source_type, source_content in self.ai_data_sources:
                source_name = f"{source_type.title()}: {os.path.basename(source_content) if source_type == 'file' else source_content[:50]}"
                sources.append(DataSource(source_name, source_type, source_content))
            
            # Get selected model
            selected_model = self.ai_model_combo.currentText()
            api_key = self.api_key_edit.text().strip()
            mapping_pdf_path = self.mapping_pdf_path_edit.text().strip()

            # Start extraction thread
            self.extractor_thread = AIDataExtractor(
                sources, self.form_fields, provider, api_key, selected_model,
                mapping_pdf_path=mapping_pdf_path,  # Pass the new path
                fieldname_to_number_map=self.fieldname_to_number_map # Pass the map
            )
            
            # CRITICAL: Set the target form path for the AI extraction context
            self.extractor_thread.target_form_path = self.current_pdf_path
            logger.info(f"Setting target form path for AI extraction: {self.current_pdf_path}")
            self.extractor_thread.data_extracted.connect(self.on_ai_data_extracted)
            self.extractor_thread.error_occurred.connect(self.on_ai_extraction_error)
            self.extractor_thread.progress_updated.connect(self.on_ai_progress_updated)
            self.extractor_thread.show_message.connect(self.show_ai_message)
            self.extractor_thread.start()
            
        except Exception as e:
            print(f"Error in extract_with_ai: {e}")
            QMessageBox.critical(self, "Error", f"Error during AI extraction: {str(e)}")
            self.ai_progress.setVisible(False)
            self.ai_extract_btn.setEnabled(True)

    def on_ai_data_extracted(self, extracted_data: dict, confidence_scores: dict):
        """Handle successful AI data extraction with enhanced translation and validation."""
        try:
            logger.info(f"Processing extraction results with {len(extracted_data)} data points")
            
            # --- ENHANCED TRANSLATION LOGIC ---
            translated_data = {}
            unmapped_data = {}
            field_name_data = {}
            number_key_count = 0
            fieldname_key_count = 0
            
            # First pass: identify nested structure in data if present
            has_nested_values = False
            for key, value in extracted_data.items():
                if isinstance(value, dict) and "value" in value:
                    has_nested_values = True
                    break
            
            logger.debug(f"Data structure {'has' if has_nested_values else 'does not have'} nested values")
            
            # Process all data points
            for key, value in extracted_data.items():
                # Handle nested structure from new prompt (data format with debug_description)
                if isinstance(value, dict) and "value" in value:
                    actual_value = value["value"]
                    logger.debug(f"Extracted key '{key}' with nested value: {actual_value}")
                else:
                    actual_value = value
                
                try:
                    # Try to convert key to integer (numbered field)
                    field_number = int(key)
                    number_key_count += 1
                    
                    if field_number in self.number_to_fieldname_map:
                        field_name = self.number_to_fieldname_map[field_number]
                        translated_data[field_name] = actual_value
                        logger.debug(f"Mapped number {field_number} to field '{field_name}'")
                    else:
                        logger.warning(f"Number key {field_number} has no mapping to field name")
                        unmapped_data[key] = actual_value
                except (ValueError, TypeError):
                    # Handle direct field name keys
                    if key in [field.name for field in self.form_fields]:
                        field_name_data[key] = actual_value
                        fieldname_key_count += 1
                        logger.debug(f"Found direct field name match: '{key}'")
                    else:
                        unmapped_data[key] = actual_value
            
            # Log statistics about the extraction
            logger.info(f"Translation stats: {number_key_count} numbered keys, {fieldname_key_count} field name keys, {len(unmapped_data)} unmapped keys")
            
            # Merge in any direct field name matches if we didn't get many numbered matches
            if len(translated_data) < 5 and field_name_data:
                logger.info("Few numbered fields found, merging in direct field name matches")
                translated_data.update(field_name_data)
            
            # If we still have very little data, try to use direct field names from unmapped data
            if len(translated_data) < 5:
                logger.warning("Very few fields mapped. Attempting additional field name matching.")
                
                # Try to match unmapped keys to field names by similarity
                for unmapped_key, unmapped_value in list(unmapped_data.items()):
                    # Skip if it's not a string (could be a number or other type)
                    if not isinstance(unmapped_key, str):
                        continue
                        
                    # Check for partial field name matches
                    for field in self.form_fields:
                        if (unmapped_key.lower() in field.name.lower() or
                            field.name.lower() in unmapped_key.lower()):
                            translated_data[field.name] = unmapped_value
                            unmapped_data.pop(unmapped_key)
                            logger.info(f"Fuzzy matched '{unmapped_key}' to field '{field.name}'")
                            break
            
            # Last resort: if no translated data, use original data
            if not translated_data and extracted_data:
                logger.warning("No data could be mapped to fields. Using original extraction data directly.")
                # Extract simple values directly
                translated_data = {k: v for k, v in extracted_data.items()
                                 if not isinstance(v, dict) or "value" not in v}
                
                # Handle nested value structure if present
                for k, v in extracted_data.items():
                    if isinstance(v, dict) and "value" in v:
                        translated_data[k] = v["value"]
            
            # Apply the translated data to the form fields
            self.field_mapping_widget.set_field_data(translated_data)
            
            # --- ENHANCED RESULTS DISPLAY ---
            # Show results with confidence when available
            result_text = "Extraction Results:\n\n"
            
            # Sort fields by confidence if available
            sorted_fields = []
            for field_name, value in translated_data.items():
                # Find corresponding confidence
                conf = None
                # Try direct field name lookup
                if field_name in confidence_scores:
                    conf = confidence_scores[field_name]
                # Try finding by number
                else:
                    for num, fname in self.number_to_fieldname_map.items():
                        if fname == field_name and str(num) in confidence_scores:
                            conf = confidence_scores[str(num)]
                            break
                
                sorted_fields.append((field_name, value, conf))
            
            # Sort by confidence if available, otherwise alphabetically
            sorted_fields.sort(key=lambda x: (-1 * (x[2] or 0), x[0]))
            
            # Display the results
            for field_name, value, conf in sorted_fields:
                if conf is not None:
                    result_text += f"• {field_name}: {value} (confidence: {conf:.2f})\n"
                else:
                    result_text += f"• {field_name}: {value}\n"

            # Show unmapped results if any
            if unmapped_data:
                result_text += "\n--- Unmapped Data ---\n"
                for key, value in unmapped_data.items():
                    result_text += f"• {key}: {value}\n"

            self.ai_results.setPlainText(result_text)
            
            # Update status message
            fill_rate = len(translated_data) / len(self.form_fields) if self.form_fields else 0
            self.status_label.setText(f"Extracted {len(translated_data)} field values ({fill_rate:.1%} of form fields)")
            
            # Log the extraction success details
            logger.info(f"Successfully extracted and mapped {len(translated_data)} fields with fill rate of {fill_rate:.1%}")
            
            # If we got a good amount of data, show a success message
            if fill_rate >= 0.3:  # At least 30% of fields filled
                self.show_ai_message("Extraction Complete",
                                    f"Successfully extracted {len(translated_data)} fields from your documents!")

        except Exception as e:
            logger.error(f"Error processing AI results: {e}", exc_info=True)
        finally:
            self.ai_progress.setVisible(False)
            self.ai_extract_btn.setEnabled(True)

    def on_ai_extraction_error(self, error_message: str):
        """Handle AI extraction error"""
        self.ai_results.setPlainText(f"Error during extraction: {error_message}")
        self.ai_progress.setVisible(False)
        self.ai_extract_btn.setEnabled(True)
        self.status_label.setText("AI extraction failed")

    def on_ai_progress_updated(self, progress: int, message: str):
        """Handle AI extraction progress updates"""
        self.ai_progress.setValue(progress)
        self.status_label.setText(message)

    def show_ai_message(self, title: str, message: str):
        """Show AI message in a thread-safe way"""
        QMessageBox.information(self, title, message)

    # Data Management Methods
    def apply_json_data(self):
        """Apply JSON data to form fields"""
        try:
            json_text = self.data_text_edit.toPlainText()
            if not json_text.strip():
                return
                
            data = json.loads(json_text)
            self.field_mapping_widget.set_field_data(data)
            self.status_label.setText("JSON data applied successfully")
            
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "Invalid JSON", f"JSON parsing error: {str(e)}")

    def export_to_json(self):
        """Export current field data to JSON"""
        data = self.field_mapping_widget.get_field_data()
        # Filter out empty fields
        filtered_data = {k: v for k, v in data.items() if v.strip()}
        
        json_text = json.dumps(filtered_data, indent=2)
        self.data_text_edit.setPlainText(json_text)

    def save_mapping(self):
        """Save current field mapping"""
        if not self.current_pdf_path:
            QMessageBox.warning(self, "No PDF", "Please select a PDF file first")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Field Mapping", "", "JSON Files (*.json)"
        )
        
        if file_path:
            data = self.field_mapping_widget.get_field_data()
            try:
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
                self.status_label.setText(f"Mapping saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save mapping: {str(e)}")

    def load_mapping(self):
        """Load field mapping from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Field Mapping", "", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                self.field_mapping_widget.set_field_data(data)
                self.status_label.setText(f"Mapping loaded from {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load mapping: {str(e)}")

    def fill_form(self):
        """Fill the PDF form with current data"""
        if not self.current_pdf_path:
            QMessageBox.warning(self, "No PDF", "Please select a PDF file first")
            return

        field_data = self.field_mapping_widget.get_field_data()
        # Filter out empty fields
        field_data = {k: v for k, v in field_data.items() if v.strip()}
        
        if not field_data:
            QMessageBox.warning(self, "No Data", "Please enter some field data first")
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save Filled PDF", "", "PDF Files (*.pdf)"
        )
        
        if output_path:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("Filling PDF form...")
            
            self.filler_thread = PDFFormFiller(
                self.current_pdf_path, field_data, output_path
            )
            self.filler_thread.form_filled.connect(self.on_form_filled)
            self.filler_thread.error_occurred.connect(self.on_fill_error)
            self.filler_thread.progress_updated.connect(self.progress_bar.setValue)
            self.filler_thread.start()

    def on_form_filled(self, output_path: str):
        """Handle successful form filling"""
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Form filled successfully: {output_path}")
        
        reply = QMessageBox.question(
            self, "Success", 
            f"PDF form filled successfully!\n\nSaved to: {output_path}\n\nOpen the file?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            os.system(f'open "{output_path}"' if sys.platform == 'darwin' else f'start "{output_path}"')

    def on_fill_error(self, error_message: str):
        """Handle form filling error"""
        self.progress_bar.setVisible(False)
        self.status_label.setText("Error filling form")
        QMessageBox.critical(self, "Error", error_message)
    
    def show_recent_data_sources(self):
        """Show a dialog with recent data sources to load"""
        try:
            recent_sources = self.paths_history.get("recent_data_sources", [])
            if not recent_sources:
                QMessageBox.information(self, "No Recent Sources", "No recent data sources found.")
                return
            
            # Create a dialog to display recent sources
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Recent Data Sources")
            dialog.setMinimumWidth(500)
            layout = QVBoxLayout(dialog)
            
            # List widget to show sources
            sources_list = QListWidget()
            for i, source in enumerate(recent_sources):
                source_type = source.get("type", "unknown")
                path = source.get("path", "")
                if os.path.exists(path):
                    item_text = f"{os.path.basename(path)} ({source_type})"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.ItemDataRole.UserRole, source)
                    sources_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
                    sources_list.addItem(item)
            
            layout.addWidget(sources_list)
            
            # Add buttons
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            # Show dialog and process result
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Add selected sources
                for item in sources_list.selectedItems():
                    source = item.data(Qt.ItemDataRole.UserRole)
                    if source.get("type") == "file" and os.path.exists(source.get("path")):
                        file_path = source.get("path")
                        file_name = os.path.basename(file_path)
                        self.sources_list.addItem(f"File: {file_name}")
                        self.ai_data_sources.append(('file', str(file_path)))
                        logger.info(f"Added file source from history: {file_name}")
                
                if sources_list.selectedItems():
                    self.status_label.setText(f"Added {len(sources_list.selectedItems())} data sources from history")
        
        except Exception as e:
            logger.error(f"Error showing recent data sources: {e}")
            QMessageBox.warning(self, "Error", f"Could not load recent data sources: {str(e)}")
    
    # Path history management methods
    def load_paths_history(self):
        """Load saved file paths from history"""
        try:
            history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paths_history.json")
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    self.paths_history = json.load(f)
                logger.info(f"Loaded paths history with {len(self.paths_history.get('recent_pdfs', []))} PDFs")
            else:
                # Initialize with empty lists
                self.paths_history = {
                    "recent_pdfs": [],
                    "recent_maps": [],
                    "recent_data_sources": []
                }
        except Exception as e:
            logger.error(f"Error loading paths history: {e}")
            self.paths_history = {
                "recent_pdfs": [],
                "recent_maps": [],
                "recent_data_sources": []
            }
    
    def save_paths_history(self):
        """Save current file paths to history"""
        try:
            # Update current paths in history
            if self.current_pdf_path and os.path.exists(self.current_pdf_path):
                # Add to recent PDFs if not already there
                if self.current_pdf_path not in self.paths_history.get("recent_pdfs", []):
                    if "recent_pdfs" not in self.paths_history:
                        self.paths_history["recent_pdfs"] = []
                    # Add to front of list and limit to 10 entries
                    self.paths_history["recent_pdfs"].insert(0, self.current_pdf_path)
                    self.paths_history["recent_pdfs"] = self.paths_history["recent_pdfs"][:10]
            
            # Add mapping PDF if it exists
            mapping_path = self.mapping_pdf_path_edit.text()
            if mapping_path and os.path.exists(mapping_path):
                if mapping_path not in self.paths_history.get("recent_maps", []):
                    if "recent_maps" not in self.paths_history:
                        self.paths_history["recent_maps"] = []
                    self.paths_history["recent_maps"].insert(0, mapping_path)
                    self.paths_history["recent_maps"] = self.paths_history["recent_maps"][:10]
            
            # Save data sources
            data_sources = []
            for source_type, source_content in self.ai_data_sources:
                if source_type == 'file' and os.path.exists(source_content):
                    data_sources.append({"type": source_type, "path": source_content})
            
            if data_sources:
                self.paths_history["recent_data_sources"] = data_sources
            
            # Write to JSON file
            history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paths_history.json")
            with open(history_file, 'w') as f:
                json.dump(self.paths_history, f, indent=2)
            
            # Update UI
            self.populate_recent_pdfs_combo()
            self.populate_recent_maps_combo()
            
            self.status_label.setText("Saved current paths to history")
            logger.info(f"Saved paths history with {len(self.paths_history.get('recent_pdfs', []))} PDFs")
            
        except Exception as e:
            logger.error(f"Error saving paths history: {e}")
            QMessageBox.warning(self, "Error", f"Could not save paths history: {str(e)}")
    
    def populate_recent_pdfs_combo(self):
        """Populate the recent PDFs combo box"""
        try:
            self.recent_pdfs_combo.clear()
            self.recent_pdfs_combo.addItem("Select a recent PDF...")
            
            for pdf_path in self.paths_history.get("recent_pdfs", []):
                if os.path.exists(pdf_path):
                    # Display only the filename in the dropdown
                    self.recent_pdfs_combo.addItem(os.path.basename(pdf_path), pdf_path)
            
        except Exception as e:
            logger.error(f"Error populating recent PDFs: {e}")
    
    def populate_recent_maps_combo(self):
        """Populate the recent mapping PDFs combo box"""
        try:
            self.recent_maps_combo.clear()
            self.recent_maps_combo.addItem("Select a recent map...")
            
            for map_path in self.paths_history.get("recent_maps", []):
                if os.path.exists(map_path):
                    # Display only the filename in the dropdown
                    self.recent_maps_combo.addItem(os.path.basename(map_path), map_path)
            
        except Exception as e:
            logger.error(f"Error populating recent maps: {e}")
    
    def load_selected_pdf(self, index):
        """Load the selected PDF from the combo box"""
        if index <= 0:  # Skip the "Select a recent PDF..." item
            return
        
        try:
            # Get the full path from the combo box's user data
            pdf_path = self.recent_pdfs_combo.itemData(index)
            if pdf_path and os.path.exists(pdf_path):
                self.current_pdf_path = pdf_path
                self.file_path_edit.setText(pdf_path)
                self.extract_fields()
                logger.info(f"Loaded PDF from history: {pdf_path}")
        except Exception as e:
            logger.error(f"Error loading selected PDF: {e}")
    
    def load_selected_map(self, index):
        """Load the selected mapping PDF from the combo box"""
        if index <= 0:  # Skip the "Select a recent map..." item
            return
        
        try:
            # Get the full path from the combo box's user data
            map_path = self.recent_maps_combo.itemData(index)
            if map_path and os.path.exists(map_path):
                self.mapping_pdf_path_edit.setText(map_path)
                logger.info(f"Loaded mapping PDF from history: {map_path}")
        except Exception as e:
            logger.error(f"Error loading selected mapping PDF: {e}")

def main():
    """Main entry point for PDF Form Filler v3"""
    app = QApplication(sys.argv)
    app.setApplicationName("PDF Form Filler")
    app.setApplicationVersion("3.0")
    
    # Set application icon if available
    try:
        app.setWindowIcon(QIcon("icon.png"))
    except:
        pass
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
