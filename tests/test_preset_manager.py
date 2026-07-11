import os
import json
import pytest
from core.preset_manager import PresetManager

@pytest.fixture
def manager(tmp_path, monkeypatch):
    """
    Fixture que cria uma instância de PresetManager mas altera a pasta home do usuário
    para um diretório temporário criado unicamente para o teste atual.
    """
    monkeypatch.setattr(os.path, "expanduser", lambda x: str(tmp_path))
    return PresetManager()

def test_preset_manager_initialization(manager, tmp_path):
    """
    Verifica se a pasta padrão foi criada corretamente com o caminho mockado.
    """
    expected_dir = os.path.join(str(tmp_path), ".config", "lyra")
    assert manager.preset_dir == expected_dir
    assert os.path.exists(manager.preset_dir)

def test_save_and_load_preset(manager):
    """
    Testa se um preset pode ser salvo e depois lido novamente pelo próprio gerenciador.
    """
    test_state = {"audio_bitrate": "320k", "video_codec": "libx264"}
    
    # Salvar
    success = manager.save_preset("MeuPreset", test_state)
    assert success is True
    
    # Limpar a memória interna para testar a leitura real do disco
    manager.presets_data = {}
    
    # Carregar
    loaded_data = manager.load_presets()
    assert "MeuPreset" in loaded_data
    assert loaded_data["MeuPreset"]["audio_bitrate"] == "320k"

def test_delete_preset(manager):
    """
    Testa a remoção de um preset já gravado.
    """
    manager.save_preset("Lixo", {"temp": "123"})
    
    # Validar se gravou
    assert "Lixo" in manager.presets_data
    
    # Deletar
    deleted = manager.delete_preset("Lixo")
    assert deleted is True
    assert "Lixo" not in manager.presets_data
    
    # Carregar de volta do disco para verificar se foi apagado do JSON
    loaded_data = manager.load_presets()
    assert "Lixo" not in loaded_data

def test_delete_non_existent_preset(manager):
    """
    Testa que tentar apagar um preset que não existe retorna False.
    """
    assert manager.delete_preset("Fantasma") is False
