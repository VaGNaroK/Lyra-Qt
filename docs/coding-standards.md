# Padrões de Codificação (Coding Standards)

## Padrões da Linguagem
- **Linguagem**: Python 3.10 ou superior.
- **Estilo**: Adoção das diretrizes da PEP 8 para estilo de código (com exceções maleáveis para limites de linha se prejudicar a leitura do Qt).
- **Nomenclatura**:
  - `snake_case` para variáveis, atributos de classe e nomes de métodos/funções.
  - `CamelCase` para nomes de Classes.
  - `UPPER_SNAKE_CASE` para constantes globais.

## Padrões PySide6
- Importações devem vir da raiz principal: `from PySide6.QtWidgets import ...`.
- Evite wildcard imports (`from PySide6 import *`), declare explicitamente o que usar para otimizar build e linting.
- Instâncias filhas dentro de widgets (`QGroupBox`, `QVBoxLayout`) devem sempre passar `self` ou o container parent, garantindo desalocação correta de memória pelo Qt C++.

## Tratamento de Erros e Logs
- Nunca use `print()` nu e cru em código de produção, pois janelas isoladas (`pythonw`) e Flatpaks perdem saída de terminal.
- Use os signals integrados (`log_updated`) para mostrar erros técnicos na aba apropriada para o usuário.
- Utilize blocos `try/except` robustos em interações com o sistema de arquivos ou chamadas de terminal de `subprocess`. Evite exceções vazias (`pass`); se algo falhar em silêncio (ex: pegar metadados da mídia não for suportado), documente internamente.

## Segurança e Blindagem
- Arquivos passados para filtros complexos do ffmpeg (como `subtitles='path'`) devem ter seus caminhos limpos/escapados (`.replace('\\', '\\\\')`) no Windows.
- Lidando com OS: Verifique `os.name == 'nt'` antes de aplicar flags do Windows (ex: ocultar a janela preta do `STARTUPINFO` do subprocess).

## Imports Relativos (Arquitetura)
Use blocos `try/except ImportError` ao carregar módulos internos caso exista dualidade de execução (da raiz do projeto vs pacotes embutidos pelo PyInstaller).
Ex:
```python
try:
    from core.ffmpeg_engine import FFmpegEngine
except ImportError:
    from ffmpeg_engine import FFmpegEngine
```
