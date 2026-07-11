import pytest
from core.ffmpeg_engine import FFmpegEngine

@pytest.fixture
def engine():
    # Iniciamos sem dependência de UI instanciando apenas o core lógico
    return FFmpegEngine(resource_dir="/tmp/mock_dir")

def test_format_time(engine):
    """
    Testa a conversão de segundos inteiros e em float para HH:MM:SS.
    """
    assert engine.format_time(0) == "00:00:00"
    assert engine.format_time(65) == "00:01:05"
    assert engine.format_time(3600) == "01:00:00"
    assert engine.format_time(3665.5) == "01:01:05"

def test_is_video_format(engine):
    """
    Testa a blindagem (detecção correta) se uma extensão final é um formato de vídeo 
    (ex: mkv, mp4) contra imagens e áudios.
    """
    # Formatos de vídeo
    assert engine.is_video_format("video.mp4") is True
    assert engine.is_video_format("C:/pasta/filme.mkv") is True
    assert engine.is_video_format("clip.webm") is True
    assert engine.is_video_format("clip.avi") is True
    
    # Formatos de áudio/imagem/legenda
    assert engine.is_video_format("musica.mp3") is False
    assert engine.is_video_format("som.wav") is False
    assert engine.is_video_format("imagem.jpg") is False
    assert engine.is_video_format("foto.webp") is False
    assert engine.is_video_format("legenda.srt") is False

def test_parse_bitrate_to_kbps(engine):
    """
    Testa o interpretador de taxa de bits string para inteiro kbps.
    """
    # Casos vazios ou padrões
    assert engine.parse_bitrate_to_kbps("") is None
    assert engine.parse_bitrate_to_kbps("default") is None
    
    # Casos Megabits
    assert engine.parse_bitrate_to_kbps("2M") == 2000
    assert engine.parse_bitrate_to_kbps("5.5m") == 5500
    assert engine.parse_bitrate_to_kbps("1 mbps") == 1000
    
    # Casos Kilobits
    assert engine.parse_bitrate_to_kbps("500k") == 500
    assert engine.parse_bitrate_to_kbps("320 kbps") == 320
    
    # Numéricos puros (assumimos como kbps na regra de negócio)
    assert engine.parse_bitrate_to_kbps("1500") == 1500
