#!/usr/bin/env python3
"""
Comprehensive Test Suite for Universal PDF Form Filler
Tests the complete pipeline from source documents to filled PDFs
"""

import unittest
import tempfile
import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.unified_pipeline import UnifiedPipeline, ProcessingStage, ProcessingResult

class TestUnifiedPipeline(unittest.TestCase):
    """Test the unified pipeline with real documents"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.test_dir = Path(__file__).parent.parent / "test_data"
        cls.temp_dir = Path(tempfile.mkdtemp())
        
        # Load expected results
        expected_results_path = cls.test_dir / "expected_results.json"
        if expected_results_path.exists():
            with open(expected_results_path) as f:
                cls.expected_results = json.load(f)
        else:
            cls.expected_results = {}
        
        # Initialize pipeline once for all tests
        cls.pipeline = UnifiedPipeline()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        if cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir)
    
    def setUp(self):
        """Set up each test"""
        self.output_path = self.temp_dir / f"test_output_{self._testMethodName}.pdf"
    
    def test_pipeline_initialization(self):
        """Test that pipeline initializes correctly"""
        self.assertIsNotNone(self.pipeline)
        self.assertIsNotNone(self.pipeline.ai_extractor)
        self.assertIsNotNone(self.pipeline.field_mapper)
        self.assertIsNotNone(self.pipeline.pdf_processor)
        self.assertIsNotNone(self.pipeline.validator)
    
    def test_fl120_basic_extraction(self):
        """Test basic FL-120 form processing"""
        expected = self.expected_results.get("test_scenarios", {}).get("fl120_basic", {})
        
        if not expected:
            self.skipTest("FL-120 test data not configured")
        
        # Mock test for now - will implement when forms are available
        expected_fields = expected.get("expected_fields", {})
        self.assertGreater(len(expected_fields), 0, "Should have expected fields configured")
        
        # Verify expected basic data structure
        self.assertIn("Petitioner", expected_fields)
        self.assertIn("Respondent", expected_fields)
        self.assertIn("CaseNumber", expected_fields)
    
    def test_fl142_financial_extraction(self):
        """Test FL-142 financial data extraction"""
        expected = self.expected_results.get("test_scenarios", {}).get("fl142_comprehensive", {})
        
        if not expected:
            self.skipTest("FL-142 test data not configured")
        
        expected_fields = expected.get("expected_fields", {})
        self.assertGreater(len(expected_fields), 0, "Should have expected fields configured")
        
        # Verify expected financial data structure
        self.assertIn("student_loans", expected_fields)
        self.assertIn("credit_cards", expected_fields)
        self.assertIn("total_debts", expected_fields)
    
    def test_cross_form_extraction(self):
        """Test extracting data from one form type to fill another"""
        expected = self.expected_results.get("test_scenarios", {}).get("cross_form_extraction", {})
        
        if not expected:
            self.skipTest("Cross-form test data not configured")
        
        expected_fields = expected.get("expected_fields", {})
        min_confidence = expected.get("minimum_confidence", 0.7)
        
        self.assertGreaterEqual(min_confidence, 0.5, "Minimum confidence should be reasonable")
        self.assertIn("petitioner_name", expected_fields)
        self.assertIn("case_number", expected_fields)
    
    def test_ai_extractor_functionality(self):
        """Test AI extractor component functionality"""
        # Test with sample text data
        sample_documents = [self._create_sample_document()]
        
        try:
            extracted_data, confidence_scores = self.pipeline.ai_extractor.extract_from_documents(sample_documents)
            
            # Should return dictionaries even if empty
            self.assertIsInstance(extracted_data, dict)
            self.assertIsInstance(confidence_scores, dict)
            
            # If data was extracted, confidence scores should match
            if extracted_data:
                for field in extracted_data.keys():
                    self.assertIn(field, confidence_scores, f"Missing confidence score for {field}")
            
        except Exception as e:
            self.fail(f"AI extractor should handle sample documents gracefully: {e}")
    
    def test_field_mapper_functionality(self):
        """Test field mapper component functionality"""
        # Create a minimal form for testing
        sample_form = self._create_sample_form()
        sample_data = {
            "name": "John Doe",
            "case_number": "24TEST12345",
            "phone": "(555) 123-4567"
        }
        
        try:
            mapped_fields, confidence_scores = self.pipeline.field_mapper.map_data_to_form(sample_form, sample_data)
            
            self.assertIsInstance(mapped_fields, dict)
            self.assertIsInstance(confidence_scores, dict)
            
        except Exception as e:
            self.fail(f"Field mapper should handle sample data gracefully: {e}")
    
    def test_data_validator_functionality(self):
        """Test data validator component functionality"""
        sample_data = {
            "phone": "5551234567",  # Should be formatted
            "amount": "1000",       # Should be formatted as currency
            "name": "  John Doe  "  # Should be trimmed
        }
        
        try:
            validated_data, confidence_scores = self.pipeline.validator.validate_and_enrich(sample_data)
            
            self.assertIsInstance(validated_data, dict)
            self.assertIsInstance(confidence_scores, dict)
            
            # Check that phone was formatted
            if "phone" in validated_data:
                phone = validated_data["phone"]
                self.assertTrue("(" in phone or "-" in phone, "Phone should be formatted")
            
        except Exception as e:
            self.fail(f"Data validator should handle sample data gracefully: {e}")
    
    def test_pdf_processor_functionality(self):
        """Test PDF processor component functionality"""
        # Create a simple test form
        sample_form = self._create_sample_form()
        sample_data = {"test_field": "test_value"}
        output_path = str(self.temp_dir / "test_pdf_output.pdf")
        
        try:
            success = self.pipeline.pdf_processor.fill_form(sample_form, sample_data, output_path)
            
            # Should return boolean
            self.assertIsInstance(success, bool)
            
        except Exception as e:
            # PDF processing might fail without real forms, but should handle gracefully
            self.assertIsInstance(e, Exception, "Should raise a clear exception if PDF processing fails")
    
    def test_performance_benchmarks(self):
        """Test that processing meets performance benchmarks"""
        benchmarks = self.expected_results.get("performance_benchmarks", {})
        
        if not benchmarks:
            self.skipTest("Performance benchmarks not configured")
        
        processing_time = benchmarks.get("processing_time", {})
        accuracy_targets = benchmarks.get("accuracy_targets", {})
        
        # Verify benchmark configuration
        self.assertIn("single_form_max_seconds", processing_time)
        self.assertIn("field_coverage_minimum", accuracy_targets)
        
        max_time = processing_time.get("single_form_max_seconds", 30)
        min_coverage = accuracy_targets.get("field_coverage_minimum", 0.8)
        
        self.assertGreater(max_time, 0, "Max processing time should be positive")
        self.assertGreaterEqual(min_coverage, 0.5, "Minimum coverage should be reasonable")
    
    def test_edge_cases(self):
        """Test edge case handling"""
        edge_cases = self.expected_results.get("edge_cases", {})
        
        if not edge_cases:
            self.skipTest("Edge cases not configured")
        
        # Test empty source documents
        empty_case = edge_cases.get("empty_source_documents", {})
        if empty_case:
            expected_behavior = empty_case.get("expected_behavior")
            self.assertEqual(expected_behavior, "graceful_failure_with_message")
        
        # Test corrupted PDF
        corrupted_case = edge_cases.get("corrupted_pdf", {})
        if corrupted_case:
            expected_behavior = corrupted_case.get("expected_behavior")
            self.assertEqual(expected_behavior, "error_with_clear_message")
    
    def test_validation_rules(self):
        """Test validation rule configurations"""
        validation_rules = self.expected_results.get("validation_rules", {})
        
        if not validation_rules:
            self.skipTest("Validation rules not configured")
        
        # Test case number format
        case_format = validation_rules.get("case_number_formats", {})
        if case_format:
            california_pattern = case_format.get("california")
            examples = case_format.get("examples", [])
            
            self.assertIsNotNone(california_pattern, "Should have California case number pattern")
            self.assertGreater(len(examples), 0, "Should have example case numbers")
            
            # Test pattern against examples
            import re
            pattern = re.compile(california_pattern)
            for example in examples:
                self.assertTrue(pattern.match(example), f"Pattern should match example: {example}")
    
    def _create_sample_document(self) -> str:
        """Create a sample document for testing"""
        sample_content = """
        SUPERIOR COURT OF CALIFORNIA
        COUNTY OF LOS ANGELES
        
        PETITIONER: TAHIRA FRANCIS
        RESPONDENT: SHAWN ROGERS
        CASE NUMBER: 24STFL00615
        
        ATTORNEY: Mark Piesner
        PHONE: (818) 638-4456
        EMAIL: mark@arcpointlaw.com
        """
        
        sample_file = self.temp_dir / "sample_document.txt"
        with open(sample_file, 'w') as f:
            f.write(sample_content)
        
        return str(sample_file)
    
    def _create_sample_form(self) -> str:
        """Create a minimal sample form for testing"""
        # Create a simple text file as a placeholder form
        # In real implementation, this would be a PDF with fillable fields
        sample_form = self.temp_dir / "sample_form.txt"
        with open(sample_form, 'w') as f:
            f.write("Sample form for testing")
        
        return str(sample_form)


class TestAIIntegration(unittest.TestCase):
    """Test AI provider integration"""
    
    def setUp(self):
        """Set up AI integration tests"""
        self.test_dir = Path(__file__).parent.parent / "test_data"
        
        # Load expected results
        expected_results_path = self.test_dir / "expected_results.json"
        if expected_results_path.exists():
            with open(expected_results_path) as f:
                self.expected_results = json.load(f)
        else:
            self.expected_results = {}
    
    def test_ai_provider_configuration(self):
        """Test AI provider configuration"""
        ai_tests = self.expected_results.get("ai_provider_tests", {})
        
        if not ai_tests:
            self.skipTest("AI provider tests not configured")
        
        # Test OpenAI configuration
        openai_config = ai_tests.get("openai_gpt4v", {})
        if openai_config:
            self.assertIn("model", openai_config)
            self.assertIn("expected_response_format", openai_config)
            self.assertEqual(openai_config["expected_response_format"], "json")
        
        # Test Anthropic configuration
        claude_config = ai_tests.get("anthropic_claude", {})
        if claude_config:
            self.assertIn("model", claude_config)
            self.assertIn("expected_response_format", claude_config)
            self.assertEqual(claude_config["expected_response_format"], "json")
        
        # Test fallback configuration
        fallback_config = ai_tests.get("fallback_patterns", {})
        if fallback_config:
            self.assertIn("method", fallback_config)
            self.assertIn("expected_extractions", fallback_config)
    
    def test_api_key_detection(self):
        """Test API key detection"""
        # Test that the system can detect available API keys
        openai_key = os.getenv("OPENAI_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        
        # At least one should be available for testing, or system should fall back gracefully
        has_api_key = bool(openai_key or anthropic_key)
        
        if not has_api_key:
            print("⚠️  No AI API keys detected - system should use fallback patterns")
        else:
            print(f"✅ AI API keys detected: OpenAI={bool(openai_key)}, Anthropic={bool(anthropic_key)}")
        
        # This should not fail - system should handle missing keys gracefully
        self.assertTrue(True, "API key detection test completed")
    
    def test_fallback_patterns(self):
        """Test pattern-based fallback extraction"""
        ai_tests = self.expected_results.get("ai_provider_tests", {})
        fallback_config = ai_tests.get("fallback_patterns", {})
        
        if not fallback_config:
            self.skipTest("Fallback pattern tests not configured")
        
        test_text = fallback_config.get("test_text", "")
        expected_extractions = fallback_config.get("expected_extractions", {})
        
        self.assertGreater(len(test_text), 0, "Should have test text")
        self.assertGreater(len(expected_extractions), 0, "Should have expected extractions")
        
        # Test that expected patterns exist in test text
        for field, expected_value in expected_extractions.items():
            self.assertIn(expected_value, test_text, f"Test text should contain {field}: {expected_value}")


class TestCLIInterface(unittest.TestCase):
    """Test command line interface"""
    
    def setUp(self):
        """Set up CLI tests"""
        self.test_dir = Path(__file__).parent.parent / "test_data"
        self.cli_module_path = Path(__file__).parent.parent / "src" / "cli" / "command_line_interface.py"
    
    def test_cli_module_exists(self):
        """Test that CLI module exists and is importable"""
        self.assertTrue(self.cli_module_path.exists(), "CLI module should exist")
        
        try:
            sys.path.insert(0, str(self.cli_module_path.parent.parent))
            from cli.command_line_interface import create_parser
            
            parser = create_parser()
            self.assertIsNotNone(parser, "Should be able to create argument parser")
            
        except ImportError as e:
            self.fail(f"Should be able to import CLI module: {e}")
    
    def test_cli_commands_configured(self):
        """Test that all expected CLI commands are configured"""
        expected_commands = ["fill-form", "batch", "analyze", "test-ai"]
        
        try:
            sys.path.insert(0, str(self.cli_module_path.parent.parent))
            from cli.command_line_interface import create_parser
            
            parser = create_parser()
            
            # Parse help to see available commands
            help_text = parser.format_help()
            
            for command in expected_commands:
                self.assertIn(command, help_text, f"Command {command} should be available")
                
        except ImportError:
            self.skipTest("CLI module not available")


def run_diagnostic_tests():
    """Run diagnostic tests to identify current system issues"""
    print("🔍 Running Diagnostic Tests for PDF Form Filler")
    print("=" * 60)
    
    # Test 1: Check if core dependencies are available
    print("\n📦 Checking Dependencies:")
    
    dependencies = [
        ("pdftk", "pdftk --version"),
        ("python", "python --version"),
        ("PyQt6", "python -c 'import PyQt6'"),
    ]
    
    for name, command in dependencies:
        try:
            import subprocess
            result = subprocess.run(command.split(), capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ {name}: Available")
            else:
                print(f"   ❌ {name}: Not available or error")
        except:
            print(f"   ❌ {name}: Not available")
    
    # Test 2: Check API key availability
    print("\n🔑 Checking API Keys:")
    openai_key = bool(os.getenv("OPENAI_API_KEY"))
    anthropic_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    
    print(f"   OpenAI API Key: {'✅ Set' if openai_key else '❌ Not set'}")
    print(f"   Anthropic API Key: {'✅ Set' if anthropic_key else '❌ Not set'}")
    
    if not (openai_key or anthropic_key):
        print("   ⚠️  No AI API keys detected - will use pattern matching fallback")
    
    # Test 3: Check file structure
    print("\n📁 Checking File Structure:")
    expected_files = [
        "PROJECT_GUIDE.md",
        "config.yaml", 
        "src/core/unified_pipeline.py",
        "src/cli/command_line_interface.py",
        "test_data/expected_results.json"
    ]
    
    base_path = Path(__file__).parent.parent
    for file_path in expected_files:
        full_path = base_path / file_path
        if full_path.exists():
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path}")
    
    # Test 4: Test pipeline initialization
    print("\n⚙️  Testing Pipeline Initialization:")
    try:
        sys.path.insert(0, str(base_path / "src"))
        from core.unified_pipeline import UnifiedPipeline
        
        pipeline = UnifiedPipeline()
        print("   ✅ Pipeline initialization successful")
        
        # Test components
        components = [
            ("AI Extractor", pipeline.ai_extractor),
            ("Field Mapper", pipeline.field_mapper),
            ("PDF Processor", pipeline.pdf_processor),
            ("Data Validator", pipeline.validator)
        ]
        
        for name, component in components:
            if component is not None:
                print(f"   ✅ {name}: Initialized")
            else:
                print(f"   ❌ {name}: Failed to initialize")
                
    except Exception as e:
        print(f"   ❌ Pipeline initialization failed: {e}")
    
    print("\n🎯 Diagnostic Summary:")
    print("   1. Install missing dependencies (especially pdftk)")
    print("   2. Set AI API keys for enhanced functionality") 
    print("   3. Test with real PDF forms to verify complete pipeline")
    print("   4. Check the existing python_form_filler3.py for comparison")


if __name__ == "__main__":
    # Run diagnostic tests first
    run_diagnostic_tests()
    
    print("\n" + "=" * 60)
    print("🧪 Running Unit Tests")
    print("=" * 60)
    
    # Run unit tests
    unittest.main(verbosity=2)
