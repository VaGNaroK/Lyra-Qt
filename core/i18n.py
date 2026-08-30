import os
import json
import logging
from PySide6.QtCore import QObject, Signal, QSettings, QLocale, QTranslator, QLibraryInfo
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {
    "pt_BR": "Português (Brasil)",
    "en_US": "English (US)",
    "es_ES": "Español",
    "fr_FR": "Français",
    "de_DE": "Deutsch",
    "it_IT": "Italiano",
    "ru_RU": "Русский",
    "zh_CN": "简体中文",
    "ja_JP": "日本語",
}

QT_TRANSLATION_MAP = {
    "pt_BR": ["qtbase_pt_BR", "qt_pt_BR"],
    "en_US": ["qtbase_en", "qt_en"],
    "es_ES": ["qtbase_es", "qt_es"],
    "fr_FR": ["qtbase_fr", "qt_fr"],
    "de_DE": ["qtbase_de", "qt_de"],
    "it_IT": ["qtbase_it", "qt_it"],
    "ru_RU": ["qtbase_ru", "qt_ru"],
    "zh_CN": ["qtbase_zh_CN", "qt_zh_CN"],
    "ja_JP": ["qtbase_ja", "qt_ja"],
}

DEFAULT_LANGUAGE = "pt_BR"
FALLBACK_LANGUAGE = "en_US"


class I18nManager(QObject):
    """
    Gerenciador de Internacionalização (i18n) e Localização (l10n) do Lyra-Qt.
    Fornece tradução reativa via dicionários JSON com fallback automático,
    suporte a QTranslator do Qt para menus de contexto nativos (Undo, Redo, Cut, Copy, Paste, Delete),
    detecção de locale do sistema e persistência em QSettings.
    """
    language_changed = Signal(str)

    def __init__(self, resource_dir=None):
        super().__init__()
        self.resource_dir = resource_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.translations_dir = os.path.join(self.resource_dir, "assets", "translations")
        self.settings = QSettings("Lyra", "Lyra-Qt")
        
        self.current_language = DEFAULT_LANGUAGE
        self._translations = {}
        self._fallback_translations = {}
        self._pt_translations = {}
        self._installed_translators = []

        # Carrega dicionários base de fallback
        self._load_base_translations()

        # Determina o idioma salvo ou detectado do sistema
        initial_lang = self.settings.value("language", None)
        if not initial_lang or initial_lang not in SUPPORTED_LANGUAGES:
            initial_lang = self.detect_system_language()

        self.set_language(initial_lang, persist=False)

    def reinit_resource_dir(self, resource_dir: str):
        """Atualiza o diretório de recursos caso resolvido após inicialização."""
        if resource_dir and resource_dir != self.resource_dir:
            self.resource_dir = resource_dir
            self.translations_dir = os.path.join(self.resource_dir, "assets", "translations")
            self._load_base_translations()
            self.set_language(self.current_language, persist=False)

    def _load_base_translations(self):
        """Carrega dicionários base (pt_BR e en_US) para garantir fallback robusto."""
        self._pt_translations = self._read_json("pt_BR")
        self._fallback_translations = self._read_json(FALLBACK_LANGUAGE)

    def _read_json(self, lang_code: str) -> dict:
        """Lê arquivo JSON de tradução com proteção contra exceções."""
        file_path = os.path.join(self.translations_dir, f"{lang_code}.json")
        if os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Falha ao ler arquivo de tradução '%s': %s", file_path, e)
        return {}

    def _map_locale_name(self, locale_name: str) -> str:
        """Mapeia uma string de locale (ex: 'pt_PT', 'fr_CA') para um idioma suportado."""
        if not locale_name:
            return DEFAULT_LANGUAGE
        if locale_name in SUPPORTED_LANGUAGES:
            return locale_name
        
        prefix = locale_name.split("_")[0].lower() if "_" in locale_name else locale_name.lower()
        for code in SUPPORTED_LANGUAGES:
            if code.lower().startswith(prefix):
                return code
        return FALLBACK_LANGUAGE

    def detect_system_language(self) -> str:
        """
        Detecta o idioma do sistema operacional e mapeia para o código suportado mais próximo.
        """
        try:
            sys_locale = QLocale.system().name()  # Ex: "pt_BR", "en_US", "es_ES", "fr_FR"
            return self._map_locale_name(sys_locale)
        except Exception:
            pass

        return DEFAULT_LANGUAGE

    def _load_qt_translators(self, lang_code: str):
        """Carrega e instala os QTranslators do Qt para traduzir menus de contexto padrão (Undo, Redo, Cut, Copy, Paste, etc.)."""
        app = QApplication.instance()
        if not app:
            return

        # Remove tradutores instalados anteriormente
        for t in self._installed_translators:
            try:
                app.removeTranslator(t)
            except Exception:
                pass
        self._installed_translators.clear()

        prefixes = QT_TRANSLATION_MAP.get(lang_code, QT_TRANSLATION_MAP.get(DEFAULT_LANGUAGE, []))
        
        # Procura tanto na pasta bundled (assets/translations/qt) quanto na biblioteca do sistema
        search_dirs = [
            os.path.join(self.translations_dir, "qt"),
            self.translations_dir,
            QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        ]

        for prefix in prefixes:
            translator = QTranslator(self)
            for d in search_dirs:
                if d and os.path.isdir(d):
                    if translator.load(prefix, d):
                        app.installTranslator(translator)
                        self._installed_translators.append(translator)
                        break

    def set_language(self, lang_code: str, persist: bool = True):
        """
        Altera o idioma ativo do aplicativo e recarrega os dicionários.
        
        Args:
            lang_code (str): Código do idioma (ex: 'en_US', 'pt_BR').
            persist (bool): Se True, salva a preferência no QSettings.
        """
        if lang_code not in SUPPORTED_LANGUAGES:
            lang_code = DEFAULT_LANGUAGE

        self.current_language = lang_code
        self._translations = self._read_json(lang_code)

        # Atualiza os tradutores nativos do Qt (menus de contexto, diálogos do sistema, etc.)
        self._load_qt_translators(lang_code)

        if persist:
            self.settings.setValue("language", lang_code)

        self.language_changed.emit(lang_code)

    def get_current_language(self) -> str:
        """Retorna o código do idioma ativo (ex: 'pt_BR')."""
        return self.current_language

    def get_available_languages(self) -> dict:
        """Retorna dicionário com todos os idiomas suportados e seus nomes legíveis."""
        return dict(SUPPORTED_LANGUAGES)

    def tr(self, key: str, default: str = None, **kwargs) -> str:
        """
        Traduz uma chave de texto para o idioma ativo.
        Aplica fallback em cascata: Idioma Atual -> pt_BR -> en_US -> default -> key.
        Suporta interpolação segura com kwargs (ex: tr("count_files", count=5)).
        
        Args:
            key (str): Chave da mensagem.
            default (str, opcional): Texto de fallback caso a chave não seja encontrada.
            **kwargs: Variáveis a serem interpoladas no texto.
            
        Returns:
            str: Texto traduzido e formatado.
        """
        text = self._translations.get(key)
        if text is None:
            text = self._pt_translations.get(key)
        if text is None:
            text = self._fallback_translations.get(key)
        if text is None:
            text = default if default is not None else key

        if kwargs:
            try:
                text = text.format(**kwargs)
            except Exception:
                pass

        return text

    def __call__(self, key: str, default: str = None, **kwargs) -> str:
        """Permite usar a instância diretamente como função de tradução: i18n('key')."""
        return self.tr(key, default=default, **kwargs)


# Instância Global Singleton para fácil acesso no app
i18n = I18nManager()
tr = i18n.tr
