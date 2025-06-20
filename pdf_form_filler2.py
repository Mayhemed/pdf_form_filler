#!/usr/bin/env python3
"""
AI-Powered PDF Form Filler v4 - MULTI-THREADED PROCESSING
Author: Assistant
Description: Enhanced version with parallel document processing and intelligent merging
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
import threading
import concurrent.futures
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, asdict
from queue import Queue
import time

try:
    import dotenv
except ImportError:
    dotenv = None
from pathlib import Path

# Set up logging
logging.basicConfig(
    filename='pdf_form_filler_v4_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('PDF_Form_Filler_v4')
logger.info("Multi-threaded PDF Form Filler v4 starting")

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
    FormField = None

# PDF processing imports
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

# AI integrations
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

@dataclass
class DocumentSource:
    """Container for a document source"""
    name: str
    content: str
    file_path: Optional[str] = None
    extraction_method: Optional[str] = None
    character_count: int = 0

@dataclass
class ExtractionResult:
    """Result from AI extraction of a single document"""
    document_name: str
    extracted_data: Dict[str, str]
    confidence_scores: Dict[str, float]
    processing_time: float
    token_count: Optional[int] = None
    extraction_method: str = "ai"

@dataclass  
class MergedResult:
    """Final merged result from multiple documents"""
    merged_data: Dict[str, str]
    confidence_scores: Dict[str, float]
    source_mapping: Dict[str, str]  # field -> source document
    total_fields: int
    processing_summary: Dict[str, Any]

class MultiThreadedDocumentProcessor:
    """Enhanced processor that handles multiple documents in parallel"""
    
    def __init__(self, api_key: str, model: str, provider: str = "claude"):
        self.api_key = api_key
        self.model = model
        self.provider = provider
        self.max_workers = 3  # Limit concurrent API calls
        
    def process_documents_parallel(self, documents: List[DocumentSource], 
                                 form_fields: List[FormField]) -> MergedResult:
        """Process multiple documents in parallel and merge results"""
        print(f"\n🔄 MULTI-THREADED PROCESSING STARTED")
        print(f"=" * 60)
        print(f"📊 Processing {len(documents)} documents with {self.max_workers} workers")
        print(f"🎯 Target fields: {len(form_fields)}")
        print(f"🤖 AI Provider: {self.provider}")
        
        start_time = time.time()
        extraction_results = []
        
        # Process documents in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all document processing tasks
            future_to_doc = {
                executor.submit(self._process_single_document, doc, form_fields): doc 
                for doc in documents
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_doc):
                doc = future_to_doc[future]
                try:
                    result = future.result()
                    extraction_results.append(result)
                    print(f"✅ Completed: {doc.name} ({len(result.extracted_data)} fields)")
                except Exception as e:
                    print(f"❌ Failed: {doc.name} - {str(e)}")
                    # Create empty result for failed document
                    extraction_results.append(ExtractionResult(
                        document_name=doc.name,
                        extracted_data={},
                        confidence_scores={},
                        processing_time=0,
                        extraction_method="failed"
                    ))
        
        # Merge all results intelligently
        merged_result = self._merge_extraction_results(extraction_results, form_fields)
        
        total_time = time.time() - start_time
        print(f"\n🎉 MULTI-THREADED PROCESSING COMPLETED")
        print(f"⏱️  Total time: {total_time:.2f}s")
        print(f"📊 Final result: {merged_result.total_fields} fields from {len(documents)} documents")
        
        return merged_result
    
    def _process_single_document(self, document: DocumentSource, 
                               form_fields: List[FormField]) -> ExtractionResult:
        """Process a single document with focused AI analysis"""
        print(f"\n🔍 Processing: {document.name}")
        print(f"   📄 Content: {len(document.content)} characters")
        
        start_time = time.time()
        
        try:
            # Create document-specific prompt
            prompt = self._create_focused_prompt(document, form_fields)
            
            # Call AI with document-specific context
            extracted_data, confidence_scores = self._call_ai_for_document(prompt, document.name)
            
            processing_time = time.time() - start_time
            
            result = ExtractionResult(
                document_name=document.name,
                extracted_data=extracted_data,
                confidence_scores=confidence_scores,
                processing_time=processing_time,
                extraction_method=self.provider
            )
            
            print(f"   ✅ Extracted {len(extracted_data)} fields in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            print(f"   ❌ Error processing {document.name}: {str(e)}")
            return ExtractionResult(
                document_name=document.name,
                extracted_data={},
                confidence_scores={},
                processing_time=time.time() - start_time,
                extraction_method="failed"
            )
    
    def _create_focused_prompt(self, document: DocumentSource, 
                             form_fields: List[FormField]) -> str:
        """Create a focused prompt for a single document"""
        
        field_names = [f.name for f in form_fields]
        
        # Determine document type for specialized extraction
        doc_type = self._classify_document_type(document)
        
        prompt = f"""You are a legal document analyst focusing on SINGLE-DOCUMENT TARGETED EXTRACTION.

🎯 CURRENT TASK: Analyze ONLY this specific document and extract relevant data.

📄 DOCUMENT TO ANALYZE:
   Name: {document.name}
   Type: {doc_type}
   Content: {len(document.content)} characters

🔍 EXTRACTION STRATEGY for {doc_type.upper()}:

{self._get_document_specific_strategy(doc_type)}

📋 TARGET FORM FIELDS:
{json.dumps(field_names, indent=2)}

📄 DOCUMENT CONTENT:
{document.content}

🎯 EXTRACTION INSTRUCTIONS:

1. **FOCUS ON THIS DOCUMENT ONLY** - Extract data that exists in this specific document
2. **DOCUMENT-TYPE AWARENESS** - Use specialized knowledge for {doc_type} documents  
3. **TARGETED EXTRACTION** - Only extract fields that make sense for this document type
4. **QUALITY OVER QUANTITY** - Extract accurate data rather than guessing
5. **CONFIDENCE SCORING** - Higher confidence for clear, obvious data

RETURN FORMAT (JSON only):
{{
    "extracted_data": {{
        "FIELD_NAME": "EXTRACTED_VALUE [Field: FIELD_LABEL]"
    }},
    "confidence_scores": {{
        "FIELD_NAME": 0.95
    }}
}}

Extract relevant data from this {doc_type} document now."""

        return prompt
    
    def _classify_document_type(self, document: DocumentSource) -> str:
        """Classify document type based on content and filename"""
        content_lower = document.content.lower()
        name_lower = document.name.lower()
        
        # Financial document indicators
        if ('fl-142' in name_lower or 'schedule of assets' in content_lower or 
            'student loans' in content_lower or 'credit cards' in content_lower):
            return 'financial_schedule'
            
        # Attorney/legal document indicators  
        elif ('fl-120' in name_lower or 'attorney or party without attorney' in content_lower or
              'telephone no' in content_lower):
            return 'attorney_legal'
            
        # Court filing indicators
        elif ('superior court' in content_lower or 'case number' in content_lower or
              'petitioner' in content_lower):
            return 'court_filing'
            
        # Default
        else:
            return 'general_legal'
    
    def _get_document_specific_strategy(self, doc_type: str) -> str:
        """Get extraction strategy based on document type"""
        strategies = {
            'financial_schedule': """
**FINANCIAL DOCUMENT STRATEGY:**
- Focus on monetary amounts, debts, assets
- Extract student loans, credit cards, bank accounts
- Look for property values, vehicle values
- Extract total debt and asset calculations
- Financial dates and account details""",
            
            'attorney_legal': """
**ATTORNEY/LEGAL DOCUMENT STRATEGY:**  
- Focus on attorney contact information
- Extract phone numbers, email addresses
- Look for law firm names and addresses
- Case numbers and court information
- Legal party names (petitioner/respondent)""",
            
            'court_filing': """
**COURT FILING STRATEGY:**
- Focus on case identification information
- Extract court names and locations
- Party names and relationships
- Filing dates and case numbers
- Legal status and proceedings""",
            
            'general_legal': """
**GENERAL LEGAL STRATEGY:**
- Extract any contact information
- Look for names, dates, locations
- Financial information if present
- Case or matter identifiers"""
        }
        
        return strategies.get(doc_type, strategies['general_legal'])
    
    def _call_ai_for_document(self, prompt: str, doc_name: str) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Call AI API for a specific document"""
        try:
            if self.provider == "claude" or self.provider == "anthropic":
                return self._call_claude(prompt, doc_name)
            elif self.provider == "openai":
                return self._call_openai(prompt, doc_name)
            else:
                print(f"   ⚠️ Unknown provider {self.provider}, using pattern matching")
                return {}, {}
                
        except Exception as e:
            print(f"   ❌ AI call failed for {doc_name}: {str(e)}")
            return {}, {}
    
    def _call_claude(self, prompt: str, doc_name: str) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Call Claude API for document processing"""
        try:
            # Try llm_client first
            import llm_client
            os.environ["ANTHROPIC_API_KEY"] = self.api_key.strip()
            response_text = llm_client.generate_with_claude(self.model, prompt)
            
        except ImportError:
            # Fallback to direct API
            client = anthropic.Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = response.content[0].text
        
        return self._parse_ai_response(response_text)
    
    def _call_openai(self, prompt: str, doc_name: str) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Call OpenAI API for document processing"""
        try:
            # Try llm_client first
            import llm_client  
            os.environ["OPENAI_API_KEY"] = self.api_key.strip()
            response_text = llm_client.generate_with_openai(self.model, prompt)
            
        except ImportError:
            # Fallback to direct API
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000
            )
            response_text = response.choices[0].message.content
        
        return self._parse_ai_response(response_text)
    
    def _parse_ai_response(self, response_text: str) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Parse AI response to extract data and confidence scores"""
        try:
            # Find JSON in response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_text = response_text[start:end]
                result = json.loads(json_text)
                
                extracted_data = result.get("extracted_data", {})
                confidence_scores = result.get("confidence_scores", {})
                
                # Generate default confidence if missing
                if extracted_data and not confidence_scores:
                    confidence_scores = {k: 0.8 for k in extracted_data.keys()}
                
                return extracted_data, confidence_scores
            else:
                return {}, {}
                
        except json.JSONDecodeError:
            return {}, {}
    
    def _merge_extraction_results(self, results: List[ExtractionResult], 
                                form_fields: List[FormField]) -> MergedResult:
        """Intelligently merge results from multiple documents"""
        print(f"\n🔗 MERGING RESULTS FROM {len(results)} DOCUMENTS")
        print("=" * 50)
        
        merged_data = {}
        confidence_scores = {}
        source_mapping = {}
        
        # Get all unique fields across all results
        all_fields = set()
        for result in results:
            all_fields.update(result.extracted_data.keys())
        
        print(f"📊 Total unique fields found: {len(all_fields)}")
        
        # For each field, pick the best data from all sources
        for field in all_fields:
            best_value = ""
            best_confidence = 0.0
            best_source = ""
            
            print(f"\n🔍 Merging field: {field}")
            
            # Check each document result
            for result in results:
                if field in result.extracted_data:
                    value = result.extracted_data[field]
                    confidence = result.confidence_scores.get(field, 0.0)
                    
                    print(f"   📄 {result.document_name}: '{value}' (confidence: {confidence:.2f})")
                    
                    # Choose best based on confidence and value quality
                    if self._is_better_value(value, confidence, best_value, best_confidence):
                        best_value = value
                        best_confidence = confidence
                        best_source = result.document_name
                        print(f"   ✅ New best value from {best_source}")
            
            if best_value:
                merged_data[field] = best_value
                confidence_scores[field] = best_confidence
                source_mapping[field] = best_source
                print(f"   🎯 Final: '{best_value}' from {best_source}")
        
        # Create processing summary
        processing_summary = {
            "documents_processed": len(results),
            "successful_documents": len([r for r in results if r.extraction_method != "failed"]),
            "total_processing_time": sum(r.processing_time for r in results),
            "document_results": [
                {
                    "name": r.document_name,
                    "fields_extracted": len(r.extracted_data),
                    "processing_time": r.processing_time,
                    "method": r.extraction_method
                }
                for r in results
            ]
        }
        
        result = MergedResult(
            merged_data=merged_data,
            confidence_scores=confidence_scores,
            source_mapping=source_mapping,
            total_fields=len(merged_data),
            processing_summary=processing_summary
        )
        
        print(f"\n🎉 MERGE COMPLETED")
        print(f"📊 Final merged result: {len(merged_data)} fields")
        print(f"📄 Source distribution:")
        source_counts = {}
        for source in source_mapping.values():
            source_counts[source] = source_counts.get(source, 0) + 1
        for source, count in source_counts.items():
            print(f"   {source}: {count} fields")
        
        return result
    
    def _is_better_value(self, new_value: str, new_confidence: float,
                        current_value: str, current_confidence: float) -> bool:
        """Determine if new value is better than current best"""
        
        # If no current value, new is better
        if not current_value:
            return bool(new_value)
        
        # If new value is empty, current is better
        if not new_value:
            return False
        
        # Strongly prefer higher confidence
        if new_confidence > current_confidence + 0.1:
            return True
        if current_confidence > new_confidence + 0.1:
            return False
        
        # Similar confidence - prefer longer, more detailed values
        if len(new_value) > len(current_value) * 1.5:
            return True
        
        # Prefer values with monetary amounts for financial fields
        if '$' in new_value and '$' not in current_value:
            return True
        
        # Prefer contact info (email, phone) for contact fields
        if '@' in new_value or '(' in new_value:
            return True
        
        # Default to current value
        return False


class PDFFormFillerV4(QMainWindow):
    """Enhanced PDF Form Filler with multi-threaded document processing"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI PDF Form Filler v4 - Multi-Threaded")
        self.setGeometry(100, 100, 1400, 900)
        
        # Initialize data
        self.form_fields = []
        self.form_file_path = ""
        self.sources = []  # DocumentSource objects
        self.api_key = ""
        self.model = "claude-3-5-sonnet-20240620"
        self.provider = "claude"
        
        # Multi-threading components
        self.processor = None
        
        self.init_ui()
        self.load_settings()
        
        print("🚀 PDF Form Filler v4 initialized with multi-threaded processing")
    
    def init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("🤖 AI PDF Form Filler v4 - Multi-Threaded Processing")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel for form and sources
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel for AI processing
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([700, 700])
        
        # Status bar
        self.status_label = QLabel("Ready - Multi-threaded processing enabled")
        layout.addWidget(self.status_label)
        
    def create_left_panel(self):
        """Create left panel with form loading and source management"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Form loading section
        form_group = QGroupBox("📄 Target PDF Form")
        form_layout = QVBoxLayout(form_group)
        
        load_form_btn = QPushButton("📁 Load PDF Form")
        load_form_btn.clicked.connect(self.load_pdf_form)
        form_layout.addWidget(load_form_btn)
        
        self.form_path_label = QLabel("No form loaded")
        form_layout.addWidget(self.form_path_label)
        
        self.fields_label = QLabel("Fields: 0")
        form_layout.addWidget(self.fields_label)
        
        layout.addWidget(form_group)
        
        # Sources section  
        sources_group = QGroupBox("📚 Source Documents")
        sources_layout = QVBoxLayout(sources_group)
        
        # Source buttons
        btn_layout = QHBoxLayout()
        
        add_pdf_btn = QPushButton("➕ PDF")
        add_pdf_btn.clicked.connect(self.add_pdf_source)
        btn_layout.addWidget(add_pdf_btn)
        
        add_text_btn = QPushButton("➕ Text")
        add_text_btn.clicked.connect(self.add_text_source)
        btn_layout.addWidget(add_text_btn)
        
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.clicked.connect(self.clear_sources)
        btn_layout.addWidget(clear_btn)
        
        sources_layout.addLayout(btn_layout)
        
        # Sources list
        self.sources_list = QListWidget()
        sources_layout.addWidget(self.sources_list)
        
        layout.addWidget(sources_group)
        
        return widget
    
    def create_right_panel(self):
        """Create right panel for AI processing and results"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # AI Configuration
        ai_group = QGroupBox("🤖 AI Configuration")
        ai_layout = QGridLayout(ai_group)
        
        # Provider selection
        ai_layout.addWidget(QLabel("Provider:"), 0, 0)
        
        self.provider_claude = QRadioButton("Claude (Anthropic)")
        self.provider_claude.setChecked(True)
        self.provider_claude.toggled.connect(self.update_provider)
        ai_layout.addWidget(self.provider_claude, 0, 1)
        
        self.provider_openai = QRadioButton("OpenAI")
        self.provider_openai.toggled.connect(self.update_provider)
        ai_layout.addWidget(self.provider_openai, 0, 2)
        
        # API Key
        ai_layout.addWidget(QLabel("API Key:"), 1, 0)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.textChanged.connect(self.update_api_key)
        ai_layout.addWidget(self.api_key_input, 1, 1, 1, 2)
        
        # Model selection
        ai_layout.addWidget(QLabel("Model:"), 2, 0)
        self.model_combo = QComboBox()
        self.model_combo.currentTextChanged.connect(self.update_model)
        ai_layout.addWidget(self.model_combo, 2, 1, 1, 2)
        
        self.update_model_list()
        
        layout.addWidget(ai_group)
        
        # Processing section
        process_group = QGroupBox("⚙️ Multi-Threaded Processing")
        process_layout = QVBoxLayout(process_group)
        
        # Processing options
        options_layout = QHBoxLayout()
        
        options_layout.addWidget(QLabel("Max Workers:"))
        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 5)
        self.workers_spin.setValue(3)
        options_layout.addWidget(self.workers_spin)
        
        options_layout.addStretch()
        
        self.parallel_check = QCheckBox("Parallel Processing")
        self.parallel_check.setChecked(True)
        options_layout.addWidget(self.parallel_check)
        
        process_layout.addLayout(options_layout)
        
        # Extract button
        self.extract_btn = QPushButton("🚀 Extract Data (Multi-Threaded)")
        self.extract_btn.clicked.connect(self.extract_data_threaded)
        self.extract_btn.setMinimumHeight(40)
        process_layout.addWidget(self.extract_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        process_layout.addWidget(self.progress_bar)
        
        layout.addWidget(process_group)
        
        # Results section
        results_group = QGroupBox("📊 Extraction Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QPlainTextEdit()
        self.results_text.setFont(QFont("Courier", 10))
        results_layout.addWidget(self.results_text)
        
        # Fill form button
        self.fill_btn = QPushButton("📝 Fill PDF Form")
        self.fill_btn.clicked.connect(self.fill_pdf_form)
        self.fill_btn.setEnabled(False)
        results_layout.addWidget(self.fill_btn)
        
        layout.addWidget(results_group)
        
        return widget
    
    def load_pdf_form(self):
        """Load target PDF form"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF Form", "", "PDF Files (*.pdf)"
        )
        
        if file_path:
            self.form_file_path = file_path
            self.form_path_label.setText(f"Form: {os.path.basename(file_path)}")
            
            # Extract form fields
            self.extract_form_fields()
            
    def extract_form_fields(self):
        """Extract fillable fields from PDF form"""
        try:
            result = subprocess.run(
                ["pdftk", self.form_file_path, "dump_data_fields"],
                capture_output=True, text=True, check=True
            )
            
            fields = self.parse_pdftk_fields(result.stdout)
            self.form_fields = fields
            self.fields_label.setText(f"Fields: {len(fields)}")
            
            print(f"✅ Extracted {len(fields)} form fields")
            
        except subprocess.CalledProcessError as e:
            QMessageBox.warning(self, "Error", f"Failed to extract form fields: {e}")
            self.form_fields = []
    
    def parse_pdftk_fields(self, pdftk_output: str) -> List[FormField]:
        """Parse pdftk field dump output"""
        fields = []
        current_field = {}
        
        for line in pdftk_output.strip().split('\n'):
            if line.startswith('FieldName:'):
                if current_field:
                    if FIELD_MAPPING_AVAILABLE:
                        field = FormField(
                            name=current_field.get('name', ''),
                            field_type=current_field.get('type', 'text'),
                            alt_text=current_field.get('alt_text', ''),
                            value=current_field.get('value', ''),
                            options=current_field.get('options', [])
                        )
                    else:
                        # Simple dict-based field for compatibility
                        field = {
                            'name': current_field.get('name', ''),
                            'type': current_field.get('type', 'text'),
                            'alt_text': current_field.get('alt_text', ''),
                            'value': current_field.get('value', ''),
                            'options': current_field.get('options', [])
                        }
                    fields.append(field)
                
                current_field = {'name': line.split(':', 1)[1].strip()}
                
            elif line.startswith('FieldType:'):
                current_field['type'] = line.split(':', 1)[1].strip()
            elif line.startswith('FieldValue:'):
                current_field['value'] = line.split(':', 1)[1].strip()
            elif line.startswith('FieldStateOption:'):
                if 'options' not in current_field:
                    current_field['options'] = []
                current_field['options'].append(line.split(':', 1)[1].strip())
        
        # Add the last field
        if current_field:
            if FIELD_MAPPING_AVAILABLE:
                field = FormField(
                    name=current_field.get('name', ''),
                    field_type=current_field.get('type', 'text'),
                    alt_text=current_field.get('alt_text', ''),
                    value=current_field.get('value', ''),
                    options=current_field.get('options', [])
                )
            else:
                field = {
                    'name': current_field.get('name', ''),
                    'type': current_field.get('type', 'text'),
                    'alt_text': current_field.get('alt_text', ''),
                    'value': current_field.get('value', ''),
                    'options': current_field.get('options', [])
                }
            fields.append(field)
        
        return fields
    
    def add_pdf_source(self):
        """Add PDF source document"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Source PDF", "", "PDF Files (*.pdf)"
        )
        
        if file_path:
            self.add_source_document(file_path, 'pdf')
    
    def add_text_source(self):
        """Add text source through input dialog"""
        text, ok = QInputDialog.getMultiLineText(
            self, "Add Text Source", "Enter text content:"
        )
        
        if ok and text.strip():
            source = DocumentSource(
                name=f"Text Input {len(self.sources) + 1}",
                content=text.strip(),
                character_count=len(text.strip()),
                extraction_method="manual"
            )
            self.sources.append(source)
            self.update_sources_display()
    
    def add_source_document(self, file_path: str, doc_type: str):
        """Add a document source"""
        try:
            print(f"📄 Adding {doc_type} source: {os.path.basename(file_path)}")
            
            # Extract text content
            content = self.extract_text_from_file(file_path)
            
            if content:
                source = DocumentSource(
                    name=os.path.basename(file_path),
                    content=content,
                    file_path=file_path,
                    character_count=len(content),
                    extraction_method="auto"
                )
                self.sources.append(source)
                self.update_sources_display()
                
                print(f"✅ Added source: {len(content)} characters")
            else:
                QMessageBox.warning(self, "Error", f"Could not extract text from {file_path}")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to add source: {str(e)}")
    
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from various file types"""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.pdf':
                return self._extract_from_pdf(file_path)
            elif ext in ['.txt', '.md']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                return f"[Unsupported file type: {ext}]"
                
        except Exception as e:
            return f"[Error reading file: {str(e)}]"
    
    def _extract_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using available libraries"""
        text_content = []
        
        # Try PyPDF2 first
        if HAS_PYPDF2:
            try:
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    for page in reader.pages:
                        text = page.extract_text()
                        if text.strip():
                            text_content.append(text)
                
                if text_content:
                    extracted_text = "\\n\\n".join(text_content)
                    print(f"✅ PyPDF2 extracted {len(extracted_text)} characters")
                    return extracted_text
                    
            except Exception as e:
                print(f"PyPDF2 extraction failed: {e}")
        
        # Try pdfplumber as fallback
        if HAS_PDFPLUMBER:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            text_content.append(text)
                
                if text_content:
                    extracted_text = "\\n\\n".join(text_content)
                    print(f"✅ pdfplumber extracted {len(extracted_text)} characters")
                    return extracted_text
                    
            except Exception as e:
                print(f"pdfplumber extraction failed: {e}")
        
        return "[PDF text extraction failed - no libraries available]"
    
    def clear_sources(self):
        """Clear all source documents"""
        self.sources = []
        self.update_sources_display()
    
    def update_sources_display(self):
        """Update the sources list display"""
        self.sources_list.clear()
        
        for i, source in enumerate(self.sources):
            item_text = f"{i+1}. {source.name} ({source.character_count:,} chars)"
            self.sources_list.addItem(item_text)
        
        print(f"📚 Total sources: {len(self.sources)}")
    
    def update_provider(self):
        """Update AI provider and model list"""
        if self.provider_claude.isChecked():
            self.provider = "claude"
        elif self.provider_openai.isChecked():
            self.provider = "openai"
        
        self.update_model_list()
    
    def update_model_list(self):
        """Update model dropdown based on provider"""
        self.model_combo.clear()
        
        if self.provider == "claude":
            models = [
                "claude-3-5-sonnet-20240620",
                "claude-3-opus-20240229", 
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307"
            ]
        elif self.provider == "openai":
            models = [
                "gpt-4o",
                "gpt-4-turbo",
                "gpt-4",
                "gpt-3.5-turbo"
            ]
        else:
            models = ["None"]
        
        self.model_combo.addItems(models)
        if models:
            self.model = models[0]
    
    def update_api_key(self):
        """Update API key"""
        self.api_key = self.api_key_input.text().strip()
    
    def update_model(self):
        """Update selected model"""
        self.model = self.model_combo.currentText()
    
    def extract_data_threaded(self):
        """Extract data using multi-threaded processing"""
        try:
            # Validation
            if not self.form_fields:
                QMessageBox.warning(self, "No Form", "Please load a PDF form first.")
                return
            
            if not self.sources:
                QMessageBox.warning(self, "No Sources", "Please add source documents.")
                return
            
            if not self.api_key:
                QMessageBox.warning(self, "No API Key", "Please enter an API key.")
                return
            
            # Create processor
            self.processor = MultiThreadedDocumentProcessor(
                api_key=self.api_key,
                model=self.model,
                provider=self.provider
            )
            
            # Update max workers from UI
            self.processor.max_workers = self.workers_spin.value()
            
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate
            self.extract_btn.setEnabled(False)
            self.status_label.setText("Processing documents in parallel...")
            
            # Clear previous results
            self.results_text.clear()
            
            # Process documents
            if self.parallel_check.isChecked():
                self.process_parallel()
            else:
                self.process_sequential()
                
        except Exception as e:
            self.extraction_finished(None, str(e))
    
    def process_parallel(self):
        """Process documents in parallel using threading"""
        def run_processing():
            try:
                # Convert form_fields to proper format
                form_fields = []
                for field in self.form_fields:
                    if FIELD_MAPPING_AVAILABLE and hasattr(field, 'name'):
                        form_fields.append(field)
                    else:
                        # Create FormField-like object
                        form_fields.append(type('FormField', (), {
                            'name': field.get('name') if isinstance(field, dict) else str(field),
                            'field_type': field.get('type', 'text') if isinstance(field, dict) else 'text',
                            'alt_text': field.get('alt_text', '') if isinstance(field, dict) else ''
                        })())
                
                # Process with multi-threading
                result = self.processor.process_documents_parallel(self.sources, form_fields)
                
                # Signal completion on main thread
                QTimer.singleShot(0, lambda: self.extraction_finished(result, None))
                
            except Exception as e:
                QTimer.singleShot(0, lambda: self.extraction_finished(None, str(e)))
        
        # Run in background thread
        thread = threading.Thread(target=run_processing)
        thread.daemon = True
        thread.start()
    
    def process_sequential(self):
        """Process documents sequentially (fallback mode)"""
        def run_processing():
            try:
                # Simple sequential processing
                all_extracted = {}
                all_confidence = {}
                
                for source in self.sources:
                    print(f"Processing {source.name} sequentially...")
                    
                    # Use first document approach but one at a time
                    processor = MultiThreadedDocumentProcessor(
                        api_key=self.api_key,
                        model=self.model, 
                        provider=self.provider
                    )
                    
                    form_fields = []
                    for field in self.form_fields:
                        if FIELD_MAPPING_AVAILABLE and hasattr(field, 'name'):
                            form_fields.append(field)
                        else:
                            form_fields.append(type('FormField', (), {
                                'name': field.get('name') if isinstance(field, dict) else str(field),
                                'field_type': field.get('type', 'text') if isinstance(field, dict) else 'text'
                            })())
                    
                    single_result = processor._process_single_document(source, form_fields)
                    
                    # Merge results
                    for field, value in single_result.extracted_data.items():
                        if field not in all_extracted or single_result.confidence_scores.get(field, 0) > all_confidence.get(field, 0):
                            all_extracted[field] = value
                            all_confidence[field] = single_result.confidence_scores.get(field, 0.8)
                
                # Create merged result
                result = MergedResult(
                    merged_data=all_extracted,
                    confidence_scores=all_confidence,
                    source_mapping={field: "sequential" for field in all_extracted},
                    total_fields=len(all_extracted),
                    processing_summary={"mode": "sequential", "documents": len(self.sources)}
                )
                
                QTimer.singleShot(0, lambda: self.extraction_finished(result, None))
                
            except Exception as e:
                QTimer.singleShot(0, lambda: self.extraction_finished(None, str(e)))
        
        thread = threading.Thread(target=run_processing)
        thread.daemon = True
        thread.start()
    
    def extraction_finished(self, result: Optional[MergedResult], error: Optional[str]):
        """Handle extraction completion"""
        self.progress_bar.setVisible(False)
        self.extract_btn.setEnabled(True)
        
        if error:
            self.status_label.setText(f"Error: {error}")
            QMessageBox.critical(self, "Extraction Error", f"Failed to extract data: {error}")
            return
        
        if not result:
            self.status_label.setText("No results extracted")
            return
        
        # Display results
        self.display_extraction_results(result)
        self.extracted_data = result.merged_data
        self.confidence_scores = result.confidence_scores
        
        # Enable form filling
        self.fill_btn.setEnabled(True)
        self.status_label.setText(f"Extracted {result.total_fields} fields from {result.processing_summary.get('documents_processed', 0)} documents")
    
    def display_extraction_results(self, result: MergedResult):
        """Display extraction results in the UI"""
        output = []
        output.append("🎉 MULTI-THREADED EXTRACTION RESULTS")
        output.append("=" * 60)
        output.append("")
        
        # Processing summary
        summary = result.processing_summary
        output.append("📊 PROCESSING SUMMARY:")
        output.append(f"   Documents processed: {summary.get('documents_processed', 0)}")
        output.append(f"   Successful extractions: {summary.get('successful_documents', 0)}")
        output.append(f"   Total processing time: {summary.get('total_processing_time', 0):.2f}s")
        output.append(f"   Total fields extracted: {result.total_fields}")
        output.append("")
        
        # Document breakdown
        if 'document_results' in summary:
            output.append("📄 DOCUMENT BREAKDOWN:")
            for doc_result in summary['document_results']:
                output.append(f"   {doc_result['name']}: {doc_result['fields_extracted']} fields ({doc_result['processing_time']:.2f}s)")
            output.append("")
        
        # Extracted data
        output.append("🔍 EXTRACTED DATA:")
        output.append("")
        
        for field, value in result.merged_data.items():
            confidence = result.confidence_scores.get(field, 0.0)
            source = result.source_mapping.get(field, "unknown")
            
            output.append(f"• {field}: {value}")
            output.append(f"  (confidence: {confidence:.1%}, source: {source})")
            output.append("")
        
        self.results_text.setPlainText("\\n".join(output))
        
        print(f"✅ Displayed results: {result.total_fields} fields")
    
    def fill_pdf_form(self):
        """Fill the PDF form with extracted data"""
        if not hasattr(self, 'extracted_data') or not self.extracted_data:
            QMessageBox.warning(self, "No Data", "Please extract data first.")
            return
        
        if not self.form_file_path:
            QMessageBox.warning(self, "No Form", "Please load a PDF form first.")
            return
        
        try:
            # Create temporary FDF file
            fdf_content = self.create_fdf_data(self.extracted_data)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.fdf', delete=False) as fdf_file:
                fdf_file.write(fdf_content)
                fdf_path = fdf_file.name
            
            # Get output file path
            output_path, _ = QFileDialog.getSaveFileName(
                self, "Save Filled Form", 
                os.path.splitext(self.form_file_path)[0] + "_filled.pdf",
                "PDF Files (*.pdf)"
            )
            
            if output_path:
                # Fill form using pdftk
                subprocess.run([
                    "pdftk", self.form_file_path,
                    "fill_form", fdf_path,
                    "output", output_path,
                    "flatten"
                ], check=True)
                
                # Clean up
                os.unlink(fdf_path)
                
                QMessageBox.information(self, "Success", f"Form filled and saved to:\\n{output_path}")
                self.status_label.setText(f"Form filled successfully: {os.path.basename(output_path)}")
            
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Failed to fill form: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unexpected error: {e}")
    
    def create_fdf_data(self, data: Dict[str, str]) -> str:
        """Create FDF data for form filling"""
        fdf_content = [
            "%FDF-1.2",
            "1 0 obj",
            "<<",
            "/FDF << /Fields ["
        ]
        
        for field_name, value in data.items():
            # Extract actual value from formatted result
            actual_value = value
            if " [Field: " in value:
                actual_value = value.split(" [Field: ")[0]
            
            # Escape special characters
            escaped_value = actual_value.replace('(', '\\(').replace(')', '\\)')
            fdf_content.append(f"<< /T ({field_name}) /V ({escaped_value}) >>")
        
        fdf_content.extend([
            "] >>",
            ">>",
            "endobj",
            "trailer",
            "<<",
            "/Root 1 0 R",
            ">>",
            "%%EOF"
        ])
        
        return "\\n".join(fdf_content)
    
    def load_settings(self):
        """Load application settings"""
        settings = QSettings("PDFFormFiller", "v4")
        
        # Load API keys from environment or settings
        self.api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY") or settings.value("api_key", "")
        if self.api_key:
            self.api_key_input.setText(self.api_key)
        
        # Load other settings
        provider = settings.value("provider", "claude")
        if provider == "openai":
            self.provider_openai.setChecked(True)
        else:
            self.provider_claude.setChecked(True)
        
        model = settings.value("model", "claude-3-5-sonnet-20240620")
        if model:
            self.model = model
            self.update_model_list()
            index = self.model_combo.findText(model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
    
    def save_settings(self):
        """Save application settings"""
        settings = QSettings("PDFFormFiller", "v4")
        settings.setValue("api_key", self.api_key)
        settings.setValue("provider", self.provider)
        settings.setValue("model", self.model)
    
    def closeEvent(self, event):
        """Handle application close"""
        self.save_settings()
        event.accept()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("PDF Form Filler v4")
    app.setApplicationVersion("4.0")
    app.setOrganizationName("AI Tools")
    
    # Create and show main window
    window = PDFFormFillerV4()
    window.show()
    
    print("🚀 PDF Form Filler v4 with Multi-Threaded Processing started")
    print("📋 Features:")
    print("   • Parallel document processing")
    print("   • Intelligent result merging")
    print("   • Document-type specific extraction")
    print("   • Enhanced confidence scoring")
    print("   • Source attribution")
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
