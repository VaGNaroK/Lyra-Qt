# Changelog

Todas as alterações notáveis no Lyra Multimedia Converter serão documentadas neste arquivo.

## [1.1.10] - 2026-06-07

### Adicionado
* **Preview de Filtros de Áudio ao Vivo (Real-Time MPV):** O player de sincronia nativo foi interligado ao painel de configurações de áudio avançadas. Agora é possível escutar em tempo real o efeito do Slider de Volume Linear (0 a 400%), do filtro Inteligente de Normalização de Vozes (DRC / Downmix) e da Redução de Ruído por IA (`cb.rnnn`). As alterações visuais na UI enviam atualizações instantâneas ao motor de áudio `libavfilter` que processa o player, sem a necessidade de recarregar a mídia.

## [1.1.9] - 2026-06-04

### Adicionado
* **Sincronia de Áudio em Tempo Real:** Adicionada a nova aba "Sincronia" que integra o player nativo `libmpv` (via `python-mpv`) para visualização e correção de atraso de áudio em tempo real. A engine FFmpeg foi preparada para injetar atrasos (+ms) via `adelay` e avanços (-ms) via `atrim` + `asetpts`.
* **Remoção Seletiva de Faixas (Negative Mapping):** Adicionado suporte inteligente à remoção cirúrgica de faixas nativas de legendas. O motor `ffprobe` agora detecta dinamicamente as legendas embutidas e preenche um `QListWidget` na aba "Legendas", permitindo que o usuário marque e descarte múltiplas faixas indesejadas do contêiner final usando mapeamento negativo (`-map -0:X?`).
* **Busca Profunda de Metadados (Media Info):** O motor agora faz busca profunda na tabela de tags de contêineres MKV/MP4 (`BPS`) para descobrir e reportar bitrates individuais de faixas de vídeo e áudio que antes eram ocultos. Adicionada extração visual clara do formato nativo e proporção de tela real.
* **Suporte a Múltiplas Faixas Externas:** A interface abandonou os inputs únicos. Adicionado suporte a `QListWidget` nas abas de Áudio e Legenda, permitindo adicionar simultaneamente incontáveis faixas (softsub e áudios multiplexados).

### Modificado (Arquitetura)
* **Algoritmo de Mapeamento Acumulativo (MUX):** O FFmpegEngine foi completamente reescrito para proteger a integridade dos contêineres. Faixas originais (áudios selecionados e *todas* as legendas nativas) são obrigatoriamente protegidas (`-map 0:s?`), enquanto novos áudios e legendas externas são anexados de forma sequencial, encerrando a exclusão acidental de faixas nativas.

### Corrigido
* **Regressão de Áudio (Race Condition no MPV):** Corrigido bug de inicialização onde o motor do MPV iniciava mudo. A rotina de auto-pause foi movida para *antes* do carregamento assíncrono da mídia (`play()`), garantindo que os drivers de som (PulseAudio/PipeWire) não sejam interrompidos durante sua alocação de memória.
* **Integração com Wayland e Encerramento Zombie:** Forçado suporte a `xcb` (X11/XWayland) em sistemas Linux para garantir que a janela embutida (WID) do `libmpv` renderize perfeitamente. Criada rotina segura de terminação do motor de vídeo (`_shutdown_mpv`) que extingue processos zumbis que travavam o encerramento da interface via System Tray.
* **Empacotamento Universal (MPV):** Scripts nativos de compilação Debian (`package.sh`), Windows (`build_windows.ps1`) e Sandbox (`flatpak`) inteiramente refatorados para realizar o download e integração autônoma das bibliotecas dinâmicas requeridas pelo MPV (`libmpv-2.dll` no Windows, `libmpv-dev` no Linux).
* **Crash de Renderização por Imagens de Capa (Cover Arts):** Corrigido bug crítico onde a opção "Incluir todas as faixas" usava a flag global `-map 0`, forçando o renderizador de vídeo (CUDA/NVENC) a tentar converter miniaturas PNG da capa do álbum como se fossem vídeos reais.

## [1.1.8] - 2026-06-03

### Adicionado
* **Extração Nativa de Legendas (Softsubs):** Adicionado suporte à extração cirúrgica de legendas de arquivos MKV/MP4 para arquivos `.srt` isolados sem perda de qualidade, suportando mapeamento de faixas e conversões em lote com alta velocidade (Copy Stream).

* **Redução de Ruído via Rede Neural (RNNoise):** Inserida integração nativa com o modelo `cb.rnnn` para limpeza avançada de ruído de fundo, incluindo mecanismo de fallback seguro que força a recodificação (`aac`) caso o usuário esqueça o codec na opção "copy".

### Corrigido
* **Atualização Crítica do Motor yt-dlp (HTTP 403 / Precondition Check Failed):** Resolvido o problema de barreira do YouTube que proibia downloads atualizando o `yt-dlp` para a mais recente versão e isolando a dependência do sistema operacional (`venv/requirements.txt`), garantindo que a aplicação execute com as assinaturas atualizadas (nsig).

## [1.1.7] - 2026-06-01

### Adicionado
* **Inspetor de Mídia Inteligente:** Nova aba "Info da Mídia" que exibe os metadados estruturados (Codec, Resolução, Canais, Bitrate, Idioma) utilizando o `ffprobe` com formatação JSON nativa.
* **Qualidade Constante Inteligente (CRF / CQ):** Adicionado slider de "Qualidade Inteligente" (0 a 51) substituindo a necessidade de adivinhar o Bitrate, suportando `-crf` (CPU) e `-cq` (NVENC).
* **Detecção Automática de Bordas (Auto-Crop):** Botão na aba de Filtros que utiliza o `cropdetect` do FFmpeg para analisar a mídia e preencher automaticamente os parâmetros de corte.
* **Áudio de Cinema (Downmix Dinâmico - DRC):** Opção para "Normalizar Vozes" (`dynaudnorm`) e converter áudios 5.1/7.1 nativamente para Estéreo sem abafar os diálogos.
* **Seletor de Faixas de Áudio:** Dropdown dinâmico que varre a mídia original e permite extrair ou converter apenas a faixa de áudio desejada.
* **Sistema de Presets Refatorado:** Possibilidade de salvar, carregar e excluir configurações customizadas de renderização diretamente da interface principal.
* **Motor Integrado do YT-DLP:** Adicionada aba completa para download de mídia da web, com suporte nativo a mesclagem de vídeo/áudio e seleção de qualidade dinâmica.

## [1.1.6] 2026-05-13

### Modificado (Arquitetura)
* **Refatoração Modular:** Código monolítico dividido em módulos escaláveis (`ffmpeg_engine.py`, `ytdlp_engine.py`, `preset_manager.py`, `utils.py`).
* **Blindagem Multiplataforma (SSOT):** Resolução dinâmica de diretórios de recursos adaptando-se ao Windows (PyInstaller), Linux nativo e Sandbox (Flatpak).
* **Gestão Assíncrona de Processos:** Otimização da classe `FFmpegEngine` com comunicação baseada em `Signal`, evitando congelamentos da GUI.

### Corrigido
* **Crash de Metadados de Imagem:** Resolvido erro onde o inspetor de mídia calculava FPS e Bitrate falsos para imagens estáticas.
* **Falha de PySide6 para C++ (`_pythonToCppCopy`):** Resolução do bug no `YTDLPEngine` simplificando o sinal para emitir apenas o código numérico (`exitCode`).
* **Corte de Textos na Interface:** Aplicado `padding-right` nos componentes `QGroupBox` para impedir o motor Qt de cortar palavras no Linux/Wayland.
* **Conflitos OGG/MP3:** Barreira de segurança interna que força a alteração para o codec `libvorbis` ao gerar contêineres `.ogg` com codec incompatível.
