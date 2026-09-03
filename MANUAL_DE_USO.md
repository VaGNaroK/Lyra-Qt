# 📖 Manual de Uso: Lyra Multimedia Converter

![Tela Principal do Lyra](manual/mascot.png)

Bem-vindo ao **Lyra Multimedia Converter**! Este aplicativo foi desenhado para ser uma "fábrica" de mídias no seu computador. Com ele, você pode transformar vídeos enormes em arquivos leves para WhatsApp, isolar a música de um clipe, limpar chiados de gravações de voz, embutir legendas e marcas d'água, acelerar áudios e até baixar conteúdo da internet. Tudo isso com o poder das opções de estúdio acessíveis em poucos cliques.

Se você não tem intimidade com termos de edição de vídeo, não se preocupe: este manual foi feito para você.

---

## 1. O Básico: Convertendo seu Primeiro Vídeo ou Áudio

Na tela inicial, a opção **"Formato:"** é onde a mágica acontece. O Lyra pode converter tanto Vídeos quanto Áudios.

### Passo-a-Passo:
1. **Adicionar Arquivos:** Clique no botão grande `Adicionar Arquivo` ou `Adicionar Pasta` (você também pode simplesmente **arrastar seus arquivos** para dentro do aplicativo).
   * **Dica de Ouro:** O Lyra se integra ao seu sistema! Você pode selecionar vídeos direto nas suas pastas, clicar com o botão direito, ir em **"Abrir com..."** e escolher o Lyra para importá-los instantaneamente!
2. **Onde Salvar:** No campo de destino (na parte inferior), clique na pastinha para dizer ao Lyra onde os arquivos novos devem ser salvos.
3. **Ações ao Concluir:** Vai converter uma pasta gigantesca e quer ir dormir? Use a opção **"Ao Concluir"** no canto inferior direito para programar o Lyra para **Desligar** ou **Suspender** o computador automaticamente quando terminar!
4. **Formato de Saída:**
   * **Se quiser vídeo:** Escolha `MP4` ou `MKV` (os mais universais), ou `WEBM` (ótimo para web).
   * **Se quiser apenas o áudio:** Escolha `MP3` (música padrão), `OGG`, `WAV`, etc.
5. **Iniciar:** Clique em `🚀 Converter` no topo ao lado direito. A barra de progresso mostrará o tempo exato e a estimativa de tamanho!

---

## 2. A Aba de Downloads da Web

Viu um vídeo ou escutou uma música na internet (como no YouTube) e quer guardar no PC? O Lyra faz isso para você.

1. Clique em **"🌐 Baixar da Web"** na barra superior.
2. Cole o **Link/URL** do vídeo na barra de endereço.
3. Modo de extração: Escolha entre `Vídeo Completo` para baixar o vídeo e `Somente Áudio` para baixar apenas o áudio.
4. Resolução Máxima: Escolha entre resoluções `480p`, `720p`, `1080p`, `1440p` ou `2160p` (4K). Recomenda-se usar `720p` ou `1080p` para obter um bom equilíbrio entre qualidade e tamanho de arquivo.
5. Clique no ícone de Download azul e espere! O Lyra fará tudo sozinho e já deixará o arquivo pronto.

---

## 3. O Poder Oculto: Menu de Opções Avançadas

Clicando no botão **"⚙️ Opções Avançadas"** no topo, você acessa a "Nave Espacial" do Lyra. Toda a interface aqui é dividida em **Abas Verticais (Menu Lateral)**, agrupadas por categorias.

### 🎧 Ferramentas de Áudio
Se o áudio do seu vídeo está estourando, abafado ou cheio de chiado de vento:
* **Leveler / DRC (Normalizador de Volume):** Equaliza o áudio. Levanta o volume das vozes suaves e abaixa o estouro das explosões.
* **Remoção de Ruído com IA (RNNN):** Isola a voz humana, apagando o chiado do vento e os ruídos de fundo.

### 🎥 Aba de Vídeo (Controles de Estúdio e Otimização do Codificador)

A aba de Vídeo do Lyra foi desenhada com inspiração nas melhores ferramentas profissionais de estúdio (como o HandBrake e FFmpeg avançado), oferecendo controle cirúrgico sobre como o vídeo é processado:

#### 1. Configurações Básicas e Qualidade
* **Taxa de Quadros (FPS) - CFR vs VFR:**
  * **CFR (Constant Frame Rate / Taxa Constante):** Trava a quantidade de quadros por segundo rigorosamente (ex: 30.00 ou 60.00 fps fixos). É **obrigatório** caso você planeje importar o vídeo em editores como Adobe Premiere, DaVinci Resolve ou Final Cut, pois evita que o áudio saia de sincronia ao longo da linha do tempo.
  * **VFR (Variable Frame Rate / Taxa Variável):** Permite que a taxa de quadros varie em momentos de pouca ação (típico de celulares e gravações de tela), economizando espaço em disco.
* **Qualidade Inteligente (CRF - Constant Rate Factor):**
  * Controla a fidelidade visual perceptual. O padrão recomendado é **23**.
  * Números menores (ex: 18 a 20): Qualidade visual praticamente indistinguível do original (Master de cinema), com arquivo maior.
  * Números maiores (ex: 26 a 28): Alta compressão para arquivos super leves, ideal para compartilhamento rápido ou mensagens.
* **2-Pass (Duas Passadas) e Turbo First Pass:**
  * Usado quando você desmarca o CRF e escolhe um Bitrate alvo fixo (ex: 2500 kbps). O Lyra analisa todo o vídeo na primeira passada e distribui os bits de forma inteligente na segunda passada, garantindo máxima fidelidade dentro do limite de tamanho.
  * O **Turbo First Pass** acelera a primeira passada em modo ultra-rápido, economizando até metade do tempo total de conversão!

#### 2. Painel de Otimização do Codificador (`Encoder Optimization`)
Este painel calibra o comportamento interno dos encoders (`libx264`, `libx265`, etc.):

* **Gama de Cores (Color Range):**
  * **Auto:** Preserva as propriedades originais do arquivo.
  * **Limited (Padrão de TV/Streaming):** Faixa de luma 16-235. É o padrão internacional de filmes, séries, YouTube e televisores. Impede que sombras pretas virem borrões sem detalhe em telas de TV.
  * **Full (Padrão de PC/Data):** Faixa de luma 0-255 total. Ideal para vídeos gravados diretamente no computador (gameplays de PC, capturas de tela com OBS, apresentações), preservando o preto puro e o branco máximo do monitor.

* **Predefinição (Preset):**
  * Controla o tempo que o processador dedica para encontrar a melhor compactação matemática possível.
  * *Importante:* O preset **não** altera a qualidade visual quando o CRF está ativo; ele altera o **tamanho final do arquivo** para a mesma qualidade!
  * **ultrafast / superfast / veryfast:** Codificação instantânea com compressão simples. Gera arquivos maiores, mas converte quase instantaneamente. Ideal para testes ou computadores modestos.
  * **medium (Padrão):** O equilíbrio perfeito entre tempo de espera e economia de espaço em disco.
  * **slow / slower:** Realiza cálculos profundos de vetores de movimento. Demora mais para processar, porém entrega arquivos até 10-15% menores mantendo a mesma nitidez visual. Recomendado para guardar filmes definitivos no HD.
  * **veryslow / placebo:** Compressão exaustiva com ganhos marginais.

* **Ajuste Fino (Tune):**
  * Calibra as matrizes psicovisuais do encoder de acordo com o tipo de imagem gravada:
    * **none:** Uso geral padrão.
    * **film:** Para filmes e séries live-action com pessoas reais (preserva contraste e bordas naturais).
    * **animation:** Para desenhos animados, animes e arte vetorial 2D/3D. Mantém traços pretos afiados e áreas uniformes de cor sem ruídos de compressão.
    * **grain:** Para filmes clássicos ou obras com granulado de película analógica. Evita que o encoder tente "limpar" o grão do filme, mantendo a textura cinematográfica original.
    * **fastdecode:** Desativa recursos pesados de descompressão, facilitando a reprodução em dispositivos lentos.
    * **zerolatency:** Elimina buffers e lookahead para transmissões com latência zero.

* **Perfil (Profile):**
  * Estabelece os recursos de decodificação que o reprodutor final deve suportar:
    * **auto:** Permite ao encoder escolher a melhor opção automaticamente.
    * **baseline:** Modo legado sem recursos modernos. Ideal para aparelhos muito antigos (smartphones de 2010 ou centrais multimídia automotivas antigas).
    * **main:** Padrão clássico de TV digital aberta.
    * **high (Recomendado):** O padrão universal para vídeos modernos em 1080p (compatível com 100% dos navegadores, Smart TVs e celulares atuais).
    * **high10:** Suporte nativo a profundidade de 10 bits, eliminando o efeito de faixas (*color banding*) em céus e cenas escuras.

* **Nível (Level):**
  * Define os limites de hardware (resolução máxima, bitrate e fps aceitos pelo chip gráfico):
    * **auto (Recomendado):** Calcula automaticamente a melhor compatibilidade.
    * **3.1:** Para telas pequenas até 720p @ 30fps.
    * **4.0 / 4.1:** Padrão universal do Blu-ray e YouTube 1080p @ 30fps.
    * **5.1 / 5.2:** Projetado para reproduzir mídias pesadas em 4K UHD @ 60fps.

* **Decodificação Rápida (Fast Decode):**
  * Caixa de seleção rápida que injeta flags para aliviar o consumo de bateria e processamento na hora de assistir. Recomendado para dispositivos fracos.

* **Opções Extras do x264/x265 (Custom Parameters):**
  * Permite que usuários avançados passem parâmetros internos diretos para a biblioteca do encoder (ex: `no-sao=1` no x265 para impedir que rostos fiquem excessivamente "emborrachados" ou plastificados).

* **Apenas Vídeo (Sem Áudio) & Corrigir Índice Quebrado (Bad Index):**
  * **Apenas Vídeo:** Remove completamente qualquer áudio (`-an`), útil para B-rolls e telas de espera.
  * **Corrigir Índice Quebrado:** Aplica `-fflags +genpts`, gerando novos carimbos de tempo para vídeos danificados da web que travam ao tentar pular cenas.

#### 💡 Guia Rápido de "Receitas" Recomendadas:
* 🍿 **Filmes e Séries:** `Preset: slow` + `Tune: film` + `Profile: high` + `CRF: 21 a 23`.
* 🎌 **Animes e Desenhos:** `Preset: medium` + `Tune: animation` + `Profile: high10` (se fonte for 10-bit) ou `high`.
* 🎮 **Gameplays de PC (Gravados em RGB):** `Color Range: Full` + `FPS Mode: CFR` + `Preset: fast ou medium`.
* 📺 **Máxima Compatibilidade com TVs / Aparelhos Antigos:** `Color Range: Limited` + `Profile: high` + `Level: 4.1` + `Fast Decode: Marcado`.
* 🎬 **Edição no Premiere / DaVinci Resolve:** `FPS Mode: CFR` (obrigatório para sincronia perfeita de áudio).


### ⏱️ Aba de Velocidade
Quer o vídeo mais rápido ou mais devagar? 
* Aqui você escolhe a aceleração de **0.1x até 10.0x**.
* **Preservar Tom do Áudio:** Deixe essa caixa marcada para evitar a "Voz de Esquilo" (pitch distorcido). O Lyra fará o processamento pesado e as vozes continuarão normais mesmo 2x mais rápido!

### 🖼️ Aba de Marcadores (Capas e Metadados)
Ideal para músicos e podcasts:
* Preencha dados como **Título, Artista, Álbum e Ano**. O título servirá como nome final do arquivo!
* **Injeção de Capa (Cover Art):** Selecione uma imagem (JPG/PNG) e ela ficará embutida magicamente dentro do seu MP3, FLAC ou OGG, aparecendo no rádio do carro ou no reprodutor do celular!

### 💬 Aba de Legendas e ✨ Filtros
* Adicione legendas `.srt` soltas aos seus vídeos ou extraia as legendas existentes!
* Insira uma **Marca D'água** (logotipo) por cima dos seus vídeos! Você define a posição (canto, centro), o tamanho e até a opacidade, perfeito para proteger seus vídeos antes de postar na internet.

### ✂️ Aba de Cortes (Trimming)
Quer apenas os 10 segundos mais engraçados de um clipe?
1. Acesse a aba **Cortes**. O player de vídeo abrirá na tela.
2. Arraste a linha do tempo e use os botões **`⏱️ Marcar Início`** e **`⏱️ Marcar Fim`**.
3. Volte para a aba principal e converta. O Lyra excluirá o resto do vídeo em tempo recorde!

---

## 4. O Segredo da Velocidade (Acelerando com a Placa de Vídeo)

Se você tem uma Placa de Vídeo (GPU) da **NVIDIA**, você tem um superpoder.
* Vá nas **Opções Avançadas -> Aba de Vídeo** e mude o Codec de Vídeo para **`h264_nvenc`** ou **`hevc_nvenc`**.
* O Lyra repassará a tarefa de renderização 100% para a sua Placa de Vídeo! O vídeo converte muito mais rápido, sem travar o processador principal do seu computador.

---

## 5. Resolução de Problemas (FAQ)

**1. A opção "Codificação com várias passagens" ou "Turbo" estão cinzas/bloqueadas!**
O FFmpeg só permite essas opções em cenários específicos. Vá na aba de Vídeo, **desmarque a "Qualidade Inteligente (CRF)"** e certifique-se de que o codec `libx264` ou `libx265` está selecionado.

**2. O download do YouTube travou ou deu "Erro na extração"!**
O YouTube altera seu sistema frequentemente para bloquear aplicativos. **Apenas feche o Lyra e tente novamente mais tarde, ou rode o script de atualização do pacote**. Nossa base (yt-dlp) atualiza constantemente para contornar bloqueios.

**3. Marquei NVENC e recebi uma mensagem de erro ao iniciar!**
Isso acontece se o seu computador usar placas da Intel/AMD ou for incompatível. O NVENC é exclusivo para placas da NVIDIA. Volte o Codec para `libx264` e a conversão prosseguirá normalmente na CPU.

**4. Atualizei o driver de vídeo no Linux e o Lyra parou de converter!**
Se você estiver usando a versão **Flatpak**, o ambiente isolado do aplicativo ainda está conectado à cópia da versão antiga do seu driver de vídeo. Para resolver, basta abrir o terminal e digitar `flatpak update`.

---

🎉 *Pronto! Você já domina 100% da fábrica de mídias do Lyra Multimedia Converter.*
