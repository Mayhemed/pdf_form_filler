#!/usr/bin/env python3
"""
Field Mapping Widget for PDF Form Filler
Author: Assistant
Description: Widget for mapping data to PDF form fields
"""

import sys
from typing import Dict, List
from dataclasses import dataclass
from typing import List as TypeList
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QComboBox, QCheckBox, QScrollArea
)
from PyQt6.QtCore import Qt

# Define FormField class directly to avoid circular imports
@dataclass
class FormField:
    """Form field class to avoid circular imports"""
    name: str
    field_type: str
    value: str = ""
    alt_text: str = ""
    flags: int = 0
    justification: str = "Left"
    state_options: TypeList[str] = None
    ai_suggested_value: str = ""
    confidence_score: float = 0.0
    
    def __post_init__(self):
        if self.state_options is None:
            self.state_options = []

class FieldMappingWidget(QWidget):
    """Widget for mapping data to form fields"""
    
    def __init__(self):
        super().__init__()
        self.fields = []
        self.field_widgets = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Search/filter
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search Fields:"))
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self.filter_fields)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)

        # Scroll area for fields
        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        layout.addWidget(self.scroll_area)

        self.setLayout(layout)

    def set_fields(self, fields: List[FormField]):
        """Set the form fields and create input widgets"""
        self.fields = fields
        self.field_widgets = {}
        
        # Clear existing widgets
        for i in reversed(range(self.scroll_layout.count())):
            self.scroll_layout.itemAt(i).widget().setParent(None)

        # Create widgets for each field
        for field in fields:
            group = QGroupBox(field.alt_text or field.name)
            group_layout = QGridLayout()
            
            # Field name (read-only)
            group_layout.addWidget(QLabel("Field Name:"), 0, 0)
            name_label = QLabel(field.name)
            name_label.setWordWrap(True)
            name_label.setStyleSheet("font-family: monospace; font-size: 8pt;")
            group_layout.addWidget(name_label, 0, 1)
            
            # Field type
            group_layout.addWidget(QLabel("Type:"), 1, 0)
            group_layout.addWidget(QLabel(field.field_type), 1, 1)
            
            # Value input
            group_layout.addWidget(QLabel("Value:"), 2, 0)
            
            if field.field_type == "Button" and field.state_options:
                # Dropdown for buttons with options
                widget = QComboBox()
                widget.addItem("")  # Empty option
                widget.addItems(field.state_options)
            elif field.field_type == "Button":
                # Checkbox for simple buttons
                widget = QCheckBox("Check this field")
            else:
                # Text input for other fields
                widget = QLineEdit()
                widget.setPlaceholderText("Enter value here...")
            
            group_layout.addWidget(widget, 2, 1)
            self.field_widgets[field.name] = widget
            
            group.setLayout(group_layout)
            self.scroll_layout.addWidget(group)

    def filter_fields(self, text: str):
        """Filter fields based on search text"""
        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if isinstance(widget, QGroupBox):
                visible = text.lower() in widget.title().lower()
                widget.setVisible(visible)

    def get_field_data(self) -> Dict[str, str]:
        """Get the current field data"""
        data = {}
        for field_name, widget in self.field_widgets.items():
            if isinstance(widget, QLineEdit):
                data[field_name] = widget.text()
            elif isinstance(widget, QComboBox):
                data[field_name] = widget.currentText()
            elif isinstance(widget, QCheckBox):
                data[field_name] = "1" if widget.isChecked() else ""
        return data

    def set_field_data(self, data: Dict[str, str]):
        """Set field data from a dictionary"""
        for field_name, value in data.items():
            if field_name in self.field_widgets:
                widget = self.field_widgets[field_name]
                if isinstance(widget, QLineEdit):
                    widget.setText(value)
                elif isinstance(widget, QComboBox):
                    index = widget.findText(value)
                    if index >= 0:
                        widget.setCurrentIndex(index)
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(bool(value and value != "0"))