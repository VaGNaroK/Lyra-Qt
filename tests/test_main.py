import os
import sys
import pytest
from main import _resolve_resource_dir

def test_resolve_resource_dir_normal(monkeypatch):
    """
    Testa o retorno convencional do script rodando via Python ou IDE.
    """
    if hasattr(sys, "frozen"):
        monkeypatch.delattr(sys, "frozen", raising=False)
    
    # O diretório retornado deve ser exatamente a raiz onde o main.py reside
    expected = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    assert _resolve_resource_dir() == expected

def test_resolve_resource_dir_frozen(monkeypatch):
    """
    Simula o empacotamento com PyInstaller no Windows, que usa sys._MEIPASS.
    """
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", "/tmp/mock_meipass", raising=False)
    
    assert _resolve_resource_dir() == "/tmp/mock_meipass"


def test_resolve_resource_dir_flatpak(monkeypatch, tmp_path):
    """
    Testa a resolução de diretório quando rodando em sandbox Flatpak.
    """
    if hasattr(sys, "frozen"):
        monkeypatch.delattr(sys, "frozen", raising=False)

    monkeypatch.setenv("FLATPAK_ID", "com.github.vagnarok.lyra")
    from unittest.mock import patch

    with patch("os.path.isdir", side_effect=lambda p: p == "/app/share/lyra"):
        from main import _resolve_resource_dir
        # Re-import ou chamada direta com flatpak mockado
        monkeypatch.setattr("main.IS_FLATPAK", True)
        assert _resolve_resource_dir() == "/app/share/lyra"

