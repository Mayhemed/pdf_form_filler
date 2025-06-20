#!/usr/bin/env python3
"""
Fixed Anthropic Method for python_form_filler3.py
Author: Assistant
Description: Clean generic anthropic extraction method
"""

def create_fixed_anthropic_method():
    """Create the fixed anthropic extraction method text"""
    
    method_text = '''    def _extract_with_anthropic(self, text: str) -> Tuple[Dict[str, str], Dict[str, float]]:
        """Extract data using Anthropic Claude via llm_client"""
        if not self.api_key:
            raise ValueError("Anthropic API key required")

        print("="*50)
        print("CLAUDE EXTRACTION DEBUGGING")
        print(f"API Key length: {len(self.api_key)} chars")
        print(f"Model specified: {self.model}")
        print(f"Text length for analysis: {len(text)} chars")

        try:
            # Import our llm_client module
            import llm_client

            # Set the API key in environment (llm_client uses this)
            os.environ["ANTHROPIC_API_KEY"] = self.api_key.strip()
            print(f"Set ANTHROPIC_API_KEY environment variable")

            field_names = [f.name for f in self.form_fields]
            field_descriptions = [f.alt_text or f.name for f in self.form_fields]

            print(f"Number of fields to extract: {len(field_names)}")
            if field_names:
                print(f"First field: {field_names[0]}")

            # Use the model specified by the user, or fall back to a default
            model = self.model if self.model else "claude-3-opus-20240229"
            print(f"Using llm_client with Claude model: {model}")

            # Generic prompt for any form type
            prompt = f"""You are analyzing documents to extract comprehensive data for a PDF form.

I have provided you with:
1. A NUMBERED MAPPING PDF showing field locations (numbered 1, 2, 3, etc.)  
2. SOURCE DOCUMENTS containing filled-in data

EXTRACTION TARGET: Extract data for ALL VISIBLE numbered fields in the mapping PDF.

COMPREHENSIVE EXTRACTION STRATEGY:
- Look at the numbered mapping PDF to see all available field numbers
- Extract data from ALL source documents
- Match data to the appropriate numbered field locations  
- Be comprehensive - try to fill as many fields as possible

EXTRACTION RULES:
✅ **USE NUMBERED KEYS**: Return field numbers (1, 2, 3) NOT field names
✅ **BE COMPREHENSIVE**: Try to extract data for as many numbered fields as visible
✅ **EXTRACT FROM ALL SOURCES**: Look in ALL source documents
✅ **EXTRACT REAL VALUES**: Only filled-in data, ignore blank fields

DOCUMENT CONTENT TO ANALYZE:
{text[:4000]}

RETURN FORMAT - Use numbered keys (1, 2, 3, etc.):

{{
    "extracted_data": {{
        "1": "extracted_value_1",
        "2": "extracted_value_2", 
        "3": "extracted_value_3"
    }},
    "confidence_scores": {{
        "1": 0.95,
        "2": 0.95,
        "3": 0.95
    }}
}}

CRITICAL: Extract data for AS MANY numbered fields as possible by looking at the mapping PDF."""

            # Generate response using llm_client
            response_text = llm_client.generate_with_claude(model, prompt)
            print(f"Claude response received, length: {len(response_text)}")
            print(f"First 100 chars of response: {response_text[:100]}")

            # Parse response - wrap in try/except to better handle parsing errors
            try:
                # Find the start and end of the JSON object if there's any surrounding text
                start = response_text.find('{')
                end = response_text.rfind('}') + 1

                print(f"JSON start position: {start}, end position: {end}")

                if start >= 0 and end > start:
                    json_text = response_text[start:end]
                    print(f"Attempting to parse JSON of length {len(json_text)}")

                    try:
                        result = json.loads(json_text)
                        extracted_data = result.get("extracted_data", {})
                        confidence_scores = result.get("confidence_scores", {})

                        # If missing confidence scores, generate defaults
                        if not confidence_scores and extracted_data:
                            confidence_scores = {k: 0.85 for k in extracted_data.keys()}

                        print(f"Successfully parsed JSON with {len(extracted_data)} extracted fields")
                        
                        # Convert numbered results to field names
                        converted_data, converted_confidence = self._convert_numbered_to_field_names(
                            extracted_data, confidence_scores
                        )
                        
                        return converted_data, converted_confidence

                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                        print(f"JSON text: {json_text[:500]}...")
                        return {}, {}
                else:
                    print(f"Invalid JSON response from Claude: {response_text[:100]}...")
                    return {}, {}

            except Exception as e:
                print(f"Error parsing Claude response: {e}")
                return {}, {}

        except Exception as e:
            print(f"Claude API error: {str(e)}")
            print(f"Exception type: {type(e).__name__}")
            print(traceback.format_exc())
            self.show_message.emit("Claude API Error", f"Error: {str(e)}")
            return {}, {}'''
    
    return method_text

if __name__ == "__main__":
    print("🔧 FIXED ANTHROPIC METHOD:")
    print("=" * 60)
    print(create_fixed_anthropic_method())
    print("=" * 60)
    print("\n✅ This is a clean, generic method that:")
    print("- Works with any PDF form type")
    print("- Uses numbered field mapping")
    print("- Doesn't hardcode any form-specific information")
    print("- Properly handles the try/except structure")
    print("- Converts numbered results to field names")
