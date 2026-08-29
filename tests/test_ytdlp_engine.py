import pytest
from PySide6.QtCore import QProcess
from core.ytdlp_engine import YTDLPEngine
import os

@pytest.fixture
def ytdlp():
    return YTDLPEngine(resource_dir="/tmp/mock_dir")

def test_start_download_audio(ytdlp, monkeypatch):
    """
    Testa a geração de argumentos para extração exclusiva de áudio (mode 1) no yt-dlp.
    """
    cmd_interceptado = {}
    
    # Fazemos o mock do start do QProcess para não rodar o binário real
    def mock_start(self):
        cmd_interceptado["program"] = self.program()
        cmd_interceptado["arguments"] = self.arguments()
        
    monkeypatch.setattr(QProcess, "start", mock_start)
    
    ytdlp.start_download(
        url="https://youtube.com/test", 
        dest_path="/tmp/out", 
        mode=1, 
        options={"a_fmt": "mp3", "a_bitrate": "320K"}
    )
    
    args = cmd_interceptado["arguments"]
    assert "-x" in args
    assert "--audio-format" in args
    assert "mp3" in args
    assert "--audio-quality" in args
    assert "320K" in args
    assert "https://youtube.com/test" in args
    assert os.path.join("/tmp/out", "%(title)s.%(ext)s") in args

def test_start_download_video(ytdlp, monkeypatch):
    """
    Testa a geração de argumentos com filtros complexos de resolução para vídeo (mode 0).
    """
    cmd_interceptado = {}
    
    def mock_start(self):
        cmd_interceptado["program"] = self.program()
        cmd_interceptado["arguments"] = self.arguments()
        
    monkeypatch.setattr(QProcess, "start", mock_start)
    
    ytdlp.start_download(
        url="https://youtube.com/video", 
        dest_path="/tmp/out_vid", 
        mode=0, 
        options={"v_fmt": "mkv", "v_res": "1080p (FullHD)"}
    )
    
    args = cmd_interceptado["arguments"]
    
    assert "-f" in args
    # Verifica se a string limitante de altura foi incorporada corretamente no argumento
    assert "bestvideo[height<=1080]+bestaudio/best[height<=1080]" in args
    assert "--merge-output-format" in args
    assert "mkv" in args
    assert "-x" not in args

def test_start_download_invalid_url(ytdlp, monkeypatch):
    """
    Testa se URLs inválidas (sem http/https) emitem erro e não iniciam processo.
    """
    started = False
    def mock_start(self):
        nonlocal started
        started = True
        
    monkeypatch.setattr(QProcess, "start", mock_start)
    
    erros = []
    ytdlp.error_occurred.connect(erros.append)
    
    ytdlp.start_download(
        url="ftp://invalid.com/file.mp4",
        dest_path="/tmp/out",
        mode=0,
        options={}
    )
    
    assert not started
    assert len(erros) == 1
    assert "URL inválida" in erros[0]

def test_ytdlp_bin_resolution(monkeypatch):
    """
    Testa a resolução de caminhos do binário do yt-dlp em Linux/Windows.
    """
    import sys
    # Simula Windows
    monkeypatch.setattr(sys, "platform", "win32")
    engine_win = YTDLPEngine(resource_dir="/app")
    assert engine_win.ytdlp_bin == os.path.join("/app", "assets", "bin", "yt-dlp.exe")
    
    # Simula Linux com fallback
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(os.path, "isfile", lambda p: False)
    engine_linux = YTDLPEngine(resource_dir="/app")
    assert engine_linux.ytdlp_bin == "yt-dlp"

