#!/usr/bin/env python3
"""
Improved AI Prompt Generator for PDF Form Filling
Author: Assistant
Description: Creates optimized prompts for better AI extraction results
"""

def create_improved_openai_prompt(form_fields, text_content, pdf_files):
    """
    Create an improved OpenAI prompt for better extraction results
    """
    
    # Get field names for context
    field_examples = []
    for i, field in enumerate(form_fields[:10]):  # Show first 10 fields as examples
        field_examples.append(f"   {field.name}: [Extract relevant value here]")
    
    source_descriptions = []
    for i, pdf_path in enumerate(pdf_files):
        import os
        filename = os.path.basename(pdf_path)
        source_descriptions.append(f"   Source {i+1}: {filename}")
    
    prompt = f"""# Legal Document Data Extraction Task

You are extracting data from California family law documents to fill an FL-142 Schedule of Assets and Debts form.

## SOURCE DOCUMENTS ({len(pdf_files)} provided):
{chr(10).join(source_descriptions)}

## TARGET: FL-142 Form Fields
I need you to extract data to fill these specific fields (showing exact field names):

{chr(10).join(field_examples)}
{"   ... and " + str(max(0, len(form_fields) - 10)) + " more fields" if len(form_fields) > 10 else ""}

## EXTRACTION STRATEGY:

### 1. ATTORNEY INFORMATION (from FL-120 if present):
- Attorney Name: Look for attorney signature, "Attorney for [Party]", or professional contact info
- Attorney Phone: Phone numbers in attorney contact section
- Attorney Email: Email addresses in attorney contact section  
- Attorney Address: Professional address for attorney

### 2. CASE INFORMATION (from any source):
- Case Number: Format like "24STFL00615" 
- Petitioner: First named party (often "PETITIONER:")
- Respondent: Second named party (often "RESPONDENT:")
- Court County: Look for court jurisdiction like "LOS ANGELES"

### 3. FINANCIAL DATA (from FL-142 if present):
Look for FILLED-IN dollar amounts (ignore $0.00 entries):
- Student Loans: Education debt amounts
- Unsecured Loans: Personal loans, lines of credit
- Credit Cards: Credit card balances and debts
- Other Debts: Additional liabilities
- Total Debts: Sum of all debts
- Assets: Bank accounts, real estate, vehicles

## CRITICAL RULES:

✅ **EXTRACT ACTUAL DATA ONLY** - filled-in values, not blank fields or form labels
✅ **USE EXACT FIELD NAMES** - Return the exact field name as the key
✅ **IGNORE TEMPLATE TEXT** - Skip instructions like "Give details", "Attach copy" 
✅ **LOOK FOR REAL VALUES** - Names, dollar amounts, case numbers, contact info
✅ **CROSS-REFERENCE DOCUMENTS** - Use attorney info from FL-120 for attorney fields

## EXAMPLE OF GOOD EXTRACTION:
```json
{{
  "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].TextField1[0]": "Mark Piesner",
  "FL-142[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Phone[0]": "(818) 638-4456",
  "FL-142[0].Page1[0].P1Caption[0].CaseNumber[0].CaseNumber[0]": "24STFL00615"
}}
```

## DOCUMENT CONTENT TO ANALYZE:
{text_content[:6000]}

Please extract all relevant data and return in this exact JSON format:

```json
{{
  "extracted_data": {{
    "EXACT_FIELD_NAME": "extracted_value"
  }},
  "confidence_scores": {{
    "EXACT_FIELD_NAME": 0.95
  }}
}}
```

Focus on quality over quantity - extract what you can clearly identify."""

    return prompt

def create_improved_anthropic_prompt(form_fields, text_content, pdf_files):
    """
    Create an improved Anthropic prompt for better extraction results
    """
    
    # Similar structure but optimized for Claude
    field_examples = []
    for i, field in enumerate(form_fields[:8]):  # Show first 8 fields for Claude
        field_examples.append(f"• {field.name}")
    
    source_list = []
    for i, pdf_path in enumerate(pdf_files):
        import os
        filename = os.path.basename(pdf_path)
        source_list.append(f"{i+1}. {filename}")
    
    prompt = f"""I need to extract data from legal documents to populate an FL-142 California family law form.

**Source Documents:**
{chr(10).join(source_list)}

**Target Fields (sample):**
{chr(10).join(field_examples)}
{"... plus " + str(max(0, len(form_fields) - 8)) + " additional fields" if len(form_fields) > 8 else ""}

**Extraction Requirements:**

**Attorney Information** (typically from FL-120 documents):
- Attorney name, phone, email, address
- Look for professional signatures and contact details

**Case Details** (from any document):  
- Case numbers (format: ##STFL#####)
- Party names (Petitioner vs Respondent)
- Court county/jurisdiction

**Financial Data** (typically from FL-142 documents):
- Dollar amounts for debts (student loans, credit cards, etc.)
- Asset values (accounts, property, vehicles)
- Only extract non-zero amounts that are clearly filled in

**Key Rules:**
1. Use the exact field names provided as keys
2. Extract only actual filled-in data, not form labels
3. Cross-reference between documents (e.g., attorney from FL-120 → attorney fields)
4. Skip empty fields or template text
5. Focus on accuracy over completeness

**Document Content:**
{text_content[:5000]}

Please return extracted data in this JSON format:

```json
{{
  "extracted_data": {{
    "exact_field_name": "extracted_value"
  }},
  "confidence_scores": {{
    "exact_field_name": 0.9
  }}
}}
```"""

    return prompt

# Integration function to patch the existing system
def patch_prompts_in_gui():
    """
    Instructions for patching the GUI with improved prompts
    """
    print("""
🔧 To improve AI extraction in python_form_filler3.py:

1. Replace the prompt in the _extract_with_openai method (around line 279) with create_improved_openai_prompt()
2. Replace the prompt in the _extract_with_anthropic method (around line 420) with create_improved_anthropic_prompt()
3. Ensure field names are passed correctly to the AI

The improved prompts:
- Use exact field names instead of numbers
- Give clearer extraction examples
- Focus on legal document structure
- Provide better context about FL-120 vs FL-142 roles
""")

if __name__ == "__main__":
    patch_prompts_in_gui()
