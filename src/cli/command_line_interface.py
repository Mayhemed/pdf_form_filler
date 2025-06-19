#!/usr/bin/env python3
"""
Command Line Interface for Universal PDF Form Filler
Provides both simple and advanced CLI operations
"""

import argparse
import logging
import os
import sys
import json
from pathlib import Path
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.unified_pipeline import UnifiedPipeline, ProcessingStage

def setup_logging(verbose: bool = False, log_file: Optional[str] = None):
    """Set up logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Set up file handler if specified
    handlers = [console_handler]
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=handlers,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def validate_inputs(target_form: str, sources: List[str], output_path: str) -> bool:
    """Validate input files and paths"""
    # Check target form exists
    if not os.path.exists(target_form):
        print(f"❌ Error: Target form not found: {target_form}")
        return False
    
    if not target_form.lower().endswith('.pdf'):
        print(f"❌ Error: Target form must be a PDF file: {target_form}")
        return False
    
    # Check source documents exist
    for source in sources:
        if not os.path.exists(source):
            print(f"❌ Error: Source document not found: {source}")
            return False
    
    # Check output directory is writable
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            print(f"❌ Error: Cannot create output directory {output_dir}: {e}")
            return False
    
    return True

def print_processing_status(pipeline: UnifiedPipeline):
    """Print real-time processing status"""
    if not pipeline.processing_history:
        return
    
    latest = pipeline.processing_history[-1]
    stage_emoji = {
        ProcessingStage.AI_EXTRACTION: "🤖",
        ProcessingStage.FIELD_MAPPING: "🗺️",
        ProcessingStage.DATA_VALIDATION: "✅",
        ProcessingStage.PDF_FILLING: "📄",
        ProcessingStage.COMPLETION: "🎉"
    }
    
    emoji = stage_emoji.get(latest.stage, "⚙️")
    status = "✅" if latest.success else "❌"
    
    print(f"{emoji} {latest.stage.value.replace('_', ' ').title()}: {status}")
    if latest.data:
        if 'fields_filled' in latest.data:
            print(f"   📊 Fields processed: {latest.data.get('fields_filled', 0)}")
        if latest.processing_time > 0:
            print(f"   ⏱️ Time: {latest.processing_time:.2f}s")

def cmd_fill_form(args):
    """Fill a single PDF form with source documents"""
    print("🚀 Universal PDF Form Filler")
    print("=" * 50)
    
    # Validate inputs
    if not validate_inputs(args.target_form, args.sources, args.output_path):
        return 1
    
    # Set up logging
    setup_logging(args.verbose, args.log_file)
    
    # Print processing info
    print(f"📋 Target Form: {os.path.basename(args.target_form)}")
    print(f"📁 Source Documents: {len(args.sources)} files")
    for i, source in enumerate(args.sources, 1):
        print(f"   {i}. {os.path.basename(source)}")
    print(f"💾 Output: {args.output_path}")
    print()
    
    try:
        # Initialize pipeline
        print("🔧 Initializing pipeline...")
        pipeline = UnifiedPipeline(config_path=args.config)
        
        # Process form
        print("⚙️ Processing form...")
        result = pipeline.process_form(
            target_form_path=args.target_form,
            source_documents=args.sources,
            output_path=args.output_path
        )
        
        # Print results
        print()
        print("📊 Processing Results:")
        print("=" * 30)
        
        if result.success:
            print("✅ Form processing completed successfully!")
            print(f"📄 Output saved to: {result.data.get('output_path')}")
            print(f"📊 Fields filled: {result.data.get('fields_filled', 0)}")
            print(f"⏱️ Total time: {result.processing_time:.2f}s")
            
            # Print detailed report if verbose
            if args.verbose:
                print("\n📈 Detailed Processing Report:")
                report = pipeline.get_processing_report()
                for stage_detail in report['stage_details']:
                    stage_name = stage_detail['stage'].replace('_', ' ').title()
                    status = "✅" if stage_detail['success'] else "❌"
                    print(f"  {status} {stage_name}: {stage_detail['processing_time']:.2f}s")
                    if stage_detail['errors']:
                        for error in stage_detail['errors']:
                            print(f"    ⚠️ {error}")
            
            return 0
        else:
            print("❌ Form processing failed!")
            for error in result.errors:
                print(f"   💥 {error}")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️ Processing interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

def cmd_batch_process(args):
    """Process multiple forms in batch"""
    print("🔄 Batch PDF Form Processing")
    print("=" * 50)
    
    # Read batch configuration
    if not os.path.exists(args.batch_file):
        print(f"❌ Error: Batch file not found: {args.batch_file}")
        return 1
    
    try:
        with open(args.batch_file, 'r') as f:
            batch_config = json.load(f)
    except Exception as e:
        print(f"❌ Error reading batch file: {e}")
        return 1
    
    # Process each job
    jobs = batch_config.get('jobs', [])
    if not jobs:
        print("❌ No jobs found in batch file")
        return 1
    
    print(f"📦 Found {len(jobs)} jobs to process")
    
    # Set up logging
    setup_logging(args.verbose, args.log_file)
    
    # Initialize pipeline once
    pipeline = UnifiedPipeline(config_path=args.config)
    
    success_count = 0
    failed_jobs = []
    
    for i, job in enumerate(jobs, 1):
        print(f"\n🔄 Processing Job {i}/{len(jobs)}")
        print(f"   📋 Form: {os.path.basename(job['target_form'])}")
        print(f"   📁 Sources: {len(job['sources'])} files")
        
        try:
            # Validate job inputs
            if not validate_inputs(job['target_form'], job['sources'], job['output_path']):
                failed_jobs.append(f"Job {i}: Input validation failed")
                continue
            
            # Process the job
            result = pipeline.process_form(
                target_form_path=job['target_form'],
                source_documents=job['sources'],
                output_path=job['output_path']
            )
            
            if result.success:
                print(f"   ✅ Success: {result.data.get('fields_filled', 0)} fields filled")
                success_count += 1
            else:
                error_msg = f"Job {i}: " + "; ".join(result.errors)
                failed_jobs.append(error_msg)
                print(f"   ❌ Failed: {'; '.join(result.errors)}")
                
        except Exception as e:
            error_msg = f"Job {i}: Unexpected error: {e}"
            failed_jobs.append(error_msg)
            print(f"   💥 Error: {e}")
    
    # Print batch summary
    print(f"\n📊 Batch Processing Complete")
    print("=" * 40)
    print(f"✅ Successful: {success_count}/{len(jobs)}")
    print(f"❌ Failed: {len(failed_jobs)}/{len(jobs)}")
    
    if failed_jobs:
        print(f"\n💥 Failed Jobs:")
        for error in failed_jobs:
            print(f"   - {error}")
    
    return 0 if success_count == len(jobs) else 1

def cmd_analyze_form(args):
    """Analyze a PDF form to understand its structure"""
    print("🔍 PDF Form Analysis")
    print("=" * 30)
    
    if not os.path.exists(args.form_path):
        print(f"❌ Error: Form not found: {args.form_path}")
        return 1
    
    try:
        import subprocess
        
        # Extract form fields using pdftk
        result = subprocess.run([
            'pdftk', args.form_path, 'dump_data_fields'
        ], capture_output=True, text=True, check=True)
        
        # Parse fields
        fields = []
        current_field = {}
        
        for line in result.stdout.strip().split('\n'):
            if line.startswith('---'):
                if current_field:
                    fields.append(current_field)
                    current_field = {}
            elif ':' in line:
                key, value = line.split(':', 1)
                current_field[key.strip()] = value.strip()
        
        if current_field:
            fields.append(current_field)
        
        # Print analysis
        print(f"📋 Form: {os.path.basename(args.form_path)}")
        print(f"📊 Total Fields: {len(fields)}")
        print()
        
        # Group fields by type
        field_types = {}
        for field in fields:
            field_type = field.get('FieldType', 'Unknown')
            field_types[field_type] = field_types.get(field_type, 0) + 1
        
        print("📈 Field Types:")
        for field_type, count in sorted(field_types.items()):
            print(f"   {field_type}: {count}")
        
        # Show sample fields if verbose
        if args.verbose:
            print(f"\n📝 Sample Fields:")
            for i, field in enumerate(fields[:10]):
                field_name = field.get('FieldName', 'Unknown')
                field_type = field.get('FieldType', 'Unknown')
                field_alt = field.get('FieldNameAlt', '')
                print(f"   {i+1}. {field_name}")
                print(f"      Type: {field_type}")
                if field_alt:
                    print(f"      Description: {field_alt}")
                print()
        
        # Save detailed analysis if requested
        if args.output:
            analysis_data = {
                "form_path": args.form_path,
                "total_fields": len(fields),
                "field_types": field_types,
                "fields": fields
            }
            
            with open(args.output, 'w') as f:
                json.dump(analysis_data, f, indent=2)
            print(f"💾 Detailed analysis saved to: {args.output}")
        
        return 0
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error analyzing form: {e}")
        print("💡 Make sure pdftk is installed and the PDF is a fillable form")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

def cmd_test_ai(args):
    """Test AI provider connectivity"""
    print("🧪 AI Provider Testing")
    print("=" * 30)
    
    # Set up logging
    setup_logging(args.verbose)
    
    try:
        # Test pipeline initialization
        print("🔧 Initializing pipeline...")
        pipeline = UnifiedPipeline(config_path=args.config)
        
        # Test AI extraction with sample data
        print("🤖 Testing AI extraction...")
        sample_text = "Test extraction with sample data: John Doe, Case 24STFL00615, $1000.00"
        
        try:
            extracted_data, confidence_scores = pipeline.ai_extractor.extract_from_documents([])
            print("✅ AI extraction component initialized successfully")
            
            # Test specific providers
            ai_config = pipeline.config.get("ai_providers", {})
            
            if ai_config.get("openai", {}).get("api_key"):
                print("🔑 OpenAI API key found")
                try:
                    from llm_client import test_openai_connection
                    if test_openai_connection():
                        print("✅ OpenAI connection successful")
                    else:
                        print("❌ OpenAI connection failed")
                except Exception as e:
                    print(f"❌ OpenAI test error: {e}")
            else:
                print("⚠️ OpenAI API key not found")
            
            if ai_config.get("anthropic", {}).get("api_key"):
                print("🔑 Anthropic API key found")
                try:
                    from llm_client import test_claude_connection
                    if test_claude_connection():
                        print("✅ Anthropic connection successful")
                    else:
                        print("❌ Anthropic connection failed")
                except Exception as e:
                    print(f"❌ Anthropic test error: {e}")
            else:
                print("⚠️ Anthropic API key not found")
            
        except Exception as e:
            print(f"❌ AI extraction test failed: {e}")
        
        print("\n💡 Tips:")
        print("   - Set OPENAI_API_KEY environment variable for OpenAI")
        print("   - Set ANTHROPIC_API_KEY environment variable for Claude")
        print("   - Check your API key permissions and quotas")
        
        return 0
        
    except Exception as e:
        print(f"❌ Pipeline initialization failed: {e}")
        return 1

def create_parser():
    """Create the argument parser"""
    parser = argparse.ArgumentParser(
        description="Universal PDF Form Filler - AI-powered form filling for any PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fill a single form
  %(prog)s fill-form target.pdf output.pdf --sources source1.pdf source2.pdf
  
  # Analyze form structure
  %(prog)s analyze target.pdf --verbose
  
  # Test AI connectivity
  %(prog)s test-ai --verbose
  
  # Batch processing
  %(prog)s batch jobs.json --verbose
        """
    )
    
    # Global options
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--log-file", help="Log file path")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Fill form command
    fill_parser = subparsers.add_parser("fill-form", help="Fill a PDF form with source documents")
    fill_parser.add_argument("target_form", help="Path to blank PDF form to fill")
    fill_parser.add_argument("output_path", help="Path for filled PDF output")
    fill_parser.add_argument("--sources", nargs="+", required=True, help="Source documents containing data")
    fill_parser.set_defaults(func=cmd_fill_form)
    
    # Batch processing command
    batch_parser = subparsers.add_parser("batch", help="Process multiple forms in batch")
    batch_parser.add_argument("batch_file", help="JSON file with batch job configuration")
    batch_parser.set_defaults(func=cmd_batch_process)
    
    # Analyze form command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze PDF form structure")
    analyze_parser.add_argument("form_path", help="Path to PDF form to analyze")
    analyze_parser.add_argument("--output", "-o", help="Save analysis to JSON file")
    analyze_parser.set_defaults(func=cmd_analyze_form)
    
    # Test AI command
    test_parser = subparsers.add_parser("test-ai", help="Test AI provider connectivity")
    test_parser.set_defaults(func=cmd_test_ai)
    
    return parser

def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n⏹️ Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        if getattr(args, 'verbose', False):
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
