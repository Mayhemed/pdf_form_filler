#!/usr/bin/env python3
"""
FL-142 Test - Step 4: PDF Form Filling
Creates FDF and fills the actual PDF form using pdftk
"""

import os
import subprocess
import tempfile

def test_pdf_form_filling():
    """Test actual PDF form filling with the mapped data"""
    
    print("📝 FL-142 PDF Form Filling Test")
    print("=" * 40)
    
    # The mapped PDF fields from previous step
    pdf_field_mapping = {
        "TextField1[0]": "Mark Piesner",
        "Phone[0]": "(818) 638-4456", 
        "Email[0]": "mark@arcpointlaw.com",
        "CrtCounty[0]": "LOS ANGELES",
        "Party1[0]": "TAHIRA FRANCIS",
        "Party2[0]": "SHAWN ROGERS",
        "CaseNumber[0]": "24STFL00615",
        "DecimalField4[0]": "10000.00",
        "DecimalField10[0]": "10473.07",
        "DecimalField40[0]": "22000.00",
        "DecimalField37[0]": "25000.00",
        "DecimalField36[0]": "3042.81",
        "DecimalField43[0]": "16583.00",
        "DecimalField41[0]": "64225.81",
        "SigDate[0]": "December 12, 2024",
        "SigName[0]": "SHAWN ROGERS"
    }
    
    print(f"📋 Preparing to fill {len(pdf_field_mapping)} fields")
    
    # Check if pdftk is available
    try:
        result = subprocess.run(['pdftk', '--version'], capture_output=True, text=True)
        pdftk_available = result.returncode == 0
        print(f"📦 pdftk available: {'✅ Yes' if pdftk_available else '❌ No'}")
        if pdftk_available:
            print(f"   Version info: {result.stdout.strip().split(chr(10))[0]}")
    except FileNotFoundError:
        pdftk_available = False
        print(f"📦 pdftk available: ❌ No (not found in PATH)")
    
    # Check for form files
    possible_form_paths = [
        "/Users/markpiesner/Documents/Github/LegalTools/PDF_Form_Filler/../../agentic_form_filler/Forms/fl142.pdf",
        "/Users/markpiesner/Documents/Github/LegalTools/PDF_Form_Filler/fl142_blank.pdf",
        "/Users/markpiesner/Documents/Github/LegalTools/PDF_Form_Filler/test_form.pdf"
    ]
    
    target_form = None
    for form_path in possible_form_paths:
        if os.path.exists(form_path):
            target_form = form_path
            print(f"📄 Found target form: {os.path.basename(form_path)}")
            break
    
    if not target_form:
        print(f"📄 Target form: ❌ Not found")
        print(f"   Looked for:")
        for path in possible_form_paths:
            print(f"   - {path}")
    
    # Create FDF content
    print(f"\n📝 Creating FDF content...")
    fdf_content = create_fdf_content(pdf_field_mapping)
    print(f"   FDF size: {len(fdf_content)} characters")
    print(f"   Fields in FDF: {len(pdf_field_mapping)}")
    
    # Show a sample of the FDF
    print(f"\n📄 FDF Content Sample:")
    fdf_lines = fdf_content.split('\n')
    for i, line in enumerate(fdf_lines[:15]):
        print(f"   {i+1:2d}: {line}")
    if len(fdf_lines) > 15:
        print(f"   ... ({len(fdf_lines)-15} more lines)")
    
    # Attempt to fill the form if everything is available
    if pdftk_available and target_form:
        print(f"\n🚀 Attempting to fill PDF form...")
        
        output_path = "/Users/markpiesner/Documents/Github/LegalTools/PDF_Form_Filler/step4_filled_output.pdf"
        
        try:
            success = fill_pdf_form(target_form, pdf_field_mapping, output_path)
            
            if success:
                print(f"   ✅ PDF form filled successfully!")
                print(f"   📁 Output: {output_path}")
                
                # Verify the output
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(f"   📊 File size: {file_size:,} bytes")
                    
                    # Try to verify field content
                    verify_filled_form(output_path)
                else:
                    print(f"   ❌ Output file not created")
            else:
                print(f"   ❌ PDF form filling failed")
        
        except Exception as e:
            print(f"   💥 Error during form filling: {e}")
    
    elif not pdftk_available:
        print(f"\n⚠️ Cannot fill form: pdftk not available")
        print(f"   Install with: brew install pdftk-java (macOS)")
    elif not target_form:
        print(f"\n⚠️ Cannot fill form: No target form found")
    
    print(f"\n📊 Step 4 Summary:")
    print(f"   Fields to fill: {len(pdf_field_mapping)}")
    print(f"   FDF created: ✅ Yes")
    print(f"   pdftk available: {'✅ Yes' if pdftk_available else '❌ No'}")
    print(f"   Target form found: {'✅ Yes' if target_form else '❌ No'}")
    print(f"   Form filling: {'✅ Attempted' if pdftk_available and target_form else '❌ Skipped'}")
    
    return pdf_field_mapping, fdf_content


def create_fdf_content(field_mapping):
    """Create FDF content for PDF form filling"""
    
    fdf_header = """%FDF-1.2
1 0 obj
<<
/FDF
<<
/Fields ["""

    fdf_fields = []
    for field_name, field_value in field_mapping.items():
        if field_value:  # Only include non-empty fields
            # Escape special characters for FDF
            escaped_value = str(field_value).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
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


def fill_pdf_form(target_form_path, field_mapping, output_path):
    """Fill PDF form using pdftk"""
    
    try:
        # Create FDF file
        fdf_content = create_fdf_content(field_mapping)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fdf', delete=False) as fdf_file:
            fdf_file.write(fdf_content)
            fdf_path = fdf_file.name
        
        try:
            # Fill the form using pdftk
            cmd = [
                'pdftk', target_form_path, 
                'fill_form', fdf_path,
                'output', output_path
            ]
            
            print(f"   🔧 Running: {' '.join(cmd[:3])} ... output {os.path.basename(output_path)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"   ✅ pdftk completed successfully")
            return True
            
        finally:
            # Clean up temporary FDF file
            try:
                os.unlink(fdf_path)
            except:
                pass
    
    except subprocess.CalledProcessError as e:
        print(f"   ❌ pdftk error: {e}")
        print(f"   stdout: {e.stdout}")
        print(f"   stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False


def verify_filled_form(output_path):
    """Verify that the form was filled correctly"""
    
    print(f"\n🔍 Verifying filled form...")
    
    try:
        # Use pdftk to dump the field values
        cmd = ['pdftk', output_path, 'dump_data_fields_utf8']
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Count filled fields
        filled_fields = 0
        field_values = {}
        current_field = None
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            if line.startswith('FieldName:'):
                current_field = line.replace('FieldName:', '').strip()
            elif line.startswith('FieldValue:') and current_field:
                value = line.replace('FieldValue:', '').strip()
                if value:  # Only count non-empty values
                    filled_fields += 1
                    field_values[current_field] = value
                current_field = None
        
        print(f"   📊 Verification results:")
        print(f"      Filled fields: {filled_fields}")
        print(f"      Expected fields: 16")
        print(f"      Success rate: {filled_fields/16*100:.1f}%")
        
        if filled_fields > 0:
            print(f"\n   📋 Sample filled fields:")
            for i, (field, value) in enumerate(list(field_values.items())[:5]):
                print(f"      {field}: {value}")
            if len(field_values) > 5:
                print(f"      ... and {len(field_values)-5} more fields")
        
        return filled_fields >= 10  # Success if at least 10 fields filled
    
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Verification failed: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Verification error: {e}")
        return False


if __name__ == "__main__":
    fields, fdf = test_pdf_form_filling()
    print(f"\n✅ PDF form filling test completed!")
