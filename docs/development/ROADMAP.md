# Análise de Viabilidade e Arquitetura: Upscaling de Vídeo com IA no Lyra-Qt

Este documento detalha o estudo técnico e o projeto arquitetural para a futura implementação de upscaling por Inteligência Artificial no **Lyra Multimedia Converter**. A proposta foca em processamento de alta performance (In-Memory) e suporte universal multiplataforma (Vulkan/TensorRT).

---

## 1. Motores de IA e Tecnologias Selecionadas

Para atender tanto a vídeos realistas quanto a animações de forma otimizada, a arquitetura do Lyra-Qt comportará três pilares de Inteligência Artificial de código aberto:

### A. Real-ESRGAN (Vulkan / TensorRT)
* **Objetivo:** Super-resolução para filmes, vídeos reais (live-action), texturas complexas e remasterização de VHS.
* **Como funciona:** Reconstrói detalhes complexos (cabelo, pele, folhas) e remove ruídos severos usando Redes Adversariais Generativas (GANs).
* **Custo Computacional:** Extremamente alto.

### B. Waifu2x (NCNN Vulkan)
* **Objetivo:** O clássico absoluto para artes 2D, ilustrações, cartoons ocidentais e animes.
* **Como funciona:** Especializado em preservar traços vetoriais/2D, bordas limpas e cores chapadas sem introduzir o aspecto "sujo/realista" que o Real-ESRGAN injetaria em um desenho.

### C. Anime4K (A Magia dos Shaders GLSL)
* **Objetivo:** Melhoria de qualidade de animes em **Velocidade Extrema (Tempo Real)**.
* **Como funciona:** Diferente das Redes Neurais super pesadas baseadas em NCNN, o Anime4K roda como shaders matemáticos ultraleves (`.glsl`) diretamente dentro da GPU. No Lyra, ele terá dupla utilidade: pode ser ativado dentro do Player (MPV) para visualização ao vivo na Aba de Sincronia, e injetado nativamente no motor do FFmpeg (através do avançado filtro `libplacebo`) para a exportação ultra-rápida.

---

## 2. A Arquitetura Profissional: Pipes / In-Memory (O Fim do Gargalo do SSD)

A abordagem amadora de desmembrar vídeos em milhares de imagens `.png` (Frame Extraction para disco rígido) está **categoricamente descartada**. O Lyra-Qt adotará a arquitetura oficial de **Piping e Memória RAM (Streaming)**, protegendo o SSD do usuário.

### O Fluxo "Zero-Disk" (Esteira de Fábrica):
1. **Decode (FFmpeg):** O FFmpeg abre o arquivo fonte e decodifica um pequeno *buffer* rotativo de quadros (ex: 20 frames) em formato de pixel bruto (RAW `YUV420p` ou `RGB24`) diretamente na **Memória RAM**.
2. **Transfer (Pipe):** Esses bytes puros viajam através de canais interprocessos virtuais (Pipes de `stdout`) para o binário da IA (ex: `realesrgan-ncnn-vulkan`).
3. **Upscale (GPU VRAM):** A IA segura as matrizes matemáticas na Memória de Vídeo (VRAM). Para evitar crashes de OOM (Out of Memory) em placas simples, a IA corta cada frame em pequenos "azulejos" (Tiling), processa o detalhamento em 4K e os recola.
4. **Encode (Pipe):** Os quadros finalizados viajam de volta (via `stdin`) para uma segunda instância invisível do FFmpeg, que junta a nova pista de vídeo 4K com a trilha de áudio original (via Stream Copy `-c:a copy`) e compacta o arquivo final `.mp4`.

> [!TIP]
> **Vantagem Absoluta:** O consumo de RAM da máquina permanecerá fixo na margem de **1 GB a 2 GB** e a VRAM estabilizada em **2 GB a 6 GB**. A duração do vídeo não esgotará a máquina nem destruirá os ciclos de gravação do HD/SSD do usuário.

---

## 3. UI/UX: Design Explicativo na Interface do Lyra-Qt

Para não sobrecarregar o usuário com terminologias técnicas complexas (NCNN, GAN, Vulkan), a aba de **Filtros e Efeitos** ganhará um design de interface altamente acessível focado no *caso de uso*.

### Painel: 🤖 Upscaling de IA (Super Resolução)
Uma combobox interativa apresentará as seguintes opções descritivas (exatamente assim para o usuário final):

1. 🚫 **Desativado (Padrão)**
   * *O Lyra usará a redimensionamento tradicional (Bicúbico/Lanczos) sem geração de IA.*
2. 🎬 **Filmes e Realismo (Real-ESRGAN)**
   * *Reconstrói detalhes complexos como pele e paisagens. Ideal para melhorar nitidez de filmes antigos e gravações de câmera. Processamento extremamente pesado (Requer placa de vídeo potente).*
3. 🌸 **Desenhos e Artes 2D (Waifu2x)**
   * *Preserva a pureza das linhas e cores sólidas de desenhos animados sem introduzir "sujeiras" ou falhas realistas. Processamento pesado.*
4. ⚡ **Anime Ultra-Rápido (Anime4K)**
   * *Algoritmo matemático de altíssima velocidade focado em animes. Melhora absurdamente as bordas e a nitidez sem fritar o seu PC, ideal para processamentos rápidos.*

### Controles Secundários Acoplados:
* **Escala Alvo:** `[ x2 ]` ou `[ x4 ]` (As opções serão limitadas aos modelos pré-treinados que embutirmos).
* **Motor de Hardware de Resgate:** Se a conversão explodir por falta de VRAM, uma opção avançada para `[ 🐌 Forçar Modo CPU (Não Recomendado) ]` existirá como salva-vidas.

---

## 4. O Roadmap de Implementação no Código (Core)

Caso essa funcionalidade entre em desenvolvimento futuro, os passos de integração no ecossistema modular do Lyra seriam:

1. **Injeção de Assets:** O script de download automático do projeto (`auto_build.sh` e PS1) precisará baixar os arquivos de modelo treinado (`.param` / `.bin`) para dentro de `assets/bin/`.
2. **Novo Motor Modular:** Criação de `core/ai_upscale_engine.py`. Esta classe será um maestro (Orchestrator) para coordenar a rotina de múltiplos processos (as instâncias gêmeas do FFmpeg lidando com Pipes e Subprocessos Popen de forma assíncrona).
3. **Prova de Conceito (MPV):** A porta de entrada mais segura seria iniciar implementando os Shaders do *Anime4K* diretamente no `MPVPlayerWidget` na Aba Sincronia, provando o funcionamento da aceleração por hardware visualmente sem tocar na pipeline de exportação ainda.

---

# [CONCLUÍDO] Marca d'água (Watermark)

Este roteiro documenta como adicionaremos o recurso de Marca d'água no Lyra-Qt.

## 1. Modificações na GUI (`gui/main_window.py`)

A interface gráfica para a Marca d'água será implementada dentro da aba **"Filtros"**.

* **Novo Grupo Visual:** Adição de um `QGroupBox` ("💧 Marca d'água") no método `create_filters_tab`.
* **Componentes Interativos:**
  * `QLabel` com bordas estilizadas para atuar como preview visual (miniatura) da imagem carregada.
  * Botões interativos: `Escolher imagem...` (com restrição nativa para `.png` e imagens na janela do OS) e `Limpar`.
  * Caixa de seleção (`QComboBox`) regulando a **Posição**: Superior esquerdo, Superior direito, Centro, Inferior esquerdo e Inferior direito (Sendo este o padrão).
  * Caixas incrementais (`QSpinBox`) manipulando o **Tamanho** (1% a 200%) e **Opacidade** (0% a 100%).
* As decisões do usuário nesta seção integrarão o dicionário mestre de opções no `get_ui_options()`.

## 2. A Pipeline do Motor (`core/ffmpeg_engine.py`)

O desenho da imagem no frame de vídeo final será arquitetado de modo que o comando `-map` existente (responsável por áudios e múltiplas legendas) continue imaculado.

* **O Filtro Source (`movie`):**
  * Para evitar a importação da imagem na stack tradicional do FFmpeg (com `-i`), ela nascerá diretamente dentro do `filtergraph` de vídeo (`-vf`) graças ao filtro nativo `movie`.
  * Isso injeta o arquivo PNG sem comprometer a contagem de streams global.
* **Propriedades Dinâmicas:**
  * O tamanho é processado usando a flag de scala sobre si próprio (`scale=iw*TAMANHO:ih*TAMANHO`).
  * O índice Alpha de transparência usará o componente `colorchannelmixer=aa=OPACIDADE`.
* **Cálculo Espacial e Rendering (Overlay):**
  * O posicionamento é injetado via string posicional. Por exemplo, alinhar no canto inferior direito requer a matemática `W-w-10:H-h-10` (onde W/H é o vídeo principal, e w/h é a largura/altura da marca d'água).
  * O motor fará o link dos filtros (ex: `yadif` ou de `crop` atuando como `[bg]`) com a marca d'água formatada (`[wm]`) fundindo as duas linhas na renderização final: `[bg][wm]overlay=x:y`.

> [!WARNING]
> O preview gerado na aba "Filtros" atuará como validação de seleção de arquivo, não como preview ao vivo em cima do vídeo base. O processamento da transparência e scala só tomarão forma via hardware durante a chamada da conversão pelo FFmpeg.

---

# [CONCLUÍDO] Normalização Profissional (EBU R128)

Este roteiro documenta a transição do limitador de áudio dinâmico (`dynaudnorm`) para o padrão ouro de mercado para streaming (`loudnorm`).

## 1. Modificações na GUI (`gui/main_window.py`)

A chave de dados mestre (`audio_drc`) será preservada por retrocompatibilidade com presets já salvos pelo usuário. No entanto, a interface visual deve refletir o nível profissional da nova engine.

* **Rebranding da Label:**
  * O texto da opção de áudio na aba pertinente deixará de ser `"Normalizar Vozes / Downmix 5.1 (DRC)"`.
  * O novo texto será: `"Normalização Profissional (EBU R128 / -16 LUFS)"`.

## 2. Motor FFmpeg (`core/ffmpeg_engine.py`)

A engine descartará o compressor agressivo em favor de um processador de "Loudness" real.

* **Filtros Injetados (`af_filters`):**
  * Ao identificar a solicitação de normalização, manteremos o downmix estérico de segurança (`pan=stereo...`). Isso blinda a pipeline contra cancelamento de fase de pistas 5.1/7.1 nativas.
  * Substituição cirúrgica da string `"dynaudnorm"` pelo novo framework: `loudnorm=I=-16:LRA=11:TP=-1.5`.
* **Os Parâmetros R128:**
  * **I=-16 (Integrated Loudness):** Eleva a base de som de forma inteligente, pareando com padrões da Apple e encostando com folga na exigência do YouTube (-14).
  * **LRA=11 (Loudness Range):** Traz folga respiratória. As vozes sobem claras e límpidas, anulando o efeito sonoro de "pumping" provocado pelo antigo dynaudnorm em picos de silêncio.
  * **TP=-1.5 (True Peak):** Um limitador escudo invisível. Impede perfeitamente a distorção do equipamento de som do usuário ao cortar milissegundos estourados a um teto seguro de -1.5 dB.

## 3. Sincronia MPV ao Vivo (`gui/mpv_widget.py`)

O widget que abriga o MPV player precisa gerar um som 1 para 1 idêntico ao da mídia processada no fim.

* A função `update_audio_filters()` espelhará exatamente a regra do core.
* Removeremos o `dynaudnorm` injetando diretamente nos parâmetros da lavfi do MPV: `loudnorm=I=-16:LRA=11:TP=-1.5`.

---

# [CONCLUÍDO] Injeção de Capa (Cover Art) em Arquivos de Áudio

**Objetivo:** Permitir que o usuário insira capas (imagens estáticas) em arquivos de saída estritamente de áudio (MP3, M4A, FLAC, etc.) utilizando a aba de "Marcadores", injetando a imagem no motor FFmpeg sem comprometer as streams de som.

## 1. Modificações na UI (`gui/main_window.py`)

A interface ganhará um módulo para lidar com imagens na aba de **Marcadores**.

* **Painel Visual:** 
  * Adição de um layout horizontal na função `create_tags_tab()`.
  * Inclusão de um `QLabel` fixo (`80x80px` ou `100x100px`) para servir como pré-visualização da imagem (exibindo `(nenhum)` como padrão).
  * Inclusão de um `QLineEdit` bloqueado (somente leitura) que indicará o caminho do arquivo selecionado ou o aviso: *"Sem capa (apenas saída de áudio)"*.
* **Controles Interativos:**
  * Botão **"Escolher imagem..."** acoplado a um `QFileDialog` para restrição nativa de imagens estáticas (`.jpg`, `.jpeg`, `.png`).
  * Botão **"Limpar"** para resetar a seleção, esvaziando a variável de estado e limpando o preview visual.
* **Integração do Dicionário de Metadados:**
  * A variável instanciada `self.meta_cover_path` será embutida no dicionário em `get_ui_options()["metadata"]["cover_path"]`.
  * O reset global em `_reset_advanced_options()` deverá contemplar a limpeza deste bloco.

## 2. A Pipeline do Motor (`core/ffmpeg_engine.py`)

A engine FFmpeg interceptará e injetará fisicamente a capa como uma stream paralela caso o formato alvo seja válido e livre de conflitos.

* **Condição de Segurança (Isolamento de Extensão):**
  * O código irá validar fortemente a intenção cruzando a flag `is_audio_only` (que cobre extensões como `.mp3`, `.m4a`, `.ogg`, `.flac`).
  * Se o usuário carregar uma Capa, mas solicitar uma conversão para vídeo (ex: `.mp4`, `.mkv`, `.webm`), a capa deve ser **silenciosamente descartada** para evitar crashes complexos no mapeamento nativo das faixas de vídeo.
* **Injeção do Input (`-i`):**
  * Ao confirmar que o destino é puramente áudio e o `cover_path` é válido, o arquivo de imagem será inserido como o **segundo input** no comando base: `-i "caminho_da_capa.jpg"`.
* **Modificação do Mapeamento (`-map`):**
  * O bloco clássico de mapeamento de áudio único precisará se desdobrar. A array `cmd` irá requerer as duas fontes independentemente: `-map 0:a?` (resgatando e re-encodando todas as pistas de som do input 0) e `-map 1:v:0` (resgatando a stream de vídeo do input 1, ou seja, a imagem).
* **Parâmetros Mágicos de Fixação (Disposition):**
  * Para forçar o FFmpeg a não tratar a stream `1:v:0` como um clipe em looping e sim como um thumbnail estático nativo de arquivo sonoro, serão acionadas as flags de codec de cópia rápida associadas à manipulação de disposição da stream final: `-c:v copy -disposition:v attached_pic`. Isto embute a foto direto no cabecalho do ID3 e MP4 sem estresse no processador.

---

# [CONCLUÍDO] Controle de Velocidade de Reprodução

**Objetivo:** Introduzir alteração de velocidade de vídeo e áudio nativamente, com suporte a efeitos de Câmera Rápida (Time-lapse) e Câmera Lenta (Slow-motion). Permitirá preservação inteligente do tom do áudio (pitch) para não distorcer as vozes, e integração visual ao vivo nas abas de Sincronia/Cortes.

## 1. Modificações na UI (`gui/main_window.py`)
A interface será construída como uma nova aba chamada **"⏩ Velocidade"**, inserida no painel de opções avançadas (junto de Filtros, Sincronia e Cortes).

* **Estrutura da Aba:**
  * **Texto Explicativo:** `QLabel` com a instrução ("Acima de 1x acelera, abaixo de 1x desacelera").
  * **Predefinições (Botões):** Um `QHBoxLayout` contendo botões estilizados de acesso rápido: `0.25x`, `0.5x`, `0.75x`, `1x`, `1.5x`, `2x`, `4x`. Ao clicar, eles alimentarão diretamente a caixa de valor principal.
  * **Controle Fino:** Um `QDoubleSpinBox` variando de `0.10x` a `10.00x` (com saltos de `0.1`), permitindo ajustes manuais cirúrgicos.
  * **Preservação de Tom:** Um `QCheckBox` "Preservar o tom do áudio" (marcado por padrão) que controla se o usuário terá vozes agudas/graves ou se a voz será processada via Machine Learning/DSP no FFmpeg para manter o timbre realista.
* **Estado e Resets:**
  * As escolhas entrarão no método mestre `get_ui_options()["speed"]` carregando a velocidade numérica e a booleana do pitch.
  * O reset global restaurará para o estado padrão blindado (1.0x, Preservar ativado).

## 2. Integração com o Preview ao Vivo (Aba Sincronia / Cortes)
O player nativo `MPV` possui bibliotecas de som C nativas para espelhar as alterações em Tempo Real na tela, garantindo que o usuário escute a alteração antes de renderizar o arquivo gigantesco!

* **Controle de Tempo na UI:** A propriedade `speed` é inerente ao libmpv. Modificaremos a injeção ao vivo com `self.mpv.speed = velocidade_escolhida`.
* **Controle de Tom ao Vivo:** O MPV mapeia `audio-pitch-correction`. Se a opção "Preservar tom" estiver marcada, ativamos `self.mpv['audio-pitch-correction'] = 'yes'`. Se o usuário desmarcar (buscando voz de robô ou esquilo), mandamos `'no'`. O play visual refletirá 100% da realidade do que será exportado.

## 3. A Pipeline do Motor (`core/ffmpeg_engine.py`)
A mágica ocorrerá via equações matemáticas injetadas nos `vf_filters` (Filtros de Vídeo) e `af_filters` (Filtros de Áudio) diretamente no build do subprocesso final.

* **Vídeo (Filtro `setpts`):**
  * Exige fração invertida. Para um vídeo em 2x de velocidade, o timestamp será metade do original. O comando renderizado dinamicamente será: `setpts=(1.0/SPEED)*PTS` (ex: `setpts=0.5*PTS`).
* **Áudio com "Tom Preservado" (Filtro `atempo`):**
  * O `atempo` não altera o pitch. O limite original do filtro é `0.5` a `100.0`. 
  * Para blindar contra limites, o código fará *chaining* numérico. Se o usuário quiser `0.25x`, geraremos programaticamente a cadeia `atempo=0.5,atempo=0.5` no lavfi array, diluindo o filtro e impedindo crashes silenciosos.
* **Áudio sem "Tom Preservado" (Filtro `asetrate`):**
  * Quando desmarcado, a pipeline invocará o binário auxiliar `ffprobe` (via método `get_audio_sample_rate`) para ler o header do arquivo original. 
  * Injetaremos: `asetrate=SAMPLE_RATE*SPEED`. Se for `44100Hz` original à `2x` = `88200Hz` (áudio super agudo e ligeiro).
  * Encadearemos um fix forçado de `aresample=SAMPLE_RATE` para abaixar o buffer de volta ao suporte do container padrão, garantindo que codecs sensíveis de áudio enxerguem o fluxo perfeitamente natural (mesmo com os timbres e tempos totalmente modificados pela UI).

---

# [CONCLUÍDO] Menu de Contexto Nativo ("Abrir com...")

**Objetivo:** Integrar o Lyra-Qt aos menus de contexto nativos dos principais gerenciadores de arquivos do ecossistema Linux (Nemo, Dolphin, Nautilus, Caja), permitindo que o usuário clique com o botão direito em múltiplos arquivos de mídia e adicione à fila instantaneamente.

## 1. Modificações de Desktop Entry (Scripts de Build)
Utilizaremos a especificação Desktop Entry da FreeDesktop (XDG).

* **Construção Debian (`build_scripts/auto_build.sh`):**
  * Modificação da string do arquivo `lyra-multimedia-converter.desktop`.
  * Adição da tag semântica: `MimeType=audio/*;video/*;image/*;`
  * Modificação da linha `Exec` de `...main.py` para `...main.py %U`. A macro `%U` capacita o repasse de múltiplas URLs locais.
* **Construção Flatpak (`build_scripts/com.github.vagnarok.lyra.yml`):**
  * O manifesto embutido receberá os mesmos identificadores de MimeType e Macro Executiva (`Exec=lyra %U`). 
  * O script Bash `/app/bin/lyra` repassará o argumento automaticamente via wildcard nativo (`"$@"`).

## 2. Leitura de Argumentos via CLI (`main.py`)
A execução cruzada via gerenciador invoca o binário do app via Terminal invisível. 

* A rotina de inicialização em `main.py` deverá varrer o array do Kernel (`sys.argv[1:]`).
* Exclusão proativa de argumentos nativos do Qt/PySide (`--platform`, `--wayland`, etc).
* Geração de um array `files_to_load` com os caminhos absolutos confirmados das mídias enviadas.

## 3. Injeção Direta na View (`gui/main_window.py`)
O app deverá ser capaz de injetar dados na Grid instantaneamente.

* Após o carregamento do pacote gráfico (`window = LyraMainWindow()`), faremos uma intercepção.
* Loop sobre cada string em `files_to_load`, chamando silenciosamente `window.add_file_to_table(caminho)`.
* **Impacto na UX:** Esta estratégia ignora popups pesados. A janela já nasce (via evento `.show()`) com todos os metadados de `ffprobe` e mídias visíveis prontas na mesa.

---

# [CONCLUÍDO] Refatoração do Layout de Opções Avançadas (Tabs Verticais)

**Objetivo:** Reestruturar a interface gráfica das "Opções Avançadas" substituindo o modelo horizontal (cujas dezenas de abas estavam ocultando botões críticos ou forçando rolagem lateral) por uma abordagem moderna com Menu Lateral (List Widget) associado a um painel dinâmico em pilha (Stacked Widget). Isso garante robustez visual perpétua para acomodar dezenas de novos recursos futuros sem quebrar a Experiência de Usuário (UX).

## 1. Substituto do Painel Tabular Central (`gui/main_window.py`)
A função que instanciava as opções de conversão sofrerá um bypass arquitetural drástico:
* **Remoção Absoluta:** Extermínio do elemento `self.tab_widget = QTabWidget()` instanciado na `create_advanced_page()`.
* **Novo Layout-Pai:** Implantação de um `QHBoxLayout` (Divisão de Tela lado a lado).
* **Navegação:** Injeção do `QListWidget` do lado esquerdo com trava de redimensionamento fixo e rolagem autônoma para garantir a usabilidade.
* **Canvas Exibidor:** Injeção do `QStackedWidget` do lado direito preenchendo o corpo majoritário da tela com as interfaces das ferramentas.

## 2. Refatoração da Inserção das Ferramentas
Atualmente as doze abas instanciam suas telas e as amarram chamando `self.tab_widget.addTab()`. Isso precisa ser reconstruído internamente para cada módulo isolado.
* **Ajuste Lógico Universal:** O código nas 12 funções (`create_audio_tab`, `create_video_tab`, etc) passará a repassar o `QWidget` contendo a ferramenta direto para o Array invisível do `QStackedWidget`.
* **Link de Navegação:** Uma string contendo o título da aba e seu ícone será injetada em um item do `QListWidget`.
* **Conector Signal/Slot:** Um trigger `currentRowChanged` no menu lateral forçará a atualização imediata (`setCurrentIndex`) do StackedWidget, refletindo instantaneamente a aba selecionada sem causar *freezes*.

---

# [CONCLUÍDO] Painel de Vídeo Avançado (Estilo Handbrake)

**Objetivo:** Reconstruir a aba "Vídeo" com suporte massivo a controles profissionais (semelhante ao UI do Handbrake), garantindo que usuários avançados consigam manipular o Encoder com perfeição diretamente da interface, sem precisar decorar parâmetros longos de linha de comando.

## 1. Nova Interface (`gui/main_window.py`)
A função `create_video_tab()` receberá um layout completo (provavelmente utilizando agrupamentos `QGroupBox` ou `QGridLayout`) para espelhar as opções solicitadas.

### Elementos:
* **Modo de Taxa de Quadros:** Dois `QRadioButton`: "Taxa constante de quadros (CFR)" e "Taxa de quadros por pico (VFR)".
* **Color Range:** `QComboBox` com as opções (Auto, Limited, Full).
* **Predefinido (Preset):** Um `QSlider` horizontal ou `QComboBox` com suporte às predefinições universais (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow, placebo).
* **Sintonia (Tune):** `QComboBox` (none, film, animation, grain, stillimage, psnr, ssim, fastdecode, zerolatency).
* **Perfil (Profile):** `QComboBox` dinâmico focado em perfis clássicos (baseline, main, high, etc).
* **Nível (Level):** `QComboBox` dinâmico variando sobre os suportes tradicionais (auto, 3.0, 3.1, 4.0, 4.1, 4.2, 5.0, 5.1, 5.2).
* **Opções Adicionais:** Um `QTextEdit` ou `QLineEdit` projetado para injetar parâmetros customizados no encoder (ex: `-x264-params` ou extras limpos).
* **Passe de Análise Turbo:** Um `QCheckBox` complementar ao modo de 2-pass.
* **Codificação Rápida:** Um `QCheckBox` complementar.

## 2. Injeção Dinâmica em `get_ui_options`
* Captura de todos os widgets implementados em um dicionário agrupado em `get_ui_options`.

## 3. Modificações no FFmpeg Engine (`core/ffmpeg_engine.py`)
O motor extrairá as marcações de interface para forjar os argumentos:
* **VFR/CFR:** Injeção rigorosa de `-fps_mode vfr` ou `-fps_mode cfr` nas flags do `-r`.
* **Color Range:** `tv` para Limited, `pc` para Full.
* **Preset, Tune, Profile, Level:** Conectados nas respectivas propriedades puras: `-preset`, `-tune`, `-profile:v`, `-level`.
* **Turbo Pass e 2-Pass:** Mapear a passagem 1 com `-fastfirstpass 1` ou forçando `-preset ultrafast` somado à supressão temporal para turbinar o _log creation_.
* **Opções Adicionais:** Flag nativa `-x264-params` sendo repassada com segurança caso codec seja compatível.
