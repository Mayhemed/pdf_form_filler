# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered PDF form filling system for legal documents, specifically designed for California family law forms (FL-142 "Schedule of Assets and Debts"). The system extracts data from source documents using AI, maps it to PDF form fields intelligently, and fills forms automatically.

## Commands

### Testing
```bash
# Run quick functionality tests
python run_tests.py quick

# Run comprehensive test suite including AI providers
python run_tests.py full

# Test only data extraction capabilities
python run_tests.py extraction

# Test with real form data
python run_tests.py real
```

### Key Dependencies
- **pdftk** - External PDF toolkit for form manipulation (required)
- **Python 3.13+** - Minimum Python version
- **PyQt6** - GUI framework (optional, for GUI mode)

### Environment Setup
Set these environment variables for AI functionality:
- `OPENAI_API_KEY` - For OpenAI API access
- `ANTHROPIC_API_KEY` - For Claude/Anthropic API access

## Architecture

### Core System Flow
```
Source Documents (FL-120/FL-142) → AI/Pattern Extraction → Enhanced Field Mapping → PDF Form Filling
```

### Key Components

#### AI Integration Layer (`enhanced_llm_client.py`)
- Supports both OpenAI and Anthropic APIs
- Intelligent data extraction with structured prompts
- Graceful fallback to pattern matching when AI unavailable

#### Enhanced Field Mapping System (`enhanced_field_mapper.py`)
- Maps 41 out of 132 FL-142 fields (31.1% coverage)
- Pattern-based extraction with intelligent field matching
- Configuration in `comprehensive_field_mapping.json`

#### Form Processing Pipeline
- `python_form_filler.py` - Core PDF form filling using pdftk
- `create_filled_fl142.py` - FL-142 specific form creation
- External form templates in `../../agentic_form_filler/Forms/`
- Client data sources in `../../agentic_form_filler/client_data/Rogers/`

### Data Extraction Components
- `generic_ai_extractor.py` - Generic AI-powered form extractor
- `comprehensive_financial_extractor.py` - Multi-agent financial data extraction
- `advanced_extraction_system.py` - Pattern-based fallback system

## Critical Status

### Working Features
- Enhanced field mapping (4x improvement over basic pattern matching)
- AI client integration framework
- PDF form filling with pdftk
- Comprehensive pattern-based fallback system

### Known Issues
1. **AI Integration Incomplete** - AI extraction components exist but aren't fully connected to enhanced mapping
2. **API Keys Missing** - System falls back to pattern matching without OPENAI_API_KEY or ANTHROPIC_API_KEY
3. **Sample Data Only** - Forms currently filled with sample data rather than extracted from source documents
4. **Missing Source Processing** - Available FL-120/FL-142 source documents not being processed

### Immediate Next Steps
1. Set AI API keys in environment variables
2. Connect `generic_ai_extractor.py` with `enhanced_field_mapper.py`
3. Process actual source documents instead of using sample data
4. Test complete end-to-end pipeline from source docs to filled PDFs

## File Structure Notes

### Core Files
- `enhanced_llm_client.py` - Main AI client
- `enhanced_field_mapper.py` - Core field mapping system
- `python_form_filler.py` - PDF form filling functionality
- `comprehensive_field_mapping.json` - Enhanced field mappings (41/132 fields)

### Test Files
All test files follow `test_*.py` naming convention. Key tests:
- `test_e2e_pipeline.py` - End-to-end pipeline testing
- `enhanced_field_mapping_test.py` - Field mapping system validation
- `simple_enhanced_test.py` - Basic form filling tests

### Legacy Files
Multiple iteration files (`python_form_filler2.py`, `python_form_filler3.py`, etc.) show system evolution. Focus on the non-numbered versions for current functionality.

## Development Notes

- The system is designed to be generic and work with any form type, not just FL-142
- Multi-agent validation and improvement systems are built-in
- Modular design with clear separation between extraction, mapping, and filling
- Quality control systems include confidence scoring and validation