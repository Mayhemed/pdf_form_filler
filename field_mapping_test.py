#!/usr/bin/env python3
"""
FL-142 Test - Step 3: Field Mapping to PDF Form
Maps extracted data to exact PDF field names using the numbered reference
"""

import re
import json

def test_field_mapping():
    """Test mapping extracted data to PDF form fields"""
    
    print("🗺️ FL-142 Field Mapping Test")
    print("=" * 40)
    
    # First, get the extracted data (from previous step)
    sample_text = """
    ATTORNEY OR PARTY WITHOUT ATTORNEY (Name and Address): Mark Piesner
    TELEPHONE NO.: (818) 638-4456
    E-MAIL ADDRESS: mark@arcpointlaw.com
    SUPERIOR COURT OF CALIFORNIA, COUNTY OF LOS ANGELES
    PETITIONER: TAHIRA FRANCIS
    RESPONDENT: SHAWN ROGERS
    CASE NUMBER: 24STFL00615
    
    2. HOUSEHOLD FURNITURE, FURNISHINGS, APPLIANCES
    10,000.00
    
    6. CHECKING ACCOUNTS
    10,473.07
    
    19. STUDENT LOANS (Give details.)
    22,000.00
    
    22. LOANS—UNSECURED
    25,000.00
    
    23. CREDIT CARDS
    3,042.81
    
    24. OTHER DEBTS (Specify.)
    16,583.00
    
    26. TOTAL DEBTS
    64,225.81
    
    Date: December 12, 2024
    SHAWN ROGERS
    """
    
    # Quick extraction (simplified)
    extracted_data = {
        "attorney_name": "Mark Piesner",
        "attorney_phone": "(818) 638-4456", 
        "attorney_email": "mark@arcpointlaw.com",
        "court_county": "LOS ANGELES",
        "petitioner": "TAHIRA FRANCIS",
        "respondent": "SHAWN ROGERS", 
        "case_number": "24STFL00615",
        "household_value": "10,000.00",
        "checking_value": "10,473.07",
        "student_loans": "22,000.00",
        "unsecured_loans": "25,000.00",
        "credit_cards": "3,042.81",
        "other_debts": "16,583.00",
        "total_debts": "64,225.81",
        "signature_date": "December 12, 2024",
        "signature_name": "SHAWN ROGERS"
    }
    
    print(f"📋 Starting with {len(extracted_data)} extracted fields")
    
    # Field mapping based on fl142_field_mapping.txt
    # Maps data types to (field_number, pdf_field_name, full_field_path)
    field_mapping_reference = {
        "attorney_name": (1, "TextField1[0]", "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].TextField1[0]"),
        "attorney_phone": (2, "Phone[0]", "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Phone[0]"),
        "attorney_email": (3, "Email[0]", "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Email[0]"),
        "court_county": (4, "CrtCounty[0]", "FL-142[0].Page1[0].P1Caption[0].CourtInfo[0].CrtCounty[0]"),
        "petitioner": (5, "Party1[0]", "FL-142[0].Page1[0].P1Caption[0].TitlePartyName[0].Party1[0]"),
        "respondent": (6, "Party2[0]", "FL-142[0].Page1[0].P1Caption[0].TitlePartyName[0].Party2[0]"),
        "case_number": (7, "CaseNumber[0]", "FL-142[0].Page1[0].P1Caption[0].CaseNumber[0].CaseNumber[0]"),
        "household_value": (16, "DecimalField4[0]", "FL-142[0].Page1[0].Table1[0].Row3[0].DecimalField4[0]"),
        "checking_value": (36, "DecimalField10[0]", "FL-142[0].Page2[0].Table2[0].Row4[0].DecimalField10[0]"),
        "student_loans": (96, "DecimalField40[0]", "FL-142[0].Page4[0].Table4[0].Row2[0].DecimalField40[0]"),
        "unsecured_loans": (108, "DecimalField37[0]", "FL-142[0].Page4[0].Table4[0].Row5[0].DecimalField37[0]"),
        "credit_cards": (112, "DecimalField36[0]", "FL-142[0].Page4[0].Table4[0].Row6[0].DecimalField36[0]"),
        "other_debts": (116, "DecimalField43[0]", "FL-142[0].Page4[0].Table4[0].Row7[0].DecimalField43[0]"),
        "total_debts": (121, "DecimalField41[0]", "FL-142[0].Page4[0].Table4[0].Row9[0].DecimalField41[0]"),
        "signature_date": (123, "SigDate[0]", "FL-142[0].Page4[0].SignSub[0].SigDate[0]"),
        "signature_name": (124, "SigName[0]", "FL-142[0].Page4[0].SignSub[0].SigName[0]")
    }
    
    print("\n🗺️ Mapping data to PDF fields...")
    
    # Create the PDF field mapping
    pdf_field_mapping = {}
    mapping_summary = []
    
    for data_type, value in extracted_data.items():
        if data_type in field_mapping_reference:
            field_number, pdf_field_name, full_path = field_mapping_reference[data_type]
            
            # Format monetary values
            if any(keyword in data_type for keyword in ["value", "loans", "debts"]):
                # Clean up monetary values
                clean_value = value.replace(",", "")
                try:
                    amount = float(clean_value)
                    formatted_value = f"{amount:.2f}"
                except ValueError:
                    formatted_value = value
            else:
                formatted_value = value
            
            pdf_field_mapping[pdf_field_name] = formatted_value
            mapping_summary.append({
                "field_number": field_number,
                "data_type": data_type,
                "pdf_field": pdf_field_name,
                "value": formatted_value,
                "full_path": full_path
            })
            
            print(f"   📋 Field {field_number:3d}: {data_type} → {pdf_field_name}")
            print(f"        Value: {formatted_value}")
        else:
            print(f"   ❌ No mapping for: {data_type}")
    
    print(f"\n📊 Field Mapping Results:")
    print(f"   Data fields extracted: {len(extracted_data)}")
    print(f"   PDF fields mapped: {len(pdf_field_mapping)}")
    print(f"   Mapping success rate: {len(pdf_field_mapping)/len(extracted_data)*100:.1f}%")
    
    # Show detailed mapping
    print(f"\n📋 Detailed PDF Field Mapping:")
    for item in sorted(mapping_summary, key=lambda x: x["field_number"]):
        print(f"   {item['field_number']:3d}. {item['pdf_field']:<20} = {item['value']}")
    
    return pdf_field_mapping, mapping_summary

if __name__ == "__main__":
    fields, summary = test_field_mapping()
    print(f"\n✅ Field mapping test completed!")
    print(f"Mapped {len(fields)} PDF fields successfully")
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
