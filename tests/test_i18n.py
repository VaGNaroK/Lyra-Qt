import os
import json
import pytest
from unittest.mock import patch, MagicMock
from core.i18n import I18nManager, tr, SUPPORTED_LANGUAGES
from core.ffmpeg_engine import FFmpegEngine
from core.ytdlp_engine import YTDLPEngine


@pytest.fixture
def resource_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def i18n_instance(resource_dir):
    manager = I18nManager(resource_dir=resource_dir)
    return manager


def test_supported_languages_list():
    assert "pt_BR" in SUPPORTED_LANGUAGES
    assert "en_US" in SUPPORTED_LANGUAGES
    assert "es_ES" in SUPPORTED_LANGUAGES
    assert "fr_FR" in SUPPORTED_LANGUAGES
    assert "de_DE" in SUPPORTED_LANGUAGES
    assert "it_IT" in SUPPORTED_LANGUAGES
    assert "ru_RU" in SUPPORTED_LANGUAGES
    assert "zh_CN" in SUPPORTED_LANGUAGES
    assert "ja_JP" in SUPPORTED_LANGUAGES
    assert len(SUPPORTED_LANGUAGES) == 9


def test_translation_files_integrity_and_key_parity(resource_dir):
    translations_dir = os.path.join(resource_dir, "assets", "translations")
    assert os.path.isdir(translations_dir), "O diretório assets/translations deve existir"

    # Carrega o dicionário base (pt_BR)
    pt_file = os.path.join(translations_dir, "pt_BR.json")
    assert os.path.exists(pt_file)
    with open(pt_file, "r", encoding="utf-8") as f:
        pt_data = json.load(f)

    base_keys = set(pt_data.keys())
    assert len(base_keys) > 50, "pt_BR.json deve conter um catálogo substancial de chaves"

    for lang_code in SUPPORTED_LANGUAGES.keys():
        lang_file = os.path.join(translations_dir, f"{lang_code}.json")
        assert os.path.exists(lang_file), f"Arquivo de tradução {lang_code}.json não encontrado"
        with open(lang_file, "r", encoding="utf-8") as f:
            lang_data = json.load(f)
        
        # Verifica se todas as chaves do pt_BR existem no idioma
        missing_keys = base_keys - set(lang_data.keys())
        assert not missing_keys, f"Idioma {lang_code} está faltando as seguintes chaves: {missing_keys}"


def test_tr_basic_and_interpolation(i18n_instance):
    i18n_instance.set_language("en_US", persist=False)
    assert i18n_instance.tr("btn_convert") == "🚀 Convert"
    assert i18n_instance.tr("app_title", version="2.0.0") == "Lyra Multimedia Converter v2.0.0"

    i18n_instance.set_language("pt_BR", persist=False)
    assert i18n_instance.tr("btn_convert") == "🚀 Converter"
    assert i18n_instance.tr("app_title", version="2.0.0") == "Lyra Multimedia Converter v2.0.0"

    i18n_instance.set_language("es_ES", persist=False)
    assert i18n_instance.tr("btn_convert") == "🚀 Convertir"


def test_tr_fallback_for_missing_key(i18n_instance):
    i18n_instance.set_language("en_US", persist=False)
    # Chave inexistente retorna a própria chave
    assert i18n_instance.tr("non_existent_key_xyz") == "non_existent_key_xyz"


def test_language_changed_signal(qtbot, i18n_instance):
    with qtbot.waitSignal(i18n_instance.language_changed, timeout=1000) as blocker:
        i18n_instance.set_language("de_DE", persist=False)
    assert blocker.args == ["de_DE"]
    assert i18n_instance.get_current_language() == "de_DE"


def test_detect_system_language():
    manager = I18nManager()
    
    # Teste de matching exato e por prefixo
    assert manager._map_locale_name("pt_BR") == "pt_BR"
    assert manager._map_locale_name("pt_PT") == "pt_BR"
    assert manager._map_locale_name("en_GB") == "en_US"
    assert manager._map_locale_name("es_AR") == "es_ES"
    assert manager._map_locale_name("fr_CA") == "fr_FR"
    assert manager._map_locale_name("de_AT") == "de_DE"
    assert manager._map_locale_name("it_CH") == "it_IT"
    assert manager._map_locale_name("ru_BY") == "ru_RU"
    assert manager._map_locale_name("zh_TW") == "zh_CN"
    assert manager._map_locale_name("ja_JP") == "ja_JP"
    assert manager._map_locale_name("ko_KR") == "en_US"  # Fallback


def test_ffmpeg_engine_canonical_tokens_support(tmp_path, resource_dir):
    engine = FFmpegEngine(resource_dir)
    engine.current_duration = 10.0

    wm_file = tmp_path / "watermark.png"
    wm_file.write_text("fake_image_data")

    # 1. Rotação e fade com token canônico
    opts_canonical = {
        "vcodec": "libx264",
        "rotate": "90_cw",
        "fade_pos": "both",
        "fade_dur": 2,
        "fade_type": "both",
        "watermark": {
            "enabled": True,
            "image_path": str(wm_file),
            "position": "top_left",
            "size": 100,
            "opacity": 100
        }
    }
    cmd_can = engine.build_ffmpeg_command("in.mp4", "out.mp4", opts_canonical)
    vf_arg = cmd_can[cmd_can.index("-vf") + 1]
    assert "transpose=1" in vf_arg
    assert "fade=t=in:st=0:d=2" in vf_arg
    assert "fade=t=out:st=8.0:d=2" in vf_arg
    assert "overlay=10:10" in vf_arg

    # 2. Teste de compatibilidade com strings legadas
    opts_legacy = {
        "vcodec": "libx264",
        "rotate": "90° Horário",
        "fade_pos": "Ambos",
        "fade_dur": 2,
        "fade_type": "Vídeo e Áudio",
        "watermark": {
            "enabled": True,
            "image_path": str(wm_file),
            "position": "Superior esquerdo",
            "size": 100,
            "opacity": 100
        }
    }
    cmd_leg = engine.build_ffmpeg_command("in.mp4", "out.mp4", opts_legacy)
    vf_arg_leg = cmd_leg[cmd_leg.index("-vf") + 1]
    assert "transpose=1" in vf_arg_leg
    assert "fade=t=in:st=0:d=2" in vf_arg_leg
    assert "overlay=10:10" in vf_arg_leg


def test_ytdlp_engine_canonical_tokens_support(resource_dir):
    engine = YTDLPEngine(resource_dir)
    engine.ytdlp_bin = "yt-dlp"

    # Teste com token canônico de resolução
    with patch.object(engine, 'log_updated'):
        with patch('PySide6.QtCore.QProcess.setProgram'):
            with patch('PySide6.QtCore.QProcess.setArguments') as mock_args:
                engine.start_download(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "/tmp",
                    0,
                    {"v_fmt": "mp4", "v_res": "1080"}
                )
                args = mock_args.call_args[0][0]
                assert "-f" in args
                idx = args.index("-f")
                assert "bestvideo[height<=1080]+bestaudio/best[height<=1080]" == args[idx + 1]


def test_gui_live_retranslation(qtbot, resource_dir):
    with patch('gui.mpv_widget.MPVPlayerWidget'):
        from gui.main_window import LyraMainWindow
        from core.i18n import i18n
        
        window = LyraMainWindow("1.1.22", resource_dir)
        qtbot.addWidget(window)

        # 1. Muda para inglês
        i18n.set_language("en_US", persist=False)
        assert window.btn_convert.text() == "🚀 Convert"
        assert window.btn_stop.text() == "🛑 Stop"
        assert window.lbl_format.text() == "🎬 Format:"
        assert window.action_add_file.text() == "📄 Add File"
        assert window.table_files.horizontalHeaderItem(0).text() == "⏭️ Skip"

        # 2. Muda para espanhol
        i18n.set_language("es_ES", persist=False)
        assert window.btn_convert.text() == "🚀 Convertir"
        assert window.lbl_format.text() == "🎬 Formato:"
        assert window.action_add_file.text() == "📄 Añadir Archivo"
        assert window.table_files.horizontalHeaderItem(0).text() == "⏭️ Omitir"

        # 3. Retorna para português
        i18n.set_language("pt_BR", persist=False)
        assert window.btn_convert.text() == "🚀 Converter"
        assert window.lbl_format.text() == "🎬 Formato:"
        assert window.action_add_file.text() == "📄 Adicionar Arquivo"
        assert window.table_files.horizontalHeaderItem(0).text() == "⏭️ Pular"


def test_qt_context_menu_translations(qtbot, resource_dir):
    from PySide6.QtWidgets import QLineEdit
    from core.i18n import i18n

    le = QLineEdit()
    qtbot.addWidget(le)

    # 1. Português
    i18n.set_language("pt_BR", persist=False)
    menu_pt = le.createStandardContextMenu()
    actions_pt = [a.text().replace("&", "") for a in menu_pt.actions() if a.text()]
    assert any("Desfazer" in a for a in actions_pt)
    assert any("Copiar" in a for a in actions_pt)
    assert any("Recortar" in a for a in actions_pt)
    assert any("Colar" in a for a in actions_pt)

    # 2. Espanhol
    i18n.set_language("es_ES", persist=False)
    menu_es = le.createStandardContextMenu()
    actions_es = [a.text().replace("&", "") for a in menu_es.actions() if a.text()]
    assert any("Deshacer" in a for a in actions_es)
    assert any("Copiar" in a for a in actions_es)
    assert any("Cortar" in a for a in actions_es)
    assert any("Pegar" in a for a in actions_es)

    # 3. Alemão
    i18n.set_language("de_DE", persist=False)
    menu_de = le.createStandardContextMenu()
    actions_de = [a.text().replace("&", "") for a in menu_de.actions() if a.text()]
    assert any("Rückgängig" in a for a in actions_de)
    assert any("Kopieren" in a for a in actions_de)
    assert any("Ausschneiden" in a for a in actions_de)
    assert any("Einfügen" in a for a in actions_de)

