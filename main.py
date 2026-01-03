#!/usr/bin/env python3

import sys
import os

# Add src directory to path
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, src_path)

from ui.main_window import MainWindow

def main():
    app = MainWindow()
    app.run()

if __name__ == '__main__':
    main()
