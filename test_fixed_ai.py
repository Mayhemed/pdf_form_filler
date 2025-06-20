#!/usr/bin/env python3
"""
Fixed AI Multi-Threaded PDF Form Filler
Uses the PROVEN v3 prompt strategy in multi-threaded architecture
"""

import sys
import os
import threading
import concurrent.futures
import time
import json
from typing import Dict, List
from dataclasses import dataclass

# AI imports
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

@dataclass
class FixedDocument:
    name: str
    content: str
    doc_type: str = "general"

class FixedAIProcessor:
    """Uses the proven v3 prompt strategy in multi-threaded mode"""
    
    def __init__(self, api_key: str, provider: str = "claude"):
        self.api_key = api_key
        self.provider = provider
        self.max_workers = 2
        print(f"🔧 Fixed AI Processor: Using PROVEN v3 prompt strategy")
    
    def process_documents_fixed(self, documents: List[FixedDocument], form_fields: List[str]) -> Dict:
        """Process with proven v3 strategy in parallel"""
        print(f"\n🔧 FIXED AI PROCESSING - Using PROVEN v3 Strategy")
        print(f"📊 Processing {len(documents)} documents")
        
        # **KEY FIX**: Instead of specialized prompts per document,
        # use the PROVEN v3 multi-document approach that worked
        
        all_results = {}
        
        try:
            # **STRATEGY 1**: Try parallel processing first
            parallel_results = self._try_parallel_processing(documents, form_fields)
            
            if len(parallel_results) >= 5:  # Good results
                print("✅ Parallel processing successful")
                return parallel_results
            
            # **STRATEGY 2**: Fall back to proven v3 single-call approach
            print("📋 Falling back to proven v3 multi-document approach...")
            combined_results = self._try_combined_processing(documents, form_fields)
            
            return combined_results
            
        except Exception as e:
            print(f"❌ Fixed processing failed: {str(e)}")
            return {}
    
    def _try_parallel_processing(self, documents: List[FixedDocument], form_fields: List[str]) -> Dict:
        """Try parallel processing with PROVEN prompts"""
        print(f"🔄 Trying parallel processing...")
        
        all_results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_doc = {
                executor.submit(self._process_single_proven, doc, form_fields, i+1): doc 
                for i, doc in enumerate(documents)
            }
            
            for future in concurrent.futures.as_completed(future_to_doc, timeout=60):
                doc = future_to_doc[future]
                try:
                    result = future.result(timeout=30)
                    print(f"📥 {doc.name}: {len(result)} fields")
                    
                    for field, value in result.items():
                        all_results[field] = f"{value} [Source: {doc.name}]"
                        
                except Exception as e:
                    print(f"❌ {doc.name} failed: {str(e)}")
        
        return all_results
    
    def _try_combined_processing(self, documents: List[FixedDocument], form_fields: List[str]) -> Dict:
        """Use the PROVEN v3 multi-document strategy that worked"""
        print(f"🎯 Using PROVEN v3 multi-document strategy...")
        
        # Combine all documents like v3 did successfully
        combined_text = ""
        for i, doc in enumerate(documents):
            combined_text += f"\n\n=== SOURCE DOCUMENT {i+1}: {doc.name} ===\n{doc.content}"
        
        # Use the EXACT successful prompt strategy from v3
        prompt = self._create_proven_v3_prompt(documents, form_fields, combined_text)
        
        # Call AI with proven approach
        try:
            result = self._call_claude_proven(prompt)
            print(f"🎉 V3 strategy extracted: {len(result)} fields")
            return result
        except Exception as e:
            print(f"❌ V3 strategy failed: {str(e)}")
            return {}
    
    def _process_single_proven(self, document: FixedDocument, form_fields: List[str], task_id: int) -> Dict[str, str]:
        """Process single document with proven approach"""
        print(f"🔧 Thread {task_id}: Using proven single-doc approach for {document.name}")
        
        try:
            # Use simplified but proven prompt for single document
            prompt = f"""You are a legal document analyst extracting data for form filling.

DOCUMENT TO ANALYZE: {document.name}
DOCUMENT TYPE: {document.doc_type}
TARGET FIELDS: {form_fields}

DOCUMENT CONTENT:
{document.content}

Extract data for form fields. Return JSON:
{{
    "extracted_data": {{
        "field_name": "extracted_value"
    }}
}}

Focus on extracting clear, accurate data that exists in this document."""

            result = self._call_claude_simple(prompt, task_id)
            return result
            
        except Exception as e:
            print(f"❌ Thread {task_id} failed: {str(e)}")
            return {}
    
    def _create_proven_v3_prompt(self, documents: List[FixedDocument], form_fields: List[str], combined_text: str) -> str:
        """Create the EXACT prompt strategy that worked in v3"""
        
        # This is based on the successful v3 prompt from the project knowledge
        prompt = f"""You are an expert legal document analyst performing COMPREHENSIVE MULTI-DOCUMENT ANALYSIS.

CRITICAL INSTRUCTION: You MUST analyze and extract data from ALL {len(documents)} source documents provided. Do NOT stop after the first document.

📋 SOURCE DOCUMENTS TO ANALYZE:
{chr(10).join([f"🔹 Document {i+1}: {doc.name} ({len(doc.content)} chars)" for i, doc in enumerate(documents)])}

🎯 MULTI-DOCUMENT EXTRACTION STRATEGY:

1. **ANALYZE EVERY DOCUMENT**: Read through ALL {len(documents)} documents completely
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
{combined_text}

TARGET FORM FIELDS (extract from ALL documents):
{json.dumps(form_fields, indent=2)}

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

EXTRACT MAXIMUM DATA by analyzing ALL {len(documents)} documents thoroughly."""

        print(f"📝 Created PROVEN v3 prompt ({len(prompt)} chars)")
        return prompt
    
    def _call_claude_proven(self, prompt: str) -> Dict[str, str]:
        """Call Claude with proven approach"""
        print(f"🤖 Calling Claude with PROVEN v3 approach...")
        
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            
            response = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text
            print(f"📨 Received response ({len(response_text)} chars)")
            
            # Parse like v3 did
            result = self._parse_like_v3(response_text)
            return result
            
        except Exception as e:
            print(f"❌ Claude call failed: {str(e)}")
            return {}
    
    def _call_claude_simple(self, prompt: str, task_id: int) -> Dict[str, str]:
        """Simple Claude call for single document"""
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            
            response = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text
            return self._parse_like_v3(response_text)
            
        except Exception as e:
            print(f"❌ Thread {task_id} Claude call failed: {str(e)}")
            return {}
    
    def _parse_like_v3(self, response_text: str) -> Dict[str, str]:
        """Parse response the same way v3 did successfully"""
        try:
            # Find JSON like v3 did
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_text = response_text[start:end]
                result = json.loads(json_text)
                
                extracted_data = result.get("extracted_data", {})
                
                # Convert to simple format
                simple_result = {}
                for field, value in extracted_data.items():
                    # Clean up the value - remove [Field: ...] if present
                    clean_value = value.split(' [Field:')[0] if ' [Field:' in value else value
                    simple_result[field] = clean_value
                
                return simple_result
            else:
                return {}
                
        except json.JSONDecodeError:
            return {}

def extract_text_fixed(pdf_path: str) -> str:
    """Extract text like v3 did"""
    try:
        import PyPDF2
        
        text_content = []
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            for page in reader.pages:
                text = page.extract_text()
                if text.strip():
                    text_content.append(text)
        
        if text_content:
            return "\\n\\n".join(text_content)
        else:
            return ""
            
    except Exception as e:
        print(f"❌ Text extraction failed: {str(e)}")
        return ""

def main_fixed():
    """Main function using proven v3 approach"""
    print("🔧 FIXED AI Multi-Threaded PDF Form Filler")
    print("Using PROVEN v3 prompt strategy in multi-threaded architecture")
    print("=" * 70)
    
    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ No ANTHROPIC_API_KEY found!")
        return
    
    print("✅ Using Claude (Anthropic)")
    
    # Load documents like v3 did
    test_files = [
        "../../agentic_form_filler/client_data/Rogers/Rogers-FL120-signed.pdf",
        "../../agentic_form_filler/client_data/Rogers/fl142 copy.pdf"
    ]
    
    documents = []
    
    print(f"\n📚 LOADING DOCUMENTS (v3 style)...")
    for file_path in test_files:
        if os.path.exists(file_path):
            print(f"📄 Processing: {file_path}")
            content = extract_text_fixed(file_path)
            
            if content and len(content) > 50:
                # Classify like before
                if 'fl-142' in file_path.lower():
                    doc_type = 'financial'
                elif 'fl-120' in file_path.lower():
                    doc_type = 'attorney'
                else:
                    doc_type = 'general'
                
                doc = FixedDocument(
                    name=os.path.basename(file_path),
                    content=content,
                    doc_type=doc_type
                )
                documents.append(doc)
                print(f"  ✅ Loaded: {doc.name} ({len(content)} chars, {doc_type})")
            else:
                print(f"  ❌ Invalid content")
        else:
            print(f"  ❌ File not found: {file_path}")
    
    if not documents:
        print("❌ No documents loaded")
        return
    
    print(f"\n📊 LOADED {len(documents)} DOCUMENTS:")
    for i, doc in enumerate(documents):
        print(f"  {i+1}. {doc.name} ({doc.doc_type}) - {len(doc.content)} chars")
    
    # Use same field names that worked in v3
    form_fields = [
        "attorney_name", "attorney_address", "attorney_phone", "attorney_email",
        "case_number", "court_name", "petitioner", "respondent", 
        "student_loans", "credit_cards", "unsecured_loans", "checking_account", 
        "savings_account", "marriage_date", "separation_date", "vehicles",
        "household_furnishings", "real_estate", "other_debts"
    ]
    
    print(f"\n🎯 TARGET FIELDS: {len(form_fields)} fields")
    
    # Process with FIXED approach
    processor = FixedAIProcessor(api_key=api_key, provider="claude")
    results = processor.process_documents_fixed(documents, form_fields)
    
    # Display results
    print(f"\n🔧 FIXED AI EXTRACTION RESULTS:")
    print("=" * 60)
    
    if results:
        print(f"📊 TOTAL FIELDS EXTRACTED: {len(results)}")
        print("")
        
        # Group by source document
        fl120_fields = []
        fl142_fields = []
        other_fields = []
        
        for field, value in results.items():
            if "Rogers-FL120" in value:
                fl120_fields.append((field, value))
            elif "fl142" in value:
                fl142_fields.append((field, value))
            else:
                other_fields.append((field, value))
        
        if fl120_fields:
            print(f"📄 FROM FL-120 (Attorney Document): {len(fl120_fields)} fields")
            for field, value in fl120_fields:
                print(f"  • {field}: {value}")
            print("")
        
        if fl142_fields:
            print(f"💰 FROM FL-142 (Financial Document): {len(fl142_fields)} fields")
            for field, value in fl142_fields:
                print(f"  • {field}: {value}")
            print("")
        
        if other_fields:
            print(f"🔍 OTHER SOURCES: {len(other_fields)} fields")
            for field, value in other_fields:
                print(f"  • {field}: {value}")
        
        # Success analysis
        print(f"\n📊 SUCCESS ANALYSIS:")
        print(f"   FL-120 (Attorney) fields: {len(fl120_fields)}")
        print(f"   FL-142 (Financial) fields: {len(fl142_fields)}")
        print(f"   Total fields extracted: {len(results)}")
        
        if len(fl142_fields) > 0 and len(fl120_fields) > 0:
            print(f"   🎉 SUCCESS: Got data from BOTH documents!")
        elif len(fl142_fields) == 0:
            print(f"   ⚠️ ISSUE: No financial data from FL-142")
        elif len(fl120_fields) == 0:
            print(f"   ⚠️ ISSUE: No attorney data from FL-120")
        
    else:
        print("❌ No results extracted")
    
    print(f"\n✅ FIXED processing complete")

if __name__ == "__main__":
    main_fixed()
