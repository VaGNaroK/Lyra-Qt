import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

# ==============================================================================
# 🔒 ÚNICA FONTE DA VERDADE (Single Source of Truth)
# O package.sh faz grep '^__version__' para extrair este valor.
# ==============================================================================
__version__ = "1.1.24"

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

# 🔒 INJEÇÃO DE DLL PATH (CRÍTICO PARA WINDOWS)
# O pacote python-mpv exige que a DLL (mpv-1.dll ou mpv-2.dll) esteja no %PATH% do sistema
# antes do próprio módulo ser importado. Aqui nós garantimos que a pasta 'assets/bin' 
# e a raiz da aplicação empacotada sejam expostas para o ambiente.
if sys.platform == "win32":
    import ctypes
    possible_dll_dirs = [
        os.path.join(RESOURCE_DIR, "assets", "bin"),
        RESOURCE_DIR,
        os.path.dirname(sys.executable),
        os.path.join(os.path.dirname(sys.executable), "assets", "bin"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "bin")
    ]
    for d in possible_dll_dirs:
        if d and os.path.isdir(d):
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, 'add_dll_directory'):
                try:
                    os.add_dll_directory(d)
                except Exception:
                    pass
            try:
                ctypes.windll.kernel32.SetDllDirectoryW(d)
            except Exception:
                pass
            
            # 🔒 MITIGAÇÃO: Remover o "Mark of the Web" para evitar o WinError 1114 no carregamento via ctypes
            try:
                for filename in os.listdir(d):
                    zone_id_path = os.path.join(d, filename) + ":Zone.Identifier"
                    if os.path.exists(zone_id_path):
                        os.remove(zone_id_path)
            except Exception:
                pass
# ==============================================================================
# 🔒 INJEÇÃO DE CUDA PATH (CRÍTICO PARA LINUX VENV)
# Garante que as bibliotecas da NVIDIA instaladas via pip sejam carregadas no ONNX
# ==============================================================================
if sys.platform.startswith('linux'):
    venv_base = os.path.dirname(os.path.dirname(sys.executable))
    nvidia_libs = os.path.join(venv_base, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages', 'nvidia')
    
    if os.path.exists(nvidia_libs):
        cuda_paths = []
        for folder in os.listdir(nvidia_libs):
            lib_path = os.path.join(nvidia_libs, folder, 'lib')
            if os.path.exists(lib_path):
                cuda_paths.append(lib_path)
        
        if cuda_paths:
            new_ld_path = ":".join(cuda_paths) + ":" + os.environ.get("LD_LIBRARY_PATH", "")
            # Previne loop infinito: só reinicia se a variável ainda não foi configurada
            if os.environ.get("LYRA_CUDA_INJECTED") != "1":
                os.environ["LD_LIBRARY_PATH"] = new_ld_path
                os.environ["LYRA_CUDA_INJECTED"] = "1"
                os.execv(sys.executable, [sys.executable] + sys.argv)

# Importação segura da GUI e do motor de internacionalização
try:
    from gui.main_window import LyraMainWindow
    from core.i18n import i18n
except ImportError:
    from main_window import LyraMainWindow
    from i18n import i18n

if __name__ == "__main__":
    i18n.reinit_resource_dir(RESOURCE_DIR)
    # Força o uso do X11 (xcb) no Linux porque o Wayland não permite embed de wid no mpv
    if sys.platform.startswith('linux'):
        os.environ["QT_QPA_PLATFORM"] = "xcb"

    # Silencia logs irrelevantes do Qt Multimedia e do QPA Services (cosmético)
    os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.multimedia.*=false;qt.qpa.services=false"

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
    
    # Processa argumentos de linha de comando (ex: via "Abrir com..." do SO)
    for arg in sys.argv[1:]:
        if arg.startswith('-'):
            continue
        if os.path.exists(arg) and os.path.isfile(arg):
            window.add_file_to_table(os.path.abspath(arg))

    window.show()
    sys.exit(app.exec())
