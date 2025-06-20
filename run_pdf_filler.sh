#!/bin/bash
# PDF Form Filler Launcher Script
# This ensures we run with the correct virtual environment

echo "🚀 Starting PDF Form Filler with virtual environment..."
echo "==========================================================="

# Activate virtual environment
source myenv/bin/activate

# Run the PDF Form Filler
python pdf_form_filler1.py

echo ""
echo "📝 Note: This script runs PDF Form Filler in the virtual environment"
echo "where PyPDF2 and pdfplumber are properly installed."
