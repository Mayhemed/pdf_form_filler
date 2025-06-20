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
            logger.info(f"AIDataExtractor v4.1: Starting extraction with {self.ai_provider}")
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

            self.progress_updated.emit(60, "Running AI analysis on multiple documents...")

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
        """Builds a prompt that instructs the AI to use the Numbered Map for perfect placement."""

        target_form_name = os.path.basename(self.target_form_path) if self.target_form_path else "the target PDF"

        prompt = f"""
    You are a hyper-accurate AI data mapping agent. Your goal is to extract data from source documents and map it to the correct field number using a provided "Numbered Mapping PDF".

    CRITICAL INSTRUCTIONS:

    USE THE VISUAL MAP: You will be given a "Numbered Mapping PDF" where each fillable field is marked with a number. You MUST refer to this visual map to understand what each number represents.
    OUTPUT FIELD NUMBERS: Your JSON output's keys MUST BE the numbers you see on the mapping PDF.
    ANALYZE ALL SOURCES: Extract the necessary information from all provided source documents (e.g., FL-120, FL-142).
    EXTRACT PRECISE VALUES: Extract only the data that should be filled in (e.g., "TAHIRA FRANCIS", "22000.00"). Do not extract the field labels.
    FIELD TO NUMBER REFERENCE MAP:
    This JSON object shows you the valid field numbers you can use as keys in your output.

    JSON

    {json.dumps(self.fieldname_to_number_map, indent=2)}
    EXAMPLE WORKFLOW:

    You look at the "Numbered Mapping PDF" and see the field for "Petitioner's Name" is labeled with the number 5.
    You analyze the source documents and find the petitioner's name is "TAHIRA FRANCIS".
    In your output JSON, you create the key-value pair: "5": "TAHIRA FRANCIS".
    ADDITIONAL TEXT CONTEXT (from non-PDF sources):
    {additional_text_context[:8000]}

    OUTPUT FORMAT:
    Return a single, clean JSON object. The keys MUST be the numbers from the map.

    {{
    "extracted_data": {{
    "5": "TAHIRA FRANCIS",
    "14": "22000.00"
    }},
    "confidence_scores": {{
    "5": 0.99,
    "14": 0.98
    }}
    }}
    """
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

        return self._parse_ai_response(response_text)
        
    def _parse_ai_response(self, response_text: str) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Parses the JSON object from the AI's response."""
        try:
            # Find the JSON block in the response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start == -1 or end == 0:
                logger.error("No JSON object found in AI response.")
                return {}, {}

            json_text = response_text[start:end]
            result = json.loads(json_text)
            
            extracted_data = result.get("extracted_data", {})
            confidence_scores = result.get("confidence_scores", {})
            
            # If confidence scores are missing, create default ones.
            if extracted_data and not confidence_scores:
                confidence_scores = {k: 0.9 for k in extracted_data.keys()}
            
            logger.info(f"Successfully parsed JSON with {len(extracted_data)} fields.")
            return extracted_data, confidence_scores

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from AI response: {e}\nResponse was:\n{response_text}")
            self.show_message.emit("JSON Parsing Error", f"The AI returned a response that could not be parsed correctly. See logs for details.")
            return {}, {}
        except Exception as e:
            logger.error(f"An unexpected error occurred while parsing AI response: {e}")
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
        # --- ADD THIS NEW LAYOUT for the mapping PDF ---
        mapping_file_layout = QHBoxLayout()
        mapping_file_layout.addWidget(QLabel("Numbered Map PDF:"))
        self.mapping_pdf_path_edit = QLineEdit()
        self.mapping_pdf_path_edit.setReadOnly(True)
        self.mapping_pdf_path_edit.setPlaceholderText("Optional: Select a PDF where fields are numbered")
        mapping_file_layout.addWidget(self.mapping_pdf_path_edit)

        self.browse_mapping_pdf_btn = QPushButton("Browse Map")
        self.browse_mapping_pdf_btn.clicked.connect(self.browse_mapping_pdf)
        mapping_file_layout.addWidget(self.browse_mapping_pdf_btn)

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
            self.extractor_thread.target_form_path = self.current_pdf_path # Let the thread know the target formlayout.addLayout(file_layout)
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

    # In MainWindow, modify on_ai_data_extracted
    def on_ai_data_extracted(self, extracted_data: dict, confidence_scores: dict):
        """Handle successful AI data extraction and translate from numbers to field names."""
        try:
            # --- NEW TRANSLATION LOGIC ---
            translated_data = {}
            unmapped_data = {}
            for number_key, value in extracted_data.items():
                try:
                    # Convert number key (which might be a string) to integer
                    field_number = int(number_key)
                    if field_number in self.number_to_fieldname_map:
                        field_name = self.number_to_fieldname_map[field_number]
                        translated_data[field_name] = value
                    else:
                        unmapped_data[number_key] = value
                except (ValueError, TypeError):
                    # Handle cases where the key is not a number (e.g., a field name)
                    unmapped_data[number_key] = value

            if unmapped_data:
                logger.warning(f"AI returned unmapped keys: {unmapped_data}")

            if not translated_data:
                # If no numbered keys were found, maybe the AI fell back to field names.
                # Let's try to use the original data.
                logger.warning("AI did not return numbered keys. Attempting to use raw data.")
                translated_data = extracted_data

            # Apply the translated data to the form fields
            self.field_mapping_widget.set_field_data(translated_data)
            # --- END OF TRANSLATION LOGIC ---

            # Show results
            result_text = "Extraction Results:\n\n"
            for field_name, value in translated_data.items():
                # We can't easily map confidence scores back, so we'll just show the value
                result_text += f"• {field_name}: {value}\n"

            if unmapped_data:
                result_text += "\n--- Unmapped Results ---\n"
                for key, value in unmapped_data.items():
                    result_text += f"• {key}: {value}\n"

            self.ai_results.setPlainText(result_text)
            self.status_label.setText(f"Extracted {len(translated_data)} field values")

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
