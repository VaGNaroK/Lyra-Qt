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


# ==============================================================================
# Testes do Pipeline GPU — scale_cuda / scale_npp / fallback CPU
# ==============================================================================

def test_detect_cuda_scale_filter_parses_npp(monkeypatch):
    """
    Testa que _detect_cuda_scale_filter retorna 'scale_npp' quando
    o output de `ffmpeg -filters` contém a string 'scale_npp'.
    """
    import subprocess
    from unittest.mock import MagicMock

    mock_result = MagicMock()
    mock_result.stdout = "... scale_npp ... scale_cuda ..."
    mock_result.stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)
    # Cria engine com detecção mockada
    engine = FFmpegEngine(resource_dir="/tmp/mock_dir")
    # Re-executa manualmente para testar o método isolado
    result = engine._detect_cuda_scale_filter()
    assert result == "scale_npp", "scale_npp deve ter prioridade sobre scale_cuda"


def test_detect_cuda_scale_filter_parses_cuda_only(monkeypatch):
    """
    Testa que _detect_cuda_scale_filter retorna 'scale_cuda' quando
    apenas scale_cuda está disponível (sem scale_npp).
    """
    import subprocess
    from unittest.mock import MagicMock

    mock_result = MagicMock()
    mock_result.stdout = "... scale_cuda ..."
    mock_result.stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: mock_result)
    engine = FFmpegEngine(resource_dir="/tmp/mock_dir")
    result = engine._detect_cuda_scale_filter()
    assert result == "scale_cuda"


def test_nvenc_scale_uses_scale_npp(engine):
    """
    Testa que com _cuda_scale_filter='scale_npp', o bloco de resize NVENC
    injeta scale_npp no -vf e mantém -hwaccel_output_format cuda.
    Verifica também que NÃO usa scale= lavfi (CPU).
    """
    from unittest.mock import patch

    engine._cuda_scale_filter = "scale_npp"

    options = {
        "vcodec": "h264_nvenc",
        "vsize": "1920x1080",
    }

    with patch.object(engine, "get_video_resolution", return_value=(3840, 2160)):
        cmd = engine.build_ffmpeg_command("input.mp4", "output.mp4", options)

    cmd_str = " ".join(cmd)

    # 🔒 FIX: hwaccel_output_format deve estar presente mesmo com resize
    assert "-hwaccel_output_format" in cmd
    assert cmd[cmd.index("-hwaccel_output_format") + 1] == "cuda"

    # Filtro GPU deve ser scale_npp
    assert "scale_npp=1920:" in cmd_str
    assert "interp=super" in cmd_str

    # NÃO deve usar scale= lavfi (CPU)
    assert "scale=1920" not in cmd_str
    assert "flags=lanczos" not in cmd_str


def test_nvenc_scale_uses_scale_cuda_fallback(engine):
    """
    Testa que com _cuda_scale_filter='scale_cuda', o bloco de resize NVENC
    injeta scale_cuda no -vf com interp_algo=lanczos.
    """
    from unittest.mock import patch

    engine._cuda_scale_filter = "scale_cuda"

    options = {
        "vcodec": "h264_nvenc",
        "vsize": "1280x720",
    }

    with patch.object(engine, "get_video_resolution", return_value=(1920, 1080)):
        cmd = engine.build_ffmpeg_command("input.mp4", "output.mp4", options)

    cmd_str = " ".join(cmd)

    assert "scale_cuda=1280:" in cmd_str
    assert "interp_algo=lanczos" in cmd_str
    assert "flags=lanczos" not in cmd_str


def test_nvenc_scale_cpu_fallback_when_gpu_unavailable(engine):
    """
    Testa que com _cuda_scale_filter='cpu', o sistema cai de volta
    para scale= lavfi e NÃO injeta -hwaccel_output_format cuda.
    Cobre o cenário de máquinas sem GPU ou FFmpeg sem CUDA.
    """
    from unittest.mock import patch

    engine._cuda_scale_filter = "cpu"

    options = {
        "vcodec": "h264_nvenc",
        "vsize": "1280x720",
    }

    with patch.object(engine, "get_video_resolution", return_value=(1920, 1080)):
        cmd = engine.build_ffmpeg_command("input.mp4", "output.mp4", options)

    cmd_str = " ".join(cmd)

    # Sem GPU, não deve ter hwaccel_output_format
    assert "-hwaccel_output_format" not in cmd

    # Deve usar scale= lavfi (CPU) como fallback
    assert "scale=" in cmd_str
    assert "flags=lanczos" in cmd_str

    # NÃO deve usar filtros GPU
    assert "scale_cuda" not in cmd_str
    assert "scale_npp" not in cmd_str


def test_nvenc_scale_cpu_fallback_when_watermark_active(engine, tmp_path):
    """
    Testa que mesmo com GPU disponível, o sistema desativa hwaccel_output_format
    e usa scale= CPU quando watermark está ativo.
    🔒 FIX: Bug 24 do project-memory — overlay (CPU) é incompatível com hwdec GPU.
    """
    from unittest.mock import patch

    engine._cuda_scale_filter = "scale_npp"

    mock_image = tmp_path / "logo.png"
    mock_image.write_text("fake")

    options = {
        "vcodec": "h264_nvenc",
        "vsize": "1280x720",
        "watermark": {
            "enabled": True,
            "image_path": str(mock_image),
            "position": "Inferior direito",
            "size": 50,
            "opacity": 80,
        },
    }

    with patch.object(engine, "get_video_resolution", return_value=(1920, 1080)):
        cmd = engine.build_ffmpeg_command("input.mp4", "output.mp4", options)

    # Com watermark ativo, hwaccel_output_format NÃO deve estar presente
    assert "-hwaccel_output_format" not in cmd

    # scale= CPU deve ser usado (compatível com overlay lavfi)
    cmd_str = " ".join(cmd)
    assert "scale=" in cmd_str
    assert "flags=lanczos" in cmd_str
    assert "scale_npp" not in cmd_str


# ==============================================================================
# Testes de Resolução de Binário e Argumentos NVENC (Bug 42)
# ==============================================================================

def test_build_ffmpeg_command_binary_priority(engine):
    """
    Testa que options['ffmpeg_path'] genérico ('ffmpeg', 'ffmpeg.exe', '', None)
    recorre prioritariamente para engine.ffmpeg_bin (binário local embutido).
    Também testa que caminho customizado explícito é respeitado.
    """
    engine.ffmpeg_bin = "/app/share/lyra/assets/bin/ffmpeg"

    # Casos padrão/genéricos devem usar o engine.ffmpeg_bin
    assert engine.build_ffmpeg_command("in.mp4", "out.mp4", {})[0] == "/app/share/lyra/assets/bin/ffmpeg"
    assert engine.build_ffmpeg_command("in.mp4", "out.mp4", {"ffmpeg_path": "ffmpeg"})[0] == "/app/share/lyra/assets/bin/ffmpeg"
    assert engine.build_ffmpeg_command("in.mp4", "out.mp4", {"ffmpeg_path": "ffmpeg.exe"})[0] == "/app/share/lyra/assets/bin/ffmpeg"
    assert engine.build_ffmpeg_command("in.mp4", "out.mp4", {"ffmpeg_path": ""})[0] == "/app/share/lyra/assets/bin/ffmpeg"

    # Caminho personalizado deve ser preservado
    custom_path = "/usr/local/bin/custom-ffmpeg"
    cmd_custom = engine.build_ffmpeg_command("in.mp4", "out.mp4", {"ffmpeg_path": custom_path})
    assert cmd_custom[0] == custom_path


def test_ffmpeg_bin_cross_platform_resolution(monkeypatch, tmp_path):
    """
    Testa a resolução de ffmpeg_bin e ffprobe_bin em ambientes Windows (.exe) e Linux.
    """
    import sys
    bin_dir = tmp_path / "assets" / "bin"
    bin_dir.mkdir(parents=True)

    # 1. Simulação Windows
    (bin_dir / "ffmpeg.exe").write_text("")
    (bin_dir / "ffprobe.exe").write_text("")
    monkeypatch.setattr(sys, "platform", "win32")

    engine_win = FFmpegEngine(resource_dir=str(tmp_path))
    assert engine_win.ffmpeg_bin.endswith("ffmpeg.exe")
    assert engine_win.ffprobe_bin.endswith("ffprobe.exe")

    # 2. Simulação Linux
    (bin_dir / "ffmpeg").write_text("")
    (bin_dir / "ffprobe").write_text("")
    monkeypatch.setattr(sys, "platform", "linux")

    engine_linux = FFmpegEngine(resource_dir=str(tmp_path))
    assert engine_linux.ffmpeg_bin.endswith("ffmpeg")
    assert not engine_linux.ffmpeg_bin.endswith(".exe")
    assert engine_linux.ffprobe_bin.endswith("ffprobe")
    assert not engine_linux.ffprobe_bin.endswith(".exe")


def test_nvenc_cq_flags_no_duplication_with_crf(engine):
    """
    Testa que ao codificar com NVENC e CRF ativado, a flag -cq não é duplicada
    (eliminando o antigo conflito entre -cq 18 estático e -cq do CRF).
    """
    options = {
        "vcodec": "h264_nvenc",
        "crf_enabled": True,
        "crf_value": 23,
    }
    cmd = engine.build_ffmpeg_command("input.mp4", "output.mp4", options)

    # -cq deve ocorrer exatamente 1 vez na lista
    assert cmd.count("-cq") == 1
    assert cmd[cmd.index("-cq") + 1] == "23"
    assert "18" not in cmd  # Não deve haver o antigo -cq 18 estático

    # -qmin e -qmax devem acompanhar o CRF
    assert "-qmin" in cmd and cmd[cmd.index("-qmin") + 1] == "23"
    assert "-qmax" in cmd and cmd[cmd.index("-qmax") + 1] == "23"

    # Presets NVENC de alto desempenho mantidos
    assert "-preset" in cmd and cmd[cmd.index("-preset") + 1] == "p7"
    assert "-tune" in cmd and cmd[cmd.index("-tune") + 1] == "hq"
    assert "-profile:v" in cmd and cmd[cmd.index("-profile:v") + 1] == "high"


def test_nvenc_bitrate_mode_no_cq(engine):
    """
    Testa que no modo taxa de bits (CRF desativado), o NVENC não injeta -cq,
    utilizando corretamente -b:v e -maxrate.
    """
    options = {
        "vcodec": "h264_nvenc",
        "crf_enabled": False,
        "vbitrate": "5M",
    }
    cmd = engine.build_ffmpeg_command("input.mp4", "output.mp4", options)

    assert "-cq" not in cmd
    assert "-qmin" not in cmd
    assert "-qmax" not in cmd
    assert "-b:v" in cmd and cmd[cmd.index("-b:v") + 1] == "5M"
    assert "-maxrate" in cmd and cmd[cmd.index("-maxrate") + 1] == "5M"


def test_nvenc_default_fallback_cq(engine):
    """
    Testa que se nem CRF nem bitrate forem informados, o NVENC recebe
    o fallback seguro -cq 23 sem duplicidade.
    """
    options = {
        "vcodec": "h264_nvenc",
        "crf_enabled": False,
        "vbitrate": "default",
    }
    cmd = engine.build_ffmpeg_command("input.mp4", "output.mp4", options)

    assert cmd.count("-cq") == 1
    assert cmd[cmd.index("-cq") + 1] == "23"

