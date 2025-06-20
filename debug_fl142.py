#!/usr/bin/env python3
"""
Debug FL-142 Content - See what's actually in the financial document
"""

import sys
import os

def extract_and_analyze_fl142():
    """Extract and analyze FL-142 content to see why no financial data was found"""
    
    print("🔍 FL-142 CONTENT ANALYSIS")
    print("=" * 50)
    
    fl142_path = "../../agentic_form_filler/client_data/Rogers/fl142 copy.pdf"
    
    if not os.path.exists(fl142_path):
        print(f"❌ File not found: {fl142_path}")
        return
    
    # Extract text
    try:
        import PyPDF2
        print(f"📄 Extracting text from FL-142...")
        
        text_content = []
        with open(fl142_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            print(f"📊 PDF has {len(reader.pages)} pages")
            
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text.strip():
                    text_content.append(f"=== PAGE {i+1} ===\n{text}")
                    print(f"📖 Page {i+1}: {len(text)} characters")
        
        full_text = "\n\n".join(text_content)
        print(f"🎉 Total extracted: {len(full_text)} characters")
        
        # Analyze content
        print(f"\n🔍 CONTENT ANALYSIS:")
        print("=" * 30)
        
        # Check for financial keywords
        financial_keywords = [
            'student loan', 'credit card', 'checking', 'savings', 'debt',
            'asset', 'loan', 'bank', 'account', 'balance', '$', 'dollar',
            'property', 'vehicle', 'real estate', 'mortgage', 'equity'
        ]
        
        found_keywords = []
        content_lower = full_text.lower()
        
        for keyword in financial_keywords:
            if keyword in content_lower:
                found_keywords.append(keyword)
        
        print(f"💰 Financial keywords found: {found_keywords}")
        
        # Check for specific amounts
        import re
        money_patterns = re.findall(r'\$[0-9,]+\.?[0-9]*', full_text)
        print(f"💵 Money amounts found: {money_patterns}")
        
        # Show first 1000 characters
        print(f"\n📝 FIRST 1000 CHARACTERS:")
        print("-" * 40)
        print(full_text[:1000])
        print("-" * 40)
        
        # Show last 1000 characters  
        print(f"\n📝 LAST 1000 CHARACTERS:")
        print("-" * 40)
        print(full_text[-1000:])
        print("-" * 40)
        
        # Look for form structure
        lines = full_text.split('\n')
        print(f"\n📋 FORM STRUCTURE ANALYSIS:")
        print(f"Total lines: {len(lines)}")
        
        # Find lines with financial terms
        financial_lines = []
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            if any(keyword in line_lower for keyword in financial_keywords):
                financial_lines.append(f"Line {i+1}: {line.strip()}")
        
        print(f"\n💰 LINES WITH FINANCIAL CONTENT:")
        if financial_lines:
            for line in financial_lines[:20]:  # Show first 20
                print(f"  {line}")
        else:
            print("  ❌ No lines with financial keywords found")
        
        # Check if it's a blank form
        if 'blank' in fl142_path.lower() or len(money_patterns) == 0:
            print(f"\n⚠️ POTENTIAL ISSUE: This might be a blank form!")
            print(f"   - No money amounts found")
            print(f"   - Consider using a filled FL-142 instead")
        
        return full_text
        
    except Exception as e:
        print(f"❌ Error extracting FL-142: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_with_enhanced_financial_prompt():
    """Test with a more aggressive financial extraction prompt"""
    
    print(f"\n🤖 TESTING ENHANCED FINANCIAL PROMPT")
    print("=" * 50)
    
    content = extract_and_analyze_fl142()
    if not content:
        return
    
    # Create enhanced prompt specifically for FL-142
    enhanced_prompt = f"""You are a financial document analyst specializing in FL-142 Schedule of Assets and Debts forms.

CRITICAL TASK: Extract ALL financial information from this FL-142 form, including:

1. DEBTS AND LIABILITIES:
   - Student loans (amounts, lenders)
   - Credit card debts (amounts, creditors)
   - Unsecured loans (amounts, lenders)
   - Mortgages and secured debts
   - Any other debts or liabilities

2. ASSETS AND PROPERTY:
   - Real estate (descriptions, values)
   - Bank accounts (checking, savings, balances)
   - Vehicles (descriptions, values)
   - Personal property (household items, values)
   - Investments, retirement accounts
   - Any other assets

3. FINANCIAL DETAILS:
   - Account numbers (if visible)
   - Dates acquired
   - Current values or balances
   - Monthly payments

DOCUMENT CONTENT:
{content}

EXTRACTION REQUIREMENTS:
- Extract EVERY financial amount you can find
- Include both filled values AND field labels
- Look for handwritten entries, typed entries, and checkmarks
- Extract partial information if complete data isn't available
- Focus on NUMBERS, AMOUNTS, and FINANCIAL DETAILS

Return JSON format:
{{
    "extracted_data": {{
        "field_name": "extracted_value_with_amount"
    }}
}}

Extract ALL financial data now - be thorough and aggressive in finding ANY financial information."""

    print(f"📝 Created enhanced prompt ({len(enhanced_prompt)} chars)")
    
    # Test the enhanced prompt with Claude
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ No ANTHROPIC_API_KEY found")
        return
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        print(f"🤖 Sending enhanced prompt to Claude...")
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            messages=[{"role": "user", "content": enhanced_prompt}]
        )
        
        response_text = response.content[0].text
        print(f"📨 Received response ({len(response_text)} chars)")
        print(f"\n🤖 ENHANCED CLAUDE RESPONSE:")
        print("-" * 40)
        print(response_text)
        print("-" * 40)
        
        # Try to parse JSON
        import json
        try:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_text = response_text[start:end]
                result = json.loads(json_text)
                extracted_data = result.get("extracted_data", {})
                
                print(f"\n💰 PARSED FINANCIAL DATA:")
                if extracted_data:
                    for field, value in extracted_data.items():
                        print(f"  • {field}: {value}")
                else:
                    print("  ❌ No financial data extracted")
            else:
                print("  ❌ No JSON found in response")
                
        except json.JSONDecodeError as e:
            print(f"  ❌ JSON parse error: {e}")
    
    except Exception as e:
        print(f"❌ Enhanced prompt test failed: {str(e)}")

def main():
    """Main debug function"""
    extract_and_analyze_fl142()
    test_with_enhanced_financial_prompt()

if __name__ == "__main__":
    main()
