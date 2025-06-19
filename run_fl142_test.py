#!/usr/bin/env python3
"""
FL-142 Comprehensive Test Runner
Executes the comprehensive test suite for FL-142 form filling
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def main():
    """Run the FL-142 comprehensive test"""
    print("🚀 Starting FL-142 Comprehensive Test Suite")
    print("=" * 60)
    
    try:
        # Import the test system
        from fl142_test_system import FL142TestSystem
        
        # Initialize and run test
        test_system = FL142TestSystem()
        results = test_system.run_comprehensive_test()
        
        print("\n" + "=" * 60)
        print("📋 TEST EXECUTION COMPLETED")
        
        if results.get('overall_success', False):
            print("✅ ALL TESTS PASSED!")
            print("\n🎯 Key Achievements:")
            print("   • Successfully extracted attorney data from FL-120")
            print("   • Successfully extracted financial data from FL-142")
            print("   • Correctly mapped data to target form fields")
            print("   • Form filling pipeline is functional")
            print("\n🚀 System is ready for production use!")
        else:
            print("⚠️ SOME TESTS NEED ATTENTION")
            print("\n🔧 Next Steps:")
            print("   • Review failed test components")
            print("   • Check API key configuration")
            print("   • Verify PDF processing dependencies")
            
        return results
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Please ensure all dependencies are installed")
        return None
    except Exception as e:
        print(f"❌ Test Execution Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()
