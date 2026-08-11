import os
import pytest
from unittest.mock import MagicMock, patch
from gui.mpv_widget import MPVPlayerWidget, format_time

def test_format_time():
    assert format_time(None) == "00:00"
    assert format_time(0) == "00:00"
    assert format_time(65) == "01:05"
    assert format_time(3600) == "01:00:00"
    assert format_time(3665) == "01:01:05"

@pytest.fixture
def mock_mpv():
    with patch('mpv.MPV') as mock_class:
        instance = mock_class.return_value
        # Mock property_observer as it is used as a decorator
        instance.property_observer.return_value = lambda f: f
        yield instance

@pytest.fixture
def widget(qtbot, mock_mpv):
    w = MPVPlayerWidget()
    qtbot.addWidget(w)
    # Aguarda o QTimer(100) disparar e rodar o init_mpv
    qtbot.wait(150)
    return w

def test_init_mpv(widget, mock_mpv):
    assert widget.mpv is not None
    # Verifica se os observers foram registrados
    mock_mpv.property_observer.assert_any_call('time-pos')
    mock_mpv.property_observer.assert_any_call('duration')
    mock_mpv.property_observer.assert_any_call('pause')

def test_play_valid_file(widget, mock_mpv, tmp_path):
    dummy_file = tmp_path / "test.mp4"
    dummy_file.touch()
    
    widget.play(str(dummy_file))
    
    assert mock_mpv.pause is True
    mock_mpv.play.assert_called_once_with(str(dummy_file))

def test_play_invalid_file(widget, mock_mpv):
    widget.play("/caminho/invalido.mp4")
    # Não deve chamar o play do mpv se o arquivo não existe
    mock_mpv.play.assert_not_called()

def test_toggle_play(widget, mock_mpv):
    mock_mpv.pause = False
    widget.toggle_play()
    assert mock_mpv.pause is True
    
    widget.toggle_play()
    assert mock_mpv.pause is False

def test_stop(widget, mock_mpv):
    widget.stop()
    mock_mpv.stop.assert_called_once()
    assert widget.time_label.text() == "00:00"
    assert widget.slider.value() == 0

def test_ui_updates(widget):
    widget.duration_changed.emit(100.0)
    assert widget.duration_label.text() == "01:40"
    
    widget.time_pos_changed.emit(50.0)
    assert widget.time_label.text() == "00:50"
    # range do slider é 0-1000, 50s de 100s = 50% = 500
    assert widget.slider.value() == 500
    
    widget.pause_changed.emit(True)
    assert widget.play_btn.text() == "▶"
    
    widget.pause_changed.emit(False)
    assert widget.play_btn.text() == "⏸"

def test_audio_filters(widget, mock_mpv):
    with patch('os.path.exists', return_value=True):
        widget.update_audio_filters(volume_pct=150, drc_enabled=True, rnnoise_enabled=True)
    
    assert mock_mpv.volume == 100
    assert "lavfi=[" in mock_mpv.af
    assert "arnndn=" in mock_mpv.af
    assert "loudnorm=" in mock_mpv.af
    assert "volume=1.5" in mock_mpv.af

def test_audio_filters_disabled(widget, mock_mpv):
    widget.update_audio_filters(volume_pct=100, drc_enabled=False, rnnoise_enabled=False)
    assert mock_mpv.af == ""

def test_video_filters(widget, mock_mpv):
    watermark_config = {
        "enabled": True,
        "image_path": "/dummy/watermark.png",
        "size": 50,
        "opacity": 75,
        "position": "Centro"
    }
    with patch('os.path.exists', return_value=True):
        widget.update_video_filters(watermark_config)
    
    assert mock_mpv.hwdec == 'no'
    assert "lavfi=[" in mock_mpv.vf
    assert "movie='/dummy/watermark.png'" in mock_mpv.vf
    assert "colorchannelmixer=aa=0.75" in mock_mpv.vf
    assert "overlay=(W-w)/2:(H-h)/2" in mock_mpv.vf

def test_video_filters_disabled(widget, mock_mpv):
    watermark_config = {"enabled": False}
    widget.update_video_filters(watermark_config)
    assert mock_mpv.vf == ""

def test_slider_seek(widget, mock_mpv):
    widget.duration_changed.emit(100.0)
    
    widget.on_slider_pressed()
    assert widget._is_seeking is True
    
    widget.slider.setValue(500)
    widget.on_slider_moved(500)
    assert widget.time_label.text() == "00:50"
    
    widget.on_slider_released()
    assert widget._is_seeking is False
    assert mock_mpv.time_pos == 50.0

def test_audio_delay_and_track(widget, mock_mpv):
    widget.set_audio_delay(1.5)
    assert mock_mpv.audio_delay == 1.5
    
    widget.set_audio_track(2)
    assert mock_mpv.aid == 2
