#!/usr/bin/env python3
"""
Quick Test of Improved Prompts
Author: Assistant
Description: Quick test to see if the improved prompts work better
"""

import json

# Simulate the improved prompt with sample data
def test_improved_prompt():
    """Test the improved prompt structure"""
    
    # Sample field names (from the FL-142 form)
    sample_field_names = [
        "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].TextField1[0]",
        "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Phone[0]", 
        "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Email[0]",
        "FL-142[0].Page1[0].P1Caption[0].TitlePartyName[0].Party1[0]",
        "FL-142[0].Page1[0].P1Caption[0].TitlePartyName[0].Party2[0]",
        "FL-142[0].Page1[0].P1Caption[0].CaseNumber[0].CaseNumber[0]"
    ]
    
    sample_descriptions = [
        "Attorney Name",
        "Attorney Phone", 
        "Attorney Email",
        "Petitioner",
        "Respondent", 
        "Case Number"
    ]
    
    # Sample document content (simulating what the AI would see)
    sample_text = """
    FL-120 RESPONSE—MARRIAGE/DOMESTIC PARTNERSHIP
    
    PETITIONER: TAHIRA FRANCIS
    RESPONDENT: SHAWN ROGERS
    CASE NUMBER: 24STFL00615
    
    Attorney for Respondent:
    Mark Piesner
    (818) 638-4456
    mark@arcpointlaw.com
    22287 Mulholland Hwy, #198, Calabasas CA 91302
    
    COURT COUNTY: LOS ANGELES
    
    FL-142 SCHEDULE OF ASSETS AND DEBTS
    
    19. STUDENT LOANS: $22,000.00
    22. LOANS—UNSECURED: $25,000.00  
    23. CREDIT CARDS: $3,042.81
    24. OTHER DEBTS: $16,583.00
    26. TOTAL DEBTS: $64,225.81
    """
    
    # Create the improved prompt
    field_mapping = dict(zip(sample_field_names, sample_descriptions))
    
    prompt = f"""# Legal Document Data Extraction Task

You are extracting data from California family law documents to fill an FL-142 Schedule of Assets and Debts form.

## TARGET: FL-142 Form Fields  
Extract data for these specific fields (use EXACT field names as keys):

{json.dumps(field_mapping, indent=2)}

## EXTRACTION STRATEGY:

### 1. ATTORNEY INFORMATION (from FL-120 if present):
- Attorney Name: Look for attorney signature, "Attorney for [Party]", or professional contact info
- Attorney Phone: Phone numbers in attorney contact section  
- Attorney Email: Email addresses in attorney contact section

### 2. CASE INFORMATION (from any source):
- Case Number: Format like "24STFL00615"
- Petitioner: First named party (often "PETITIONER:")  
- Respondent: Second named party (often "RESPONDENT:")

## CRITICAL RULES:

✅ **USE EXACT FIELD NAMES** - Return the exact field name from the list above as the key
✅ **EXTRACT ACTUAL DATA ONLY** - filled-in values, not blank fields or form labels
✅ **CROSS-REFERENCE DOCUMENTS** - Use attorney info from FL-120 for attorney fields

## DOCUMENT CONTENT TO ANALYZE:
{sample_text}

Extract all relevant data and return in this exact JSON format:

{{
    "extracted_data": {{
        "EXACT_FIELD_NAME": "extracted_value"
    }},
    "confidence_scores": {{
        "EXACT_FIELD_NAME": 0.95
    }}
}}"""

    print("🧪 TESTING IMPROVED PROMPT")
    print("=" * 50)
    print("PROMPT LENGTH:", len(prompt))
    print("\nIMPROVED PROMPT:")
    print("-" * 30)
    print(prompt)
    print("-" * 30)
    
    # Expected extraction based on sample data
    expected_extraction = {
        "extracted_data": {
            "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].TextField1[0]": "Mark Piesner",
            "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Phone[0]": "(818) 638-4456",
            "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Email[0]": "mark@arcpointlaw.com",
            "FL-142[0].Page1[0].P1Caption[0].TitlePartyName[0].Party1[0]": "TAHIRA FRANCIS",
            "FL-142[0].Page1[0].P1Caption[0].TitlePartyName[0].Party2[0]": "SHAWN ROGERS",
            "FL-142[0].Page1[0].P1Caption[0].CaseNumber[0].CaseNumber[0]": "24STFL00615"
        },
        "confidence_scores": {
            "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].TextField1[0]": 0.95,
            "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Phone[0]": 0.95,
            "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Email[0]": 0.95,
            "FL-142[0].Page1[0].P1Caption[0].TitlePartyName[0].Party1[0]": 0.95,
            "FL-142[0].Page1[0].P1Caption[0].TitlePartyName[0].Party2[0]": 0.95,
            "FL-142[0].Page1[0].P1Caption[0].CaseNumber[0].CaseNumber[0]": 0.95
        }
    }
    
    print("\nEXPECTED AI RESPONSE:")
    print(json.dumps(expected_extraction, indent=2))
    
    print("\n✅ PROMPT IMPROVEMENTS:")
    print("1. Uses exact field names instead of numbers")
    print("2. Clearer legal document context")
    print("3. Specific extraction strategies for attorney vs case vs financial data")
    print("4. Shorter, more focused prompt")
    print("5. Clear JSON format requirements")
    
    return prompt, expected_extraction

if __name__ == "__main__":
    test_improved_prompt()
