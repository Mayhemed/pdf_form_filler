# main_app.py

import sys
import os
import json
import logging
from typing import List, Dict
from collections import Counter

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QFileDialog, QLabel, QLineEdit, QTextEdit, QTabWidget,
    QMessageBox, QProgressBar, QGroupBox, QListWidget, QRadioButton, QComboBox,
    QDialog, QDialogButtonBox, QInputDialog
)
from PyQt6.QtCore import Qt

# Local imports from our new refactored files
from models import FormField, DataSource
from extractors import PDFFieldExtractor, AIDataExtractor
from filler import PDFFormFiller

try:
    from fieldmappingwidget import FieldMappingWidget
    FIELD_MAPPING_AVAILABLE = True
except ImportError:
    FIELD_MAPPING_AVAILABLE = False
    class FieldMappingWidget(QWidget): # Placeholder if not found
        def __init__(self): super().__init__(); layout = QVBoxLayout(self); layout.addWidget(QLabel("FieldMappingWidget not found."))
        def set_fields(self, fields): pass
        def get_field_data(self): return {}
        def set_field_data(self, data): pass

logger = logging.getLogger('PDF_Form_Filler')

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_pdf_path, self.form_fields, self.ai_data_sources = "", [], []
        self.fieldname_to_number_map, self.number_to_fieldname_map = {}, {}
        self.settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf_filler_settings.json")
        
        # Create status_label early to avoid access errors during settings load
        self.status_label = QLabel("Ready")
        
        # Now it's safe to load settings and initialize UI
        self.load_settings()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("PDF Form Filler - Universal v4.3") 
        self.setGeometry(100, 100, 1200, 800)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.addWidget(self._create_file_selection_area())
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        self.tab_widget = QTabWidget()
        if FIELD_MAPPING_AVAILABLE:
            self.field_mapping_widget = FieldMappingWidget()
            self.tab_widget.addTab(self.field_mapping_widget, "Field Mapping")
            
        # Create all UI components first
        self.tab_widget.addTab(self._create_ai_extraction_tab(), "AI Data Extraction")
        
        # Apply saved settings after ALL UI is created
        self.apply_saved_settings()
        layout.addWidget(self.tab_widget)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.fill_form_btn = QPushButton("Fill PDF Form")
        self.fill_form_btn.clicked.connect(self.fill_form)
        self.fill_form_btn.setEnabled(False)
        btn_layout.addWidget(self.fill_form_btn)
        layout.addLayout(btn_layout)
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

    def _create_file_selection_area(self):
        container = QGroupBox("1. Form & Map Selection")
        layout = QVBoxLayout(container)
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("Target PDF:"))
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        target_layout.addWidget(self.file_path_edit)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_pdf)
        target_layout.addWidget(browse_btn)
        layout.addLayout(target_layout)
        map_layout = QHBoxLayout()
        map_layout.addWidget(QLabel("Numbered Map PDF:"))
        self.mapping_pdf_path_edit = QLineEdit()
        self.mapping_pdf_path_edit.setReadOnly(True)
        self.mapping_pdf_path_edit.setPlaceholderText("Optional, but highly recommended for accuracy")
        map_layout.addWidget(self.mapping_pdf_path_edit)
        browse_map_btn = QPushButton("Browse Map")
        browse_map_btn.clicked.connect(self.browse_mapping_pdf)
        map_layout.addWidget(browse_map_btn)
        layout.addLayout(map_layout)
        return container

    def _create_ai_extraction_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        provider_group = QGroupBox("2. AI Provider & Data Sources")
        provider_layout = QVBoxLayout(provider_group)
        self.ai_provider_radios = {"openai": QRadioButton("OpenAI"), "anthropic": QRadioButton("Anthropic Claude")}
        
        # Create the model combo box BEFORE connecting signals
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.ai_model_combo = QComboBox()
        model_layout.addWidget(self.ai_model_combo)
        
        # Now it's safe to connect signals
        for r in self.ai_provider_radios.values():
            provider_layout.addWidget(r)
            r.toggled.connect(self._update_ai_model_list)
        self.ai_provider_radios["anthropic"].setChecked(True)
        
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("API Key:"))
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        key_layout.addWidget(self.api_key_edit)
        provider_layout.addLayout(key_layout)
        provider_layout.addLayout(model_layout)
        sources_layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        for text, method in [("Add File(s)", self.add_ai_file_source), ("Add Text", self.add_ai_text_source)]:
            btn = QPushButton(text)
            btn.clicked.connect(method)
            btn_layout.addWidget(btn)
        btn_layout.addStretch()
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_ai_sources)
        btn_layout.addWidget(clear_btn)
        sources_layout.addLayout(btn_layout)
        self.sources_list = QListWidget()
        self.sources_list.setMaximumHeight(100)
        sources_layout.addWidget(self.sources_list)
        provider_layout.addLayout(sources_layout)
        layout.addWidget(provider_group)
        
        # Add prompt editor section between data sources and extraction button
        prompt_group = QGroupBox("3. Extraction Prompt")
        prompt_layout = QVBoxLayout(prompt_group)
        
        prompt_label = QLabel("Edit the AI extraction prompt before submitting:")
        prompt_layout.addWidget(prompt_label)
        
        self.prompt_editor = QTextEdit()
        self.prompt_editor.setPlaceholderText("AI extraction prompt will appear here when you click Extract Data...")
        
        # Use monospace font for better readability
        font = self.prompt_editor.font()
        font.setFamily("Courier New")
        font.setPointSize(10)
        self.prompt_editor.setFont(font)
        
        prompt_layout.addWidget(self.prompt_editor)
        
        # Add prompt management buttons
        prompt_btn_layout = QHBoxLayout()
        reset_prompt_btn = QPushButton("Reset to Default")
        reset_prompt_btn.clicked.connect(self.reset_prompt)
        save_prompt_btn = QPushButton("Save Prompt")
        save_prompt_btn.clicked.connect(self.save_prompt_to_file)
        load_prompt_btn = QPushButton("Load Prompt")
        load_prompt_btn.clicked.connect(self.load_prompt_from_file)
        
        prompt_btn_layout.addWidget(reset_prompt_btn)
        prompt_btn_layout.addWidget(save_prompt_btn)
        prompt_btn_layout.addWidget(load_prompt_btn)
        prompt_layout.addLayout(prompt_btn_layout)
        
        layout.addWidget(prompt_group)
        
        extract_group = QGroupBox("4. Run Extraction")
        extract_layout = QVBoxLayout(extract_group)
        self.ai_extract_btn = QPushButton("Extract Data")
        self.ai_extract_btn.clicked.connect(self.extract_with_ai)
        extract_layout.addWidget(self.ai_extract_btn)
        self.ai_results = QTextEdit()
        self.ai_results.setReadOnly(True)
        self.ai_results.setPlaceholderText("AI extraction results will appear here...")
        extract_layout.addWidget(self.ai_results)
        layout.addWidget(extract_group)
        self._update_ai_model_list()
        return tab

    def load_settings(self):
        """Load saved settings from a JSON file, including paths and other preferences."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    
                # Load target PDF path
                self.current_pdf_path = settings.get('target_pdf_path', '')
                
                # Load mapping PDF path
                self.mapping_pdf_path = settings.get('mapping_pdf_path', '')
                
                # Load API key (with caution)
                api_key = settings.get('api_key', '')
                
                # Load AI provider preference
                ai_provider = settings.get('ai_provider', 'anthropic')
                
                # Load data sources if available
                data_sources = settings.get('data_sources', [])
                if data_sources:
                    logger.info(f"Found {len(data_sources)} saved data sources")
                
                logger.info(f"Loaded settings with target PDF: {os.path.basename(self.current_pdf_path) if self.current_pdf_path else 'None'}")
                logger.info(f"Loaded settings with mapping PDF: {os.path.basename(self.mapping_pdf_path) if self.mapping_pdf_path else 'None'}")
                
                return settings
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return {}
    
    def save_settings(self):
        """Save current settings to a JSON file for persistence between app restarts."""
        try:
            # Serialize data sources without duplicating file content
            serialized_sources = []
            for source in self.ai_data_sources:
                # Only save file paths and metadata, not content for files
                if source.source_type == 'file':
                    serialized_sources.append({
                        'name': source.name,
                        'source_type': source.source_type,
                        'content': source.content  # For files, this is just the path
                    })
                elif source.source_type == 'text' and len(source.content) < 1000:
                    # For text sources, only save if reasonably small
                    serialized_sources.append({
                        'name': source.name,
                        'source_type': source.source_type,
                        'content': source.content
                    })
            
            settings = {
                'target_pdf_path': self.current_pdf_path,
                'mapping_pdf_path': self.mapping_pdf_path_edit.text(),
                'ai_provider': next((name for name, radio in self.ai_provider_radios.items() if radio.isChecked()), 'anthropic'),
                'api_key': self.api_key_edit.text(),
                'data_sources': serialized_sources
            }
            
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
                
            logger.info(f"Settings saved to {self.settings_file} with {len(serialized_sources)} data sources")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False
    
    def browse_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Target PDF", "", "PDF Files (*.pdf)")
        if path:
            self.current_pdf_path = path
            self.file_path_edit.setText(path)
            self.extract_fields()
            self.save_settings()  # Save settings after changing the path

    def browse_mapping_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Numbered Mapping PDF", "", "PDF Files (*.pdf)")
        if path:
            self.mapping_pdf_path_edit.setText(path)
            self.save_settings()  # Save settings after changing the path

    def apply_saved_settings(self):
        """Apply the saved settings to the UI components."""
        try:
            # Apply target PDF path if available
            if self.current_pdf_path and os.path.exists(self.current_pdf_path):
                self.file_path_edit.setText(self.current_pdf_path)
                logger.info(f"Restored target PDF path: {self.current_pdf_path}")
                
                # If we have a PDF path, also load its fields
                if self.current_pdf_path.lower().endswith('.pdf'):
                    self.extract_fields()
            
            # Apply mapping PDF path if available
            settings = self.load_settings()  # Reload to get any settings that might have been missed
            mapping_path = settings.get('mapping_pdf_path', '')
            if mapping_path and os.path.exists(mapping_path):
                self.mapping_pdf_path_edit.setText(mapping_path)
                logger.info(f"Restored mapping PDF path: {mapping_path}")
            
            # Apply AI provider preference if available
            ai_provider = settings.get('ai_provider', 'anthropic')
            if ai_provider in self.ai_provider_radios:
                self.ai_provider_radios[ai_provider].setChecked(True)
                logger.info(f"Restored AI provider preference: {ai_provider}")
            # Apply API key if available
            api_key = settings.get('api_key', '')
            if api_key:
                self.api_key_edit.setText(api_key)
                logger.info("Restored API key from settings")
            
            # Restore data sources if available
            data_sources = settings.get('data_sources', [])
            if data_sources:
                # Clear existing sources first
                self.clear_ai_sources()
                
                # Add each saved source
                restored_count = 0
                for source_data in data_sources:
                    try:
                        source_type = source_data.get('source_type')
                        source_content = source_data.get('content')
                        source_name = source_data.get('name')
                        
                        if source_type == 'file' and os.path.exists(source_content):
                            # For files, check if they still exist
                            self.ai_data_sources.append(DataSource(source_name, source_type, source_content))
                            self.sources_list.addItem(f"File: {os.path.basename(source_content)}")
                            restored_count += 1
                        elif source_type == 'text' and source_content:
                            # For text sources
                            self.ai_data_sources.append(DataSource(source_name, source_type, source_content))
                            self.sources_list.addItem(f"Text: {len(source_content)} chars")
                            restored_count += 1
                    except Exception as e:
                        logger.error(f"Error restoring data source: {e}")
                
                logger.info(f"Restored {restored_count} data sources from settings")
                
                
        except Exception as e:
            logger.error(f"Error applying saved settings: {e}")
    
    def extract_fields(self):
        if not self.current_pdf_path:
            return
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Extracting form fields...")
        self.field_extractor = PDFFieldExtractor(self.current_pdf_path)
        self.field_extractor.fields_extracted.connect(self.on_fields_extracted)
        self.field_extractor.error_occurred.connect(self.on_error)
        self.field_extractor.start()

    def on_fields_extracted(self, fields: List[FormField]):
        self.progress_bar.setVisible(False)
        self.field_mapping_widget.set_fields(fields)
        self.form_fields = fields
        self.fieldname_to_number_map = {field.name: i + 1 for i, field in enumerate(fields)}
        self.number_to_fieldname_map = {i + 1: field.name for i, field in enumerate(fields)}
        self.fill_form_btn.setEnabled(True)
        self.status_label.setText(f"Ready - Found {len(fields)} fields and created number map.")
        logger.info(f"Successfully extracted {len(fields)} fields and created number map.")

    def add_ai_file_source(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Data Source Files", "", "PDF, Text (*.pdf *.txt)")
        for path in paths:
            self.ai_data_sources.append(DataSource(os.path.basename(path), 'file', path))
            self.sources_list.addItem(f"File: {os.path.basename(path)}")

    def add_ai_text_source(self):
        text, ok = QInputDialog.getMultiLineText(self, "Add Text Source", "Paste text content:")
        if ok and text:
            self.ai_data_sources.append(DataSource("Pasted Text", 'text', text))
            self.sources_list.addItem(f"Text: {len(text)} chars")

    def clear_ai_sources(self):
        self.sources_list.clear()
        self.ai_data_sources.clear()

    def _update_ai_model_list(self):
        self.ai_model_combo.clear()
        if self.ai_provider_radios["openai"].isChecked():
            self.ai_model_combo.addItems(["gpt-4o", "gpt-4-turbo"])
        elif self.ai_provider_radios["anthropic"].isChecked():
            self.ai_model_combo.addItems(["claude-3-5-sonnet-20240620", "claude-3-opus-20240229"])
            
    def reset_prompt(self):
        """Reset the prompt editor to the default prompt template"""
        try:
            # Get basic form information for placeholders
            target_form_name = os.path.basename(self.current_pdf_path) if self.current_pdf_path else "target form"
            mapping_form_name = os.path.basename(self.mapping_pdf_path_edit.text()) if self.mapping_pdf_path_edit.text() else "(Not provided)"
            
            # Create a prompt template using the user's preferred format with placeholders
            default_prompt = f"""You are an expert AI data extraction agent for a universal PDF form filling system. Your task is to extract information from multiple source documents to fill a specific target PDF form. Follow these instructions carefully:

1. Target Form:
The target form you will be filling is:
<target_form>
{target_form_name}
</target_form>

2. Field Mapping:
Use this field mapping table for correct field mapping:
<field_mapping_table>
The numbered mapping PDF ({mapping_form_name}) shows the EXACT field numbers and field labels.
CRITICAL: Each field number must contain EXACTLY the type of data indicated by its label:
- Field #1 is "Attorney or Party Without Attorney" and should contain attorney name, firm, address, etc.
- Field #2 is "ATTORNEY FOR (Name)" and should contain who the attorney represents
- Field #3 is "COURT COUNTY" and should contain only the county name (e.g., "LOS ANGELES")
- Field #4 is "STREET ADDRESS" and should contain the court street address
- Field #5 is "MAILING ADDRESS" and should contain a mailing address if different
- Field #6 is "CITY AND ZIP CODE" and should contain city and zip (e.g., "Los Angeles, 90012")
- Field #7 is "BRANCH NAME" and should contain court branch name (e.g., "Central District")
- Field #8 is "PETITIONER/PLAINTIFF" and should contain petitioner's full name
- Field #9 is "RESPONDENT/DEFENDANT" and should contain respondent's full name
- Field #10 is "CASE NUMBER" and should contain only the case number
|
DO NOT mix up these fields! For example, DO NOT put a person's name in the "CITY AND ZIP CODE" field,
and DO NOT put an address in the "ATTORNEY FOR" field.
|
IMPORTANT: Use EXACTLY these field numbers as the keys in your JSON response.
DO NOT extract data FROM the mapping PDF - it just shows the field numbering and labels.
</field_mapping_table>

3. Output Format:
Return a single, clean JSON object with the field numbers as keys (not field names). Include an "extracted_data" object and a "confidence_scores" object. For example:

```json
{{
    "extracted_data": {{
        "1": "ExtractedValue1",
        "2": "ExtractedValue2"
    }},
    "confidence_scores": {{
        "1": 0.95,
        "2": 0.99
    }}
}}
```

**CRITICAL SUCCESS REQUIREMENTS:**

1. **ANALYZE ALL DOCUMENTS COMPLETELY:** You MUST thoroughly process EVERY document - not just the first or second one
2. **BE PRECISE:** Extract exact values as they appear in the source documents
3. **MAP ACCURATELY:** Ensure extracted values are mapped to the correct field numbers
4. **EXTRACT ALL DATES AND NAMES:** Always capture ALL dates, names and numbers mentioned in the documents
"""
            # Set the prompt in the editor
            self.prompt_editor.setPlainText(default_prompt)
            logger.info("Reset prompt to default template")
            
        except Exception as e:
            logger.error(f"Error resetting prompt: {e}")
            QMessageBox.warning(self, "Error", f"Could not reset prompt: {str(e)}")
    
    def save_prompt_to_file(self):
        """Save the current prompt to a file"""
        try:
            # Get the prompt text
            prompt_text = self.prompt_editor.toPlainText()
            if not prompt_text.strip():
                QMessageBox.warning(self, "Empty Prompt", "Cannot save an empty prompt.")
                return
                
            # Export to file
            self.export_template_to_file(prompt_text)
            
        except Exception as e:
            logger.error(f"Error saving prompt: {e}")
            QMessageBox.warning(self, "Error", f"Could not save prompt: {str(e)}")
    
    def load_prompt_from_file(self):
        """Load a prompt from a file"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Prompt Template File", "", "Text Files (*.txt)"
            )
            if file_path:
                # Load the file
                with open(file_path, 'r', encoding='utf-8') as f:
                    prompt_text = f.read()
                    
                # Set the prompt in the editor
                self.prompt_editor.setPlainText(prompt_text)
                logger.info(f"Loaded prompt from file: {file_path}")
                
        except Exception as e:
            logger.error(f"Error loading prompt: {e}")
            QMessageBox.warning(self, "Error", f"Could not load prompt: {str(e)}")

    class PromptEditorDialog(QDialog):
        """Memory-safe dialog for editing AI extraction prompts."""
        def __init__(self, parent=None, prompt="", title="Edit AI Extraction Prompt"):
            super().__init__(parent)
            self.setWindowTitle(title)
            self.resize(1000, 800)  # Larger size for better editing
            self.current_prompt = prompt  # Store the prompt text separately
            self.update_timer = None      # Timer for delayed updates
            
            # Main layout
            layout = QVBoxLayout(self)
            
            # Status bar at top for immediate feedback
            status_layout = QHBoxLayout()
            self.char_count_label = QLabel(f"Character count: {len(prompt):,}")
            status_layout.addWidget(self.char_count_label)
            
            self.size_warning_label = QLabel("")
            self.size_warning_label.setStyleSheet("color: red;")
            status_layout.addWidget(self.size_warning_label)
            status_layout.addStretch()
            layout.addLayout(status_layout)
            
            # Create the main editor in a group box
            editor_group = QGroupBox("Prompt Editor")
            editor_layout = QVBoxLayout(editor_group)
            
            # Create a more memory-efficient text editor
            # Use a plain QTextEdit with optimized settings
            self.prompt_editor = QTextEdit()
            self.prompt_editor.setPlainText(prompt)
            self.prompt_editor.setAcceptRichText(False)  # Disable rich text for better performance
            self.prompt_editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
            self.prompt_editor.setTabChangesFocus(True)  # Tab changes focus instead of inserting tabs
            
            # Set a monospace font for better editing
            font = self.prompt_editor.font()
            font.setFamily("Courier New")
            font.setPointSize(12)
            self.prompt_editor.setFont(font)
            
            # Defer text change events to avoid excessive processing
            self.prompt_editor.textChanged.connect(self.queue_update)
            
            editor_layout.addWidget(self.prompt_editor)
            layout.addWidget(editor_group, 1)  # Give editor more space
            
            # Add placeholder insertion section
            placeholder_group = QGroupBox("Insert Template Placeholders")
            placeholder_layout = QVBoxLayout(placeholder_group)
            
            # Create a grid for placeholders
            placeholder_grid = QHBoxLayout()
            
            # Modern placeholders matching the template format
            placeholders = [
                "<target_form>",
                "</target_form>",
                "<field_mapping_table>",
                "</field_mapping_table>",
                "<field_names>",
                "</field_names>",
                "<source_documents>",
                "</source_documents>"
            ]
            
            # Create buttons in two rows for better layout
            for placeholder in placeholders:
                btn = QPushButton(placeholder)
                # Use functools.partial for safer slot connections
                btn.clicked.connect(lambda checked=False, p=placeholder: self.insert_placeholder(p))
                placeholder_grid.addWidget(btn)
            
            placeholder_layout.addLayout(placeholder_grid)
            
            # Add a help label
            placeholder_help = QLabel(
                "Use these tags to create placeholders for dynamic content in your prompt.\n"
                "The system will replace these with actual data at runtime."
            )
            placeholder_help.setStyleSheet("font-style: italic; color: #666;")
            placeholder_layout.addWidget(placeholder_help)
            
            layout.addWidget(placeholder_group)
            
            # Add safety instructions
            instructions = QLabel(
                "MEMORY SAFETY TIPS:\n"
                "• Keep prompt length under 30,000 characters\n"
                "• Use small edits rather than complete rewrites\n"
                "• If you experience crashes, try editing in smaller sections\n"
                "• Save your work regularly using the template feature"
            )
            instructions.setStyleSheet("background-color: #fff0f0; padding: 10px; border-radius: 5px; font-weight: bold;")
            layout.addWidget(instructions)
            
            # Dialog buttons
            button_layout = QHBoxLayout()
            
            # Add template management
            template_btn_group = QGroupBox("Template Management")
            template_btn_layout = QHBoxLayout(template_btn_group)
            
            self.save_template_btn = QPushButton("Save Template")
            self.save_template_btn.setToolTip("Save this prompt as a template for future use")
            self.save_template_btn.clicked.connect(self.save_template)
            template_btn_layout.addWidget(self.save_template_btn)
            
            self.load_template_btn = QPushButton("Load Template")
            self.load_template_btn.setToolTip("Load a previously saved prompt template")
            self.load_template_btn.clicked.connect(self.load_template)
            template_btn_layout.addWidget(self.load_template_btn)
            
            button_layout.addWidget(template_btn_group)
            button_layout.addStretch()
            
            # Standard dialog buttons
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(self.validate_and_accept)
            buttons.rejected.connect(self.reject)
            button_layout.addWidget(buttons)
            
            layout.addLayout(button_layout)
            
            # Initialize status
            self.update_status(check_tags=False)
            
        def queue_update(self):
            """Queue a delayed update to avoid excessive processing."""
            # Cancel any pending update
            if self.update_timer is not None:
                self.update_timer = None
                
            # Get the current text safely
            try:
                # This is a potentially expensive operation, but we're deferring it
                current_text = self.prompt_editor.toPlainText()
                # Update the character count immediately for responsiveness
                char_count = len(current_text)
                self.char_count_label.setText(f"Character count: {char_count:,}")
                
                # Update warning based on size
                if char_count > 50000:
                    self.size_warning_label.setText("⚠️ DANGER: Extremely large prompt!")
                    self.size_warning_label.setStyleSheet("color: red; font-weight: bold;")
                elif char_count > 30000:
                    self.size_warning_label.setText("⚠️ Warning: Large prompt")
                    self.size_warning_label.setStyleSheet("color: orange;")
                else:
                    self.size_warning_label.setText("✓ Size OK")
                    self.size_warning_label.setStyleSheet("color: green;")
                    
                # Store the current text safely
                self.current_prompt = current_text
                
            except Exception as e:
                logger.error(f"Error in queue_update: {e}", exc_info=True)
                self.size_warning_label.setText("⚠️ Error updating")
                self.size_warning_label.setStyleSheet("color: red;")
        
        def update_status(self, check_tags=True):
            """Update status information about the prompt."""
            try:
                # Get character count
                char_count = len(self.current_prompt)
                self.char_count_label.setText(f"Character count: {char_count:,}")
                
                # Check for warning conditions
                if char_count > 50000:
                    self.size_warning_label.setText("⚠️ DANGER: Extremely large prompt!")
                    self.size_warning_label.setStyleSheet("color: red; font-weight: bold;")
                elif char_count > 30000:
                    self.size_warning_label.setText("⚠️ Warning: Large prompt")
                    self.size_warning_label.setStyleSheet("color: orange;")
                else:
                    self.size_warning_label.setText("✓ Size OK")
                    self.size_warning_label.setStyleSheet("color: green;")
                
            except Exception as e:
                logger.error(f"Error updating status: {e}", exc_info=True)
                
        def insert_placeholder(self, placeholder):
            """Insert a placeholder at the current cursor position."""
            try:
                # Insert text at cursor position
                self.prompt_editor.insertPlainText(placeholder)
                # Update the stored prompt text
                self.current_prompt = self.prompt_editor.toPlainText()
                # Update status
                self.update_status()
            except Exception as e:
                logger.error(f"Error inserting placeholder: {e}", exc_info=True)
                QMessageBox.warning(self, "Error", f"Failed to insert placeholder: {str(e)}")
            
        def validate_and_accept(self):
            """Validate the prompt before accepting."""
            try:
                # Get current text
                current_text = self.prompt_editor.toPlainText()
                char_count = len(current_text)
                
                # Warn about very large prompts
                if char_count > 50000:
                    result = QMessageBox.warning(
                        self,
                        "Memory Safety Warning",
                        f"Your prompt is extremely large ({char_count:,} characters) and may cause crashes.\n\n"
                        "Consider reducing the size or splitting into multiple extractions.\n\n"
                        "Do you want to continue anyway?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    
                    if result == QMessageBox.StandardButton.No:
                        return
                
                # Store the final text
                self.current_prompt = current_text
                
                # Accept the dialog
                self.accept()
                
            except Exception as e:
                logger.error(f"Error validating prompt: {e}", exc_info=True)
                QMessageBox.critical(self, "Error",
                                    f"An error occurred validating the prompt: {str(e)}\n"
                                    "Please try with a smaller prompt.")
            
        def get_prompt(self):
            """Return the edited prompt with safety checks."""
            try:
                # Use the stored prompt text rather than getting it from the widget again
                # This avoids potential memory issues during dialog closure
                prompt = self.current_prompt
                
                # Ensure the text is valid UTF-8
                safe_prompt = prompt.encode('utf-8', errors='replace').decode('utf-8')
                return safe_prompt
            except Exception as e:
                logger.error(f"Error getting prompt: {e}", exc_info=True)
                # Return a safe version if there are encoding issues
                return self.current_prompt.encode('ascii', errors='replace').decode('ascii')
            
        def save_template(self):
            """Save the current prompt as a template with proper error handling."""
            try:
                # Get template name
                name, ok = QInputDialog.getText(self, "Template Name", "Enter template name:")
                if not ok or not name:
                    return
                
                # Create templates directory
                templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt_templates")
                os.makedirs(templates_dir, exist_ok=True)
                
                # Create file path
                template_file = os.path.join(templates_dir, f"{name}.txt")
                
                # Check for overwrite
                if os.path.exists(template_file):
                    result = QMessageBox.question(
                        self,
                        "Template Exists",
                        f"Template '{name}' already exists. Do you want to overwrite it?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if result == QMessageBox.StandardButton.No:
                        return
                
                # Save the template in chunks to avoid memory issues
                with open(template_file, 'w', encoding='utf-8') as f:
                    # Use the stored prompt text which is safer
                    f.write(self.current_prompt)
                
                QMessageBox.information(self, "Success", f"Template '{name}' saved successfully.")
                
            except Exception as e:
                logger.error(f"Error saving template: {e}", exc_info=True)
                QMessageBox.warning(self, "Error", f"Failed to save template: {str(e)}")
                
        def load_template(self):
            """Load a saved prompt template with proper error handling."""
            try:
                # Create templates directory
                templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt_templates")
                os.makedirs(templates_dir, exist_ok=True)
                
                # Get template list
                templates = [f[:-4] for f in os.listdir(templates_dir) if f.endswith('.txt')]
                if not templates:
                    QMessageBox.information(self, "No Templates", "No saved templates found.")
                    return
                
                # Select template
                template_name, ok = QInputDialog.getItem(
                    self, "Select Template", "Choose a template to load:", templates, 0, False
                )
                if not ok or not template_name:
                    return
                    
                template_file = os.path.join(templates_dir, f"{template_name}.txt")
                
                # Confirm replacement if needed
                current_text = self.prompt_editor.toPlainText()
                if current_text.strip():
                    result = QMessageBox.question(
                        self,
                        "Replace Current Prompt",
                        "This will replace your current prompt content. Continue?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if result == QMessageBox.StandardButton.No:
                        return
                
                # Load the template safely in chunks
                with open(template_file, 'r', encoding='utf-8') as f:
                    prompt = f.read()
                
                # Update the UI
                self.prompt_editor.setPlainText(prompt)
                self.current_prompt = prompt
                
                # Update status
                self.update_status()
                
            except Exception as e:
                logger.error(f"Error loading template: {e}", exc_info=True)
                QMessageBox.warning(self, "Error", f"Failed to load template: {str(e)}")

    def extract_with_ai(self):
        """Extract data from source documents using AI to fill PDF form fields"""
        # Validate requirements
        if not self.form_fields:
            return QMessageBox.warning(self, "No Form", "Load a target PDF form first.")
        if not self.ai_data_sources:
            return QMessageBox.warning(self, "No Sources", "Add at least one data source.")
        
        # Get the selected AI provider
        provider = [p for p, r in self.ai_provider_radios.items() if r.isChecked()][0]
        
        try:
            # Show progress information
            self.status_label.setText("Preparing AI extraction...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)
            
            # Create the AI extractor instance
            self.ai_extractor = AIDataExtractor(
                self.ai_data_sources,
                self.form_fields,
                provider,
                self.api_key_edit.text(),
                self.ai_model_combo.currentText(),
                self.mapping_pdf_path_edit.text(),
                self.fieldname_to_number_map
            )
            
            # Set the target form path for context
            self.ai_extractor.target_form_path = self.current_pdf_path
            logger.info(f"Setting target form path for AI extraction: {self.current_pdf_path}")
            
            # Reset the prompt editor with default template
            self.reset_prompt()
            self.progress_bar.setValue(20)
            
            # Show confirmation dialog
            result = QMessageBox.question(
                self,
                "Ready to Extract",
                "The extraction prompt has been loaded into the editor.\n\n"
                "1. Review and edit the prompt as needed\n"
                "2. Click 'Yes' when ready to start extraction\n"
                "3. Click 'No' to cancel",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if result == QMessageBox.StandardButton.No:
                self.progress_bar.setVisible(False)
                self.status_label.setText("AI extraction canceled")
                return
                
            # Get the edited prompt from the editor
            prompt_text = self.prompt_editor.toPlainText()
            if not prompt_text.strip():
                QMessageBox.warning(self, "Empty Prompt", "Cannot extract with an empty prompt.")
                self.progress_bar.setVisible(False)
                return
                
            # Set the prompt on the extractor (with safety encoding)
            sanitized_prompt = prompt_text.encode('utf-8', errors='replace').decode('utf-8')
            self.ai_extractor.custom_prompt = sanitized_prompt
            logger.info(f"Using user-edited prompt ({len(sanitized_prompt)} chars)")
            
            # Update progress
            self.progress_bar.setValue(40)
            self.status_label.setText("Starting AI extraction...")
            self.ai_extract_btn.setEnabled(False)
            
            # Count PDF files for user feedback
            pdf_sources = [source for source in self.ai_data_sources
                          if source.source_type == 'file' and source.content.lower().endswith('.pdf')]
            
            # Show PDF processing message in UI
            if pdf_sources:
                pdf_names = [os.path.basename(source.content) for source in pdf_sources]
                pdf_list = ", ".join(pdf_names[:3])
                if len(pdf_names) > 3:
                    pdf_list += f" and {len(pdf_names) - 3} more"
                self.status_label.setText(f"Processing {len(pdf_sources)} PDF(s): {pdf_list}")
                self.ai_results.setPlainText(f"AI EXTRACTION IN PROGRESS\n\nProcessing these PDFs:\n" +
                                           "\n".join([f"- {os.path.basename(s.content)}" for s in pdf_sources]) +
                                           "\n\nUsing model: " + self.ai_model_combo.currentText() +
                                           "\n\nThis may take several minutes...")
            else:
                self.status_label.setText("Processing text sources only (no PDFs)")
            
            # Connect signals
            self.ai_extractor.data_extracted.connect(self.on_ai_data_extracted)
            self.ai_extractor.error_occurred.connect(self.on_error)
            self.ai_extractor.progress_updated.connect(self.on_progress_update)
            
            # Start the extraction thread
            self.ai_extractor.start()
            logger.info(f"Started AI extraction with provider: {provider}, model: {self.ai_model_combo.currentText()}")
            
        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR in AI extraction: {e}", exc_info=True)
            self.on_error(f"Error processing extraction: {str(e)}\nTry simplifying the prompt or removing special formatting.")
            self.progress_bar.setVisible(False)
            self.ai_extract_btn.setEnabled(True)

    def on_ai_data_extracted(self, data: dict, conf: dict):
        """Process AI extraction results with improved handling of field names to numbers conversion"""
        self.progress_bar.setVisible(False)
        self.ai_extract_btn.setEnabled(True)
        try:
            logger.info(f"Processing AI extraction results")
            
            # Initialize containers
            translated_data = {}  # Will store field_name -> value
            numbered_data = {}    # Will store field_number -> value (for display)
            confidence_scores = {}  # Will store field_name -> confidence
            extraction_data = {}  # Will store field_number -> value
            unmapped_data = {}  # Anything that couldn't be mapped
            
            # Get the extracted_data from the structure
            if "extracted_data" in data and isinstance(data["extracted_data"], dict):
                # The AI returned the expected structure with extracted_data
                logger.info("Found structured response with extracted_data")
                extraction_data = data["extracted_data"]
            else:
                # The AI returned a flat structure - use it directly
                logger.warning("AI response missing 'extracted_data' object - using flat structure")
                extraction_data = data
            
            # Get confidence scores if available
            ai_confidence = {}
            if "confidence_scores" in data and isinstance(data["confidence_scores"], dict):
                logger.info("Found confidence_scores in AI response")
                ai_confidence = data["confidence_scores"]
            else:
                logger.info("No confidence scores provided by AI. Creating default values.")
            
            # Track counts for logging
            number_key_count = 0
            fieldname_key_count = 0
            
            # Create a reverse mapping for field name lookup
            field_name_to_number = {}
            for field in self.form_fields:
                # Strip any extra formatting/paths from field names for more flexible matching
                simple_name = field.name.split('.')[-1].strip('[]0123456789')
                field_name_to_number[field.name] = self.fieldname_to_number_map.get(field.name)
                # Also add a simplified version for more flexible matching
                if simple_name:
                    field_name_to_number[simple_name] = self.fieldname_to_number_map.get(field.name)
            
            # Process all data points with better field name handling
            for key, val in extraction_data.items():
                # Skip empty values
                if val is None or val == "":
                    continue
                
                # Get the actual value (handle nested structures)
                if isinstance(val, dict) and "value" in val:
                    actual_value = val["value"]
                else:
                    actual_value = val
                
                # Track if we've found a mapping
                mapped = False
                field_name = None
                field_number = None
                
                try:
                    # APPROACH 1: Key is already a number
                    field_number = int(key)
                    number_key_count += 1
                    
                    # Look up the field name using the number
                    if field_number in self.number_to_fieldname_map:
                        field_name = self.number_to_fieldname_map[field_number]
                        mapped = True
                        logger.debug(f"Direct number match: {field_number} -> '{field_name}'")
                except (ValueError, TypeError):
                    # Not a number key, continue to other approaches
                    pass
                
                if not mapped:
                    # APPROACH 2: Key is a direct field name match
                    if key in self.fieldname_to_number_map:
                        field_name = key
                        field_number = self.fieldname_to_number_map[key]
                        mapped = True
                        fieldname_key_count += 1
                        logger.debug(f"Direct field name match: '{key}' -> {field_number}")
                
                if not mapped:
                    # APPROACH 3: Key exists in our fields list
                    for field in self.form_fields:
                        if key == field.name:
                            field_name = field.name
                            field_number = self.fieldname_to_number_map.get(field_name)
                            if field_number:
                                mapped = True
                                fieldname_key_count += 1
                                logger.debug(f"Field list match: '{key}' -> {field_number}")
                                break
                
                if not mapped:
                    # APPROACH 4: Fuzzy matching for field names
                    # Try to extract the base field name without indices
                    base_key = key.split('.')[-1]  # Get the last part after the dot
                    base_key = ''.join([c for c in base_key if not c.isdigit() and c not in '[]'])
                    
                    for field_name, number in self.fieldname_to_number_map.items():
                        if base_key in field_name:
                            field_number = number
                            mapped = True
                            fieldname_key_count += 1
                            logger.debug(f"Fuzzy field name match: '{key}' -> {field_number} (via {field_name})")
                            break
                
                # If we found a mapping, store it
                if mapped and field_name and field_number:
                    translated_data[field_name] = actual_value
                    numbered_data[str(field_number)] = actual_value
                    
                    # Add confidence score
                    if str(field_number) in ai_confidence:
                        confidence_scores[field_name] = ai_confidence[str(field_number)]
                    else:
                        confidence_scores[field_name] = 0.8
                else:
                    # No mapping found
                    unmapped_data[key] = actual_value
                    logger.warning(f"Could not map key: '{key}'")
            
            # Log statistics about the extraction
            logger.info(f"Translation stats: {number_key_count} numbered keys, {fieldname_key_count} field name keys, {len(unmapped_data)} unmapped keys")
            
            # Apply the data to form fields
            self.field_mapping_widget.set_field_data(translated_data)
            
            # Add debugging logs to help diagnose extraction issues
            logger.info(f"Filled {len(translated_data)} out of {len(self.form_fields)} form fields")
            logger.info(f"Most common field types extracted: {', '.join([f[0] for f in Counter([f.split('.')[-1][:4] for f in translated_data.keys()]).most_common(5)])}")
            
            # Create a more informative results display
            fill_rate = len(translated_data) / len(self.form_fields) if self.form_fields else 0
            result_text = f"EXTRACTION RESULTS: {len(translated_data)} fields filled ({fill_rate:.1%} of form)\n\n"
            
            # Show source PDFs that were used
            pdf_sources = [source.content for source in self.ai_data_sources
                          if source.source_type == 'file' and source.content.lower().endswith('.pdf')]
            if pdf_sources:
                result_text += "Source PDFs:\n"
                for pdf in pdf_sources:
                    result_text += f"- {os.path.basename(pdf)}\n"
                result_text += "\n"
            
            # Add a mapping of common form field numbers to their semantic names
            # This helps connect field numbers to their actual meaning on the form
            semantic_field_names = {
                # Common legal form field labels - these are examples and should match actual form fields
                "1": "Attorney or Party Without Attorney",
                "2": "ATTORNEY FOR (Name)",
                "3": "COURT COUNTY",
                "4": "STREET ADDRESS",
                "5": "MAILING ADDRESS",
                "6": "CITY AND ZIP CODE",
                "7": "BRANCH NAME",
                "8": "PETITIONER/PLAINTIFF",
                "9": "RESPONDENT/DEFENDANT",
                "10": "CASE NUMBER",
                "11": "Real estate/Current gross market value",
                # Add other known semantic field names based on the form's printed labels
            }
            
            # Display NUMBERED data with SEMANTIC FIELD TITLES for better readability
            # Generate field titles combining both semantic names and technical extraction
            field_titles = {}
            for field_name in self.fieldname_to_number_map:
                field_num = self.fieldname_to_number_map[field_name]
                field_num_str = str(field_num)
                
                # Try to get a semantic name first
                if field_num_str in semantic_field_names:
                    # Use the pre-defined semantic name
                    field_titles[field_num_str] = semantic_field_names[field_num_str]
                    continue
                    
                # Try extracting a semantic title from the field name
                title = ""
                
                # Method 1: Extract from the field name directly
                parts = field_name.split('.')
                if parts:
                    # Take the last part and clean it up
                    raw_title = parts[-1]
                    
                    # Remove common prefixes/suffixes
                    prefixes = ['txt', 'cb', 'rb', 'tf', 'df', 'btn', 'lbl']
                    for prefix in prefixes:
                        if raw_title.lower().startswith(prefix):
                            raw_title = raw_title[len(prefix):]
                    
                    # Strip any digits, brackets, etc.
                    raw_title = ''.join([c for c in raw_title if not c.isdigit() and c not in '[](){}'])
                    
                    # Replace camelCase with spaces
                    import re
                    title = re.sub(r'([a-z])([A-Z])', r'\1 \2', raw_title)
                    
                    # Clean up any other issues
                    title = title.replace('_', ' ').strip()
                
                # Try method 2 only if method 1 didn't produce a useful title
                if len(title) <= 2:
                    # Look for meaningful segments in the full field name
                    segments = re.findall(r'[A-Z][a-z]+', field_name)
                    if segments:
                        title = ' '.join(segments)
                
                # Method 3: If still nothing useful, try to infer from field type hints
                if not title or len(title) <= 2:
                    if 'date' in field_name.lower():
                        title = 'Date field'
                    elif 'phone' in field_name.lower():
                        title = 'Phone number'
                    elif 'email' in field_name.lower():
                        title = 'Email address'
                    elif 'name' in field_name.lower():
                        title = 'Name field'
                    elif 'address' in field_name.lower():
                        title = 'Address field'
                    elif 'amount' in field_name.lower() or 'total' in field_name.lower():
                        title = 'Amount field'
                    elif 'check' in field_name.lower() or 'cb' in field_name.lower():
                        title = 'Checkbox field'
                    elif 'rb' in field_name.lower():
                        title = 'Selection field'
                    elif 'btn' in field_name.lower():
                        title = 'Button field'
                    elif 'tf' in field_name.lower() or 'text' in field_name.lower():
                        title = 'Text field'
                    else:
                        title = 'Form field'
                
                # For table fields, try to extract row/column info
                if 'table' in field_name.lower() or 'row' in field_name.lower() or 'col' in field_name.lower():
                    # Try to extract table row and column context
                    row_match = re.search(r'row[_\s]*(\d+)|r(\d+)', field_name.lower())
                    col_match = re.search(r'col[_\s]*(\d+)|c(\d+)', field_name.lower())
                    
                    if row_match and col_match:
                        row = row_match.group(1) or row_match.group(2)
                        col = col_match.group(1) or col_match.group(2)
                        title = f"Table cell (row {row}, col {col})"
                
                # Store the title if we found something
                if title:
                    field_titles[field_num_str] = title
            
            # Create a helper function to format field keys with readable titles
            def format_field_key(field_num):
                field_num_str = str(field_num)
                if field_num_str in field_titles:
                    return f"{field_num_str} ({field_titles[field_num_str]})"
                return field_num_str
            
            # Show data by confidence level using FIELD NUMBERS for output display
            result_text += "HIGH CONFIDENCE FIELDS (>0.8):\n"
            
            # Convert high confidence items to use field numbers with titles
            high_conf_numbered = {}
            for field_name, value in translated_data.items():
                if field_name in confidence_scores and confidence_scores[field_name] > 0.8:
                    # Get the field number for this field name
                    field_num = self.fieldname_to_number_map.get(field_name)
                    if field_num:
                        field_key = format_field_key(field_num)
                        high_conf_numbered[field_key] = value
            
            if high_conf_numbered:
                result_text += json.dumps(high_conf_numbered, indent=2)
            else:
                result_text += "(None)\n"
                
            result_text += "\n\nOTHER EXTRACTED FIELDS:\n"
            
            # Convert other confidence items to use field numbers with titles
            other_conf_numbered = {}
            for field_name, value in translated_data.items():
                if field_name not in confidence_scores or confidence_scores[field_name] <= 0.8:
                    # Get the field number for this field name
                    field_num = self.fieldname_to_number_map.get(field_name)
                    if field_num:
                        field_key = format_field_key(field_num)
                        other_conf_numbered[field_key] = value
            
            if other_conf_numbered:
                result_text += json.dumps(other_conf_numbered, indent=2)
            else:
                result_text += "(None)\n"
            
            # Add unmapped data if any
            if unmapped_data:
                result_text += "\n\n--- UNMAPPED DATA ---\n"
                result_text += json.dumps(unmapped_data, indent=2)
            
            self.ai_results.setPlainText(result_text)
            self.status_label.setText(f"Success! Extracted {len(translated_data)} fields ({fill_rate:.1%} fill rate)")
            logger.info(f"AI extraction complete: mapped {len(translated_data)} fields with {number_key_count} field numbers ({fill_rate:.1%} fill rate)")
        except Exception as e:
            logger.error(f"Error processing AI results: {e}", exc_info=True)
            self.on_error(f"Error processing AI results: {e}")

    def fill_form(self):
        if not self.current_pdf_path:
            return QMessageBox.warning(self, "No PDF", "Please select a target PDF file first")
        data_to_fill = self.field_mapping_widget.get_field_data()
        if not data_to_fill:
            return QMessageBox.warning(self, "No Data", "No data available to fill.")
        
        path, _ = QFileDialog.getSaveFileName(self, "Save Filled PDF", "", "PDF Files (*.pdf)")
        if path:
            self.filler = PDFFormFiller(self.current_pdf_path, data_to_fill, path)
            self.filler.form_filled.connect(self.on_form_filled)
            self.filler.error_occurred.connect(self.on_error)
            self.filler.start()
            
    def on_form_filled(self, path: str):
        self.status_label.setText(f"Successfully saved filled PDF to {path}")
        if QMessageBox.question(self, "Success", f"Saved to {path}\nOpen the file?") == QMessageBox.StandardButton.Yes:
            if sys.platform == 'darwin':
                os.system(f'open "{path}"')
            else:
                os.system(f'start "" "{path}"')
    
    def on_progress_update(self, val, msg):
        self.progress_bar.setValue(val)
        self.status_label.setText(msg)
        
    def on_error(self, msg: str):
        self.progress_bar.setVisible(False)
        self.ai_extract_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", msg)
    
    def export_template_to_file(self, template_text):
        """Export the template to a file that can be edited externally."""
        try:
            # Let user select a save location
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Template File", "", "Text Files (*.txt)"
            )
            if file_path:
                # Add .txt extension if not present
                if not file_path.lower().endswith('.txt'):
                    file_path += '.txt'
                    
                # Save the template to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(template_text)
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Template Exported",
                    f"Template successfully exported to:\n{file_path}\n\nYou can edit this file externally and load it later."
                )
                logger.info(f"Template exported to: {file_path}")
                
                return True
        except Exception as e:
            logger.error(f"Error exporting template: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Could not save template: {str(e)}")
            
        return False

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()