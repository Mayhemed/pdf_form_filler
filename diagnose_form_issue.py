#!/usr/bin/env python3
"""
PDF Form Field Analysis and Debugging
Diagnoses why form filling is failing and provides solutions
"""

import subprocess
import json
import re
from pathlib import Path

def analyze_pdf_form_fields(pdf_path: str):
    """Analyze the PDF form to understand its structure"""
    print("🔍 Analyzing PDF Form Structure")
    print("=" * 50)
    
    try:
        # Get detailed field information
        result = subprocess.run([
            'pdftk', pdf_path, 'dump_data_fields_utf8'
        ], capture_output=True, text=True, check=True)
        
        fields = []
        current_field = {}
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            if line.startswith('---'):
                if current_field:
                    fields.append(current_field)
                current_field = {}
            elif ': ' in line:
                key, value = line.split(': ', 1)
                current_field[key] = value
        
        if current_field:
            fields.append(current_field)
        
        print(f"📋 Found {len(fields)} form fields")
        
        # Analyze field types and names
        field_types = {}
        field_names = []
        
        for field in fields:
            field_name = field.get('FieldName', '')
            field_type = field.get('FieldType', '')
            
            if field_name:
                field_names.append(field_name)
                if field_type not in field_types:
                    field_types[field_type] = 0
                field_types[field_type] += 1
        
        print(f"\n📊 Field Types:")
        for field_type, count in field_types.items():
            print(f"   {field_type}: {count} fields")
        
        # Look for our target fields
        target_fields = [
            "TextField1[0]", "Phone[0]", "Email[0]", "Party1[0]", "Party2[0]", 
            "CaseNumber[0]", "CrtCounty[0]", "DecimalField40[0]", 
            "DecimalField37[0]", "DecimalField36[0]", "DecimalField43[0]", "DecimalField41[0]"
        ]
        
        print(f"\n🎯 Target Field Analysis:")
        found_fields = []
        missing_fields = []
        
        for target in target_fields:
            found = False
            for field in fields:
                if field.get('FieldName') == target:
                    found_fields.append(target)
                    field_type = field.get('FieldType', 'Unknown')
                    field_flags = field.get('FieldFlags', '0')
                    print(f"   ✅ {target} ({field_type}, flags: {field_flags})")
                    found = True
                    break
            if not found:
                missing_fields.append(target)
                print(f"   ❌ {target} NOT FOUND")
        
        print(f"\n📈 Summary:")
        print(f"   Found target fields: {len(found_fields)}/{len(target_fields)}")
        print(f"   Missing fields: {len(missing_fields)}")
        
        if missing_fields:
            print(f"\n🔍 Searching for similar field names...")
            similar_fields = find_similar_fields(field_names, missing_fields)
            for missing, similar in similar_fields.items():
                print(f"   {missing} → Maybe: {similar}")
        
        return fields, found_fields, missing_fields
        
    except Exception as e:
        print(f"❌ Error analyzing form: {e}")
        return [], [], []

def find_similar_fields(all_field_names: list, missing_fields: list) -> dict:
    """Find similar field names for missing fields"""
    similar = {}
    
    for missing in missing_fields:
        # Extract base name without array notation
        base_missing = re.sub(r'\[.*?\]', '', missing).lower()
        
        best_matches = []
        for field_name in all_field_names:
            base_field = re.sub(r'\[.*?\]', '', field_name).lower()
            
            # Check for partial matches
            if base_missing in base_field or base_field in base_missing:
                best_matches.append(field_name)
            elif any(word in base_field for word in base_missing.split('field')):
                best_matches.append(field_name)
        
        if best_matches:
            similar[missing] = best_matches[:3]  # Top 3 matches
    
    return similar

def test_simple_form_filling(pdf_path: str):
    """Test form filling with a simple field"""
    print(f"\n🧪 Testing Simple Form Filling")
    print("=" * 50)
    
    # Try to fill just one field to test basic functionality
    simple_fdf = """%FDF-1.2
1 0 obj
<<
/FDF
<<
/Fields [
<<
/T (TextField1[0])
/V (TEST VALUE)
>>
]
>>
>>
endobj
trailer
<<
/Root 1 0 R
>>
%%EOF"""
    
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fdf', delete=False) as fdf_file:
        fdf_file.write(simple_fdf)
        fdf_path = fdf_file.name
    
    output_path = "/Users/markpiesner/Documents/Github/LegalTools/PDF_Form_Filler/test_simple_fill.pdf"
    
    try:
        result = subprocess.run([
            'pdftk', pdf_path, 'fill_form', fdf_path,
            'output', output_path
        ], capture_output=True, text=True)
        
        os.unlink(fdf_path)
        
        if result.returncode == 0:
            print(f"✅ Simple fill command succeeded")
            
            # Check if the field was actually filled
            verify_result = subprocess.run([
                'pdftk', output_path, 'dump_data_fields_utf8'
            ], capture_output=True, text=True)
            
            if 'TEST VALUE' in verify_result.stdout:
                print(f"✅ Field successfully filled with test value!")
                return True
            else:
                print(f"❌ Field not filled (command succeeded but no data)")
                return False
        else:
            print(f"❌ Simple fill command failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Simple fill test error: {e}")
        if os.path.exists(fdf_path):
            os.unlink(fdf_path)
        return False

def create_corrected_field_mapping():
    """Create corrected field mapping based on actual form analysis"""
    print(f"\n🔧 Creating Corrected Field Mapping")
    print("=" * 50)
    
    # Run form analysis first
    pdf_path = "/Users/markpiesner/Documents/GitHub/agentic_form_filler/forms/fl142.pdf"
    fields, found_fields, missing_fields = analyze_pdf_form_fields(pdf_path)
    
    if not fields:
        print("❌ Cannot analyze form structure")
        return {}
    
    # Create mapping based on actual field names in the form
    corrected_mapping = {}
    
    # Our data to map
    data_to_map = {
        "attorney_name": "Mark Piesner",
        "attorney_phone": "(818) 638-4456", 
        "attorney_email": "mark@arcpointlaw.com",
        "petitioner": "TAHIRA FRANCIS",
        "respondent": "SHAWN ROGERS",
        "case_number": "24STFL00615",
        "county": "LOS ANGELES",
        "student_loans": "22000.00",
        "unsecured_loans": "25000.00",
        "credit_cards": "3042.81",
        "other_debts": "16583.00",
        "total_debts": "64225.81"
    }
    
    print(f"🔍 Mapping data to actual form fields...")
    
    # Try to find the correct field names
    for field in fields:
        field_name = field.get('FieldName', '')
        field_type = field.get('FieldType', '')
        
        # Skip non-fillable fields
        if field_type not in ['Text', 'Button']:
            continue
        
        # Map based on field names and descriptions
        if 'attorney' in field_name.lower() or 'TextField1' in field_name:
            corrected_mapping[field_name] = data_to_map["attorney_name"]
        elif 'phone' in field_name.lower() and 'Phone' in field_name:
            corrected_mapping[field_name] = data_to_map["attorney_phone"]
        elif 'email' in field_name.lower():
            corrected_mapping[field_name] = data_to_map["attorney_email"]
        elif 'party1' in field_name.lower() or ('Party1' in field_name):
            corrected_mapping[field_name] = data_to_map["petitioner"]
        elif 'party2' in field_name.lower() or ('Party2' in field_name):
            corrected_mapping[field_name] = data_to_map["respondent"]
        elif 'case' in field_name.lower():
            corrected_mapping[field_name] = data_to_map["case_number"]
        elif 'county' in field_name.lower():
            corrected_mapping[field_name] = data_to_map["county"]
    
    print(f"📋 Corrected mapping created with {len(corrected_mapping)} fields:")
    for field_name, value in corrected_mapping.items():
        print(f"   {field_name} = {value}")
    
    return corrected_mapping

def main():
    """Main diagnostic function"""
    print("🔧 PDF Form Filling Diagnosis and Fix")
    print("=" * 60)
    
    pdf_path = "/Users/markpiesner/Documents/GitHub/agentic_form_filler/forms/fl142.pdf"
    
    if not Path(pdf_path).exists():
        print(f"❌ PDF form not found: {pdf_path}")
        return
    
    # Step 1: Analyze form structure
    fields, found_fields, missing_fields = analyze_pdf_form_fields(pdf_path)
    
    # Step 2: Test basic form filling capability
    basic_fill_works = test_simple_form_filling(pdf_path)
    
    # Step 3: Create corrected mapping
    corrected_mapping = create_corrected_field_mapping()
    
    # Step 4: Provide diagnosis and recommendations
    print(f"\n🏥 DIAGNOSIS")
    print("=" * 30)
    
    if not basic_fill_works:
        print("❌ CRITICAL: Basic form filling is not working")
        print("   • PDF may not be fillable")
        print("   • pdftk may have compatibility issues")
        print("   • Form may be protected or encrypted")
    else:
        print("✅ Basic form filling works")
        
    if missing_fields:
        print(f"⚠️ Field mapping issues: {len(missing_fields)} target fields not found")
        print("   • Field names in our mapping don't match actual form")
        print("   • Need to update field mapping to match actual PDF")
    else:
        print("✅ All target fields found in form")
    
    print(f"\n💡 RECOMMENDATIONS:")
    if not basic_fill_works:
        print("1. Check if PDF is actually fillable")
        print("2. Try different PDF form or version")
        print("3. Check pdftk compatibility with this form")
    elif missing_fields:
        print("1. Use corrected field mapping (created above)")
        print("2. Update field names to match actual form structure")
        print("3. Test with corrected mapping")
    else:
        print("1. Form should work - check FDF format")
        print("2. Verify field value formatting")
    
    # Save corrected mapping
    if corrected_mapping:
        output_file = "/Users/markpiesner/Documents/Github/LegalTools/PDF_Form_Filler/corrected_field_mapping.json"
        with open(output_file, 'w') as f:
            json.dump(corrected_mapping, f, indent=2)
        print(f"\n💾 Corrected mapping saved to: {output_file}")

if __name__ == "__main__":
    main()
