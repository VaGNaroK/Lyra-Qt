import os
import locale
import mpv
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

class MPVPlayerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DontCreateNativeAncestors)
        self.setAttribute(Qt.WA_NativeWindow)
        
        # mpv is sometimes picky about locales
        locale.setlocale(locale.LC_NUMERIC, 'C')
        
        import sys
        mpv_opts = {
            'wid': str(int(self.winId())),
            'log_handler': print,
            'loglevel': 'error',
            'input_default_bindings': True,
            'input_vo_keyboard': True
        }
        
        # Em Linux/Flatpak, o MPV pode se confundir com as camadas Wayland/DRM.
        # Forçamos o uso do X11, que funciona perfeitamente com QT_QPA_PLATFORM=xcb
        if sys.platform.startswith('linux'):
            mpv_opts['vo'] = 'x11'

        # Inicializa o player MPV
        self.mpv = mpv.MPV(**mpv_opts)
                           
    def play(self, filepath):
        if os.path.exists(filepath):
            self.mpv.pause = True
            self.mpv.play(filepath)
            
    def set_audio_delay(self, seconds):
        """
        Define o deslocamento de áudio.
        Valor positivo (ex: 1.5) atrasa o áudio em relação ao vídeo.
        Valor negativo (ex: -1.5) adianta o áudio em relação ao vídeo.
        """
        self.mpv.audio_delay = seconds

    def stop(self):
        self.mpv.stop()
        
    def pause(self, paused=True):
        self.mpv.pause = paused
        
    def update_audio_filters(self, volume_pct, drc_enabled, rnnoise_enabled):
        """
        Aplica os filtros de volume, normalização e redução de ruído em tempo real no player.
        """
        if not hasattr(self, 'mpv') or not self.mpv:
            return
            
        # 1. Volume nativo do MPV mantido em 100 (para evitar curvas não lineares)
        self.mpv.volume = 100
            
        filters = []
        # 1.5 Aplica a mesma escala de amplitude linear do FFmpeg Engine
        if volume_pct != 100:
            filters.append(f"volume={volume_pct/100.0}")
            
        # 2. DRC / Downmix
        if drc_enabled:
            filters.append("pan=stereo|FL=0.5*FC+0.707*FL+0.707*BL+0.5*LFE|FR=0.5*FC+0.707*FR+0.707*BR+0.5*LFE,dynaudnorm")
            
        # 3. RNNoise (Redução de Ruído por IA)
        if rnnoise_enabled:
            model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "models", "cb.rnnn")
            if os.path.exists(model_path):
                # Escapa os caracteres para o lavfi do MPV
                escaped_model_path = model_path.replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
                filters.append(f"lavfi=[arnndn=m='{escaped_model_path}']")
                
        # Aplica os filtros na propriedade af
        self.mpv.af = ",".join(filters) if filters else ""
        
    def __del__(self):
        if hasattr(self, 'mpv') and self.mpv:
            self.mpv.terminate()
