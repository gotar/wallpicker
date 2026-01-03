#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add src directory to path
project_dir = Path(__file__).parent
src_dir = project_dir / "src"
sys.path.insert(0, str(src_dir))

# Change to project directory
os.chdir(project_dir)

# Import and run main
from ui.main_window import MainWindow
from gi.repository import Gtk, GLib

app = MainWindow()
exit_status = app.run(sys.argv)
sys.exit(exit_status)
