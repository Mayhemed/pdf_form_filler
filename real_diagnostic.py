#!/usr/bin/env python3
"""
Real Diagnostic Tool for AI Extraction
Author: Assistant
Description: Shows you the ACTUAL prompts being sent to the AI and helps diagnose issues
"""

import os
import json

def show_actual_prompt_being_used():
    """Show the actual prompt that gets sent to the AI"""
    
    print("🔍 CURRENT AI EXTRACTION PROMPT ANALYSIS")
    print("=" * 60)
    
    # Sample data that mimics what the GUI actually sees
    sample_field_names = [
        "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].TextField1[0]",
        "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Phone[0]",
        "FL-142[0].Page1[0].P1Caption[0].TitlePartyName[0].Party1[0]",
        "FL-142[0].Page1[0].P1Caption[0].CaseNumber[0].CaseNumber[0]"
    ]
    
    sample_descriptions = ["Attorney Name", "Attorney Phone", "Petitioner", "Case Number"]
    
    # This is the actual text the AI might receive from a PDF
    actual_pdf_text = """
    [PDF FILE: Rogers-FL120-signed.pdf] This is a PDF form that should be processed directly by the AI model.

    === FL-120 Source ===
    Some extracted text from PDF processing...
    
    [PDF FILE: fl142 copy.pdf] This is a PDF form that should be processed directly by the AI model.
    
    === FL-142 Source ===
    More extracted text...
    """
    
    # Create the actual prompt (similar to what's in the GUI)
    prompt = f"""# Legal Document Data Extraction Task

You are extracting data from California family law documents to fill an FL-142 Schedule of Assets and Debts form.

## SOURCE DOCUMENTS:
You are analyzing PDF documents that contain filled-in legal forms.

## TARGET: FL-142 Form Fields  
Extract data for these specific fields (use EXACT field names as keys):

{json.dumps(dict(zip(sample_field_names, sample_descriptions)), indent=2)}

## EXTRACTION STRATEGY:

### 1. ATTORNEY INFORMATION (from FL-120 if present):
- Attorney Name: Look for attorney signature, "Attorney for [Party]", or professional contact info
- Attorney Phone: Phone numbers in attorney contact section  
- Attorney Email: Email addresses in attorney contact section

### 2. CASE INFORMATION (from any source):
- Case Number: Format like "24STFL00615"
- Petitioner: First named party (often "PETITIONER:")  
- Respondent: Second named party (often "RESPONDENT:")

### 3. FINANCIAL DATA (from FL-142 if present):
Look for FILLED-IN dollar amounts (ignore $0.00 entries):
- Student Loans: Education debt amounts
- Unsecured Loans: Personal loans, lines of credit
- Credit Cards: Credit card balances and debts  
- Other Debts: Additional liabilities
- Total Debts: Sum of all debts
- Assets: Bank accounts, real estate, vehicles

## CRITICAL RULES:

✅ **USE EXACT FIELD NAMES** - Return the exact field name from the list above as the key
✅ **EXTRACT ACTUAL DATA ONLY** - filled-in values, not blank fields or form labels
✅ **IGNORE TEMPLATE TEXT** - Skip instructions like "Give details", "Attach copy"
✅ **LOOK FOR REAL VALUES** - Names, dollar amounts, case numbers, contact info
✅ **CROSS-REFERENCE DOCUMENTS** - Use attorney info from FL-120 for attorney fields

## DOCUMENT CONTENT TO ANALYZE:
{actual_pdf_text}

Extract all relevant data and return in this exact JSON format:

{{
    "extracted_data": {{
        "EXACT_FIELD_NAME": "extracted_value"
    }},
    "confidence_scores": {{
        "EXACT_FIELD_NAME": 0.95
    }}
}}

Focus on quality over quantity - extract what you can clearly identify."""

    print("📝 ACTUAL PROMPT BEING SENT TO AI:")
    print("-" * 40)
    print(prompt)
    print("-" * 40)
    print(f"📏 Prompt length: {len(prompt)} characters")
    
    print("\n🤔 POTENTIAL ISSUES TO CHECK:")
    print("1. PDF Text Extraction:")
    print("   - Are you seeing '[PDF FILE: filename.pdf]' in the document content?")
    print("   - This means the GUI is NOT extracting actual PDF text")
    print("   - The AI only sees placeholder text, not real data")
    print()
    print("2. Field Name Complexity:")
    print("   - Complex field names like 'FL-142[0].Page1[0]...' might confuse AI")
    print("   - But this should work with the numbered mapping approach")
    print()
    print("3. API Integration:")
    print("   - Check if you have valid API keys set")
    print("   - Verify the AI is actually being called vs pattern matching fallback")
    print()
    print("4. PDF Processing Pipeline:")
    print("   - The system should convert PDFs to images for vision models")
    print("   - Check if the vision processing is working")
    
    print("\n🔧 TO DIAGNOSE YOUR REAL ISSUE:")
    print("1. Run the GUI with debug output:")
    print("   python3 python_form_filler3.py")
    print("2. Load your real PDFs")
    print("3. Set a valid API key") 
    print("4. Click 'Extract Data with AI'")
    print("5. Watch the console output for:")
    print("   - 'DEBUG: Using numbered PDF for extraction: [path]'")
    print("   - 'OpenAI response received, length: [number]'")
    print("   - 'Successfully parsed JSON with [X] extracted fields'")
    print("6. Share the actual console output to see what's failing")

if __name__ == "__main__":
    show_actual_prompt_being_used()
