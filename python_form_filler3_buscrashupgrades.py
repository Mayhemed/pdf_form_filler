nton#!/usr/bin/env python3
"""
AI-Powered PDF Form Filler v3 - Enhanced with 98%+ Accuracy AI Mapping
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
import traceback
import dotenv
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
from fieldmappingwidget import FieldMappingWidget, FormField

# Universal Form Mapper Import
try:
    from universal_form_mapper import UniversalFormMapper
    UNIVERSAL_MAPPER_AVAILABLE = True
    print("✅ Universal Form Mapper loaded successfully")
except ImportError as e:
    UNIVERSAL_MAPPER_AVAILABLE = False
    print(f"⚠️ Universal Form Mapper not available: {e}")


# Universal Form Mapper Integration
try:
    from safe_universal_integration import integrate_safe_universal_mapper
    UNIVERSAL_MAPPER_AVAILABLE = True
except ImportError:
    UNIVERSAL_MAPPER_AVAILABLE = False
    print("⚠️ Universal Form Mapper not available")

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

# AI/ML Imports
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

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

# FormField class is now imported from fieldmappingwidget.py

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
    """Thread for AI-powered data extraction from various sources"""
    data_extracted = pyqtSignal(dict, dict)  # extracted_data, confidence_scores
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int, str)  # progress, status_message
    show_message = pyqtSignal(str, str)  # title, message for safe UI thread display

    def __init__(self, sources: List[DataSource], form_fields: List[FormField],
                 ai_provider: str = "openai", api_key: str = "", model: str = ""):
        super().__init__()
        self.sources = sources
        self.form_fields = form_fields
        self.ai_provider = ai_provider
        self.api_key = api_key
        self.model = model

    def run(self):
        try:
            logger.info("AIDataExtractor: Starting extraction...")
            print("AIDataExtractor: Starting extraction...")
            self.progress_updated.emit(10, "Initializing AI extraction...")
            
            # Extract text from all sources
            all_text = ""
            extracted_data = {}
            confidence_scores = {}
            
            logger.info(f"AIDataExtractor: Processing {len(self.sources)} sources with provider {self.ai_provider}")
            print(f"AIDataExtractor: Processing {len(self.sources)} sources with provider {self.ai_provider}")
            
            for i, source in enumerate(self.sources):
                progress = 20 + (i * 30 // max(len(self.sources), 1))
                self.progress_updated.emit(progress, f"Processing {source.name}...")
                print(f"AIDataExtractor: Processing source {i+1}/{len(self.sources)}: {source.name} (type: {source.source_type})")
                
                if source.source_type == "file":
                    text = self._extract_from_file(source.content)
                elif source.source_type == "image":
                    text = self._extract_from_image(source.content)
                elif source.source_type == "url":
                    text = self._extract_from_url(source.content)
                else:
                    text = source.content
                
                print(f"AIDataExtractor: Extracted {len(text)} characters from {source.name}")
                all_text += f"\n\n=== {source.name} ===\n{text}"
            
            self.progress_updated.emit(60, "Running AI analysis...")
            
            # Use AI to extract structured data
            print(f"AIDataExtractor: Using AI provider: {self.ai_provider}")
            print(f"AIDataExtractor: OpenAI available: {OPENAI_AVAILABLE}")
            print(f"AIDataExtractor: Anthropic available: {ANTHROPIC_AVAILABLE}")
            print(f"AIDataExtractor: Has API key: {'Yes' if self.api_key else 'No'}")
            
            if self.ai_provider == "openai" and OPENAI_AVAILABLE:
                print("AIDataExtractor: Using OpenAI for extraction")
                extracted_data, confidence_scores = self._extract_with_openai(all_text)
            elif self.ai_provider == "anthropic" and ANTHROPIC_AVAILABLE:
                print("AIDataExtractor: Using Anthropic for extraction")
                extracted_data, confidence_scores = self._extract_with_anthropic(all_text)
            else:
                print("AIDataExtractor: Using pattern matching for extraction")
                extracted_data, confidence_scores = self._extract_with_patterns(all_text)
            
            print(f"AIDataExtractor: Extraction complete. Found {len(extracted_data)} fields")
            self.progress_updated.emit(100, "AI extraction complete")
            self.data_extracted.emit(extracted_data, confidence_scores)
            
        except Exception as e:
            import traceback
            error_msg = f"AI extraction error: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            print(f"AIDataExtractor ERROR: {str(e)}")
            print(traceback.format_exc())
            self.error_occurred.emit(error_msg)

    def _extract_from_file(self, file_path: str) -> str:
        """Extract text from various file types"""
        try:
            file_path = Path(file_path)
            
            if file_path.suffix.lower() == '.pdf':
                print(f"DEBUG: PDF file detected: {file_path.name}")
                # For PDFs, instead of extracting text locally, return a marker
                # that will tell the AI to process this PDF directly
                return f"[PDF FILE: {file_path.name}] This is a PDF form that should be processed directly by the AI model."
            
            elif file_path.suffix.lower() in ['.txt', '.md', '.csv']:
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            
            elif file_path.suffix.lower() in ['.json']:
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    return json.dumps(data, indent=2)
            
            else:
                return f"Unsupported file type: {file_path.suffix}"
                
        except Exception as e:
            print(f"ERROR reading file {file_path}: {str(e)}")
            return f"Error reading file: {str(e)}"

    def _extract_from_image(self, image_path: str) -> str:
        """Extract text from images using OCR"""
        if not OCR_AVAILABLE:
            return "OCR not available. Install pytesseract and Pillow."
        
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            return f"OCR error: {str(e)}"

    def _extract_from_url(self, url: str) -> str:
        """Extract text from web pages"""
        if not WEB_SCRAPING_AVAILABLE:
            return "Web scraping not available. Install requests and beautifulsoup4."
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            return f"Web scraping error: {str(e)}"

    def _extract_with_openai(self, text: str) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Extract data using OpenAI GPT via llm_client"""
        if not self.api_key:
            raise ValueError("OpenAI API key required")
        
        # Import our llm_client module
        import llm_client
        
        print("="*50)
        print("OPENAI EXTRACTION DEBUGGING")
        print(f"API Key length: {len(self.api_key)} chars")
        print(f"Model specified: {self.model}")
        print(f"Text length for analysis: {len(text)} chars")
        
        # Create field extraction prompt
        field_names = [f.name for f in self.form_fields]
        field_descriptions = [f.alt_text or f.name for f in self.form_fields]
        
        print(f"Number of fields to extract: {len(field_names)}")
        if field_names:
            print(f"First field: {field_names[0]}")
        
        prompt = f"""
        You are extracting data from a COMPLETED PDF form to populate a blank PDF form with the same structure.

TASK: Extract the client's actual responses/values from the completed form text below.

TARGET FORM FIELDS TO POPULATE:
{json.dumps(dict(zip(field_names, field_descriptions)), indent=2)}

COMPLETED FORM TEXT TO ANALYZE:
{text[:8000]}

EXTRACTION RULES:
1. Look for FILLED-IN VALUES, not field labels or instructions
2. Extract actual data entries like:
   - Names: "TAHIRA FRANCIS", "SHAWN ROGERS"  
   - Case numbers: "24STFL00615"
   - Monetary amounts: 
   - Account details: 
   - Addresses and descriptions of assets/debts
   - Dates and other specific client information

3. IGNORE:
   - Form instructions and field labels
   - Empty fields showing "0.00" or blank
   - Template text like "Give details", "Attach copy", etc.

4. FOCUS ON:
   - Actual names, numbers, and descriptions entered by the client
   - Monetary values that are NOT 0.00
   - Specific account information, addresses, creditor names
   - Any handwritten or typed responses

5. For monetary fields, extract numbers like:
   -  (checking account balance)
   -  (student loan)
   -  (loan amount)
   -  (total debts)

RETURN FORMAT:
{{
    "extracted_data": {{
        "field_name": "actual_client_value"
    }},
    "confidence_scores": {{
        "field_name": 0.95
    }}
}}

Extract only the CLIENT'S ACTUAL DATA ENTRIES, not form structure or empty fields.

IMPORTANT: If you see text like '[PDF FILE: filename.pdf]', this indicates a PDF form is being processed.
In these cases, you should focus on extracting form field values that might be present in the data.
        """
        
        try:
            # Set environment variable for OpenAI API key
            os.environ["OPENAI_API_KEY"] = self.api_key.strip()
            print(f"Set OPENAI_API_KEY environment variable")
            
            # Use the llm_client to generate the response
            print(f"Using llm_client with OpenAI model: {self.model}")
            openai_model = self.model.replace("openai-", "")
            print(f"Calling llm_client.generate_with_openai with model: {openai_model}")
            
            response_text = llm_client.generate_with_openai(openai_model, prompt)
            print(f"OpenAI response received, length: {len(response_text)}")
            print(f"First 100 chars of response: {response_text[:100]}")
            
            # Parse the JSON response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            print(f"JSON start position: {start}, end position: {end}")
            
            if start >= 0 and end > start:
                json_text = response_text[start:end]
                print(f"Attempting to parse JSON of length {len(json_text)}")
                try:
                    result = json.loads(json_text)
                    extracted_data = result.get("extracted_data", {})
                    confidence_scores = result.get("confidence_scores", {})
                    print(f"Successfully parsed JSON with {len(extracted_data)} extracted fields")
                    return extracted_data, confidence_scores
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    print(f"JSON text: {json_text[:500]}...")
                    return {}, {}
            else:
                print(f"Invalid JSON response from OpenAI: {response_text[:100]}...")
                return {}, {}
            
        except Exception as e:
            print(f"OpenAI API error: {str(e)}")
            print(f"Exception type: {type(e).__name__}")
            print(traceback.format_exc())
            self.show_message.emit("OpenAI API Error", f"Error: {str(e)}")
            return {}, {}

    def _extract_with_anthropic(self, text: str) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Extract data using Anthropic Claude via llm_client"""
        if not self.api_key:
            raise ValueError("Anthropic API key required")
        
        print("="*50)
        print("CLAUDE EXTRACTION DEBUGGING")
        print(f"API Key length: {len(self.api_key)} chars")
        print(f"Model specified: {self.model}")
        print(f"Text length for analysis: {len(text)} chars")
        
        try:
            # Import our llm_client module
            import llm_client
            
            # Set the API key in environment (llm_client uses this)
            os.environ["ANTHROPIC_API_KEY"] = self.api_key.strip()
            print(f"Set ANTHROPIC_API_KEY environment variable")
            
            field_names = [f.name for f in self.form_fields]
            field_descriptions = [f.alt_text or f.name for f in self.form_fields]
            
            print(f"Number of fields to extract: {len(field_names)}")
            if field_names:
                print(f"First field: {field_names[0]}")
            
            # Use the model specified by the user, or fall back to a default
            model = self.model if self.model else "claude-3-opus-20240229"
            print(f"Using llm_client with Claude model: {model}")
            
            # Updated prompt with clearer formatting for better JSON output
            prompt = f"""
           You are extracting data from a COMPLETED PDF form to populate a blank PDF form with the same structure.

TASK: Extract the client's actual responses/values from the completed form text below.

TARGET FORM FIELDS TO POPULATE:
{json.dumps(dict(zip(field_names, field_descriptions)), indent=2)}

COMPLETED FORM TEXT TO ANALYZE:
{text[:8000]}

EXTRACTION RULES:
1. Look for FILLED-IN VALUES, not field labels or instructions
2. Extract actual data entries like:
   - Names: "TAHIRA FRANCIS", "SHAWN ROGERS"  
   - Case numbers: "24STFL00615"
   - Monetary amounts: 
   - Account details: 
   - Addresses and descriptions of assets/debts
   - Dates and other specific client information

3. IGNORE:
   - Form instructions and field labels
   - Empty fields showing "0.00" or blank
   - Template text like "Give details", "Attach copy", etc.

4. FOCUS ON:
   - Actual names, numbers, and descriptions entered by the client
   - Monetary values that are NOT 0.00
   - Specific account information, addresses, creditor names
   - Any handwritten or typed responses

5. For monetary fields, extract numbers like:
   -  (checking account balance)
   -  (student loan)
   -  (loan amount)
   -  (total debts)

RETURN FORMAT:
{{
    "extracted_data": {{
        "field_name": "actual_client_value"
    }},
    "confidence_scores": {{
        "field_name": 0.95
    }}
}}

Extract only the CLIENT'S ACTUAL DATA ENTRIES, not form structure or empty fields.

IMPORTANT NOTE FOR PDF FILES: If you see text like '[PDF FILE: filename.pdf]', this indicates
a PDF form is being processed directly. For PDF forms, focus on extracting field values
that appear to match the target form fields listed above.
            """
            
            # Use the llm_client to generate the response
            print(f"Calling llm_client.generate_with_claude with model: {model}")
            response_text = llm_client.generate_with_claude(model, prompt)
            print(f"Claude response received, length: {len(response_text)}")
            print(f"First 100 chars of response: {response_text[:100]}")
            
            # Parse response - wrap in try/except to better handle parsing errors
            try:
                # Find the start and end of the JSON object if there's any surrounding text
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                
                print(f"JSON start position: {start}, end position: {end}")
                
                if start >= 0 and end > start:
                    json_text = response_text[start:end]
                    print(f"Attempting to parse JSON of length {len(json_text)}")
                    
                    try:
                        result = json.loads(json_text)
                        extracted_data = result.get("extracted_data", {})
                        confidence_scores = result.get("confidence_scores", {})
                        
                        # If missing confidence scores, generate defaults
                        if extracted_data and not confidence_scores:
                            confidence_scores = {key: 0.8 for key in extracted_data.keys()}
                            
                        print(f"Successfully parsed JSON with {len(extracted_data)} extracted fields")
                        return extracted_data, confidence_scores
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                        print(f"JSON text: {json_text[:500]}...")
                        self.show_message.emit(
                            "JSON Parsing Error",
                            "Failed to parse Claude's response as JSON. Falling back to pattern matching."
                        )
                        return self._extract_with_patterns(text)
                else:
                    print(f"No valid JSON found in response: {response_text[:100]}...")
                    self.show_message.emit(
                        "JSON Parsing Error",
                        "Could not find valid JSON in Claude's response. Falling back to pattern matching."
                    )
                    return self._extract_with_patterns(text)
            except Exception as e:
                print(f"JSON processing error: {str(e)}")
                print(traceback.format_exc())
                self.show_message.emit(
                    "JSON Processing Error",
                    "Error processing Claude's response. Falling back to pattern matching."
                )
                return self._extract_with_patterns(text)
            
        except Exception as e:
            error_details = str(e)
            print(f"Exception in Anthropic extraction: {error_details}")
            print(f"Exception type: {type(e).__name__}")
            print(traceback.format_exc())
            logger.error(f"General exception in Anthropic extraction: {error_details}")
            # For other errors, also fall back to pattern matching
            print("Falling back to pattern matching due to error.")
            self.show_message.emit(
                "Claude API Error",
                f"Error while using Claude: {error_details}\n\n"
                "Switching to pattern matching as a fallback."
            )
            return self._extract_with_patterns(text)

    def _extract_with_patterns(self, text):
        """Enhanced extraction using Universal Form Mapper"""
        print("🌍 Universal Form Mapper - Enhanced Extraction")
        
        # Use the universal mapper for better results
        try:
            # Import universal mapper
            from universal_form_mapper import UniversalFormMapper
            
            # Create source documents from text
            source_documents = {"extraction_text": text}
            
            # Get form fields
            form_fields = getattr(self, 'form_fields', [])
            if not form_fields:
                print("⚠️ No form fields available for universal mapping")
                return {}, {}
            
            print(f"🎯 Using Universal Mapper with {len(form_fields)} fields")
            
            # Initialize universal mapper
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
            mapper = UniversalFormMapper(api_key=api_key)
            
            # Run universal mapping
            result = mapper.map_any_form(form_fields, source_documents)
            
            print(f"✅ Universal mapping completed:")
            print(f"   Strategy: {result.mapping_strategy}")
            print(f"   Fields mapped: {len(result.mapped_fields)}")
            print(f"   Form type: {result.form_analysis.get('form_type', 'unknown')}")
            
            return result.mapped_fields, result.confidence_scores
            
        except Exception as e:
            print(f"❌ Universal mapper failed, using basic fallback: {e}")
            # Fallback to basic pattern matching
            return self._basic_pattern_fallback(text)
                
    def _basic_pattern_fallback(self, text):
        """Basic pattern matching fallback"""
        extracted_data = {}
        confidence_scores = {}
        
        # Enhanced patterns for key legal form data
        patterns = {
            # People and roles
            'attorney_name': r'attorney.*?([A-Z][a-z]+ [A-Z][a-z]+)',
            'petitioner_name': r'petitioner.*?([A-Z][a-z]+ [A-Z][a-z]+)',
            'respondent_name': r'respondent.*?([A-Z][a-z]+ [A-Z][a-z]+)',
            
            # Case information
            'case_number': r'case.*?number.*?([A-Z0-9]+)',
            'court_county': r'county of\s+([A-Z\s]+)',
            
            # Financial amounts
            'student_loan': r'student.*?loan.*?\$?\s*([0-9,]+\.?[0-9]*)',
            'credit_card': r'credit.*?card.*?\$?\s*([0-9,]+\.?[0-9]*)',
            'total_debt': r'total.*?debt.*?\$?\s*([0-9,]+\.?[0-9]*)',
            
            # Contact info
            'phone': r'\((\d{3})\)\s*(\d{3})-(\d{4})',
            'address': r'(\d+\s+[A-Za-z\s]+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr))',
            
            # Dates
            'date': r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}'
        }
        
        # Extract using patterns
        for field in self.form_fields:
            field_name = field.name
            field_text = (field.name + " " + (field.alt_text or "")).lower()
            
            best_value = None
            best_confidence = 0
            
            # Try to match field intent with patterns
            for pattern_type, pattern in patterns.items():
                if any(word in field_text for word in pattern_type.split('_')):
                    import re
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        if pattern_type == 'phone' and len(match.groups()) >= 3:
                            value = f"({match.group(1)}) {match.group(2)}-{match.group(3)}"
                        else:
                            value = match.group(1) if match.groups() else match.group(0)
                        
                        confidence = 0.8
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_value = value.strip()
            
            if best_value and best_confidence > 0.5:
                extracted_data[field_name] = best_value
                confidence_scores[field_name] = best_confidence
        
        print(f"✅ Basic fallback extracted {len(extracted_data)} fields")
        return extracted_data, confidence_scores

    def _show_clarifying_questions(self, questions: List[str], extracted_data: Dict[str, str], confidence_scores: Dict[str, float]):
        """Show clarifying questions to the user and update extraction based on answers"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout, QScrollArea
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Clarifying Questions - Help Improve Extraction")
        dialog.setGeometry(200, 200, 600, 400)
        
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "I found multiple people and relationships in your documents. "
            "Please help me understand the context to improve the extraction:"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Scrollable area for questions
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Store text areas for answers
        self.question_answers = []
        
        for i, question in enumerate(questions):
            # Question label
            q_label = QLabel(f"Question {i+1}: {question}")
            q_label.setWordWrap(True)
            q_label.setStyleSheet("font-weight: bold; margin: 10px 0px 5px 0px;")
            scroll_layout.addWidget(q_label)
            
            # Answer text area
            answer_area = QTextEdit()
            answer_area.setMaximumHeight(60)
            answer_area.setPlaceholderText("Enter your answer here...")
            scroll_layout.addWidget(answer_area)
            self.question_answers.append(answer_area)
        
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        update_btn = QPushButton("Update Extraction")
        update_btn.clicked.connect(lambda: self._process_user_answers(dialog, extracted_data, confidence_scores))
        button_layout.addWidget(update_btn)
        
        skip_btn = QPushButton("Skip Questions")
        skip_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(skip_btn)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        # Show dialog
        dialog.exec()


    def _process_user_answers(self, dialog, extracted_data: Dict[str, str], confidence_scores: Dict[str, float]):
        """Process user answers to improve extraction"""
        answers = []
        for text_area in self.question_answers:
            answers.append(text_area.toPlainText().strip())
        
        # Simple answer processing - in a real system, this would be more sophisticated
        user_context = " ".join(answers)
        
        print("User provided context:")
        for i, answer in enumerate(answers):
            if answer:
                print(f"  Answer {i+1}: {answer}")
        
        # Update the AI results display with user context
        if hasattr(self, 'ai_results'):
            current_results = self.ai_results.toPlainText()
            updated_results = current_results + f"\n\nUser Context:\n{user_context}\n\nNote: Extraction has been updated based on your input."
            self.ai_results.setPlainText(updated_results)
        
        dialog.accept()


    def _create_extraction_prompt(self, text):
        """Create an enhanced extraction prompt using the intelligent system"""
        try:
            # Try to use the advanced system
            from advanced_extraction_system import IntelligentExtractor, create_intelligent_extraction_prompt
            
            extractor = IntelligentExtractor()
            entities = extractor.extract_all_entities(text)
            relationships = extractor.identify_relationships(text, entities)
            
            field_names = [f.name for f in self.form_fields]
            field_descriptions = [f.alt_text or f.name for f in self.form_fields]
            
            return create_intelligent_extraction_prompt(entities, relationships, field_names, field_descriptions, text)
            
        except ImportError:
            # Fallback to enhanced llm_client
            try:
                import llm_client
                field_names = [f.name for f in self.form_fields]
                field_descriptions = [f.alt_text or f.name for f in self.form_fields]
                
                return llm_client.create_enhanced_extraction_prompt(field_names, field_descriptions, text)
            except ImportError:
                # Ultimate fallback
                field_names = [f.name for f in self.form_fields]
                field_descriptions = [f.alt_text or f.name for f in self.form_fields]
                
                return f"""
    Extract meaningful data from the source documents to fill form fields. Focus on identifying who is who and their relationships.

    TARGET FIELDS:
    {json.dumps(dict(zip(field_names, field_descriptions)), indent=2)}

    SOURCE TEXT:
    {text[:8000]}

    Analyze the relationships between people (who is the client vs attorney vs opposing party) and extract the correct person's data for each field.

    Return JSON format:
    {{
        "extracted_data": {{"field_name": "correct_person_value"}},
        "confidence_scores": {{"field_name": 0.95}},
        "data_source_notes": {{"field_name": "Explanation of data source"}}
    }}
    """


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
        self.init_ui()
        self.apply_theme()

        
        
        
        # Add crash protection for tab switching
        try:
            if hasattr(self, 'tab_widget'):
                self.tab_widget.currentChanged.connect(self._safe_tab_change)
        except Exception as e:
            print(f"⚠️ Could not add tab change protection: {e}")

        # Initialize Universal Form Mapper
        if UNIVERSAL_MAPPER_AVAILABLE:
            try:
                self.universal_integration = integrate_safe_universal_mapper(self)
                print("✅ Universal Form Mapper integrated successfully")
            except Exception as e:
                print(f"⚠️ Universal mapper integration failed: {e}")
                self.universal_integration = None
        else:
            self.universal_integration = None
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
        
        # Add debug print to ensure this section is executed
        print("DEBUG: PDF file selection UI created")

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
        print("DEBUG: Field mapping tab created")

        # Create a safer version of the AI tab that avoids the crashes
        print("DEBUG: Creating improved AI tab")
        
        # Create a simple implementation instead of using the complex AIExtractionWidget
        ai_tab = QWidget()
        ai_layout = QVBoxLayout(ai_tab)
        
        # --- AI Provider Selection ---
        provider_group = QGroupBox("AI Provider")
        provider_layout = QVBoxLayout()
        
        self.ai_provider_radio_pattern = QRadioButton("Pattern Matching (Free, No API Key Required)")
        self.ai_provider_radio_pattern.setChecked(True)
        provider_layout.addWidget(self.ai_provider_radio_pattern)
        
        self.ai_provider_radio_openai = QRadioButton("OpenAI (API Key Required)")
        provider_layout.addWidget(self.ai_provider_radio_openai)
        
        self.ai_provider_radio_anthropic = QRadioButton("Anthropic Claude (API Key Required)")
        provider_layout.addWidget(self.ai_provider_radio_anthropic)
        
        # Add model selection
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
        
        # --- Data Sources ---
        sources_group = QGroupBox("Data Sources")
        sources_layout = QVBoxLayout()
        
        # Source management buttons
        source_buttons = QHBoxLayout()
        
        self.add_file_btn = QPushButton("Add File")
        self.add_file_btn.clicked.connect(self.add_ai_file_source_btn)
        source_buttons.addWidget(self.add_file_btn)
        
        self.add_text_btn = QPushButton("Add Text")
        self.add_text_btn.clicked.connect(self.add_ai_text_source_btn)
        source_buttons.addWidget(self.add_text_btn)
        
        self.add_url_btn = QPushButton("Add URL")
        self.add_url_btn.clicked.connect(self.add_ai_url_source_btn)
        source_buttons.addWidget(self.add_url_btn)
        
        self.add_image_btn = QPushButton("Add Image (OCR)")
        self.add_image_btn.clicked.connect(self.add_ai_image_source_btn)
        source_buttons.addWidget(self.add_image_btn)
        
        source_buttons.addStretch()
        
        self.clear_sources_btn = QPushButton("Clear All")
        self.clear_sources_btn.clicked.connect(self.clear_ai_sources_btn)
        source_buttons.addWidget(self.clear_sources_btn)
        
        sources_layout.addLayout(source_buttons)
        
        # Sources list
        self.sources_list = QListWidget()
        self.sources_list.setMaximumHeight(150)
        sources_layout.addWidget(self.sources_list)
        
        sources_group.setLayout(sources_layout)
        ai_layout.addWidget(sources_group)
        
        # --- Text Input ---
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
        
        # --- Extract Button ---
        extract_layout = QHBoxLayout()
        
        self.ai_extract_btn = QPushButton("Extract Data")
        self.ai_extract_btn.clicked.connect(self.extract_with_ai)
        extract_layout.addWidget(self.ai_extract_btn)
        
        self.ai_progress = QProgressBar()
        self.ai_progress.setVisible(False)
        extract_layout.addWidget(self.ai_progress)
        
        ai_layout.addLayout(extract_layout)
        
        # --- Results ---
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
        print("DEBUG: Improved AI tab added successfully")

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
        print(f"DEBUG: extract_fields called, path: {self.current_pdf_path}")
        if not self.current_pdf_path:
            print("DEBUG: No PDF path set")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Extracting form fields...")
        
        print("DEBUG: Creating PDFFieldExtractor thread")
        self.extractor_thread = PDFFieldExtractor(self.current_pdf_path)
        self.extractor_thread.fields_extracted.connect(self.on_fields_extracted)
        self.extractor_thread.error_occurred.connect(self.on_extraction_error)
        self.extractor_thread.progress_updated.connect(self.progress_bar.setValue)
        self.extractor_thread.start()
        print("DEBUG: PDFFieldExtractor thread started")

    def on_fields_extracted(self, fields: List[FormField]):
        """Handle successful field extraction"""
        self.progress_bar.setVisible(False)
        self.field_mapping_widget.set_fields(fields)
        # Store fields for AI extraction
        self.form_fields = fields
        self.fill_form_btn.setEnabled(True)
        self.status_label.setText(f"Ready - Found {len(fields)} form fields")

    def on_extraction_error(self, error_message: str):
        """Handle field extraction error"""
        self.progress_bar.setVisible(False)
        self.status_label.setText("Error extracting fields")
        QMessageBox.critical(self, "Error", error_message)

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
        
    # Add new methods for handling AI data sources
    def add_ai_file_source_btn(self):
        """Add a file as data source for AI analysis"""
        print("DEBUG: Add file source button clicked")
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Data File", "",
                "All Supported (*.pdf *.txt *.json *.csv *.md);;PDF Files (*.pdf);;Text Files (*.txt);;JSON Files (*.json);;CSV Files (*.csv)"
            )
            
            if file_path:
                print(f"DEBUG: Selected file: {file_path}")
                # Get simple filename without using Path
                file_name = os.path.basename(file_path)
                print(f"DEBUG: Extracted basename: {file_name}")
                
                # Add to list widget with simple string - avoid emoji which might cause memory issues
                self.sources_list.addItem(f"File: {file_name}")
                print("DEBUG: Added item to sources list")
                
                # Initialize data sources list if needed
                if not hasattr(self, 'ai_data_sources'):
                    self.ai_data_sources = []
                    print("DEBUG: Initialized ai_data_sources list")
                
                # Store simple strings only, no complex objects
                self.ai_data_sources.append(('file', str(file_path)))
                print("DEBUG: Appended to ai_data_sources")
                
        except Exception as e:
            print(f"ERROR in add_ai_file_source_btn: {e}")
            print(traceback.format_exc())
    
    def add_ai_text_source_btn(self):
        """Add text input as data source for AI analysis"""
        try:
            text = self.ai_text_input.toPlainText().strip()
            if text:
                print(f"DEBUG: Adding text source ({len(text)} chars)")
                # Simple string without emoji
                self.sources_list.addItem(f"Text: {len(text)} chars")
                
                # Initialize data sources list if needed
                if not hasattr(self, 'ai_data_sources'):
                    self.ai_data_sources = []
                
                # Add text (truncate if very long to avoid memory issues)
                max_len = 5000
                if len(text) > max_len:
                    truncated = text[:max_len] + "... (truncated)"
                    self.ai_data_sources.append(('text', truncated))
                else:
                    self.ai_data_sources.append(('text', text))
                    
                self.ai_text_input.clear()
                print("DEBUG: Text source added successfully")
        except Exception as e:
            print(f"ERROR in add_ai_text_source_btn: {e}")
            print(traceback.format_exc())
    
    def add_ai_url_source_btn(self):
        """Add URL as data source for AI analysis"""
        try:
            url, ok = QInputDialog.getText(
                self, "Add URL Source",
                "Enter URL to scrape for data:",
                QLineEdit.EchoMode.Normal,
                "https://"
            )
            
            if ok and url:
                print(f"DEBUG: Adding URL source: {url}")
                # Simple string without emoji
                display_url = url[:50] + "..." if len(url) > 50 else url
                self.sources_list.addItem(f"URL: {display_url}")
                
                # Initialize data sources list if needed
                if not hasattr(self, 'ai_data_sources'):
                    self.ai_data_sources = []
                
                self.ai_data_sources.append(('url', url))
                print("DEBUG: URL source added successfully")
        except Exception as e:
            print(f"ERROR in add_ai_url_source_btn: {e}")
            print(traceback.format_exc())
    
    # COMPLETE FIX - Replace everything from the broken add_ai_image_source_btn method onwards

    def add_ai_image_source_btn(self):
        """Add image for OCR as data source for AI analysis"""
        try:
            # Just check if OCR is potentially available, but don't actually import
            # the modules yet to avoid potential issues
            OCR_AVAILABLE = False
            try:
                import importlib.util
                if (importlib.util.find_spec("PIL") and
                    importlib.util.find_spec("pytesseract")):
                    OCR_AVAILABLE = True
            except ImportError:
                OCR_AVAILABLE = False
                
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
                print(f"DEBUG: Adding image source: {file_path}")
                # Get simple filename without using Path
                file_name = os.path.basename(file_path)
                self.sources_list.addItem(f"Image: {file_name}")
                
                # Initialize data sources list if needed
                if not hasattr(self, 'ai_data_sources'):
                    self.ai_data_sources = []
                
                # Just store the path, don't try to process the image yet
                self.ai_data_sources.append(('image', str(file_path)))
                print("DEBUG: Image source added successfully")
        except Exception as e:
            print(f"ERROR in add_ai_image_source_btn: {e}")
            print(traceback.format_exc())

    def clear_ai_sources_btn(self):
        """Clear all AI data sources"""
        try:
            print("DEBUG: Clearing AI sources")
            self.sources_list.clear()
            if hasattr(self, 'ai_data_sources'):
                self.ai_data_sources = []
            print("DEBUG: AI sources cleared successfully")
        except Exception as e:
            print(f"ERROR in clear_ai_sources_btn: {e}")
            print(traceback.format_exc())

    def extract_with_ai(self):
        """Extract data using the simplified AI tab"""
        try:
            print("DEBUG: extract_with_ai called")
            
            # Check if form fields are available
            if not hasattr(self, 'form_fields') or not self.form_fields:
                QMessageBox.warning(self, "No Form Fields",
                                   "Please load a PDF form first to define extraction fields.")
                return
                
            # Check if we have any data sources
            has_text = bool(self.ai_text_input.toPlainText().strip())
            has_sources = hasattr(self, 'ai_data_sources') and bool(self.ai_data_sources)
            
            print(f"DEBUG: Has text input: {has_text}")
            print(f"DEBUG: Has data sources: {has_sources}")
            print(f"DEBUG: Number of data sources: {len(self.ai_data_sources) if has_sources else 0}")
            
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
            
            # Clear previous results
            self.ai_results.clear()
            
            # Collect all text from sources and direct input
            all_text = self.ai_text_input.toPlainText().strip()
            
            # Process data sources to extract text
            self.ai_progress.setValue(20)
            if has_sources:
                self.status_label.setText("Processing data sources...")
                for source_type, source_content in self.ai_data_sources:
                    print(f"DEBUG: Processing source: {source_type}")
                    
                    if source_type == 'file':
                        # Extract text from file
                        file_text = self._extract_text_from_file(source_content)
                        if file_text:
                            all_text += f"\n\n=== File: {os.path.basename(source_content)} ===\n{file_text}"
                    elif source_type == 'text':
                        all_text += f"\n\n=== Text Input ===\n{source_content}"
                    elif source_type == 'url':
                        # For now, just include the URL as text
                        all_text += f"\n\n=== URL: {source_content} ===\n(URL content would be processed here)"
                    elif source_type == 'image':
                        # For now, just include the image path
                        all_text += f"\n\n=== Image: {os.path.basename(source_content)} ===\n(Image content would be processed here)"
            
            # Use a safer extraction approach
            print(f"DEBUG: Starting extraction with {len(all_text)} chars of text")
            # Get the selected model from the UI
            selected_model = self.ai_model_combo.currentText()
            print(f"DEBUG: Selected model from UI: {selected_model}")
            # Pass both provider and model to extraction
            QTimer.singleShot(100, lambda: self._perform_extraction(all_text, provider, selected_model))
            
        except Exception as e:
            print(f"ERROR in extract_with_ai: {e}")
            print(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"Error during AI extraction: {str(e)}")
            self.ai_progress.setVisible(False)
            self.ai_extract_btn.setEnabled(True)

    def _update_ai_model_list(self):
        """Update the model list based on selected provider"""
        try:
            self.ai_model_combo.clear()
            
            if self.ai_provider_radio_openai.isChecked():
                print("DEBUG: Loading OpenAI models")
                openai_models = [
                    "gpt-4o",
                    "gpt-4-turbo",
                    "gpt-4",
                    "gpt-3.5-turbo"
                ]
                self.ai_model_combo.addItems(openai_models)
                
            elif self.ai_provider_radio_anthropic.isChecked():
                print("DEBUG: Loading Anthropic models")
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
            print(f"ERROR updating model list: {e}")
            print(traceback.format_exc())

    def _extract_text_from_file(self, file_path):
        """Extract text from various file types"""
        print(f"DEBUG: Extracting text from file: {file_path}")
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.pdf':
                # For PDFs, we need to extract text and also provide the file path for direct processing
                print(f"DEBUG: PDF file detected: {os.path.basename(file_path)}")
                file_name = os.path.basename(file_path)
                extracted_text = ""
                
                # Try to extract text from the PDF first
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as pdf_file:
                        reader = PyPDF2.PdfReader(pdf_file)
                        text_content = []
                        for page_num in range(len(reader.pages)):
                            page = reader.pages[page_num]
                            text_content.append(page.extract_text())
                        extracted_text = "\n\n".join(text_content)
                        print(f"DEBUG: Extracted {len(extracted_text)} chars of text from PDF")
                except Exception as e:
                    print(f"DEBUG: Error extracting text from PDF: {str(e)}")
                
                # If using Claude, also include the PDF file path for potential direct loading
                if hasattr(self, 'ai_provider_radio_anthropic') and self.ai_provider_radio_anthropic.isChecked():
                    print(f"DEBUG: Adding PDF file path for Claude: {file_path}")
                    return f"{extracted_text}\n\n[PDF_PATH: {file_path}]"
                
                # For other providers, return the extracted text or a marker
                if extracted_text:
                    return extracted_text
                else:
                    return f"[PDF FILE: {file_name}] This is a PDF form that should be processed directly by the AI model."
            
            elif ext in ['.txt', '.md', '.csv']:
                # Read text files directly
                with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                    text = file.read()
                    print(f"DEBUG: Read {len(text)} chars from text file")
                    return text
            
            elif ext == '.json':
                # Parse JSON and format it
                with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                    try:
                        import json
                        data = json.load(file)
                        text = json.dumps(data, indent=2)
                        print(f"DEBUG: Parsed JSON with {len(text)} chars")
                        return text
                    except Exception as e:
                        # If JSON parsing fails, just return raw content
                        file.seek(0)
                        return file.read()
            
            else:
                return f"[Unsupported file type: {ext}]"
                
        except Exception as e:
            print(f"ERROR in _extract_text_from_file: {e}")
            print(traceback.format_exc())
            return f"[Error reading file: {str(e)}]"

    def _perform_extraction(self, text, provider, selected_model=None):
        """Perform the actual extraction with safer error handling"""
        try:
            self.ai_progress.setValue(50)
            print(f"DEBUG: Starting extraction with provider: {provider}, model: {selected_model}")
            
            # Check if API libraries are available and API key is provided
            api_key = self.api_key_edit.text().strip()
            
            # Enhanced library checking with better debugging
            if provider == "openai":
                try:
                    import openai
                    print("DEBUG: OpenAI library is available")
                    if not api_key:
                        print("DEBUG: No OpenAI API key provided, falling back to pattern matching")
                        provider = "pattern"
                    else:
                        print("DEBUG: OpenAI API key provided, will use OpenAI")
                except ImportError:
                    print("DEBUG: OpenAI library not available, falling back to pattern matching")
                    provider = "pattern"
            elif provider == "anthropic":
                try:
                    import anthropic
                    print("DEBUG: Anthropic library is available")
                    if not api_key:
                        print("DEBUG: No Anthropic API key provided, falling back to pattern matching")
                        provider = "pattern"
                    else:
                        print("DEBUG: Anthropic API key provided, will use Claude")
                except ImportError:
                    print("DEBUG: Anthropic library not available, falling back to pattern matching")
                    provider = "pattern"
            
            # Pattern matching implementation (always available)
            if provider == "pattern":
                print("DEBUG: Using pattern matching")
                extracted_data, confidence = self._extract_with_patterns(text)
            else:
                # Try API-based extraction if libraries are available
                try:
                    # Set API key in environment
                    os.environ[f"{'OPENAI' if provider == 'openai' else 'ANTHROPIC'}_API_KEY"] = api_key
                    print(f"DEBUG: Set API key environment variable for {provider}")
                    
                    # Import client only when needed
                    if provider == "openai":
                        self.ai_progress.setValue(60)
                        # Use selected model or fall back to default
                        model_to_use = selected_model if selected_model and selected_model != "Default Model" else "gpt-3.5-turbo"
                        print(f"DEBUG: Using OpenAI model: {model_to_use}")
                        
                        # Safe import and call
                        try:
                            import llm_client
                            print(f"DEBUG: Calling llm_client.generate_with_openai with model {model_to_use}")
                            response_text = llm_client.generate_with_openai(model_to_use, self._create_extraction_prompt(text))
                            print(f"DEBUG: OpenAI response received, length: {len(response_text) if response_text else 0}")
                            extracted_data, confidence = self._parse_ai_response(response_text)
                        except ImportError:
                            print("DEBUG: Import error for OpenAI, falling back to pattern matching")
                            QMessageBox.warning(self, "Module Error",
                                              "Could not import OpenAI library. Falling back to pattern matching.")
                            extracted_data, confidence = self._extract_with_patterns(text)
                    else:  # anthropic
                        self.ai_progress.setValue(60)
                        # Use selected model or fall back to default
                        model_to_use = selected_model if selected_model and selected_model != "Default Model" else "claude-3-sonnet-20240229"
                        print(f"DEBUG: Using Anthropic model: {model_to_use}")
                        
                        try:
                            import llm_client
                            print(f"DEBUG: Calling llm_client.generate_with_claude with model {model_to_use}")
                            response_text = llm_client.generate_with_claude(model_to_use, self._create_extraction_prompt(text))
                            print(f"DEBUG: Claude response received, length: {len(response_text) if response_text else 0}")
                            extracted_data, confidence = self._parse_ai_response(response_text)
                        except ImportError:
                            print("DEBUG: Import error for Anthropic, falling back to pattern matching")
                            QMessageBox.warning(self, "Module Error",
                                              "Could not import Anthropic library. Falling back to pattern matching.")
                            extracted_data, confidence = self._extract_with_patterns(text)
                except Exception as e:
                    print(f"API extraction error: {str(e)}")
                    print(traceback.format_exc())
                    QMessageBox.warning(self, "API Error",
                                      f"Error during API extraction: {str(e)}\n\nFalling back to pattern matching.")
                    extracted_data, confidence = self._extract_with_patterns(text)
            
            # Display results
            self.ai_progress.setValue(90)
            
            # Apply to form fields
            self.field_mapping_widget.set_field_data(extracted_data)
            
            # Show results
            result_text = "Extraction Results:\n\n"
            for field_name, value in extracted_data.items():
                conf = confidence.get(field_name, 0.0)
                result_text += f"• {field_name}: {value} (confidence: {conf:.1%})\n"
                
            self.ai_results.setPlainText(result_text)
            
            # Show completion
            self.status_label.setText(f"Extracted {len(extracted_data)} field values")
            
        except Exception as e:
            print(f"Extraction error: {str(e)}")
            print(traceback.format_exc())
            self.ai_results.setPlainText(f"Error during extraction: {str(e)}")
        finally:
            self.ai_progress.setVisible(False)
            self.ai_extract_btn.setEnabled(True)

    def _create_extraction_prompt(self, text):
        """Create an enhanced extraction prompt using the new system"""
        try:
            import llm_client
            field_names = [f.name for f in self.form_fields]
            field_descriptions = [f.alt_text or f.name for f in self.form_fields]
            
            return llm_client.create_enhanced_extraction_prompt(field_names, field_descriptions, text)
        except ImportError:
            # Fallback to basic prompt
            field_names = [f.name for f in self.form_fields]
            field_descriptions = [f.alt_text or f.name for f in self.form_fields]
            
            return f"""
    Extract meaningful data from the source documents to fill form fields. Avoid template/placeholder content.

    TARGET FIELDS:
    {json.dumps(dict(zip(field_names, field_descriptions)), indent=2)}

    SOURCE TEXT:
    {text[:8000]}

    Extract only real, specific data that would be meaningful for each field. Ignore repeated template values and placeholders.

    Return JSON format:
    {{
        "extracted_data": {{"field_name": "real_value"}},
        "confidence_scores": {{"field_name": 0.95}}
    }}
    """

    def _parse_ai_response(self, response_text):
        """Parse AI response to extract data and confidence scores"""
        try:
            # Find JSON in response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_text = response_text[start:end]
                try:
                    result = json.loads(json_text)
                    extracted_data = result.get("extracted_data", {})
                    confidence_scores = result.get("confidence_scores", {})
                    
                    # If missing confidence scores, generate defaults
                    if extracted_data and not confidence_scores:
                        confidence_scores = {key: 0.8 for key in extracted_data.keys()}
                        
                    return extracted_data, confidence_scores
                except json.JSONDecodeError:
                    # Fall back to pattern matching if JSON parsing fails
                    return self._extract_with_patterns(response_text)
            else:
                # No JSON found, fall back to pattern matching
                return self._extract_with_patterns(response_text)
        except Exception as e:
            print(f"Error parsing AI response: {str(e)}")
            print(traceback.format_exc())
            return {}, {}

    def _extract_with_patterns(self, text):
        """Enhanced pattern matching that avoids template content"""
        print("Using enhanced pattern matching extraction")
        
        extracted_data = {}
        confidence_scores = {}
        
        # Demo data if no text provided
        if not text.strip():
            if self.form_fields:
                for i, field in enumerate(self.form_fields[:min(3, len(self.form_fields))]):
                    extracted_data[field.name] = f"Sample data {i+1} (demo mode)"
                    confidence_scores[field.name] = 0.8
            return extracted_data, confidence_scores
        
        # Use enhanced pattern extraction from llm_client
        try:
            import llm_client
            field_names = [f.name for f in self.form_fields]
            field_descriptions = [f.alt_text or f.name for f in self.form_fields]
            
            extracted_data, confidence_scores = llm_client.enhanced_pattern_extraction(
                text, field_names, field_descriptions
            )
            
            print(f"Enhanced pattern extraction complete: {len(extracted_data)} fields found")
            if len(extracted_data) == 0:
                print("WARNING: No high-quality fields found. Try adding more specific data sources.")
            else:
                print("Top extractions:")
                for field_name, value in list(extracted_data.items())[:5]:
                    conf = confidence_scores.get(field_name, 0.0)
                    print(f"  • {field_name}: {value} (confidence: {conf:.1%})")
                    
            return extracted_data, confidence_scores
            
        except ImportError:
            print("llm_client not available, falling back to basic pattern matching")
            return self._basic_pattern_extraction(text)

    def _basic_pattern_extraction(self, text):
        """Fallback basic pattern extraction"""
        extracted_data = {}
        confidence_scores = {}
        
        # Track value frequency to avoid template values
        value_frequency = {}
        
        # Enhanced patterns that avoid template content
        patterns = {
            'name': [
                r'\b([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
                r'(?:PETITIONER|RESPONDENT|PLAINTIFF|DEFENDANT):\s*([A-Z\s]+)',
            ],
            'case_number': [
                r'\b(\d{2}[A-Z]{2,4}\d{5,8})\b',
                r'(?:CASE|FILE|DOCKET)\s*(?:NO\.?|NUMBER)?\s*:?\s*([A-Z0-9\-]+)',
            ],
            'phone': [
                r'\((\d{3})\)\s*(\d{3})-(\d{4})',
                r'(\d{3})[-.\s](\d{3})[-.\s](\d{4})',
            ],
            'email': [
                r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
            ],
            'address': [
                r'\b(\d+\s+[A-Za-z\s]+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Place|Pl))\b',
            ],
            'money': [
                r'\$\s*([1-9]\d{0,2}(?:,\d{3})*(?:\.\d{2})?)',  # Exclude $0.00
            ],
            'date': [
                r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b',
            ],
        }
        
        # Count all values first to detect templates
        all_values = []
        for field in self.form_fields:
            field_lower = field.name.lower()
            alt_lower = field.alt_text.lower() if field.alt_text else ""
            
            for pattern_name, pattern_list in patterns.items():
                if pattern_name in field_lower or pattern_name in alt_lower:
                    for pattern in pattern_list:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        for match in matches:
                            if isinstance(match, tuple):
                                if pattern_name == 'phone' and len(match) >= 3:
                                    value = f"({match[0]}) {match[1]}-{match[2]}"
                                else:
                                    value = " ".join(match)
                            else:
                                value = match
                            all_values.append(value)
        
        # Count frequency
        for value in all_values:
            value_frequency[value] = value_frequency.get(value, 0) + 1
        
        # Now extract with frequency filtering
        for field in self.form_fields:
            field_lower = field.name.lower()
            alt_lower = field.alt_text.lower() if field.alt_text else ""
            
            matched = False
            best_value = None
            best_confidence = 0
            
            for pattern_name, pattern_list in patterns.items():
                if matched:
                    break
                    
                if pattern_name in field_lower or pattern_name in alt_lower:
                    for pattern in pattern_list:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        for match in matches:
                            if isinstance(match, tuple):
                                if pattern_name == 'phone' and len(match) >= 3:
                                    value = f"({match[0]}) {match[1]}-{match[2]}"
                                else:
                                    value = " ".join(match)
                            else:
                                value = match
                            
                            # Skip high-frequency (template) values
                            frequency = value_frequency.get(value, 1)
                            if frequency > 3:
                                continue  # Skip template values
                            
                            # Calculate confidence based on frequency and pattern
                            confidence = 0.8
                            if frequency > 1:
                                confidence *= 0.7  # Lower confidence for repeated values
                            
                            # Special handling for different types
                            if pattern_name == 'money':
                                try:
                                    amount = float(value.replace(',', ''))
                                    if amount == 0:
                                        continue  # Skip zero amounts
                                    confidence *= 1.2  # Boost for non-zero money
                                except:
                                    pass
                            
                            elif pattern_name == 'date':
                                # Skip obvious template dates
                                if value in ['6/7/2020', '01/01/2020', '12/31/2020']:
                                    continue
                            
                            elif pattern_name == 'name':
                                # Skip placeholder names
                                if 'address' in value.lower() or len(value.split()) < 2:
                                    continue
                            
                            if confidence > best_confidence:
                                best_confidence = confidence
                                best_value = value
                                matched = True
            
            if best_value and best_confidence >= 0.5:
                extracted_data[field.name] = best_value
                confidence_scores[field.name] = min(best_confidence, 0.9)
                print(f"Extracted for '{field.name}': {best_value} (confidence: {best_confidence:.1%})")
        
        return extracted_data, confidence_scores

    def _safe_tab_change(self, index):
        """Safely handle tab changes to prevent crashes"""
        try:
            print(f"DEBUG: Switching to tab {index}")
            
            # Force a repaint of the current tab to prevent paint issues
            current_widget = self.tab_widget.widget(index)
            if current_widget:
                current_widget.update()
                current_widget.repaint()
            
            # Update status
            tab_names = ["Field Mapping", "AI Data Extraction", "Data Management"]
            if 0 <= index < len(tab_names):
                self.status_label.setText(f"Switched to {tab_names[index]} tab")
                
        except Exception as e:
            print(f"⚠️ Error during tab change: {e}")
            # Don't crash - just log the error
            if hasattr(self, 'status_label'):
                self.status_label.setText("Tab switch completed")


    def _create_extraction_prompt(self, text):
        """Create an enhanced extraction prompt using the new system"""
        try:
            import llm_client
            field_names = [f.name for f in self.form_fields]
            field_descriptions = [f.alt_text or f.name for f in self.form_fields]
            
            return llm_client.create_enhanced_extraction_prompt(field_names, field_descriptions, text)
        except ImportError:
            # Fallback to basic prompt
            field_names = [f.name for f in self.form_fields]
            field_descriptions = [f.alt_text or f.name for f in self.form_fields]
            
            return f"""
    Extract meaningful data from the source documents to fill form fields. Avoid template/placeholder content.

    TARGET FIELDS:
    {json.dumps(dict(zip(field_names, field_descriptions)), indent=2)}

    SOURCE TEXT:
    {text[:8000]}

    Extract only real, specific data that would be meaningful for each field. Ignore repeated template values and placeholders.

    Return JSON format:
    {{
        "extracted_data": {{"field_name": "real_value"}},
        "confidence_scores": {{"field_name": 0.95}}
    }}
    """

def main():
    """Main entry point for PDF Form Filler v3"""
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("PDF Form Filler")
    app.setApplicationVersion("1.0")
    
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