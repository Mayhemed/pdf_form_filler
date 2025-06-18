#!/usr/bin/env python3
"""
Intelligent Form Analyzer
Compares target form with source documents to determine extraction strategy
"""

import os
import subprocess
import json
import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path

class IntelligentFormAnalyzer:
    """Analyzes forms to determine optimal extraction strategy"""
    
    def __init__(self):
        self.form_signatures = {}
        self.field_mappings = {}
    
    def analyze_form_relationship(self, target_form_path: str, source_paths: List[str]) -> Dict:
        """
        Analyze relationship between target form and source documents
        
        Returns:
        {
            "strategy": "same_form" | "cross_form" | "hybrid",
            "same_form_sources": [paths],
            "cross_form_sources": [paths], 
            "target_analysis": {...},
            "source_analyses": {...}
        }
        """
        result = {
            "strategy": "cross_form",
            "same_form_sources": [],
            "cross_form_sources": [],
            "target_analysis": {},
            "source_analyses": {}
        }
        
        # Analyze target form
        target_analysis = self._analyze_single_form(target_form_path)
        result["target_analysis"] = target_analysis
        
        print(f"🎯 Target form: {os.path.basename(target_form_path)}")
        print(f"   Type: {target_analysis['form_type']}")
        print(f"   Fields: {target_analysis['field_count']}")
        
        # Analyze each source document
        for source_path in source_paths:
            source_analysis = self._analyze_single_form(source_path)
            result["source_analyses"][source_path] = source_analysis
            
            print(f"📄 Source: {os.path.basename(source_path)}")
            print(f"   Type: {source_analysis['form_type']}")
            print(f"   Fields: {source_analysis['field_count']}")
            
            # Compare forms to determine relationship
            if self._are_same_form_type(target_analysis, source_analysis):
                result["same_form_sources"].append(source_path)
                print(f"   ✅ SAME FORM TYPE - will extract user data only")
            else:
                result["cross_form_sources"].append(source_path)
                print(f"   🔄 DIFFERENT FORM - will extract overlapping content")
        
        # Determine overall strategy
        if result["same_form_sources"] and result["cross_form_sources"]:
            result["strategy"] = "hybrid"
        elif result["same_form_sources"]:
            result["strategy"] = "same_form"
        else:
            result["strategy"] = "cross_form"
        
        print(f"\n🧠 STRATEGY: {result['strategy'].upper()}")
        return result
    
    def _analyze_single_form(self, pdf_path: str) -> Dict:
        """Analyze a single PDF form"""
        try:
            # Extract form fields
            fields = self._extract_form_fields(pdf_path)
            
            # Determine form type based on field patterns
            form_type = self._detect_form_type(fields, pdf_path)
            
            # Create form signature
            signature = self._create_form_signature(fields)
            
            return {
                "form_type": form_type,
                "field_count": len(fields),
                "signature": signature,
                "fields": fields,
                "path": pdf_path
            }
            
        except Exception as e:
            print(f"Error analyzing form {pdf_path}: {e}")
            return {
                "form_type": "unknown",
                "field_count": 0,
                "signature": "",
                "fields": [],
                "path": pdf_path
            }
    
    def _extract_form_fields(self, pdf_path: str) -> List[Dict]:
        """Extract form fields using pdftk"""
        try:
            cmd = ['pdftk', pdf_path, 'dump_data_fields']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            fields = []
            current_field = {}
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('---'):
                    if current_field:
                        fields.append(current_field)
                        current_field = {}
                elif ': ' in line:
                    key, value = line.split(': ', 1)
                    current_field[key] = value
            
            if current_field:
                fields.append(current_field)
                
            return fields
            
        except Exception as e:
            print(f"Error extracting fields from {pdf_path}: {e}")
            return []
    
    def _detect_form_type(self, fields: List[Dict], pdf_path: str) -> str:
        """Detect form type based on fields and filename"""
        filename = os.path.basename(pdf_path).lower()
        
        # Check filename patterns first
        if 'fl-142' in filename or 'fl142' in filename:
            return "FL-142"
        elif 'fl-120' in filename or 'fl120' in filename:
            return "FL-120"
        elif 'fl-335' in filename or 'fl335' in filename:
            return "FL-335"
        
        # Analyze field patterns
        field_names = [f.get('FieldName', '').lower() for f in fields]
        field_texts = ' '.join(field_names)
        
        # FL-142 patterns (Schedule of Assets and Debts)
        if any(pattern in field_texts for pattern in [
            'decimalfield', 'asset', 'debt', 'real estate', 'household', 'vehicle'
        ]):
            return "FL-142"
        
        # FL-120 patterns (Declaration)
        if any(pattern in field_texts for pattern in [
            'declaration', 'attorney', 'petitioner', 'respondent'
        ]):
            return "FL-120"
        
        return "Unknown"
    
    def _create_form_signature(self, fields: List[Dict]) -> str:
        """Create a signature to identify form types"""
        # Use field count and key field patterns
        field_count = len(fields)
        
        # Key field patterns
        patterns = []
        for field in fields[:10]:  # Use first 10 fields for signature
            field_name = field.get('FieldName', '')
            if field_name:
                # Normalize field name
                normalized = re.sub(r'\[\d+\]', '', field_name).lower()
                patterns.append(normalized)
        
        return f"{field_count}:{':'.join(patterns[:5])}"
    
    def _are_same_form_type(self, target_analysis: Dict, source_analysis: Dict) -> bool:
        """Determine if two forms are the same type"""
        
        # Direct form type match
        if (target_analysis["form_type"] != "Unknown" and 
            source_analysis["form_type"] != "Unknown" and
            target_analysis["form_type"] == source_analysis["form_type"]):
            return True
        
        # Field count similarity (within 10%)
        target_count = target_analysis["field_count"]
        source_count = source_analysis["field_count"]
        
        if target_count > 0 and source_count > 0:
            ratio = min(target_count, source_count) / max(target_count, source_count)
            if ratio > 0.9:  # 90% similarity in field count
                return True
        
        # Signature similarity
        target_sig = target_analysis["signature"]
        source_sig = source_analysis["signature"]
        
        if target_sig and source_sig:
            # Compare field count part
            target_count_sig = target_sig.split(':')[0]
            source_count_sig = source_sig.split(':')[0]
            
            if target_count_sig == source_count_sig:
                return True
        
        return False
    
    def create_extraction_strategy(self, analysis_result: Dict, target_mapping: Dict) -> Dict:
        """Create extraction strategy based on form analysis"""
        
        strategy = {
            "approach": analysis_result["strategy"],
            "extractions": []
        }
        
        # Handle same form sources (extract user data only)
        for source_path in analysis_result["same_form_sources"]:
            strategy["extractions"].append({
                "source": source_path,
                "type": "user_data_only",
                "method": "field_diff",
                "description": "Extract only user-entered data, ignore template content"
            })
        
        # Handle cross-form sources (extract overlapping content)
        for source_path in analysis_result["cross_form_sources"]:
            strategy["extractions"].append({
                "source": source_path,
                "type": "semantic_mapping",
                "method": "intelligent_overlap",
                "description": "Find semantically matching content across different form types"
            })
        
        return strategy


def test_form_analyzer():
    """Test the form analyzer"""
    analyzer = IntelligentFormAnalyzer()
    
    # Test with sample files (adjust paths as needed)
    target_form = "/Users/markpiesner/Arc Point Law Dropbox/Forms/fl142blank.pdf"
    source_files = [
        "/Users/markpiesner/Documents/GitHub/agentic_form_filler/client_data/Rogers/fl142 copy.pdf",
        "/Users/markpiesner/Documents/GitHub/agentic_form_filler/client_data/Rogers/Rogers-FL120-signed.pdf"
    ]
    
    if os.path.exists(target_form):
        result = analyzer.analyze_form_relationship(target_form, [f for f in source_files if os.path.exists(f)])
        strategy = analyzer.create_extraction_strategy(result, {})
        
        print(f"\n📊 ANALYSIS COMPLETE")
        print(f"Strategy: {strategy['approach']}")
        for extraction in strategy['extractions']:
            print(f"  - {os.path.basename(extraction['source'])}: {extraction['type']}")
    else:
        print(f"Target form not found: {target_form}")


if __name__ == "__main__":
    test_form_analyzer()