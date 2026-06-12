import os
import locale
import mpv
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QLabel
from PySide6.QtCore import Qt, QTimer, Signal

def format_time(seconds):
    if seconds is None:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

class MPVPlayerWidget(QWidget):
    # Sinais para comunicação thread-safe com o MPV
    time_pos_changed = Signal(float)
    duration_changed = Signal(float)
    pause_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Layout principal do container
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Widget nativo de vídeo para o MPV desenhar
        self.video_widget = QWidget(self)
        self.video_widget.setAttribute(Qt.WA_DontCreateNativeAncestors)
        self.video_widget.setAttribute(Qt.WA_NativeWindow)
        from PySide6.QtWidgets import QSizePolicy
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.layout.addWidget(self.video_widget, stretch=1)

        # Barra de Controles Nativos do Qt
        self.controls_widget = QWidget(self)
        self.controls_layout = QHBoxLayout(self.controls_widget)
        self.controls_layout.setContentsMargins(10, 5, 10, 5)

        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(30, 30)
        self.play_btn.clicked.connect(self.toggle_play)

        self.time_label = QLabel("00:00")
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        self.slider.sliderMoved.connect(self.on_slider_moved)

        self.duration_label = QLabel("00:00")

        self.controls_layout.addWidget(self.play_btn)
        self.controls_layout.addWidget(self.time_label)
        self.controls_layout.addWidget(self.slider)
        self.controls_layout.addWidget(self.duration_label)

        self.layout.addWidget(self.controls_widget)

        # Conecta os sinais assíncronos às funções da UI
        self.time_pos_changed.connect(self.update_time_ui)
        self.duration_changed.connect(self.update_duration_ui)
        self.pause_changed.connect(self.update_pause_ui)

        self._is_seeking = False
        self._duration = 0

        # O MPV exige isso em algumas distribuições
        locale.setlocale(locale.LC_NUMERIC, 'C')

        self.mpv = None

        # Dá 100ms para o Qt criar a janela nativa no compositor e gerar um winId válido
        QTimer.singleShot(100, self.init_mpv)

    def init_mpv(self):
        import sys

        mpv_opts = {
            'wid': str(int(self.video_widget.winId())),
            'log_handler': print,
            'loglevel': 'error',
            'input_default_bindings': False, # Impede roubo de atalhos do Qt
            'input_vo_keyboard': False,
            'keep_open': 'yes',
            'hwdec': 'auto-safe',
        }

        if sys.platform.startswith('linux'):
            # Silencia os logs diretos de libva (que ignoram o msg_level do MPV e cospem no stderr)
            os.environ['LIBVA_MESSAGING_LEVEL'] = '0'
            
            mpv_opts['vo'] = 'gpu'
            mpv_opts['gpu_api'] = 'opengl'
            mpv_opts['gpu_context'] = 'auto'
            mpv_opts['force_window'] = 'no'
            mpv_opts['terminal'] = 'no'
            # Desativa o log verboso de drivers não encontrados (VAAPI) do X11/DRM
            mpv_opts['msg_level'] = 'all=fatal'

        try:
            self.mpv = mpv.MPV(**mpv_opts)
            
            # Registra os observadores do MPV (eles rodam numa thread paralela do MPV)
            @self.mpv.property_observer('time-pos')
            def time_observer(_name, value):
                if value is not None:
                    self.time_pos_changed.emit(value)

            @self.mpv.property_observer('duration')
            def duration_observer(_name, value):
                if value is not None:
                    self.duration_changed.emit(value)

            @self.mpv.property_observer('pause')
            def pause_observer(_name, value):
                if value is not None:
                    self.pause_changed.emit(value)

        except Exception as e:
            print(f"CRITICAL ERROR IN MPV INITIALIZATION: {e}")

    # --- Slots de Atualização da UI ---
    def update_time_ui(self, value):
        if not self._is_seeking and self._duration > 0:
            self.time_label.setText(format_time(value))
            pos = int((value / self._duration) * 1000)
            self.slider.blockSignals(True)
            self.slider.setValue(pos)
            self.slider.blockSignals(False)

    def update_duration_ui(self, value):
        self._duration = value
        self.duration_label.setText(format_time(value))

    def update_pause_ui(self, paused):
        self.play_btn.setText("▶" if paused else "⏸")

    # --- Ações do Usuário ---
    def toggle_play(self):
        if self.mpv:
            self.mpv.pause = not self.mpv.pause

    def on_slider_pressed(self):
        self._is_seeking = True

    def on_slider_moved(self, position):
        if self._duration > 0:
            seek_time = (position / 1000.0) * self._duration
            self.time_label.setText(format_time(seek_time))

    def on_slider_released(self):
        self._is_seeking = False
        if self.mpv and self._duration > 0:
            try:
                seek_time = (self.slider.value() / 1000.0) * self._duration
                self.mpv.time_pos = seek_time
            except Exception:
                pass

    # --- API Original do Player ---
    def play(self, filepath):
        if os.path.exists(filepath):
            self.mpv.pause = True
            self.mpv.play(filepath)

    def set_audio_delay(self, seconds):
        if self.mpv:
            self.mpv.audio_delay = seconds

    def set_audio_track(self, aid_value):
        """
        Altera a faixa de áudio em tempo real no MPV.
        aid_value: 'auto', 'no', ou inteiro (1, 2, 3...)
        """
        if self.mpv:
            try:
                self.mpv.aid = aid_value
            except Exception as e:
                print(f"Erro ao mudar a faixa de áudio no MPV: {e}")

    def stop(self):
        if self.mpv:
            self.mpv.stop()
        self.time_label.setText("00:00")
        self.slider.blockSignals(True)
        self.slider.setValue(0)
        self.slider.blockSignals(False)

    def pause(self, paused=True):
        if self.mpv:
            self.mpv.pause = paused

    def update_audio_filters(self, volume_pct, drc_enabled, rnnoise_enabled):
        if not hasattr(self, 'mpv') or not self.mpv:
            return

        self.mpv.volume = 100
        filters = []
        if volume_pct != 100:
            filters.append(f"volume={volume_pct/100.0}")
        if drc_enabled:
            filters.append("pan=stereo|FL=0.5*FC+0.707*FL+0.707*BL+0.5*LFE|FR=0.5*FC+0.707*FR+0.707*BR+0.5*LFE,dynaudnorm")
        if rnnoise_enabled:
            model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "models", "cb.rnnn")
            if os.path.exists(model_path):
                escaped_model_path = model_path.replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
                filters.append(f"lavfi=[arnndn=m='{escaped_model_path}']")
        
        self.mpv.af = ",".join(filters) if filters else ""

    def __del__(self):
        if hasattr(self, 'mpv') and self.mpv:
            self.mpv.terminate()
