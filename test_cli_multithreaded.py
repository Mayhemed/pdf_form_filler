#!/usr/bin/env python3
"""
Command Line Multi-Threaded PDF Form Filler
Run this to see real-time output and debug hanging issues
"""

import sys
import os
import threading
import concurrent.futures
import time
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class CLIDocument:
    name: str
    content: str
    doc_type: str = "general"

class CLIMultiThreadProcessor:
    """Command-line processor with verbose debugging"""
    
    def __init__(self, api_key: str = "", provider: str = "pattern"):
        self.api_key = api_key
        self.provider = provider
        self.max_workers = 2
        print(f"🔧 CLI Processor initialized: {provider}, workers: {self.max_workers}")
    
    def process_documents_cli(self, documents: List[CLIDocument], form_fields: List[str]) -> Dict:
        """Process documents with real-time debugging output"""
        print(f"\n🔄 CLI MULTI-THREADING STARTED")
        print(f"📊 Processing {len(documents)} documents")
        print(f"🎯 Target fields: {len(form_fields)}")
        print(f"⚡ Max workers: {self.max_workers}")
        
        start_time = time.time()
        all_results = {}
        
        try:
            print(f"\n🚀 Creating ThreadPoolExecutor...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                print(f"✅ ThreadPoolExecutor created")
                
                print(f"\n📋 Submitting {len(documents)} tasks...")
                future_to_doc = {}
                
                for i, doc in enumerate(documents):
                    print(f"  📤 Submitting task {i+1}: {doc.name}")
                    future = executor.submit(self._process_single_cli, doc, form_fields, i+1)
                    future_to_doc[future] = doc
                    print(f"  ✅ Task {i+1} submitted")
                
                print(f"\n⏳ Waiting for task completion...")
                
                # Process results with timeout and real-time updates
                completed_count = 0
                for future in concurrent.futures.as_completed(future_to_doc, timeout=60):
                    doc = future_to_doc[future]
                    completed_count += 1
                    
                    print(f"\n📥 Task {completed_count}/{len(documents)} completed: {doc.name}")
                    
                    try:
                        result = future.result(timeout=10)
                        print(f"  ✅ Success: {len(result)} fields extracted")
                        
                        # Merge results
                        for field, value in result.items():
                            all_results[field] = f"{value} [Source: {doc.name}]"
                            print(f"    • {field}: {value}")
                        
                    except concurrent.futures.TimeoutError:
                        print(f"  ⏰ Task timeout: {doc.name}")
                    except Exception as e:
                        print(f"  ❌ Task failed: {doc.name} - {str(e)}")
                
                print(f"\n🎉 All tasks completed!")
                
        except concurrent.futures.TimeoutError:
            print(f"\n⏰ TIMEOUT: Overall processing took too long")
        except Exception as e:
            print(f"\n❌ PROCESSING ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
        
        elapsed = time.time() - start_time
        print(f"\n📊 PROCESSING SUMMARY:")
        print(f"   Total time: {elapsed:.2f} seconds")
        print(f"   Total fields: {len(all_results)}")
        print(f"   Success rate: {len(all_results) > 0}")
        
        return all_results
    
    def _process_single_cli(self, document: CLIDocument, form_fields: List[str], task_id: int) -> Dict[str, str]:
        """Process single document with detailed logging"""
        thread_name = threading.current_thread().name
        print(f"\n🧵 THREAD {task_id} [{thread_name}] STARTED: {document.name}")
        print(f"   📄 Content length: {len(document.content)} chars")
        print(f"   📝 Document type: {document.doc_type}")
        print(f"   🎯 Target fields: {len(form_fields)}")
        
        start_time = time.time()
        
        try:
            print(f"   🔍 Starting extraction...")
            
            if self.provider == "pattern":
                print(f"   📋 Using pattern matching...")
                result = self._pattern_extract_cli(document.content, form_fields, task_id)
            else:
                print(f"   🤖 Using AI processing...")
                result = self._ai_extract_cli(document.content, form_fields, task_id)
            
            elapsed = time.time() - start_time
            print(f"   ✅ THREAD {task_id} COMPLETED: {len(result)} fields in {elapsed:.2f}s")
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ THREAD {task_id} FAILED: {str(e)} after {elapsed:.2f}s")
            import traceback
            traceback.print_exc()
            return {}
    
    def _pattern_extract_cli(self, content: str, form_fields: List[str], task_id: int) -> Dict[str, str]:
        """Pattern extraction with debugging"""
        import re
        
        print(f"   🔍 Thread {task_id}: Starting pattern matching...")
        
        extracted = {}
        content_lower = content.lower()
        
        # Enhanced patterns
        patterns = {
            'case_number': r'case\s*(?:number|no\.?)\s*:?\s*([A-Z0-9]+)',
            'attorney_name': r'(?:attorney|counsel).*?:?\s*([A-Za-z\s,\.]+)',
            'phone': r'(?:phone|tel|telephone)\s*(?:number|no\.?)?\s*:?\s*(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})',
            'email': r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            'petitioner': r'petitioner\s*:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            'respondent': r'respondent\s*:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            'student_loans': r'student\s+loans?\s*:?\s*\$?([0-9,]+\.?[0-9]*)',
            'credit_cards': r'credit\s+cards?\s*:?\s*\$?([0-9,]+\.?[0-9]*)',
            'checking': r'checking\s*(?:account)?\s*:?\s*\$?([0-9,]+\.?[0-9]*)',
            'savings': r'savings\s*(?:account)?\s*:?\s*\$?([0-9,]+\.?[0-9]*)'
        }
        
        for field_type, pattern in patterns.items():
            print(f"     🔍 Thread {task_id}: Checking {field_type}...")
            
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                value = matches[0].strip()
                extracted[field_type] = value
                print(f"     ✅ Thread {task_id}: Found {field_type} = {value}")
            else:
                print(f"     ⭕ Thread {task_id}: No match for {field_type}")
        
        print(f"   📊 Thread {task_id}: Pattern extraction complete - {len(extracted)} fields")
        return extracted
    
    def _ai_extract_cli(self, content: str, form_fields: List[str], task_id: int) -> Dict[str, str]:
        """AI extraction with debugging (placeholder)"""
        print(f"   🤖 Thread {task_id}: AI extraction not implemented yet")
        print(f"   📋 Thread {task_id}: Falling back to pattern matching...")
        return self._pattern_extract_cli(content, form_fields, task_id)

def extract_text_cli(pdf_path: str) -> str:
    """Extract text with debugging"""
    print(f"📄 Extracting text from: {os.path.basename(pdf_path)}")
    
    try:
        import PyPDF2
        print("  ✅ Using PyPDF2...")
        
        text_content = []
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            print(f"  📊 PDF has {len(reader.pages)} pages")
            
            for i, page in enumerate(reader.pages):
                print(f"  📖 Reading page {i+1}...")
                text = page.extract_text()
                if text.strip():
                    text_content.append(text)
                    print(f"    ✅ Page {i+1}: {len(text)} characters")
                else:
                    print(f"    ⭕ Page {i+1}: No text")
        
        if text_content:
            full_text = "\\n\\n".join(text_content)
            print(f"  🎉 Total extracted: {len(full_text)} characters")
            return full_text
        else:
            print("  ❌ No text extracted")
            return ""
            
    except ImportError:
        print("  ❌ PyPDF2 not available")
        return "[PyPDF2 not available]"
    except Exception as e:
        print(f"  ❌ Extraction failed: {str(e)}")
        return f"[Error: {str(e)}]"

def classify_document_cli(content: str, filename: str) -> str:
    """Classify document with debugging"""
    print(f"🏷️  Classifying: {filename}")
    
    content_lower = content.lower()
    filename_lower = filename.lower()
    
    if 'fl-142' in filename_lower or 'schedule of assets' in content_lower:
        doc_type = 'financial'
    elif 'fl-120' in filename_lower or 'attorney' in content_lower:
        doc_type = 'attorney'
    else:
        doc_type = 'general'
    
    print(f"  🏷️  Type: {doc_type}")
    return doc_type

def main_cli():
    """Main CLI interface"""
    print("🚀 CLI Multi-Threaded PDF Form Filler")
    print("=" * 60)
    
    # Hardcoded test with your files for debugging
    test_files = [
        "../../agentic_form_filler/client_data/Rogers/Rogers-FL120-signed.pdf",
        "../../agentic_form_filler/client_data/Rogers/fl142 copy.pdf"
    ]
    
    documents = []
    
    # Load documents
    print(f"\n📚 LOADING DOCUMENTS...")
    for file_path in test_files:
        if os.path.exists(file_path):
            print(f"\n📄 Processing: {file_path}")
            content = extract_text_cli(file_path)
            
            if content and len(content) > 50:  # Valid content
                doc_type = classify_document_cli(content, os.path.basename(file_path))
                
                doc = CLIDocument(
                    name=os.path.basename(file_path),
                    content=content,
                    doc_type=doc_type
                )
                documents.append(doc)
                print(f"  ✅ Added: {doc.name} ({len(content)} chars, {doc_type})")
            else:
                print(f"  ❌ Invalid content: {content[:100]}...")
        else:
            print(f"  ❌ File not found: {file_path}")
    
    if not documents:
        print("\n❌ No valid documents loaded")
        return
    
    print(f"\n📊 LOADED {len(documents)} DOCUMENTS:")
    for i, doc in enumerate(documents):
        print(f"  {i+1}. {doc.name} ({doc.doc_type}) - {len(doc.content)} chars")
    
    # Dummy form fields
    form_fields = [
        "attorney_name", "case_number", "petitioner", "respondent",
        "phone", "email", "student_loans", "credit_cards"
    ]
    
    print(f"\n🎯 TARGET FIELDS: {form_fields}")
    
    # Process documents
    processor = CLIMultiThreadProcessor(provider="pattern")
    results = processor.process_documents_cli(documents, form_fields)
    
    # Display final results
    print(f"\n🎉 FINAL RESULTS:")
    print("=" * 50)
    
    if results:
        for field, value in results.items():
            print(f"• {field}: {value}")
    else:
        print("❌ No results extracted")
    
    print(f"\n✅ CLI testing complete")

if __name__ == "__main__":
    main_cli()
