#!/usr/bin/env python3
"""
Apply the enhanced extraction prompt to pdf_form_filler1.py
This preserves current label extraction AND adds filled data extraction
"""

import re

def enhance_anthropic_prompt():
    """Enhance the Anthropic extraction prompt in pdf_form_filler1.py"""
    
    file_path = "pdf_form_filler1.py"
    
    # Read the current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Create backup
    with open(file_path + ".backup_before_enhancement", 'w') as f:
        f.write(content)
    print("✅ Created backup: pdf_form_filler1.py.backup_before_enhancement")
    
    # Enhanced prompt text that preserves labels AND adds data
    enhanced_prompt = '''prompt = f"""You are analyzing legal documents to extract COMPREHENSIVE FORM DATA including both field labels and filled-in values.

TARGET EXTRACTION: For each form field, extract BOTH the field label/description AND any filled-in data values.

EXTRACTION STRATEGY:

1. FIELD LABELS/TITLES (preserve current functionality):
   - Extract field descriptions, labels, and instructions
   - Example: "ATTORNEY OR PARTY WITHOUT ATTORNEY (Name and Address):"
   - Example: "CASE NUMBER:"
   - Example: "PETITIONER:"

2. FILLED-IN DATA VALUES (new enhanced functionality):
   - Look for actual user-entered data near each field
   - Names: "Mark Piesner", "TAHIRA FRANCIS", "SHAWN ROGERS"
   - Case numbers: "24STFL00615"  
   - Addresses: "22287 Mulholland Hwy, Calabasas CA 91302"
   - Phone numbers: "(818) 638-4456"
   - Email addresses: "mark@arcpointlaw.com"
   - Financial amounts: "$22,000.00", "$25,000.00"
   - Dates: "December 12, 2024"

3. SMART FIELD MAPPING:
   For each form field, provide the BEST available information:
   - If field has both label AND data: combine them intelligently
   - If field has only label: provide the label (current behavior)
   - If field has only data: provide the data value
   - If field appears empty: provide the label for reference

EXAMPLES OF ENHANCED EXTRACTION:

Field: TextField1[0] (Attorney Name field)
Current: "ATTORNEY OR PARTY WITHOUT ATTORNEY (Name and Address):"
Enhanced: "Mark Piesner, Arc Point Law PC, 22287 Mulholland Hwy, Calabasas CA 91302 [Field: ATTORNEY OR PARTY WITHOUT ATTORNEY]"

Field: CaseNumber[0] (Case Number field)  
Current: "CASE NUMBER:"
Enhanced: "24STFL00615 [Field: CASE NUMBER]"

Field: Party1[0] (Petitioner field)
Current: "PETITIONER:"
Enhanced: "TAHIRA FRANCIS [Field: PETITIONER]"

DOCUMENT CONTENT TO ANALYZE:
{text[:4000]}

AVAILABLE FORM FIELDS (extract enhanced data for these exact field names):
{json.dumps(field_names[:20], indent=2)}

RETURN FORMAT - Enhanced JSON with both labels and data:

{{
    "extracted_data": {{
        "EXACT_FIELD_NAME": "FILLED_VALUE [Field: FIELD_LABEL]"
    }},
    "confidence_scores": {{
        "EXACT_FIELD_NAME": 0.95
    }}
}}

EXTRACTION RULES:
✅ KEEP current field label extraction (preserve existing functionality)
✅ ADD filled-in data values where available (new enhancement)
✅ COMBINE intelligently: "VALUE [Field: LABEL]" format when both exist
✅ USE exact field names from the list as keys
✅ IGNORE completely empty fields (no label, no data)
✅ PRIORITIZE actual user data over template text
✅ PROVIDE context by including field labels in brackets

Extract comprehensive data for AS MANY fields as possible, combining both labels and values."""'''
    
    # Find the current prompt in the Anthropic method and replace it
    # Look for the current prompt pattern
    pattern = r'prompt = f"""You are analyzing documents to extract comprehensive data for a PDF form\..*?Extract data for AS MANY fields as possible\."""'
    
    # Replace with enhanced prompt
    new_content = re.sub(pattern, enhanced_prompt, content, flags=re.DOTALL)
    
    if new_content != content:
        # Write the enhanced content
        with open(file_path, 'w') as f:
            f.write(new_content)
        print("✅ Enhanced Anthropic extraction prompt successfully!")
        return True
    else:
        print("❌ Could not find Anthropic prompt to enhance")
        return False

def enhance_openai_prompt():
    """Enhance the OpenAI extraction prompt in pdf_form_filler1.py"""
    
    file_path = "pdf_form_filler1.py"
    
    # Read the current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Enhanced OpenAI prompt
    enhanced_openai_prompt = '''prompt = f"""# Enhanced Legal Document Data Extraction

You are extracting COMPREHENSIVE form data from California family law documents, capturing BOTH field labels AND filled-in values.

## ENHANCED EXTRACTION APPROACH:

### 1. DUAL EXTRACTION STRATEGY:
- **Field Labels**: Extract form field descriptions and labels (current functionality)
- **Filled Data**: Extract actual user-entered values (new enhancement)
- **Smart Combination**: Merge both when available in format "VALUE [Field: LABEL]"

### 2. ATTORNEY INFORMATION (from FL-120 if present):
- Field Labels: "ATTORNEY OR PARTY WITHOUT ATTORNEY", "TELEPHONE NO:", "ATTORNEY FOR"
- Filled Data: "Mark Piesner", "(818) 638-4456", "mark@arcpointlaw.com"
- Enhanced Output: "Mark Piesner, Arc Point Law PC [Field: ATTORNEY OR PARTY WITHOUT ATTORNEY]"

### 3. CASE INFORMATION (from any source):
- Field Labels: "CASE NUMBER:", "PETITIONER:", "RESPONDENT:", "COUNTY OF"
- Filled Data: "24STFL00615", "TAHIRA FRANCIS", "SHAWN ROGERS", "LOS ANGELES"
- Enhanced Output: "24STFL00615 [Field: CASE NUMBER]"

### 4. FINANCIAL DATA (from FL-142 if present):
- Field Labels: "STUDENT LOANS", "CREDIT CARDS", "TOTAL DEBTS"
- Filled Data: "$22,000.00", "$3,042.81", "$64,225.81"
- Enhanced Output: "$22,000.00 [Field: STUDENT LOANS]"

## TARGET FIELDS (extract enhanced data for these exact field names):
{json.dumps(dict(zip(field_names, field_descriptions)), indent=2)}

## EXTRACTION RULES:

✅ **PRESERVE CURRENT FUNCTIONALITY** - Keep extracting field labels/descriptions
✅ **ADD FILLED VALUES** - Extract actual user-entered data where available  
✅ **SMART COMBINATION** - Use "VALUE [Field: LABEL]" format when both exist
✅ **EXACT FIELD NAMES** - Return exact field name from list as key
✅ **COMPREHENSIVE COVERAGE** - Extract both template and data elements
✅ **PRIORITIZE USER DATA** - When available, emphasize actual filled values
✅ **MAINTAIN CONTEXT** - Include field labels for reference even with data

## DOCUMENT CONTENT TO ANALYZE:
{text[:6000]}

Extract comprehensive data combining both field context and actual values for maximum utility.

RETURN FORMAT:

{{
    "extracted_data": {{
        "EXACT_FIELD_NAME": "FILLED_VALUE [Field: FIELD_LABEL]"
    }},
    "confidence_scores": {{
        "EXACT_FIELD_NAME": 0.95
    }}
}}

Focus on quality over quantity - extract what you can clearly identify with both context and data."""'''
    
    # Find and replace the OpenAI prompt
    pattern = r'prompt = f"""# Legal Document Data Extraction Task.*?Focus on quality over quantity - extract what you can clearly identify\."""'
    
    new_content = re.sub(pattern, enhanced_openai_prompt, content, flags=re.DOTALL)
    
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print("✅ Enhanced OpenAI extraction prompt successfully!")
        return True
    else:
        print("❌ Could not find OpenAI prompt to enhance")
        return False

def main():
    """Apply both enhancements"""
    print("🔧 Enhancing AI Extraction - Adding Filled Data to Field Labels")
    print("=" * 70)
    print("This enhancement preserves your current field label extraction")
    print("while adding extraction of actual filled-in values.")
    print()
    
    success_anthropic = enhance_anthropic_prompt()
    success_openai = enhance_openai_prompt()
    
    print(f"\n📊 Enhancement Results:")
    print(f"   Anthropic prompt: {'✅ Enhanced' if success_anthropic else '❌ Failed'}")
    print(f"   OpenAI prompt: {'✅ Enhanced' if success_openai else '❌ Failed'}")
    
    if success_anthropic or success_openai:
        print(f"\n🎉 Enhancement Applied Successfully!")
        print(f"Now your extraction will get:")
        print(f"   • Field labels (current): 'CASE NUMBER:'")
        print(f"   • PLUS filled data (new): '24STFL00615 [Field: CASE NUMBER]'")
        print(f"\n🧪 Test with: source myenv/bin/activate && python pdf_form_filler1.py")
    else:
        print(f"\n❌ Enhancement failed - prompts may have changed")
        print(f"Manual enhancement may be needed")

if __name__ == "__main__":
    main()
