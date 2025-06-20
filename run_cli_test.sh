#!/bin/bash
# Run CLI test script to debug the hanging issue

echo "🔧 Testing CLI Multi-Threaded Processing"
echo "This will show real-time output so you can see where it hangs"
echo ""

# Navigate to project directory
cd /Users/markpiesner/Documents/GitHub/LegalTools/PDF_Form_Filler

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source myenv/bin/activate

# Check dependencies
echo "🔍 Checking dependencies..."
python3 -c "
try:
    import PyPDF2
    print('✅ PyPDF2 available')
    import concurrent.futures
    print('✅ concurrent.futures available')
    import threading
    print('✅ threading available')
except Exception as e:
    print(f'❌ Missing dependency: {e}')
"

echo ""
echo "🚀 Running CLI test..."
echo "Watch for where it hangs - you can Ctrl+C to stop"
echo ""

# Run the CLI test
python3 test_cli_multithreaded.py
