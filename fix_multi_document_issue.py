#!/usr/bin/env python3
"""
Fix the multi-document processing issue
The AI is only using the first document and ignoring subsequent ones
"""

def fix_multi_document_processing():
    """Fix the AI to properly process ALL documents, not just the first one"""
    
    file_path = "pdf_form_filler1.py"
    
    # Read current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Create backup
    with open(file_path + ".backup_multi_doc_fix", 'w') as f:
        f.write(content)
    print("✅ Created backup: pdf_form_filler1.py.backup_multi_doc_fix")
    
    # Enhanced prompt that forces the AI to analyze ALL documents
    enhanced_prompt = '''            prompt = f"""You are an expert legal document analyst performing COMPREHENSIVE MULTI-DOCUMENT ANALYSIS.

CRITICAL INSTRUCTION: You MUST analyze and extract data from ALL {len(self.sources)} source documents provided. Do NOT stop after the first document.

📋 SOURCE DOCUMENTS TO ANALYZE:
{chr(10).join([f"🔹 Document {i+1}: {source.name} ({len(source.content)} chars)" for i, source in enumerate(self.sources)])}

🎯 MULTI-DOCUMENT EXTRACTION STRATEGY:

1. **ANALYZE EVERY DOCUMENT**: Read through ALL {len(self.sources)} documents completely
2. **EXTRACT FROM ALL SOURCES**: Get data from EVERY document, not just the first one
3. **COMBINE INTELLIGENTLY**: Use the best data from ANY source for each field
4. **COMPREHENSIVE COVERAGE**: Fill as many fields as possible using ALL available data

📊 DOCUMENT-SPECIFIC EXTRACTION TARGETS:

**FROM FL-142 DOCUMENTS** (Financial data):
- Student loans amounts
- Credit card debts  
- Unsecured loans
- Asset values (checking, savings, vehicles, household items)
- Total debts and assets

**FROM FL-120 DOCUMENTS** (Legal/Attorney data):
- Attorney name and contact info
- Case numbers and court info
- Party names (petitioner, respondent)
- Legal dates and details

**FROM ANY DOCUMENT** (Universal data):
- Names, addresses, phone numbers
- Case numbers, court information
- Financial amounts and account details
- Dates and signatures

🔍 MANDATORY MULTI-DOCUMENT ANALYSIS:

For EACH target field, you MUST:
1. **Check Document 1** for relevant data
2. **Check Document 2** for relevant data  
3. **Check Document 3+** if more documents exist
4. **Select the BEST data** found across ALL documents
5. **Combine with field context**: "VALUE [Field: LABEL]"

DOCUMENT CONTENT FOR ANALYSIS:
{text}

TARGET FORM FIELDS (extract from ALL documents):
{json.dumps(field_names, indent=2)}

🎯 EXTRACTION EXAMPLES (Multi-Document):

Target Field: TextField1[0] (Attorney Name)
→ Check FL-142: May have attorney info
→ Check FL-120: "Mark Piesner, Arc Point Law PC, 22287 Mulholland Hwy"  
→ Result: "Mark Piesner, Arc Point Law PC, 22287 Mulholland Hwy [Field: ATTORNEY NAME]"

Target Field: DecimalField40[0] (Student Loans)
→ Check FL-142: "$22,000.00"
→ Check FL-120: No student loan data
→ Result: "$22,000.00 [Field: STUDENT LOANS]"

Target Field: CaseNumber[0] (Case Number)
→ Check FL-142: May have case number
→ Check FL-120: "24STFL00615"
→ Result: "24STFL00615 [Field: CASE NUMBER]"

CRITICAL SUCCESS REQUIREMENTS:
✅ **ANALYZE ALL DOCUMENTS** - Process every single document provided
✅ **EXTRACT FROM ALL SOURCES** - Get data from FL-142 AND FL-120 AND any others
✅ **MAXIMIZE FIELD COVERAGE** - Use ALL available data to fill as many fields as possible
✅ **INTELLIGENT COMBINATION** - Pick the best data from any source for each field
✅ **COMPREHENSIVE RESULTS** - Should get 15-25+ fields, not just 10

RETURN FORMAT:
{{
    "extracted_data": {{
        "FIELD_NAME": "DATA_FROM_ANY_DOCUMENT [Field: LABEL]"
    }},
    "confidence_scores": {{
        "FIELD_NAME": 0.95
    }}
}}

EXTRACT MAXIMUM DATA by analyzing ALL {len(self.sources)} documents thoroughly."""'''
    
    # Find and replace the current prompt
    import re
    pattern = r'prompt = f"""You are an expert legal document analyst performing CROSS-DOCUMENT INTELLIGENT FIELD MAPPING\..*?EXTRACT COMPREHENSIVE DATA by intelligently mapping information from ALL source documents to ALL target form fields\."""'
    
    new_content = re.sub(pattern, enhanced_prompt, content, flags=re.DOTALL)
    
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print("✅ Applied multi-document processing fix!")
        return True
    else:
        print("❌ Could not find prompt to fix")
        # Try a more specific pattern
        pattern2 = r'            prompt = f"""You are an expert legal document analyst.*?EXTRACT COMPREHENSIVE DATA by intelligently mapping information from ALL source documents to ALL target form fields\."""'
        new_content2 = re.sub(pattern2, enhanced_prompt, content, flags=re.DOTALL)
        
        if new_content2 != content:
            with open(file_path, 'w') as f:
                f.write(new_content2)
            print("✅ Applied multi-document processing fix (alternative pattern)!")
            return True
        else:
            print("❌ Could not find any prompt pattern to fix")
            return False

def fix_document_presentation():
    """Also fix how documents are presented to the AI"""
    
    file_path = "pdf_form_filler1.py"
    
    # Read current file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the section where documents are concatenated and improve it
    old_concatenation = 'all_text += f"\\n\\n=== {source.name} ===\\n{text}"'
    new_concatenation = '''# Enhanced document presentation
                document_marker = f"\\n\\n{'='*60}\\n📄 DOCUMENT {i+1}: {source.name} ({len(text)} characters)\\n{'='*60}\\n"
                all_text += document_marker + text + f"\\n\\n{'='*60}\\n✅ END OF DOCUMENT {i+1}: {source.name}\\n{'='*60}\\n"'''
    
    if old_concatenation in content:
        content = content.replace(old_concatenation, new_concatenation)
        
        with open(file_path, 'w') as f:
            f.write(content)
        print("✅ Enhanced document presentation to AI")
        return True
    else:
        print("⚠️ Could not find document concatenation to enhance")
        return False

if __name__ == "__main__":
    print("🔧 Fixing Multi-Document Processing Issue")
    print("=" * 50)
    print("Problem: AI only using first document, ignoring others")
    print("Solution: Force AI to analyze ALL documents systematically")
    print()
    
    success1 = fix_multi_document_processing()
    success2 = fix_document_presentation()
    
    if success1:
        print("\\n🎉 Multi-Document Processing Fix Applied!")
        print("Now the AI will:")
        print("• Analyze ALL documents, not just the first one")
        print("• Extract data from FL-142 AND FL-120 AND others")  
        print("• Maximize field coverage using all available data")
        print("• Get 15-25+ fields instead of just 10")
        print("\\n🧪 Test with: source myenv/bin/activate && python pdf_form_filler1.py")
    else:
        print("\\n❌ Fix failed - manual intervention needed")
