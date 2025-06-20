#!/bin/bash
# Run AI-enabled CLI test script

echo "🤖 Testing AI Multi-Threaded Processing"
echo "This will test with real AI to get proper extraction results"
echo ""

# Navigate to project directory
cd /Users/markpiesner/Documents/GitHub/LegalTools/PDF_Form_Filler

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source myenv/bin/activate

# Check for API keys
if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️ No API keys found in environment"
    echo "Please set one of these environment variables:"
    echo "   export ANTHROPIC_API_KEY='your_anthropic_key'"
    echo "   export OPENAI_API_KEY='your_openai_key'"
    echo ""
    echo "You can also enter the API key manually when prompted"
else
    echo "✅ API key found"
fi

# Check AI dependencies
echo "🔍 Checking AI dependencies..."
python3 -c "
try:
    import anthropic
    print('✅ Anthropic library available')
except ImportError:
    print('⚠️ Anthropic library not available - install with: pip install anthropic')

try:
    import openai
    print('✅ OpenAI library available')
except ImportError:
    print('⚠️ OpenAI library not available - install with: pip install openai')
"

echo ""
echo "🤖 Running AI CLI test..."
echo "This will process your FL-120 and FL-142 documents with specialized AI prompts"
echo "Watch for real AI extraction results!"
echo ""

# Run the AI test
python3 test_ai_multithreaded.py
