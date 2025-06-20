#!/usr/bin/env python3
"""
PDF Field Name Inspector
Author: Assistant
Description: Inspects actual field names in PDF forms to help with accurate mapping
"""

import subprocess
import sys
from pathlib import Path

def inspect_pdf_fields(pdf_path: str) -> None:
    """Inspect and display all field names in a PDF form"""
    print(f"🔍 Inspecting PDF Fields: {Path(pdf_path).name}")
    print("=" * 60)
    
    try:
        # Get field information using pdftk
        result = subprocess.run([
            "pdftk", pdf_path, "dump_data_fields"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"❌ pdftk failed: {result.stderr}")
            return
        
        # Parse field information
        lines = result.stdout.split('\n')
        fields = []
        current_field = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('FieldName:'):
                if current_field:
                    fields.append(current_field)
                current_field = {'name': line.replace('FieldName:', '').strip()}
            elif line.startswith('FieldType:') and current_field:
                current_field['type'] = line.replace('FieldType:', '').strip()
            elif line.startswith('FieldValue:') and current_field:
                current_field['value'] = line.replace('FieldValue:', '').strip()
            elif line.startswith('FieldValueDefault:') and current_field:
                current_field['default'] = line.replace('FieldValueDefault:', '').strip()
        
        if current_field:
            fields.append(current_field)
        
        print(f"📊 Found {len(fields)} fillable fields")
        print("")
        
        # Group fields by type
        field_types = {}
        for field in fields:
            field_type = field.get('type', 'Unknown')
            if field_type not in field_types:
                field_types[field_type] = []
            field_types[field_type].append(field)
        
        for field_type, type_fields in field_types.items():
            print(f"📝 {field_type} Fields ({len(type_fields)}):")
            for i, field in enumerate(type_fields[:10]):  # Show first 10 of each type
                name = field.get('name', 'Unknown')
                value = field.get('value', '')
                default = field.get('default', '')
                
                print(f"   {i+1:2d}. {name}")
                if value:
                    print(f"       Current: {value}")
                if default:
                    print(f"       Default: {default}")
            
            if len(type_fields) > 10:
                print(f"       ... and {len(type_fields) - 10} more {field_type} fields")
            print("")
        
        # Show fields that might be relevant for FL-142
        print("🎯 Fields that might match FL-142 data:")
        relevant_keywords = [
            'name', 'attorney', 'phone', 'email', 'party', 'petitioner', 'respondent',
            'case', 'county', 'court', 'debt', 'loan', 'credit', 'total', 'amount',
            'decimal', 'student', 'unsecured'
        ]
        
        relevant_fields = []
        for field in fields:
            field_name = field.get('name', '').lower()
            for keyword in relevant_keywords:
                if keyword in field_name:
                    relevant_fields.append(field)
                    break
        
        if relevant_fields:
            for field in relevant_fields[:20]:  # Show first 20 relevant fields
                print(f"   • {field.get('name', 'Unknown')}")
        else:
            print("   No obviously relevant fields found with common keywords")
        
        # Generate sample test data
        print("")
        print("🧪 Sample Test Data (Python dict format):")
        print("test_data = {")
        for i, field in enumerate(fields[:12]):  # Show first 12 fields
            field_name = field.get('name', f'field_{i}')
            field_type = field.get('type', 'Text')
            
            if 'decimal' in field_name.lower() or 'amount' in field_name.lower():
                sample_value = "1000.00"
            elif 'phone' in field_name.lower():
                sample_value = "(555) 123-4567"
            elif 'email' in field_name.lower():
                sample_value = "test@example.com"
            elif 'case' in field_name.lower():
                sample_value = "24STFL00615"
            elif 'county' in field_name.lower():
                sample_value = "LOS ANGELES"
            else:
                sample_value = "Test Value"
            
            print(f'    "{field_name}": "{sample_value}",')
        
        print("}")
        
    except subprocess.TimeoutExpired:
        print("❌ pdftk command timed out")
    except FileNotFoundError:
        print("❌ pdftk not found - install pdftk to inspect PDF fields")
    except Exception as e:
        print(f"❌ Error inspecting PDF: {e}")

def main():
    """Main function"""
    base_path = Path("/Users/markpiesner/Documents/Github/LegalTools/PDF_Form_Filler")
    
    # Find the FL-142 PDF
    possible_paths = [
        str(base_path / "../../agentic_form_filler/Forms/fl142.pdf"),
        str(base_path / "fl142.pdf"),
        str(base_path / "FL-142.pdf"),
    ]
    
    pdf_path = None
    for path in possible_paths:
        if Path(path).exists():
            pdf_path = path
            break
    
    if not pdf_path:
        print("❌ No FL-142 PDF found in expected locations")
        print("Expected locations:")
        for path in possible_paths:
            print(f"   • {path}")
        return
    
    inspect_pdf_fields(pdf_path)

if __name__ == "__main__":
    main()
