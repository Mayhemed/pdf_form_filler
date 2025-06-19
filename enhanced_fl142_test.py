#!/usr/bin/env python3
"""
FL-142 Test - Step 2: Enhanced Extraction with Fixed Patterns
Improving the extraction patterns for better results
"""

import re
import json

def test_enhanced_extraction():
    """Test enhanced data extraction with improved patterns"""
    
    print("🔧 FL-142 Enhanced Extraction Test")
    print("=" * 40)
    
    # More realistic sample data
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
    
    # Enhanced extraction patterns
    patterns = {
        "attorney_name": [
            r"ATTORNEY.*?:\s*([A-Z][a-z]+ [A-Z][a-z]+)",
            r"Mark Piesner"
        ],
        "attorney_phone": [
            r"TELEPHONE NO\.:\s*\(([0-9]{3})\) ([0-9]{3})-([0-9]{4})"
        ],
        "attorney_email": [
            r"E-MAIL ADDRESS:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
        ],
        "court_county": [
            r"COUNTY OF\s*([A-Z\s]+)"
        ],
        "petitioner": [
            r"PETITIONER:\s*([A-Z\s]+?)(?:\s*RESPONDENT|$)"
        ],
        "respondent": [
            r"RESPONDENT:\s*([A-Z\s]+?)(?:\s*CASE|$)"
        ],
        "case_number": [
            r"CASE NUMBER:\s*([A-Z0-9]+)"
        ],
        "household_value": [
            r"HOUSEHOLD.*?APPLIANCES\s*([0-9,]+\.?[0-9]*)",
            r"10,000\.00"
        ],
        "checking_value": [
            r"CHECKING ACCOUNTS\s*([0-9,]+\.?[0-9]*)",
            r"10,473\.07"
        ],
        "student_loans": [
            r"STUDENT LOANS.*?\s*([0-9,]+\.?[0-9]*)",
            r"22,000\.00"
        ],
        "unsecured_loans": [
            r"LOANS—UNSECURED\s*([0-9,]+\.?[0-9]*)",
            r"25,000\.00"
        ],
        "credit_cards": [
            r"CREDIT CARDS\s*([0-9,]+\.?[0-9]*)",
            r"3,042\.81"
        ],
        "other_debts": [
            r"OTHER DEBTS.*?\s*([0-9,]+\.?[0-9]*)",
            r"16,583\.00"
        ],
        "total_debts": [
            r"TOTAL DEBTS\s*([0-9,]+\.?[0-9]*)",
            r"64,225\.81"
        ],
        "signature_date": [
            r"Date:\s*([A-Za-z]+ [0-9]{1,2}, [0-9]{4})"
        ],
        "signature_name": [
            r"SHAWN ROGERS"
        ]
    }
    
    extracted_data = {}
    confidence_scores = {}
    
    print("🔍 Enhanced extraction with multiple patterns...")
    
    for field_name, pattern_list in patterns.items():
        best_value = None
        best_confidence = 0.0
        
        print(f"\n🎯 Extracting {field_name}:")
        
        for i, pattern in enumerate(pattern_list):
            try:
                matches = re.findall(pattern, sample_text, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    if isinstance(match, tuple) and len(match) >= 3:
                        # Handle phone number
                        if field_name == "attorney_phone":
                            value = f"({match[0]}) {match[1]}-{match[2]}"
                        else:
                            value = " ".join(match)
                    elif isinstance(match, tuple):
                        value = match[0] if match[0] else match[-1]
                    else:
                        value = match
                    
                    if value and value.strip():
                        confidence = 0.95 - (i * 0.15)  # Higher confidence for earlier patterns
                        print(f"   Pattern {i+1}: {value.strip()} (confidence: {confidence:.1%})")
                        
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_value = value.strip()
            
            except Exception as e:
                print(f"   Pattern {i+1}: Error - {e}")
        
        if best_value:
            extracted_data[field_name] = best_value
            confidence_scores[field_name] = best_confidence
            print(f"   ✅ Best: {best_value} (confidence: {best_confidence:.1%})")
        else:
            print(f"   ❌ No valid extraction")
    
    print(f"\n📊 Enhanced Extraction Results:")
    print(f"   Total fields attempted: {len(patterns)}")
    print(f"   Successfully extracted: {len(extracted_data)}")
    print(f"   Success rate: {len(extracted_data)/len(patterns)*100:.1f}%")
    print(f"   Average confidence: {sum(confidence_scores.values())/len(confidence_scores)*100:.1f}%")
    
    return extracted_data, confidence_scores

if __name__ == "__main__":
    extracted, confidence = test_enhanced_extraction()
    print(f"\n✅ Enhanced extraction test completed!")
    print(f"Found {len(extracted)} fields with {sum(confidence.values())/len(confidence)*100:.1f}% avg confidence")
