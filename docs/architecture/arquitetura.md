# Arquitetura do Lyra-Qt

## Visão Geral
O Lyra-Qt utiliza uma arquitetura modular baseada no padrão Model-View-Controller (MVC) adaptado para o ecossistema Qt (PySide6). A premissa central é a **separação estrita entre interface de usuário (GUI) e a lógica de processamento (Core)**, garantindo que operações pesadas de conversão e download nunca congelem a interface.

## Princípios Arquiteturais
1. **Event-Driven & Assincronicidade**: O projeto é altamente guiado a eventos. O motor de processamento (`core/`) se comunica com a interface (`gui/`) exclusivamente através de **Qt Signals e Slots**. A execução de comandos externos (FFmpeg, yt-dlp) utiliza `QProcess` de forma não bloqueante.
2. **Abstração de CLI**: O Lyra atua como um wrapper gráfico. Toda a complexidade da linha de comando do FFmpeg e yt-dlp é encapsulada em classes "Engine", que constroem os parâmetros e processam o log de saída em tempo real.
3. **Plataforma Agnóstica**: O código Python interage com binários de sistema (FFmpeg/yt-dlp) que podem mudar dependendo do SO, mantendo o software portátil (Linux/Windows).

## Fluxo de Dados
- **Input do Usuário**: A `LyraMainWindow` capta as opções (Codec, CRF, Crop, etc.).
- **Delegação**: Os parâmetros são passados na forma de dicionários ou argumentos para as instâncias de `FFmpegEngine` ou `YTDLPEngine`.
- **Execução**: O `QProcess` inicia o binário no sistema.
- **Feedback**: A saída padrão (stdout/stderr) é capturada e transformada em porcentagens/logs legíveis, enviados via sinal para atualização visual na GUI.
