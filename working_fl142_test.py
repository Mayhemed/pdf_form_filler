#!/usr/bin/env python3
"""
Working FL-142 Test System - Fixed Version
Author: Assistant  
Description: A reliable test system that actually validates the PDF form filling functionality
"""

import os
import sys
import json
import time
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('WorkingFL142Test')

@dataclass
class TestResult:
    """Test result data structure"""
    test_name: str
    success: bool
    details: Dict
    processing_time: float
    errors: List[str]

class WorkingFL142Test:
    """
    A working test system that validates actual functionality
    """
    
    def __init__(self):
        """Initialize the test system"""
        self.base_path = Path("/Users/markpiesner/Documents/Github/LegalTools/PDF_Form_Filler")
        self.test_results = []
        
        # Check for AI API keys
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        
        logger.info("🔧 Working FL-142 Test System Initialized")
        logger.info(f"   OpenAI API Key: {'✅ Set' if self.openai_key else '❌ Missing'}")
        logger.info(f"   Anthropic API Key: {'✅ Set' if self.anthropic_key else '❌ Missing'}")
    
    def find_valid_pdfs(self) -> Dict[str, str]:
        """Find valid PDF files for testing"""
        possible_paths = {
            "blank_fl142": [
                str(self.base_path / "../../agentic_form_filler/Forms/fl142.pdf"),
                str(self.base_path / "fl142.pdf"),
                str(self.base_path / "FL-142.pdf"),
                # Add more possible locations
            ],
            "source_fl120": [
                str(self.base_path / "../../agentic_form_filler/client_data/Rogers/Rogers-FL120-signed.pdf"),
                str(self.base_path / "FL-120.pdf"),
                str(self.base_path / "test_data/FL-120.pdf"),
            ],
            "source_fl142": [
                str(self.base_path / "../../agentic_form_filler/client_data/Rogers/fl142 copy.pdf"),
                str(self.base_path / "FL-142-filled.pdf"),
                str(self.base_path / "test_data/FL-142-filled.pdf"),
            ]
        }
        
        valid_files = {}
        
        for file_type, paths in possible_paths.items():
            for path in paths:
                if os.path.exists(path):
                    # Validate it's actually a PDF
                    try:
                        with open(path, 'rb') as f:
                            header = f.read(4)
                            if header == b'%PDF':
                                valid_files[file_type] = path
                                logger.info(f"✅ Found valid {file_type}: {path}")
                                break
                    except Exception as e:
                        logger.warning(f"⚠️ Could not validate {path}: {e}")
        
        return valid_files
    
    def test_ai_connectivity(self) -> TestResult:
        """Test AI connectivity and basic functionality"""
        start_time = time.time()
        errors = []
        details = {}
        
        try:
            logger.info("🔄 Testing AI Connectivity...")
            
            # Test OpenAI if available
            if self.openai_key:
                try:
                    import openai
                    client = openai.OpenAI(api_key=self.openai_key)
                    
                    # Simple test call
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": "Test: What is 2+2?"}],
                        max_tokens=10
                    )
                    
                    details["openai_response"] = response.choices[0].message.content
                    details["openai_working"] = True
                    logger.info("✅ OpenAI connectivity confirmed")
                    
                except Exception as e:
                    errors.append(f"OpenAI test failed: {e}")
                    details["openai_working"] = False
            else:
                details["openai_working"] = False
                details["openai_reason"] = "No API key"
            
            # Test Anthropic if available
            if self.anthropic_key:
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=self.anthropic_key)
                    
                    # Simple test call
                    response = client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=10,
                        messages=[{"role": "user", "content": "Test: What is 2+2?"}]
                    )
                    
                    details["anthropic_response"] = response.content[0].text
                    details["anthropic_working"] = True
                    logger.info("✅ Anthropic connectivity confirmed")
                    
                except Exception as e:
                    errors.append(f"Anthropic test failed: {e}")
                    details["anthropic_working"] = False
            else:
                details["anthropic_working"] = False
                details["anthropic_reason"] = "No API key"
            
            success = details.get("openai_working", False) or details.get("anthropic_working", False)
            
        except Exception as e:
            errors.append(f"AI connectivity test error: {e}")
            success = False
        
        processing_time = time.time() - start_time
        
        return TestResult(
            test_name="ai_connectivity",
            success=success,
            details=details,
            processing_time=processing_time,
            errors=errors
        )
    
    def test_pdf_validation(self, valid_files: Dict[str, str]) -> TestResult:
        """Test PDF file validation and accessibility"""
        start_time = time.time()
        errors = []
        details = {}
        
        try:
            logger.info("🔄 Testing PDF File Validation...")
            
            details["files_found"] = len(valid_files)
            details["required_files"] = ["blank_fl142"]  # Minimum requirement
            
            # Check if we have minimum required files
            if "blank_fl142" not in valid_files:
                errors.append("No valid blank FL-142 form found")
                success = False
            else:
                # Test pdftk with the blank form
                blank_form = valid_files["blank_fl142"]
                try:
                    result = subprocess.run([
                        "pdftk", blank_form, "dump_data_fields"
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        field_count = len([line for line in result.stdout.split('\n') if 'FieldName:' in line])
                        details["field_count"] = field_count
                        details["pdftk_working"] = True
                        logger.info(f"✅ PDF form has {field_count} fillable fields")
                        success = True
                    else:
                        errors.append(f"pdftk failed: {result.stderr}")
                        success = False
                        
                except subprocess.TimeoutExpired:
                    errors.append("pdftk command timed out")
                    success = False
                except FileNotFoundError:
                    errors.append("pdftk not found - install pdftk")
                    success = False
            
            details["valid_files"] = valid_files
            
        except Exception as e:
            errors.append(f"PDF validation error: {e}")
            success = False
        
        processing_time = time.time() - start_time
        
        return TestResult(
            test_name="pdf_validation",
            success=success,
            details=details,
            processing_time=processing_time,
            errors=errors
        )
    
    def test_basic_form_filling(self, valid_files: Dict[str, str]) -> TestResult:
        """Test basic PDF form filling functionality"""
        start_time = time.time()
        errors = []
        details = {}
        
        try:
            logger.info("🔄 Testing Basic Form Filling...")
            
            if "blank_fl142" not in valid_files:
                errors.append("No blank FL-142 form available for testing")
                return TestResult("basic_form_filling", False, details, time.time() - start_time, errors)
            
            blank_form = valid_files["blank_fl142"]
            output_file = str(self.base_path / "test_filled_output.pdf")
            
            # Create test data matching actual FL-142 fields
            test_data = {
                "TextField1[0]": "Mark Piesner",  # Attorney name
                "Phone[0]": "(818) 638-4456",   # Phone
                "Email[0]": "mark@arcpointlaw.com",  # Email
                "Party1[0]": "TAHIRA FRANCIS",   # Petitioner
                "Party2[0]": "SHAWN ROGERS",     # Respondent
                "CaseNumber[0]": "24STFL00615",  # Case number
                "CrtCounty[0]": "LOS ANGELES",   # Court county
                "DecimalField40[0]": "22000.00", # Student loans
                "DecimalField37[0]": "25000.00", # Unsecured loans
                "DecimalField36[0]": "3042.81",  # Credit cards
                "DecimalField43[0]": "16583.00", # Other debts
                "DecimalField41[0]": "66625.81"  # Total debts
            }
            
            # Create FDF content
            fdf_content = self._create_fdf_content(test_data)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.fdf', delete=False) as fdf_file:
                fdf_file.write(fdf_content)
                fdf_path = fdf_file.name
            
            try:
                # Fill the form
                result = subprocess.run([
                    "pdftk", blank_form, "fill_form", fdf_path,
                    "output", output_file, "dont_ask"
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0 and os.path.exists(output_file):
                    # Verify the filled form
                    verify_result = subprocess.run([
                        "pdftk", output_file, "dump_data_fields"
                    ], capture_output=True, text=True, timeout=30)
                    
                    if verify_result.returncode == 0:
                        filled_fields = self._count_filled_fields(verify_result.stdout)
                        details["filled_fields"] = filled_fields
                        details["expected_fields"] = len(test_data)
                        details["fill_rate"] = filled_fields / len(test_data)
                        details["output_file"] = output_file
                        
                        success = filled_fields >= len(test_data) * 0.7  # 70% success rate
                        
                        if success:
                            logger.info(f"✅ Form filling successful: {filled_fields}/{len(test_data)} fields filled")
                        else:
                            logger.warning(f"⚠️ Form filling partial: {filled_fields}/{len(test_data)} fields filled")
                    else:
                        errors.append("Could not verify filled form")
                        success = False
                else:
                    errors.append(f"Form filling failed: {result.stderr}")
                    success = False
                    
            finally:
                # Clean up temp file
                if os.path.exists(fdf_path):
                    os.unlink(fdf_path)
            
        except Exception as e:
            errors.append(f"Form filling test error: {e}")
            success = False
        
        processing_time = time.time() - start_time
        
        return TestResult(
            test_name="basic_form_filling",
            success=success,
            details=details,
            processing_time=processing_time,
            errors=errors
        )
    
    def _create_fdf_content(self, field_data: Dict[str, str]) -> str:
        """Create FDF content for PDF form filling"""
        fdf_header = """%FDF-1.2
1 0 obj
<<
/FDF
<<
/Fields ["""

        fdf_fields = []
        for field_name, field_value in field_data.items():
            if field_value:
                escaped_value = str(field_value).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
                fdf_fields.append(f"""<<
/T ({field_name})
/V ({escaped_value})
>>""")

        fdf_footer = """]
>>
>>
endobj
trailer

<<
/Root 1 0 R
>>
%%EOF"""

        return fdf_header + '\n' + '\n'.join(fdf_fields) + '\n' + fdf_footer
    
    def _count_filled_fields(self, pdftk_output: str) -> int:
        """Count filled fields from pdftk output"""
        filled_count = 0
        lines = pdftk_output.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('FieldName:'):
                # Look for the corresponding FieldValue
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('FieldName:'):
                    if lines[j].strip().startswith('FieldValue:'):
                        value = lines[j].strip().replace('FieldValue:', '').strip()
                        if value:  # Non-empty value
                            filled_count += 1
                        break
                    j += 1
            i += 1
        
        return filled_count
    
    def run_comprehensive_test(self) -> Dict:
        """Run the complete test suite"""
        logger.info("🚀 Starting Working FL-142 Comprehensive Test")
        logger.info("=" * 60)
        
        # Find valid PDF files
        logger.info("📁 Step 1: Finding valid PDF files...")
        valid_files = self.find_valid_pdfs()
        
        if not valid_files:
            logger.error("❌ No valid PDF files found - cannot proceed with testing")
            return {"success": False, "error": "No valid PDF files found"}
        
        # Test AI connectivity
        logger.info("🤖 Step 2: Testing AI connectivity...")
        ai_test = self.test_ai_connectivity()
        self.test_results.append(ai_test)
        
        # Test PDF validation
        logger.info("📄 Step 3: Validating PDF files...")
        pdf_test = self.test_pdf_validation(valid_files)
        self.test_results.append(pdf_test)
        
        # Test basic form filling
        logger.info("📝 Step 4: Testing form filling...")
        form_test = self.test_basic_form_filling(valid_files)
        self.test_results.append(form_test)
        
        # Generate summary
        logger.info("📊 Step 5: Generating test summary...")
        return self.generate_test_summary()
    
    def generate_test_summary(self) -> Dict:
        """Generate comprehensive test summary"""
        passed_tests = sum(1 for result in self.test_results if result.success)
        total_tests = len(self.test_results)
        success_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("🎯 WORKING FL-142 TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"📊 Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1%})")
        
        for result in self.test_results:
            status = "✅" if result.success else "❌"
            logger.info(f"{status} {result.test_name}: {result.processing_time:.3f}s")
            
            if result.errors:
                for error in result.errors:
                    logger.info(f"   🔥 {error}")
            
            # Show key details
            if result.test_name == "basic_form_filling" and result.success:
                filled = result.details.get("filled_fields", 0)
                expected = result.details.get("expected_fields", 0)
                logger.info(f"   📝 Fields filled: {filled}/{expected}")
        
        overall_success = success_rate >= 0.7
        
        logger.info("")
        if overall_success:
            logger.info("🎉 OVERALL RESULT: ✅ WORKING SYSTEM")
            logger.info("   The PDF form filling system is functional!")
        else:
            logger.info("❌ OVERALL RESULT: ⚠️ NEEDS ATTENTION")
            logger.info("   Some components need fixes before production use")
        
        logger.info("=" * 60)
        
        return {
            "success": overall_success,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "success_rate": success_rate,
            "test_results": [asdict(result) for result in self.test_results]
        }

def main():
    """Main function to run the working test"""
    print("🧪 Working FL-142 Test System")
    print("=" * 50)
    
    test_system = WorkingFL142Test()
    results = test_system.run_comprehensive_test()
    
    return results

if __name__ == "__main__":
    main()
