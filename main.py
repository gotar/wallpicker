#!/usr/bin/env python3
import os
import sys

# Add src directory to path
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
sys.path.insert(0, src_path)  # noqa: E402

from ui.main_window import MainWindow


def main():
    debug = "--debug" in sys.argv
    if debug:
        sys.argv.remove("--debug")

    app = MainWindow(debug=debug)
    app.run()


if __name__ == "__main__":
    main()
