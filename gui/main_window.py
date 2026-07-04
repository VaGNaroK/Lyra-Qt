import sys
import os
import subprocess
# pyrefly: ignore [missing-import]
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QToolBar,
    QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
    QComboBox, QFrame, QAbstractItemView, QFileDialog, QTabWidget,
    QFormLayout, QCheckBox, QSlider, QSpinBox, QDoubleSpinBox, QLineEdit, QGroupBox, QTimeEdit,
    QMessageBox, QSizePolicy, QPlainTextEdit, QSystemTrayIcon, QMenu,
    QStyle, QApplication, QInputDialog, QListWidget, QListWidgetItem
)
from PySide6.QtGui import QAction, QTextCursor, QIcon, QScreen, QDesktopServices
from PySide6.QtCore import Qt, QSize, QUrl, QSettings, QTime
from PySide6.QtMultimedia import QSoundEffect
from gui.mpv_widget import MPVPlayerWidget

# ==============================================================================
# 🔒 Importação da nossa nova arquitetura modular
# ==============================================================================
try:
    from core.ffmpeg_engine import FFmpegEngine
    from core.preset_manager import PresetManager
    from core.ytdlp_engine import YTDLPEngine
    from core.utils import normalize_bitrate
except ImportError:
    from ffmpeg_engine import FFmpegEngine
    from preset_manager import PresetManager
    from ytdlp_engine import YTDLPEngine
    from utils import normalize_bitrate

class LyraMainWindow(QMainWindow):
    """
    Classe principal da Interface Gráfica (GUI) do Lyra Multimedia Converter.
    Gerencia todas as abas, layouts, interações do usuário e delega as tarefas pesadas
    aos motores assíncronos (FFmpegEngine e YTDLPEngine).
    """
    def __init__(self, version, resource_dir=None):
        super().__init__()
        self.settings = QSettings("Lyra", "Lyra-Qt")
        self.setWindowTitle(f"Lyra Multimedia Converter v{version}")
        self.resize(1024, 650)
        self.setMinimumSize(850, 550)
        self.setAcceptDrops(True)

        self.version = version
        self.resource_dir = resource_dir or os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(self.resource_dir, "assets", "icons", "lyra.svg")
        self.app_icon = (
            QIcon(icon_path) if os.path.exists(icon_path)
            else self.style().standardIcon(QStyle.SP_ComputerIcon)
        )
        self.setWindowIcon(self.app_icon)

        self.is_converting = False
        self.is_downloading = False
        self.tray_available = False

        # ======================================================================
        # ⚙️ INICIALIZAÇÃO DOS MOTORES (CORE)
        # ======================================================================
        self.engine = FFmpegEngine(self.resource_dir)
        self.engine.progress_updated.connect(self.update_progress_ui)
        self.engine.log_updated.connect(self.update_log_ui)
        self.engine.process_finished.connect(self.on_ffmpeg_finished)

        self.preset_manager = PresetManager()
        self.ytdlp_engine = YTDLPEngine(self.resource_dir)

        self.ytdlp_engine.log_updated.connect(
            lambda text: (self.dl_log.insertPlainText(text), self.dl_log.moveCursor(QTextCursor.End))
        )
        self.ytdlp_engine.process_finished.connect(self.on_dl_finished)
        self.ytdlp_engine.error_occurred.connect(self.on_dl_error)

        self.done_sound = QSoundEffect(self)
        sound_path = os.path.join(self.resource_dir, "assets", "sounds", "done.wav")
        if os.path.exists(sound_path):
            self.done_sound.setSource(QUrl.fromLocalFile(os.path.abspath(sound_path)))
            self.done_sound.setVolume(0.7)
        else:
            self.done_sound = None

        self.setup_ui()
        self.setup_tray()
        self.center_on_screen()
        self.load_presets()
        self.apply_checkbox_stylesheet()

    def apply_checkbox_stylesheet(self):
        chk_checked = os.path.join(self.resource_dir, "assets", "icons", "checkbox_checked.svg").replace("\\", "/")
        chk_unchecked = os.path.join(self.resource_dir, "assets", "icons", "checkbox_unchecked.svg").replace("\\", "/")
        
        checkbox_style = f"""
        QCheckBox::indicator, QTableView::indicator, QListView::indicator {{
            width: 18px;
            height: 18px;
        }}
        QCheckBox::indicator:unchecked, QTableView::indicator:unchecked, QListView::indicator:unchecked {{
            image: url("{chk_unchecked}");
        }}
        QCheckBox::indicator:checked, QTableView::indicator:checked, QListView::indicator:checked {{
            image: url("{chk_checked}");
        }}
        """
        self.setStyleSheet(self.styleSheet() + checkbox_style)

    def center_on_screen(self):
        """
        Centraliza a janela do aplicativo perfeitamente no meio do monitor principal do usuário.
        """
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def _play_done_sound(self):
        """
        Toca o arquivo de áudio (done.wav) para alertar o usuário que a conversão foi finalizada.
        """
        if self.done_sound is not None:
            try:
                self.done_sound.play()
            except Exception:
                pass

    def setup_tray(self):
        """
        Configura o ícone na bandeja do sistema (System Tray) para notificações silenciosas.
        """
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            self.tray_available = False
            return

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.app_icon)
        self.tray_icon.setToolTip("Lyra Multimedia Converter")

        show_action = QAction("🖥️ Mostrar Lyra", self)
        quit_action = QAction("❌ Sair", self)
        show_action.triggered.connect(self.showNormal)
        quit_action.triggered.connect(self.force_quit)

        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_available = True

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    def _show_tray_message(self, title, message, icon=QSystemTrayIcon.Information, ms=3000):
        if self.tray_available and self.tray_icon is not None:
            try:
                self.tray_icon.showMessage(title, message, icon, ms)
            except Exception:
                pass
        self._notify_send_fallback(title, message)

    def _notify_send_fallback(self, title, message):
        try:
            subprocess.Popen(
                ["notify-send", "-i", "lyra", title, message],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    def closeEvent(self, event):
        """
        Intercepta o fechamento da janela. Se houver downloads ou conversões ocorrendo,
        pergunta ao usuário se ele realmente quer abortar tudo.
        """
        if getattr(self, '_force_quitting', False):
            event.accept()
            return
            
        if self.tray_available:
            event.ignore()
            self.hide()
            if self.is_converting or self.is_downloading:
                self._show_tray_message(
                    "Lyra em Execução",
                    "O app continuará rodando em segundo plano.",
                    QSystemTrayIcon.Information, 3000
                )
        else:
            if self.is_converting or self.is_downloading:
                resposta = QMessageBox.question(
                    self, "Aviso",
                    "Há uma tarefa em andamento. Deseja forçar o encerramento?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if resposta == QMessageBox.Yes:
                    self.engine.stop_all()
                    self.ytdlp_engine.stop()
                    self._shutdown_mpv()
                    event.accept()
                else:
                    event.ignore()
            else:
                self._shutdown_mpv()
                event.accept()

    def force_quit(self):
        if self.is_converting or self.is_downloading:
            # Parente None para não forçar o 'show()' automático da janela oculta pelo Qt
            resposta = QMessageBox.question(
                None, "Aviso",
                "Há uma tarefa em andamento. Deseja forçar o encerramento?",
                QMessageBox.Yes | QMessageBox.No
            )
            if resposta == QMessageBox.Yes:
                self.engine.stop_all()
                self.ytdlp_engine.stop()
                self._shutdown_mpv()
                self._force_quitting = True
                QApplication.instance().quit()
        else:
            self._shutdown_mpv()
            self._force_quitting = True
            QApplication.instance().quit()

    def _shutdown_mpv(self):
        if hasattr(self, 'mpv_widget'):
            try:
                self.mpv_widget.stop()
                if hasattr(self.mpv_widget, 'mpv') and self.mpv_widget.mpv:
                    self.mpv_widget.mpv.terminate()
            except Exception:
                pass

    def setup_ui(self):
        """
        Ponto de entrada central para construção de toda a interface do aplicativo.
        Configura os painéis (Main, Advanced, Download) e a barra lateral de navegação.
        """
        self.toolbar = QToolBar("Ferramentas Principais")
        self.toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.setStyleSheet("QToolBar QToolButton { font-size: 14px; padding: 4px; font-weight: bold; }")

        self.action_add_file = QAction("📄 Adicionar Arquivo", self)
        self.action_add_folder = QAction("📁 Adicionar Pasta", self)
        self.action_remove = QAction("🗑️ Remover", self)
        self.action_clear = QAction("🧹 Limpar Lista", self)
        self.action_download = QAction("🌐 Baixar da Web", self)
        self.action_advanced = QAction("⚙️ Opções Avançadas", self)

        self.toolbar.addAction(self.action_add_file)
        self.toolbar.addAction(self.action_add_folder)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_remove)
        self.toolbar.addAction(self.action_clear)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_download)
        self.toolbar.addAction(self.action_advanced)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)

        self.btn_convert = QPushButton("🚀 Converter")
        self.btn_convert.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold; padding: 6px 15px; font-size: 13px;")
        self.btn_convert.clicked.connect(self.start_conversion_queue)

        self.btn_stop = QPushButton("🛑 Parar")
        self.btn_stop.setStyleSheet("background-color: #C62828; color: white; font-weight: bold; padding: 6px 15px; font-size: 13px;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_conversion_queue)

        self.toolbar.addWidget(self.btn_convert)
        self.toolbar.addWidget(self.btn_stop)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.create_main_page()
        self.create_advanced_page()
        self.create_download_page()

        self.action_add_file.triggered.connect(self.add_files_dialog)
        self.action_add_folder.triggered.connect(self.add_folder_dialog)
        self.action_remove.triggered.connect(self.remove_selected_files)
        self.action_clear.triggered.connect(self.clear_table)
        self.action_advanced.triggered.connect(lambda: self.switch_page(1 if self.stacked_widget.currentIndex() != 1 else 0))
        self.action_download.triggered.connect(lambda: self.switch_page(2 if self.stacked_widget.currentIndex() != 2 else 0))

    def create_main_page(self):
        """
        Constrói a tela principal onde fica a Tabela de Arquivos e o painel de Destino.
        """
        self.main_page = QWidget()
        main_layout = QVBoxLayout(self.main_page)
        main_layout.setContentsMargins(8, 8, 8, 8)

        format_layout = QHBoxLayout()
        self.combo_format = QComboBox()
        self.combo_format.addItems(["MP4", "MKV", "WEBM", "AVI", "MP3", "OGG", "OPUS", "WAV", "JPG", "PNG", "GIF", "BMP", "WEBP", "SRT"])
        self.combo_format.setMinimumWidth(150)
        format_layout.addWidget(QLabel("🎬 Formato:"))
        format_layout.addWidget(self.combo_format)
        
        self.combo_presets = QComboBox()
        self.combo_presets.setMinimumWidth(200)
        self.combo_presets.currentIndexChanged.connect(self.on_preset_selected)

        self.btn_save_preset = QPushButton("💾 Salvar Preset")
        self.btn_save_preset.clicked.connect(self.save_new_preset)

        self.btn_delete_preset = QPushButton("🗑️ Remover")
        self.btn_delete_preset.clicked.connect(self.delete_selected_preset)
        self.btn_delete_preset.setEnabled(False)

        self.btn_reset_all = QPushButton("🔄 Restaurar Padrões")
        self.btn_reset_all.clicked.connect(self._trigger_hard_reset)

        format_layout.addWidget(QLabel("📂 Presets:"))
        format_layout.addWidget(self.combo_presets)
        format_layout.addWidget(self.btn_reset_all)
        format_layout.addWidget(self.btn_save_preset)
        format_layout.addWidget(self.btn_delete_preset)
        format_layout.addStretch()
        main_layout.addLayout(format_layout)

        self.table_files = QTableWidget(0, 8)
        self.table_files.setHorizontalHeaderLabels([
            "⏭️ Pular", "📋 Arquivo", "⚖️ Tamanho", "⏱️ Duração",
            "📊 Est. Tamanho", "⏳ Decorrido", "⏳ Restante", "📈 Progresso"
        ])
        self.table_files.setStyleSheet("QHeaderView::section { font-size: 13px; font-weight: bold; }")
        self.table_files.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_files.setAlternatingRowColors(True)
        self.table_files.verticalHeader().setVisible(False)
        self.table_files.setColumnWidth(0, 85)
        self.table_files.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for i in range(2, 7):
            self.table_files.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table_files.setColumnWidth(7, 120)
        self.table_files.itemSelectionChanged.connect(self.on_file_selected_for_info)
        main_layout.addWidget(self.table_files)

        dest_layout = QHBoxLayout()
        self.combo_exist_action = QComboBox()
        self.combo_exist_action.addItems(["Sobrescrever", "Escolher outro nome", "Pular conversão"])
        default_dest = os.path.join(os.path.expanduser("~"), "Vídeos", "Lyra")
        saved_dest = self.settings.value("last_destination", default_dest)
        if not os.path.exists(saved_dest):
            try:
                os.makedirs(saved_dest, exist_ok=True)
            except Exception:
                saved_dest = default_dest
                os.makedirs(saved_dest, exist_ok=True)
        self.lbl_dest_path = QLabel(saved_dest)
        self.lbl_dest_path.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.lbl_dest_path.setMinimumWidth(300)
        self.btn_browse_dest = QPushButton("🔍 Procurar...")
        self.btn_browse_dest.clicked.connect(self.browse_destination)
        self.btn_open_dest = QPushButton("📂 Abrir Pasta")
        self.btn_open_dest.clicked.connect(self.open_destination_folder)
        dest_layout.addWidget(QLabel("📂 Destino:"))
        dest_layout.addWidget(self.combo_exist_action)
        dest_layout.addWidget(self.lbl_dest_path)
        dest_layout.addWidget(self.btn_browse_dest)
        dest_layout.addWidget(self.btn_open_dest)
        dest_layout.addStretch()
        main_layout.addLayout(dest_layout)
        self.stacked_widget.addWidget(self.main_page)

    def create_advanced_page(self):
        """
        Constrói a tela de "Opções Avançadas", agrupando todas as abas de codificação:
        Áudio, Vídeo, Imagem, Legenda, Filtros e Mais.
        """
        self.advanced_page = QWidget()
        advanced_layout = QVBoxLayout(self.advanced_page)
        self.tab_widget = QTabWidget()
        self.create_audio_tab()
        self.create_sync_tab()
        self.create_trim_tab()
        self.create_video_tab()
        self.create_image_tab()
        self.create_subtitle_tab()
        self.create_filters_tab()
        self.create_more_tab()
        self.create_info_tab()
        self.create_log_tab()
        
        self.combo_format.currentTextChanged.connect(self.update_format_locks)
        self.update_format_locks()
        advanced_layout.addWidget(self.tab_widget)
        self.stacked_widget.addWidget(self.advanced_page)

    def create_download_page(self):
        """
        Constrói a tela de "Baixar da Web", injetando o painel de URL e opções de qualidade do yt-dlp.
        """
        self.download_page = QWidget()
        layout = QVBoxLayout(self.download_page)
        layout.setContentsMargins(16, 16, 16, 16)

        lbl_title = QLabel("📥 Baixar Mídia da Web")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #42A5F5;")
        layout.addWidget(lbl_title)

        url_layout = QHBoxLayout()
        self.entry_dl_url = QLineEdit()
        self.entry_dl_url.setPlaceholderText("Cole o link do YouTube, Vimeo, Twitter, etc. aqui...")
        url_layout.addWidget(QLabel("🔗 URL do Vídeo:"))
        url_layout.addWidget(self.entry_dl_url)
        layout.addLayout(url_layout)

        group_config = QGroupBox("🛠️ Configurações do Download")
        group_config.setStyleSheet("QGroupBox::title { padding-right: 40px; }") # 🔒 FIX
        config_layout = QVBoxLayout(group_config)

        mode_layout = QHBoxLayout()
        self.combo_dl_mode = QComboBox()
        self.combo_dl_mode.addItems(["Vídeo Completo", "Somente Áudio"])
        self.combo_dl_mode.currentIndexChanged.connect(self.toggle_dl_options)
        mode_layout.addWidget(QLabel("🎭 Modo de Extração:"))
        mode_layout.addWidget(self.combo_dl_mode)
        mode_layout.addStretch()
        config_layout.addLayout(mode_layout)

        self.frame_dl_video = QFrame()
        v_layout = QHBoxLayout(self.frame_dl_video)
        self.combo_dl_v_res = QComboBox()
        self.combo_dl_v_res.addItems(["Melhor Disponível", "2160p (4K)", "1440p (QuadHD)", "1080p (FullHD)", "720p (HD)", "480p (SD)"])
        self.combo_dl_v_fmt = QComboBox()
        self.combo_dl_v_fmt.addItems(["mp4", "mkv", "webm"])
        v_layout.addWidget(QLabel("🖥️ Resolução Máxima:"))
        v_layout.addWidget(self.combo_dl_v_res)
        v_layout.addWidget(QLabel("📦 Formato do Contêiner:"))
        v_layout.addWidget(self.combo_dl_v_fmt)
        v_layout.addStretch()
        config_layout.addWidget(self.frame_dl_video)

        self.frame_dl_audio = QFrame()
        a_layout = QHBoxLayout(self.frame_dl_audio)
        self.combo_dl_a_fmt = QComboBox()
        self.combo_dl_a_fmt.addItems(["mp3", "m4a", "opus", "wav", "flac"])
        self.combo_dl_a_bitrate = QComboBox()
        self.combo_dl_a_bitrate.addItems(["320K", "256K", "192K", "128K"])
        a_layout.addWidget(QLabel("🎵 Formato do Áudio:"))
        a_layout.addWidget(self.combo_dl_a_fmt)
        a_layout.addWidget(QLabel("💎 Qualidade (Bitrate):"))
        a_layout.addWidget(self.combo_dl_a_bitrate)
        a_layout.addStretch()
        config_layout.addWidget(self.frame_dl_audio)
        self.frame_dl_audio.setVisible(False)
        layout.addWidget(group_config)

        btn_dl_layout = QHBoxLayout()
        self.btn_start_dl = QPushButton("📥 Iniciar Download")
        self.btn_start_dl.setStyleSheet("background-color: #0277BD; color: white; font-weight: bold; padding: 6px 20px;")
        self.btn_start_dl.clicked.connect(self.start_download)
        self.btn_stop_dl = QPushButton("❌ Cancelar")
        self.btn_stop_dl.setStyleSheet("background-color: #C62828; color: white; font-weight: bold; padding: 6px 20px;")
        self.btn_stop_dl.setEnabled(False)
        self.btn_stop_dl.clicked.connect(self.stop_download)
        btn_dl_layout.addStretch()
        btn_dl_layout.addWidget(self.btn_start_dl)
        btn_dl_layout.addWidget(self.btn_stop_dl)
        layout.addLayout(btn_dl_layout)

        self.dl_log = QPlainTextEdit()
        self.dl_log.setReadOnly(True)
        self.dl_log.setStyleSheet("background-color: #1e1e1e; color: #00bcd4; font-family: monospace; font-size: 11px;")
        layout.addWidget(self.dl_log)
        self.stacked_widget.addWidget(self.download_page)

    def create_audio_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        
        self.combo_audio_codec = QComboBox()
        self.combo_audio_codec.addItems(["default", "copy", "aac", "libmp3lame", "libvorbis", "libopus", "pcm_s16le"])
        
        self.combo_audio_bitrate = QComboBox()
        self.combo_audio_bitrate.addItems(["default", "64 kbps", "128 kbps", "192 kbps", "256 kbps", "320 kbps"])
        self.combo_audio_bitrate.setEditable(True)
        
        self.combo_audio_freq = QComboBox()
        self.combo_audio_freq.addItems(["default", "22050 Hz", "44100 Hz", "48000 Hz"])
        
        self.combo_audio_channels = QComboBox()
        self.combo_audio_channels.addItems(["default", "1 (Mono)", "2 (Stereo)", "6 (5.1)"])
        
        self.combo_audio_track = QComboBox()
        self.combo_audio_track.addItem("Padrão (Faixa Principal)", -1)
        self.combo_audio_track.currentIndexChanged.connect(self._on_audio_track_changed)
        
        self.chk_all_tracks = QCheckBox("Incluir todas as faixas de áudio")
        self.chk_all_tracks.toggled.connect(lambda checked: self.combo_audio_track.setEnabled(not checked))

        self.chk_audio_drc = QCheckBox("Normalizar Vozes / Downmix 5.1 (DRC)")
        self.chk_audio_drc.stateChanged.connect(self._sync_live_audio_filters)
        
        self.chk_noise_reduction = QCheckBox("Reduzir Ruído de Fundo (Rede Neural RNNoise)")
        self.chk_noise_reduction.stateChanged.connect(self._sync_live_audio_filters)
        
        self.slider_volume = QSlider(Qt.Horizontal)
        self.slider_volume.setRange(0, 400)
        self.slider_volume.setValue(100)
        self.lbl_volume_val = QLabel("100%")
        self.slider_volume.valueChanged.connect(lambda v: self.lbl_volume_val.setText(f"{v}%"))
        self.slider_volume.valueChanged.connect(self._sync_live_audio_filters)
        
        vol_layout = QHBoxLayout()
        vol_layout.addWidget(self.slider_volume)
        vol_layout.addWidget(self.lbl_volume_val)

        layout.addRow("🔊 Codec de Áudio:", self.combo_audio_codec)
        layout.addRow("🎯 Selecionar Faixa:", self.combo_audio_track)
        layout.addRow("💎 Taxa de Bits (Bitrate):", self.combo_audio_bitrate)
        layout.addRow("📊 Frequência:", self.combo_audio_freq)
        layout.addRow("🎛️ Canais:", self.combo_audio_channels)
        layout.addRow("", self.chk_all_tracks)
        layout.addRow("", self.chk_audio_drc)
        layout.addRow("", self.chk_noise_reduction)
        layout.addRow("🔊 Volume do Áudio:", vol_layout)

        group_external_audio = QGroupBox("🎵 Áudios Externos")
        group_external_audio.setStyleSheet("QGroupBox::title { padding-right: 40px; }")
        ext_audio_layout = QVBoxLayout(group_external_audio)
        self.list_external_audios = QListWidget()
        self.list_external_audios.setFixedHeight(60)
        
        btn_ext_audio_layout = QHBoxLayout()
        btn_add_audio = QPushButton("➕ Adicionar")
        btn_add_audio.clicked.connect(self.browse_audio)
        btn_rem_audio = QPushButton("➖ Remover")
        btn_rem_audio.clicked.connect(lambda: self.list_external_audios.takeItem(self.list_external_audios.currentRow()))
        btn_clear_audio = QPushButton("🧹 Limpar")
        btn_clear_audio.clicked.connect(self.list_external_audios.clear)
        
        btn_ext_audio_layout.addWidget(btn_add_audio)
        btn_ext_audio_layout.addWidget(btn_rem_audio)
        btn_ext_audio_layout.addWidget(btn_clear_audio)
        
        ext_audio_layout.addWidget(self.list_external_audios)
        ext_audio_layout.addLayout(btn_ext_audio_layout)
        
        layout.addRow(group_external_audio)
        
        # 🔒 AQUI ESTAVA O PROBLEMA: A linha abaixo tinha desaparecido do seu código!
        self.tab_widget.addTab(tab, "🎵 Áudio")

    def create_sync_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.mpv_widget = MPVPlayerWidget(self)
        self.mpv_widget.setMinimumHeight(300)
        layout.addWidget(self.mpv_widget, 1)
        
        controls_layout = QHBoxLayout()
        self.slider_audio_sync = QSlider(Qt.Horizontal)
        self.slider_audio_sync.setRange(-5000, 5000)
        self.slider_audio_sync.setValue(0)
        
        self.spin_audio_sync = QDoubleSpinBox()
        self.spin_audio_sync.setRange(-5.0, 5.0)
        self.spin_audio_sync.setSingleStep(0.1)
        self.spin_audio_sync.setSuffix("s")
        
        def update_from_slider(val):
            sec = val / 1000.0
            self.spin_audio_sync.blockSignals(True)
            self.spin_audio_sync.setValue(sec)
            self.spin_audio_sync.blockSignals(False)
            self.mpv_widget.set_audio_delay(sec)
            
        def update_from_spin(val):
            ms = int(val * 1000)
            self.slider_audio_sync.blockSignals(True)
            self.slider_audio_sync.setValue(ms)
            self.slider_audio_sync.blockSignals(False)
            self.mpv_widget.set_audio_delay(val)
            
        self.slider_audio_sync.valueChanged.connect(update_from_slider)
        self.spin_audio_sync.valueChanged.connect(update_from_spin)
        
        btn_play = QPushButton("▶️ Play/Pause")
        try:
            btn_play.clicked.connect(lambda: self.mpv_widget.pause(not self.mpv_widget.mpv.pause))
        except:
            pass # handle gracefully if mpv not initialized
        
        controls_layout.addWidget(QLabel("⏳ Atraso de Áudio:"))
        controls_layout.addWidget(self.slider_audio_sync)
        controls_layout.addWidget(self.spin_audio_sync)
        controls_layout.addWidget(btn_play)
        
        layout.addLayout(controls_layout)
        self.tab_widget.addTab(tab, "⏱️ Sincronia")

    def create_trim_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.chk_enable_trim = QCheckBox("✂️ Ativar Corte de Vídeo (Trimming)")
        self.chk_enable_trim.setChecked(False)
        layout.addWidget(self.chk_enable_trim)

        self.mpv_widget_trim = MPVPlayerWidget(self)
        self.mpv_widget_trim.setMinimumHeight(300)
        layout.addWidget(self.mpv_widget_trim, 1)

        controls_layout = QHBoxLayout()

        self.time_start = QTimeEdit()
        self.time_start.setDisplayFormat("HH:mm:ss.zzz")
        self.btn_mark_start = QPushButton("⏱️ Marcar Início")

        self.time_end = QTimeEdit()
        self.time_end.setDisplayFormat("HH:mm:ss.zzz")
        self.btn_mark_end = QPushButton("⏱️ Marcar Fim")

        def set_time_from_mpv(time_edit):
            if hasattr(self.mpv_widget_trim, 'mpv') and self.mpv_widget_trim.mpv:
                pos = self.mpv_widget_trim.mpv.time_pos
                if pos is not None:
                    ms = int(pos * 1000)
                    time_edit.setTime(QTime(0, 0).addMSecs(ms))

        self.btn_mark_start.clicked.connect(lambda: set_time_from_mpv(self.time_start))
        self.btn_mark_end.clicked.connect(lambda: set_time_from_mpv(self.time_end))

        controls_layout.addWidget(QLabel("De:"))
        controls_layout.addWidget(self.time_start)
        controls_layout.addWidget(self.btn_mark_start)
        controls_layout.addStretch()
        controls_layout.addWidget(QLabel("Até:"))
        controls_layout.addWidget(self.time_end)
        controls_layout.addWidget(self.btn_mark_end)

        layout.addLayout(controls_layout)
        self.tab_widget.addTab(tab, "✂️ Cortes")

    def create_video_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        
        self.combo_video_codec = QComboBox()
        self.combo_video_codec.addItems(["default", "copy", "libx264", "libx265", "h264_nvenc", "h.265 nvenc", "mpeg4", "libvpx-vp9", "libvpx-vp8"])

        self.chk_crf = QCheckBox("Usar Qualidade Inteligente (CRF / CQ)")
        self.chk_crf.setChecked(True)
        
        self.slider_crf = QSlider(Qt.Horizontal)
        self.slider_crf.setRange(0, 51)
        self.slider_crf.setValue(23)
        self.lbl_crf_val = QLabel("23 (Qualidade Normal)")

        def update_crf_label(v):
            if v == 0: text = f"{v} (Sem Perdas / Arquivo Gigante)"
            elif v <= 17: text = f"{v} (Insana / Transparente)"
            elif v <= 22: text = f"{v} (Alta Qualidade)"
            elif v <= 27: text = f"{v} (Qualidade Normal)"
            elif v <= 34: text = f"{v} (Qualidade Média)"
            elif v <= 43: text = f"{v} (Qualidade Baixa)"
            else: text = f"{v} (Péssima / Menor Tamanho)"
            self.lbl_crf_val.setText(text)

        self.slider_crf.valueChanged.connect(update_crf_label)

        crf_layout = QHBoxLayout()
        crf_layout.addWidget(self.slider_crf)
        crf_layout.addWidget(self.lbl_crf_val)

        self.combo_video_bitrate = QComboBox()
        self.combo_video_bitrate.addItems(["default", "800 kbps", "1200 kbps", "2500 kbps", "5000 kbps", "8000 kbps"])
        self.combo_video_bitrate.setEditable(True)

        self.combo_video_fps = QComboBox()
        self.combo_video_fps.addItems(["default", "23.976", "24", "25", "29.97", "30", "60"])
        
        self.combo_video_size = QComboBox()
        self.combo_video_size.addItems(["default", "640x480", "854x480 (480p Wide)", "1280x720 (720p)", "1920x1080 (1080p)", "2560x1440 (QuadHD)", "3840x2160 (4K)"])
        self.combo_video_size.setEditable(True)
        
        self.combo_video_ratio = QComboBox()
        self.combo_video_ratio.addItems(["default", "4:3", "16:9", "21:9"])

        self.chk_2pass = QCheckBox("Habilitar Codificação em 2-Passos")
        self.chk_video_only = QCheckBox("Somente Vídeo (Remover Áudio)")
        self.chk_bad_index = QCheckBox("Corrigir index de arquivo corrompido")

        layout.addRow("📹 Codec de Vídeo:", self.combo_video_codec)
        layout.addRow("", self.chk_crf)
        layout.addRow("🎯 Qualidade (CRF):", crf_layout)
        layout.addRow("💎 Taxa de Bits (Bitrate):", self.combo_video_bitrate)
        layout.addRow("🎞️ Quadros por FPS:", self.combo_video_fps)
        layout.addRow("🖥️ Resolução:", self.combo_video_size)
        layout.addRow("📐 Proporção (Aspect):", self.combo_video_ratio)
        layout.addRow("", self.chk_2pass)
        layout.addRow("", self.chk_video_only)
        layout.addRow("", self.chk_bad_index)

        def toggle_crf_mode(checked):
            self.slider_crf.setEnabled(checked)
            self.combo_video_bitrate.setEnabled(not checked)
            if checked:
                self.chk_2pass.setChecked(False)
                self.chk_2pass.setEnabled(False)
            else:
                self.update_video_codec_ui()

        self.chk_crf.toggled.connect(toggle_crf_mode)
        self.combo_video_codec.currentIndexChanged.connect(self.update_video_codec_ui)
        self.update_video_codec_ui()
        toggle_crf_mode(True)

        self.tab_widget.addTab(tab, "🎥 Vídeo")

    def update_video_codec_ui(self):
        codec = self.combo_video_codec.currentText()
        if codec in ["libx264", "libx265"]:
            self.chk_2pass.setEnabled(True)
        else:
            self.chk_2pass.setChecked(False)
            self.chk_2pass.setEnabled(False)

    def update_format_locks(self):
        if not hasattr(self, 'combo_video_codec') or not hasattr(self, 'combo_audio_codec'):
            return
        fmt = self.combo_format.currentText().upper()
        restrict = fmt in ["MP4", "AVI"]
        
        v_model = self.combo_video_codec.model()
        for i in range(self.combo_video_codec.count()):
            if self.combo_video_codec.itemText(i) in ["libvpx-vp9", "libvpx-vp8"]:
                item = v_model.item(i)
                if item:
                    item.setEnabled(not restrict)
                    if restrict and self.combo_video_codec.currentIndex() == i:
                        self.combo_video_codec.setCurrentIndex(0)
                        
        a_model = self.combo_audio_codec.model()
        for i in range(self.combo_audio_codec.count()):
            if self.combo_audio_codec.itemText(i) == "libopus":
                item = a_model.item(i)
                if item:
                    item.setEnabled(not restrict)
                    if restrict and self.combo_audio_codec.currentIndex() == i:
                        self.combo_audio_codec.setCurrentIndex(0)

    def create_image_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        self.combo_img_size = QComboBox()
        self.combo_img_size.addItems(["default", "800x600", "1024x768", "1280x720", "1920x1080", "2560x1440", "3840x2160"])
        self.combo_img_size.setEditable(True)

        self.slider_img_quality = QSlider(Qt.Horizontal)
        self.slider_img_quality.setRange(1, 31)
        self.slider_img_quality.setValue(2)
        self.lbl_img_quality_val = QLabel("2 (Qualidade Máxima)")

        def update_img_label(v):
            if v <= 5: text = f"{v} (Qualidade Máxima)"
            elif v <= 15: text = f"{v} (Boa Qualidade)"
            elif v <= 25: text = f"{v} (Qualidade Média)"
            else: text = f"{v} (Baixa / Mais Leve)"
            self.lbl_img_quality_val.setText(text)

        self.slider_img_quality.valueChanged.connect(update_img_label)
        img_quality_layout = QHBoxLayout()
        img_quality_layout.addWidget(self.slider_img_quality)
        img_quality_layout.addWidget(self.lbl_img_quality_val)

        layout.addRow("🖼️ Resolução (Tamanho):", self.combo_img_size)
        layout.addRow("🎯 Compressão (1-31):", img_quality_layout)
        self.tab_widget.addTab(tab, "🖼️ Imagem")

    def create_subtitle_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group_file = QGroupBox("📁 Seleção de Legendas")
        group_file.setMinimumWidth(450)
        group_file.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        group_file.setStyleSheet("QGroupBox::title { padding-right: 40px; }") # 🔒 FIX

        file_layout = QVBoxLayout(group_file)
        self.list_external_subs = QListWidget()
        self.list_external_subs.setFixedHeight(60)
        
        btn_ext_sub_layout = QHBoxLayout()
        btn_add_sub = QPushButton("➕ Adicionar")
        btn_add_sub.clicked.connect(self.browse_subtitle)
        btn_rem_sub = QPushButton("➖ Remover")
        btn_rem_sub.clicked.connect(lambda: self.list_external_subs.takeItem(self.list_external_subs.currentRow()))
        btn_clear_sub = QPushButton("🧹 Limpar")
        btn_clear_sub.clicked.connect(self.list_external_subs.clear)
        
        btn_ext_sub_layout.addWidget(btn_add_sub)
        btn_ext_sub_layout.addWidget(btn_rem_sub)
        btn_ext_sub_layout.addWidget(btn_clear_sub)
        
        file_layout.addWidget(self.list_external_subs)
        file_layout.addLayout(btn_ext_sub_layout)

        group_mode = QGroupBox("⚙️ Modo de Aplicação")
        group_mode.setStyleSheet("QGroupBox::title { padding-right: 40px; }") # 🔒 FIX
        mode_layout = QFormLayout(group_mode)
        self.combo_sub_mode = QComboBox()
        self.combo_sub_mode.addItems(["Embutir no arquivo (Softsub)", "Queimar no vídeo (Hardsub)"])
        mode_layout.addRow("🎭 Tipo de Renderização:", self.combo_sub_mode)

        layout.addWidget(group_file)
        layout.addWidget(group_mode)

        group_extract = QGroupBox("📤 Extração de Legenda (MKV, MP4)")
        group_extract.setStyleSheet("QGroupBox::title { padding-right: 40px; }")
        extract_layout = QFormLayout(group_extract)
        self.combo_sub_extract_track = QComboBox()
        self.combo_sub_extract_track.addItems(["Faixa 1 (Padrão)", "Faixa 2", "Faixa 3", "Faixa 4"])
        extract_layout.addRow("🎯 Extrair Faixa:", self.combo_sub_extract_track)
        extract_note = QLabel("<i>Nota: Para extrair, selecione 'SRT' como formato na aba principal.<br>Legendas de imagem (PGS) não são suportadas sem OCR.</i>")
        extract_note.setStyleSheet("color: gray;")
        extract_layout.addRow(extract_note)
        layout.addWidget(group_extract)

        group_remove = QGroupBox("🚫 Remoção de Faixas Nativas (Descarte)")
        group_remove.setStyleSheet("QGroupBox::title { padding-right: 40px; }")
        remove_layout = QVBoxLayout(group_remove)
        self.list_sub_remove_tracks = QListWidget()
        self.list_sub_remove_tracks.setFixedHeight(80)
        remove_layout.addWidget(self.list_sub_remove_tracks)
        layout.addWidget(group_remove)

        layout.addStretch()
        self.tab_widget.addTab(tab, "📝 Legendas")

    def browse_subtitle(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Selecionar Legendas", os.path.expanduser("~"),
            "Arquivos de Legenda (*.srt *.ass *.vtt);;Todos os Arquivos (*.*)"
        )
        if paths:
            for path in paths:
                self.list_external_subs.addItem(path)

    def browse_audio(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Selecionar Áudios", os.path.expanduser("~"),
            "Arquivos de Áudio (*.mp3 *.wav *.aac *.flac *.ogg *.m4a);;Todos os Arquivos (*.*)"
        )
        if paths:
            for path in paths:
                self.list_external_audios.addItem(path)

    def create_filters_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        basic_group = QGroupBox("🥋 Filtros Básicos")
        basic_group.setStyleSheet("QGroupBox::title { padding-right: 40px; }") # 🔒 FIX
        basic_layout = QFormLayout(basic_group)
        self.combo_rotate = QComboBox()
        self.combo_rotate.addItems(["Normal", "90° Horário", "90° Anti-horário", "180°", "Espelhar Horizontal", "Espelhar Vertical"])
        self.chk_deinterlace = QCheckBox("Aplicar Desentrelaçamento (Yadif)")
        basic_layout.addRow("🔄 Rotação:", self.combo_rotate)
        basic_layout.addRow("", self.chk_deinterlace)
        layout.addWidget(basic_group)

        fade_group = QGroupBox("🌓 Efeitos de Desvanecimento (Fade)")
        fade_group.setStyleSheet("QGroupBox::title { padding-right: 40px; }") # 🔒 FIX
        fade_layout = QFormLayout(fade_group)
        self.spin_fade_duration = QSpinBox()
        self.spin_fade_duration.setRange(0, 20)
        self.combo_fade_pos = QComboBox()
        self.combo_fade_pos.addItems(["Nenhum", "No início", "No final", "Ambos"])
        self.combo_fade_type = QComboBox()
        self.combo_fade_type.addItems(["Vídeo e Áudio", "Somente Vídeo", "Somente Áudio"])
        fade_layout.addRow("⏳ Duração:", self.spin_fade_duration)
        fade_layout.addRow("📍 Posição:", self.combo_fade_pos)
        fade_layout.addRow("🎭 Tipo:", self.combo_fade_type)
        layout.addWidget(fade_group)

        self.group_crop = QGroupBox("✂️ Cortar Imagem (Crop)")
        self.group_crop.setCheckable(True)
        self.group_crop.setChecked(False)
        self.group_crop.setStyleSheet("QGroupBox::title { padding-right: 40px; }") # 🔒 FIX
        crop_main_layout = QVBoxLayout(self.group_crop)
        crop_layout = QHBoxLayout()
        self.spin_crop_top = QSpinBox()
        self.spin_crop_top.setRange(0, 10000)
        self.spin_crop_bottom = QSpinBox()
        self.spin_crop_bottom.setRange(0, 10000)
        self.spin_crop_left = QSpinBox()
        self.spin_crop_left.setRange(0, 10000)
        self.spin_crop_right = QSpinBox()
        self.spin_crop_right.setRange(0, 10000)
        crop_layout.addWidget(QLabel("🔝 Topo:"))
        crop_layout.addWidget(self.spin_crop_top)
        crop_layout.addWidget(QLabel("🔜 Base:"))
        crop_layout.addWidget(self.spin_crop_bottom)
        crop_layout.addWidget(QLabel("⬅️ Esq:"))
        crop_layout.addWidget(self.spin_crop_left)
        crop_layout.addWidget(QLabel("➡️ Dir:"))
        crop_layout.addWidget(self.spin_crop_right)
        self.btn_auto_crop = QPushButton("🔍 Detectar Bordas Automagicamente")
        self.btn_auto_crop.clicked.connect(self.run_auto_crop)
        crop_main_layout.addLayout(crop_layout)
        crop_main_layout.addWidget(self.btn_auto_crop)
        layout.addWidget(self.group_crop)

        self.group_pad = QGroupBox("🔲 Preencher Bordas (Pad)")
        self.group_pad.setCheckable(True)
        self.group_pad.setChecked(False)
        self.group_pad.setStyleSheet("QGroupBox::title { padding-right: 40px; }") # 🔒 FIX
        pad_layout = QHBoxLayout(self.group_pad)
        self.spin_pad_top = QSpinBox()
        self.spin_pad_top.setRange(0, 10000)
        self.spin_pad_bottom = QSpinBox()
        self.spin_pad_bottom.setRange(0, 10000)
        self.spin_pad_left = QSpinBox()
        self.spin_pad_left.setRange(0, 10000)
        self.spin_pad_right = QSpinBox()
        self.spin_pad_right.setRange(0, 10000)
        pad_layout.addWidget(QLabel("🔝 Topo:"))
        pad_layout.addWidget(self.spin_pad_top)
        pad_layout.addWidget(QLabel("🔜 Base:"))
        pad_layout.addWidget(self.spin_pad_bottom)
        pad_layout.addWidget(QLabel("⬅️ Esq:"))
        pad_layout.addWidget(self.spin_pad_left)
        pad_layout.addWidget(QLabel("➡️ Dir:"))
        pad_layout.addWidget(self.spin_pad_right)
        layout.addWidget(self.group_pad)

        layout.addStretch()
        self.tab_widget.addTab(tab, "🎨 Filtros")

    def run_auto_crop(self):
        selected = self.table_files.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Aviso", "Selecione um ficheiro de vídeo na lista principal primeiro!")
            return
            
        row = selected[0].row()
        file_path = self.table_files.item(row, 1).toolTip()
        
        if not os.path.exists(file_path):
            return
            
        self.btn_auto_crop.setText("⏳ A analisar vídeo...")
        self.btn_auto_crop.setEnabled(False)
        QApplication.processEvents() 
        
        crop_data = self.engine.detect_crop(file_path)
        
        self.btn_auto_crop.setText("🔍 Detectar Bordas Automagicamente")
        self.btn_auto_crop.setEnabled(True)
        
        if crop_data:
            t, b, l, r = crop_data["t"], crop_data["b"], crop_data["l"], crop_data["r"]
            if t == 0 and b == 0 and l == 0 and r == 0:
                QMessageBox.information(self, "Auto-Crop", "O vídeo não tem barras pretas! Já está perfeito.")
            else:
                self.spin_crop_top.setValue(t)
                self.spin_crop_bottom.setValue(b)
                self.spin_crop_left.setValue(l)
                self.spin_crop_right.setValue(r)
                self.group_crop.setChecked(True)
                QMessageBox.information(self, "Auto-Crop", f"Barras removidas com sucesso!\n\nForam cortados:\nTopo: {t}px | Base: {b}px\nEsquerda: {l}px | Direita: {r}px")
        else:
            QMessageBox.warning(self, "Erro", "Não foi possível analisar as bordas deste ficheiro.")

    def create_more_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)

        max_threads = os.cpu_count() or 4
        self.slider_threads = QSlider(Qt.Horizontal)
        self.slider_threads.setRange(0, max_threads)
        self.slider_threads.setValue(0)
        self.lbl_threads_val = QLabel("Auto (Potência Máxima)")

        def update_threads_label(v):
            if v == 0: self.lbl_threads_val.setText("Auto (Potência Máxima)")
            elif v == 1: self.lbl_threads_val.setText("1 Núcleo (Background)")
            else: self.lbl_threads_val.setText(f"{v} Núcleos dedicados")

        self.slider_threads.valueChanged.connect(update_threads_label)
        threads_layout = QHBoxLayout()
        threads_layout.addWidget(self.slider_threads)
        threads_layout.addWidget(self.lbl_threads_val)

        self.entry_extra_args = QLineEdit()
        self.entry_extra_args.setPlaceholderText("Ex: -preset ultrafast -tune animation")
        self.entry_ffmpeg_path = QLineEdit("ffmpeg")

        layout.addRow("🧠 Threads do Processador:", threads_layout)
        layout.addRow("➕ Argumentos Extras do FFMPEG:", self.entry_extra_args)
        layout.addRow("⚙️ Executável do Conversor:", self.entry_ffmpeg_path)
        self.tab_widget.addTab(tab, "➕ Mais Opções")

    def create_log_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.text_log = QPlainTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: monospace; font-size: 11px;")
        layout.addWidget(self.text_log)
        self.tab_widget.addTab(tab, "📜 Log do FFMPEG")

    def create_info_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.text_media_info = QPlainTextEdit()
        self.text_media_info.setReadOnly(True)
        self.text_media_info.setStyleSheet("background-color: #2b2b2b; color: #ffeb3b; font-family: monospace; font-size: 13px;")
        layout.addWidget(self.text_media_info)
        self.tab_widget.addTab(tab, "ℹ️ Info da Mídia")

    def on_file_selected_for_info(self):
        selected_items = self.table_files.selectedItems()
        if not selected_items:
            self.text_media_info.clear()
            return
        
        row = selected_items[0].row()
        file_path = self.table_files.item(row, 1).toolTip()
        
        # 🔒 AQUI ESTAVA O PROBLEMA: Código duplicado limpo para uma única execução fluida
        if os.path.exists(file_path):
            if hasattr(self, 'mpv_widget'):
                self.mpv_widget.play(file_path)
            if hasattr(self, 'mpv_widget_trim'):
                self.mpv_widget_trim.play(file_path)
            self.text_media_info.setPlainText("A analisar mídia...")
            info_text = self.engine.get_human_media_info(file_path)
            self.text_media_info.setPlainText(info_text)
            
            self.combo_audio_track.blockSignals(True)
            self.combo_audio_track.clear()
            self.combo_audio_track.addItem("Padrão (Faixa Principal)", -1)
            
            tracks = self.engine.get_audio_tracks(file_path)
            for track_idx, desc in tracks:
                self.combo_audio_track.addItem(desc, track_idx)
                
            self.combo_audio_track.blockSignals(False)

            self.list_sub_remove_tracks.clear()
            sub_tracks = self.engine.get_subtitle_tracks(file_path)
            for track_idx, desc in sub_tracks:
                item = QListWidgetItem(desc)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                item.setData(Qt.UserRole, track_idx)
                self.list_sub_remove_tracks.addItem(item)
                
            self._sync_live_audio_filters()

    def _sync_live_audio_filters(self, *args):
        if hasattr(self, 'mpv_widget'):
            self.mpv_widget.update_audio_filters(
                self.slider_volume.value(),
                self.chk_audio_drc.isChecked(),
                self.chk_noise_reduction.isChecked()
            )

    def _on_audio_track_changed(self, index):
        if hasattr(self, 'mpv_widget') and hasattr(self.mpv_widget, 'mpv') and self.mpv_widget.mpv:
            track_idx = self.combo_audio_track.currentData()
            if track_idx == -1:
                self.mpv_widget.set_audio_track('auto')
            else:
                self.mpv_widget.set_audio_track(track_idx + 1)

    def switch_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        is_main = (index == 0)
        self.action_add_file.setEnabled(is_main)
        self.action_add_folder.setEnabled(is_main)
        self.action_remove.setEnabled(is_main)
        self.action_clear.setEnabled(is_main)
        self.action_advanced.setText("⚙️ Opções Avançadas" if is_main else ("↩️ Voltar para Lista" if index == 1 else "⚙️ Opções Avançadas"))
        self.action_download.setText("🌐 Baixar da Web" if is_main else ("↩️ Voltar para Lista" if index == 2 else "🌐 Baixar da Web"))

    def toggle_dl_options(self):
        is_audio = self.combo_dl_mode.currentIndex() == 1
        self.frame_dl_video.setVisible(not is_audio)
        self.frame_dl_audio.setVisible(is_audio)

    def open_destination_folder(self):
        path = self.lbl_dest_path.text()
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def browse_destination(self):
        path = QFileDialog.getExistingDirectory(self, "Selecionar Pasta de Destino", self.lbl_dest_path.text(), options=QFileDialog.ShowDirsOnly)
        if path: 
            self.lbl_dest_path.setText(path)
            self.settings.setValue("last_destination", path)

    def add_files_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Adicionar Arquivos", os.path.expanduser("~"))
        for path in paths: self.add_file_to_table(path)

    def add_folder_dialog(self):
        path = QFileDialog.getExistingDirectory(self, "Adicionar Pasta", os.path.expanduser("~"), options=QFileDialog.ShowDirsOnly)
        if path:
            for root, _, files in os.walk(path):
                for f in files: self.add_file_to_table(os.path.join(root, f))

    def add_file_to_table(self, file_path):
        if not os.path.isfile(file_path): return
        row = self.table_files.rowCount()
        self.table_files.insertRow(row)

        chk = QTableWidgetItem()
        chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        chk.setCheckState(Qt.Checked)
        name = QTableWidgetItem(os.path.basename(file_path))
        name.setToolTip(file_path)
        dur_sec = self.engine.get_media_duration(file_path)
        dur = QTableWidgetItem(self.engine.format_time(dur_sec) if dur_sec > 0 else "Imagem/ND")
        dur.setToolTip(str(dur_sec))

        self.table_files.setItem(row, 0, chk)
        self.table_files.setItem(row, 1, name)
        self.table_files.setItem(row, 2, QTableWidgetItem(f"{os.path.getsize(file_path)/1024/1024:.2f} MB"))
        self.table_files.setItem(row, 3, dur)
        self.table_files.setItem(row, 4, QTableWidgetItem("--"))
        self.table_files.setItem(row, 5, QTableWidgetItem("--:--:--"))
        self.table_files.setItem(row, 6, QTableWidgetItem("--:--:--"))
        self.table_files.setItem(row, 7, QTableWidgetItem("Pronto"))

    def remove_selected_files(self):
        if self.is_converting: return
        for row in sorted([r.topRow() for r in self.table_files.selectedRanges()], reverse=True):
            self.table_files.removeRow(row)

    def clear_table(self):
        if not self.is_converting: self.table_files.setRowCount(0)

    def get_ui_options(self):
        return {
            "ffmpeg_path": self.entry_ffmpeg_path.text().strip() or "ffmpeg",
            "vcodec": self.combo_video_codec.currentText(),
            "vbitrate": normalize_bitrate(self.combo_video_bitrate.currentText()),
            "vsize": self.combo_video_size.currentText(),
            "crf_enabled": self.chk_crf.isChecked(),
            "crf_value": self.slider_crf.value(),
            "vfps": self.combo_video_fps.currentText(),
            "acodec": self.combo_audio_codec.currentText(),
            "abitrate": normalize_bitrate(self.combo_audio_bitrate.currentText()),
            "freq": self.combo_audio_freq.currentText().replace(" Hz", "").strip(),
            "channels": self.combo_audio_channels.currentText().split(" ")[0],
            "audio_track": self.combo_audio_track.currentData(),
            "volume": self.slider_volume.value(),
            "all_tracks": self.chk_all_tracks.isChecked(),
            "audio_drc": self.chk_audio_drc.isChecked(),
            "noise_reduction": self.chk_noise_reduction.isChecked(),
            "two_pass": self.chk_2pass.isChecked(),
            "img_size": self.combo_img_size.currentText(),
            "img_quality": self.slider_img_quality.value(),
            "sub_paths": [self.list_external_subs.item(i).text() for i in range(self.list_external_subs.count())],
            "audio_paths": [self.list_external_audios.item(i).text() for i in range(self.list_external_audios.count())],
            "sub_mode": self.combo_sub_mode.currentIndex(),
            "extract_sub_track": self.combo_sub_extract_track.currentIndex(),
            "remove_sub_tracks": [self.list_sub_remove_tracks.item(i).data(Qt.UserRole) for i in range(self.list_sub_remove_tracks.count()) if self.list_sub_remove_tracks.item(i).checkState() == Qt.Checked],
            "trim_enabled": hasattr(self, 'chk_enable_trim') and self.chk_enable_trim.isChecked(),
            "trim_start": self.time_start.time().toString("HH:mm:ss.zzz") if hasattr(self, 'time_start') else "00:00:00.000",
            "trim_end": self.time_end.time().toString("HH:mm:ss.zzz") if hasattr(self, 'time_end') else "00:00:00.000",
            "rotate": self.combo_rotate.currentText(),
            "deinterlace": self.chk_deinterlace.isChecked(),
            "audio_offset_ms": getattr(self, 'slider_audio_sync', None).value() if hasattr(self, 'slider_audio_sync') else 0,
            "fade_dur": self.spin_fade_duration.value(),
            "fade_pos": self.combo_fade_pos.currentText(),
            "fade_type": self.combo_fade_type.currentText(),
            "crop": {
                "enabled": self.group_crop.isChecked(),
                "t": self.spin_crop_top.value(), "b": self.spin_crop_bottom.value(),
                "l": self.spin_crop_left.value(), "r": self.spin_crop_right.value()
            },
            "pad": {
                "enabled": self.group_pad.isChecked(),
                "t": self.spin_pad_top.value(), "b": self.spin_pad_bottom.value(),
                "l": self.spin_pad_left.value(), "r": self.spin_pad_right.value()
            },
            "threads": self.slider_threads.value(),
            "extra_args": self.entry_extra_args.text().strip()
        }

    def start_conversion_queue(self):
        if self.is_converting or self.table_files.rowCount() == 0: return
        
        # Reseta o status de arquivos marcados que já foram concluídos ou deram erro
        for row in range(self.table_files.rowCount()):
            if self.table_files.item(row, 0).checkState() == Qt.Checked:
                current_status = self.table_files.item(row, 7).text()
                if current_status in ("Concluído", "Erro"):
                    self.table_files.item(row, 7).setText("Pronto")
                    self.table_files.item(row, 4).setText("--")
                    self.table_files.item(row, 5).setText("--:--:--")
                    self.table_files.item(row, 6).setText("--:--:--")

        self.is_converting = True
        self.btn_convert.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.text_log.clear()
        self.process_next_file()

    def stop_conversion_queue(self):
        self.engine.stop_all()
        self.is_converting = False
        self.btn_convert.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def process_next_file(self):
        if not self.is_converting: return
        row_to_process = -1
        for row in range(self.table_files.rowCount()):
            if (self.table_files.item(row, 0).checkState() == Qt.Checked and self.table_files.item(row, 7).text() == "Pronto"):
                row_to_process = row
                break

        if row_to_process == -1:
            self.stop_conversion_queue()
            self.text_log.appendPlainText("\n--- FILA DE CONVERSÃO CONCLUÍDA ---\n")
            self._play_done_sound()
            self._show_tray_message("Lyra", "Conversão Concluída!", QSystemTrayIcon.Information, 5000)
            if self.isActiveWindow(): QMessageBox.information(self, "Aviso", "Conversão da lista concluída!")
            return

        input_file = self.table_files.item(row_to_process, 1).toolTip()
        duration = float(self.table_files.item(row_to_process, 3).toolTip())
        output_file = os.path.join(self.lbl_dest_path.text(), f"{os.path.splitext(os.path.basename(input_file))[0]}.{self.combo_format.currentText().lower()}")

        if os.path.exists(output_file):
            action = self.combo_exist_action.currentText()
            if action == "Pular conversão":
                self.table_files.setItem(row_to_process, 7, QTableWidgetItem("Pulado"))
                self.text_log.appendPlainText(f"\n[Aviso] O arquivo '{os.path.basename(output_file)}' já existe. Pulando conversão...\n")
                # Usa um pequeno delay para não travar a UI caso muitos sejam pulados sequencialmente
                from PySide6.QtCore import QTimer
                QTimer.singleShot(100, self.process_next_file)
                return
            elif action == "Escolher outro nome":
                base, ext = os.path.splitext(output_file)
                counter = 1
                while os.path.exists(output_file):
                    output_file = f"{base}_{counter}{ext}"
                    counter += 1
            # Se for "Sobrescrever", segue normalmente, pois o FFmpeg_engine já passa a flag '-y'.

        self.table_files.setItem(row_to_process, 7, QTableWidgetItem("Processando..."))
        self.engine.start_conversion(row_to_process, input_file, output_file, duration, self.get_ui_options())

    def update_progress_ui(self, row, progress, elapsed, rem, size, status):
        self.table_files.item(row, 5).setText(elapsed)
        self.table_files.item(row, 6).setText(rem)
        self.table_files.item(row, 7).setText(status)
        if size: self.table_files.item(row, 4).setText(size)

    def update_log_ui(self, text):
        self.text_log.insertPlainText(text)
        self.text_log.moveCursor(QTextCursor.End)

    def on_ffmpeg_finished(self, row, exitCode, is_download):
        self.text_log.appendPlainText(f"\n[Código de saída: {exitCode}]\n")
        status = "Concluído" if exitCode == 0 else "Erro"
        self.table_files.setItem(row, 7, QTableWidgetItem(status))
        self.process_next_file()

    def load_presets(self):
        data = self.preset_manager.load_presets()
        self.combo_presets.blockSignals(True)
        self.combo_presets.clear()
        self.combo_presets.addItem("🟢 Padrão do Sistema (Automático)")
        for name in data: self.combo_presets.addItem(f"⭐ {name}")
        self.combo_presets.setCurrentIndex(0)
        self.combo_presets.blockSignals(False)
        self.btn_delete_preset.setEnabled(False)

    def _capture_preset_state(self):
        return {
            "preset_version": 1,
            "format": self.combo_format.currentText(),
            "vcodec": self.combo_video_codec.currentText(),
            "vbitrate": self.combo_video_bitrate.currentText(),
            "vsize": self.combo_video_size.currentText(),
            "vfps": self.combo_video_fps.currentText(),
            "two_pass": self.chk_2pass.isChecked(),
            "acodec": self.combo_audio_codec.currentText(),
            "abitrate": self.combo_audio_bitrate.currentText(),
            "freq": self.combo_audio_freq.currentText(),
            "channels": self.combo_audio_channels.currentText(),
            "volume": self.slider_volume.value(),
            "audio_drc": self.chk_audio_drc.isChecked(),
            "noise_reduction": self.chk_noise_reduction.isChecked(),
            "all_tracks": self.chk_all_tracks.isChecked(),
            "rotate": self.combo_rotate.currentText(),
            "deinterlace": self.chk_deinterlace.isChecked(),
            "fade_dur": self.spin_fade_duration.value(),
            "fade_pos": self.combo_fade_pos.currentText(),
            "fade_type": self.combo_fade_type.currentText(),
            "threads": self.slider_threads.value(),
            "sub_mode": self.combo_sub_mode.currentIndex(),
            "crop_enabled": self.group_crop.isChecked(),
            "crop_t": self.spin_crop_top.value(), "crop_b": self.spin_crop_bottom.value(),
            "crop_l": self.spin_crop_left.value(), "crop_r": self.spin_crop_right.value(),
            "pad_enabled": self.group_pad.isChecked(),
            "pad_t": self.spin_pad_top.value(), "pad_b": self.spin_pad_bottom.value(),
            "pad_l": self.spin_pad_left.value(), "pad_r": self.spin_pad_right.value(),
            "extra_args": self.entry_extra_args.text().strip()
        }

    def _apply_preset_state(self, state):
        def set_combo(combo, val):
            if val and combo.findText(val) == -1: combo.addItem(val)
            combo.setCurrentText(val or "default")

        combos = [self.combo_format, self.combo_video_codec, self.combo_video_bitrate, self.combo_video_size, self.combo_video_fps, self.combo_audio_codec, self.combo_audio_bitrate, self.combo_audio_freq, self.combo_audio_channels, self.combo_rotate, self.combo_fade_pos, self.combo_fade_type]
        for c in combos: c.blockSignals(True)

        try:
            self.combo_format.setCurrentText(state.get("format", "MP4"))
            set_combo(self.combo_video_codec, state.get("vcodec"))
            set_combo(self.combo_video_bitrate, state.get("vbitrate"))
            set_combo(self.combo_video_size, state.get("vsize"))
            set_combo(self.combo_video_fps, state.get("vfps"))
            self.chk_2pass.setChecked(bool(state.get("two_pass")))
            set_combo(self.combo_audio_codec, state.get("acodec"))
            set_combo(self.combo_audio_bitrate, state.get("abitrate"))
            set_combo(self.combo_audio_freq, state.get("freq"))
            set_combo(self.combo_audio_channels, state.get("channels"))
            self.slider_volume.setValue(state.get("volume", 100))
            self.chk_all_tracks.setChecked(bool(state.get("all_tracks")))
            self.chk_audio_drc.setChecked(bool(state.get("audio_drc")))
            self.chk_noise_reduction.setChecked(bool(state.get("noise_reduction")))
            set_combo(self.combo_rotate, state.get("rotate"))
            self.chk_deinterlace.setChecked(bool(state.get("deinterlace")))
            self.spin_fade_duration.setValue(state.get("fade_dur", 0))
            set_combo(self.combo_fade_pos, state.get("fade_pos"))
            set_combo(self.combo_fade_type, state.get("fade_type"))
            self.slider_threads.setValue(state.get("threads", 0))
            self.combo_sub_mode.setCurrentIndex(state.get("sub_mode", 0))
            self.group_crop.setChecked(bool(state.get("crop_enabled")))
            self.spin_crop_top.setValue(state.get("crop_t", 0))
            self.spin_crop_bottom.setValue(state.get("crop_b", 0))
            self.spin_crop_left.setValue(state.get("crop_l", 0))
            self.spin_crop_right.setValue(state.get("crop_r", 0))
            self.group_pad.setChecked(bool(state.get("pad_enabled")))
            self.spin_pad_top.setValue(state.get("pad_t", 0))
            self.spin_pad_bottom.setValue(state.get("pad_b", 0))
            self.spin_pad_left.setValue(state.get("pad_l", 0))
            self.spin_pad_right.setValue(state.get("pad_r", 0))
            self.entry_extra_args.setText(state.get("extra_args", ""))
            self.update_video_codec_ui()
        finally:
            for c in combos: c.blockSignals(False)

    def _reset_advanced_options(self):
        combos = [self.combo_video_codec, self.combo_video_bitrate, self.combo_video_size, self.combo_video_fps, 
                  self.combo_audio_codec, self.combo_audio_bitrate, self.combo_audio_freq, self.combo_audio_channels, 
                  self.combo_rotate, self.combo_fade_pos, self.combo_fade_type]
        for c in combos:
            c.blockSignals(True)
            c.setCurrentIndex(0)
            c.blockSignals(False)

        self.chk_2pass.setChecked(False)
        self.chk_all_tracks.setChecked(False)
        self.chk_audio_drc.setChecked(False)
        self.chk_noise_reduction.setChecked(False)
        self.chk_deinterlace.setChecked(False)
        self.slider_volume.setValue(100)
        self.spin_fade_duration.setValue(0)
        self.slider_threads.setValue(0)
        self.combo_sub_mode.setCurrentIndex(0)
        
        self.group_crop.setChecked(False)
        self.spin_crop_top.setValue(0)
        self.spin_crop_bottom.setValue(0)
        self.spin_crop_left.setValue(0)
        self.spin_crop_right.setValue(0)
        
        self.group_pad.setChecked(False)
        self.spin_pad_top.setValue(0)
        self.spin_pad_bottom.setValue(0)
        self.spin_pad_left.setValue(0)
        self.spin_pad_right.setValue(0)
        
        self.entry_extra_args.setText("")
        
        # Fugitivos da Aba Vídeo
        if hasattr(self, 'combo_video_ratio'):
            self.combo_video_ratio.blockSignals(True)
            self.combo_video_ratio.setCurrentIndex(0)
            self.combo_video_ratio.blockSignals(False)
        if hasattr(self, 'chk_crf'):
            self.chk_crf.setChecked(True)
        if hasattr(self, 'slider_crf'):
            self.slider_crf.setValue(23)
        if hasattr(self, 'chk_video_only'):
            self.chk_video_only.setChecked(False)
        if hasattr(self, 'chk_bad_index'):
            self.chk_bad_index.setChecked(False)

        # Fugitivos da Aba Áudio
        if hasattr(self, 'combo_audio_track'):
            self.combo_audio_track.blockSignals(True)
            self.combo_audio_track.setCurrentIndex(0)
            self.combo_audio_track.blockSignals(False)
        if hasattr(self, 'list_external_audios'):
            self.list_external_audios.clear()
        
        # Aba Imagem
        if hasattr(self, 'combo_img_size'):
            self.combo_img_size.blockSignals(True)
            self.combo_img_size.setCurrentIndex(0)
            self.combo_img_size.blockSignals(False)
        if hasattr(self, 'slider_img_quality'):
            self.slider_img_quality.setValue(2)

        # Aba Legendas
        if hasattr(self, 'list_external_subs'):
            self.list_external_subs.clear()
        if hasattr(self, 'combo_sub_extract_track'):
            self.combo_sub_extract_track.setCurrentIndex(0)
        if hasattr(self, 'list_sub_remove_tracks'):
            self.list_sub_remove_tracks.clear()

        # Aba Sincronia
        if hasattr(self, 'slider_audio_sync'):
            self.slider_audio_sync.setValue(0)
        if hasattr(self, 'spin_audio_sync'):
            self.spin_audio_sync.setValue(0.0)

        # Aba Corte (Trimming)
        from PySide6.QtCore import QTime
        if hasattr(self, 'chk_enable_trim'):
            self.chk_enable_trim.setChecked(False)
        if hasattr(self, 'time_start'):
            self.time_start.setTime(QTime(0, 0))
        if hasattr(self, 'time_end'):
            self.time_end.setTime(QTime(0, 0))

        self.update_video_codec_ui()

    def _trigger_hard_reset(self):
        self.combo_presets.blockSignals(True)
        self.combo_presets.setCurrentIndex(0)
        self.combo_presets.blockSignals(False)
        self._reset_advanced_options()

    def save_new_preset(self):
        name, ok = QInputDialog.getText(self, "Salvar Preset", "Nome do Preset:")
        if not ok or not name.strip(): return
        name = name.strip()
        if name in self.preset_manager.presets_data:
            QMessageBox.warning(self, "Conflito", f"Já existe um preset chamado '{name}'.")
            return
        state = self._capture_preset_state()
        if self.preset_manager.save_preset(name, state):
            self.load_presets()
            idx = self.combo_presets.findText(f"⭐ {name}")
            if idx != -1: self.combo_presets.setCurrentIndex(idx)
            QMessageBox.information(self, "Sucesso", f"Preset '{name}' salvo!")
        else:
            QMessageBox.critical(self, "Erro", "Falha ao salvar o preset no disco.")

    def delete_selected_preset(self):
        current = self.combo_presets.currentText()
        if not current.startswith("⭐ "): return
        name = current[2:]
        if QMessageBox.question(self, "Confirmar", f"Remover preset '{name}'?") == QMessageBox.No: return
        if self.preset_manager.delete_preset(name):
            self.load_presets()
        else:
            QMessageBox.critical(self, "Erro", "Falha ao remover o preset.")

    def on_preset_selected(self, index):
        if index == 0:
            self.btn_delete_preset.setEnabled(False)
            self._reset_advanced_options()
            return
        self.btn_delete_preset.setEnabled(True)
        current = self.combo_presets.itemText(index)
        if not current.startswith("⭐ "): return
        name = current[2:]
        state = self.preset_manager.presets_data.get(name)
        if state: self._apply_preset_state(state)

    def start_download(self):
        url = self.entry_dl_url.text().strip()
        if not url: return
        self.is_downloading = True
        self.btn_start_dl.setEnabled(False)
        self.btn_stop_dl.setEnabled(True)
        self.dl_log.clear()
        dest_path = self.lbl_dest_path.text()
        mode = self.combo_dl_mode.currentIndex()
        options = {
            "a_fmt": self.combo_dl_a_fmt.currentText(),
            "a_bitrate": self.combo_dl_a_bitrate.currentText(),
            "v_fmt": self.combo_dl_v_fmt.currentText(),
            "v_res": self.combo_dl_v_res.currentText()
        }
        self.ytdlp_engine.start_download(url, dest_path, mode, options)

    def stop_download(self):
        self.ytdlp_engine.stop()
        self.is_downloading = False
        self.btn_start_dl.setEnabled(True)
        self.btn_stop_dl.setEnabled(False)

    def on_dl_finished(self, exitCode):
        self.is_downloading = False
        self.btn_start_dl.setEnabled(True)
        self.btn_stop_dl.setEnabled(False)
        self.dl_log.appendPlainText("\n✅ Concluído!" if exitCode == 0 else f"\n❌ Falha (Código {exitCode}).")
        self._play_done_sound()
        self._show_tray_message("Lyra", "Download Concluído!", QSystemTrayIcon.Information, 5000)
        
    def on_dl_error(self, error):
        self.is_downloading = False
        self.btn_start_dl.setEnabled(True)
        self.btn_stop_dl.setEnabled(False)
        self.dl_log.appendPlainText(f"\n❌ Erro crítico: Falha ao iniciar o motor de download ({error}).")

    # ======================================================================
    # DRAG AND DROP EVENTS
    # ======================================================================
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                self.add_file_to_table(file_path)
            elif os.path.isdir(file_path):
                for root, _, files in os.walk(file_path):
                    for file in files:
                        self.add_file_to_table(os.path.join(root, file))