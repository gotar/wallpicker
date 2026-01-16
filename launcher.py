#!/usr/bin/env python3
import os
import signal
import sys
from pathlib import Path

# Add src directory to path FIRST
project_dir = Path(__file__).parent
src_dir = project_dir / "src"
sys.path.insert(0, str(src_dir))

# Change to project directory
os.chdir(project_dir)

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# Set up asyncio event loop for GTK integration
from core.asyncio_integration import setup_event_loop

loop = setup_event_loop()

# Import and run main
from ui.main_window import MainWindow

app = MainWindow()

# Disable default SIGINT handler that conflicts with GTK
signal.signal(signal.SIGINT, signal.SIG_DFL)

exit_status = app.run()
sys.exit(exit_status)
