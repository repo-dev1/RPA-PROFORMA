"""
ACONIC - Cuadro Comparativo de Proformas
Entry point for the GUI application.
"""

import os
import sys


def get_base_dir():
    """Get the base directory of the application.
    Works both when running as a script and as a PyInstaller .exe.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe — use the directory where the .exe is
        return os.path.dirname(sys.executable)
    else:
        # Running as a script
        return os.path.dirname(os.path.abspath(__file__))


def main():
    base_dir = get_base_dir()

    # Parse --output-dir argument for network deployment
    output_dir = None
    for i, arg in enumerate(sys.argv):
        if arg == '--output-dir' and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]
            break

    # Set working directory to the base dir so relative imports work
    os.chdir(base_dir)

    # Ensure required directories exist
    os.makedirs("input", exist_ok=True)
    os.makedirs("templates", exist_ok=True)

    # Output directory: use --output-dir if specified, otherwise local 'output/'
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        os.environ['PROFORMA_OUTPUT_DIR'] = output_dir
    else:
        os.makedirs("output", exist_ok=True)
        os.environ['PROFORMA_OUTPUT_DIR'] = os.path.join(base_dir, "output")

    from gui.app import ProformaApp
    app = ProformaApp()
    app.mainloop()


if __name__ == "__main__":
    main()