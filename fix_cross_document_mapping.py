#!/usr/bin/env python3
"""
Fix the AI prompt to do intelligent cross-document field mapping
"""

def create_cross_document_mapping_prompt():
    """Create a prompt that intelligently maps data from any source to any form field"""
    
    return '''
        # CROSS-DOCUMENT INTELLIGENT FIELD MAPPING PROMPT
        prompt = f"""You are an expert legal document analyst performing CROSS-DOCUMENT INTELLIGENT FIELD MAPPING.

TASK: For each form field in the TARGET FORM, search ALL source documents to find data that could fill that field.

CROSS-DOCUMENT MAPPING STRATEGY:

🎯 FOR EACH FORM FIELD:
1. **Understand what the field needs** (attorney name, case number, debt amount, etc.)
2. **Search ALL source documents** for data matching that field type
3. **Extract the best match** regardless of which document contains it
4. **Combine field label + found data** in format: "DATA [Field: LABEL]"

📋 INTELLIGENT FIELD TYPE MAPPING:

**ATTORNEY FIELDS** (TextField1, Phone, Email):
- Search for: Attorney names, law firm names, phone numbers, email addresses
- Look in: FL-120 attorney sections, signature blocks, contact info
- Example: "Mark Piesner, Arc Point Law PC [Field: ATTORNEY NAME]"

**CASE FIELDS** (CaseNumber, Party1, Party2, County):
- Search for: Case numbers (24STFL00615), party names, court counties
- Look in: Headers, captions, any document with case info
- Example: "24STFL00615 [Field: CASE NUMBER]"

**FINANCIAL FIELDS** (DecimalField40, DecimalField37, etc.):
- Search for: Dollar amounts, debt values, asset amounts
- Look in: FL-142 filled fields, financial statements, any money amounts
- Example: "$22,000.00 [Field: STUDENT LOANS]"

**ASSET FIELDS** (household, checking, savings, vehicles):
- Search for: Property descriptions, account balances, asset values
- Look in: Asset declarations, bank statements, property lists
- Example: "$5,000.00 [Field: CHECKING ACCOUNTS]"

**DEBT FIELDS** (student loans, credit cards, unsecured loans):
- Search for: Debt amounts, creditor names, loan balances
- Look in: Debt schedules, credit reports, financial disclosures
- Example: "$25,000.00 [Field: UNSECURED LOANS]"

📊 SOURCE DOCUMENTS AVAILABLE:
{text[:1000]}... [TRUNCATED - FULL CONTENT AVAILABLE FOR ANALYSIS]

🎯 TARGET FORM FIELDS TO FILL:
{json.dumps(field_names, indent=2)}

💡 CROSS-DOCUMENT EXTRACTION EXAMPLES:

Target Field: "FL-142[0].Page4[0].Table4[0].Row2[0].DecimalField40[0]" (Student Loans)
→ Search Strategy: Look for "student loan" amounts in ALL documents
→ Found in FL-142: "$22,000.00"
→ Output: "$22,000.00 [Field: STUDENT LOANS]"

Target Field: "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].TextField1[0]" (Attorney)
→ Search Strategy: Look for attorney info in ALL documents  
→ Found in FL-120: "Mark Piesner, Arc Point Law PC"
→ Output: "Mark Piesner, Arc Point Law PC [Field: ATTORNEY NAME]"

Target Field: "FL-142[0].Page4[0].Table4[0].Row5[0].DecimalField37[0]" (Unsecured Loans)
→ Search Strategy: Look for unsecured loan amounts in ALL documents
→ Found in FL-142: "$25,000.00"
→ Output: "$25,000.00 [Field: UNSECURED LOANS]"

🔍 COMPREHENSIVE SEARCH INSTRUCTIONS:

1. **ANALYZE EVERY FIELD**: For each of the {len(field_names)} target fields, determine what type of data it needs

2. **SEARCH ALL DOCUMENTS**: Don't just use FL-120 data - actively search FL-142 and other sources for:
   - Financial amounts (student loans, credit cards, assets, debts)
   - Account information (checking, savings, investments)
   - Property details (real estate, vehicles, personal property)
   - Debt details (creditor names, amounts, dates)

3. **INTELLIGENT MATCHING**: Match data semantically, not just by exact labels:
   - "Student loan: $22,000" → DecimalField40[0] (Student Loans field)
   - "Credit card debt: $3,042.81" → Credit Cards field
   - "Checking account: $1,500" → Checking Accounts field

4. **COMPREHENSIVE COVERAGE**: Extract data for AS MANY fields as possible by searching ALL sources

5. **PRIORITIZE FILLED DATA**: When you find actual amounts/values, use those over empty template text

CRITICAL SUCCESS FACTORS:
✅ **SEARCH ALL DOCUMENTS** - Don't just use FL-120, actively mine FL-142 for financial data
✅ **FIELD-TYPE MATCHING** - Understand what each field needs and search for that data type
✅ **CROSS-DOCUMENT INTELLIGENCE** - Use attorney info from FL-120 for attorney fields, financial data from FL-142 for financial fields
✅ **COMPREHENSIVE EXTRACTION** - Fill as many fields as possible from available data
✅ **SMART COMBINATION** - Format as "ACTUAL_VALUE [Field: FIELD_LABEL]"

RETURN FORMAT:
{{
    "extracted_data": {{
        "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].TextField1[0]": "Mark Piesner, Arc Point Law PC [Field: ATTORNEY NAME]",
        "FL-142[0].Page4[0].Table4[0].Row2[0].DecimalField40[0]": "$22,000.00 [Field: STUDENT LOANS]",
        "FL-142[0].Page4[0].Table4[0].Row5[0].DecimalField37[0]": "$25,000.00 [Field: UNSECURED LOANS]",
        "FL-142[0].Page4[0].Table4[0].Row6[0].DecimalField36[0]": "$3,042.81 [Field: CREDIT CARDS]"
    }},
    "confidence_scores": {{
        "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].TextField1[0]": 0.95,
        "FL-142[0].Page4[0].Table4[0].Row2[0].DecimalField40[0]": 0.95,
        "FL-142[0].Page4[0].Table4[0].Row5[0].DecimalField37[0]": 0.95,
        "FL-142[0].Page4[0].Table4[0].Row6[0].DecimalField36[0]": 0.95
    }}
}}

EXTRACT COMPREHENSIVE DATA by intelligently mapping information from ALL source documents to ALL target form fields."""
    '''

def apply_cross_document_fix():
    """Apply the cross-document mapping fix to the current file"""
    
    file_path = "pdf_form_filler1.py"
    
    # Read current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Create backup
    with open(file_path + ".backup_cross_document", 'w') as f:
        f.write(content)
    print("✅ Created backup: pdf_form_filler1.py.backup_cross_document")
    
    # Get the new cross-document prompt
    new_prompt = create_cross_document_mapping_prompt().strip()
    
    # Find and replace the current Anthropic prompt
    import re
    pattern = r'prompt = f"""You are analyzing legal documents to extract COMPREHENSIVE FORM DATA.*?Extract comprehensive data for AS MANY fields as possible, combining both labels and values\."""'
    
    new_content = re.sub(pattern, new_prompt, content, flags=re.DOTALL)
    
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print("✅ Applied cross-document intelligent mapping fix!")
        return True
    else:
        print("❌ Could not find prompt to fix")
        return False

if __name__ == "__main__":
    print("🔧 Applying Cross-Document Intelligent Field Mapping Fix")
    print("=" * 60)
    print("This fix teaches the AI to:")
    print("• Understand what each form field needs")  
    print("• Search ALL source documents for matching data")
    print("• Use attorney info from FL-120 for attorney fields")
    print("• Use financial data from FL-142 for financial fields")
    print("• Extract comprehensive data across all documents")
    print()
    
    success = apply_cross_document_fix()
    
    if success:
        print("\n🎉 Cross-Document Mapping Fix Applied!")
        print("Now the AI will intelligently search ALL documents")
        print("to fill ALL possible form fields.")
        print("\n🧪 Test with: source myenv/bin/activate && python pdf_form_filler1.py")
    else:
        print("\n❌ Fix failed - manual intervention needed")
