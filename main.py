import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

# ==============================================================================
# 🔒 ÚNICA FONTE DA VERDADE (Single Source of Truth)
# O package.sh faz grep '^__version__' para extrair este valor.
# ==============================================================================
__version__ = "1.1.8"

# ==============================================================================
# 🔒 DETECÇÃO DE AMBIENTE FLATPAK
# ==============================================================================
IS_FLATPAK = "FLATPAK_ID" in os.environ

def _resolve_resource_dir():
    """Retorna o diretório dos recursos estáticos (lyra.svg, done.wav, motores .exe)."""
    # 1. Modo Windows Compilado (PyInstaller)
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS

    # 2. Modo Linux Sandbox (Flatpak)
    if IS_FLATPAK:
        flatpak_dir = "/app/share/lyra"
        if os.path.isdir(flatpak_dir):
            return flatpak_dir
            
    # 3. Modo Desenvolvimento Normal (Linux/Windows Terminal)
    return os.path.dirname(os.path.abspath(__file__))

RESOURCE_DIR = _resolve_resource_dir()

# Importação segura da GUI
try:
    from gui.main_window import LyraMainWindow
except ImportError:
    from main_window import LyraMainWindow

if __name__ == "__main__":
    # Silencia log informativo do Qt Multimedia (cosmético)
    os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.ffmpeg=false")

    app = QApplication(sys.argv)
    app.setApplicationName("Lyra Multimedia Converter")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("VaGNaroK")
    app.setDesktopFileName("lyra-multimedia-converter")
    app.setStyle("Fusion")

    # Tema Dark Blindado
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)

    window = LyraMainWindow(__version__, RESOURCE_DIR)
    window.show()
    sys.exit(app.exec())
