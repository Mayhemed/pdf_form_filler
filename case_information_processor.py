#!/usr/bin/env python3
"""
Case Information Statement Processor
Author: Assistant
Description: Processes case information statements to guide AI form filling decisions
"""

import json
import re
import logging
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class CaseInformation:
    """Structured case information to guide form filling"""
    case_number: Optional[str] = None
    court_county: Optional[str] = None
    petitioner: Optional[str] = None
    respondent: Optional[str] = None
    case_type: Optional[str] = None
    attorney_name: Optional[str] = None
    attorney_phone: Optional[str] = None
    attorney_email: Optional[str] = None
    attorney_address: Optional[str] = None
    marriage_date: Optional[str] = None
    separation_date: Optional[str] = None
    children_involved: Optional[bool] = None
    property_disputes: Optional[bool] = None
    support_requests: Optional[bool] = None
    restraining_orders: Optional[bool] = None
    special_instructions: Optional[str] = None
    filing_party: Optional[str] = None  # "petitioner" or "respondent"
    
class CaseInformationProcessor:
    """
    Processes case information statements to provide context for AI form filling.
    This helps the AI understand what information should be prioritized and 
    how different form fields should be populated based on case context.
    """
    
    def __init__(self):
        """Initialize the case information processor"""
        self.case_info = CaseInformation()
        
    def process_case_statement(self, statement: Union[str, Dict, Path]) -> CaseInformation:
        """
        Process a case information statement from various input formats
        
        Args:
            statement: Can be:
                - String: Natural language case description
                - Dict: Structured case information
                - Path: Path to case information file (JSON, text)
                
        Returns:
            CaseInformation object with structured case details
        """
        logger.info("🔍 Processing case information statement")
        
        if isinstance(statement, (str, Path)):
            if isinstance(statement, Path) or (isinstance(statement, str) and statement.endswith(('.json', '.txt'))):
                # File path
                return self._process_case_file(Path(statement))
            else:
                # Natural language string
                return self._process_natural_language(statement)
        elif isinstance(statement, dict):
            # Structured dictionary
            return self._process_structured_dict(statement)
        else:
            raise ValueError(f"Unsupported case statement type: {type(statement)}")
    
    def _process_natural_language(self, statement: str) -> CaseInformation:
        """Process natural language case description"""
        logger.info("📝 Processing natural language case statement")
        
        case_info = CaseInformation()
        statement_lower = statement.lower()
        
        # Extract case number
        case_pattern = r'\b(?:case\s+(?:number|no\.?)\s*:?\s*)?([0-9]+[A-Z]+[0-9]+)\b'
        case_match = re.search(case_pattern, statement, re.IGNORECASE)
        if case_match:
            case_info.case_number = case_match.group(1)
        
        # Extract names with common legal patterns
        petitioner_patterns = [
            r'petitioner\s*:?\s*([A-Z][a-z]+ [A-Z][a-z]+)',
            r'plaintiff\s*:?\s*([A-Z][a-z]+ [A-Z][a-z]+)',
            r'filing\s+party\s*:?\s*([A-Z][a-z]+ [A-Z][a-z]+)'
        ]
        
        for pattern in petitioner_patterns:
            match = re.search(pattern, statement, re.IGNORECASE)
            if match:
                case_info.petitioner = match.group(1)
                break
        
        respondent_patterns = [
            r'respondent\s*:?\s*([A-Z][a-z]+ [A-Z][a-z]+)',
            r'defendant\s*:?\s*([A-Z][a-z]+ [A-Z][a-z]+)'
        ]
        
        for pattern in respondent_patterns:
            match = re.search(pattern, statement, re.IGNORECASE)
            if match:
                case_info.respondent = match.group(1)
                break
        
        # Extract attorney information
        attorney_patterns = [
            r'attorney\s*:?\s*([A-Z][a-z]+ [A-Z][a-z]+)',
            r'lawyer\s*:?\s*([A-Z][a-z]+ [A-Z][a-z]+)',
            r'counsel\s*:?\s*([A-Z][a-z]+ [A-Z][a-z]+)'
        ]
        
        for pattern in attorney_patterns:
            match = re.search(pattern, statement, re.IGNORECASE)
            if match:
                case_info.attorney_name = match.group(1)
                break
        
        # Extract phone number
        phone_pattern = r'\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        phone_match = re.search(phone_pattern, statement)
        if phone_match:
            case_info.attorney_phone = f"({phone_match.group(1)}) {phone_match.group(2)}-{phone_match.group(3)}"
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, statement)
        if email_match:
            case_info.attorney_email = email_match.group(0)
        
        # Extract court county
        county_pattern = r'county\s+of\s+([A-Z\s]+?)(?:\s|,|$)'
        county_match = re.search(county_pattern, statement, re.IGNORECASE)
        if county_match:
            case_info.court_county = county_match.group(1).strip().upper()
        
        # Detect case type based on keywords
        if any(word in statement_lower for word in ['divorce', 'dissolution', 'marriage', 'domestic']):
            case_info.case_type = "Family Law - Dissolution"
        elif any(word in statement_lower for word in ['custody', 'visitation', 'child support']):
            case_info.case_type = "Family Law - Child Custody/Support"
        elif any(word in statement_lower for word in ['restraining', 'protective order']):
            case_info.case_type = "Family Law - Restraining Order"
        
        # Detect key issues
        case_info.children_involved = any(word in statement_lower for word in ['child', 'children', 'custody', 'visitation'])
        case_info.property_disputes = any(word in statement_lower for word in ['property', 'asset', 'debt', 'financial'])
        case_info.support_requests = any(word in statement_lower for word in ['support', 'alimony', 'spousal'])
        case_info.restraining_orders = any(word in statement_lower for word in ['restraining', 'protective', 'dv'])
        
        # Extract dates
        date_patterns = [
            r'married\s+(?:on\s+)?([A-Z][a-z]+ \d{1,2},? \d{4})',
            r'marriage\s+date\s*:?\s*([A-Z][a-z]+ \d{1,2},? \d{4})',
            r'separated\s+(?:on\s+)?([A-Z][a-z]+ \d{1,2},? \d{4})',
            r'separation\s+date\s*:?\s*([A-Z][a-z]+ \d{1,2},? \d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, statement, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                if 'married' in pattern or 'marriage' in pattern:
                    case_info.marriage_date = date_str
                elif 'separated' in pattern or 'separation' in pattern:
                    case_info.separation_date = date_str
        
        logger.info(f"✅ Extracted case information: {case_info.case_number}, {case_info.petitioner} vs {case_info.respondent}")
        return case_info
    
    def _process_structured_dict(self, data: Dict) -> CaseInformation:
        """Process structured dictionary case information"""
        logger.info("📊 Processing structured case information")
        
        case_info = CaseInformation()
        
        # Direct mapping from dictionary
        for field_name in case_info.__dataclass_fields__.keys():
            if field_name in data:
                setattr(case_info, field_name, data[field_name])
        
        return case_info
    
    def _process_case_file(self, file_path: Path) -> CaseInformation:
        """Process case information from file"""
        logger.info(f"📂 Processing case file: {file_path.name}")
        
        if not file_path.exists():
            raise FileNotFoundError(f"Case information file not found: {file_path}")
        
        if file_path.suffix.lower() == '.json':
            with open(file_path, 'r') as f:
                data = json.load(f)
            return self._process_structured_dict(data)
        else:
            # Text file
            with open(file_path, 'r') as f:
                content = f.read()
            return self._process_natural_language(content)
    
    def generate_ai_context_prompt(self, case_info: CaseInformation) -> str:
        """
        Generate a context prompt for AI form filling based on case information
        
        Args:
            case_info: Structured case information
            
        Returns:
            String prompt to provide context to AI for form filling decisions
        """
        prompt_parts = [
            "CASE CONTEXT FOR FORM FILLING:",
            "You are filling out a legal form with the following case context:\n"
        ]
        
        if case_info.case_type:
            prompt_parts.append(f"Case Type: {case_info.case_type}")
        
        if case_info.case_number:
            prompt_parts.append(f"Case Number: {case_info.case_number}")
        
        if case_info.petitioner and case_info.respondent:
            prompt_parts.append(f"Parties: {case_info.petitioner} (Petitioner) vs {case_info.respondent} (Respondent)")
        
        if case_info.attorney_name:
            prompt_parts.append(f"Attorney: {case_info.attorney_name}")
            if case_info.attorney_phone:
                prompt_parts.append(f"Attorney Phone: {case_info.attorney_phone}")
            if case_info.attorney_email:
                prompt_parts.append(f"Attorney Email: {case_info.attorney_email}")
        
        if case_info.court_county:
            prompt_parts.append(f"Court County: {case_info.court_county}")
        
        # Key issues
        issues = []
        if case_info.children_involved:
            issues.append("children/custody involved")
        if case_info.property_disputes:
            issues.append("property/financial disputes")
        if case_info.support_requests:
            issues.append("support requests")
        if case_info.restraining_orders:
            issues.append("restraining orders")
        
        if issues:
            prompt_parts.append(f"Key Issues: {', '.join(issues)}")
        
        if case_info.marriage_date:
            prompt_parts.append(f"Marriage Date: {case_info.marriage_date}")
        
        if case_info.separation_date:
            prompt_parts.append(f"Separation Date: {case_info.separation_date}")
        
        if case_info.filing_party:
            prompt_parts.append(f"Filing Party: {case_info.filing_party}")
        
        if case_info.special_instructions:
            prompt_parts.append(f"Special Instructions: {case_info.special_instructions}")
        
        prompt_parts.extend([
            "\nWhen filling this form:",
            "1. Prioritize information relevant to the case type and key issues",
            "2. Use the correct party names in the appropriate fields",
            "3. Include attorney information where required",
            "4. Consider the case context when making field completion decisions",
            "5. If multiple interpretations are possible, choose based on case context\n"
        ])
        
        return "\n".join(prompt_parts)
    
    def get_field_priorities(self, case_info: CaseInformation) -> Dict[str, int]:
        """
        Generate field priorities based on case information
        
        Args:
            case_info: Structured case information
            
        Returns:
            Dictionary mapping field types to priority scores (1-10, 10 being highest)
        """
        priorities = {
            "case_number": 10,
            "party_names": 10,
            "attorney_info": 9,
            "court_info": 9,
            "dates": 7,
            "financial_info": 5,
            "property_info": 5,
            "child_info": 5,
            "support_info": 5
        }
        
        # Adjust priorities based on case context
        if case_info.children_involved:
            priorities["child_info"] = 9
            priorities["support_info"] = 8
        
        if case_info.property_disputes:
            priorities["financial_info"] = 8
            priorities["property_info"] = 8
        
        if case_info.support_requests:
            priorities["support_info"] = 9
            priorities["financial_info"] = 8
        
        return priorities
    
    def to_dict(self, case_info: CaseInformation) -> Dict:
        """Convert case information to dictionary"""
        return asdict(case_info)
    
    def to_json(self, case_info: CaseInformation) -> str:
        """Convert case information to JSON string"""
        return json.dumps(self.to_dict(case_info), indent=2)

# Example usage and testing
if __name__ == "__main__":
    # Test with the actual case from the FL-120 document
    processor = CaseInformationProcessor()
    
    test_statement = """
    Case Number: 24STFL00615
    County of Los Angeles
    Petitioner: TAHIRA FRANCIS
    Respondent: SHAWN ROGERS
    Attorney: Mark Piesner
    Phone: (818) 638-4456
    Email: mark@arcpointlaw.com
    
    This is a family law dissolution case involving marriage dissolution.
    The parties were married on November 20, 2021 and separated on September 1, 2023.
    There are financial assets and debts to be divided.
    Attorney represents the respondent in this matter.
    """
    
    case_info = processor.process_case_statement(test_statement)
    print("🔍 Processed Case Information:")
    print(processor.to_json(case_info))
    
    print("\n📝 AI Context Prompt:")
    print(processor.generate_ai_context_prompt(case_info))
    
    print("\n📊 Field Priorities:")
    priorities = processor.get_field_priorities(case_info)
    for field_type, priority in sorted(priorities.items(), key=lambda x: x[1], reverse=True):
        print(f"  {field_type}: {priority}/10")
