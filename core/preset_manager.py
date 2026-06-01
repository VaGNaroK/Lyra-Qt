import os
import json

class PresetManager:
    def __init__(self):
        self.preset_dir = os.path.join(os.path.expanduser("~"), ".config", "lyra")
        self.preset_file = os.path.join(self.preset_dir, "presets.json")
        self.presets_data = {}
        os.makedirs(self.preset_dir, exist_ok=True)

    def load_presets(self) -> dict:
        self.presets_data = {}
        if os.path.exists(self.preset_file):
            try:
                with open(self.preset_file, "r", encoding="utf-8") as f:
                    self.presets_data = json.load(f)
            except Exception as e:
                print(f"⚠️ Erro ao carregar presets: {e}")
                self.presets_data = {}
        return self.presets_data

    def save_preset(self, name: str, state: dict) -> bool:
        self.presets_data[name] = state
        return self._write_to_disk()

    def delete_preset(self, name: str) -> bool:
        if name in self.presets_data:
            self.presets_data.pop(name)
            return self._write_to_disk()
        return False

    def _write_to_disk(self) -> bool:
        try:
            with open(self.preset_file, "w", encoding="utf-8") as f:
                json.dump(self.presets_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Erro crítico ao salvar o preset no disco: {e}")
            return False