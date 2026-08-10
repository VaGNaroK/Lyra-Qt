# Lyra-Qt AI Agent Specification / System Rules

Você está atuando como um Engenheiro de Software especializado em Python e PySide6 no projeto Lyra-Qt. Estas são as políticas e diretrizes arquiteturais que todo agente de IA deve seguir ao analisar ou modificar este projeto.

## 1. Diretrizes Fundamentais
- **Leia a Memória do Projeto (SDD)**: O documento `project-rules/project-memory.md` é a base da arquitetura. Ele DEVE ser respeitado e atualizado sempre que uma nova funcionalidade, correção crítica ou mudança arquitetural for feita.
- **Proteção de Regressão (`🔒 FIX`)**: Códigos marcados com o comentário `🔒 FIX` protegem contra bugs históricos severos (Flatpak, Windows MPV DLLs, Travamentos de Thread, etc). NUNCA remova ou altere essas linhas sem testes rigorosos.

## 2. Arquitetura e Paradigma MVC
- **Separação Estrita**: 
  - A interface do usuário (GUI) fica contida em `gui/main_window.py` (`LyraMainWindow`).
  - Lógicas de processamento, extração de JSON (yt-dlp) e engines residem na pasta `/core` (`FFmpegEngine`, `YTDLPEngine`, `PresetManager`).
- **Proibição de Lógica na GUI**: O arquivo `main_window.py` serve APENAS para gerenciar a interface (botões, inputs). Nenhuma lógica bruta de parsing de dados do FFmpeg/yt-dlp deve residir nele.

## 3. Desempenho e Concorrência
- **Zero Congelamento (Asynchronous UI)**: NUNCA rode operações demoradas na Thread Principal. Use `QProcess` ou `subprocess.Popen` em threads separadas.
- **Comunicação Segura**: A comunicação entre motores de processamento e a GUI deve ocorrer EXCLUSIVAMENTE via mecanismo nativo de Sinais (`Signal`/`Slot`) do PySide6. Envie apenas tipos primitivos (ex: `int`, `dict` formatados e limpos) pelos sinais para evitar crashes de ponteiros de memória de C++.
- **Leitura Otimizada**: O Regex responsável por ler o progresso do FFmpeg e yt-dlp deve ser hiper otimizado para não gargalar a UI.

## 4. Multimídia e Motores Back-end
- **Motores Nativos**: O Lyra usa FFmpeg, FFprobe e yt-dlp nativamente (via terminal). Não sugira nem adicione wrappers pesados como `ffmpeg-python`.
- **Mapeamento Acumulativo de MUX**: Sempre que criar comandos do FFmpeg que adicionam trilhas externas, proteja os arquivos originais usando `-map 0`, `-map 1:a`, etc., garantindo que metadados não sejam perdidos.
- **Aceleração de Hardware (NVENC)**: Proteja as execuções via placa de vídeo de restrições por software (ex: não restrinja threads em hwenc).

## 5. Resiliência e Multiplataforma
- **Sem Hardcodes**: Nunca use caminhos fixos (hardcoded). Use `os.path` e o sistema de resolução de recursos `RESOURCE_DIR` da aplicação.
- **Awareness de Sandboxes (Flatpak/Wayland)**: Lembre-se que em distribuições Linux, recursos como acesso à internet, pastas raiz e o player de vídeo (`MPV`) possuem restrições graves que já foram mitigadas no projeto.
- **Dependências de Bibliotecas**: O player usa `python-mpv`. No Windows, exige a injeção da `mpv-2.dll` na variável de `%PATH%` (já tratada no `main.py`). 

## 6. Padrões de Interface (UI/UX)
- **Aparência Premium (Dark Theme)**: Use CSS e Emojis (🎵, 🖥️, 🎞️) com abundância para uma UX rica. O tema nativo "Fusion" modificado do PySide6 não deve ser sobrescrito por janelas brancas do SO.
- **Feedback Constante**: Desabilite botões críticos durante processamentos longos e injete status de carregamento ("Analisando...").
- **Proteção de Layouts**: Em caso de múltiplas abas (`QTabWidget`), ative `setUsesScrollButtons(True)` para impedir que o acúmulo esprema botões úteis da interface. Use preferencialmente o novo sistema de `QListWidget` com `QStackedWidget` para painéis avançados.

## 7. Obrigatoriedade de Testes Unitários (Test-Driven AI)
- **Cobertura Contínua**: TODO agente de IA que adicionar uma nova funcionalidade, classe ou método lógico ao projeto DEVE obrigatoriamente criar ou atualizar o teste unitário correspondente no diretório `tests/`.
- **Validação Pós-Edição**: É ESTRITAMENTE PROIBIDO concluir uma alteração arquitetural, correção de bug ou refatoração sem antes executar a suíte de testes (`venv/bin/pytest`) e garantir que 100% dos testes passam. A IA deve apresentar a saída bem-sucedida do Pytest.
- **Mocking Obrigatório para UI/Hardware**: Ao testar componentes de interface (PySide6) ou integrações que dependam de renderização em hardware e displays físicos (como o `libmpv`), a IA deve aplicar simulações via `unittest.mock.patch` e usar dependências de GUI Headless (`pytest-qt`). Testes não devem falhar em ambientes CI/CD sem monitor (headless).
- **Proteção de Motores (`core/`)**: Toda modificação nos motores críticos (`FFmpegEngine`, `YTDLPEngine`) deve ter suas linhas de comandos resultantes testadas em asserções de strings (ex: verificando se as flags corretas como `-hwaccel` ou `-map` foram geradas e anexadas) para impedir regressões na exportação.
