#!/usr/bin/env python3
"""
Smart Data Extractor
Uses intelligent form analysis to extract data with appropriate strategy
"""

import os
import json
import re
from typing import Dict, List, Tuple, Optional

class SmartDataExtractor:
    """Intelligently extracts data based on form analysis"""
    
    def __init__(self):
        pass
    
    def extract_user_data_only(self, blank_form_path: str, filled_form_path: str) -> Dict:
        """
        Extract only user-entered data from a filled form of the same type
        
        This compares the blank template with the filled version to identify
        only the data that was actually entered by the user.
        """
        print(f"🔍 Extracting user data only from {os.path.basename(filled_form_path)}")
        
        try:
            # Get field values from both forms
            blank_values = self._extract_field_values(blank_form_path)
            filled_values = self._extract_field_values(filled_form_path)
            
            user_data = {}
            
            # Compare field by field
            for field_name in filled_values:
                blank_value = blank_values.get(field_name, "")
                filled_value = filled_values.get(field_name, "")
                
                # Check if user actually entered data
                if self._is_user_entered_data(blank_value, filled_value):
                    user_data[field_name] = filled_value
                    print(f"  ✅ User data: {field_name} = '{filled_value}'")
            
            print(f"  📊 Found {len(user_data)} user-entered fields")
            return user_data
            
        except Exception as e:
            print(f"❌ Error extracting user data: {e}")
            return {}
    
    def extract_semantic_overlap(self, target_fields: List[Dict], source_path: str, target_mapping: Dict) -> Dict:
        """
        Extract semantically overlapping data from different form types
        
        This finds data in source documents that can be meaningfully mapped
        to fields in the target form, even if they're different form types.
        """
        print(f"🔄 Extracting semantic overlap from {os.path.basename(source_path)}")
        
        try:
            # Extract all data from source
            source_values = self._extract_field_values(source_path)
            
            semantic_matches = {}
            
            # For each target field, find semantic matches in source
            for field_num, field_info in target_mapping.items():
                target_field_name = field_info.get('full_field_name', '')
                target_description = field_info.get('description', '').lower()
                
                # Find best semantic match
                best_match = self._find_semantic_match(
                    target_field_name, target_description, source_values
                )
                
                if best_match:
                    semantic_matches[field_num] = best_match['value']
                    print(f"  ✅ Semantic match: Field {field_num} ({target_description[:30]}...) = '{best_match['value']}'")
            
            print(f"  📊 Found {len(semantic_matches)} semantic matches")
            return semantic_matches
            
        except Exception as e:
            print(f"❌ Error extracting semantic overlap: {e}")
            return {}
    
    def _extract_field_values(self, pdf_path: str) -> Dict[str, str]:
        """Extract current field values from PDF"""
        try:
            import subprocess
            
            # Use pdftk to dump field data
            cmd = ['pdftk', pdf_path, 'dump_data_fields']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            values = {}
            current_field = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('---'):
                    if current_field and 'FieldName' in current_field:
                        field_name = current_field['FieldName']
                        field_value = current_field.get('FieldValue', '')
                        values[field_name] = field_value
                        current_field = {}
                elif ': ' in line:
                    key, value = line.split(': ', 1)
                    current_field[key] = value
            
            # Handle last field
            if current_field and 'FieldName' in current_field:
                field_name = current_field['FieldName']
                field_value = current_field.get('FieldValue', '')
                values[field_name] = field_value
            
            return values
            
        except Exception as e:
            print(f"Error extracting field values: {e}")
            return {}
    
    def _is_user_entered_data(self, blank_value: str, filled_value: str) -> bool:
        """Determine if a field contains user-entered data vs template content"""
        
        # Skip empty fields
        if not filled_value or not filled_value.strip():
            return False
        
        # Skip if same as blank template
        if blank_value == filled_value:
            return False
        
        # Skip common template values
        template_patterns = [
            r'^\d{1,3}$',  # Just numbers 1-999
            r'^enter\s+',  # "Enter data here"
            r'^fill\s+',   # "Fill in"
            r'^placeholder', # Placeholder text
            r'^example',   # Example text
            r'^\$0\.00$',  # Zero money amounts
            r'^0+$',       # All zeros
        ]
        
        filled_lower = filled_value.lower().strip()
        for pattern in template_patterns:
            if re.match(pattern, filled_lower):
                return False
        
        # If we get here, it's likely user data
        return True
    
    def _find_semantic_match(self, target_field_name: str, target_description: str, source_values: Dict[str, str]) -> Optional[Dict]:
        """Find semantic match for target field in source values"""
        
        best_match = None
        best_score = 0.0
        
        # Determine what type of data the target field needs
        field_intent = self._determine_field_intent(target_field_name, target_description)
        
        for source_field_name, source_value in source_values.items():
            if not source_value or not source_value.strip():
                continue
            
            # Calculate semantic similarity
            score = self._calculate_semantic_score(
                field_intent, source_field_name, source_value
            )
            
            if score > best_score and score > 0.5:  # Minimum threshold
                best_score = score
                best_match = {
                    'value': source_value,
                    'source_field': source_field_name,
                    'score': score
                }
        
        return best_match
    
    def _determine_field_intent(self, field_name: str, description: str) -> str:
        """Determine what type of data a field is looking for"""
        
        combined_text = (field_name + " " + description).lower()
        
        # Define intent patterns
        intent_patterns = {
            "attorney_name": ["attorney", "lawyer", "counsel"],
            "attorney_phone": ["attorney", "phone", "telephone"],
            "attorney_email": ["attorney", "email"],
            "petitioner_name": ["petitioner", "plaintiff"],
            "respondent_name": ["respondent", "defendant"],
            "case_number": ["case", "number", "file"],
            "court_name": ["court", "county", "jurisdiction"],
            "monetary_amount": ["amount", "value", "balance", "total", "decimal"],
            "date": ["date", "when", "time"],
            "address": ["address", "street", "location"],
            "phone": ["phone", "telephone"],
            "email": ["email", "e-mail"],
            "description": ["description", "detail", "specify"]
        }
        
        # Find best matching intent
        for intent, keywords in intent_patterns.items():
            if any(keyword in combined_text for keyword in keywords):
                return intent
        
        return "general"
    
    def _calculate_semantic_score(self, target_intent: str, source_field_name: str, source_value: str) -> float:
        """Calculate semantic similarity score"""
        
        score = 0.0
        source_field_lower = source_field_name.lower()
        source_value_lower = source_value.lower()
        
        # Intent-based scoring
        if target_intent == "attorney_name":
            if any(word in source_field_lower for word in ["attorney", "lawyer", "counsel"]):
                score += 0.8
            if self._looks_like_name(source_value):
                score += 0.6
        
        elif target_intent == "attorney_phone":
            if "phone" in source_field_lower and "attorney" in source_field_lower:
                score += 0.9
            elif self._looks_like_phone(source_value):
                score += 0.7
        
        elif target_intent == "case_number":
            if any(word in source_field_lower for word in ["case", "number", "file"]):
                score += 0.8
            if self._looks_like_case_number(source_value):
                score += 0.6
        
        elif target_intent == "monetary_amount":
            if any(word in source_field_lower for word in ["amount", "balance", "total"]):
                score += 0.8
            if self._looks_like_money(source_value):
                score += 0.6
        
        elif target_intent == "petitioner_name":
            if "petitioner" in source_field_lower or "plaintiff" in source_field_lower:
                score += 0.9
            elif self._looks_like_name(source_value):
                score += 0.5
        
        elif target_intent == "respondent_name":
            if "respondent" in source_field_lower or "defendant" in source_field_lower:
                score += 0.9
            elif self._looks_like_name(source_value):
                score += 0.5
        
        # General field name similarity
        if any(word in source_field_lower for word in target_intent.split('_')):
            score += 0.3
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _looks_like_name(self, value: str) -> bool:
        """Check if value looks like a person's name"""
        if not value:
            return False
        return bool(re.match(r'^[A-Z][a-z]+(?: [A-Z][a-z]+)+$', value.strip()))
    
    def _looks_like_phone(self, value: str) -> bool:
        """Check if value looks like a phone number"""
        if not value:
            return False
        return bool(re.match(r'^\(?[\d\s\-\.\(\)]{10,}$', value.strip()))
    
    def _looks_like_case_number(self, value: str) -> bool:
        """Check if value looks like a case number"""
        if not value:
            return False
        return bool(re.match(r'^\d{2}[A-Z]{2,4}\d{5,8}$', value.strip()))
    
    def _looks_like_money(self, value: str) -> bool:
        """Check if value looks like a monetary amount"""
        if not value:
            return False
        return bool(re.match(r'^\$?[\d,]+\.?\d*$', value.replace(' ', '')))


def test_smart_extractor():
    """Test the smart data extractor"""
    extractor = SmartDataExtractor()
    
    # Test paths (adjust as needed)
    blank_form = "/Users/markpiesner/Arc Point Law Dropbox/Forms/fl142blank.pdf"
    filled_form = "/Users/markpiesner/Documents/GitHub/agentic_form_filler/client_data/Rogers/fl142 copy.pdf"
    
    if os.path.exists(blank_form) and os.path.exists(filled_form):
        print("🧪 Testing smart data extraction...")
        user_data = extractor.extract_user_data_only(blank_form, filled_form)
        print(f"\n📊 Extracted {len(user_data)} user-entered fields")
        
        for field_name, value in list(user_data.items())[:5]:  # Show first 5
            print(f"  {field_name}: {value}")
    else:
        print("Test files not found")


if __name__ == "__main__":
    test_smart_extractor()