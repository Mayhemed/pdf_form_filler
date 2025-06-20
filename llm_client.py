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

# Check if OpenAI is available
OPENAI_AVAILABLE = False
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    logger.warning("OpenAI library not available. Install with: pip install openai")

# Check if Anthropic is available
ANTHROPIC_AVAILABLE = False
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    logger.warning("Anthropic library not available. Install with: pip install anthropic")

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
            
            # Add mapping PDF first if provided - with enhanced processing
            if mapping_pdf_path and os.path.exists(mapping_pdf_path):
                doc = fitz.open(mapping_pdf_path)
                mapping_pages = len(doc)
                logger.info(f"Processing mapping PDF with {mapping_pages} pages at high resolution")
                
                # Process all pages of the mapping PDF to ensure all field numbers are visible
                for page_num in range(mapping_pages):
                    page = doc[page_num]
                    # Increase DPI for better visibility of field numbers
                    pix = page.get_pixmap(dpi=300)  # Increased from 200 to 300 DPI
                    img_data = pix.tobytes("png")
                    img_base64 = base64.b64encode(img_data).decode('utf-8')
                    images.append(img_base64)
                    logger.info(f"Added mapping PDF page {page_num+1}/{mapping_pages} (image #{len(images)})")
                doc.close()
                
                # Add explicit mapping instructions to the prompt
                enhanced_mapping_instructions = f"""
CRITICAL MAPPING INSTRUCTIONS:
The first {mapping_pages} image(s) show the NUMBERED MAPPING PDF with field numbers.
- EACH FIELD on the form has a NUMBER next to it (e.g., "5", "12", "138")
- You MUST use these EXACT numbers as keys in your JSON response
- Field #5 might be "Petitioner Name", Field #12 might be "Case Number", etc.
- Even if the field looks like "FL-142[0].Page1[0].TextField1[0]", use ONLY the NUMBER shown on the mapping PDF
"""
                prompt = prompt + "\n\n" + enhanced_mapping_instructions
            
            # Add source PDFs
            for pdf_file in pdf_files:
                if os.path.exists(pdf_file):
                    doc = fitz.open(pdf_file)
                    pdf_name = os.path.basename(pdf_file)
                    total_pages = len(doc)
                    logger.info(f"Processing PDF: {pdf_name} with {total_pages} pages")
                    
                    # Process up to 4 pages per PDF for better coverage (increased from 2)
                    pages_to_process = min(total_pages, 4)
                    
                    # Always process first and last page for better coverage
                    process_pages = list(range(min(pages_to_process, 3)))
                    if total_pages > 3 and pages_to_process > 3:
                        process_pages.append(total_pages - 1)  # Add the last page
                    
                    logger.info(f"Will process pages {process_pages} from {pdf_name}")
                    
                    for page_idx, page_num in enumerate(process_pages):
                        page = doc[page_num]
                        pix = page.get_pixmap(dpi=200)
                        img_data = pix.tobytes("png")
                        img_base64 = base64.b64encode(img_data).decode('utf-8')
                        images.append(img_base64)
                        logger.info(f"Added page {page_num+1} from {pdf_name} (image #{len(images)})")
                    doc.close()
            
            if images:
                logger.info(f"Total images for multi-PDF processing: {len(images)}")
                
                # Create content with text and document metadata
                document_metadata = "\n\n== DOCUMENT INVENTORY ==\n"
                for i, pdf_path in enumerate(pdf_files):
                    filename = os.path.basename(pdf_path)
                    file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
                    document_metadata += f"Document {i+1}: '{filename}' ({file_size_mb:.2f} MB)\n"
                
                enhanced_prompt = f"""{prompt}

PROCESSING {len(pdf_files)} SOURCE DOCUMENTS - EXTRACT AND MERGE COMPREHENSIVELY FROM ALL!

{document_metadata}

⚠️ YOUR PRIMARY TASK IS TO MERGE DATA FROM ALL THESE DOCUMENTS
Do not prioritize any single document. Each document contains important data that must be combined.
"""
                content = [{"type": "text", "text": enhanced_prompt}]
                
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
            logger.error("❌ CRITICAL: PyMuPDF not available, required for multi-PDF processing")
            # We'll attempt text extraction of all PDFs as fallback
            enhanced_prompt = prompt + "\n\n**CRITICAL: ANALYZE ALL PDF DOCUMENTS THOROUGHLY!**\n\n"
            text_extracts = []
            
            try:
                import PyPDF2
                logger.info("Attempting PyPDF2 fallback for all documents")
                
                for i, pdf_path in enumerate(pdf_files):
                    if os.path.exists(pdf_path):
                        pdf_name = os.path.basename(pdf_path)
                        try:
                            with open(pdf_path, 'rb') as file:
                                pdf_reader = PyPDF2.PdfReader(file)
                                extracted_text = ""
                                for page in pdf_reader.pages:
                                    extracted_text += page.extract_text() + "\n"
                                
                                logger.info(f"Extracted {len(extracted_text)} chars from {pdf_name}")
                                text_extracts.append(f"--- BEGIN DOCUMENT {i+1}: {pdf_name} ---\n{extracted_text[:10000]}\n--- END DOCUMENT {i+1} ---\n")
                        except Exception as e2:
                            logger.error(f"Failed to extract text from {pdf_name}: {e2}")
                
                if text_extracts:
                    combined_text = "\n\n".join(text_extracts)
                    enhanced_prompt += f"\n\nEXTRACTED TEXT FROM {len(text_extracts)} DOCUMENTS:\n\n{combined_text[:30000]}"
                    
                    # Call OpenAI with the text-based fallback
                    client = openai.OpenAI(api_key=api_key)
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": enhanced_prompt}],
                        temperature=0.1,
                        max_tokens=4000
                    )
                    return response.choices[0].message.content
            except Exception as text_e:
                logger.error(f"Text extraction fallback failed: {text_e}")
            
            # Last resort: just use the first PDF
            logger.warning("⚠️ All fallbacks failed, using only first PDF as last resort")
            return generate_with_openai(model, prompt + "\n\n**WARNING: Only first document processed due to technical issues**",
                                       pdf_files[0] if pdf_files else None, mapping_pdf_path)
                
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            logger.info("Attempting alternative PDF processing method...")
            
            # Try a different approach instead of falling back to single PDF
            try:
                # Add stronger warning in prompt
                enhanced_prompt = prompt + f"\n\n**CRITICAL INSTRUCTION: You MUST analyze ALL {len(pdf_files)} documents thoroughly!**"
                
                # Try text extraction as fallback
                return generate_with_openai(model, enhanced_prompt, pdf_files[0] if pdf_files else None, mapping_pdf_path)
            except Exception as e2:
                logger.error(f"Alternative approach failed: {e2}")
                logger.warning("⚠️ Using only first PDF as last resort")
                return generate_with_openai(model, prompt, pdf_files[0] if pdf_files else None, mapping_pdf_path)
        
        # We should never reach here, but just in case:
        logger.error("⚠️ Unexpected code path in multi-PDF processing")
        return generate_with_openai(model, prompt, pdf_files[0] if pdf_files else None, mapping_pdf_path)
        
    except Exception as e:
        logger.error(f"❌ CRITICAL: Multi-PDF OpenAI API error: {str(e)}")
        
        # Attempt last-ditch effort with more direct prompt
        try:
            enhanced_prompt = prompt + "\n\n**SYSTEM ALERT: Multi-PDF processing error occurred. This is critical: You MUST still try to extract from ALL documents!**"
            return generate_with_openai(model, enhanced_prompt, pdf_files[0] if pdf_files else None, mapping_pdf_path)
        except:
            # Absolute last resort
            logger.error("⚠️ Final fallback: using only first PDF")
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
            # Create document metadata
            document_metadata = "\n\n== DOCUMENT INVENTORY ==\n"
            for i, pdf_path in enumerate(pdf_files):
                filename = os.path.basename(pdf_path)
                file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
                document_metadata += f"Document {i+1}: '{filename}' ({file_size_mb:.2f} MB)\n"
            
            enhanced_prompt = f"""{prompt}

PROCESSING {len(pdf_files)} SOURCE DOCUMENTS - EXTRACT AND MERGE COMPREHENSIVELY FROM ALL!

{document_metadata}

⚠️ YOUR PRIMARY TASK IS TO MERGE DATA FROM ALL THESE DOCUMENTS
Do not prioritize any single document. Each document contains important data that must be combined.
"""
            content = [{
                "type": "text",
                "text": enhanced_prompt
            }]
            
            # Add mapping PDF first if provided - with enhanced instructions
            if mapping_pdf_path and os.path.exists(mapping_pdf_path):
                mapping_pdf_name = os.path.basename(mapping_pdf_path)
                mapping_pdf_size = os.path.getsize(mapping_pdf_path) / (1024 * 1024)
                logger.info(f"Adding numbered mapping PDF: {mapping_pdf_name} ({mapping_pdf_size:.2f} MB)")
                
                # Add explicit mapping instructions to the prompt
                try:
                    import PyPDF2
                    with open(mapping_pdf_path, 'rb') as f:
                        page_count = len(PyPDF2.PdfReader(f).pages)
                except:
                    page_count = "multiple"
                
                mapping_instructions = f"""
CRITICAL MAPPING INSTRUCTIONS:
The NUMBERED MAPPING PDF ({mapping_pdf_name}) shows all form fields with their numbers.
- EACH FIELD on the form has a NUMBER next to it (e.g., "5", "12", "138")
- You MUST use these EXACT numbers as keys in your JSON response
- Field #5 might be "Petitioner Name", Field #12 might be "Case Number", etc.
- Even if you see field IDs like "FL-142[0].Page1[0].TextField1[0]", use ONLY the NUMBER shown on the mapping PDF
"""
                # Add mapping instructions to the prompt
                enhanced_prompt = content[0]["text"] + "\n\n" + mapping_instructions
                content[0]["text"] = enhanced_prompt
                
                # Now add the actual mapping PDF
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
                logger.info(f"Added mapping PDF with {page_count} pages and mapping instructions")
            
            # Add source PDFs with enhanced logging
            if not pdf_files:
                logger.warning("No PDF files provided to Claude multi-PDF processor!")
                
            for i, pdf_file in enumerate(pdf_files):
                if os.path.exists(pdf_file):
                    pdf_name = os.path.basename(pdf_file)
                    pdf_size_mb = os.path.getsize(pdf_file) / (1024 * 1024)
                    
                    logger.info(f"Processing PDF {i+1}/{len(pdf_files)}: {pdf_name} ({pdf_size_mb:.2f} MB)")
                    
                    try:
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
                        logger.info(f"✓ Successfully added {pdf_name} to Claude request (document #{len(content)-1})")
                    except Exception as e:
                        logger.error(f"❌ Failed to process PDF {pdf_name}: {str(e)}")
                        # Don't raise exception - try to continue with other PDFs
                else:
                    logger.error(f"❌ PDF file does not exist: {pdf_file}")
            
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
            logger.error(f"❌ Claude multi-PDF processing failed: {e}")
            
            # Enhanced fallback that tries to include all PDFs
            try:
                logger.info("Attempting text extraction fallback for all documents with Claude")
                
                # Add stronger emphasis in prompt for multiple documents
                enhanced_prompt = prompt + f"\n\n**CRITICAL INSTRUCTION: There was an error processing multiple PDFs. You MUST still try to extract data from ALL {len(pdf_files)} documents thoroughly!**"
                
                # Try to extract text from all PDFs as a fallback
                import PyPDF2
                text_extracts = []
                
                for i, pdf_path in enumerate(pdf_files):
                    if os.path.exists(pdf_path):
                        pdf_name = os.path.basename(pdf_path)
                        try:
                            with open(pdf_path, 'rb') as file:
                                pdf_reader = PyPDF2.PdfReader(file)
                                extracted_text = ""
                                for page in pdf_reader.pages:
                                    extracted_text += page.extract_text() + "\n"
                                
                                logger.info(f"Extracted {len(extracted_text)} chars from {pdf_name}")
                                text_extracts.append(f"--- BEGIN DOCUMENT {i+1}: {pdf_name} ---\n{extracted_text[:10000]}\n--- END DOCUMENT {i+1} ---\n")
                        except Exception as e2:
                            logger.error(f"Failed to extract text from {pdf_name}: {e2}")
                
                if text_extracts:
                    combined_text = "\n\n".join(text_extracts)
                    enhanced_prompt += f"\n\nEXTRACTED TEXT FROM {len(text_extracts)} DOCUMENTS:\n\n{combined_text[:30000]}"
                    
                    # Make Claude API call with text extracts
                    text_response = client.messages.create(
                        model=model,
                        max_tokens=4000,
                        temperature=0.1,
                        messages=[
                            {"role": "user", "content": enhanced_prompt}
                        ]
                    )
                    
                    return text_response.content[0].text
                
            except Exception as text_e:
                logger.error(f"Claude text extraction fallback failed: {text_e}")
            
            # Last resort: use the first PDF only, but with a warning
            logger.warning("⚠️ All fallbacks failed, using only first PDF with Claude as last resort")
            return generate_with_claude(model, prompt + "\n\n**WARNING: Only first document processed due to technical issues**",
                                      pdf_files[0] if pdf_files else None, mapping_pdf_path)
        
    except Exception as e:
        logger.error(f"❌ CRITICAL: Multi-PDF Claude API error: {str(e)}")
        
        # Attempt last-ditch effort with enhanced prompt
        try:
            enhanced_prompt = prompt + "\n\n**SYSTEM ALERT: Multi-PDF processing error occurred. This is critical: You MUST still try to extract from ALL documents!**"
            return generate_with_claude(model, enhanced_prompt, pdf_files[0] if pdf_files else None, mapping_pdf_path)
        except:
            # Absolute last resort
            logger.error("⚠️ Final fallback: using only first PDF with Claude")
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
