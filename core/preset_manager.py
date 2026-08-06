import os
import json
import logging
logger = logging.getLogger(__name__)

class PresetManager:
    """
    Gerencia o salvamento, carregamento e exclusão de presets do usuário.
    Os presets são salvos localmente em um arquivo JSON na pasta de configurações do usuário.
    """
    def __init__(self):
        import sys
        # ✅ FIX: Usar o diretório correto conforme o sistema operacional
        if sys.platform == "win32":
            base_dir = os.environ.get("APPDATA", os.path.expanduser("~"))
            self.preset_dir = os.path.join(base_dir, "Lyra")
        elif sys.platform == "darwin":
            self.preset_dir = os.path.join(
                os.path.expanduser("~"), "Library", "Application Support", "Lyra"
            )
        else:
            # Linux/BSD
            self.preset_dir = os.path.join(os.path.expanduser("~"), ".config", "lyra")

        self.preset_file = os.path.join(self.preset_dir, "presets.json")
        self.presets_data = {}
        os.makedirs(self.preset_dir, exist_ok=True)

        # ✅ Migração automática: mover presets do caminho antigo para o novo (apenas Windows)
        if sys.platform == "win32":
            old_file = os.path.join(os.path.expanduser("~"), ".config", "lyra", "presets.json")
            if os.path.exists(old_file) and not os.path.exists(self.preset_file):
                import shutil
                try:
                    shutil.copy2(old_file, self.preset_file)
                except Exception:
                    pass

    def load_presets(self) -> dict:
        """
        Carrega todos os presets do arquivo JSON no disco.
        
        Returns:
            dict: Um dicionário contendo todos os presets salvos.
        """
        self.presets_data = {}
        if os.path.exists(self.preset_file):
            try:
                with open(self.preset_file, "r", encoding="utf-8") as f:
                    self.presets_data = json.load(f)
            except Exception as e:
                logger.warning("Erro ao carregar presets: %s", e)
                self.presets_data = {}
        return self.presets_data

    def save_preset(self, name: str, state: dict) -> bool:
        """
        Salva o estado atual da interface gráfica como um novo preset.
        
        Args:
            name (str): O nome do preset.
            state (dict): O dicionário de configurações da GUI.
            
        Returns:
            bool: True se salvo com sucesso, False caso contrário.
        """
        self.presets_data[name] = state
        return self._write_to_disk()

    def delete_preset(self, name: str) -> bool:
        """
        Deleta um preset específico pelo nome.
        
        Args:
            name (str): O nome do preset a ser excluído.
            
        Returns:
            bool: True se excluído com sucesso, False caso não encontrado ou falha.
        """
        if name in self.presets_data:
            self.presets_data.pop(name)
            return self._write_to_disk()
        return False

    def _write_to_disk(self) -> bool:
        """
        Método privado para consolidar e escrever o dicionário de presets atual no disco.
        
        Returns:
            bool: True em caso de sucesso na escrita.
        """
        try:
            with open(self.preset_file, "w", encoding="utf-8") as f:
                json.dump(self.presets_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error("Erro crítico ao salvar o preset no disco: %s", e)
            return False