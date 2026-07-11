import os
import pytest
from core.ffmpeg_engine import FFmpegEngine

@pytest.fixture
def engine():
    return FFmpegEngine(resource_dir="/tmp/mock_dir")

def test_watermark_filter_injection(engine, tmp_path):
    """
    Testa se o filtro de vídeo (-vf) é construído corretamente ao ativar a marca d'água.
    """
    # Cria uma imagem de mentira para passar na validação de arquivo existente
    mock_image = tmp_path / "logo.png"
    mock_image.write_text("fake image content")
    img_path = str(mock_image)
    
    options = {
        "vcodec": "libx264",
        "watermark": {
            "enabled": True,
            "image_path": img_path,
            "position": "Inferior direito",
            "size": 50,
            "opacity": 75
        }
    }
    
    cmd = engine.build_ffmpeg_command("input.mp4", "output.mp4", options)
    
    assert "-vf" in cmd
    
    vf_index = cmd.index("-vf")
    vf_arg = cmd[vf_index + 1]
    
    escaped_img = img_path.replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
    
    # Valida a presença dos parâmetros matemáticos na string
    assert f"movie='{escaped_img}'[wm]" in vf_arg
    assert "scale=iw*0.5:ih*0.5" in vf_arg
    assert "colorchannelmixer=aa=0.75[wm_mod]" in vf_arg
    
    # Valida o overlay posicional (Inferior direito padrão: W-w-10:H-h-10)
    assert "[in][wm_mod]overlay=W-w-10:H-h-10" in vf_arg

def test_watermark_filter_with_existing_vf(engine, tmp_path):
    """
    Testa se a marca d'água se mescla corretamente (formando o background [bg])
    quando já existem filtros de vídeo atuando (ex: Crop).
    """
    mock_image = tmp_path / "logo.png"
    mock_image.touch()
    img_path = str(mock_image)
    
    options = {
        "vcodec": "libx264",
        "crop": {"enabled": True, "t": 10, "b": 10, "l": 0, "r": 0},
        "watermark": {
            "enabled": True,
            "image_path": img_path,
            "position": "Superior esquerdo",
            "size": 100,
            "opacity": 100
        }
    }
    
    cmd = engine.build_ffmpeg_command("input.mp4", "output.mp4", options)
    vf_index = cmd.index("-vf")
    vf_arg = cmd[vf_index + 1]
    
    # Deve conter o crop virando [bg]
    assert "crop=iw-0-0:ih-10-10:0:10[bg]" in vf_arg
    
    # Deve fundir o background com o modificador overlay nas coordenadas corretas (10:10)
    assert "[bg][wm_mod]overlay=10:10" in vf_arg

def test_watermark_disabled_fallback(engine, tmp_path):
    """
    Testa se a pipeline segue o fluxo natural ignorando os injetores caso a funcionalidade esteja desmarcada.
    """
    mock_image = tmp_path / "logo.png"
    mock_image.touch()
    
    options = {
        "vcodec": "libx264",
        "crop": {"enabled": True, "t": 10, "b": 10, "l": 0, "r": 0},
        "watermark": {
            "enabled": False, # Desativado
            "image_path": str(mock_image)
        }
    }
    
    cmd = engine.build_ffmpeg_command("input.mp4", "output.mp4", options)
    vf_index = cmd.index("-vf")
    vf_arg = cmd[vf_index + 1]
    
    # Deve ter apenas o Crop limpo, sem o complex_filtergraph da marca d'água
    assert "crop=iw-0-0:ih-10-10:0:10" == vf_arg
    assert "[bg]" not in vf_arg
    assert "movie=" not in vf_arg
