# filler.py

import os
import subprocess
import tempfile
import logging
from typing import Dict
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger('PDF_Form_Filler')

class PDFFormFiller(QThread):
    """Thread for filling PDF forms using pdftk."""
    form_filled = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, pdf_path: str, data: Dict, out_path: str, flatten: bool = True):
        super().__init__()
        self.pdf_path = pdf_path
        self.data_to_fill = self._preprocess_form_data(data)
        self.output_path = out_path
        self.flatten = flatten
        
    def _preprocess_form_data(self, data: Dict) -> Dict:
        """
        Preprocess form data to handle special cases and ensure proper formatting
        """
        processed_data = {}
        
        # Log original data count
        logger.info(f"Preprocessing {len(data)} form fields")
        
        for key, value in data.items():
            # Skip empty values
            if not value or value.strip() == "":
                continue
                
            # Handle checkbox/radio fields
            if any(indicator in key for indicator in ["CheckBox", "Check", "RB", "Radio", "Choice"]):
                checkbox_values = ["X", "YES", "ON", "TRUE"]
                if isinstance(value, str) and value.strip().upper() in checkbox_values:
                    processed_data[key] = "Yes"
                    logger.debug(f"Converted checkbox field '{key}' value to 'Yes'")
                    continue
            
            # Handle decimal fields - ensure proper formatting
            if "DecimalField" in key:
                try:
                    # Clean the value and ensure it has proper decimal formatting
                    clean_value = value.strip().replace('$', '').replace(',', '')
                    if clean_value and clean_value != "0" and clean_value != "0.00":
                        # Try to parse as float and format with commas
                        numeric_value = float(clean_value)
                        formatted_value = f"{numeric_value:,.2f}"
                        processed_data[key] = formatted_value
                        logger.debug(f"Formatted decimal field '{key}' from '{value}' to '{formatted_value}'")
                        continue
                except (ValueError, TypeError):
                    # If parsing fails, use the original value
                    logger.warning(f"Could not parse decimal field '{key}' value: '{value}'")
            
            # Handle multiline text fields
            if '\n' in str(value):
                # Some PDF readers struggle with newlines in FDF
                # Replace with appropriate line breaks
                processed_value = value.replace('\n', '\r\n')
                processed_data[key] = processed_value
                logger.debug(f"Processed multiline field '{key}'")
                continue
                
            # Default case - use value as is
            processed_data[key] = value
            
        logger.info(f"Preprocessing complete: {len(processed_data)} fields after processing")
        return processed_data
    
    def run(self):
        logger.info(f"Starting PDF fill process for '{self.output_path}'")
        try:
            # Log the data we're filling with
            field_count = len(self.data_to_fill)
            logger.info(f"Filling {field_count} fields in the form")
            
            # Create a temporary FDF file to hold the data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.fdf', delete=False, encoding='utf-8') as f:
                fdf_content = self._create_fdf(self.data_to_fill)
                f.write(fdf_content)
                fdf_path = f.name
            
            logger.debug(f"Created temporary FDF file at: {fdf_path}")
            
            # Log the first few fields for debugging
            first_fields = list(self.data_to_fill.items())[:5]
            logger.info(f"Sample fields being filled: {first_fields}")
            
            # Save a copy of the FDF for debugging if needed
            debug_fdf = os.path.join(os.path.dirname(self.output_path), "debug_form_data.fdf")
            try:
                with open(debug_fdf, 'w', encoding='utf-8') as df:
                    df.write(fdf_content)
                logger.info(f"Saved debug FDF to: {debug_fdf}")
            except Exception as e:
                logger.warning(f"Could not save debug FDF: {e}")
            
            try:
                # Use pdftk to fill the form with flatten option if requested
                cmd = ['pdftk', self.pdf_path, 'fill_form', fdf_path, 'output', self.output_path]
                
                # Add flatten option if requested (makes form fields uneditable)
                if self.flatten:
                    cmd.append('flatten')
                    logger.info("Using flatten option to make form fields non-editable")
                
                logger.info(f"Executing command: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    check=True, capture_output=True, text=True
                )
                
                if result.stdout:
                    logger.info(f"pdftk stdout: {result.stdout}")
                
                logger.info("pdftk completed successfully.")
                self.form_filled.emit(self.output_path)
            finally:
                # Ensure the temporary file is deleted
                os.unlink(fdf_path)
                logger.debug("Deleted temporary FDF file.")
        except subprocess.CalledProcessError as e:
            error_message = f"pdftk error: {e.stderr}"
            logger.error(error_message)
            self.error_occurred.emit(error_message)
        except Exception as e:
            logger.error(f"An unexpected error occurred during form filling: {e}", exc_info=True)
            self.error_occurred.emit(f"An unexpected error occurred: {e}")

    def _create_fdf(self, data: Dict) -> str:
        """
        Creates properly formatted FDF (Forms Data Format) content with improved field handling.
        Handles different field types and properly formats the FDF structure.
        """
        fields = []
        for key, value in data.items():
            if not value:  # Skip empty fields
                continue
                
            # Determine if this is a checkbox/radio button or text field
            is_checkbox = False
            if isinstance(value, str) and value.strip().upper() in ["X", "YES", "ON", "TRUE"]:
                # Check if field name contains indicators it might be a checkbox
                checkbox_indicators = ["CheckBox", "Check", "RB", "Radio", "Choice"]
                if any(indicator in key for indicator in checkbox_indicators):
                    is_checkbox = True
                    # For checkboxes, the value should typically be /Yes
                    value_str = "/Yes"
                    logger.debug(f"Treating field '{key}' as checkbox with value '{value}'")
            
            if not is_checkbox:
                # Handle text fields, including multiline text
                # Properly escape special characters
                escaped_value = value.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)').replace('\n', '\\r\\n')
                value_str = f"({escaped_value})"
                logger.debug(f"Processing text field '{key}' with value length: {len(value)}")
            
            # Add the field to our array
            fields.append(f"<< /T ({key}) /V {value_str} >>")
        
        # Join all fields with proper separations
        fields_str = "\n".join(fields)
        
        # Create properly formatted FDF content
        fdf_content = f"""%FDF-1.2
%âãÏÓ
1 0 obj
<< /FDF << /Fields [
{fields_str}
] >> >>
endobj
trailer
<< /Root 1 0 R >>
%%EOF"""
        
        logger.info(f"Created FDF with {len(fields)} fields")
        return fdf_content