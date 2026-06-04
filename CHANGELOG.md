# Changelog

Todas as alterações notáveis no Lyra Multimedia Converter serão documentadas neste arquivo.

## [1.1.8] - 2026-06-03

### Adicionado
* **Extração Nativa de Legendas (Softsubs):** Adicionado suporte à extração cirúrgica de legendas de arquivos MKV/MP4 para arquivos `.srt` isolados sem perda de qualidade, suportando mapeamento de faixas e conversões em lote com alta velocidade (Copy Stream).

* **Redução de Ruído via Rede Neural (RNNoise):** Inserida integração nativa com o modelo `cb.rnnn` para limpeza avançada de ruído de fundo, incluindo mecanismo de fallback seguro que força a recodificação (`aac`) caso o usuário esqueça o codec na opção "copy".

## [1.1.7] - 2026-06-01

### Adicionado
* **Inspetor de Mídia Inteligente:** Nova aba "Info da Mídia" que exibe os metadados estruturados (Codec, Resolução, Canais, Bitrate, Idioma) utilizando o `ffprobe` com formatação JSON nativa.
* **Qualidade Constante Inteligente (CRF / CQ):** Adicionado slider de "Qualidade Inteligente" (0 a 51) substituindo a necessidade de adivinhar o Bitrate, suportando `-crf` (CPU) e `-cq` (NVENC).
* **Detecção Automática de Bordas (Auto-Crop):** Botão na aba de Filtros que utiliza o `cropdetect` do FFmpeg para analisar a mídia e preencher automaticamente os parâmetros de corte.
* **Áudio de Cinema (Downmix Dinâmico - DRC):** Opção para "Normalizar Vozes" (`dynaudnorm`) e converter áudios 5.1/7.1 nativamente para Estéreo sem abafar os diálogos.
* **Seletor de Faixas de Áudio:** Dropdown dinâmico que varre a mídia original e permite extrair ou converter apenas a faixa de áudio desejada.
* **Sistema de Presets Refatorado:** Possibilidade de salvar, carregar e excluir configurações customizadas de renderização diretamente da interface principal.
* **Motor Integrado do YT-DLP:** Adicionada aba completa para download de mídia da web, com suporte nativo a mesclagem de vídeo/áudio e seleção de qualidade dinâmica.

### Modificado (Arquitetura)
* **Refatoração Modular:** Código monolítico dividido em módulos escaláveis (`ffmpeg_engine.py`, `ytdlp_engine.py`, `preset_manager.py`, `utils.py`).
* **Blindagem Multiplataforma (SSOT):** Resolução dinâmica de diretórios de recursos adaptando-se ao Windows (PyInstaller), Linux nativo e Sandbox (Flatpak).
* **Gestão Assíncrona de Processos:** Otimização da classe `FFmpegEngine` com comunicação baseada em `Signal`, evitando congelamentos da GUI.

### Corrigido
* **Crash de Metadados de Imagem:** Resolvido erro onde o inspetor de mídia calculava FPS e Bitrate falsos para imagens estáticas.
* **Falha de PySide6 para C++ (`_pythonToCppCopy`):** Resolução do bug no `YTDLPEngine` simplificando o sinal para emitir apenas o código numérico (`exitCode`).
* **Corte de Textos na Interface:** Aplicado `padding-right` nos componentes `QGroupBox` para impedir o motor Qt de cortar palavras no Linux/Wayland.
* **Conflitos OGG/MP3:** Barreira de segurança interna que força a alteração para o codec `libvorbis` ao gerar contêineres `.ogg` com codec incompatível.