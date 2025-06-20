#!/usr/bin/env python3
"""
Minimal test version to isolate bus error issue
"""

import sys
import os

print("🔍 Testing minimal PyQt6 functionality...")

try:
    print("1. Testing basic PyQt6 import...")
    from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
    from PyQt6.QtCore import Qt
    print("✅ PyQt6 widgets imported successfully")
    
    print("2. Testing QApplication creation...")
    app = QApplication(sys.argv)
    print("✅ QApplication created successfully")
    
    print("3. Testing basic window creation...")
    
    class MinimalWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Minimal Test")
            self.setGeometry(100, 100, 400, 300)
            
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            layout = QVBoxLayout(central_widget)
            label = QLabel("✅ Minimal PyQt6 window working!")
            layout.addWidget(label)
            
            print("✅ Minimal window created successfully")
    
    print("4. Testing window instantiation...")
    window = MinimalWindow()
    print("✅ Window instantiated successfully")
    
    print("5. Testing window show...")
    window.show()
    print("✅ Window shown successfully")
    
    print("🎉 ALL BASIC TESTS PASSED")
    print("The bus error is likely in the more complex parts of pdf_form_filler2.py")
    
    # Run for 2 seconds then exit
    import threading
    def close_app():
        import time
        time.sleep(2)
        app.quit()
    
    timer_thread = threading.Thread(target=close_app)
    timer_thread.daemon = True
    timer_thread.start()
    
    sys.exit(app.exec())
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
