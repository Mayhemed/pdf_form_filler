#!/usr/bin/env python3
"""
AI-Enabled CLI Multi-Threaded PDF Form Filler
Test with real AI processing to get proper results
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
    print("✅ Anthropic available")
except ImportError:
    HAS_ANTHROPIC = False
    print("⚠️ Anthropic not available")

try:
    import openai
    HAS_OPENAI = True
    print("✅ OpenAI available")
except ImportError:
    HAS_OPENAI = False
    print("⚠️ OpenAI not available")

@dataclass
class AIDocument:
    name: str
    content: str
    doc_type: str = "general"

class AIMultiThreadProcessor:
    """AI-enabled processor with specialized prompts per document type"""
    
    def __init__(self, api_key: str, provider: str = "claude"):
        self.api_key = api_key
        self.provider = provider
        self.max_workers = 2  # Conservative for API rate limits
        print(f"🤖 AI Processor initialized: {provider}, workers: {self.max_workers}")
    
    def process_documents_ai(self, documents: List[AIDocument], form_fields: List[str]) -> Dict:
        """Process documents with AI in parallel"""
        print(f"\n🤖 AI MULTI-THREADING STARTED")
        print(f"📊 Processing {len(documents)} documents with AI")
        print(f"🎯 Target fields: {len(form_fields)}")
        print(f"⚡ Max workers: {self.max_workers}")
        
        start_time = time.time()
        all_results = {}
        
        try:
            print(f"\n🚀 Creating ThreadPoolExecutor for AI processing...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                print(f"✅ ThreadPoolExecutor created")
                
                print(f"\n📋 Submitting {len(documents)} AI tasks...")
                future_to_doc = {}
                
                for i, doc in enumerate(documents):
                    print(f"  📤 Submitting AI task {i+1}: {doc.name} ({doc.doc_type})")
                    future = executor.submit(self._process_single_ai, doc, form_fields, i+1)
                    future_to_doc[future] = doc
                    print(f"  ✅ AI task {i+1} submitted")
                
                print(f"\n⏳ Waiting for AI task completion...")
                
                # Process results with timeout
                completed_count = 0
                for future in concurrent.futures.as_completed(future_to_doc, timeout=120):  # 2 minute timeout
                    doc = future_to_doc[future]
                    completed_count += 1
                    
                    print(f"\n📥 AI Task {completed_count}/{len(documents)} completed: {doc.name}")
                    
                    try:
                        result = future.result(timeout=30)  # 30 second per-task timeout
                        print(f"  🎉 AI Success: {len(result)} fields extracted")
                        
                        # Merge results with source attribution
                        for field, value in result.items():
                            # Check if this field has better data than existing
                            if field not in all_results or len(value) > len(all_results[field].split(' [Source:')[0]):
                                all_results[field] = f"{value} [Source: {doc.name}]"
                                print(f"    🆕 {field}: {value}")
                            else:
                                print(f"    📝 {field}: Keeping existing value")
                        
                    except concurrent.futures.TimeoutError:
                        print(f"  ⏰ AI Task timeout: {doc.name}")
                    except Exception as e:
                        print(f"  ❌ AI Task failed: {doc.name} - {str(e)}")
                
                print(f"\n🎉 All AI tasks completed!")
                
        except concurrent.futures.TimeoutError:
            print(f"\n⏰ TIMEOUT: AI processing took too long")
        except Exception as e:
            print(f"\n❌ AI PROCESSING ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
        
        elapsed = time.time() - start_time
        print(f"\n📊 AI PROCESSING SUMMARY:")
        print(f"   Total time: {elapsed:.2f} seconds")
        print(f"   Total fields: {len(all_results)}")
        print(f"   Success rate: {len(all_results) > 0}")
        
        return all_results
    
    def _process_single_ai(self, document: AIDocument, form_fields: List[str], task_id: int) -> Dict[str, str]:
        """Process single document with AI"""
        thread_name = threading.current_thread().name
        print(f"\n🤖 AI THREAD {task_id} [{thread_name}] STARTED: {document.name}")
        print(f"   📄 Content length: {len(document.content)} chars")
        print(f"   📝 Document type: {document.doc_type}")
        print(f"   🎯 Target fields: {len(form_fields)}")
        
        start_time = time.time()
        
        try:
            print(f"   🧠 Creating specialized AI prompt for {document.doc_type}...")
            prompt = self._create_specialized_prompt(document, form_fields, task_id)
            
            print(f"   🚀 Calling {self.provider} API...")
            if self.provider == "claude":
                result = self._call_claude_ai(prompt, task_id)
            elif self.provider == "openai":
                result = self._call_openai_ai(prompt, task_id)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")
            
            elapsed = time.time() - start_time
            print(f"   ✅ AI THREAD {task_id} COMPLETED: {len(result)} fields in {elapsed:.2f}s")
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ AI THREAD {task_id} FAILED: {str(e)} after {elapsed:.2f}s")
            import traceback
            traceback.print_exc()
            return {}
    
    def _create_specialized_prompt(self, document: AIDocument, form_fields: List[str], task_id: int) -> str:
        """Create document-type specific AI prompt"""
        
        # Get strategy based on document type
        if document.doc_type == "attorney":
            strategy = """
**ATTORNEY/LEGAL DOCUMENT STRATEGY:**
- Focus on attorney contact information and legal case details
- Extract complete attorney names, law firm names
- Look for phone numbers, email addresses, addresses
- Extract case numbers, court information
- Identify party names (petitioner, respondent)
- Legal dates and filing information"""
            
        elif document.doc_type == "financial":
            strategy = """
**FINANCIAL DOCUMENT STRATEGY:**
- Focus on monetary amounts, debts, and assets
- Extract student loans, credit cards, loans amounts
- Look for bank account balances (checking, savings)
- Property values, vehicle values
- Total debt and asset calculations
- Financial account details and numbers"""
            
        else:
            strategy = """
**GENERAL LEGAL DOCUMENT STRATEGY:**
- Extract any contact information
- Look for names, dates, addresses
- Financial information if present
- Case or matter identifiers
- Legal entity names and relationships"""
        
        prompt = f"""You are a legal document analyst performing FOCUSED SINGLE-DOCUMENT EXTRACTION.

🎯 CURRENT TASK: Analyze this {document.doc_type} document and extract relevant data.

📄 DOCUMENT TO ANALYZE:
   Name: {document.name}
   Type: {document.doc_type}
   Content: {len(document.content)} characters

🔍 EXTRACTION STRATEGY:
{strategy}

📋 TARGET FORM FIELDS:
{json.dumps(form_fields, indent=2)}

📄 DOCUMENT CONTENT:
{document.content}

🎯 EXTRACTION INSTRUCTIONS:

1. **ANALYZE THIS DOCUMENT ONLY** - Extract data that clearly exists in this document
2. **USE DOCUMENT-TYPE EXPERTISE** - Apply specialized knowledge for {document.doc_type} documents
3. **EXTRACT COMPLETE VALUES** - Get full names, complete addresses, full amounts
4. **HIGH QUALITY ONLY** - Only extract clear, obvious, accurate data
5. **PROPER FORMATTING** - Return clean, properly formatted values

RETURN FORMAT (JSON only):
{{
    "extracted_data": {{
        "FIELD_NAME": "COMPLETE_EXTRACTED_VALUE"
    }},
    "confidence_scores": {{
        "FIELD_NAME": 0.95
    }}
}}

Extract high-quality data from this {document.doc_type} document now."""

        print(f"   📝 Thread {task_id}: Created {len(prompt)} character prompt for {document.doc_type}")
        return prompt
    
    def _call_claude_ai(self, prompt: str, task_id: int) -> Dict[str, str]:
        """Call Claude API"""
        print(f"   🤖 Thread {task_id}: Calling Claude API...")
        
        if not HAS_ANTHROPIC:
            raise ImportError("Anthropic library not available")
        
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            
            print(f"   📡 Thread {task_id}: Sending request to Claude...")
            response = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text
            print(f"   📨 Thread {task_id}: Received Claude response ({len(response_text)} chars)")
            
            return self._parse_ai_response(response_text, task_id)
            
        except Exception as e:
            print(f"   ❌ Thread {task_id}: Claude API error: {str(e)}")
            raise
    
    def _call_openai_ai(self, prompt: str, task_id: int) -> Dict[str, str]:
        """Call OpenAI API"""
        print(f"   🤖 Thread {task_id}: Calling OpenAI API...")
        
        if not HAS_OPENAI:
            raise ImportError("OpenAI library not available")
        
        try:
            client = openai.OpenAI(api_key=self.api_key)
            
            print(f"   📡 Thread {task_id}: Sending request to OpenAI...")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000
            )
            
            response_text = response.choices[0].message.content
            print(f"   📨 Thread {task_id}: Received OpenAI response ({len(response_text)} chars)")
            
            return self._parse_ai_response(response_text, task_id)
            
        except Exception as e:
            print(f"   ❌ Thread {task_id}: OpenAI API error: {str(e)}")
            raise
    
    def _parse_ai_response(self, response_text: str, task_id: int) -> Dict[str, str]:
        """Parse AI response to extract structured data"""
        print(f"   🔍 Thread {task_id}: Parsing AI response...")
        
        try:
            # Find JSON in response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_text = response_text[start:end]
                print(f"   📊 Thread {task_id}: Found JSON ({len(json_text)} chars)")
                
                result = json.loads(json_text)
                extracted_data = result.get("extracted_data", {})
                
                print(f"   ✅ Thread {task_id}: Parsed {len(extracted_data)} fields")
                return extracted_data
            else:
                print(f"   ❌ Thread {task_id}: No JSON found in response")
                return {}
                
        except json.JSONDecodeError as e:
            print(f"   ❌ Thread {task_id}: JSON parse error: {str(e)}")
            return {}

def extract_text_ai(pdf_path: str) -> str:
    """Extract text for AI processing"""
    print(f"📄 Extracting text from: {os.path.basename(pdf_path)}")
    
    try:
        import PyPDF2
        
        text_content = []
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():
                    text_content.append(text)
        
        if text_content:
            full_text = "\\n\\n".join(text_content)
            print(f"  🎉 Extracted: {len(full_text)} characters")
            return full_text
        else:
            return ""
            
    except Exception as e:
        print(f"  ❌ Extraction failed: {str(e)}")
        return ""

def classify_document_ai(content: str, filename: str) -> str:
    """Classify document for AI processing"""
    content_lower = content.lower()
    filename_lower = filename.lower()
    
    if 'fl-142' in filename_lower or 'schedule of assets' in content_lower:
        return 'financial'
    elif 'fl-120' in filename_lower or 'attorney' in content_lower:
        return 'attorney'
    else:
        return 'general'

def main_ai():
    """Main AI CLI interface"""
    print("🤖 AI Multi-Threaded PDF Form Filler")
    print("=" * 60)
    
    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ No API key found!")
        print("Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable")
        api_key = input("Enter API key manually: ").strip()
    
    if not api_key:
        print("❌ No API key provided - cannot run AI processing")
        return
    
    # Determine provider
    if os.getenv("ANTHROPIC_API_KEY"):
        provider = "claude"
        print("✅ Using Claude (Anthropic)")
    elif os.getenv("OPENAI_API_KEY"):
        provider = "openai"
        print("✅ Using OpenAI")
    else:
        provider = "claude"  # Default
        print("⚠️ Defaulting to Claude")
    
    # Test files
    test_files = [
        "../../agentic_form_filler/client_data/Rogers/Rogers-FL120-signed.pdf",
        "../../agentic_form_filler/client_data/Rogers/fl142 copy.pdf"
    ]
    
    documents = []
    
    # Load documents
    print(f"\n📚 LOADING DOCUMENTS FOR AI PROCESSING...")
    for file_path in test_files:
        if os.path.exists(file_path):
            print(f"\n📄 Processing: {file_path}")
            content = extract_text_ai(file_path)
            
            if content and len(content) > 50:
                doc_type = classify_document_ai(content, os.path.basename(file_path))
                
                doc = AIDocument(
                    name=os.path.basename(file_path),
                    content=content,
                    doc_type=doc_type
                )
                documents.append(doc)
                print(f"  ✅ Ready for AI: {doc.name} ({len(content)} chars, {doc_type})")
            else:
                print(f"  ❌ Invalid content")
        else:
            print(f"  ❌ File not found: {file_path}")
    
    if not documents:
        print("\n❌ No valid documents loaded")
        return
    
    print(f"\n📊 LOADED {len(documents)} DOCUMENTS FOR AI PROCESSING:")
    for i, doc in enumerate(documents):
        print(f"  {i+1}. {doc.name} ({doc.doc_type}) - {len(doc.content)} chars")
    
    # Enhanced form fields for better AI extraction
    form_fields = [
        "attorney_name", "attorney_address", "attorney_phone", "attorney_email",
        "case_number", "court_name", "petitioner", "respondent", 
        "student_loans", "credit_cards", "checking_account", "savings_account",
        "marriage_date", "separation_date"
    ]
    
    print(f"\n🎯 AI TARGET FIELDS: {form_fields}")
    
    # Process with AI
    processor = AIMultiThreadProcessor(api_key=api_key, provider=provider)
    results = processor.process_documents_ai(documents, form_fields)
    
    # Display AI results
    print(f"\n🤖 AI EXTRACTION RESULTS:")
    print("=" * 60)
    
    if results:
        for field, value in results.items():
            print(f"• {field}: {value}")
    else:
        print("❌ No AI results extracted")
    
    print(f"\n✅ AI CLI testing complete")

if __name__ == "__main__":
    main_ai()
