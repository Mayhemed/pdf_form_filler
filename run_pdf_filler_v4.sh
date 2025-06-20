#!/bin/bash
# Launch script for PDF Form Filler v4 Multi-Threaded

echo "🚀 Starting PDF Form Filler v4 - Multi-Threaded Processing"
echo "=" * 60

# Check if virtual environment exists
if [ ! -d "myenv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Creating virtual environment..."
    python3 -m venv myenv
    
    echo "Installing dependencies..."
    source myenv/bin/activate
    pip install PyQt6 PyPDF2 pdfplumber openai anthropic
else
    echo "✅ Virtual environment found"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source myenv/bin/activate

# Check if pdf_form_filler2.py exists
if [ ! -f "pdf_form_filler2.py" ]; then
    echo "❌ pdf_form_filler2.py not found!"
    echo "Using fallback: pdf_form_filler1.py"
    python pdf_form_filler1.py
    exit 1
fi

# Run syntax check
echo "🔍 Checking syntax..."
python3 -m py_compile pdf_form_filler2.py
if [ $? -ne 0 ]; then
    echo "❌ Syntax error in pdf_form_filler2.py"
    echo "Using fallback: pdf_form_filler1.py"
    python pdf_form_filler1.py
    exit 1
fi

echo "✅ Syntax check passed"

# Check for API keys
if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️ No API keys found in environment"
    echo "   Set ANTHROPIC_API_KEY or OPENAI_API_KEY for best results"
    echo "   You can also enter API key in the application"
else
    echo "✅ API key found"
fi

# Launch application
echo "🚀 Launching PDF Form Filler v4..."
echo ""
python pdf_form_filler2.py
