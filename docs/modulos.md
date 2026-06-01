# Módulos do Sistema

O Lyra-Qt é segmentado em dois pacotes principais: `core/` e `gui/`.

## 1. Pacote `core/` (Lógica de Negócios e Motores)
Este módulo contém toda a inteligência e abstração de processos do aplicativo. Nenhuma biblioteca visual (widgets) deve ser importada aqui, apenas bibliotecas do `QtCore` (como `QObject`, `QProcess`, `Signal`).

* **`ffmpeg_engine.py`**:
  - Classe `FFmpegEngine`: Motor central de conversão.
  - Responsabilidades: Identificação de mídia (usando `ffprobe`), cálculo de Crop, extração de resolução, formatação de comandos do `ffmpeg` com base em dicionários de opções, controle de conversão em 2 passos, e parse progressivo de log de saída (extração de tempo e tamanho para cálculo de porcentagem).
* **`ytdlp_engine.py`**:
  - Classe `YTDLPEngine`: Wrapper para download da web.
  - Responsabilidades: Execução do binário `yt-dlp`, formatação de strings de comando para extração de vídeo/áudio com seletores de formato, captura de saída de download.
* **`preset_manager.py`**:
  - Classe `PresetManager`: Gerenciamento de predefinições do usuário.
  - Responsabilidades: Salvar, carregar e excluir arquivos `.json` contendo perfis de conversão favoritos.
* **`utils.py`**:
  - Funções auxiliares (ex: `normalize_bitrate`) e utilitários gerais que não requerem estado.

## 2. Pacote `gui/` (Interface do Usuário)
Responsável por apresentar os controles ao usuário de forma amigável e limpa.

* **`main_window.py`**:
  - Classe `LyraMainWindow`: A janela principal do aplicativo (PySide6).
  - Responsabilidades: Criação de abas dinâmicas, validação de entradas, interações do usuário, conexão de signals do motor para atualização de progresso (barras e logs), integração na bandeja do sistema (System Tray) e notificações.
* **`dialogs/`** (Submódulo opcional):
  - Pop-ups de configuração e diálogos adicionais.
