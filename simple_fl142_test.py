#!/usr/bin/env python3
"""
Simple FL-142 Test - Step 1: Basic Extraction
Testing the core extraction functionality first
"""

import re
import json

def test_basic_extraction():
    """Test basic data extraction from FL-142 documents"""
    
    print("🧪 FL-142 Basic Extraction Test")
    print("=" * 40)
    
    # Sample data from the documents
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
    
    19. STUDENT LOANS
    22,000.00
    
    22. LOANS—UNSECURED
    25,000.00
    
    23. CREDIT CARDS
    3,042.81
    
    24. OTHER DEBTS
    16,583.00
    
    26. TOTAL DEBTS
    64,225.81
    
    Date: December 12, 2024
    SHAWN ROGERS
    """
    
    # Basic extraction patterns
    patterns = {
        "attorney_name": r"ATTORNEY.*?:\s*([A-Z][a-z]+ [A-Z][a-z]+)",
        "attorney_phone": r"TELEPHONE NO\.:\s*\(([0-9]{3})\) ([0-9]{3})-([0-9]{4})",
        "attorney_email": r"E-MAIL ADDRESS:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        "court_county": r"COUNTY OF\s*([A-Z\s]+)",
        "petitioner": r"PETITIONER:\s*([A-Z\s]+)",
        "respondent": r"RESPONDENT:\s*([A-Z\s]+)",
        "case_number": r"CASE NUMBER:\s*([A-Z0-9]+)",
        "household_value": r"HOUSEHOLD.*?([0-9,]+\.?[0-9]*)",
        "checking_value": r"CHECKING.*?([0-9,]+\.?[0-9]*)",
        "student_loans": r"STUDENT LOANS.*?([0-9,]+\.?[0-9]*)",
        "unsecured_loans": r"UNSECURED.*?([0-9,]+\.?[0-9]*)",
        "credit_cards": r"CREDIT CARDS.*?([0-9,]+\.?[0-9]*)",
        "other_debts": r"OTHER DEBTS.*?([0-9,]+\.?[0-9]*)",
        "total_debts": r"TOTAL DEBTS.*?([0-9,]+\.?[0-9]*)",
        "signature_date": r"Date:\s*([A-Za-z]+ [0-9]{1,2}, [0-9]{4})",
        "signature_name": r"SHAWN ROGERS"
    }
    
    extracted_data = {}
    
    print("🔍 Extracting data...")
    
    for field_name, pattern in patterns.items():
        try:
            match = re.search(pattern, sample_text, re.IGNORECASE | re.MULTILINE)
            if match:
                if isinstance(match.groups(), tuple) and len(match.groups()) > 1:
                    # Handle phone number
                    if field_name == "attorney_phone":
                        value = f"({match.group(1)}) {match.group(2)}-{match.group(3)}"
                    else:
                        value = match.group(1)
                elif match.groups():
                    value = match.group(1)
                else:
                    value = match.group(0)
                
                extracted_data[field_name] = value.strip()
                print(f"   ✅ {field_name}: {value.strip()}")
            else:
                print(f"   ❌ {field_name}: Not found")
        
        except Exception as e:
            print(f"   ⚠️ {field_name}: Error - {e}")
    
    print(f"\n📊 Extraction Results:")
    print(f"   Total fields attempted: {len(patterns)}")
    print(f"   Successfully extracted: {len(extracted_data)}")
    print(f"   Success rate: {len(extracted_data)/len(patterns)*100:.1f}%")
    
    return extracted_data

if __name__ == "__main__":
    result = test_basic_extraction()
    print(f"\n✅ Basic extraction test completed!")
    print(f"Found {len(result)} fields")
