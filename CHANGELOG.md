# Changelog

Todas as alterações notáveis no Lyra Multimedia Converter serão documentadas neste arquivo.

## [1.1.18] - 2026-07-10

### Adicionado
* **Marca d'água (Watermark):** Suporte nativo para sobreposição de imagens (PNG, JPEG, etc) em vídeos, configurável na aba "Filtros" com opções de redimensionamento (1% a 200%), opacidade e posicionamento em 5 pontos da tela.
* **Infraestrutura de Testes:** Preparação da base de testes automatizados com a adição do framework `pytest` e `pytest-qt` aos requisitos do projeto.

### Alterado
* **Normalização Profissional de Áudio (EBU R128):** Substituição do antigo limitador dinâmico (`dynaudnorm`) pelo padrão ouro de mercado para streaming (`loudnorm`). O áudio agora é normalizado de forma cirúrgica mantendo níveis em -16 LUFS e evitando completamente distorções de volume (True Peak cravado em -1.5 dB).

## [1.1.17] - 2026-07-04

### Adicionado
* **Clonagem Inteligente de Specs (Motor de Análise):** Um botão inteligente ("🧠 Clonar Info") na aba de Destino extrai bitrates, codec e FPS do arquivo fonte original e cria um *Preset Dinâmico* replicando essas características. Ideal para otimizar tamanho com máxima fidelidade.
* **Ações Automáticas "Ao Concluir":** Inserido um controle de energia na janela principal. O usuário pode instruir o Lyra a "Fechar o aplicativo", "Suspender Computador" ou "Desligar Computador" ao finalizar a fila de conversões inteira. Permissões seguras via D-Bus (`org.freedesktop.login1`) foram criadas para o empacotamento em Flatpak.
* **Aba de Marcadores (Metadados ID3/MP4):** Uma nova seção ("🏷️ Marcadores") em *Opções Avançadas*. O usuário pode sobrescrever Título, Artista, Álbum, Gênero e Ano.
* **Renomeio Dinâmico:** Se um único arquivo for processado, o "Título" fornecido na aba de Marcadores passará a ser utilizado como o novo nome do arquivo convertido gerado no HD.
* **Ajudas Visuais (ToolTips):** Adicionadas descrições rápidas flutuantes nos botões vitais do app para suavizar a curva de aprendizado de usuários iniciantes.
* **Informações Avançadas de Imagens:** O painel de Informações da Mídia agora cruza os mapeamentos de pixels do FFprobe para exibir o Perfil, a Profundidade de Cor (ex: 8-bit, 10-bit HDR) e o Espaço de Cor amigável (como RGB, CMYK, YUV ou Escala de Cinza) ao carregar imagens.
* **Aviso de Blindagem SRT:** Inserido um alerta explícito no console de Logs informando quando o usuário tentar extrair legendas (`.srt`) de mídias nativamente incompatíveis (como Áudios ou Imagens estáticas), educando sobre o motivo da falha do FFmpeg sem interromper a fila.

### Corrigido
* **Bug de "0.00 MB" em Imagens:** O FFprobe frequentemente omite o pacote de bytes totais em fluxos de imagem estática (`image2`), o que forçava a interface do Lyra a exibir um tamanho falso. Resolvido adicionando um fallback direto à API do SO (`os.path.getsize`) e estabelecendo limite flutuante automático para Kilobytes (KB) em mídias minúsculas.
* **Erro 1114 no Windows (Falha ao carregar mpv-2.dll):** Corrigido um problema crítico que impedia o aplicativo de abrir em algumas máquinas Windows. O script de compilação foi ajustado para baixar a versão genérica `x86_64` do libmpv (removendo a exigência de processadores com instruções AVX2) e adicionada uma rotina nativa na inicialização (`main.py`) para limpar a flag "Mark of the Web" (`:Zone.Identifier`) injetada pelo Windows em arquivos baixados via ZIP.
* **Quebra de Layout na Janela:** O acúmulo de novas sub-abas em "Opções Avançadas" empurrava os botões da barra superior para fora da tela. Corrigido ativando a rolagem nativa de abas (`setUsesScrollButtons`) e expandindo a janela padrão do app para `1150x700`.
* **Incompatibilidade em Contêineres WEBM:** O Lyra agora acopla de forma agressiva a lógica de "Trava de UI" à injeção de Presets (como o preset Clonado). Ao tentar empacotar codificações nativas H.264 em recipientes Google WEBM, o app reescreve ativamente a estrutura do perfil para VP9/Opus, corrigindo os crashes do FFmpeg de saída "Invalid argument".
* **Amnésia de Sessão em Conversões em Lote:** O Lyra sofria de uma vulnerabilidade onde a interface atualizava as opções da fila de conversão dinamicamente. Se o usuário clicasse em outro arquivo na tabela durante a conversão, as configurações do lote se perdiam (como descarte de legendas). Corrigido com a implementação de um *Snapshot de Sessão* na largada da fila, congelando as opções para todo o processamento.
* **Descarte de Legendas Incompatíveis em Lote:** O mapeamento de remoção de legendas confiava em índices globais (ex: `Faixa 2`), o que falhava quando os arquivos na fila tinham arquiteturas de áudio/vídeo diferentes. O código foi totalmente reestruturado para identificar índices relativos exclusivos (`-map -0:s:N`) integrados no motor do FFmpeg.

## [1.1.16] - 2026-07-03

### Adicionado
* **Suporte a Formatos WEBM e OPUS:** Adicionada compatibilidade completa com os formatos WEBM (vídeo) e OPUS (áudio), incluindo mapeamento inteligente das legendas convertidas automaticamente para `webvtt`.
* **Novos Codecs Visuais (VP8 e VP9):** Integrados os encoders `libvpx-vp9` e `libvpx-vp8` diretamente na interface, permitindo exportar arquivos com alta eficiência.
* **Trava Dinâmica (UX/UI):** Implementado um sistema inteligente de bloqueio visual que remove encoders incompatíveis (como VP8/VP9 e OPUS) caso o usuário selecione recipientes inadequados (como MP4 ou AVI), evitando falhas nas conversões.
* **Fallback e Segurança no Motor (FFmpeg):** Adicionado um fallback automático no engine de conversão que substitui de forma transparente codecs inválidos (impedindo crashes no backend).

### Corrigido
* **Bugs de UI no Windows (Checkbox Invisível):** Corrigido o bug visual no Windows em que caminhos contendo espaços quebravam o interpretador QSS (CSS), deixando as caixas de seleção invisíveis.
* **Janelas do Sistema em Inglês:** Removida a trava `DontUseNativeDialog`. O sistema agora invoca os gerenciadores de arquivos do próprio Sistema Operacional, aproveitando as traduções em português (ou do idioma nativo do user).
* **Script de Compilação (Limpeza):** O script `auto_build.sh` agora detecta e apaga corretamente os arquivos finais `.deb` e `.flatpak` gerados na raiz quando a opção de Limpeza de Cache é acionada.

## [1.1.15] - 2026-06-30

### Adicionado
* **Drag & Drop Nativo:** Suporte completo para arrastar e soltar arquivos de mídia e pastas inteiras diretamente na janela principal para adicioná-los à fila de conversão.
* **Resolução de Conflito de Arquivos (Existentes):** Implementada a lógica funcional para o menu de destino (Sobrescrever, Escolher outro nome, Pular conversão). O Lyra agora respeita a escolha do usuário e checa se o arquivo de saída já existe antes de enviar para o FFmpeg (anteriormente a flag `-y` era forçada globalmente).

### Corrigido
* **Reaproveitamento na Fila de Conversão:** O app agora redefine o status de arquivos com estado "Concluído" ou "Erro" de volta para "Pronto" se eles continuarem marcados na fila e você clicar em "Converter". Isso permite reconversão instantânea (com outros presets) sem a necessidade de remover e adicionar o vídeo novamente.
* **Encerramento Fantasma via System Tray:** Corrigido o erro crônico que mantinha o app rodando oculto no background após clicar em "Sair" pela bandeja do sistema. O evento de encerramento (`closeEvent`) agora aceita a morte do processo com sucesso.
* **Janela Principal Surgindo do Nada:** A tela principal não volta mais subitamente ao centro da tela no Windows quando o aviso de encerramento forçado do Tray é acionado (o parentesco do QMessageBox foi neutralizado).
* **Bug de Importação do PySide6:** Corrigido um import isolado que poderia acionar bibliotecas do PyQt5 e crashar a interface ao tentar pular uma conversão.

## [1.1.14] - 2026-06-26

### Corrigido
* **Travamento do Player no Flatpak (MPV/PipeWire):** Corrigido o congelamento fatal (deadlock) que ocorria na aba de "Sincronia" e "Cortes" ao iniciar o player em pacotes Flatpak. O MPV tentava forçar o carregamento de drivers VA-API (decodificação por hardware) e um contexto puro em OpenGL que muitas vezes estavam restritos pelo sandbox, crachando a UI. O MPV agora roda com `hwdec=no` e VO flexível em Flatpak.
* **Áudio Mudo no Flatpak:** Adicionado socket nativo do PipeWire (`--filesystem=xdg-run/pipewire-0`) no manifesto YAML, eliminando a falha "Host está desligado" e permitindo que o libmpv comunique corretamente com o servidor de áudio. Além disso, foi adicionado um fallback no código do player (`ao=pulse`) para garantir que o áudio não fique mudo ao tentar inicializar PipeWire nativo incorretamente dentro da sandbox.

## [1.1.13] - 2026-06-26

### Adicionado
* **Script Unificado de Compilação (`auto_build.sh`)**: Criado um script interativo único dentro de `build_scripts/` capaz de gerar e instalar pacotes universais (Flatpak) e Debian (.deb) de forma autônoma. O script resolve dependências nativas (flathub/apt), extrai a versão atual de forma dinâmica e questiona o usuário antes de concluir a instalação. Ele também integra uma rotina opcional de limpeza profunda de cache de compilação pós-geração do pacote.

### Modificado (UX/UI)
* **Visibilidade de Checkboxes em Tema Dark:** Injetados ícones vetoriais SVG de forma dinâmica via *Stylesheet* global do PySide6. Essa modificação substitui a renderização nativa de checkboxes (`QCheckBox`, `QTableView`, `QListView`), garantindo que itens selecionados ou desmarcados (especialmente nas tabelas de conversão e abas avançadas) fiquem com visibilidade perfeita, eliminando o erro onde checkboxes "desapareciam" no fundo preto.

### Removido
* Removido `package.sh` e `clean_flatpak_cache.sh` em favor da unificação de rotinas de empacotamento e limpeza no novo `auto_build.sh`.

## [1.1.12] - 2026-06-13

### Corrigido
* **Resolução Universal de yt-dlp:** O motor de download agora identifica e executa dinamicamente o binário do `yt-dlp` contido no próprio ambiente virtual (`venv`), prevenindo que instalações `.deb` tentem utilizar versões severamente desatualizadas dos repositórios APT (o que quebrava o bypass do YouTube).
* **Falha de Escalonamento de Vídeo (Filter Not Found):** Removido o filtro `scale_cuda` (não compatível com o build nativo do Flatpak sem o LLVM gigante) e refatorado o motor Python para isolar corretamente os fluxos de memória de hardware e software. O Lyra agora transiciona perfeitamente de NVENC para CPU em redimensionamentos, e volta à GPU no encode final, sem crachar.
* **Refatoração do FFmpeg nos Scripts de Empacotamento:** O FFmpeg do BtbN foi removido dos empacotamentos Flatpak, DEB e Windows por exigir drivers muito recentes (API NVENC 13.1) que quebravam computadores padrão.
  * **Flatpak:** O FFmpeg 7.0 agora é compilado nativamente usando os cabeçalhos NVIDIA `n12.1.14.0`.
  * **Debian (.deb):** Usa-se ativamente o pacote oficial `ffmpeg` estável do sistema host via dependência nativa APT.
  * **Windows:** O build passa a baixar o release "Essentials" do repositório Gyan.dev, focado em altíssima estabilidade e retrocompatibilidade do driver da placa de vídeo.
* **Ordem de Processamento de Áudio (Slider vs DRC) e Preview no MPV:** Corrigida a anomalia visual e auditiva onde o volume parecia não subir adequadamente. O motor FFmpeg foi refatorado para aplicar o Volume *após* a compressão (DRC), impedindo o filtro Inteligente de esmagar o desejo do usuário. Adicionalmente, toda a cadeia de áudio foi encapsulada na sintaxe nativa de ponte `lavfi=[...]` no MPV, restaurando o suporte instantâneo (Real-Time Preview) da Redução Neural de Ruídos e Normalização de Vozes na aba Sincronia.
* **Limpeza Universal de Estados Residuais (State Leak):** Resolvido o erro crítico de decodificação (`Encoder not found`) que ocorria ao tentar converter imagens simples (PNG para WEBP) logo após usar perfis pesados de vídeo. A função interna `_reset_advanced_options` foi expandida em duas etapas para varrer e zerar imperativamente todos os 25 componentes da interface. Agora, caixas de seleção ocultas (CRF, Corrigir Index, Somente Vídeo), temporizadores de corte (`-ss`), listas de Áudios Externos e sliders de sincronia nas abas Avançadas são neutralizados, impedindo que "estados fantasmas" vazem de um arquivo para o próximo.
* **Correção de Evento Fantasma no Reset:** O botão de "Restaurar Padrões" foi desvinculado do evento dependente de estado da Combobox (o PySide6 abortava o gatilho se o índice da combobox já estivesse no zero, o que impossibilitava a limpeza caso o usuário modificasse opções manualmente). Agora o botão possui uma função exclusiva de **Bypass (`_trigger_hard_reset`)** que executa a faxina forçosamente independente do índice.
* **Blindagem Total contra Armadilha de 2 Passos (State Bleed):** O motor de renderização principal (`ffmpeg_engine.py`) foi blindado contra configurações alienígenas vindas da interface. Anteriormente, se um usuário marcasse opções de "Habilitar 2-Passos" mas solicitasse a conversão de uma Imagem (`.webp`) ou Áudio (`.mp3`), o motor disparava as 2 fases erroneamente e o FFmpeg travava por falta de logs de encodamento. O método `start_conversion` agora exige que a extensão de saída do arquivo passe pelo filtro `is_video_format`, abortando silenciosamente os 2 passos se o destino não for um vídeo genuíno.
* **Mapeamento Estrito de Codecs de Imagem (WebP/GIF):** Corrigido erro (`Encoder not found`) que impedia conversão para `.webp` em certos binários do FFmpeg empacotados (como o Flatpak) onde a seleção automática de encoder ficava desativada. Criou-se um dicionário universal em Python que injeça coercitivamente os encoders nativos apropriados baseados na extensão final do arquivo (incluindo o uso estratégico de `libwebp_anim` para lidar com WebP animado sem quebra de frames).



### Modificado (UX)
* **Design de Navegação de Presets:** O rótulo confuso da combobox de perfis foi renomeado de `"Carregar Preset Salvo..."` para `"🟢 Padrão do Sistema (Automático)"`, informando claramente o usuário sobre o controle delegado ao Lyra.
* **Botão Dedicado de Limpeza:** Injetado um botão físico `"🔄 Restaurar Padrões"` diretamente na tela principal, permitindo que o usuário dê um Hard Reset instantâneo nas configurações de forma segura.
## [1.1.11] - 2026-06-11

### Adicionado
* **Aba de Cortes de Vídeo (Trimming):** Nova aba dedicada nas Configurações Avançadas que permite carregar um player visual independente e fatiar a duração do vídeo graficamente (`HH:MM:SS.ms`) utilizando marcadores interativos (`Marcar Início` / `Marcar Fim`).
* **Cortes Otimizados (Fast Seek):** O sistema de corte não faz decodificação por software de trechos inutilizados. Ele usa injeção de parâmetros (`-ss` e `-to`) antes do seletor `-i` no FFmpeg, permitindo pular instantaneamente para a linha temporal selecionada, economizando até 90% da CPU em vídeos longos.

### Corrigido
* **Crash OOM no MPV (Memória/Decodificação):** A restrição rígida antiga (`vd='h264'`) no `MPVPlayerWidget` impedia a reprodução de arquivos HEVC e gerava erros de ponteiro nulo (`get_buffer() failed`) ao tentar abrir duas mídias em abas simultâneas, resultando na queda silenciosa do decoder do mpv. Resolvido ajustando para `hwdec='auto-safe'` delegando corretamente a GPU host sem forçar codec estático.
* **Supressão de Falsos-Positivos (libva/VA-API):** Injetada a flag `LIBVA_MESSAGING_LEVEL=0` no ambiente do Linux, impedindo que a biblioteca C nativa `libva` causasse poluição no log do terminal tentando testar drivers Intel em sistemas restritos NVIDIA.

## [1.1.10] - 2026-06-07

### Adicionado
* **Troca Dinâmica de Faixa de Áudio:** Ao selecionar um idioma/faixa específica de áudio na guia de Configurações Avançadas, o player reflete a escolha quase instantaneamente atualizando a propriedade interna (`aid`) do MPV. Permite o ajuste da sincronia escutando a faixa exata que se deseja manipular.
* **Controles Nativos de Reprodução PySide6:** Substituição do OSC nativo do MPV, que sofria bloqueios de mouse no ambiente Wayland/Flatpak, por controles `Qt` (Play/Pause, Slider de Progresso temporal, Marcações de tempo). A resposta da barra é totalmente orientada a eventos (`Signals` e `Observers` de propriedades), evitando travamentos de thread principal.
* **Preview de Filtros de Áudio ao Vivo (Real-Time MPV):** O player de sincronia nativo foi interligado ao painel de configurações de áudio avançadas. Agora é possível escutar em tempo real o efeito do Slider de Volume Linear (0 a 400%), do filtro Inteligente de Normalização de Vozes (DRC / Downmix) e da Redução de Ruído por IA (`cb.rnnn`). As alterações visuais na UI enviam atualizações instantâneas ao motor de áudio `libavfilter` que processa o player, sem a necessidade de recarregar a mídia.

### Corrigido
* **Resolução de DLL do MPV no Windows (PyInstaller):** Resolvido o erro crítico onde o `python-mpv` falhava ao iniciar em instalações Windows autônomas (via PyInstaller) com a mensagem `OSError: Cannot find mpv-2.dll in your system %PATH%`. Foi adicionada uma injeção explícita de `os.environ["PATH"]` no momento de inicialização para expor a pasta oculta `assets/bin` ao motor do MPV.
* **API de Download Automático no Windows (`build_windows.ps1`):** O script de compilação de Windows falhava devido à remoção repentina de symlinks (Erro 404) do repositório SourceForge. O script foi reescrito para utilizar chamadas `Invoke-RestMethod` diretamente na API de releases do GitHub, detectando a última compilação automaticamente sem links quebrados.
* **Renderização do MPV no Sandbox Flatpak:** Corrigido o erro crítico de falha de contexto de GPU (`VT_GETMODE` e Permissão Negada em KMS/DRM) que incapacitava a execução do player na aba "Sincronia". Foram ativados no `libmpv` empacotado os sinalizadores explícitos de `gl`, `egl`, `x11` e `wayland`, juntamente com a injeção da biblioteca vital `libXpresent`. No lado da interface, o ciclo de vida do Qt foi resguardado com a inicialização atrasada da aba (`QTimer`) para geração de `winId` válido, além de travas ativas contra roubo de terminal TTY.
* **Falha de NVENC no Linux (Sandbox/Flatpak e `.deb`):** O motor de conversão falhava ao usar aceleração de hardware (NVENC/CUDA) no Linux (`Unrecognized option 'cq'`) devido à ausência dos drivers da NVIDIA no FFmpeg nativo das distros. Resolvido aplicando a arquitetura *SSOT*: os empacotadores `package.sh` e `com.github.vagnarok.lyra.yml` agora baixam e embutem silenciosamente os binários estáticos master do BtbN, garantindo compatibilidade universal com NVENC moderno.
* **Erro de Muxing de Legendas SRT para MP4:** Resolvido erro onde a conversão de MKV para MP4 abortava ao herdar as legendas originais. O FFmpegEngine agora obriga globalmente o uso do encoder `-c:s mov_text` para contêineres `.mp4`, e utiliza `copy` transparente em contêineres `.mkv`.

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
