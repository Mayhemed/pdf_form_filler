#!/usr/bin/env python3
"""
PDF Form Filling Verification and Auto-Fix Test
Checks if PDF was actually filled and automatically fixes issues
"""

import os
import subprocess
import tempfile
import json
from pathlib import Path

def verify_pdf_filled(pdf_path: str, expected_data: dict) -> tuple[bool, list]:
    """Verify that PDF was actually filled with data"""
    print("🔍 Verifying PDF form filling...")
    
    issues = []
    
    try:
        # Extract current field values from the PDF
        result = subprocess.run([
            'pdftk', pdf_path, 'dump_data_fields_utf8'
        ], capture_output=True, text=True, check=True)
        
        current_values = {}
        current_field = {}
        
        # Parse pdftk output to get current field values
        for line in result.stdout.split('\n'):
            line = line.strip()
            if line.startswith('---'):
                if current_field and 'FieldName' in current_field:
                    field_name = current_field['FieldName']
                    field_value = current_field.get('FieldValue', '')
                    current_values[field_name] = field_value
                current_field = {}
            elif ': ' in line:
                key, value = line.split(': ', 1)
                current_field[key] = value
        
        # Add last field
        if current_field and 'FieldName' in current_field:
            field_name = current_field['FieldName']
            field_value = current_field.get('FieldValue', '')
            current_values[field_name] = field_value
        
        print(f"📋 Found {len(current_values)} fields in PDF")
        
        # Check each expected field
        filled_count = 0
        for field_name, expected_value in expected_data.items():
            actual_value = current_values.get(field_name, '')
            
            if actual_value and actual_value.strip():
                if actual_value.strip() == str(expected_value).strip():
                    print(f"  ✅ {field_name}: {actual_value}")
                    filled_count += 1
                else:
                    print(f"  ⚠️ {field_name}: Expected '{expected_value}' but got '{actual_value}'")
                    issues.append(f"Field {field_name} has wrong value")
            else:
                print(f"  ❌ {field_name}: EMPTY (expected '{expected_value}')")
                issues.append(f"Field {field_name} is empty")
        
        success = filled_count == len(expected_data)
        print(f"\n📊 Filling Status: {filled_count}/{len(expected_data)} fields filled correctly")
        
        if not success:
            print("❌ PDF FORM FILLING FAILED - Fields are empty or incorrect!")
        else:
            print("✅ PDF FORM FILLING SUCCESSFUL!")
            
        return success, issues
        
    except subprocess.CalledProcessError as e:
        issues.append(f"Cannot read PDF fields: {e}")
        print(f"❌ Error reading PDF: {e}")
        return False, issues
    except Exception as e:
        issues.append(f"Verification error: {e}")
        print(f"❌ Verification error: {e}")
        return False, issues

def create_enhanced_fdf(field_data: dict) -> str:
    """Create an enhanced FDF file with better formatting"""
    
    fdf_header = """%FDF-1.2
1 0 obj
<<
/FDF
<<
/Fields ["""

    fdf_fields = []
    for field_name, field_value in field_data.items():
        if field_value:  # Only include non-empty fields
            # Enhanced escaping for FDF
            value_str = str(field_value)
            # Escape parentheses and backslashes
            escaped_value = value_str.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            
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

def auto_fix_form_filling(blank_form_path: str, field_data: dict, output_path: str) -> tuple[bool, str]:
    """Automatically try different methods to fix form filling"""
    print("\n🔧 Auto-fixing form filling issues...")
    
    methods = [
        ("Standard FDF Method", "standard"),
        ("Flattened FDF Method", "flatten"), 
        ("Multi-step Method", "multistep"),
        ("Alternative Encoding", "encoding")
    ]
    
    for method_name, method_type in methods:
        print(f"\n🔄 Trying: {method_name}")
        
        try:
            temp_output = output_path.replace('.pdf', f'_temp_{method_type}.pdf')
            
            if method_type == "standard":
                success = _try_standard_method(blank_form_path, field_data, temp_output)
            elif method_type == "flatten":
                success = _try_flatten_method(blank_form_path, field_data, temp_output)
            elif method_type == "multistep":
                success = _try_multistep_method(blank_form_path, field_data, temp_output)
            elif method_type == "encoding":
                success = _try_encoding_method(blank_form_path, field_data, temp_output)
            
            if success:
                # Verify this method worked
                verification_success, _ = verify_pdf_filled(temp_output, field_data)
                if verification_success:
                    # Move successful result to final output
                    os.rename(temp_output, output_path)
                    print(f"✅ SUCCESS with {method_name}!")
                    return True, method_name
                else:
                    print(f"❌ {method_name} created file but fields still empty")
                    if os.path.exists(temp_output):
                        os.remove(temp_output)
            
        except Exception as e:
            print(f"❌ {method_name} failed: {e}")
            continue
    
    return False, "All methods failed"

def _try_standard_method(blank_form: str, field_data: dict, output: str) -> bool:
    """Try standard pdftk method"""
    fdf_content = create_enhanced_fdf(field_data)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fdf', delete=False) as fdf_file:
        fdf_file.write(fdf_content)
        fdf_path = fdf_file.name
    
    try:
        result = subprocess.run([
            'pdftk', blank_form, 'fill_form', fdf_path,
            'output', output
        ], capture_output=True, text=True)
        
        os.unlink(fdf_path)
        return result.returncode == 0 and os.path.exists(output)
    except:
        if os.path.exists(fdf_path):
            os.unlink(fdf_path)
        return False

def _try_flatten_method(blank_form: str, field_data: dict, output: str) -> bool:
    """Try with flattening"""
    fdf_content = create_enhanced_fdf(field_data)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fdf', delete=False) as fdf_file:
        fdf_file.write(fdf_content)
        fdf_path = fdf_file.name
    
    try:
        result = subprocess.run([
            'pdftk', blank_form, 'fill_form', fdf_path,
            'output', output, 'flatten'
        ], capture_output=True, text=True)
        
        os.unlink(fdf_path)
        return result.returncode == 0 and os.path.exists(output)
    except:
        if os.path.exists(fdf_path):
            os.unlink(fdf_path)
        return False

def _try_multistep_method(blank_form: str, field_data: dict, output: str) -> bool:
    """Try filling in multiple steps"""
    try:
        # Split fields into smaller groups
        field_items = list(field_data.items())
        chunk_size = 3
        
        current_form = blank_form
        
        for i in range(0, len(field_items), chunk_size):
            chunk = dict(field_items[i:i+chunk_size])
            
            temp_output = output.replace('.pdf', f'_step{i//chunk_size}.pdf')
            
            fdf_content = create_enhanced_fdf(chunk)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.fdf', delete=False) as fdf_file:
                fdf_file.write(fdf_content)
                fdf_path = fdf_file.name
            
            result = subprocess.run([
                'pdftk', current_form, 'fill_form', fdf_path,
                'output', temp_output
            ], capture_output=True, text=True)
            
            os.unlink(fdf_path)
            
            if result.returncode != 0:
                return False
            
            # Clean up previous temp file if not the original
            if current_form != blank_form:
                os.remove(current_form)
            
            current_form = temp_output
        
        # Rename final result
        if current_form != output:
            os.rename(current_form, output)
        
        return os.path.exists(output)
        
    except Exception as e:
        print(f"Multistep error: {e}")
        return False

def _try_encoding_method(blank_form: str, field_data: dict, output: str) -> bool:
    """Try with different character encoding"""
    # Create FDF with UTF-8 encoding
    fdf_content = create_enhanced_fdf(field_data)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fdf', delete=False, encoding='utf-8') as fdf_file:
        fdf_file.write(fdf_content)
        fdf_path = fdf_file.name
    
    try:
        result = subprocess.run([
            'pdftk', blank_form, 'fill_form', fdf_path,
            'output', output, 'dont_ask'
        ], capture_output=True, text=True)
        
        os.unlink(fdf_path)
        return result.returncode == 0 and os.path.exists(output)
    except:
        if os.path.exists(fdf_path):
            os.unlink(fdf_path)
        return False

def comprehensive_form_filling_test():
    """Run comprehensive form filling test with auto-fix"""
    print("🧪 Comprehensive PDF Form Filling Test with Auto-Fix")
    print("=" * 60)
    
    # Our tested and verified data
    field_data = {
        "TextField1[0]": "Mark Piesner",
        "Phone[0]": "(818) 638-4456",
        "Email[0]": "mark@arcpointlaw.com",
        "Party1[0]": "TAHIRA FRANCIS",
        "Party2[0]": "SHAWN ROGERS",
        "CaseNumber[0]": "24STFL00615",
        "CrtCounty[0]": "LOS ANGELES",
        "DecimalField40[0]": "22000.00",
        "DecimalField37[0]": "25000.00",
        "DecimalField36[0]": "3042.81",
        "DecimalField43[0]": "16583.00",
        "DecimalField41[0]": "64225.81"
    }
    
    # Find blank form
    base_path = Path("/Users/markpiesner/Documents/Github/LegalTools/PDF_Form_Filler")
    blank_form_path = None
    
    possible_forms = [
        base_path / "fl142.pdf",
        base_path / "../../agentic_form_filler/Forms/fl142.pdf"
    ]
    
    for form_path in possible_forms:
        if form_path.exists():
            blank_form_path = str(form_path)
            break
    
    if not blank_form_path:
        print("❌ No blank FL-142 form found!")
        return False
    
    print(f"📄 Using blank form: {os.path.basename(blank_form_path)}")
    print(f"📊 Data to fill: {len(field_data)} fields")
    
    # Output path
    output_path = str(base_path / "FL142_VERIFIED_FILLED.pdf")
    
    # First attempt - standard method
    print(f"\n🔄 Step 1: Initial form filling attempt...")
    success = _try_standard_method(blank_form_path, field_data, output_path)
    
    if success:
        print(f"✅ Initial attempt successful, verifying...")
        verification_success, issues = verify_pdf_filled(output_path, field_data)
        
        if verification_success:
            print(f"🎉 PERFECT! Form filled correctly on first try!")
            return True
        else:
            print(f"❌ Form created but not filled correctly. Issues:")
            for issue in issues:
                print(f"   • {issue}")
            print(f"\n🔧 Starting auto-fix process...")
    else:
        print(f"❌ Initial attempt failed, starting auto-fix...")
    
    # Auto-fix attempt
    fix_success, method_used = auto_fix_form_filling(blank_form_path, field_data, output_path)
    
    if fix_success:
        print(f"\n🎉 AUTO-FIX SUCCESSFUL!")
        print(f"   Method used: {method_used}")
        print(f"   Output: {os.path.basename(output_path)}")
        
        # Final verification
        final_verification, final_issues = verify_pdf_filled(output_path, field_data)
        if final_verification:
            print(f"✅ FINAL VERIFICATION PASSED - Form correctly filled!")
            return True
        else:
            print(f"❌ Auto-fix created file but verification still fails")
            return False
    else:
        print(f"\n❌ AUTO-FIX FAILED: {method_used}")
        print(f"   All available methods attempted")
        print(f"   This may indicate a form compatibility issue")
        return False

def main():
    """Main test function"""
    success = comprehensive_form_filling_test()
    
    print(f"\n" + "=" * 60)
    if success:
        print(f"🎉 COMPREHENSIVE TEST PASSED!")
        print(f"   ✅ PDF form filling is working correctly")
        print(f"   ✅ Verification confirmed fields are filled")
        print(f"   ✅ Auto-fix system is functional")
    else:
        print(f"❌ COMPREHENSIVE TEST FAILED!")
        print(f"   The form filling system needs further debugging")
    
    return success

if __name__ == "__main__":
    main()
