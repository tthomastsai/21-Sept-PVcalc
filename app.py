"""
Entry point for the Bond & Installment Accounts Calculator (v2.0.1).

    python app.py            Launch the HTML GUI in your browser (default)
    python app.py --tk       Launch the legacy Tkinter desktop GUI
    python app.py --cli      Launch the interactive terminal mode

HTML GUI options (see web_app.py): --port N, --no-browser
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)

    if "--cli" in argv or "--tk" in argv:
        # Imported lazily so the HTML GUI works on Pythons without tkinter.
        from bond_app import main as legacy_main

        sys.argv = [sys.argv[0]] + (["--cli"] if "--cli" in argv else [])
        legacy_main()
    else:
        from web_app import main as web_main

        web_main(argv)


if __name__ == "__main__":
    main()
