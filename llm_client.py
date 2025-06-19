#!/usr/bin/env python3
"""
Enhanced LLM Client for AI-Powered PDF Form Filler v4.1
Supports both OpenAI and Anthropic APIs with direct PDF processing and intelligent extraction
"""

import os
import logging
import json
import re
import base64
from typing import Optional, Dict, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

def generate_with_openai_direct_pdf(model: str, prompt: str, pdf_path: str = None) -> str:
    """
    Generate response using OpenAI API with direct PDF processing (no image conversion)
    
    Args:
        model: Model name (e.g., 'gpt-4-turbo-preview', 'gpt-4')
        prompt: Input prompt
        pdf_path: Path to PDF file to analyze directly
        
    Returns:
        Generated text response
    """
    try:
        import openai
        
        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Initialize client
        client = openai.OpenAI(api_key=api_key)
        
        # For text models, we need to extract text from PDF first
        if pdf_path and os.path.exists(pdf_path):
            try:
                # Try to extract text using PyPDF2 for context
                import PyPDF2
                
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    extracted_text = ""
                    for page in pdf_reader.pages:
                        extracted_text += page.extract_text() + "\n"
                
                # Combine prompt with extracted text context
                enhanced_prompt = f"""{prompt}

EXTRACTED PDF TEXT FOR CONTEXT:
{extracted_text[:8000]}  

Note: The above text was extracted from the PDF for context. Use this along with your analysis."""
                
                logger.info(f"Enhanced prompt with {len(extracted_text)} chars of extracted text")
                
            except Exception as e:
                logger.warning(f"Could not extract PDF text: {e}, using original prompt")
                enhanced_prompt = prompt
        else:
            enhanced_prompt = prompt
        
        # Make API call
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": enhanced_prompt}
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

def generate_with_claude_direct_pdf(model: str, prompt: str, pdf_path: str = None) -> str:
    """
    Generate response using Anthropic Claude API with direct PDF processing
    
    Args:
        model: Model name (e.g., 'claude-3-opus-20240229', 'claude-3-sonnet-20240229')
        prompt: Input prompt
        pdf_path: Path to PDF file to analyze directly
        
    Returns:
        Generated text response
    """
    try:
        import anthropic
        
        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        # Initialize client
        client = anthropic.Anthropic(api_key=api_key)
        
        # Claude supports PDF documents directly
        if pdf_path and os.path.exists(pdf_path):
            try:
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_data = pdf_file.read()
                
                pdf_b64 = base64.b64encode(pdf_data).decode('utf-8')
                
                # Create message with PDF document
                response = client.messages.create(
                    model=model,
                    max_tokens=4000,
                    temperature=0.1,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "document",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "application/pdf",
                                        "data": pdf_b64
                                    }
                                }
                            ]
                        }
                    ]
                )
                
                return response.content[0].text
                
            except Exception as e:
                logger.warning(f"Direct PDF processing failed: {e}, trying text extraction")
                # Fallback to text extraction
                try:
                    import PyPDF2
                    
                    with open(pdf_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        extracted_text = ""
                        for page in pdf_reader.pages:
                            extracted_text += page.extract_text() + "\n"
                    
                    enhanced_prompt = f"""{prompt}

EXTRACTED PDF TEXT FOR CONTEXT:
{extracted_text[:8000]}

Note: The above text was extracted from the PDF for context."""
                    
                    response = client.messages.create(
                        model=model,
                        max_tokens=4000,
                        temperature=0.1,
                        messages=[
                            {"role": "user", "content": enhanced_prompt}
                        ]
                    )
                    
                    return response.content[0].text
                    
                except Exception as e2:
                    logger.error(f"PDF fallback processing failed: {e2}")
                    raise
        else:
            # Text-only message
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

# Enhanced backward compatibility functions that choose between direct PDF and image processing
def generate_with_openai(model: str, prompt: str, pdf_path: str = None, mapping_pdf_path: str = None) -> str:
    """
    Enhanced OpenAI generation with intelligent PDF processing selection
    
    Args:
        model: Model name
        prompt: Input prompt
        pdf_path: Optional path to filled PDF file to analyze
        mapping_pdf_path: Optional path to numbered mapping PDF for reference
        
    Returns:
        Generated text response
    """
    
    # For newer models, prefer direct PDF processing when analyzing a single PDF
    if model in ['gpt-4-turbo-preview', 'gpt-4-turbo', 'gpt-4o'] and pdf_path and not mapping_pdf_path:
        try:
            logger.info(f"Using direct PDF processing with {model}")
            return generate_with_openai_direct_pdf(model, prompt, pdf_path)
        except Exception as e:
            logger.warning(f"Direct PDF processing failed: {e}, falling back to image processing")
    
    # Fall back to original image-based processing for backward compatibility
    return generate_with_openai_legacy(model, prompt, pdf_path, mapping_pdf_path)

def generate_with_claude(model: str, prompt: str, pdf_path: str = None, mapping_pdf_path: str = None) -> str:
    """
    Enhanced Claude generation with intelligent PDF processing selection
    
    Args:
        model: Model name
        prompt: Input prompt
        pdf_path: Optional path to filled PDF file to analyze
        mapping_pdf_path: Optional path to numbered mapping PDF for reference
        
    Returns:
        Generated text response
    """
    
    # Claude has excellent native PDF support, prefer direct processing
    if pdf_path and not mapping_pdf_path:
        try:
            logger.info(f"Using direct PDF processing with {model}")
            return generate_with_claude_direct_pdf(model, prompt, pdf_path)
        except Exception as e:
            logger.warning(f"Direct PDF processing failed: {e}, falling back to legacy processing")
    
    # Fall back to original processing for backward compatibility
    return generate_with_claude_legacy(model, prompt, pdf_path, mapping_pdf_path)

# Legacy functions (original image-based processing) for backward compatibility
def generate_with_openai_legacy(model: str, prompt: str, pdf_path: str = None, mapping_pdf_path: str = None) -> str:
    """
    Original OpenAI generation with image-based PDF processing
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
                        pix = page.get_pixmap(dpi=200)  # Increased from 150 to 200 DPI
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
                        pix = page.get_pixmap(dpi=200)  # Increased from 150 to 200 DPI
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

def generate_with_claude_legacy(model: str, prompt: str, pdf_path: str = None, mapping_pdf_path: str = None) -> str:
    """
    Original Claude generation with image-based PDF processing
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
            content = [{"type": "text", "text": prompt}]
            
            # Add mapping PDF for reference
            if mapping_pdf_path and os.path.exists(mapping_pdf_path):
                with open(mapping_pdf_path, 'rb') as pdf_file:
                    pdf_data = pdf_file.read()
                
                pdf_b64 = base64.b64encode(pdf_data).decode('utf-8')
                content.append({
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_b64
                    }
                })
                logger.info("Added mapping PDF to Claude request")
            
            # Add filled PDF for analysis
            if pdf_path and os.path.exists(pdf_path) and pdf_path != mapping_pdf_path:
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_data = pdf_file.read()
                
                pdf_b64 = base64.b64encode(pdf_data).decode('utf-8')
                content.append({
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_b64
                    }
                })
                logger.info("Added filled PDF to Claude request")
            
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
            logger.warning(f"PDF processing failed: {e}, falling back to text-only")
            
            # Fallback to text-only
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

# Multi-PDF processing functions
def generate_with_multiple_pdfs_openai(model: str, prompt: str, pdf_files: List[str], mapping_pdf_path: str = None) -> str:
    """
    Generate response using OpenAI API with multiple PDF files
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
        
        # Convert PDFs to images for vision processing
        try:
            import fitz  # PyMuPDF
            
            images = []
            
            # Add mapping PDF first if provided
            if mapping_pdf_path and os.path.exists(mapping_pdf_path):
                doc = fitz.open(mapping_pdf_path)
                for page_num in range(min(len(doc), 2)):  # Limit mapping PDF to 2 pages
                    page = doc[page_num]
                    pix = page.get_pixmap(dpi=200)
                    img_data = pix.tobytes("png")
                    img_base64 = base64.b64encode(img_data).decode('utf-8')
                    images.append(img_base64)
                doc.close()
                logger.info(f"Converted mapping PDF to {len(images)} images")
            
            # Add source PDFs
            for pdf_file in pdf_files:
                if os.path.exists(pdf_file):
                    doc = fitz.open(pdf_file)
                    # Limit each PDF to 2 pages to stay within token limits
                    for page_num in range(min(len(doc), 2)):
                        page = doc[page_num]
                        pix = page.get_pixmap(dpi=200)
                        img_data = pix.tobytes("png")
                        img_base64 = base64.b64encode(img_data).decode('utf-8')
                        images.append(img_base64)
                    doc.close()
            
            if images:
                logger.info(f"Total images for multi-PDF processing: {len(images)}")
                
                # Create content with text and all images
                content = [{"type": "text", "text": f"{prompt}\n\nPROCESSING {len(pdf_files)} SOURCE DOCUMENTS - EXTRACT COMPREHENSIVELY FROM ALL!"}]
                
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
            
            # Add mapping PDF first if provided
            if mapping_pdf_path and os.path.exists(mapping_pdf_path):
                with open(mapping_pdf_path, 'rb') as pdf_file:
                    pdf_data = pdf_file.read()
                
                pdf_b64 = base64.b64encode(pdf_data).decode('utf-8')
                content.append({
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_b64
                    }
                })
            
            # Add source PDFs
            for pdf_file in pdf_files:
                if os.path.exists(pdf_file):
                    with open(pdf_file, 'rb') as file:
                        pdf_data = file.read()
                    
                    pdf_b64 = base64.b64encode(pdf_data).decode('utf-8')
                    content.append({
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64
                        }
                    })
            
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
            logger.warning(f"Multi-PDF processing failed: {e}, falling back to single PDF")
            return generate_with_claude(model, prompt, pdf_files[0] if pdf_files else None, mapping_pdf_path)
        
    except Exception as e:
        logger.error(f"Multi-PDF Claude API error: {str(e)}")
        return generate_with_claude(model, prompt, pdf_files[0] if pdf_files else None, mapping_pdf_path)

# Utility functions
def create_enhanced_extraction_prompt(field_names: List[str], field_descriptions: List[str], text: str) -> str:
    """Create enhanced extraction prompt for better AI performance"""
    
    field_info = dict(zip(field_names, field_descriptions))
    
    return f"""
EXPERT PDF FORM DATA EXTRACTION

You are extracting data from completed legal documents to populate blank forms with equivalent information.

TARGET FORM FIELDS:
{json.dumps(field_info, indent=2)}

SOURCE DOCUMENT TEXT:
{text[:8000]}

EXTRACTION STRATEGY:
1. IDENTIFY KEY DATA: Look for names, case numbers, monetary amounts, dates, addresses
2. MATCH SEMANTICALLY: Match data meaning, not just field names
3. EXTRACT PRECISELY: Get exact values as they appear in source documents
4. VALIDATE CONTEXT: Ensure extracted data makes sense for the target field

OUTPUT FORMAT:
{{
    "extracted_data": {{
        "field_name": "extracted_value"
    }},
    "confidence_scores": {{
        "field_name": 0.95
    }},
    "extraction_notes": "Brief explanation of extraction approach"
}}

FOCUS: Accuracy and completeness. Extract real data, ignore template text and empty fields.
"""

if __name__ == "__main__":
    # Test the enhanced functions
    print("Enhanced LLM Client v4.1 - Direct PDF Processing")
    print("Available functions:")
    print("- generate_with_openai() - Smart PDF processing")
    print("- generate_with_claude() - Smart PDF processing") 
    print("- generate_with_openai_direct_pdf() - Direct PDF processing")
    print("- generate_with_claude_direct_pdf() - Direct PDF processing")
    print("- generate_with_multiple_pdfs_openai() - Multi-PDF processing")
    print("- generate_with_multiple_pdfs_claude() - Multi-PDF processing")
