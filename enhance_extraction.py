#!/usr/bin/env python3
"""
Enhanced AI extraction to get BOTH field labels AND filled data
"""

def create_enhanced_extraction_prompt():
    """Create an enhanced prompt that gets both field labels and filled data"""
    
    return '''
def _extract_with_anthropic(self, text: str) -> Tuple[Dict[str, str], Dict[str, float]]:
    """Extract data using Anthropic Claude - ENHANCED TO GET BOTH LABELS AND DATA"""
    if not self.api_key:
        raise ValueError("Anthropic API key required")

    print("="*50)
    print("CLAUDE EXTRACTION DEBUGGING")
    print(f"API Key length: {len(self.api_key)} chars")
    print(f"Model specified: {self.model}")
    print(f"Text length for analysis: {len(text)} chars")

    try:
        field_names = [f.name for f in self.form_fields]
        field_descriptions = [f.alt_text or f.name for f in self.form_fields]

        print(f"Number of fields to extract: {len(field_names)}")
        if field_names:
            print(f"First field: {field_names[0]}")

        # Use the model specified by the user, or fall back to a default
        model = self.model if self.model else "claude-3-sonnet-20240229"
        print(f"Using Claude model: {model}")

        # ENHANCED PROMPT - Gets BOTH field labels AND filled data
        prompt = f"""You are analyzing legal documents to extract COMPREHENSIVE FORM DATA including both field labels and filled-in values.

TARGET EXTRACTION: For each form field, extract BOTH the field label/description AND any filled-in data values.

EXTRACTION STRATEGY:

1. FIELD LABELS/TITLES (keep current functionality):
   - Extract field descriptions, labels, and instructions
   - Example: "ATTORNEY OR PARTY WITHOUT ATTORNEY (Name and Address):"
   - Example: "CASE NUMBER:"
   - Example: "PETITIONER:"

2. FILLED-IN DATA VALUES (new enhanced functionality):
   - Look for actual user-entered data near each field
   - Names: "Mark Piesner", "TAHIRA FRANCIS", "SHAWN ROGERS"
   - Case numbers: "24STFL00615"  
   - Addresses: "22287 Mulholland Hwy, Calabasas CA 91302"
   - Phone numbers: "(818) 638-4456"
   - Email addresses: "mark@arcpointlaw.com"
   - Financial amounts: "$22,000.00", "$25,000.00"
   - Dates: "December 12, 2024"

3. SMART FIELD MAPPING:
   For each form field, provide the BEST available information:
   - If field has both label AND data: combine them intelligently
   - If field has only label: provide the label (current behavior)
   - If field has only data: provide the data value
   - If field appears empty: provide the label for reference

EXAMPLES OF ENHANCED EXTRACTION:

Field: TextField1[0] (Attorney Name field)
Current: "ATTORNEY OR PARTY WITHOUT ATTORNEY (Name and Address):"
Enhanced: "Mark Piesner, Arc Point Law PC, 22287 Mulholland Hwy, Calabasas CA 91302 [Field: ATTORNEY OR PARTY WITHOUT ATTORNEY]"

Field: CaseNumber[0] (Case Number field)  
Current: "CASE NUMBER:"
Enhanced: "24STFL00615 [Field: CASE NUMBER]"

Field: Party1[0] (Petitioner field)
Current: "PETITIONER:"
Enhanced: "TAHIRA FRANCIS [Field: PETITIONER]"

DOCUMENT CONTENT TO ANALYZE:
{text[:4000]}

AVAILABLE FORM FIELDS (extract enhanced data for these exact field names):
{json.dumps(field_names[:20], indent=2)}

RETURN FORMAT - Enhanced JSON with both labels and data:

{{
    "extracted_data": {{
        "EXACT_FIELD_NAME": "FILLED_VALUE [Field: FIELD_LABEL]"
    }},
    "confidence_scores": {{
        "EXACT_FIELD_NAME": 0.95
    }}
}}

EXTRACTION RULES:
✅ KEEP current field label extraction (preserve existing functionality)
✅ ADD filled-in data values where available (new enhancement)
✅ COMBINE intelligently: "VALUE [Field: LABEL]" format when both exist
✅ USE exact field names from the list as keys
✅ IGNORE completely empty fields (no label, no data)
✅ PRIORITIZE actual user data over template text
✅ PROVIDE context by including field labels in brackets

Extract comprehensive data for AS MANY fields as possible, combining both labels and values."""

        try:
            # Try to use llm_client if available
            import llm_client
            os.environ["ANTHROPIC_API_KEY"] = self.api_key.strip()
            print(f"Set ANTHROPIC_API_KEY environment variable")
            
            response_text = llm_client.generate_with_claude(model, prompt)
            print(f"Claude response received, length: {len(response_text)}")
            print(f"Raw response preview: {response_text[:200]}...")
            
        except ImportError:
            # Fallback to direct Anthropic API
            print("llm_client not available, using direct Anthropic API")
            client = anthropic.Anthropic(api_key=self.api_key)
            
            response = client.messages.create(
                model=model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = response.content[0].text
            print(f"Claude response received, length: {len(response_text)}")
            print(f"Raw response preview: {response_text[:200]}...")

        # Parse response using existing method
        extracted_data, confidence_scores = self._parse_claude_response(response_text)
        
        if extracted_data:
            print(f"Successfully extracted {len(extracted_data)} enhanced fields")
            return extracted_data, confidence_scores
        else:
            print("No data extracted, falling back to pattern matching")
            return self._extract_with_patterns(text)

    except Exception as e:
        print(f"Claude API error: {str(e)}")
        print("Falling back to pattern matching")
        return self._extract_with_patterns(text)
    '''

def create_enhanced_openai_prompt():
    """Create an enhanced OpenAI prompt that gets both field labels and filled data"""
    
    return '''
def _extract_with_openai(self, text: str) -> Tuple[Dict[str, str], Dict[str, float]]:
    """Extract data using OpenAI GPT - ENHANCED TO GET BOTH LABELS AND DATA"""
    if not self.api_key:
        raise ValueError("OpenAI API key required")
    
    print("="*50)
    print("OPENAI EXTRACTION DEBUGGING")
    print(f"API Key length: {len(self.api_key)} chars")
    print(f"Model specified: {self.model}")
    print(f"Text length for analysis: {len(text)} chars")
    
    # Create field extraction prompt
    field_names = [f.name for f in self.form_fields]
    field_descriptions = [f.alt_text or f.name for f in self.form_fields]
    
    print(f"Number of fields to extract: {len(field_names)}")
    if field_names:
        print(f"First field: {field_names[0]}")
    
    # ENHANCED PROMPT - Gets BOTH field labels AND filled data
    prompt = f"""# Enhanced Legal Document Data Extraction

You are extracting COMPREHENSIVE form data from California family law documents, capturing BOTH field labels AND filled-in values.

## ENHANCED EXTRACTION APPROACH:

### 1. DUAL EXTRACTION STRATEGY:
- **Field Labels**: Extract form field descriptions and labels (current functionality)
- **Filled Data**: Extract actual user-entered values (new enhancement)
- **Smart Combination**: Merge both when available in format "VALUE [Field: LABEL]"

### 2. ATTORNEY INFORMATION (from FL-120 if present):
- Field Labels: "ATTORNEY OR PARTY WITHOUT ATTORNEY", "TELEPHONE NO:", "ATTORNEY FOR"
- Filled Data: "Mark Piesner", "(818) 638-4456", "mark@arcpointlaw.com"
- Enhanced Output: "Mark Piesner, Arc Point Law PC [Field: ATTORNEY OR PARTY WITHOUT ATTORNEY]"

### 3. CASE INFORMATION (from any source):
- Field Labels: "CASE NUMBER:", "PETITIONER:", "RESPONDENT:", "COUNTY OF"
- Filled Data: "24STFL00615", "TAHIRA FRANCIS", "SHAWN ROGERS", "LOS ANGELES"
- Enhanced Output: "24STFL00615 [Field: CASE NUMBER]"

### 4. FINANCIAL DATA (from FL-142 if present):
- Field Labels: "STUDENT LOANS", "CREDIT CARDS", "TOTAL DEBTS"
- Filled Data: "$22,000.00", "$3,042.81", "$64,225.81"
- Enhanced Output: "$22,000.00 [Field: STUDENT LOANS]"

## TARGET FIELDS (extract enhanced data for these exact field names):
{json.dumps(dict(zip(field_names, field_descriptions)), indent=2)}

## EXTRACTION RULES:

✅ **PRESERVE CURRENT FUNCTIONALITY** - Keep extracting field labels/descriptions
✅ **ADD FILLED VALUES** - Extract actual user-entered data where available  
✅ **SMART COMBINATION** - Use "VALUE [Field: LABEL]" format when both exist
✅ **EXACT FIELD NAMES** - Return exact field name from list as key
✅ **COMPREHENSIVE COVERAGE** - Extract both template and data elements
✅ **PRIORITIZE USER DATA** - When available, emphasize actual filled values
✅ **MAINTAIN CONTEXT** - Include field labels for reference even with data

## DOCUMENT CONTENT TO ANALYZE:
{text[:6000]}

## ENHANCED OUTPUT FORMAT:

{{
    "extracted_data": {{
        "TextField1[0]": "Mark Piesner, Arc Point Law PC, 22287 Mulholland Hwy [Field: ATTORNEY OR PARTY WITHOUT ATTORNEY]",
        "CaseNumber[0]": "24STFL00615 [Field: CASE NUMBER]",
        "Party1[0]": "TAHIRA FRANCIS [Field: PETITIONER]",
        "DecimalField40[0]": "$22,000.00 [Field: STUDENT LOANS]"
    }},
    "confidence_scores": {{
        "TextField1[0]": 0.95,
        "CaseNumber[0]": 0.95,
        "Party1[0]": 0.95,
        "DecimalField40[0]": 0.90
    }}
}}

Extract comprehensive data combining both field context and actual values for maximum utility."""
    
    # Continue with existing OpenAI implementation...
    '''

if __name__ == "__main__":
    print("🔧 Enhanced AI Extraction - Gets Both Labels AND Data")
    print("=" * 60)
    print("This enhancement preserves current field label extraction")
    print("while adding extraction of actual filled-in values.")
    print()
    print("Enhanced format: 'ACTUAL_VALUE [Field: FIELD_LABEL]'")
    print()
    print("Examples:")
    print("• Current: 'CASE NUMBER:'")
    print("• Enhanced: '24STFL00615 [Field: CASE NUMBER]'")
    print()
    print("• Current: 'ATTORNEY OR PARTY WITHOUT ATTORNEY:'")  
    print("• Enhanced: 'Mark Piesner, Arc Point Law PC [Field: ATTORNEY OR PARTY WITHOUT ATTORNEY]'")
    print()
    print("This gives you BOTH the field context AND the actual data!")
