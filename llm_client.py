#!/usr/bin/env python3
"""
Enhanced LLM Client for AI-Powered PDF Form Filler
Supports both OpenAI and Anthropic APIs with intelligent extraction
"""

import os
import logging
import json
import re
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)

def generate_with_openai(model: str, prompt: str, pdf_path: str = None, mapping_pdf_path: str = None) -> str:
    """
    Generate response using OpenAI API with optional PDF support
    
    Args:
        model: Model name (e.g., 'gpt-4', 'gpt-3.5-turbo', 'gpt-4o')
        prompt: Input prompt
        pdf_path: Optional path to filled PDF file to analyze
        mapping_pdf_path: Optional path to numbered mapping PDF for reference
        
    Returns:
        Generated text response
    """
    try:
        import openai
        import base64
        
        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Initialize client
        client = openai.OpenAI(api_key=api_key)
        
        # Prepare message content
        if pdf_path or mapping_pdf_path:
            # Convert PDFs to images for vision models
            try:
                import fitz  # PyMuPDF
                
                images = []
                pdf_descriptions = []
                
                # Add mapping PDF first (for reference)
                if mapping_pdf_path and os.path.exists(mapping_pdf_path):
                    doc = fitz.open(mapping_pdf_path)
                    for page_num in range(min(len(doc), 4)):  # Max 4 pages
                        page = doc[page_num]
                        pix = page.get_pixmap(dpi=150)
                        img_data = pix.tobytes("png")
                        img_base64 = base64.b64encode(img_data).decode('utf-8')
                        images.append(img_base64)
                        pdf_descriptions.append(f"NUMBERED MAPPING PDF - Page {page_num + 1}")
                    doc.close()
                    logger.info(f"Converted mapping PDF to {len(images)} images")
                
                # Add filled PDF (for data extraction)
                if pdf_path and os.path.exists(pdf_path):
                    doc = fitz.open(pdf_path)
                    filled_pdf_start = len(images)
                    for page_num in range(min(len(doc), 4)):  # Max 4 pages
                        page = doc[page_num]
                        pix = page.get_pixmap(dpi=150)
                        img_data = pix.tobytes("png")
                        img_base64 = base64.b64encode(img_data).decode('utf-8')
                        images.append(img_base64)
                        pdf_descriptions.append(f"FILLED PDF - Page {page_num + 1}")
                    doc.close()
                    logger.info(f"Converted filled PDF to {len(images) - filled_pdf_start} images")
                
                if images:
                    logger.info(f"Total images for OpenAI: {len(images)}")
                    
                    # Create content with images
                    content = [{"type": "text", "text": prompt}]
                    
                    for i, img_base64 in enumerate(images):
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}",
                                "detail": "high"
                            }
                        })
                    
                    # Make API call with images
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "user", "content": content}
                        ],
                        temperature=0.1,
                        max_tokens=4000
                    )
                    
                    return response.choices[0].message.content
                
            except ImportError:
                logger.warning("PyMuPDF not available, falling back to text-only")
                # Fall back to text-only
                pass
            except Exception as e:
                logger.warning(f"PDF conversion failed: {e}, falling back to text-only")
                pass
        
        # Text-only API call
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        
        return response.choices[0].message.content
        
    except ImportError:
        raise ImportError("OpenAI library not installed. Install with: pip install openai")
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise


def generate_with_claude(model: str, prompt: str, pdf_path: str = None, mapping_pdf_path: str = None) -> str:
    """
    Generate response using Anthropic Claude API with optional PDF support
    
    Args:
        model: Model name (e.g., 'claude-3-opus-20240229', 'claude-3-sonnet-20240229')
        prompt: Input prompt
        pdf_path: Optional path to filled PDF file to analyze
        mapping_pdf_path: Optional path to numbered mapping PDF for reference
        
    Returns:
        Generated text response
    """
    try:
        import anthropic
        import base64
        
        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        # Initialize client
        client = anthropic.Anthropic(api_key=api_key)
        
        # Prepare message content
        if pdf_path or mapping_pdf_path:
            # Claude supports PDF documents directly
            try:
                content = [{"type": "text", "text": prompt}]
                
                # Add mapping PDF first (for reference)
                if mapping_pdf_path and os.path.exists(mapping_pdf_path):
                    with open(mapping_pdf_path, 'rb') as pdf_file:
                        pdf_data = pdf_file.read()
                        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
                    
                    content.append({
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_base64
                        }
                    })
                    logger.info(f"Added mapping PDF ({len(pdf_data)} bytes) for Claude analysis")
                
                # Add filled PDF (for data extraction)
                if pdf_path and os.path.exists(pdf_path):
                    with open(pdf_path, 'rb') as pdf_file:
                        pdf_data = pdf_file.read()
                        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
                    
                    content.append({
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_base64
                        }
                    })
                    logger.info(f"Added filled PDF ({len(pdf_data)} bytes) for Claude analysis")
                
                # Make API call with PDFs
                response = client.messages.create(
                    model=model,
                    max_tokens=4000,
                    temperature=0.1,
                    messages=[
                        {"role": "user", "content": content}
                    ]
                )
                
                return response.content[0].text
                
            except Exception as e:
                logger.warning(f"PDF loading failed: {e}, falling back to text-only")
                pass
        
        # Text-only API call
        response = client.messages.create(
            model=model,
            max_tokens=4000,
            temperature=0.1,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.content[0].text
        
    except ImportError:
        raise ImportError("Anthropic library not installed. Install with: pip install anthropic")
    except Exception as e:
        logger.error(f"Anthropic API error: {str(e)}")
        raise


def generate_with_multiple_pdfs_openai(model: str, prompt: str, pdf_files: List[str], mapping_pdf_path: str = None) -> str:
    """
    Generate response using OpenAI API with multiple PDF files
    
    Args:
        model: Model name (e.g., 'gpt-4', 'gpt-3.5-turbo', 'gpt-4o')
        prompt: Input prompt
        pdf_files: List of PDF file paths to analyze
        mapping_pdf_path: Optional path to numbered mapping PDF for reference
        
    Returns:
        Generated text response
    """
    try:
        import openai
        import base64
        
        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Initialize client
        client = openai.OpenAI(api_key=api_key)
        
        # Convert all PDFs to images for vision models
        try:
            import fitz  # PyMuPDF
            
            images = []
            pdf_descriptions = []
            
            # Add mapping PDF first (for reference)
            if mapping_pdf_path and os.path.exists(mapping_pdf_path):
                doc = fitz.open(mapping_pdf_path)
                for page_num in range(min(len(doc), 4)):  # Max 4 pages
                    page = doc[page_num]
                    pix = page.get_pixmap(dpi=150)
                    img_data = pix.tobytes("png")
                    img_base64 = base64.b64encode(img_data).decode('utf-8')
                    images.append(img_base64)
                    pdf_descriptions.append(f"NUMBERED MAPPING PDF - Page {page_num + 1}")
                doc.close()
                logger.info(f"Converted mapping PDF to {len(images)} images")
            
            # Add all source PDFs (for data extraction)
            for pdf_idx, pdf_path in enumerate(pdf_files):
                if os.path.exists(pdf_path):
                    doc = fitz.open(pdf_path)
                    source_pdf_start = len(images)
                    for page_num in range(min(len(doc), 4)):  # Max 4 pages per PDF
                        page = doc[page_num]
                        pix = page.get_pixmap(dpi=150)
                        img_data = pix.tobytes("png")
                        img_base64 = base64.b64encode(img_data).decode('utf-8')
                        images.append(img_base64)
                        pdf_descriptions.append(f"SOURCE PDF {pdf_idx+1} ({os.path.basename(pdf_path)}) - Page {page_num + 1}")
                    doc.close()
                    logger.info(f"Converted source PDF {pdf_idx+1} to {len(images) - source_pdf_start} images")
            
            if images:
                logger.info(f"Total images for OpenAI: {len(images)}")
                
                # Create content with images
                content = [{
                    "type": "text", 
                    "text": f"{prompt}\n\nPROCESSING {len(pdf_files)} SOURCE DOCUMENTS - EXTRACT COMPREHENSIVELY FROM ALL!"
                }]
                
                for i, img_base64 in enumerate(images):
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_base64}",
                            "detail": "high"
                        }
                    })
                
                # Make API call with images
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "user", "content": content}
                    ],
                    temperature=0.1,
                    max_tokens=4000
                )
                
                return response.choices[0].message.content
            
        except ImportError:
            logger.warning("PyMuPDF not available, falling back to single PDF")
            return generate_with_openai(model, prompt, pdf_files[0] if pdf_files else None, mapping_pdf_path)
        except Exception as e:
            logger.warning(f"PDF conversion failed: {e}, falling back to single PDF")
            return generate_with_openai(model, prompt, pdf_files[0] if pdf_files else None, mapping_pdf_path)
        
        # Fallback
        return generate_with_openai(model, prompt, pdf_files[0] if pdf_files else None, mapping_pdf_path)
        
    except Exception as e:
        logger.error(f"Multi-PDF OpenAI API error: {str(e)}")
        return generate_with_openai(model, prompt, pdf_files[0] if pdf_files else None, mapping_pdf_path)


def generate_with_multiple_pdfs_claude(model: str, prompt: str, pdf_files: List[str], mapping_pdf_path: str = None) -> str:
    """
    Generate response using Anthropic Claude API with multiple PDF files
    
    Args:
        model: Model name (e.g., 'claude-3-opus-20240229', 'claude-3-sonnet-20240229')
        prompt: Input prompt
        pdf_files: List of PDF file paths to analyze
        mapping_pdf_path: Optional path to numbered mapping PDF for reference
        
    Returns:
        Generated text response
    """
    try:
        import anthropic
        import base64
        
        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        # Initialize client
        client = anthropic.Anthropic(api_key=api_key)
        
        # Claude supports PDF documents directly
        try:
            content = [{
                "type": "text", 
                "text": f"{prompt}\n\nPROCESSING {len(pdf_files)} SOURCE DOCUMENTS - EXTRACT COMPREHENSIVELY FROM ALL!"
            }]
            
            # Add mapping PDF first (for reference)
            if mapping_pdf_path and os.path.exists(mapping_pdf_path):
                with open(mapping_pdf_path, 'rb') as pdf_file:
                    pdf_data = pdf_file.read()
                    pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
                
                content.append({
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_base64
                    }
                })
                logger.info(f"Added mapping PDF ({len(pdf_data)} bytes) for Claude analysis")
            
            # Add all source PDFs (for data extraction)
            for pdf_idx, pdf_path in enumerate(pdf_files):
                if os.path.exists(pdf_path):
                    with open(pdf_path, 'rb') as pdf_file:
                        pdf_data = pdf_file.read()
                        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
                    
                    content.append({
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_base64
                        }
                    })
                    logger.info(f"Added source PDF {pdf_idx+1} ({len(pdf_data)} bytes) for Claude analysis")
            
            # Make API call with PDFs
            response = client.messages.create(
                model=model,
                max_tokens=4000,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": content}
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.warning(f"Multi-PDF loading failed: {e}, falling back to single PDF")
            return generate_with_claude(model, prompt, pdf_files[0] if pdf_files else None, mapping_pdf_path)
        
    except Exception as e:
        logger.error(f"Multi-PDF Anthropic API error: {str(e)}")
        return generate_with_claude(model, prompt, pdf_files[0] if pdf_files else None, mapping_pdf_path)


def analyze_field_types(field_names: List[str], field_descriptions: List[str]) -> Dict[str, str]:
    """
    Analyze form fields to determine their likely data types and purposes.
    This helps guide intelligent extraction.
    """
    field_analysis = {}
    
    for i, (name, desc) in enumerate(zip(field_names, field_descriptions)):
        name_lower = name.lower()
        desc_lower = (desc or "").lower()
        combined = f"{name_lower} {desc_lower}"
        
        # Determine field type based on name patterns
        if any(keyword in combined for keyword in ['name', 'petitioner', 'respondent', 'plaintiff', 'defendant', 'client']):
            field_type = "person_name"
        elif any(keyword in combined for keyword in ['address', 'street', 'city', 'state', 'zip']):
            field_type = "address"
        elif any(keyword in combined for keyword in ['phone', 'tel', 'fax']):
            field_type = "phone_number"
        elif any(keyword in combined for keyword in ['email', 'e-mail']):
            field_type = "email_address"
        elif any(keyword in combined for keyword in ['case', 'number', 'docket', 'file']):
            field_type = "case_identifier"
        elif any(keyword in combined for keyword in ['date', 'when', 'time']):
            field_type = "date"
        elif any(keyword in combined for keyword in ['amount', 'value', 'price', 'cost', 'balance', '$', 'dollar']):
            field_type = "monetary_amount"
        elif any(keyword in combined for keyword in ['account', 'bank', 'financial']):
            field_type = "financial_account"
        elif any(keyword in combined for keyword in ['attorney', 'lawyer', 'counsel']):
            field_type = "attorney_info"
        elif any(keyword in combined for keyword in ['court', 'county', 'jurisdiction']):
            field_type = "court_info"
        elif any(keyword in combined for keyword in ['description', 'detail', 'specify', 'explain']):
            field_type = "description_text"
        elif any(keyword in combined for keyword in ['check', 'box', 'select', 'choose']):
            field_type = "checkbox_selection"
        else:
            field_type = "general_text"
            
        field_analysis[name] = field_type
    
    return field_analysis


def enhanced_pattern_extraction(text: str, field_names: List[str], field_descriptions: List[str]) -> Tuple[Dict[str, str], Dict[str, float]]:
    """
    Enhanced pattern matching that's smarter about avoiding template content
    """
    extracted_data = {}
    confidence_scores = {}
    
    # Get field type analysis
    field_analysis = analyze_field_types(field_names, field_descriptions)
    
    # Enhanced patterns for different data types
    patterns = {
        'person_name': [
            r'\b([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',  # Proper names
            r'(?:PETITIONER|RESPONDENT|PLAINTIFF|DEFENDANT):\s*([A-Z\s]+)',
        ],
        'case_identifier': [
            r'\b(\d{2}[A-Z]{2,4}\d{5,8})\b',  # Case number patterns
            r'(?:CASE|FILE|DOCKET)\s*(?:NO\.?|NUMBER)?\s*:?\s*([A-Z0-9\-]+)',
        ],
        'phone_number': [
            r'\((\d{3})\)\s*(\d{3})-(\d{4})',
            r'(\d{3})[-.\s](\d{3})[-.\s](\d{4})',
        ],
        'email_address': [
            r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
        ],
        'address': [
            r'\b(\d+\s+[A-Za-z\s]+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Place|Pl))\b',
        ],
        'monetary_amount': [
            r'\$\s*([1-9]\d{0,2}(?:,\d{3})*(?:\.\d{2})?)',  # Exclude $0.00 and single digits
        ],
        'date': [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b',
            r'\b([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})\b',  # Month day, year
        ],
    }
    
    # Track value frequency to detect templates
    value_frequency = {}
    
    # First pass - extract all potential values and count frequency
    all_potential_values = {}
    for field_idx, (field_name, field_type) in enumerate(field_analysis.items()):
        if field_type in patterns:
            for pattern in patterns[field_type]:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        # For phone numbers, format properly
                        if field_type == 'phone_number' and len(match) >= 3:
                            value = f"({match[0]}) {match[1]}-{match[2]}"
                        else:
                            value = " ".join(match)
                    else:
                        value = match
                    
                    # Count frequency
                    value_frequency[value] = value_frequency.get(value, 0) + 1
                    
                    # Store potential match
                    if field_name not in all_potential_values:
                        all_potential_values[field_name] = []
                    all_potential_values[field_name].append(value)
    
    # Second pass - select best values while avoiding high-frequency template values
    for field_name, field_type in field_analysis.items():
        if field_name in all_potential_values:
            candidates = all_potential_values[field_name]
            
            # Score candidates
            best_candidate = None
            best_score = 0
            
            for candidate in candidates:
                score = 1.0
                
                # Penalize high-frequency values (likely templates)
                frequency = value_frequency.get(candidate, 1)
                if frequency > 3:
                    score *= 0.3  # Heavy penalty for frequent values
                elif frequency > 1:
                    score *= 0.7  # Light penalty for repeated values
                
                # Boost score for appropriate field types
                if field_type == 'monetary_amount':
                    # Prefer non-zero amounts
                    try:
                        amount = float(candidate.replace(',', '').replace('$', ''))
                        if amount > 0:
                            score *= 1.5
                        else:
                            score *= 0.1
                    except:
                        pass
                
                elif field_type == 'date':
                    # Penalize obviously template dates
                    if candidate in ['6/7/2020', '01/01/2020', '12/31/2020']:
                        score *= 0.1
                
                elif field_type == 'person_name':
                    # Prefer names that look realistic
                    if 'address' in candidate.lower() or len(candidate.split()) < 2:
                        score *= 0.1
                
                if score > best_score:
                    best_score = score
                    best_candidate = candidate
            
            # Only include if confidence is reasonable
            if best_candidate and best_score >= 0.3:
                extracted_data[field_name] = best_candidate
                confidence_scores[field_name] = min(best_score, 0.9)  # Cap at 0.9
    
    return extracted_data, confidence_scores


def create_enhanced_extraction_prompt(field_names: List[str], field_descriptions: List[str], text: str) -> str:
    """Create an enhanced prompt for intelligent data extraction from any form type"""
    
    # Build field mapping
    field_mapping = dict(zip(field_names, field_descriptions))
    
    # Analyze field types to provide intelligent guidance
    field_analysis = analyze_field_types(field_names, field_descriptions)
    
    return f"""
You are an expert document analyst extracting real data from source documents to populate form fields. Your task is to intelligently match actual data values to form fields while avoiding template/placeholder content.

TARGET FORM FIELDS TO POPULATE:
{json.dumps(field_mapping, indent=2)}

FIELD TYPE ANALYSIS:
{json.dumps(field_analysis, indent=2)}

SOURCE DOCUMENTS TEXT:
{text[:12000]}

INTELLIGENT EXTRACTION RULES:

1. IDENTIFY REAL DATA vs TEMPLATE CONTENT:
   
   REAL DATA (extract this):
   - Unique personal identifiers (names, SSNs, IDs, case numbers)
   - Specific addresses with actual street names/numbers
   - Contact information (real phone numbers, email addresses)
   - Financial data (account numbers, balances, specific dollar amounts)
   - Dates tied to specific events or transactions
   - Business/institution names (banks, employers, courts)
   - Asset descriptions (property addresses, vehicle details, account info)
   - Debt information (creditor names, specific amounts owed)
   
   TEMPLATE CONTENT (ignore this):
   - Repeated identical values across unrelated fields
   - Generic placeholder text ("Enter name here", "Give details")
   - Form instructions and field labels
   - Template dates that appear everywhere
   - Generic monetary placeholders ($0.00, $X.XX)
   - Instructional text ("Attach copy", "See instructions")

2. SMART FIELD MATCHING STRATEGY:
   
   For each target field:
   a) Analyze the field name/description to understand what data type is needed
   b) Search source documents for data that logically fits that field type
   c) Validate that the data is specific and not generic/template content
   d) Ensure the data hasn't been used for multiple unrelated fields
   
   Field Type Matching:
   - Name fields → Look for actual person/entity names (capitalized, proper nouns)
   - Address fields → Find complete addresses with street numbers and names
   - Phone fields → Extract formatted phone numbers (xxx-xxx-xxxx patterns)
   - Email fields → Find valid email address formats
   - Date fields → Use dates that are contextually relevant to that specific field
   - Money fields → Extract specific dollar amounts (not zeros or placeholders)
   - ID/Number fields → Find unique identifiers, case numbers, account numbers
   - Description fields → Extract detailed, specific descriptions

3. TEMPLATE DETECTION AND AVOIDANCE:
   
   Red flags for template content:
   - Same value appears in 5+ unrelated fields
   - Generic instructional language
   - Obvious placeholder patterns
   - Values that don't make logical sense for the field type
   
   Validation questions:
   - Does this data make sense for this specific field?
   - Is this value unique and meaningful?
   - Would a real person have entered this data?

4. CONFIDENCE SCORING CRITERIA:
   
   High confidence (0.9-1.0):
   - Data clearly matches field type and purpose
   - Unique, specific, and meaningful value
   - Contextually appropriate for the field
   
   Medium confidence (0.6-0.8):
   - Data type matches but some ambiguity
   - Could be real data but uncertain context
   
   Low confidence (0.3-0.5):
   - Possible match but high uncertainty
   - Data might be template or placeholder
   
   Skip (confidence < 0.3):
   - Clearly template or placeholder content
   - No logical connection to field purpose

5. OUTPUT FORMAT:
{{
    "extracted_data": {{
        "field_name": "actual_extracted_value"
    }},
    "confidence_scores": {{
        "field_name": 0.95
    }},
    "extraction_notes": {{
        "field_name": "Reason for extraction/confidence level"
    }}
}}

EXTRACT ONLY HIGH-QUALITY, MEANINGFUL DATA THAT WOULD GENUINELY BE USEFUL FOR POPULATING THE TARGET FORM.
    """


def test_openai_connection() -> bool:
    """Test OpenAI API connection"""
    try:
        response = generate_with_openai("gpt-3.5-turbo", "Say 'Hello' if you can read this.")
        return "hello" in response.lower()
    except Exception as e:
        logger.error(f"OpenAI connection test failed: {str(e)}")
        return False


def test_claude_connection() -> bool:
    """Test Anthropic Claude API connection"""
    try:
        response = generate_with_claude("claude-3-haiku-20240307", "Say 'Hello' if you can read this.")
        return "hello" in response.lower()
    except Exception as e:
        logger.error(f"Claude connection test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Test script
    print("Testing LLM Client...")
    
    # Test OpenAI if API key is available
    if os.getenv("OPENAI_API_KEY"):
        print("Testing OpenAI...")
        if test_openai_connection():
            print("✓ OpenAI connection successful")
        else:
            print("✗ OpenAI connection failed")
    else:
        print("⚠ OpenAI API key not set")
    
    # Test Claude if API key is available
    if os.getenv("ANTHROPIC_API_KEY"):
        print("Testing Claude...")
        if test_claude_connection():
            print("✓ Claude connection successful")
        else:
            print("✗ Claude connection failed")
    else:
        print("⚠ Anthropic API key not set")