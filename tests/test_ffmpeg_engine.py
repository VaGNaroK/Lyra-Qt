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

def test_build_ffmpeg_command_cover_art_audio(engine):
    """
    Testa a injeção correta da Capa (Cover Art) ao converter para áudio.
    Espera-se o '-i', o '-map 1:v:0' e o disposition.
    """
    options = {
        "metadata": {
            "cover_path": "/tmp/mock_cover.jpg"
        }
    }
    from unittest.mock import patch
    with patch('os.path.isfile', return_value=True):
        cmd = engine.build_ffmpeg_command("input.wav", "output.mp3", options)
        
    # A capa deve ser o segundo input
    assert cmd.count("-i") == 2
    assert "/tmp/mock_cover.jpg" in cmd
    
    # As flags de injeção ID3/Attached Pic devem estar presentes
    assert "1:v:0" in cmd
    assert "attached_pic" in cmd
    assert "-vn" not in cmd  # Não deve desabilitar vídeo, pois o vídeo é a capa

def test_build_ffmpeg_command_cover_art_video_bypass(engine):
    """
    Testa se a engine ignora silenciosamente a injeção da Capa ao converter para vídeo.
    Evita crashes ao misturar mapping de thumbnail num arquivo .mp4 convencional.
    """
    options = {
        "metadata": {
            "cover_path": "/tmp/mock_cover.jpg"
        }
    }
    from unittest.mock import patch
    with patch('os.path.isfile', return_value=True):
        cmd = engine.build_ffmpeg_command("input.mp4", "output.mp4", options)
        
    # Deve haver apenas o input principal
    assert cmd.count("-i") == 1
    assert "/tmp/mock_cover.jpg" not in cmd
    assert "attached_pic" not in cmd

def test_build_ffmpeg_command_speed_pitch_preserved(engine):
    """
    Testa a injeção do controle de velocidade preservando o tom (Pitch Preserved).
    Verifica a matemática do setpts e a cadeia do atempo para valores menores que 0.5.
    """
    options = {
        "speed": {
            "value": 0.25,
            "preserve_pitch": True
        }
    }
    cmd = engine.build_ffmpeg_command("input.mp4", "output.mp4", options)
    cmd_str = " ".join(cmd)
    
    # Video speed: 1.0 / 0.25 = 4.0
    assert "setpts=4.0*PTS" in cmd_str
    
    # Audio pitch (atempo limit is 0.5)
    # tempo = 0.25. While tempo < 0.5: atempo=0.5 -> tempo = 0.5. then atempo=0.5.
    # Total: atempo=0.5,atempo=0.5
    assert "atempo=0.5" in cmd_str
    assert cmd_str.count("atempo=0.5") >= 2

def test_build_ffmpeg_command_speed_no_pitch(engine):
    """
    Testa a injeção do controle de velocidade SEM preservar o tom (No Pitch).
    Verifica se o asetrate e aresample são injetados corretamente.
    """
    options = {
        "speed": {
            "value": 2.0,
            "preserve_pitch": False
        }
    }
    from unittest.mock import patch
    with patch.object(engine, 'get_media_specs', return_value={"afreq": "48000 Hz"}):
        cmd = engine.build_ffmpeg_command("input.mp4", "output.mp4", options)
    
    cmd_str = " ".join(cmd)
    
    # Video speed: 1.0 / 2.0 = 0.5
    assert "setpts=0.5*PTS" in cmd_str
    
    # Audio speed (No Pitch): asetrate = 48000 * 2.0 = 96000
    assert "asetrate=96000.0" in cmd_str
    # Resample back to original
    assert "aresample=48000" in cmd_str

def test_advanced_video_handbrake_options(engine):
    """
    Testa se as configurações Handbrake (preset, tune, profile, level, color range, cfr/vfr)
    são corretamente renderizadas pela engine no formato de destino.
    """
    options = {
        "vcodec": "libx264",
        "vfps": "30",
        "video_advanced": {
            "fps_mode": "cfr",
            "color_range": "Limited",
            "preset": "slow",
            "tune": "film",
            "profile": "high",
            "level": "4.1",
            "x264_opts": "bframes=3",
            "turbo_first_pass": False
        }
    }
    cmd = engine.build_ffmpeg_command("input.mp4", "output.mp4", options, pass_num=1)
    
    assert "-preset" in cmd
    assert cmd[cmd.index("-preset") + 1] == "slow"
    
    assert "-profile:v" in cmd
    assert cmd[cmd.index("-profile:v") + 1] == "high"
    
    assert "-level" in cmd
    assert cmd[cmd.index("-level") + 1] == "4.1"
    
    assert "-tune" in cmd
    assert cmd[cmd.index("-tune") + 1] == "film"
    
    assert "-x264-params" in cmd
    assert cmd[cmd.index("-x264-params") + 1] == "bframes=3"
    
    assert "-color_range" in cmd
    assert cmd[cmd.index("-color_range") + 1] == "tv"
    
    # 🔒 FIX: FFmpeg 5+ deprecou -vsync em favor de -fps_mode. A engine usa -fps_mode corretamente.
    assert "-fps_mode" in cmd
    assert cmd[cmd.index("-fps_mode") + 1] == "cfr"

def test_advanced_video_turbo_pass(engine):
    """
    Testa se o Turbo Pass substitui o preset por ultrafast na passada 1
    quando configurado.
    """
    options = {
        "vcodec": "libx264",
        "video_advanced": {
            "preset": "veryslow",
            "turbo_first_pass": True
        }
    }
    # Pass 1
    cmd1 = engine.build_ffmpeg_command("input.mp4", "output.mp4", options, pass_num=1)
    assert "-preset" in cmd1
    assert cmd1[cmd1.index("-preset") + 1] == "ultrafast" # Override feito pelo turbo
    
    # Pass 2
    cmd2 = engine.build_ffmpeg_command("input.mp4", "output.mp4", options, pass_num=2)
    assert "-preset" in cmd2
    assert cmd2[cmd2.index("-preset") + 1] == "veryslow" # Preset original restaurado
