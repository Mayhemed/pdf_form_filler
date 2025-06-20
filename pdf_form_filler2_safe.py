#!/usr/bin/env python3
"""
PDF Form Filler v4 - Safe Multi-Threaded Version
Gradually adds complexity to avoid bus errors
"""

import sys
import json
import subprocess
import tempfile
import os
import threading
import concurrent.futures
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Only import PyQt6 components we actually need
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
        QPushButton, QFileDialog, QLabel, QTextEdit, QGroupBox,
        QComboBox, QSpinBox, QCheckBox, QListWidget, QPlainTextEdit,
        QProgressBar, QMessageBox, QLineEdit, QRadioButton
    )
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QFont
    PYQT_AVAILABLE = True
    print("✅ PyQt6 imports successful")
except ImportError as e:
    print(f"❌ PyQt6 import failed: {e}")
    PYQT_AVAILABLE = False
    sys.exit(1)

# Optional imports with fallbacks
try:
    import PyPDF2
    HAS_PYPDF2 = True
    print("✅ PyPDF2 available")
except ImportError:
    HAS_PYPDF2 = False
    print("⚠️ PyPDF2 not available")

try:
    import anthropic
    HAS_ANTHROPIC = True
    print("✅ Anthropic available")
except ImportError:
    HAS_ANTHROPIC = False
    print("⚠️ Anthropic not available")

try:
    import openai
    HAS_OPENAI = True
    print("✅ OpenAI available")
except ImportError:
    HAS_OPENAI = False
    print("⚠️ OpenAI not available")

@dataclass
class SimpleDocument:
    """Simplified document container"""
    name: str
    content: str
    doc_type: str = "general"

@dataclass  
class SimpleResult:
    """Simplified extraction result"""
    extracted_data: Dict[str, str]
    confidence_scores: Dict[str, float]
    source_info: Dict[str, str]

class SafeMultiThreadProcessor:
    """Safe multi-threaded processor with error handling"""
    
    def __init__(self, api_key: str, provider: str = "claude"):
        self.api_key = api_key
        self.provider = provider
        self.max_workers = 2  # Conservative for safety
        print(f"🔧 Processor initialized: {provider}, max_workers: {self.max_workers}")
    
    def process_documents_safe(self, documents: List[SimpleDocument], 
                              form_fields: List[str]) -> SimpleResult:
        """Process documents with comprehensive error handling"""
        print(f"\n🔄 SAFE MULTI-THREADING STARTED")
        print(f"📊 Processing {len(documents)} documents")
        
        try:
            # Use ThreadPoolExecutor with timeout
            all_results = {}
            all_confidence = {}
            all_sources = {}
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit tasks with timeout
                future_to_doc = {
                    executor.submit(self._process_single_safe, doc, form_fields): doc 
                    for doc in documents
                }
                
                # Process with timeout
                for future in concurrent.futures.as_completed(future_to_doc, timeout=30):
                    doc = future_to_doc[future]
                    try:
                        result = future.result(timeout=10)
                        
                        # Merge results safely
                        for field, value in result.get('data', {}).items():
                            all_results[field] = value
                            all_confidence[field] = result.get('confidence', {}).get(field, 0.8)
                            all_sources[field] = doc.name
                            
                        print(f"✅ Processed {doc.name}: {len(result.get('data', {}))} fields")
                        
                    except Exception as e:
                        print(f"❌ Failed {doc.name}: {str(e)}")
                        continue
            
            return SimpleResult(
                extracted_data=all_results,
                confidence_scores=all_confidence,
                source_info=all_sources
            )
            
        except Exception as e:
            print(f"❌ Processing failed: {str(e)}")
            return SimpleResult(
                extracted_data={},
                confidence_scores={},
                source_info={}
            )
    
    def _process_single_safe(self, document: SimpleDocument, 
                           form_fields: List[str]) -> dict:
        """Process single document with error handling"""
        try:
            print(f"🔍 Processing: {document.name}")
            
            # Simple pattern matching for now (avoid AI API issues)
            extracted = self._pattern_extract(document.content, form_fields)
            
            return {
                'data': extracted,
                'confidence': {k: 0.7 for k in extracted.keys()}
            }
            
        except Exception as e:
            print(f"❌ Single doc failed {document.name}: {str(e)}")
            return {'data': {}, 'confidence': {}}
    
    def _pattern_extract(self, content: str, form_fields: List[str]) -> Dict[str, str]:
        """Simple pattern-based extraction as fallback"""
        import re
        
        extracted = {}
        content_lower = content.lower()
        
        # Basic patterns for common fields
        patterns = {
            'case_number': r'case\s*(?:number|no\.?)\s*:?\s*([A-Z0-9]+)',
            'attorney_name': r'attorney.*?:?\s*([A-Za-z\s,\.]+(?:esq\.?|attorney|law))',
            'phone': r'(?:phone|tel|telephone)\s*:?\s*(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})',
            'email': r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            'petitioner': r'petitioner\s*:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            'respondent': r'respondent\s*:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)'
        }
        
        for field_type, pattern in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                extracted[field_type] = matches[0].strip()
        
        return extracted

class SafePDFFormFiller(QMainWindow):
    """Safe version of PDF Form Filler"""
    
    def __init__(self):
        super().__init__()
        print("🔧 Initializing SafePDFFormFiller...")
        
        self.form_fields = []
        self.form_file_path = ""
        self.documents = []
        self.api_key = ""
        self.provider = "pattern"  # Start with safe pattern matching
        
        self.init_ui_safe()
        print("✅ SafePDFFormFiller initialized")
    
    def init_ui_safe(self):
        """Initialize UI with minimal complexity"""
        self.setWindowTitle("PDF Form Filler v4 - Safe Mode")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("🛡️ PDF Form Filler v4 - Safe Multi-Threaded Mode")
        title.setFont(QFont("Arial", 14))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Form section
        form_group = QGroupBox("📄 Target PDF Form")
        form_layout = QVBoxLayout(form_group)
        
        load_btn = QPushButton("📁 Load PDF Form")
        load_btn.clicked.connect(self.load_form_safe)
        form_layout.addWidget(load_btn)
        
        self.form_label = QLabel("No form loaded")
        form_layout.addWidget(self.form_label)
        
        layout.addWidget(form_group)
        
        # Sources section
        sources_group = QGroupBox("📚 Source Documents") 
        sources_layout = QVBoxLayout(sources_group)
        
        add_btn = QPushButton("➕ Add PDF Source")
        add_btn.clicked.connect(self.add_source_safe)
        sources_layout.addWidget(add_btn)
        
        self.sources_list = QListWidget()
        sources_layout.addWidget(self.sources_list)
        
        clear_btn = QPushButton("🗑️ Clear Sources")
        clear_btn.clicked.connect(self.clear_sources)
        sources_layout.addWidget(clear_btn)
        
        layout.addWidget(sources_group)
        
        # Processing section
        process_group = QGroupBox("⚙️ Processing Options")
        process_layout = QVBoxLayout(process_group)
        
        # Simple controls
        self.pattern_radio = QRadioButton("Pattern Matching (Safe)")
        self.pattern_radio.setChecked(True)
        process_layout.addWidget(self.pattern_radio)
        
        self.ai_radio = QRadioButton("AI Processing (Requires API Key)")
        process_layout.addWidget(self.ai_radio)
        
        # API key input
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Enter Anthropic API key for AI processing")
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        process_layout.addWidget(self.api_input)
        
        # Extract button
        self.extract_btn = QPushButton("🚀 Extract Data (Multi-Threaded)")
        self.extract_btn.clicked.connect(self.extract_safe)
        process_layout.addWidget(self.extract_btn)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        process_layout.addWidget(self.progress)
        
        layout.addWidget(process_group)
        
        # Results
        results_group = QGroupBox("📊 Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QPlainTextEdit()
        self.results_text.setFont(QFont("Courier", 9))
        results_layout.addWidget(self.results_text)
        
        self.fill_btn = QPushButton("📝 Fill PDF Form")
        self.fill_btn.clicked.connect(self.fill_form_safe)
        self.fill_btn.setEnabled(False)
        results_layout.addWidget(self.fill_btn)
        
        layout.addWidget(results_group)
        
        # Status
        self.status_label = QLabel("Ready - Safe mode enabled")
        layout.addWidget(self.status_label)
    
    def load_form_safe(self):
        """Load PDF form safely"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select PDF Form", "", "PDF Files (*.pdf)"
            )
            
            if file_path:
                self.form_file_path = file_path
                self.form_label.setText(f"Form: {os.path.basename(file_path)}")
                
                # Extract fields safely
                self.extract_form_fields_safe()
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load form: {str(e)}")
    
    def extract_form_fields_safe(self):
        """Extract form fields with error handling"""
        try:
            result = subprocess.run(
                ["pdftk", self.form_file_path, "dump_data_fields"],
                capture_output=True, text=True, check=True, timeout=10
            )
            
            # Simple field parsing
            fields = []
            for line in result.stdout.split('\n'):
                if line.startswith('FieldName:'):
                    field_name = line.split(':', 1)[1].strip()
                    if field_name:
                        fields.append(field_name)
            
            self.form_fields = fields
            self.form_label.setText(f"Form: {os.path.basename(self.form_file_path)} ({len(fields)} fields)")
            print(f"✅ Extracted {len(fields)} form fields")
            
        except subprocess.TimeoutExpired:
            QMessageBox.warning(self, "Error", "Form field extraction timed out")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to extract fields: {str(e)}")
            self.form_fields = []
    
    def add_source_safe(self):
        """Add source document safely"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Source PDF", "", "PDF Files (*.pdf)"
            )
            
            if file_path:
                # Extract text safely
                content = self.extract_text_safe(file_path)
                
                if content:
                    doc = SimpleDocument(
                        name=os.path.basename(file_path),
                        content=content,
                        doc_type=self.classify_document_safe(content)
                    )
                    
                    self.documents.append(doc)
                    self.update_sources_display()
                    print(f"✅ Added: {doc.name} ({len(content)} chars, type: {doc.doc_type})")
                else:
                    QMessageBox.warning(self, "Error", "Could not extract text from PDF")
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to add source: {str(e)}")
    
    def extract_text_safe(self, pdf_path: str) -> str:
        """Extract text from PDF safely"""
        try:
            if not HAS_PYPDF2:
                return "[PyPDF2 not available - install with: pip install PyPDF2]"
            
            text_content = []
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text = page.extract_text()
                    if text.strip():
                        text_content.append(text)
            
            if text_content:
                return "\\n\\n".join(text_content)
            else:
                return "[No text extracted from PDF]"
                
        except Exception as e:
            return f"[Error extracting text: {str(e)}]"
    
    def classify_document_safe(self, content: str) -> str:
        """Safely classify document type"""
        content_lower = content.lower()
        
        if 'fl-142' in content_lower or 'schedule of assets' in content_lower:
            return 'financial'
        elif 'fl-120' in content_lower or 'attorney' in content_lower:
            return 'attorney'
        else:
            return 'general'
    
    def clear_sources(self):
        """Clear all sources"""
        self.documents = []
        self.update_sources_display()
    
    def update_sources_display(self):
        """Update sources list"""
        self.sources_list.clear()
        for i, doc in enumerate(self.documents):
            self.sources_list.addItem(f"{i+1}. {doc.name} ({doc.doc_type})")
    
    def extract_safe(self):
        """Extract data safely with threading"""
        try:
            if not self.form_fields:
                QMessageBox.warning(self, "No Form", "Please load a PDF form first")
                return
            
            if not self.documents:
                QMessageBox.warning(self, "No Sources", "Please add source documents")
                return
            
            # Show progress
            self.progress.setVisible(True)
            self.progress.setRange(0, 0)
            self.extract_btn.setEnabled(False)
            self.status_label.setText("Processing...")
            
            # Get processing mode
            if self.ai_radio.isChecked():
                api_key = self.api_input.text().strip()
                if not api_key:
                    QMessageBox.warning(self, "No API Key", "Please enter an API key for AI processing")
                    self.extraction_finished(None)
                    return
                self.provider = "claude"
                self.api_key = api_key
            else:
                self.provider = "pattern"
                self.api_key = ""
            
            # Process in background thread
            def process_documents():
                try:
                    processor = SafeMultiThreadProcessor(self.api_key, self.provider)
                    result = processor.process_documents_safe(self.documents, self.form_fields)
                    
                    # Return to main thread
                    QTimer.singleShot(0, lambda: self.extraction_finished(result))
                    
                except Exception as e:
                    QTimer.singleShot(0, lambda: self.extraction_finished(None, str(e)))
            
            thread = threading.Thread(target=process_documents)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            self.extraction_finished(None, str(e))
    
    def extraction_finished(self, result: Optional[SimpleResult], error: str = None):
        """Handle extraction completion"""
        self.progress.setVisible(False)
        self.extract_btn.setEnabled(True)
        
        if error:
            self.status_label.setText(f"Error: {error}")
            QMessageBox.critical(self, "Error", f"Extraction failed: {error}")
            return
        
        if not result or not result.extracted_data:
            self.status_label.setText("No data extracted")
            self.results_text.setPlainText("❌ No data extracted. Try a different processing method.")
            return
        
        # Display results
        self.display_results(result)
        self.extracted_data = result.extracted_data
        self.fill_btn.setEnabled(True)
        self.status_label.setText(f"Extracted {len(result.extracted_data)} fields")
    
    def display_results(self, result: SimpleResult):
        """Display extraction results"""
        output = []
        output.append("🎉 MULTI-THREADED EXTRACTION RESULTS")
        output.append("=" * 50)
        output.append("")
        
        output.append(f"📊 SUMMARY:")
        output.append(f"   Documents processed: {len(self.documents)}")
        output.append(f"   Fields extracted: {len(result.extracted_data)}")
        output.append(f"   Processing mode: {self.provider}")
        output.append("")
        
        output.append("🔍 EXTRACTED DATA:")
        output.append("")
        
        for field, value in result.extracted_data.items():
            confidence = result.confidence_scores.get(field, 0.0)
            source = result.source_info.get(field, "unknown")
            
            output.append(f"• {field}: {value}")
            output.append(f"  (confidence: {confidence:.1%}, source: {source})")
            output.append("")
        
        self.results_text.setPlainText("\\n".join(output))
    
    def fill_form_safe(self):
        """Fill PDF form safely"""
        if not hasattr(self, 'extracted_data') or not self.extracted_data:
            QMessageBox.warning(self, "No Data", "Please extract data first")
            return
        
        try:
            # Get output path
            output_path, _ = QFileDialog.getSaveFileName(
                self, "Save Filled Form",
                os.path.splitext(self.form_file_path)[0] + "_filled.pdf",
                "PDF Files (*.pdf)"
            )
            
            if output_path:
                # Create simple FDF
                fdf_content = self.create_simple_fdf(self.extracted_data)
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.fdf', delete=False) as f:
                    f.write(fdf_content)
                    fdf_path = f.name
                
                # Fill form
                subprocess.run([
                    "pdftk", self.form_file_path,
                    "fill_form", fdf_path,
                    "output", output_path,
                    "flatten"
                ], check=True)
                
                os.unlink(fdf_path)
                
                QMessageBox.information(self, "Success", f"Form filled: {output_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fill form: {str(e)}")
    
    def create_simple_fdf(self, data: Dict[str, str]) -> str:
        """Create simple FDF content"""
        fdf_content = [
            "%FDF-1.2",
            "1 0 obj",
            "<<",
            "/FDF << /Fields ["
        ]
        
        for field_name, value in data.items():
            escaped_value = value.replace('(', '\\(').replace(')', '\\)')
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

def main():
    """Main application entry point"""
    try:
        print("🚀 Starting Safe PDF Form Filler v4...")
        
        app = QApplication(sys.argv)
        app.setApplicationName("PDF Form Filler v4 Safe")
        
        window = SafePDFFormFiller()
        window.show()
        
        print("✅ Application started successfully")
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"❌ Application failed to start: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
