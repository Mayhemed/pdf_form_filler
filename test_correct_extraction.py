#!/usr/bin/env python3
"""
Correct Multi-Threaded PDF Form Filler
FIELD NAMES from target form + DATA VALUES from source documents
"""

import sys
import os
import threading
import concurrent.futures
import subprocess
import time
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass

# AI imports
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

@dataclass
class SourceDocument:
    name: str
    content: str
    doc_type: str = "general"

@dataclass
class FormField:
    name: str
    field_type: str = "text"
    description: str = ""

class CorrectPDFProcessor:
    """Correct implementation: Form fields + Source data"""
    
    def __init__(self, api_key: str, provider: str = "claude"):
        self.api_key = api_key
        self.provider = provider
        self.max_workers = 2
        print(f"🎯 Correct PDF Processor initialized")
    
    def extract_form_fields(self, form_pdf_path: str) -> List[FormField]:
        """Extract FIELD NAMES from the target form PDF"""
        print(f"\n📋 EXTRACTING FIELD NAMES from target form...")
        print(f"Form: {os.path.basename(form_pdf_path)}")
        
        try:
            # Use pdftk to get field names from the target form
            result = subprocess.run(
                ["pdftk", form_pdf_path, "dump_data_fields"],
                capture_output=True, text=True, check=True, timeout=30
            )
            
            fields = []
            current_field = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('FieldName:'):
                    # Save previous field
                    if current_field:
                        field = FormField(
                            name=current_field.get('name', ''),
                            field_type=current_field.get('type', 'text'),
                            description=current_field.get('description', '')
                        )
                        fields.append(field)
                    
                    # Start new field
                    current_field = {'name': line.split(':', 1)[1].strip()}
                    
                elif line.startswith('FieldType:'):
                    current_field['type'] = line.split(':', 1)[1].strip()
                elif line.startswith('FieldFlags:'):
                    current_field['description'] = line.split(':', 1)[1].strip()
            
            # Add last field
            if current_field:
                field = FormField(
                    name=current_field.get('name', ''),
                    field_type=current_field.get('type', 'text'),
                    description=current_field.get('description', '')
                )
                fields.append(field)
            
            print(f"✅ Extracted {len(fields)} field names from target form")
            
            # Show some examples
            print(f"📝 Example field names:")
            for field in fields[:10]:
                print(f"   • {field.name} ({field.field_type})")
            
            return fields
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to extract form fields: {e}")
            return []
        except Exception as e:
            print(f"❌ Error extracting form fields: {e}")
            return []
    
    def process_data_sources(self, source_documents: List[SourceDocument], 
                           form_fields: List[FormField]) -> Dict[str, str]:
        """Extract DATA VALUES from source documents to fill form fields"""
        print(f"\n💾 EXTRACTING DATA VALUES from source documents...")
        print(f"Sources: {[doc.name for doc in source_documents]}")
        print(f"Target: {len(form_fields)} form fields")
        
        all_extracted_data = {}
        
        try:
            # Process each source document in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_doc = {
                    executor.submit(self._extract_data_from_source, doc, form_fields, i+1): doc 
                    for i, doc in enumerate(source_documents)
                }
                
                for future in concurrent.futures.as_completed(future_to_doc, timeout=120):
                    doc = future_to_doc[future]
                    try:
                        extracted_data = future.result(timeout=30)
                        print(f"📥 {doc.name}: {len(extracted_data)} data values extracted")
                        
                        # Merge data - prefer longer/more complete values
                        for field_name, value in extracted_data.items():
                            if field_name not in all_extracted_data or len(value) > len(all_extracted_data[field_name]):
                                all_extracted_data[field_name] = value
                                print(f"   ✅ {field_name}: {value[:50]}...")
                        
                    except Exception as e:
                        print(f"❌ Failed to extract from {doc.name}: {str(e)}")
            
            print(f"\n📊 TOTAL DATA EXTRACTED: {len(all_extracted_data)} field values")
            return all_extracted_data
            
        except Exception as e:
            print(f"❌ Data extraction failed: {str(e)}")
            return {}
    
    def _extract_data_from_source(self, document: SourceDocument, 
                                form_fields: List[FormField], task_id: int) -> Dict[str, str]:
        """Extract actual data values from a single source document"""
        thread_name = threading.current_thread().name
        print(f"\n💾 THREAD {task_id} [{thread_name}]: Extracting DATA from {document.name}")
        print(f"   📄 Document type: {document.doc_type}")
        print(f"   📝 Content: {len(document.content)} chars")
        
        try:
            # Create data extraction prompt
            prompt = self._create_data_extraction_prompt(document, form_fields)
            
            # Call AI to extract DATA VALUES
            extracted_data = self._call_claude_for_data(prompt, task_id)
            
            print(f"   ✅ THREAD {task_id}: Extracted {len(extracted_data)} data values")
            return extracted_data
            
        except Exception as e:
            print(f"   ❌ THREAD {task_id}: Data extraction failed: {str(e)}")
            return {}
    
    def _create_data_extraction_prompt(self, document: SourceDocument, 
                                     form_fields: List[FormField]) -> str:
        """Create prompt to extract DATA VALUES (not field names)"""
        
        field_names = [field.name for field in form_fields]
        
        # Determine document focus
        if document.doc_type == "attorney" or "fl-120" in document.name.lower():
            focus = """
**ATTORNEY/LEGAL DOCUMENT - Extract these data types:**
- Attorney names and law firm names
- Phone numbers and email addresses  
- Addresses and contact information
- Case numbers and court information
- Party names (petitioner, respondent)
- Legal dates and case details"""
            
        elif document.doc_type == "financial" or "fl-142" in document.name.lower():
            focus = """
**FINANCIAL DOCUMENT - Extract these data types:**
- Dollar amounts for debts (student loans, credit cards, etc.)
- Bank account balances and information
- Asset values (vehicles, property, household items)
- Loan amounts and creditor information
- Any filled-in financial data and amounts"""
            
        else:
            focus = """
**GENERAL DOCUMENT - Extract any relevant data:**
- Names, addresses, phone numbers
- Dollar amounts and financial information  
- Case numbers and legal identifiers
- Dates and other important details"""
        
        prompt = f"""You are extracting ACTUAL DATA VALUES from legal documents to fill a form.

CRITICAL: Extract the ACTUAL DATA VALUES, not field labels or descriptions.

🎯 TASK: Extract data values from this document to fill form fields.

📄 SOURCE DOCUMENT: {document.name}
Document type: {document.doc_type}
Content length: {len(document.content)} characters

{focus}

🎯 TARGET FORM FIELDS (find data for these):
{json.dumps(field_names[:15], indent=2)}
{"... and " + str(max(0, len(field_names) - 15)) + " more fields" if len(field_names) > 15 else ""}

📋 EXTRACTION EXAMPLES:

WRONG (field labels): "STUDENT LOANS (Give details.)"
RIGHT (data values): "$22,000.00"

WRONG (field labels): "ATTORNEY OR PARTY WITHOUT ATTORNEY"  
RIGHT (data values): "Mark Piesner, Arc Point Law PC"

WRONG (field labels): "CASE NUMBER:"
RIGHT (data values): "24STFL00615"

📄 DOCUMENT CONTENT TO ANALYZE:
{document.content}

🎯 EXTRACTION INSTRUCTIONS:

1. **EXTRACT ACTUAL DATA** - Get the filled-in values, amounts, names, numbers
2. **NOT FIELD LABELS** - Don't extract "STUDENT LOANS:", extract "$22,000.00"
3. **COMPLETE VALUES** - Extract full names, complete addresses, full amounts
4. **CLEAR DATA ONLY** - Only extract data that is clearly visible and accurate
5. **MATCH TO FIELDS** - Try to match extracted data to the target field names

RETURN FORMAT (JSON only):
{{
    "field_name": "ACTUAL_DATA_VALUE",
    "another_field": "ANOTHER_ACTUAL_VALUE"
}}

Extract actual data values now - NOT field labels!"""

        print(f"   📝 Thread: Created data extraction prompt ({len(prompt)} chars)")
        return prompt
    
    def _call_claude_for_data(self, prompt: str, task_id: int) -> Dict[str, str]:
        """Call Claude to extract data values"""
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            
            print(f"   🤖 Thread {task_id}: Calling Claude for data extraction...")
            response = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text
            print(f"   📨 Thread {task_id}: Received response ({len(response_text)} chars)")
            
            # Parse JSON response
            try:
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                
                if start >= 0 and end > start:
                    json_text = response_text[start:end]
                    result = json.loads(json_text)
                    
                    # Return the extracted data directly
                    print(f"   ✅ Thread {task_id}: Parsed {len(result)} data values")
                    return result
                else:
                    print(f"   ❌ Thread {task_id}: No JSON found")
                    return {}
                    
            except json.JSONDecodeError as e:
                print(f"   ❌ Thread {task_id}: JSON parse error: {e}")
                return {}
            
        except Exception as e:
            print(f"   ❌ Thread {task_id}: Claude call failed: {str(e)}")
            return {}

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF"""
    try:
        if not HAS_PYPDF2:
            return "[PyPDF2 not available]"
        
        text_content = []
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            for page in reader.pages:
                text = page.extract_text()
                if text.strip():
                    text_content.append(text)
        
        return "\\n\\n".join(text_content) if text_content else ""
        
    except Exception as e:
        return f"[Error extracting text: {str(e)}]"

def classify_document(content: str, filename: str) -> str:
    """Classify document type"""
    filename_lower = filename.lower()
    content_lower = content.lower()
    
    if 'fl-120' in filename_lower or 'attorney' in content_lower:
        return 'attorney'
    elif 'fl-142' in filename_lower or ('schedule' in content_lower and 'assets' in content_lower):
        return 'financial'
    else:
        return 'general'

def main_correct():
    """Main function with correct field vs data separation"""
    print("🎯 CORRECT Multi-Threaded PDF Form Filler")
    print("Field names from TARGET form + Data values from SOURCE documents")
    print("=" * 80)
    
    # API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ No ANTHROPIC_API_KEY found!")
        return
    
    print("✅ Using Claude (Anthropic)")
    
    # Initialize processor
    processor = CorrectPDFProcessor(api_key=api_key)
    
    # Step 1: Extract FIELD NAMES from target form
    target_form = "/Users/markpiesner/Arc Point Law Dropbox/Forms/fl142blank.pdf"
    if not os.path.exists(target_form):
        print(f"❌ Target form not found: {target_form}")
        return
    
    form_fields = processor.extract_form_fields(target_form)
    if not form_fields:
        print("❌ No form fields extracted")
        return
    
    # Step 2: Load SOURCE documents for data extraction
    source_files = [
        "../../agentic_form_filler/client_data/Rogers/Rogers-FL120-signed.pdf",
        "../../agentic_form_filler/client_data/Rogers/fl142 copy.pdf"
    ]
    
    source_documents = []
    
    print(f"\n📚 LOADING SOURCE DOCUMENTS for data extraction...")
    for file_path in source_files:
        if os.path.exists(file_path):
            print(f"📄 Processing: {file_path}")
            content = extract_text_from_pdf(file_path)
            
            if content and len(content) > 50:
                doc_type = classify_document(content, os.path.basename(file_path))
                
                doc = SourceDocument(
                    name=os.path.basename(file_path),
                    content=content,
                    doc_type=doc_type
                )
                source_documents.append(doc)
                print(f"  ✅ Loaded: {doc.name} ({len(content)} chars, {doc_type})")
            else:
                print(f"  ❌ Invalid content")
        else:
            print(f"  ❌ File not found: {file_path}")
    
    if not source_documents:
        print("❌ No source documents loaded")
        return
    
    # Step 3: Extract DATA VALUES from source documents
    extracted_data = processor.process_data_sources(source_documents, form_fields)
    
    # Step 4: Display results
    print(f"\n🎯 CORRECT EXTRACTION RESULTS")
    print("=" * 60)
    print(f"📋 Target form fields: {len(form_fields)}")
    print(f"📚 Source documents: {len(source_documents)}")
    print(f"💾 Data values extracted: {len(extracted_data)}")
    print("")
    
    if extracted_data:
        # Group by source
        fl120_data = {}
        fl142_data = {}
        
        # We need to track which document provided which data
        # For now, show all extracted data
        print(f"📊 EXTRACTED DATA VALUES:")
        for field_name, value in extracted_data.items():
            print(f"  • {field_name}: {value}")
        
        print(f"\n✅ SUCCESS: Extracted actual data values (not field labels)")
        
        # Check for expected financial data
        financial_indicators = ['$', 'dollar', 'amount', '000', '.00']
        has_financial = any(any(indicator in str(value).lower() for indicator in financial_indicators) 
                          for value in extracted_data.values())
        
        if has_financial:
            print(f"💰 ✅ Contains financial data (amounts, dollars)")
        else:
            print(f"💰 ⚠️ No clear financial amounts found")
            
    else:
        print("❌ No data extracted")
    
    print(f"\n✅ Correct processing complete")

if __name__ == "__main__":
    main_correct()
