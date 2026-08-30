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
    QStyle, QApplication, QInputDialog, QListWidget, QListWidgetItem, QRadioButton,
    QProgressBar
)
from PySide6.QtGui import QAction, QTextCursor, QIcon, QScreen, QDesktopServices, QStandardItemModel, QPixmap
from PySide6.QtCore import Qt, QSize, QUrl, QSettings, QTime
from PySide6.QtMultimedia import QSoundEffect
from gui.mpv_widget import MPVPlayerWidget

# ==============================================================================
# 🔒 Importação da nossa arquitetura modular e internacionalização
# ==============================================================================
try:
    from core.ffmpeg_engine import FFmpegEngine
    from core.preset_manager import PresetManager
    from core.ytdlp_engine import YTDLPEngine
    from core.utils import normalize_bitrate
    from core.i18n import i18n, tr, SUPPORTED_LANGUAGES
except ImportError:
    from ffmpeg_engine import FFmpegEngine
    from preset_manager import PresetManager
    from ytdlp_engine import YTDLPEngine
    from utils import normalize_bitrate
    from i18n import i18n, tr, SUPPORTED_LANGUAGES


class LyraMainWindow(QMainWindow):
    """
    Classe principal da Interface Gráfica (GUI) do Lyra Multimedia Converter.
    Gerencia todas as abas, layouts, interações do usuário e delega as tarefas pesadas
    aos motores assíncronos (FFmpegEngine e YTDLPEngine).
    Totalmente internacionalizada com suporte a múltiplos idiomas em tempo de execução.
    """
    def __init__(self, version, resource_dir=None):
        super().__init__()
        self.settings = QSettings("Lyra", "Lyra-Qt")
        self.version = version
        self.resource_dir = resource_dir or os.path.dirname(os.path.abspath(__file__))
        
        # Inicializa o subsistema de internacionalização
        i18n.reinit_resource_dir(self.resource_dir)

        self.setWindowTitle(tr("app_title", version=self.version))
        self.resize(1050, 700)
        self.setMinimumSize(950, 550)
        self.setAcceptDrops(True)

        icon_path = os.path.join(self.resource_dir, "assets", "icons", "lyra.svg")
        self.app_icon = (
            QIcon(icon_path) if os.path.exists(icon_path)
            else self.style().standardIcon(QStyle.SP_ComputerIcon)
        )
        self.setWindowIcon(self.app_icon)

        self.is_converting = False
        self.is_downloading = False
        self.tray_available = False
        self._force_quitting = False  # ✅ FIX: declaração explícita evita estado implícito (getattr defensivo)

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

        # Conecta sinal de alteração de idioma para re-tradução dinâmica da interface
        i18n.language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()

    def apply_checkbox_stylesheet(self):
        chk_checked = os.path.join(self.resource_dir, "assets", "icons", "checkbox_checked.svg").replace("\\", "/")
        chk_unchecked = os.path.join(self.resource_dir, "assets", "icons", "checkbox_unchecked.svg").replace("\\", "/")
        
        checkbox_style = f"""
        QLineEdit {{
            placeholder-text-color: white;
        }}
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
        self.tray_icon.setToolTip(tr("app_name"))

        self.tray_show_action = QAction(tr("tray_show"), self)
        self.tray_quit_action = QAction(tr("tray_quit"), self)
        self.tray_show_action.triggered.connect(self.showNormal)
        self.tray_quit_action.triggered.connect(self.force_quit)

        tray_menu = QMenu()
        tray_menu.addAction(self.tray_show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(self.tray_quit_action)

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
            icon_path = os.path.join(self.resource_dir, "assets", "icons", "lyra.svg")
            if not os.path.exists(icon_path):
                icon_path = "dialog-information"
            
            subprocess.Popen(
                ["notify-send", "-a", "Lyra", "-i", icon_path, title, message],
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
        if self._force_quitting:
            event.accept()
            return
            
        if self.tray_available:
            event.ignore()
            self.hide()
            if self.is_converting or self.is_downloading:
                self._show_tray_message(
                    tr("tray_running_title"),
                    tr("tray_running_msg"),
                    QSystemTrayIcon.Information, 3000
                )
        else:
            if self.is_converting or self.is_downloading:
                resposta = QMessageBox.question(
                    self, tr("dialog_warning"),
                    tr("close_confirm_msg"),
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
            resposta = QMessageBox.question(
                None, tr("dialog_warning"),
                tr("close_confirm_msg"),
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
        Configura os painéis (Main, Advanced, Download), barra lateral e seletor de idiomas.
        """
        self.toolbar = QToolBar(tr("toolbar_title"))
        self.toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.toolbar.setStyleSheet("QToolBar QToolButton { font-size: 14px; padding: 4px; font-weight: bold; }")

        self.action_add_file = QAction(tr("action_add_file"), self)
        self.action_add_file.setShortcut("Ctrl+O")
        self.action_add_file.setToolTip(tr("action_add_file_tt"))

        self.action_add_folder = QAction(tr("action_add_folder"), self)
        self.action_add_folder.setShortcut("Ctrl+Shift+O")
        self.action_add_folder.setToolTip(tr("action_add_folder_tt"))

        self.action_remove = QAction(tr("action_remove"), self)
        self.action_remove.setShortcut("Delete")
        self.action_remove.setToolTip(tr("action_remove_tt"))
        
        self.action_clear = QAction(tr("action_clear"), self)
        self.action_clear.setShortcut("Ctrl+L")
        self.action_clear.setToolTip(tr("action_clear_tt"))
        
        self.action_download = QAction(tr("action_download"), self)
        self.action_download.setShortcut("Ctrl+D")
        self.action_download.setToolTip(tr("action_download_tt"))
        
        self.action_advanced = QAction(tr("action_advanced"), self)
        self.action_advanced.setShortcut("Ctrl+E")
        self.action_advanced.setToolTip(tr("action_advanced_tt"))

        self.toolbar.addAction(self.action_add_file)
        self.toolbar.addAction(self.action_add_folder)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_remove)
        self.toolbar.addAction(self.action_clear)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.action_download)
        self.toolbar.addAction(self.action_advanced)

        self.btn_convert = QPushButton(tr("btn_convert"))
        self.btn_convert.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold; padding: 6px 15px; font-size: 13px;")
        self.btn_convert.clicked.connect(self.start_conversion_queue)

        self.btn_stop = QPushButton(tr("btn_stop"))
        self.btn_stop.setStyleSheet("background-color: #C62828; color: white; font-weight: bold; padding: 6px 15px; font-size: 13px;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_conversion_queue)

        self.btn_convert.setShortcut("F5")
        self.btn_stop.setShortcut("Escape")

        # Espaçamento visual antes dos botões de ação
        spacer_small = QWidget()
        spacer_small.setFixedWidth(20)
        self.toolbar.addWidget(spacer_small)

        self.toolbar.addWidget(self.btn_convert)
        self.toolbar.addWidget(self.btn_stop)

        # Espaçador dinâmico
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)

        # Seletor de Idioma na Toolbar
        self.combo_language = QComboBox()
        self.combo_language.setMinimumWidth(160)
        self.combo_language.setStyleSheet("font-size: 12px; font-weight: bold; padding: 3px 8px;")
        for code, name in SUPPORTED_LANGUAGES.items():
            self.combo_language.addItem(f"🌐 {name}", code)
        cur_lang = i18n.get_current_language()
        lang_idx = self.combo_language.findData(cur_lang)
        if lang_idx != -1:
            self.combo_language.setCurrentIndex(lang_idx)
        self.combo_language.currentIndexChanged.connect(self._on_language_selector_changed)
        self.toolbar.addWidget(self.combo_language)

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

    def _on_language_selector_changed(self, index):
        lang_code = self.combo_language.currentData()
        if lang_code and lang_code != i18n.get_current_language():
            i18n.set_language(lang_code, persist=True)

    def create_main_page(self):
        """
        Constrói a tela principal onde fica a Tabela de Arquivos e o painel de Destino.
        """
        self.main_page = QWidget()
        main_layout = QVBoxLayout(self.main_page)
        main_layout.setContentsMargins(8, 8, 8, 8)

        format_layout = QHBoxLayout()
        self.lbl_format = QLabel(tr("lbl_format"))
        self.combo_format = QComboBox()
        self.combo_format.addItems(["MP4", "MKV", "WEBM", "AVI", "MP3", "OGG", "OPUS", "WAV", "JPG", "PNG", "GIF", "BMP", "WEBP", "SRT"])
        self.combo_format.setMinimumWidth(150)
        format_layout.addWidget(self.lbl_format)
        format_layout.addWidget(self.combo_format)
        
        self.btn_clone_specs = QPushButton(tr("btn_clone_specs"))
        self.btn_clone_specs.setToolTip(tr("btn_clone_specs_tt"))
        self.btn_clone_specs.clicked.connect(self.clone_video_specs)
        format_layout.addWidget(self.btn_clone_specs)
        
        self.combo_presets = QComboBox()
        self.combo_presets.setMinimumWidth(200)
        self.combo_presets.currentIndexChanged.connect(self.on_preset_selected)

        self.btn_save_preset = QPushButton(tr("btn_save_preset"))
        self.btn_save_preset.setToolTip(tr("btn_save_preset_tt"))
        self.btn_save_preset.clicked.connect(self.save_new_preset)

        self.btn_delete_preset = QPushButton(tr("btn_delete_preset"))
        self.btn_delete_preset.setToolTip(tr("btn_delete_preset_tt"))
        self.btn_delete_preset.clicked.connect(self.delete_selected_preset)
        self.btn_delete_preset.setEnabled(False)

        self.btn_reset_all = QPushButton(tr("btn_reset_all"))
        self.btn_reset_all.setToolTip(tr("btn_reset_all_tt"))
        self.btn_reset_all.clicked.connect(self._trigger_hard_reset)

        self.lbl_presets = QLabel(tr("lbl_presets"))
        format_layout.addWidget(self.lbl_presets)
        format_layout.addWidget(self.combo_presets)
        format_layout.addWidget(self.btn_reset_all)
        format_layout.addWidget(self.btn_save_preset)
        format_layout.addWidget(self.btn_delete_preset)
        format_layout.addStretch()
        main_layout.addLayout(format_layout)

        self.table_files = QTableWidget(0, 8)
        self.table_files.setHorizontalHeaderLabels([
            tr("th_skip"), tr("th_file"), tr("th_size"), tr("th_duration"),
            tr("th_est_size"), tr("th_elapsed"), tr("th_remaining"), tr("th_progress")
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
        self.combo_exist_action.addItems([tr("exist_overwrite"), tr("exist_rename"), tr("exist_skip")])
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
        self.btn_browse_dest = QPushButton(tr("btn_browse_dest"))
        self.btn_browse_dest.clicked.connect(self.browse_destination)
        self.btn_open_dest = QPushButton(tr("btn_open_dest"))
        self.btn_open_dest.clicked.connect(self.open_destination_folder)
        
        self.lbl_dest_title = QLabel(tr("lbl_destination"))
        dest_layout.addWidget(self.lbl_dest_title)
        dest_layout.addWidget(self.combo_exist_action)
        dest_layout.addWidget(self.lbl_dest_path)
        dest_layout.addWidget(self.btn_browse_dest)
        dest_layout.addWidget(self.btn_open_dest)
        dest_layout.addStretch()
        
        self.lbl_post_action = QLabel(tr("lbl_post_action"))
        self.lbl_post_action.setStyleSheet("font-weight: bold;")
        self.combo_post_action = QComboBox()
        self.combo_post_action.addItems([
            tr("post_do_nothing"), tr("post_close_lyra"),
            tr("post_suspend_pc"), tr("post_shutdown_pc")
        ])
        dest_layout.addWidget(self.lbl_post_action)
        dest_layout.addWidget(self.combo_post_action)
        main_layout.addLayout(dest_layout)
        self.stacked_widget.addWidget(self.main_page)

    def create_advanced_page(self):
        """
        Constrói a tela de "Opções Avançadas", agrupando todas as abas de codificação:
        Áudio, Vídeo, Imagem, Legenda, Filtros e Mais.
        """
        self.advanced_page = QWidget()
        advanced_layout = QHBoxLayout(self.advanced_page)
        
        # Menu Lateral (Vertical Tabs)
        self.advanced_menu = QListWidget()
        self.advanced_menu.setFixedWidth(200)
        self.advanced_menu.setFocusPolicy(Qt.NoFocus)
        self.advanced_menu.setStyleSheet("""
            QListWidget::item { padding: 12px; font-weight: bold; border-radius: 5px; margin: 2px; }
            QListWidget::item:selected { background-color: #2D5A27; color: white; }
            QListWidget::item:hover { background-color: #3e3e3e; }
        """)
        
        self.advanced_stack = QStackedWidget()
        
        advanced_layout.addWidget(self.advanced_menu)
        advanced_layout.addWidget(self.advanced_stack)
        
        # Sincronizador Signal/Slot
        self.advanced_menu.currentRowChanged.connect(self.advanced_stack.setCurrentIndex)
        
        self.create_audio_tab()
        self.create_sync_tab()
        self.create_trim_tab()
        self.create_video_tab()
        self.create_image_tab()
        self.create_subtitle_tab()
        self.create_filters_tab()
        self.create_speed_tab()
        self.create_more_tab()
        self.create_tags_tab()
        self.create_info_tab()
        self.create_log_tab()
        
        # ✅ FIX: adiciona advanced_page ao stack UMA única vez, após todas as abas serem criadas
        self.stacked_widget.addWidget(self.advanced_page)
        
        self.advanced_menu.setCurrentRow(0)
        
        self.combo_format.currentTextChanged.connect(self.update_format_locks)
        self.update_format_locks()
        # ✅ FIX: Carregar player MPV sob demanda ao trocar de aba
        self.advanced_menu.currentRowChanged.connect(lambda _: self._load_mpv_for_current_tab())

    def add_advanced_tab(self, tab, title):
        self.advanced_menu.addItem(title)
        self.advanced_stack.addWidget(tab)

    def create_download_page(self):
        """
        Constrói a tela de "Baixar da Web", injetando o painel de URL e opções de qualidade do yt-dlp.
        """
        self.download_page = QWidget()
        layout = QVBoxLayout(self.download_page)
        layout.setContentsMargins(16, 16, 16, 16)

        self.lbl_dl_title = QLabel(tr("lbl_dl_title"))
        self.lbl_dl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #42A5F5;")
        layout.addWidget(self.lbl_dl_title)

        url_layout = QHBoxLayout()
        self.entry_dl_url = QLineEdit()
        self.entry_dl_url.setPlaceholderText(tr("ph_dl_url"))
        self.lbl_dl_url = QLabel(tr("lbl_dl_url"))
        url_layout.addWidget(self.lbl_dl_url)
        url_layout.addWidget(self.entry_dl_url)
        layout.addLayout(url_layout)

        self.group_dl_config = QGroupBox(tr("grp_dl_config"))
        self.group_dl_config.setStyleSheet("QGroupBox::title { padding-right: 40px; }") # 🔒 FIX
        config_layout = QVBoxLayout(self.group_dl_config)

        mode_layout = QHBoxLayout()
        self.combo_dl_mode = QComboBox()
        self.combo_dl_mode.addItems([tr("dl_mode_video"), tr("dl_mode_audio")])
        self.combo_dl_mode.currentIndexChanged.connect(self.toggle_dl_options)
        self.lbl_dl_mode = QLabel(tr("lbl_dl_mode"))
        mode_layout.addWidget(self.lbl_dl_mode)
        mode_layout.addWidget(self.combo_dl_mode)
        mode_layout.addStretch()
        config_layout.addLayout(mode_layout)

        self.frame_dl_video = QFrame()
        v_layout = QHBoxLayout(self.frame_dl_video)
        self.combo_dl_v_res = QComboBox()
        self.combo_dl_v_res.addItems([tr("dl_res_best"), "2160p (4K)", "1440p (QuadHD)", "1080p (FullHD)", "720p (HD)", "480p (SD)"])
        self.combo_dl_v_fmt = QComboBox()
        self.combo_dl_v_fmt.addItems(["mp4", "mkv", "webm"])
        self.lbl_dl_max_res = QLabel(tr("lbl_dl_max_res"))
        self.lbl_dl_container_fmt = QLabel(tr("lbl_dl_container_fmt"))
        v_layout.addWidget(self.lbl_dl_max_res)
        v_layout.addWidget(self.combo_dl_v_res)
        v_layout.addWidget(self.lbl_dl_container_fmt)
        v_layout.addWidget(self.combo_dl_v_fmt)
        v_layout.addStretch()
        config_layout.addWidget(self.frame_dl_video)

        self.frame_dl_audio = QFrame()
        a_layout = QHBoxLayout(self.frame_dl_audio)
        self.combo_dl_a_fmt = QComboBox()
        self.combo_dl_a_fmt.addItems(["mp3", "m4a", "opus", "wav", "flac"])
        self.combo_dl_a_bitrate = QComboBox()
        self.combo_dl_a_bitrate.addItems(["320K", "256K", "192K", "128K"])
        self.lbl_dl_audio_fmt = QLabel(tr("lbl_dl_audio_fmt"))
        self.lbl_dl_audio_quality = QLabel(tr("lbl_dl_audio_quality"))
        a_layout.addWidget(self.lbl_dl_audio_fmt)
        a_layout.addWidget(self.combo_dl_a_fmt)
        a_layout.addWidget(self.lbl_dl_audio_quality)
        a_layout.addWidget(self.combo_dl_a_bitrate)
        a_layout.addStretch()
        config_layout.addWidget(self.frame_dl_audio)
        self.frame_dl_audio.setVisible(False)
        layout.addWidget(self.group_dl_config)

        btn_dl_layout = QHBoxLayout()
        self.btn_start_dl = QPushButton(tr("btn_start_dl"))
        self.btn_start_dl.setStyleSheet("background-color: #0277BD; color: white; font-weight: bold; padding: 6px 20px;")
        self.btn_start_dl.clicked.connect(self.start_download)
        self.btn_stop_dl = QPushButton(tr("btn_stop_dl"))
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
        self.combo_audio_codec.setModel(QStandardItemModel())
        self.combo_audio_codec.addItems(["default", "copy", "aac", "libmp3lame", "libvorbis", "libopus", "pcm_s16le"])
        
        self.combo_audio_bitrate = QComboBox()
        self.combo_audio_bitrate.addItems(["default", "64 kbps", "128 kbps", "192 kbps", "256 kbps", "320 kbps"])
        self.combo_audio_bitrate.setEditable(True)
        
        self.combo_audio_freq = QComboBox()
        self.combo_audio_freq.addItems(["default", "22050 Hz", "44100 Hz", "48000 Hz"])
        
        self.combo_audio_channels = QComboBox()
        self.combo_audio_channels.addItems(["default", "1 (Mono)", "2 (Stereo)", "6 (5.1)"])
        
        self.combo_audio_track = QComboBox()
        self.combo_audio_track.addItem(tr("audio_track_default"), -1)
        self.combo_audio_track.currentIndexChanged.connect(self._on_audio_track_changed)
        
        self.chk_all_tracks = QCheckBox(tr("chk_all_tracks"))
        self.chk_all_tracks.setToolTip(tr("chk_all_tracks_tt"))
        self.chk_all_tracks.toggled.connect(lambda checked: self.combo_audio_track.setEnabled(not checked))

        self.chk_audio_drc = QCheckBox(tr("chk_audio_drc"))
        self.chk_audio_drc.setToolTip(tr("chk_audio_drc_tt"))
        self.chk_audio_drc.stateChanged.connect(self._sync_live_audio_filters)
        
        self.chk_noise_reduction = QCheckBox(tr("chk_noise_reduction"))
        self.chk_noise_reduction.setToolTip(tr("chk_noise_reduction_tt"))
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

        self.lbl_row_acodec = QLabel(tr("lbl_audio_codec"))
        self.lbl_row_atrack = QLabel(tr("lbl_audio_track"))
        self.lbl_row_abitrate = QLabel(tr("lbl_audio_bitrate"))
        self.lbl_row_afreq = QLabel(tr("lbl_audio_freq"))
        self.lbl_row_achannels = QLabel(tr("lbl_audio_channels"))
        self.lbl_row_avolume = QLabel(tr("lbl_audio_volume"))

        layout.addRow(self.lbl_row_acodec, self.combo_audio_codec)
        layout.addRow(self.lbl_row_atrack, self.combo_audio_track)
        layout.addRow(self.lbl_row_abitrate, self.combo_audio_bitrate)
        layout.addRow(self.lbl_row_afreq, self.combo_audio_freq)
        layout.addRow(self.lbl_row_achannels, self.combo_audio_channels)
        layout.addRow("", self.chk_all_tracks)
        layout.addRow("", self.chk_audio_drc)
        layout.addRow("", self.chk_noise_reduction)
        layout.addRow(self.lbl_row_avolume, vol_layout)

        self.group_external_audio = QGroupBox(tr("grp_external_audio"))
        self.group_external_audio.setStyleSheet("QGroupBox::title { padding-right: 40px; }")
        ext_audio_layout = QVBoxLayout(self.group_external_audio)
        self.list_external_audios = QListWidget()
        self.list_external_audios.setFixedHeight(60)
        
        btn_ext_audio_layout = QHBoxLayout()
        self.btn_add_audio = QPushButton(tr("btn_add"))
        self.btn_add_audio.clicked.connect(self.browse_audio)
        self.btn_rem_audio = QPushButton(tr("btn_remove"))
        self.btn_rem_audio.clicked.connect(lambda: self.list_external_audios.takeItem(self.list_external_audios.currentRow()))
        self.btn_clear_audio = QPushButton(tr("btn_clear"))
        self.btn_clear_audio.clicked.connect(self.list_external_audios.clear)
        
        btn_ext_audio_layout.addWidget(self.btn_add_audio)
        btn_ext_audio_layout.addWidget(self.btn_rem_audio)
        btn_ext_audio_layout.addWidget(self.btn_clear_audio)
        
        ext_audio_layout.addWidget(self.list_external_audios)
        ext_audio_layout.addLayout(btn_ext_audio_layout)
        
        layout.addRow(self.group_external_audio)
        self.add_advanced_tab(tab, tr("tab_audio"))

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
        
        self.btn_sync_play = QPushButton(tr("btn_play_pause"))
        try:
            self.btn_sync_play.clicked.connect(lambda: self.mpv_widget.pause(not self.mpv_widget.mpv.pause))
        except Exception:
            pass
        
        self.lbl_sync_delay = QLabel(tr("lbl_audio_delay"))
        controls_layout.addWidget(self.lbl_sync_delay)
        controls_layout.addWidget(self.slider_audio_sync)
        controls_layout.addWidget(self.spin_audio_sync)
        controls_layout.addWidget(self.btn_sync_play)
        
        layout.addLayout(controls_layout)
        self.add_advanced_tab(tab, tr("tab_sync"))

    def create_trim_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.chk_enable_trim = QCheckBox(tr("chk_enable_trim"))
        self.chk_enable_trim.setToolTip(tr("chk_enable_trim_tt"))
        self.chk_enable_trim.setChecked(False)
        layout.addWidget(self.chk_enable_trim)

        self.mpv_widget_trim = MPVPlayerWidget(self)
        self.mpv_widget_trim.setMinimumHeight(300)
        layout.addWidget(self.mpv_widget_trim, 1)

        controls_layout = QHBoxLayout()

        self.time_start = QTimeEdit()
        self.time_start.setDisplayFormat("HH:mm:ss.zzz")
        self.btn_mark_start = QPushButton(tr("btn_mark_start"))

        self.time_end = QTimeEdit()
        self.time_end.setDisplayFormat("HH:mm:ss.zzz")
        self.btn_mark_end = QPushButton(tr("btn_mark_end"))

        def set_time_from_mpv(time_edit):
            if hasattr(self.mpv_widget_trim, 'mpv') and self.mpv_widget_trim.mpv:
                pos = self.mpv_widget_trim.mpv.time_pos
                if pos is not None:
                    ms = int(pos * 1000)
                    time_edit.setTime(QTime(0, 0).addMSecs(ms))

        self.btn_mark_start.clicked.connect(lambda: set_time_from_mpv(self.time_start))
        self.btn_mark_end.clicked.connect(lambda: set_time_from_mpv(self.time_end))

        self.lbl_trim_from = QLabel(tr("lbl_trim_from"))
        self.lbl_trim_to = QLabel(tr("lbl_trim_to"))

        controls_layout.addWidget(self.lbl_trim_from)
        controls_layout.addWidget(self.time_start)
        controls_layout.addWidget(self.btn_mark_start)
        controls_layout.addStretch()
        controls_layout.addWidget(self.lbl_trim_to)
        controls_layout.addWidget(self.time_end)
        controls_layout.addWidget(self.btn_mark_end)

        layout.addLayout(controls_layout)
        self.add_advanced_tab(tab, tr("tab_trim"))

    def create_video_tab(self):
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        
        # 1. Configurações Básicas
        self.grp_basic = QGroupBox(tr("grp_basic_settings"))
        basic_layout = QFormLayout(self.grp_basic)
        
        self.combo_video_codec = QComboBox()
        self.combo_video_codec.setModel(QStandardItemModel())
        self.combo_video_codec.addItems(["default", "copy", "libx264", "libx265", "h264_nvenc", "h.265 nvenc", "mpeg4", "libvpx-vp9", "libvpx-vp8"])
        
        self.combo_video_fps = QComboBox()
        self.combo_video_fps.addItems(["default", "23.976", "24", "25", "29.97", "30", "60"])
        
        fps_mode_layout = QHBoxLayout()
        self.radio_vfr = QRadioButton(tr("radio_vfr"))
        self.radio_cfr = QRadioButton(tr("radio_cfr"))
        self.radio_vfr.setChecked(True)
        fps_mode_layout.addWidget(self.radio_vfr)
        fps_mode_layout.addWidget(self.radio_cfr)
        
        self.combo_video_size = QComboBox()
        self.combo_video_size.addItems(["default", "640x480", "854x480 (480p Wide)", "1280x720 (720p)", "1920x1080 (1080p)", "2560x1440 (QuadHD)", "3840x2160 (4K)"])
        self.combo_video_size.setEditable(True)
        
        self.combo_video_ratio = QComboBox()
        self.combo_video_ratio.addItems(["default", "4:3", "16:9", "21:9"])

        self.lbl_vcodec = QLabel(tr("lbl_video_codec"))
        self.lbl_vfps = QLabel(tr("lbl_video_fps"))
        self.lbl_vsize = QLabel(tr("lbl_video_size"))
        self.lbl_vratio = QLabel(tr("lbl_video_ratio"))

        basic_layout.addRow(self.lbl_vcodec, self.combo_video_codec)
        basic_layout.addRow(self.lbl_vfps, self.combo_video_fps)
        basic_layout.addRow("", fps_mode_layout)
        basic_layout.addRow(self.lbl_vsize, self.combo_video_size)
        basic_layout.addRow(self.lbl_vratio, self.combo_video_ratio)
        main_layout.addWidget(self.grp_basic)
        
        # 2. Qualidade
        self.grp_quality = QGroupBox(tr("grp_quality"))
        quality_layout = QFormLayout(self.grp_quality)
        
        self.chk_crf = QCheckBox(tr("chk_crf"))
        self.chk_crf.setToolTip(tr("chk_crf_tt"))
        self.chk_crf.setChecked(True)
        
        self.slider_crf = QSlider(Qt.Horizontal)
        self.slider_crf.setRange(0, 51)
        self.slider_crf.setValue(23)
        self.lbl_crf_val = QLabel("23")
        self.slider_crf.valueChanged.connect(lambda v: self.lbl_crf_val.setText(str(v)))
        
        crf_layout = QHBoxLayout()
        crf_layout.addWidget(self.chk_crf)
        crf_layout.addWidget(self.slider_crf)
        crf_layout.addWidget(self.lbl_crf_val)
        
        self.combo_video_bitrate = QComboBox()
        self.combo_video_bitrate.addItems(["default", "800", "1200", "2500", "5000", "8000"])
        self.combo_video_bitrate.setEditable(True)
        
        self.lbl_vbitrate = QLabel(tr("lbl_video_bitrate"))
        bitrate_layout = QHBoxLayout()
        bitrate_layout.addWidget(self.lbl_vbitrate)
        bitrate_layout.addWidget(self.combo_video_bitrate)
        
        self.chk_2pass = QCheckBox(tr("chk_2pass"))
        self.chk_2pass.setToolTip(tr("chk_2pass_tt"))
        self.chk_turbo_first_pass = QCheckBox(tr("chk_turbo_first_pass"))
        self.chk_turbo_first_pass.setToolTip(tr("chk_turbo_first_pass_tt"))
        self.chk_turbo_first_pass.setEnabled(False)
        
        self.chk_2pass.toggled.connect(self.chk_turbo_first_pass.setEnabled)
        
        bitrate_opts_layout = QHBoxLayout()
        bitrate_opts_layout.addWidget(self.chk_2pass)
        bitrate_opts_layout.addWidget(self.chk_turbo_first_pass)
        
        quality_layout.addRow("", crf_layout)
        quality_layout.addRow("", bitrate_layout)
        quality_layout.addRow("", bitrate_opts_layout)
        main_layout.addWidget(self.grp_quality)
        
        # 3. Opções Avançadas de Encoder
        self.grp_enc = QGroupBox(tr("grp_encoder_opt"))
        enc_layout = QFormLayout(self.grp_enc)
        
        self.combo_color_range = QComboBox()
        self.combo_color_range.addItems(["Auto", "Limited", "Full"])
        
        self.combo_preset = QComboBox()
        self.combo_preset.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow", "placebo"])
        self.combo_preset.setCurrentText("medium")
        
        self.combo_tune = QComboBox()
        self.combo_tune.addItems(["none", "film", "animation", "grain", "stillimage", "psnr", "ssim", "fastdecode", "zerolatency"])
        
        self.combo_profile = QComboBox()
        self.combo_profile.addItems(["auto", "baseline", "main", "high", "high10", "high422", "high444"])
        
        self.combo_level = QComboBox()
        self.combo_level.addItems(["auto", "3.0", "3.1", "4.0", "4.1", "4.2", "5.0", "5.1", "5.2"])
        
        self.chk_fast_decode = QCheckBox(tr("chk_fast_decode"))
        self.chk_fast_decode.setToolTip(tr("chk_fast_decode_tt"))
        
        self.entry_x264_opts = QLineEdit()
        self.entry_x264_opts.setPlaceholderText(tr("ph_x264_opts"))
        
        self.lbl_color_range = QLabel(tr("lbl_color_range"))
        self.lbl_preset = QLabel(tr("lbl_preset"))
        self.lbl_tune = QLabel(tr("lbl_tune"))
        self.lbl_profile = QLabel(tr("lbl_profile"))
        self.lbl_level = QLabel(tr("lbl_level"))
        self.lbl_extra_opts = QLabel(tr("lbl_extra_opts"))

        enc_layout.addRow(self.lbl_color_range, self.combo_color_range)
        enc_layout.addRow(self.lbl_preset, self.combo_preset)
        enc_layout.addRow(self.lbl_tune, self.combo_tune)
        enc_layout.addRow(self.lbl_profile, self.combo_profile)
        enc_layout.addRow(self.lbl_level, self.combo_level)
        enc_layout.addRow("", self.chk_fast_decode)
        enc_layout.addRow(self.lbl_extra_opts, self.entry_x264_opts)
        
        main_layout.addWidget(self.grp_enc)

        self.chk_video_only = QCheckBox(tr("chk_video_only"))
        self.chk_video_only.setToolTip(tr("chk_video_only_tt"))
        self.chk_bad_index = QCheckBox(tr("chk_bad_index"))
        self.chk_bad_index.setToolTip(tr("chk_bad_index_tt"))
        main_layout.addWidget(self.chk_video_only)
        main_layout.addWidget(self.chk_bad_index)
        
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

        self.add_advanced_tab(tab, tr("tab_video"))

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
                        
        if fmt == "WEBM":
            vcodec = self.combo_video_codec.currentText()
            if vcodec not in ["default", "copy", "libvpx-vp9", "libvpx-vp8"]:
                idx = self.combo_video_codec.findText("libvpx-vp9")
                if idx != -1: self.combo_video_codec.setCurrentIndex(idx)
                
            acodec = self.combo_audio_codec.currentText()
            if acodec not in ["default", "copy", "libvorbis", "libopus"]:
                idx = self.combo_audio_codec.findText("libopus")
                if idx != -1: self.combo_audio_codec.setCurrentIndex(idx)

    def create_image_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        self.combo_img_size = QComboBox()
        self.combo_img_size.addItems(["default", "800x600", "1024x768", "1280x720", "1920x1080", "2560x1440", "3840x2160"])
        self.combo_img_size.setEditable(True)

        self.slider_img_quality = QSlider(Qt.Horizontal)
        self.slider_img_quality.setRange(1, 31)
        self.slider_img_quality.setValue(2)
        self.lbl_img_quality_val = QLabel(f"2 ({tr('img_quality_max')})")

        def update_img_label(v):
            if v <= 5: text = f"{v} ({tr('img_quality_max')})"
            elif v <= 15: text = f"{v} ({tr('img_quality_good')})"
            elif v <= 25: text = f"{v} ({tr('img_quality_med')})"
            else: text = f"{v} ({tr('img_quality_low')})"
            self.lbl_img_quality_val.setText(text)

        self.slider_img_quality.valueChanged.connect(update_img_label)
        img_quality_layout = QHBoxLayout()
        img_quality_layout.addWidget(self.slider_img_quality)
        img_quality_layout.addWidget(self.lbl_img_quality_val)

        self.lbl_img_size = QLabel(tr("lbl_img_size"))
        self.lbl_img_quality = QLabel(tr("lbl_img_quality"))

        layout.addRow(self.lbl_img_size, self.combo_img_size)
        layout.addRow(self.lbl_img_quality, img_quality_layout)
        self.add_advanced_tab(tab, tr("tab_image"))

    def create_subtitle_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.group_sub_file = QGroupBox(tr("grp_sub_selection"))
        self.group_sub_file.setMinimumWidth(450)
        self.group_sub_file.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.group_sub_file.setStyleSheet("QGroupBox::title { padding-right: 40px; }") # 🔒 FIX

        file_layout = QVBoxLayout(self.group_sub_file)
        self.list_external_subs = QListWidget()
        self.list_external_subs.setFixedHeight(60)
        
        btn_ext_sub_layout = QHBoxLayout()
        self.btn_add_sub = QPushButton(tr("btn_add"))
        self.btn_add_sub.clicked.connect(self.browse_subtitle)
        self.btn_rem_sub = QPushButton(tr("btn_remove"))
        self.btn_rem_sub.clicked.connect(lambda: self.list_external_subs.takeItem(self.list_external_subs.currentRow()))
        self.btn_clear_sub = QPushButton(tr("btn_clear"))
        self.btn_clear_sub.clicked.connect(self.list_external_subs.clear)
        
        btn_ext_sub_layout.addWidget(self.btn_add_sub)
        btn_ext_sub_layout.addWidget(self.btn_rem_sub)
        btn_ext_sub_layout.addWidget(self.btn_clear_sub)
        
        file_layout.addWidget(self.list_external_subs)
        file_layout.addLayout(btn_ext_sub_layout)

        self.group_sub_mode = QGroupBox(tr("grp_sub_mode"))
        self.group_sub_mode.setStyleSheet("QGroupBox::title { padding-right: 40px; }") # 🔒 FIX
        mode_layout = QFormLayout(self.group_sub_mode)
        self.combo_sub_mode = QComboBox()
        self.combo_sub_mode.addItems([tr("sub_mode_softsub"), tr("sub_mode_hardsub")])
        self.lbl_sub_render_type = QLabel(tr("lbl_sub_render_type"))
        mode_layout.addRow(self.lbl_sub_render_type, self.combo_sub_mode)

        layout.addWidget(self.group_sub_file)
        layout.addWidget(self.group_sub_mode)

        self.group_sub_extract = QGroupBox(tr("grp_sub_extract"))
        self.group_sub_extract.setStyleSheet("QGroupBox::title { padding-right: 40px; }")
        extract_layout = QFormLayout(self.group_sub_extract)
        self.combo_sub_extract_track = QComboBox()
        self.combo_sub_extract_track.addItems([
            tr("sub_track_1_default"),
            tr("sub_track_n", n=2),
            tr("sub_track_n", n=3),
            tr("sub_track_n", n=4)
        ])
        self.lbl_sub_extract_track = QLabel(tr("lbl_sub_extract_track"))
        extract_layout.addRow(self.lbl_sub_extract_track, self.combo_sub_extract_track)
        self.extract_note = QLabel(tr("sub_extract_note"))
        self.extract_note.setStyleSheet("color: white;")
        extract_layout.addRow(self.extract_note)
        layout.addWidget(self.group_sub_extract)

        self.group_sub_remove = QGroupBox(tr("grp_sub_remove"))
        self.group_sub_remove.setStyleSheet("QGroupBox::title { padding-right: 40px; }")
        remove_layout = QVBoxLayout(self.group_sub_remove)
        self.list_sub_remove_tracks = QListWidget()
        self.list_sub_remove_tracks.setFixedHeight(80)
        remove_layout.addWidget(self.list_sub_remove_tracks)
        layout.addWidget(self.group_sub_remove)

        layout.addStretch()
        self.add_advanced_tab(tab, tr("tab_subtitles"))

    def browse_subtitle(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, tr("dialog_select_subs"), os.path.expanduser("~"),
            "Arquivos de Legenda (*.srt *.ass *.vtt);;Todos os Arquivos (*.*)"
        )
        if paths:
            for path in paths:
                self.list_external_subs.addItem(path)

    def browse_audio(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, tr("dialog_select_audios"), os.path.expanduser("~"),
            "Arquivos de Áudio (*.mp3 *.wav *.aac *.flac *.ogg *.m4a);;Todos os Arquivos (*.*)"
        )
        if paths:
            for path in paths:
                self.list_external_audios.addItem(path)

    def create_filters_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.basic_filter_group = QGroupBox(tr("grp_basic_filters"))
        self.basic_filter_group.setStyleSheet("QGroupBox::title { padding-right: 40px; }") # 🔒 FIX
        basic_layout = QFormLayout(self.basic_filter_group)
        self.combo_rotate = QComboBox()
        self.combo_rotate.addItems([
            tr("rotate_normal"), tr("rotate_90_cw"), tr("rotate_90_ccw"),
            tr("rotate_180"), tr("rotate_hflip"), tr("rotate_vflip")
        ])
        self.chk_deinterlace = QCheckBox(tr("chk_deinterlace"))
        self.chk_deinterlace.setToolTip(tr("chk_deinterlace_tt"))
        self.lbl_rotate = QLabel(tr("lbl_rotation"))
        basic_layout.addRow(self.lbl_rotate, self.combo_rotate)
        basic_layout.addRow("", self.chk_deinterlace)
        layout.addWidget(self.basic_filter_group)

        self.fade_group = QGroupBox(tr("grp_fade"))
        self.fade_group.setStyleSheet("QGroupBox::title { padding-right: 40px; }") # 🔒 FIX
        fade_layout = QFormLayout(self.fade_group)
        self.spin_fade_duration = QSpinBox()
        self.spin_fade_duration.setRange(0, 20)
        self.combo_fade_pos = QComboBox()
        self.combo_fade_pos.addItems([
            tr("fade_pos_none"), tr("fade_pos_start"), tr("fade_pos_end"), tr("fade_pos_both")
        ])
        self.combo_fade_type = QComboBox()
        self.combo_fade_type.addItems([
            tr("fade_type_both"), tr("fade_type_video"), tr("fade_type_audio")
        ])
        self.lbl_fade_dur = QLabel(tr("lbl_duration"))
        self.lbl_fade_pos = QLabel(tr("lbl_position"))
        self.lbl_fade_type = QLabel(tr("lbl_type"))
        fade_layout.addRow(self.lbl_fade_dur, self.spin_fade_duration)
        fade_layout.addRow(self.lbl_fade_pos, self.combo_fade_pos)
        fade_layout.addRow(self.lbl_fade_type, self.combo_fade_type)
        layout.addWidget(self.fade_group)

        self.group_crop = QGroupBox(tr("grp_crop"))
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
        
        self.lbl_crop_top = QLabel(tr("lbl_crop_top"))
        self.lbl_crop_bottom = QLabel(tr("lbl_crop_bottom"))
        self.lbl_crop_left = QLabel(tr("lbl_crop_left"))
        self.lbl_crop_right = QLabel(tr("lbl_crop_right"))

        crop_layout.addWidget(self.lbl_crop_top)
        crop_layout.addWidget(self.spin_crop_top)
        crop_layout.addWidget(self.lbl_crop_bottom)
        crop_layout.addWidget(self.spin_crop_bottom)
        crop_layout.addWidget(self.lbl_crop_left)
        crop_layout.addWidget(self.spin_crop_left)
        crop_layout.addWidget(self.lbl_crop_right)
        crop_layout.addWidget(self.spin_crop_right)
        self.btn_auto_crop = QPushButton(tr("btn_auto_crop"))
        self.btn_auto_crop.clicked.connect(self.run_auto_crop)
        crop_main_layout.addLayout(crop_layout)
        crop_main_layout.addWidget(self.btn_auto_crop)
        layout.addWidget(self.group_crop)

        self.group_pad = QGroupBox(tr("grp_pad"))
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
        
        self.lbl_pad_top = QLabel(tr("lbl_crop_top"))
        self.lbl_pad_bottom = QLabel(tr("lbl_crop_bottom"))
        self.lbl_pad_left = QLabel(tr("lbl_crop_left"))
        self.lbl_pad_right = QLabel(tr("lbl_crop_right"))

        pad_layout.addWidget(self.lbl_pad_top)
        pad_layout.addWidget(self.spin_pad_top)
        pad_layout.addWidget(self.lbl_pad_bottom)
        pad_layout.addWidget(self.spin_pad_bottom)
        pad_layout.addWidget(self.lbl_pad_left)
        pad_layout.addWidget(self.spin_pad_left)
        pad_layout.addWidget(self.lbl_pad_right)
        pad_layout.addWidget(self.spin_pad_right)
        layout.addWidget(self.group_pad)

        self.group_watermark = QGroupBox(tr("grp_watermark"))
        self.group_watermark.setCheckable(True)
        self.group_watermark.setChecked(False)
        self.group_watermark.setStyleSheet("QGroupBox::title { padding-right: 40px; }")
        wm_layout = QFormLayout(self.group_watermark)
        
        self.lbl_wm_image = QLabel(tr("lbl_no_image_selected"))
        self.lbl_wm_image.setWordWrap(True)
        self.lbl_wm_image.setStyleSheet("background-color: black; border: 1px dashed gray; padding: 5px;")
        
        wm_btn_layout = QHBoxLayout()
        self.btn_wm_select = QPushButton(tr("btn_choose_image"))
        self.btn_wm_select.clicked.connect(self.select_watermark_image)
        self.btn_wm_clear = QPushButton(tr("btn_clear_wm"))
        self.btn_wm_clear.clicked.connect(self.clear_watermark_image)
        wm_btn_layout.addWidget(self.btn_wm_select)
        wm_btn_layout.addWidget(self.btn_wm_clear)
        
        self.combo_wm_pos = QComboBox()
        self.combo_wm_pos.addItems([
            tr("wm_pos_br"), tr("wm_pos_bl"), tr("wm_pos_tr"), tr("wm_pos_tl"), tr("wm_pos_center")
        ])
        
        self.spin_wm_size = QSpinBox()
        self.spin_wm_size.setRange(1, 200)
        self.spin_wm_size.setValue(100)
        self.spin_wm_size.setSuffix("%")
        
        self.spin_wm_opacity = QSpinBox()
        self.spin_wm_opacity.setRange(0, 100)
        self.spin_wm_opacity.setValue(100)
        self.spin_wm_opacity.setSuffix("%")
        
        self.watermark_path = ""
        
        self.lbl_wm_pos = QLabel(tr("lbl_position"))
        self.lbl_wm_size = QLabel(tr("lbl_size"))
        self.lbl_wm_opacity = QLabel(tr("lbl_opacity"))

        wm_layout.addRow(self.lbl_wm_image)
        wm_layout.addRow(wm_btn_layout)
        wm_layout.addRow(self.lbl_wm_pos, self.combo_wm_pos)
        wm_layout.addRow(self.lbl_wm_size, self.spin_wm_size)
        wm_layout.addRow(self.lbl_wm_opacity, self.spin_wm_opacity)
        
        self.group_watermark.toggled.connect(self.update_player_watermark)
        self.combo_wm_pos.currentIndexChanged.connect(self.update_player_watermark)
        self.spin_wm_size.valueChanged.connect(self.update_player_watermark)
        self.spin_wm_opacity.valueChanged.connect(self.update_player_watermark)
        
        layout.addWidget(self.group_watermark)
        layout.addStretch()
        self.add_advanced_tab(tab, tr("tab_filters"))

    def select_watermark_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, tr("dialog_choose_wm"), "", "Imagens (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            self.lbl_wm_image.setText(file_path)
            self.watermark_path = file_path
            self.update_player_watermark()

    def clear_watermark_image(self):
        self.lbl_wm_image.setText(tr("lbl_no_image_selected"))
        self.watermark_path = ""
        self.update_player_watermark()

    def update_player_watermark(self):
        if hasattr(self, 'mpv_widget'):
            wm_pos_tokens = ["bottom_right", "bottom_left", "top_right", "top_left", "center"]
            idx = self.combo_wm_pos.currentIndex() if hasattr(self, 'combo_wm_pos') else 0
            pos_token = wm_pos_tokens[idx] if 0 <= idx < len(wm_pos_tokens) else "bottom_right"

            watermark_options = {
                "enabled": getattr(self, 'group_watermark', None) and self.group_watermark.isChecked(),
                "image_path": getattr(self, 'watermark_path', ""),
                "position": pos_token,
                "size": self.spin_wm_size.value(),
                "opacity": self.spin_wm_opacity.value()
            }
            self.mpv_widget.update_video_filters(watermark_options)

    def run_auto_crop(self):
        selected = self.table_files.selectedItems()
        if not selected:
            QMessageBox.warning(self, tr("dialog_warning"), tr("auto_crop_select_file"))
            return
            
        row = selected[0].row()
        file_path = self.table_files.item(row, 1).toolTip()
        
        if not os.path.exists(file_path):
            return
            
        self.btn_auto_crop.setText(tr("btn_auto_crop_analyzing"))
        self.btn_auto_crop.setEnabled(False)
        QApplication.processEvents() 
        
        crop_data = self.engine.detect_crop(file_path)
        
        self.btn_auto_crop.setText(tr("btn_auto_crop"))
        self.btn_auto_crop.setEnabled(True)
        
        if crop_data:
            t, b, l, r = crop_data["t"], crop_data["b"], crop_data["l"], crop_data["r"]
            if t == 0 and b == 0 and l == 0 and r == 0:
                QMessageBox.information(self, tr("dialog_auto_crop_title"), tr("auto_crop_no_bars"))
            else:
                self.spin_crop_top.setValue(t)
                self.spin_crop_bottom.setValue(b)
                self.spin_crop_left.setValue(l)
                self.spin_crop_right.setValue(r)
                self.group_crop.setChecked(True)
                QMessageBox.information(self, tr("dialog_auto_crop_title"), tr("auto_crop_success", t=t, b=b, l=l, r=r))
        else:
            QMessageBox.warning(self, tr("dialog_error"), tr("auto_crop_error"))

    def create_speed_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.lbl_speed_info = QLabel(tr("lbl_speed_info"))
        self.lbl_speed_info.setStyleSheet("color: white; font-size: 11px;")
        layout.addWidget(self.lbl_speed_info)

        # Preset buttons
        presets_layout = QHBoxLayout()
        speeds = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 4.0]
        for s in speeds:
            btn = QPushButton(f"{s}x")
            btn.clicked.connect(lambda checked=False, val=s: self.spin_speed.setValue(val))
            presets_layout.addWidget(btn)
        layout.addLayout(presets_layout)

        # Fine tuning
        fine_layout = QFormLayout()
        self.spin_speed = QDoubleSpinBox()
        self.spin_speed.setRange(0.10, 10.00)
        self.spin_speed.setSingleStep(0.1)
        self.spin_speed.setValue(1.0)
        self.spin_speed.valueChanged.connect(self.update_speed_live)
        self.lbl_exact_speed = QLabel(tr("lbl_exact_speed"))
        fine_layout.addRow(self.lbl_exact_speed, self.spin_speed)

        # Pitch Preservation
        self.chk_pitch = QCheckBox(tr("chk_preserve_pitch"))
        self.chk_pitch.setToolTip(tr("chk_preserve_pitch_tt"))
        self.chk_pitch.setChecked(True)
        self.chk_pitch.toggled.connect(self.update_speed_live)
        fine_layout.addRow("", self.chk_pitch)

        layout.addLayout(fine_layout)
        layout.addStretch()

        self.add_advanced_tab(tab, tr("tab_speed"))

    def update_speed_live(self):
        speed = self.spin_speed.value()
        preserve = self.chk_pitch.isChecked()
        
        for widget in [getattr(self, 'mpv_widget', None), getattr(self, 'mpv_widget_trim', None)]:
            if widget and hasattr(widget, 'mpv') and widget.mpv:
                widget.mpv.speed = speed
                try:
                    widget.mpv.audio_pitch_correction = preserve
                except:
                    pass

    def create_more_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)

        max_threads = os.cpu_count() or 4
        self.slider_threads = QSlider(Qt.Horizontal)
        self.slider_threads.setRange(0, max_threads)
        self.slider_threads.setValue(0)
        self.lbl_threads_val = QLabel(tr("threads_auto"))

        def update_threads_label(v):
            if v == 0: self.lbl_threads_val.setText(tr("threads_auto"))
            elif v == 1: self.lbl_threads_val.setText(tr("threads_1"))
            else: self.lbl_threads_val.setText(tr("threads_n", n=v))

        self.slider_threads.valueChanged.connect(update_threads_label)
        threads_layout = QHBoxLayout()
        threads_layout.addWidget(self.slider_threads)
        threads_layout.addWidget(self.lbl_threads_val)

        self.entry_extra_args = QLineEdit()
        self.entry_extra_args.setPlaceholderText(tr("ph_extra_ffmpeg_args"))
        self.entry_ffmpeg_path = QLineEdit("ffmpeg")

        self.lbl_threads_title = QLabel(tr("lbl_cpu_threads"))
        self.lbl_extra_args_title = QLabel(tr("lbl_extra_ffmpeg_args"))
        self.lbl_ffmpeg_path_title = QLabel(tr("lbl_converter_exec"))

        layout.addRow(self.lbl_threads_title, threads_layout)
        layout.addRow(self.lbl_extra_args_title, self.entry_extra_args)
        layout.addRow(self.lbl_ffmpeg_path_title, self.entry_ffmpeg_path)

        self.add_advanced_tab(tab, tr("tab_more"))

    def create_tags_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)

        self.lbl_tags_warning = QLabel(tr("lbl_tags_warning"))
        self.lbl_tags_warning.setStyleSheet("color: white; font-size: 11px;")
        self.lbl_tags_warning.setWordWrap(True)
        layout.addRow(self.lbl_tags_warning)
        spacer = QLabel("")
        spacer.setFixedHeight(15)
        layout.addRow(spacer)

        self.entry_meta_title = QLineEdit()
        self.entry_meta_title.setPlaceholderText(tr("ph_meta_title"))
        self.entry_meta_title.setToolTip(tr("tt_meta_title"))
        
        self.entry_meta_artist = QLineEdit()
        self.entry_meta_artist.setPlaceholderText(tr("ph_meta_artist"))
        
        self.entry_meta_album = QLineEdit()
        self.entry_meta_album.setPlaceholderText(tr("ph_meta_album"))
        
        self.entry_meta_year = QLineEdit()
        self.entry_meta_year.setPlaceholderText(tr("ph_meta_year"))
        
        self.entry_meta_genre = QLineEdit()
        self.entry_meta_genre.setPlaceholderText(tr("ph_meta_genre"))
        
        self.entry_meta_comment = QLineEdit()
        self.entry_meta_comment.setPlaceholderText(tr("ph_meta_comment"))

        self.meta_cover_path = ""
        self.lbl_cover_preview = QLabel(tr("lbl_cover_none"))
        self.lbl_cover_preview.setFixedSize(80, 80)
        self.lbl_cover_preview.setAlignment(Qt.AlignCenter)
        self.lbl_cover_preview.setStyleSheet("border: 1px solid #555;")
        self.lbl_cover_preview.setScaledContents(True)

        self.entry_cover_path = QLineEdit()
        self.entry_cover_path.setReadOnly(True)
        self.entry_cover_path.setPlaceholderText(tr("ph_no_cover"))

        self.btn_choose_cover = QPushButton(tr("btn_choose_image"))
        self.btn_choose_cover.clicked.connect(self.choose_cover_art)
        self.btn_clear_cover = QPushButton(tr("btn_clear_wm"))
        self.btn_clear_cover.clicked.connect(self.clear_cover_art)

        cover_controls_layout = QHBoxLayout()
        cover_controls_layout.addWidget(self.entry_cover_path)
        cover_controls_layout.addWidget(self.btn_choose_cover)
        cover_controls_layout.addWidget(self.btn_clear_cover)

        self.lbl_meta_title = QLabel(tr("lbl_meta_title"))
        self.lbl_meta_artist = QLabel(tr("lbl_meta_artist"))
        self.lbl_meta_album = QLabel(tr("lbl_meta_album"))
        self.lbl_meta_year = QLabel(tr("lbl_meta_year"))
        self.lbl_meta_genre = QLabel(tr("lbl_meta_genre"))
        self.lbl_meta_comment = QLabel(tr("lbl_meta_comment"))
        self.lbl_meta_cover = QLabel(tr("lbl_meta_cover"))

        layout.addRow(self.lbl_meta_title, self.entry_meta_title)
        layout.addRow(self.lbl_meta_artist, self.entry_meta_artist)
        layout.addRow(self.lbl_meta_album, self.entry_meta_album)
        layout.addRow(self.lbl_meta_year, self.entry_meta_year)
        layout.addRow(self.lbl_meta_genre, self.entry_meta_genre)
        layout.addRow(self.lbl_meta_comment, self.entry_meta_comment)
        layout.addRow(self.lbl_meta_cover, cover_controls_layout)
        layout.addRow("", self.lbl_cover_preview)

        self.add_advanced_tab(tab, tr("tab_tags"))

    def choose_cover_art(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("dialog_select_cover"), "", "Imagens (*.jpg *.jpeg *.png)"
        )
        if file_path:
            self.meta_cover_path = file_path
            self.entry_cover_path.setText(os.path.basename(file_path))
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.lbl_cover_preview.setPixmap(pixmap)
            else:
                self.lbl_cover_preview.setText(tr("lbl_cover_error"))

    def clear_cover_art(self):
        self.meta_cover_path = ""
        self.entry_cover_path.clear()
        self.lbl_cover_preview.clear()
        self.lbl_cover_preview.setText(tr("lbl_cover_none"))

    def create_log_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.text_log = QPlainTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: monospace; font-size: 11px;")
        layout.addWidget(self.text_log)
        self.add_advanced_tab(tab, tr("tab_log"))

    def create_info_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.text_media_info = QPlainTextEdit()
        self.text_media_info.setReadOnly(True)
        self.text_media_info.setStyleSheet("background-color: #2b2b2b; color: #ffeb3b; font-family: monospace; font-size: 13px;")
        layout.addWidget(self.text_media_info)
        self.add_advanced_tab(tab, tr("tab_info"))

    def _load_mpv_for_current_tab(self):
        """Carrega o player MPV correto apenas se a aba correspondente estiver ativa."""
        if not hasattr(self, '_last_selected_file') or not self._last_selected_file:
            return
        file_path = self._last_selected_file
        if not os.path.exists(file_path):
            return

        current_idx = self.advanced_menu.currentRow()

        # Índice 1 = Sincronia, Índice 2 = Cortes
        if current_idx == 1 and hasattr(self, 'mpv_widget'):
            self.mpv_widget.play(file_path)
            self.update_player_watermark()
        elif current_idx == 2 and hasattr(self, 'mpv_widget_trim'):
            self.mpv_widget_trim.play(file_path)

    def on_file_selected_for_info(self):
        selected_items = self.table_files.selectedItems()
        if not selected_items:
            self.text_media_info.clear()
            return
        
        row = selected_items[0].row()
        file_path = self.table_files.item(row, 1).toolTip()
        
        if os.path.exists(file_path):
            self._last_selected_file = file_path
            self._load_mpv_for_current_tab()
            self.text_media_info.setPlainText(tr("analyzing_media"))
            info_text = self.engine.get_human_media_info(file_path)
            self.text_media_info.setPlainText(info_text)
            
            self.combo_audio_track.blockSignals(True)
            self.combo_audio_track.clear()
            self.combo_audio_track.addItem(tr("audio_track_default"), -1)
            
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
        self.action_advanced.setText(tr("action_advanced") if is_main else (tr("action_back_to_list") if index == 1 else tr("action_advanced")))
        self.action_download.setText(tr("action_download") if is_main else (tr("action_back_to_list") if index == 2 else tr("action_download")))

    def toggle_dl_options(self):
        is_audio = self.combo_dl_mode.currentIndex() == 1
        self.frame_dl_video.setVisible(not is_audio)
        self.frame_dl_audio.setVisible(is_audio)

    def open_destination_folder(self):
        path = self.lbl_dest_path.text()
        if os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def browse_destination(self):
        path = QFileDialog.getExistingDirectory(self, tr("dialog_select_dest"), self.lbl_dest_path.text(), options=QFileDialog.ShowDirsOnly)
        if path: 
            self.lbl_dest_path.setText(path)
            self.settings.setValue("last_destination", path)

    def add_files_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, tr("dialog_add_files"), os.path.expanduser("~"))
        for path in paths: self.add_file_to_table(path)

    def add_folder_dialog(self):
        path = QFileDialog.getExistingDirectory(self, tr("dialog_add_folder"), os.path.expanduser("~"), options=QFileDialog.ShowDirsOnly)
        if path:
            for root, _, files in os.walk(path):
                for f in files: self.add_file_to_table(os.path.join(root, f))

    def add_file_to_table(self, file_path):
        if not os.path.isfile(file_path):
            return
        # ✅ FIX: Verificar se o arquivo já está na lista (insensível a maiúsculas no Windows)
        normalized_path = os.path.normcase(os.path.abspath(file_path))
        for r in range(self.table_files.rowCount()):
            existing_item = self.table_files.item(r, 1)
            if existing_item and os.path.normcase(existing_item.toolTip()) == normalized_path:
                return

        row = self.table_files.rowCount()
        self.table_files.insertRow(row)

        chk = QTableWidgetItem()
        chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        chk.setCheckState(Qt.Checked)
        name = QTableWidgetItem(os.path.basename(file_path))
        name.setToolTip(file_path)
        dur_sec = self.engine.get_media_duration(file_path)
        dur = QTableWidgetItem(self.engine.format_time(dur_sec) if dur_sec > 0 else tr("status_img_na"))
        dur.setToolTip(str(dur_sec))

        self.table_files.setItem(row, 0, chk)
        self.table_files.setItem(row, 1, name)
        self.table_files.setItem(row, 2, QTableWidgetItem(f"{os.path.getsize(file_path)/1024/1024:.2f} MB"))
        self.table_files.setItem(row, 3, dur)
        self.table_files.setItem(row, 4, QTableWidgetItem("--"))
        self.table_files.setItem(row, 5, QTableWidgetItem("--:--:--"))
        self.table_files.setItem(row, 6, QTableWidgetItem("--:--:--"))
        
        # ✅ FIX: QProgressBar visual na coluna de progresso
        _PROGRESS_STYLE = """
            QProgressBar {
                border: 1px solid #555; border-radius: 3px;
                background-color: #2d2d2d; text-align: center;
                color: white; font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1565C0, stop:1 #42A5F5);
                border-radius: 2px;
            }
        """
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat(tr("status_ready"))
        progress_bar.setStyleSheet(_PROGRESS_STYLE)
        self.table_files.setCellWidget(row, 7, progress_bar)

    def remove_selected_files(self):
        if self.is_converting: return
        for row in sorted([r.topRow() for r in self.table_files.selectedRanges()], reverse=True):
            self.table_files.removeRow(row)

    def clear_table(self):
        if not self.is_converting: self.table_files.setRowCount(0)

    def get_ui_options(self):
        fade_pos_tokens = ["none", "start", "end", "both"]
        fade_type_tokens = ["both", "video", "audio"]
        rotate_tokens = ["normal", "90_cw", "90_ccw", "180", "hflip", "vflip"]
        wm_pos_tokens = ["bottom_right", "bottom_left", "top_right", "top_left", "center"]

        rot_idx = self.combo_rotate.currentIndex() if hasattr(self, 'combo_rotate') else 0
        rot_val = rotate_tokens[rot_idx] if 0 <= rot_idx < len(rotate_tokens) else "normal"

        f_pos_idx = self.combo_fade_pos.currentIndex() if hasattr(self, 'combo_fade_pos') else 0
        f_pos_val = fade_pos_tokens[f_pos_idx] if 0 <= f_pos_idx < len(fade_pos_tokens) else "none"

        f_type_idx = self.combo_fade_type.currentIndex() if hasattr(self, 'combo_fade_type') else 0
        f_type_val = fade_type_tokens[f_type_idx] if 0 <= f_type_idx < len(fade_type_tokens) else "both"

        wm_pos_idx = self.combo_wm_pos.currentIndex() if hasattr(self, 'combo_wm_pos') else 0
        wm_pos_val = wm_pos_tokens[wm_pos_idx] if 0 <= wm_pos_idx < len(wm_pos_tokens) else "bottom_right"

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
            "rotate": rot_val,
            "deinterlace": self.chk_deinterlace.isChecked(),
            "audio_offset_ms": getattr(self, 'slider_audio_sync', None).value() if hasattr(self, 'slider_audio_sync') else 0,
            "fade_dur": self.spin_fade_duration.value(),
            "fade_pos": f_pos_val,
            "fade_type": f_type_val,
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
            "watermark": {
                "enabled": getattr(self, 'group_watermark', None) and self.group_watermark.isChecked(),
                "image_path": getattr(self, 'watermark_path', ""),
                "position": wm_pos_val,
                "size": getattr(self, 'spin_wm_size', None).value() if hasattr(self, 'spin_wm_size') else 100,
                "opacity": getattr(self, 'spin_wm_opacity', None).value() if hasattr(self, 'spin_wm_opacity') else 100
            },
            "metadata": {
                "title": getattr(self, 'entry_meta_title', None).text().strip() if hasattr(self, 'entry_meta_title') else "",
                "artist": getattr(self, 'entry_meta_artist', None).text().strip() if hasattr(self, 'entry_meta_artist') else "",
                "album": getattr(self, 'entry_meta_album', None).text().strip() if hasattr(self, 'entry_meta_album') else "",
                "year": getattr(self, 'entry_meta_year', None).text().strip() if hasattr(self, 'entry_meta_year') else "",
                "genre": getattr(self, 'entry_meta_genre', None).text().strip() if hasattr(self, 'entry_meta_genre') else "",
                "comment": getattr(self, 'entry_meta_comment', None).text().strip() if hasattr(self, 'entry_meta_comment') else "",
                "cover_path": getattr(self, 'meta_cover_path', "")
            },
            "threads": self.slider_threads.value(),
            "extra_args": self.entry_extra_args.text().strip(),
            "speed": {
                "value": getattr(self, 'spin_speed', None).value() if hasattr(self, 'spin_speed') else 1.0,
                "preserve_pitch": getattr(self, 'chk_pitch', None).isChecked() if hasattr(self, 'chk_pitch') else True
            },

            "video_advanced": {
                "fps_mode": "vfr" if getattr(self, 'radio_vfr', None) and self.radio_vfr.isChecked() else "cfr",
                "color_range": getattr(self, 'combo_color_range', None).currentText() if hasattr(self, 'combo_color_range') else "Auto",
                "preset": getattr(self, 'combo_preset', None).currentText() if hasattr(self, 'combo_preset') else "medium",
                "tune": getattr(self, 'combo_tune', None).currentText() if hasattr(self, 'combo_tune') else "none",
                "profile": getattr(self, 'combo_profile', None).currentText() if hasattr(self, 'combo_profile') else "auto",
                "level": getattr(self, 'combo_level', None).currentText() if hasattr(self, 'combo_level') else "auto",
                "fast_decode": getattr(self, 'chk_fast_decode', None).isChecked() if hasattr(self, 'chk_fast_decode') else False,
                "x264_opts": getattr(self, 'entry_x264_opts', None).text().strip() if hasattr(self, 'entry_x264_opts') else "",
                "turbo_first_pass": getattr(self, 'chk_turbo_first_pass', None).isChecked() if hasattr(self, 'chk_turbo_first_pass') else False,
                "video_only": getattr(self, 'chk_video_only', None).isChecked() if hasattr(self, 'chk_video_only') else False,
                "bad_index": getattr(self, 'chk_bad_index', None).isChecked() if hasattr(self, 'chk_bad_index') else False
            }
        }

    def start_conversion_queue(self):
        if self.is_converting or self.table_files.rowCount() == 0: return
        
        # 🔒 SNAPSHOT DA SESSÃO: Congela as opções da UI no momento do clique para toda a fila
        self.current_batch_options = self.get_ui_options()
        
        # Reseta o status de arquivos marcados que já foram concluídos ou deram erro
        for row in range(self.table_files.rowCount()):
            if self.table_files.item(row, 0).checkState() == Qt.Checked:
                bar = self.table_files.cellWidget(row, 7)
                if isinstance(bar, QProgressBar):
                    bar.setValue(0)
                    bar.setFormat(tr("status_ready"))
                    bar.setStyleSheet("""
                        QProgressBar { border:1px solid #555; border-radius:3px;
                            background-color:#2d2d2d; text-align:center; color:white; font-size:11px; }
                        QProgressBar::chunk { background-color:qlineargradient(
                            x1:0,y1:0,x2:1,y2:0, stop:0 #1565C0, stop:1 #42A5F5);
                            border-radius:2px; }
                    """)
                    self.table_files.item(row, 4).setText("--")
                    self.table_files.item(row, 5).setText("--:--:--")
                    self.table_files.item(row, 6).setText("--:--:--")
                else:
                    current_status = self.table_files.item(row, 7)
                    if current_status:
                        current_status.setText(tr("status_ready"))
                        self.table_files.item(row, 4).setText("--")
                        self.table_files.item(row, 5).setText("--:--:--")
                        self.table_files.item(row, 6).setText("--:--:--")

        self.is_converting = True
        self.btn_convert.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.text_log.clear()
        self.process_next_file()

    def stop_conversion_queue(self):
        if hasattr(self, 'engine'): self.engine.stop_all()
        self.is_converting = False
        self.btn_convert.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def process_next_file(self):
        if not self.is_converting: return
        row_to_process = -1
        for row in range(self.table_files.rowCount()):
            if self.table_files.item(row, 0).checkState() == Qt.Checked:
                bar = self.table_files.cellWidget(row, 7)
                status = bar.format() if isinstance(bar, QProgressBar) else (self.table_files.item(row, 7).text() if self.table_files.item(row, 7) else "")
                if status in (tr("status_ready"), "Pronto", "Ready", "Listo", "Prêt", "Bereit"):
                    row_to_process = row
                    break

        if row_to_process == -1:
            if hasattr(self, 'current_batch_options'):
                self.current_batch_options = None
            self.stop_conversion_queue()
            self.text_log.appendPlainText("\n--- FILA DE CONVERSÃO CONCLUÍDA ---\n")
            self._play_done_sound()
            self._show_tray_message("Lyra", tr("tray_conv_done"), QSystemTrayIcon.Information, 5000)
            
            post_idx = self.combo_post_action.currentIndex()
            if post_idx == 1:
                QApplication.quit()
            elif post_idx == 2:
                self.engine.suspend_pc()
            elif post_idx == 3:
                self.engine.shutdown_pc()
            else:
                if self.isActiveWindow(): QMessageBox.information(self, tr("dialog_warning"), tr("conversion_completed_msg"))
            
            return

        ui_opts = getattr(self, 'current_batch_options', self.get_ui_options())
        input_file = self.table_files.item(row_to_process, 1).toolTip()
        try:
            duration = float(self.table_files.item(row_to_process, 3).toolTip())
        except (ValueError, TypeError):
            duration = 0.0
        
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        ext = self.combo_format.currentText().lower()
        
        checked_count = sum(1 for r in range(self.table_files.rowCount()) if self.table_files.item(r, 0).checkState() == Qt.Checked)
        if checked_count == 1 and ui_opts["metadata"]["title"]:
            base_name = ui_opts["metadata"]["title"]
            
        output_file = os.path.join(self.lbl_dest_path.text(), f"{base_name}.{ext}")

        if os.path.exists(output_file):
            action_idx = self.combo_exist_action.currentIndex()
            if action_idx == 2: # Skip
                self.table_files.setItem(row_to_process, 7, QTableWidgetItem(tr("status_skipped")))
                self.text_log.appendPlainText(f"\n[Aviso] O arquivo '{os.path.basename(output_file)}' já existe. Pulando conversão...\n")
                from PySide6.QtCore import QTimer
                QTimer.singleShot(100, self.process_next_file)
                return
            elif action_idx == 1: # Rename
                base, ext_out = os.path.splitext(output_file)
                counter = 1
                while os.path.exists(output_file):
                    output_file = f"{base}_{counter}{ext_out}"
                    counter += 1

        self.table_files.setItem(row_to_process, 7, QTableWidgetItem(tr("status_processing")))
        self.engine.start_conversion(row_to_process, input_file, output_file, duration, ui_opts)

    def update_progress_ui(self, row, progress, elapsed, rem, size, status):
        self.table_files.item(row, 5).setText(elapsed)
        self.table_files.item(row, 6).setText(rem)
        if size:
            self.table_files.item(row, 4).setText(size)
        bar = self.table_files.cellWidget(row, 7)
        if isinstance(bar, QProgressBar):
            bar.setValue(progress)
            bar.setFormat(status)

    def update_log_ui(self, text):
        self.text_log.insertPlainText(text)
        self.text_log.moveCursor(QTextCursor.End)

    def on_ffmpeg_finished(self, row, exitCode, is_download):
        self.text_log.appendPlainText(f"\n[Código de saída: {exitCode}]\n")
        bar = self.table_files.cellWidget(row, 7)
        if isinstance(bar, QProgressBar):
            if exitCode == 0:
                bar.setValue(100)
                bar.setFormat(tr("status_completed"))
                bar.setStyleSheet("""
                    QProgressBar { border:1px solid #2E7D32; border-radius:3px;
                        background-color:#1B5E20; text-align:center; color:white; font-size:11px; }
                    QProgressBar::chunk { background-color:#4CAF50; border-radius:2px; }
                """)
            else:
                bar.setValue(0)
                bar.setFormat(tr("status_error"))
                bar.setStyleSheet("""
                    QProgressBar { border:1px solid #B71C1C; border-radius:3px;
                        background-color:#4a1a1a; text-align:center; color:white; font-size:11px; }
                    QProgressBar::chunk { background-color:#EF5350; border-radius:2px; }
                """)
        else:
            status = tr("status_completed") if exitCode == 0 else tr("status_error")
            self.table_files.setItem(row, 7, QTableWidgetItem(status))
        self.process_next_file()

    def load_presets(self):
        data = self.preset_manager.load_presets()
        self.combo_presets.blockSignals(True)
        self.combo_presets.clear()
        self.combo_presets.addItem(tr("preset_default_name"))
        for name in data: self.combo_presets.addItem(f"⭐ {name}")
        self.combo_presets.setCurrentIndex(0)
        self.combo_presets.blockSignals(False)
        self.btn_delete_preset.setEnabled(False)

    def _capture_preset_state(self):
        fade_pos_tokens = ["none", "start", "end", "both"]
        fade_type_tokens = ["both", "video", "audio"]
        rotate_tokens = ["normal", "90_cw", "90_ccw", "180", "hflip", "vflip"]

        rot_idx = self.combo_rotate.currentIndex() if hasattr(self, 'combo_rotate') else 0
        rot_val = rotate_tokens[rot_idx] if 0 <= rot_idx < len(rotate_tokens) else "normal"

        f_pos_idx = self.combo_fade_pos.currentIndex() if hasattr(self, 'combo_fade_pos') else 0
        f_pos_val = fade_pos_tokens[f_pos_idx] if 0 <= f_pos_idx < len(fade_pos_tokens) else "none"

        f_type_idx = self.combo_fade_type.currentIndex() if hasattr(self, 'combo_fade_type') else 0
        f_type_val = fade_type_tokens[f_type_idx] if 0 <= f_type_idx < len(fade_type_tokens) else "both"

        return {
            "preset_version": 2,
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
            "rotate": rot_val,
            "deinterlace": self.chk_deinterlace.isChecked(),
            "fade_dur": self.spin_fade_duration.value(),
            "fade_pos": f_pos_val,
            "fade_type": f_type_val,
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

        rotate_map = {
            "normal": 0, "Normal": 0,
            "90_cw": 1, "90° Horário": 1, "90° Clockwise": 1, "90° Horario": 1,
            "90_ccw": 2, "90° Anti-horário": 2, "90° Counter-Clockwise": 2, "90° Antihorario": 2, "90° Anti-horaire": 2,
            "180": 3, "180°": 3,
            "hflip": 4, "Espelhar Horizontal": 4, "Horizontal Flip": 4, "Voltear Horizontal": 4, "Miroir horizontal": 4,
            "vflip": 5, "Espelhar Vertical": 5, "Vertical Flip": 5, "Voltear Vertical": 5, "Miroir vertical": 5
        }
        fade_pos_map = {
            "none": 0, "Nenhum": 0, "None": 0, "Ninguno": 0, "Aucun": 0, "Keine": 0,
            "start": 1, "No início": 1, "At start": 1, "Al inicio": 1, "Au début": 1, "Am Anfang": 1,
            "end": 2, "No final": 2, "At end": 2, "Al final": 2, "À la fin": 2, "Am Ende": 2,
            "both": 3, "Ambos": 3, "Both": 3, "Les deux": 3, "Beide": 3
        }
        fade_type_map = {
            "both": 0, "Vídeo e Áudio": 0, "Video and Audio": 0, "Vídeo y Audio": 0, "Vidéo et Audio": 0, "Video und Audio": 0,
            "video": 1, "Somente Vídeo": 1, "Video Only": 1, "Solo Vídeo": 1, "Vidéo seule": 1, "Nur Video": 1,
            "audio": 2, "Somente Áudio": 2, "Audio Only": 2, "Solo Audio": 2, "Audio seul": 2, "Nur Audio": 2
        }

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

            rot_val = state.get("rotate", "normal")
            self.combo_rotate.setCurrentIndex(rotate_map.get(rot_val, 0))

            self.chk_deinterlace.setChecked(bool(state.get("deinterlace")))
            self.spin_fade_duration.setValue(state.get("fade_dur", 0))

            f_pos_val = state.get("fade_pos", "none")
            self.combo_fade_pos.setCurrentIndex(fade_pos_map.get(f_pos_val, 0))

            f_type_val = state.get("fade_type", "both")
            self.combo_fade_type.setCurrentIndex(fade_type_map.get(f_type_val, 0))

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
        
        if hasattr(self, 'clear_cover_art'):
            self.clear_cover_art()
            
        if hasattr(self, 'spin_speed'):
            self.spin_speed.setValue(1.0)
            self.chk_pitch.setChecked(True)
        
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
        
        if hasattr(self, 'group_watermark'):
            self.group_watermark.setChecked(False)
            self.combo_wm_pos.setCurrentIndex(0)
            self.spin_wm_size.setValue(100)
            self.spin_wm_opacity.setValue(100)
            self.clear_watermark_image()

        self.entry_extra_args.setText("")
        
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
            
        if hasattr(self, 'combo_color_range'):
            self.combo_color_range.setCurrentIndex(0)
            self.combo_preset.setCurrentText("medium")
            self.combo_tune.setCurrentIndex(0)
            self.combo_profile.setCurrentIndex(0)
            self.combo_level.setCurrentIndex(0)
            self.chk_fast_decode.setChecked(False)
            self.chk_turbo_first_pass.setChecked(False)
            self.entry_x264_opts.setText("")
            self.radio_vfr.setChecked(True)

        if hasattr(self, 'combo_audio_track'):
            self.combo_audio_track.blockSignals(True)
            self.combo_audio_track.setCurrentIndex(0)
            self.combo_audio_track.blockSignals(False)
        if hasattr(self, 'list_external_audios'):
            self.list_external_audios.clear()
        
        if hasattr(self, 'combo_img_size'):
            self.combo_img_size.blockSignals(True)
            self.combo_img_size.setCurrentIndex(0)
            self.combo_img_size.blockSignals(False)
        if hasattr(self, 'slider_img_quality'):
            self.slider_img_quality.setValue(2)

        if hasattr(self, 'list_external_subs'):
            self.list_external_subs.clear()
        if hasattr(self, 'combo_sub_extract_track'):
            self.combo_sub_extract_track.setCurrentIndex(0)
        if hasattr(self, 'list_sub_remove_tracks'):
            self.list_sub_remove_tracks.clear()

        if hasattr(self, 'slider_audio_sync'):
            self.slider_audio_sync.setValue(0)
        if hasattr(self, 'spin_audio_sync'):
            self.spin_audio_sync.setValue(0.0)
            
        if hasattr(self, 'entry_meta_title'):
            self.entry_meta_title.setText("")
        if hasattr(self, 'entry_meta_artist'):
            self.entry_meta_artist.setText("")
        if hasattr(self, 'entry_meta_album'):
            self.entry_meta_album.setText("")
        if hasattr(self, 'entry_meta_year'):
            self.entry_meta_year.setText("")
        if hasattr(self, 'entry_meta_genre'):
            self.entry_meta_genre.setText("")
        if hasattr(self, 'entry_meta_comment'):
            self.entry_meta_comment.setText("")
            
        if hasattr(self, 'entry_ffmpeg_path'):
            self.entry_ffmpeg_path.setText("ffmpeg")

        if hasattr(self, 'chk_enable_trim'):
            self.chk_enable_trim.setChecked(False)
        if hasattr(self, 'time_start'):
            self.time_start.setTime(QTime(0, 0))
        if hasattr(self, 'time_end'):
            self.time_end.setTime(QTime(0, 0))

        self.update_video_codec_ui()
        self.update_format_locks()

    def _trigger_hard_reset(self):
        self.combo_presets.blockSignals(True)
        self.combo_presets.setCurrentIndex(0)
        self.combo_presets.blockSignals(False)
        self._reset_advanced_options()

    def save_new_preset(self):
        name, ok = QInputDialog.getText(self, tr("preset_name_prompt_title"), tr("preset_name_prompt_label"))
        if not ok or not name.strip(): return
        name = name.strip()
        if name in self.preset_manager.presets_data:
            QMessageBox.warning(self, tr("dialog_conflict"), tr("preset_exists_conflict", name=name))
            return
        state = self._capture_preset_state()
        if self.preset_manager.save_preset(name, state):
            self.load_presets()
            idx = self.combo_presets.findText(f"⭐ {name}")
            if idx != -1: self.combo_presets.setCurrentIndex(idx)
            QMessageBox.information(self, tr("dialog_success"), tr("preset_saved_success", name=name))
        else:
            QMessageBox.critical(self, tr("dialog_error"), tr("preset_save_error"))

    def clone_video_specs(self):
        selected_rows = [item.row() for item in self.table_files.selectedItems()]
        if not selected_rows:
            QMessageBox.warning(self, tr("clone_no_file_title"), tr("clone_no_file_selected"))
            return
            
        row = selected_rows[0]
        file_path = self.table_files.item(row, 1).toolTip()
        if not file_path or not os.path.exists(file_path):
            return
        specs = self.engine.get_media_specs(file_path)
        
        if specs["vcodec"] == "default" and specs["vbitrate"] == "default":
            QMessageBox.warning(self, tr("clone_failed_title"), tr("clone_failed_msg"))
            return

        state = self._capture_preset_state()
        state["vcodec"] = specs["vcodec"]
        if specs["vbitrate"] != "default": state["vbitrate"] = specs["vbitrate"]
        if specs["vsize"] != "default": state["vsize"] = specs["vsize"]
        if specs["vfps"] != "default": state["vfps"] = specs["vfps"]
        
        state["acodec"] = specs["acodec"]
        if specs["abitrate"] != "default": state["abitrate"] = specs["abitrate"]
        if specs["afreq"] != "default": state["afreq"] = specs["afreq"]
        if specs["achannels"] != "default": state["achannels"] = specs["achannels"]
        state["crf_enabled"] = False

        preset_name = f"Clone: {os.path.basename(file_path)}"
        self.preset_manager.presets_data[preset_name] = state
        preset_ui_name = f"⭐ {preset_name}"
        
        idx = self.combo_presets.findText(preset_ui_name)
        if idx != -1:
            self.combo_presets.removeItem(idx)
            
        self.combo_presets.addItem(preset_ui_name)
        self.combo_presets.setCurrentIndex(self.combo_presets.count() - 1)
        
        QMessageBox.information(self, tr("clone_success_title"), tr("clone_success_msg", filename=os.path.basename(file_path)))

    def delete_selected_preset(self):
        current = self.combo_presets.currentText()
        if not current.startswith("⭐ "): return
        name = current[2:]
        if QMessageBox.question(self, tr("dialog_confirm"), tr("preset_delete_confirm", name=name)) == QMessageBox.No: return
        if self.preset_manager.delete_preset(name):
            self.load_presets()
        else:
            QMessageBox.critical(self, tr("dialog_error"), tr("preset_delete_error"))

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

        v_res_tokens = ["best", "2160", "1440", "1080", "720", "480"]
        res_idx = self.combo_dl_v_res.currentIndex()
        v_res_val = v_res_tokens[res_idx] if 0 <= res_idx < len(v_res_tokens) else "best"

        options = {
            "a_fmt": self.combo_dl_a_fmt.currentText(),
            "a_bitrate": self.combo_dl_a_bitrate.currentText(),
            "v_fmt": self.combo_dl_v_fmt.currentText(),
            "v_res": v_res_val
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
        self.dl_log.appendPlainText(f"\n{tr('status_completed')}" if exitCode == 0 else f"\n{tr('status_error')} ({exitCode}).")
        self._play_done_sound()
        self._show_tray_message("Lyra", tr("tray_dl_done"), QSystemTrayIcon.Information, 5000)
        
    def on_dl_error(self, error):
        self.is_downloading = False
        self.btn_start_dl.setEnabled(True)
        self.btn_stop_dl.setEnabled(False)
        self.dl_log.appendPlainText(f"\n❌ Erro crítico: Falha ao iniciar o motor de download ({error}).")

    def retranslate_ui(self):
        """
        Atualiza todas as strings da interface gráfica quando o idioma é alterado.
        Permite tradução instantânea e dinâmica sem necessidade de reiniciar o aplicativo.
        """
        # Janela e Tray
        self.setWindowTitle(tr("app_title", version=self.version))
        if getattr(self, 'tray_icon', None):
            self.tray_icon.setToolTip(tr("app_name"))
        if hasattr(self, 'tray_show_action'):
            self.tray_show_action.setText(tr("tray_show"))
        if hasattr(self, 'tray_quit_action'):
            self.tray_quit_action.setText(tr("tray_quit"))

        # Sincroniza o combobox de idiomas
        if hasattr(self, 'combo_language'):
            self.combo_language.blockSignals(True)
            lang_idx = self.combo_language.findData(i18n.get_current_language())
            if lang_idx != -1:
                self.combo_language.setCurrentIndex(lang_idx)
            self.combo_language.blockSignals(False)

        # Toolbar
        if hasattr(self, 'toolbar'):
            self.toolbar.setWindowTitle(tr("toolbar_title"))
        if hasattr(self, 'action_add_file'):
            self.action_add_file.setText(tr("action_add_file"))
            self.action_add_file.setToolTip(tr("action_add_file_tt"))
        if hasattr(self, 'action_add_folder'):
            self.action_add_folder.setText(tr("action_add_folder"))
            self.action_add_folder.setToolTip(tr("action_add_folder_tt"))
        if hasattr(self, 'action_remove'):
            self.action_remove.setText(tr("action_remove"))
            self.action_remove.setToolTip(tr("action_remove_tt"))
        if hasattr(self, 'action_clear'):
            self.action_clear.setText(tr("action_clear"))
            self.action_clear.setToolTip(tr("action_clear_tt"))
        if hasattr(self, 'action_download'):
            is_main = (self.stacked_widget.currentIndex() == 0) if hasattr(self, 'stacked_widget') else True
            self.action_download.setText(tr("action_download") if is_main else (tr("action_back_to_list") if self.stacked_widget.currentIndex() == 2 else tr("action_download")))
            self.action_download.setToolTip(tr("action_download_tt"))
        if hasattr(self, 'action_advanced'):
            is_main = (self.stacked_widget.currentIndex() == 0) if hasattr(self, 'stacked_widget') else True
            self.action_advanced.setText(tr("action_advanced") if is_main else (tr("action_back_to_list") if self.stacked_widget.currentIndex() == 1 else tr("action_advanced")))
            self.action_advanced.setToolTip(tr("action_advanced_tt"))
        if hasattr(self, 'btn_convert'):
            self.btn_convert.setText(tr("btn_convert"))
        if hasattr(self, 'btn_stop'):
            self.btn_stop.setText(tr("btn_stop"))

        # Tela Principal
        if hasattr(self, 'lbl_format'):
            self.lbl_format.setText(tr("lbl_format"))
        if hasattr(self, 'btn_clone_specs'):
            self.btn_clone_specs.setText(tr("btn_clone_specs"))
            self.btn_clone_specs.setToolTip(tr("btn_clone_specs_tt"))
        if hasattr(self, 'lbl_presets'):
            self.lbl_presets.setText(tr("lbl_presets"))
        if hasattr(self, 'btn_reset_all'):
            self.btn_reset_all.setText(tr("btn_reset_all"))
            self.btn_reset_all.setToolTip(tr("btn_reset_all_tt"))
        if hasattr(self, 'btn_save_preset'):
            self.btn_save_preset.setText(tr("btn_save_preset"))
            self.btn_save_preset.setToolTip(tr("btn_save_preset_tt"))
        if hasattr(self, 'btn_delete_preset'):
            self.btn_delete_preset.setText(tr("btn_delete_preset"))
            self.btn_delete_preset.setToolTip(tr("btn_delete_preset_tt"))
        if hasattr(self, 'combo_presets') and self.combo_presets.count() > 0:
            self.combo_presets.setItemText(0, tr("preset_default_name"))

        if hasattr(self, 'table_files'):
            self.table_files.setHorizontalHeaderLabels([
                tr("th_skip"), tr("th_file"), tr("th_size"), tr("th_duration"),
                tr("th_est_size"), tr("th_elapsed"), tr("th_remaining"), tr("th_progress")
            ])

        if hasattr(self, 'lbl_dest_title'):
            self.lbl_dest_title.setText(tr("lbl_destination"))
        if hasattr(self, 'combo_exist_action') and self.combo_exist_action.count() >= 3:
            self.combo_exist_action.setItemText(0, tr("exist_overwrite"))
            self.combo_exist_action.setItemText(1, tr("exist_rename"))
            self.combo_exist_action.setItemText(2, tr("exist_skip"))
        if hasattr(self, 'btn_browse_dest'):
            self.btn_browse_dest.setText(tr("btn_browse_dest"))
        if hasattr(self, 'btn_open_dest'):
            self.btn_open_dest.setText(tr("btn_open_dest"))
        if hasattr(self, 'lbl_post_action'):
            self.lbl_post_action.setText(tr("lbl_post_action"))
        if hasattr(self, 'combo_post_action') and self.combo_post_action.count() >= 4:
            self.combo_post_action.setItemText(0, tr("post_do_nothing"))
            self.combo_post_action.setItemText(1, tr("post_close_lyra"))
            self.combo_post_action.setItemText(2, tr("post_suspend_pc"))
            self.combo_post_action.setItemText(3, tr("post_shutdown_pc"))

        # Menu Lateral Avançado (12 Abas)
        tab_keys = [
            "tab_audio", "tab_sync", "tab_trim", "tab_video", "tab_image",
            "tab_subtitles", "tab_filters", "tab_speed", "tab_more",
            "tab_tags", "tab_info", "tab_log"
        ]
        if hasattr(self, 'advanced_menu'):
            for i, key in enumerate(tab_keys):
                if i < self.advanced_menu.count():
                    self.advanced_menu.item(i).setText(tr(key))

        # Aba Áudio
        if hasattr(self, 'lbl_row_acodec'): self.lbl_row_acodec.setText(tr("lbl_audio_codec"))
        if hasattr(self, 'lbl_row_atrack'): self.lbl_row_atrack.setText(tr("lbl_audio_track"))
        if hasattr(self, 'lbl_row_abitrate'): self.lbl_row_abitrate.setText(tr("lbl_audio_bitrate"))
        if hasattr(self, 'lbl_row_afreq'): self.lbl_row_afreq.setText(tr("lbl_audio_freq"))
        if hasattr(self, 'lbl_row_achannels'): self.lbl_row_achannels.setText(tr("lbl_audio_channels"))
        if hasattr(self, 'lbl_row_avolume'): self.lbl_row_avolume.setText(tr("lbl_audio_volume"))
        if hasattr(self, 'chk_all_tracks'):
            self.chk_all_tracks.setText(tr("chk_all_tracks"))
            self.chk_all_tracks.setToolTip(tr("chk_all_tracks_tt"))
        if hasattr(self, 'chk_audio_drc'):
            self.chk_audio_drc.setText(tr("chk_audio_drc"))
            self.chk_audio_drc.setToolTip(tr("chk_audio_drc_tt"))
        if hasattr(self, 'chk_noise_reduction'):
            self.chk_noise_reduction.setText(tr("chk_noise_reduction"))
            self.chk_noise_reduction.setToolTip(tr("chk_noise_reduction_tt"))
        if hasattr(self, 'group_external_audio'): self.group_external_audio.setTitle(tr("grp_external_audio"))
        if hasattr(self, 'btn_add_audio'): self.btn_add_audio.setText(tr("btn_add"))
        if hasattr(self, 'btn_rem_audio'): self.btn_rem_audio.setText(tr("btn_remove"))
        if hasattr(self, 'btn_clear_audio'): self.btn_clear_audio.setText(tr("btn_clear"))

        # Aba Sincronia
        if hasattr(self, 'lbl_sync_delay'): self.lbl_sync_delay.setText(tr("lbl_audio_delay"))
        if hasattr(self, 'btn_sync_play'): self.btn_sync_play.setText(tr("btn_play_pause"))

        # Aba Cortes
        if hasattr(self, 'chk_enable_trim'):
            self.chk_enable_trim.setText(tr("chk_enable_trim"))
            self.chk_enable_trim.setToolTip(tr("chk_enable_trim_tt"))
        if hasattr(self, 'lbl_trim_from'): self.lbl_trim_from.setText(tr("lbl_trim_from"))
        if hasattr(self, 'lbl_trim_to'): self.lbl_trim_to.setText(tr("lbl_trim_to"))
        if hasattr(self, 'btn_mark_start'): self.btn_mark_start.setText(tr("btn_mark_start"))
        if hasattr(self, 'btn_mark_end'): self.btn_mark_end.setText(tr("btn_mark_end"))

        # Aba Vídeo
        if hasattr(self, 'grp_basic'): self.grp_basic.setTitle(tr("grp_basic_settings"))
        if hasattr(self, 'lbl_vcodec'): self.lbl_vcodec.setText(tr("lbl_video_codec"))
        if hasattr(self, 'lbl_vfps'): self.lbl_vfps.setText(tr("lbl_video_fps"))
        if hasattr(self, 'radio_vfr'): self.radio_vfr.setText(tr("radio_vfr"))
        if hasattr(self, 'radio_cfr'): self.radio_cfr.setText(tr("radio_cfr"))
        if hasattr(self, 'lbl_vsize'): self.lbl_vsize.setText(tr("lbl_video_size"))
        if hasattr(self, 'lbl_vratio'): self.lbl_vratio.setText(tr("lbl_video_ratio"))
        if hasattr(self, 'grp_quality'): self.grp_quality.setTitle(tr("grp_quality"))
        if hasattr(self, 'chk_crf'):
            self.chk_crf.setText(tr("chk_crf"))
            self.chk_crf.setToolTip(tr("chk_crf_tt"))
        if hasattr(self, 'lbl_vbitrate'): self.lbl_vbitrate.setText(tr("lbl_video_bitrate"))
        if hasattr(self, 'chk_2pass'):
            self.chk_2pass.setText(tr("chk_2pass"))
            self.chk_2pass.setToolTip(tr("chk_2pass_tt"))
        if hasattr(self, 'chk_turbo_first_pass'):
            self.chk_turbo_first_pass.setText(tr("chk_turbo_first_pass"))
            self.chk_turbo_first_pass.setToolTip(tr("chk_turbo_first_pass_tt"))
        if hasattr(self, 'grp_enc'): self.grp_enc.setTitle(tr("grp_encoder_opt"))
        if hasattr(self, 'lbl_color_range'): self.lbl_color_range.setText(tr("lbl_color_range"))
        if hasattr(self, 'lbl_preset'): self.lbl_preset.setText(tr("lbl_preset"))
        if hasattr(self, 'lbl_tune'): self.lbl_tune.setText(tr("lbl_tune"))
        if hasattr(self, 'lbl_profile'): self.lbl_profile.setText(tr("lbl_profile"))
        if hasattr(self, 'lbl_level'): self.lbl_level.setText(tr("lbl_level"))
        if hasattr(self, 'chk_fast_decode'):
            self.chk_fast_decode.setText(tr("chk_fast_decode"))
            self.chk_fast_decode.setToolTip(tr("chk_fast_decode_tt"))
        if hasattr(self, 'lbl_extra_opts'): self.lbl_extra_opts.setText(tr("lbl_extra_opts"))
        if hasattr(self, 'entry_x264_opts'): self.entry_x264_opts.setPlaceholderText(tr("ph_x264_opts"))
        if hasattr(self, 'chk_video_only'):
            self.chk_video_only.setText(tr("chk_video_only"))
            self.chk_video_only.setToolTip(tr("chk_video_only_tt"))
        if hasattr(self, 'chk_bad_index'):
            self.chk_bad_index.setText(tr("chk_bad_index"))
            self.chk_bad_index.setToolTip(tr("chk_bad_index_tt"))

        # Aba Imagem
        if hasattr(self, 'lbl_img_size'): self.lbl_img_size.setText(tr("lbl_img_size"))
        if hasattr(self, 'lbl_img_quality'): self.lbl_img_quality.setText(tr("lbl_img_quality"))

        # Aba Legendas
        if hasattr(self, 'group_sub_file'): self.group_sub_file.setTitle(tr("grp_sub_selection"))
        if hasattr(self, 'btn_add_sub'): self.btn_add_sub.setText(tr("btn_add"))
        if hasattr(self, 'btn_rem_sub'): self.btn_rem_sub.setText(tr("btn_remove"))
        if hasattr(self, 'btn_clear_sub'): self.btn_clear_sub.setText(tr("btn_clear"))
        if hasattr(self, 'group_sub_mode'): self.group_sub_mode.setTitle(tr("grp_sub_mode"))
        if hasattr(self, 'lbl_sub_render_type'): self.lbl_sub_render_type.setText(tr("lbl_sub_render_type"))
        if hasattr(self, 'combo_sub_mode') and self.combo_sub_mode.count() >= 2:
            self.combo_sub_mode.setItemText(0, tr("sub_mode_softsub"))
            self.combo_sub_mode.setItemText(1, tr("sub_mode_hardsub"))
        if hasattr(self, 'group_sub_extract'): self.group_sub_extract.setTitle(tr("grp_sub_extract"))
        if hasattr(self, 'lbl_sub_extract_track'): self.lbl_sub_extract_track.setText(tr("lbl_sub_extract_track"))
        if hasattr(self, 'combo_sub_extract_track') and self.combo_sub_extract_track.count() >= 4:
            self.combo_sub_extract_track.setItemText(0, tr("sub_track_1_default"))
            self.combo_sub_extract_track.setItemText(1, tr("sub_track_n", n=2))
            self.combo_sub_extract_track.setItemText(2, tr("sub_track_n", n=3))
            self.combo_sub_extract_track.setItemText(3, tr("sub_track_n", n=4))
        if hasattr(self, 'extract_note'): self.extract_note.setText(tr("sub_extract_note"))
        if hasattr(self, 'group_sub_remove'): self.group_sub_remove.setTitle(tr("grp_sub_remove"))

        # Aba Filtros
        if hasattr(self, 'basic_filter_group'): self.basic_filter_group.setTitle(tr("grp_basic_filters"))
        if hasattr(self, 'lbl_rotate'): self.lbl_rotate.setText(tr("lbl_rotation"))
        if hasattr(self, 'combo_rotate') and self.combo_rotate.count() >= 6:
            self.combo_rotate.setItemText(0, tr("rotate_normal"))
            self.combo_rotate.setItemText(1, tr("rotate_90_cw"))
            self.combo_rotate.setItemText(2, tr("rotate_90_ccw"))
            self.combo_rotate.setItemText(3, tr("rotate_180"))
            self.combo_rotate.setItemText(4, tr("rotate_hflip"))
            self.combo_rotate.setItemText(5, tr("rotate_vflip"))
        if hasattr(self, 'chk_deinterlace'):
            self.chk_deinterlace.setText(tr("chk_deinterlace"))
            self.chk_deinterlace.setToolTip(tr("chk_deinterlace_tt"))
        if hasattr(self, 'fade_group'): self.fade_group.setTitle(tr("grp_fade"))
        if hasattr(self, 'lbl_fade_dur'): self.lbl_fade_dur.setText(tr("lbl_duration"))
        if hasattr(self, 'lbl_fade_pos'): self.lbl_fade_pos.setText(tr("lbl_position"))
        if hasattr(self, 'combo_fade_pos') and self.combo_fade_pos.count() >= 4:
            self.combo_fade_pos.setItemText(0, tr("fade_pos_none"))
            self.combo_fade_pos.setItemText(1, tr("fade_pos_start"))
            self.combo_fade_pos.setItemText(2, tr("fade_pos_end"))
            self.combo_fade_pos.setItemText(3, tr("fade_pos_both"))
        if hasattr(self, 'lbl_fade_type'): self.lbl_fade_type.setText(tr("lbl_type"))
        if hasattr(self, 'combo_fade_type') and self.combo_fade_type.count() >= 3:
            self.combo_fade_type.setItemText(0, tr("fade_type_both"))
            self.combo_fade_type.setItemText(1, tr("fade_type_video"))
            self.combo_fade_type.setItemText(2, tr("fade_type_audio"))
        if hasattr(self, 'group_crop'): self.group_crop.setTitle(tr("grp_crop"))
        if hasattr(self, 'lbl_crop_top'): self.lbl_crop_top.setText(tr("lbl_crop_top"))
        if hasattr(self, 'lbl_crop_bottom'): self.lbl_crop_bottom.setText(tr("lbl_crop_bottom"))
        if hasattr(self, 'lbl_crop_left'): self.lbl_crop_left.setText(tr("lbl_crop_left"))
        if hasattr(self, 'lbl_crop_right'): self.lbl_crop_right.setText(tr("lbl_crop_right"))
        if hasattr(self, 'btn_auto_crop'): self.btn_auto_crop.setText(tr("btn_auto_crop"))
        if hasattr(self, 'group_pad'): self.group_pad.setTitle(tr("grp_pad"))
        if hasattr(self, 'lbl_pad_top'): self.lbl_pad_top.setText(tr("lbl_crop_top"))
        if hasattr(self, 'lbl_pad_bottom'): self.lbl_pad_bottom.setText(tr("lbl_crop_bottom"))
        if hasattr(self, 'lbl_pad_left'): self.lbl_pad_left.setText(tr("lbl_crop_left"))
        if hasattr(self, 'lbl_pad_right'): self.lbl_pad_right.setText(tr("lbl_crop_right"))
        if hasattr(self, 'group_watermark'): self.group_watermark.setTitle(tr("grp_watermark"))
        if hasattr(self, 'btn_wm_select'): self.btn_wm_select.setText(tr("btn_choose_image"))
        if hasattr(self, 'btn_wm_clear'): self.btn_wm_clear.setText(tr("btn_clear_wm"))
        if hasattr(self, 'lbl_wm_pos'): self.lbl_wm_pos.setText(tr("lbl_position"))
        if hasattr(self, 'lbl_wm_size'): self.lbl_wm_size.setText(tr("lbl_size"))
        if hasattr(self, 'lbl_wm_opacity'): self.lbl_wm_opacity.setText(tr("lbl_opacity"))
        if hasattr(self, 'combo_wm_pos') and self.combo_wm_pos.count() >= 5:
            self.combo_wm_pos.setItemText(0, tr("wm_pos_br"))
            self.combo_wm_pos.setItemText(1, tr("wm_pos_bl"))
            self.combo_wm_pos.setItemText(2, tr("wm_pos_tr"))
            self.combo_wm_pos.setItemText(3, tr("wm_pos_tl"))
            self.combo_wm_pos.setItemText(4, tr("wm_pos_center"))

        # Aba Velocidade
        if hasattr(self, 'lbl_speed_info'): self.lbl_speed_info.setText(tr("lbl_speed_info"))
        if hasattr(self, 'lbl_exact_speed'): self.lbl_exact_speed.setText(tr("lbl_exact_speed"))
        if hasattr(self, 'chk_pitch'):
            self.chk_pitch.setText(tr("chk_preserve_pitch"))
            self.chk_pitch.setToolTip(tr("chk_preserve_pitch_tt"))

        # Aba Mais
        if hasattr(self, 'lbl_threads_title'): self.lbl_threads_title.setText(tr("lbl_cpu_threads"))
        if hasattr(self, 'lbl_extra_args_title'): self.lbl_extra_args_title.setText(tr("lbl_extra_ffmpeg_args"))
        if hasattr(self, 'entry_extra_args'): self.entry_extra_args.setPlaceholderText(tr("ph_extra_ffmpeg_args"))
        if hasattr(self, 'lbl_ffmpeg_path_title'): self.lbl_ffmpeg_path_title.setText(tr("lbl_converter_exec"))

        # Aba Marcadores
        if hasattr(self, 'lbl_tags_warning'): self.lbl_tags_warning.setText(tr("lbl_tags_warning"))
        if hasattr(self, 'lbl_meta_title'): self.lbl_meta_title.setText(tr("lbl_meta_title"))
        if hasattr(self, 'entry_meta_title'):
            self.entry_meta_title.setPlaceholderText(tr("ph_meta_title"))
            self.entry_meta_title.setToolTip(tr("tt_meta_title"))
        if hasattr(self, 'lbl_meta_artist'): self.lbl_meta_artist.setText(tr("lbl_meta_artist"))
        if hasattr(self, 'entry_meta_artist'): self.entry_meta_artist.setPlaceholderText(tr("ph_meta_artist"))
        if hasattr(self, 'lbl_meta_album'): self.lbl_meta_album.setText(tr("lbl_meta_album"))
        if hasattr(self, 'entry_meta_album'): self.entry_meta_album.setPlaceholderText(tr("ph_meta_album"))
        if hasattr(self, 'lbl_meta_year'): self.lbl_meta_year.setText(tr("lbl_meta_year"))
        if hasattr(self, 'entry_meta_year'): self.entry_meta_year.setPlaceholderText(tr("ph_meta_year"))
        if hasattr(self, 'lbl_meta_genre'): self.lbl_meta_genre.setText(tr("lbl_meta_genre"))
        if hasattr(self, 'entry_meta_genre'): self.entry_meta_genre.setPlaceholderText(tr("ph_meta_genre"))
        if hasattr(self, 'lbl_meta_comment'): self.lbl_meta_comment.setText(tr("lbl_meta_comment"))
        if hasattr(self, 'entry_meta_comment'): self.entry_meta_comment.setPlaceholderText(tr("ph_meta_comment"))
        if hasattr(self, 'lbl_meta_cover'): self.lbl_meta_cover.setText(tr("lbl_meta_cover"))
        if hasattr(self, 'entry_cover_path'): self.entry_cover_path.setPlaceholderText(tr("ph_no_cover"))
        if hasattr(self, 'btn_choose_cover'): self.btn_choose_cover.setText(tr("btn_choose_image"))
        if hasattr(self, 'btn_clear_cover'): self.btn_clear_cover.setText(tr("btn_clear_wm"))

        # Página Download
        if hasattr(self, 'lbl_dl_title'): self.lbl_dl_title.setText(tr("lbl_dl_title"))
        if hasattr(self, 'lbl_dl_url'): self.lbl_dl_url.setText(tr("lbl_dl_url"))
        if hasattr(self, 'entry_dl_url'): self.entry_dl_url.setPlaceholderText(tr("ph_dl_url"))
        if hasattr(self, 'group_dl_config'): self.group_dl_config.setTitle(tr("grp_dl_config"))
        if hasattr(self, 'lbl_dl_mode'): self.lbl_dl_mode.setText(tr("lbl_dl_mode"))
        if hasattr(self, 'combo_dl_mode') and self.combo_dl_mode.count() >= 2:
            self.combo_dl_mode.setItemText(0, tr("dl_mode_video"))
            self.combo_dl_mode.setItemText(1, tr("dl_mode_audio"))
        if hasattr(self, 'lbl_dl_max_res'): self.lbl_dl_max_res.setText(tr("lbl_dl_max_res"))
        if hasattr(self, 'combo_dl_v_res') and self.combo_dl_v_res.count() > 0:
            self.combo_dl_v_res.setItemText(0, tr("dl_res_best"))
        if hasattr(self, 'lbl_dl_container_fmt'): self.lbl_dl_container_fmt.setText(tr("lbl_dl_container_fmt"))
        if hasattr(self, 'lbl_dl_audio_fmt'): self.lbl_dl_audio_fmt.setText(tr("lbl_dl_audio_fmt"))
        if hasattr(self, 'lbl_dl_audio_quality'): self.lbl_dl_audio_quality.setText(tr("lbl_dl_audio_quality"))
        if hasattr(self, 'btn_start_dl'): self.btn_start_dl.setText(tr("btn_start_dl"))
        if hasattr(self, 'btn_stop_dl'): self.btn_stop_dl.setText(tr("btn_stop_dl"))

    # ======================================================================
    # DRAG AND DROP EVENTS
    # ======================================================================
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        from PySide6.QtWidgets import QMessageBox
        failed_files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                self.add_file_to_table(file_path)
            elif os.path.isdir(file_path):
                for root, _, files in os.walk(file_path):
                    for file in files:
                        self.add_file_to_table(os.path.join(root, file))
            else:
                if file_path:
                    failed_files.append(file_path)
                    
        if failed_files:
            QMessageBox.warning(
                self, tr("dnd_permission_warning_title"),
                tr("dnd_permission_warning_msg", count=len(failed_files))
            )