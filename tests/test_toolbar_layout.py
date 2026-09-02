import os
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSize
from gui.main_window import LyraMainWindow
from core.i18n import i18n, SUPPORTED_LANGUAGES


@pytest.fixture
def resource_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def main_window(qtbot, resource_dir):
    """Cria uma instância da LyraMainWindow para testes de layout de UI."""
    win = LyraMainWindow("1.1.23", resource_dir)
    qtbot.addWidget(win)
    with qtbot.waitExposed(win):
        win.show()
    return win


def test_window_default_and_minimum_dimensions(main_window):
    """Garante que as dimensões padrão e mínimas da janela foram definidas adequadamente."""
    assert main_window.width() >= 1040
    assert main_window.height() >= 600
    assert main_window.minimumSize() == QSize(1040, 600)


def test_language_selector_presence_and_items(main_window):
    """Garante que o seletor de idioma está presente na toolbar com todos os idiomas suportados."""
    assert hasattr(main_window, "combo_language")
    assert main_window.combo_language is not None
    assert main_window.combo_language.count() == len(SUPPORTED_LANGUAGES)

    for code, name in SUPPORTED_LANGUAGES.items():
        idx = main_window.combo_language.findData(code)
        assert idx != -1, f"Idioma {code} ({name}) deve estar presente no combobox"


def test_language_selector_visibility_across_all_languages(qtbot, main_window):
    """
    🔒 FIX / Regressão: Testa se o dropdown de idiomas permanece 100% visível,
    não sofre corte (clip) e não é ocultado pela toolbar em nenhum dos 9 idiomas suportados,
    especialmente ao alternar para idiomas com textos longos como espanhol (es_ES) ou alemão (de_DE).
    """
    default_width = main_window.width()
    default_height = main_window.height()

    for lang_code in SUPPORTED_LANGUAGES.keys():
        i18n.set_language(lang_code, persist=False)
        QApplication.processEvents()

        # O combobox de idioma DEVE estar visível
        assert main_window.combo_language.isVisible(), (
            f"combo_language ficou invisível/ocultado no idioma {lang_code}!"
        )

        # Os botões críticos de conversão também devem estar visíveis
        assert main_window.btn_convert.isVisible(), (
            f"btn_convert ficou invisível no idioma {lang_code}!"
        )
        assert main_window.btn_stop.isVisible(), (
            f"btn_stop ficou invisível no idioma {lang_code}!"
        )

        # A toolbar não deve exceder a largura da janela principal
        tb_hint = main_window.toolbar.sizeHint().width()
        assert tb_hint <= main_window.width(), (
            f"Toolbar sizeHint ({tb_hint}px) excedeu a largura da janela ({main_window.width()}px) no idioma {lang_code}!"
        )

        # A geometria do combobox deve estar dentro da janela
        combo_geom = main_window.combo_language.geometry()
        assert combo_geom.x() + combo_geom.width() <= main_window.width(), (
            f"combo_language ultrapassou o limite direito da janela ({combo_geom.x() + combo_geom.width()} > {main_window.width()}) no idioma {lang_code}!"
        )

    # Garante que a janela não sofreu expansão anômala após transitar por todos os idiomas
    assert main_window.width() == default_width, "A largura da janela expandiu indevidamente após troca de idiomas!"
    assert main_window.height() == default_height, "A altura da janela expandiu indevidamente após troca de idiomas!"


def test_responsive_toolbar_buttons_scaling(main_window):
    """
    Testa se os botões da toolbar (Adicionar Arquivo, Adicionar Pasta, Remover, etc.)
    escalam proporcionalmente (aumentam e diminuem) conforme o tamanho da janela varia.
    """
    responsive_buttons = [
        main_window.btn_tool_add_file,
        main_window.btn_tool_add_folder,
        main_window.btn_tool_remove,
        main_window.btn_tool_clear,
        main_window.btn_tool_download,
        main_window.btn_tool_advanced,
    ]

    # Mede larguras em resoluções crescentes
    widths_1040 = []
    main_window.resize(1040, 600)
    QApplication.processEvents()
    for b in responsive_buttons:
        assert b.isVisible()
        assert b.width() >= 80, f"Botão {b.text()} ficou menor que o mínimo de 80px"
        assert b.width() <= 210, f"Botão {b.text()} excedeu o máximo de 210px"
        widths_1040.append(b.width())

    widths_1400 = []
    main_window.resize(1400, 700)
    QApplication.processEvents()
    for b in responsive_buttons:
        assert b.isVisible()
        widths_1400.append(b.width())

    widths_1800 = []
    main_window.resize(1800, 700)
    QApplication.processEvents()
    for b in responsive_buttons:
        assert b.isVisible()
        assert b.width() <= 210, f"Botão {b.text()} excedeu o teto de 210px em 1800px"
        widths_1800.append(b.width())

    # Verifica se os botões expandiram de 1040px para 1400px
    avg_1040 = sum(widths_1040) / len(widths_1040)
    avg_1400 = sum(widths_1400) / len(widths_1400)
    avg_1800 = sum(widths_1800) / len(widths_1800)

    assert avg_1400 > avg_1040, f"Os botões deveriam expandir de 1040px para 1400px! ({avg_1040} -> {avg_1400})"
    assert avg_1800 >= avg_1400, f"Os botões deveriam expandir ou manter o teto entre 1400px e 1800px! ({avg_1400} -> {avg_1800})"

    # Controles principais devem continuar visíveis
    assert main_window.btn_convert.isVisible()
    assert main_window.btn_stop.isVisible()
    assert main_window.combo_language.isVisible()

