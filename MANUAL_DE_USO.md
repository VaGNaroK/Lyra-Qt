# 📖 Manual de Uso: Lyra Multimedia Converter

Bem-vindo ao **Lyra Multimedia Converter**! Este aplicativo foi desenhado para ser uma "fábrica" de mídias no seu computador. Com ele, você pode transformar vídeos enormes em arquivos leves para WhatsApp, isolar a música de um clipe, limpar chiados de gravações de voz ou até baixar conteúdo da internet, tudo com apenas alguns cliques.

Se você não tem intimidade com termos de edição de vídeo, não se preocupe: este manual foi feito para você.

---

## 1. O Básico: Convertendo seu Primeiro Vídeo ou Áudio

A aba principal **"Conversor"** é onde a mágica acontece. O Lyra pode converter tanto Vídeos quanto Áudios.

### Passo-a-Passo:
1. **Adicionar Arquivos:** Clique no botão grande `Adicionar Arquivos` (ou arraste seus arquivos de mídia para a janela do aplicativo). Você pode escolher dezenas de vídeos de uma vez.
2. **Onde Salvar:** No campo `Pasta de Destino`, clique em `Buscar...` para dizer ao Lyra onde os vídeos novos devem ser salvos (por padrão, eles vão para a sua pasta principal de Vídeos).
3. **Formato de Saída:**
   * **Se quiser vídeo:** Escolha `MP4` ou `MKV` (são os mais universais).
   * **Se quiser apenas o áudio:** Escolha `MP3` (música padrão) ou `OGG`/`WAV`.
4. **Qualidade e Tamanho (Importante!)**
   * **Modo Automático (CRF):** Deixe marcado. Ele ajusta a qualidade de forma inteligente! O valor `18` significa altíssima qualidade. Se você aumentar o número (ex: `28`), o vídeo fica **mais leve**, mas com a imagem um pouquinho mais borrada.
   * **Modo Manual (Bitrate):** Use só se precisar limitar o tamanho do arquivo (ex: "Quero no máximo 2000 kbps para caber no Telegram").
5. **Resolução:** Você quer manter o tamanho original da tela? Deixe em `Original`. Se o vídeo for um 4K pesado e você quiser assistir no celular sem travar, mude para `1280x720` ou `640x360`. O Lyra vai encolher a tela perfeitamente para você.
6. **Iniciar:** Clique em `Iniciar Conversão`. Uma barra de progresso mostrará o tempo exato para terminar!

---

## 2. A Aba de Downloads da Web

Viu um vídeo ou escutou uma música na internet (como no YouTube) e quer guardar no PC? O Lyra faz isso para você sem precisar instalar sites perigosos.

1. Vá na aba lateral **"Baixar Mídia da Web"**.
2. Cole o **Link/URL** do vídeo na barra de endereço.
3. Escolha o destino: onde salvar o arquivo.
4. O que você quer baixar?
   * **Quero um Vídeo:** Marque `Baixar Vídeo`. Escolha a qualidade (Ex: `1080p (FullHD)` se sua TV for boa, ou `720p (HD)` para tocar leve). E escolha o formato (`MP4`).
   * **Quero a Música:** Marque `Apenas Áudio`. O formato de música aparecerá para você escolher (`MP3`, `WAV`, etc.).
5. Clique no ícone de Download azul gigante e espere! O Lyra fará tudo sozinho.

---

## 3. O Poder Oculto: Configurações Avançadas

A aba **Configurações Avançadas** foi feita para consertar problemas que a maioria dos outros programas não consegue.

### 🎧 Ferramentas de Áudio
Se o áudio do seu vídeo está horrível (muito baixo, estourando ou cheio de chiado do vento), use essas opções:
* **Normalizar Volume Inteligente (Leveler / DRC):** Você já assistiu a um filme em que as explosões acordam os vizinhos, mas as vozes são tão baixinhas que você não entende nada? Se você ligar essa caixa, o Lyra vira um engenheiro de som: ele levanta o volume das vozes suaves e abaixa o estouro das explosões. Tudo fica no mesmo nível!
* **Remover Ruído com IA (RNNN):** Se o seu áudio foi gravado num ventilador ou na rua, ative isso. Uma Inteligência Artificial vai isolar apenas a voz humana e apagar o vento e o chiado.
* **Preview ao Vivo:** O Lyra tem um player embutido! Clique em `▶ Preview Audio` para abrir o reprodutor. Se você mexer no volume ou ligar o filtro de voz, **você escuta a mudança na mesma hora**, antes mesmo de converter!

### 💬 Injetando Legendas (Softsub)
Tem um arquivo de filme (`.mp4`) e um arquivo de legenda (`.srt`) solto? 
1. Vá na aba "Legendas e Áudio".
2. Clique em `Adicionar Legendas` e selecione seus arquivos `.srt`.
3. Ao converter, as legendas vão para "dentro" do vídeo de forma mágica, podendo ser ativadas ou desativadas na sua TV ou no Netflix.

### ✂️ Como Cortar um Vídeo (Trimming)
Quer apenas os 10 segundos mais engraçados de um vídeo de 1 hora?
1. Vá na aba **"Cortes"**.
2. O player de vídeo vai abrir.
3. Arraste a linha do tempo (a barra de progresso) até onde o momento legal começa e clique em `[ Marcar Início ]`.
4. Arraste até onde acaba e clique em `[ Marcar Fim ]`.
5. Volte para a aba inicial e clique em "Converter". O Lyra vai jogar fora todo o resto do vídeo em tempo recorde.

---

## 4. O Segredo da Velocidade (Acelerando com a Placa de Vídeo)

Por que o Lyra é tão especial? Ele tem suporte para **NVENC**.

Se você tem uma Placa de Vídeo (GPU) da **NVIDIA**, procure a opção **Codec de Vídeo** na tela inicial e mude de `Padrão (CPU)` para **`H.264 (NVENC)`**.
* **O que acontece?** Em vez de usar o cérebro principal do seu computador (deixando tudo lento e travado enquanto você espera o vídeo renderizar), o Lyra repassa 100% da tarefa bruta para a sua Placa de Vídeo!
* **Resultado:** O seu vídeo converte até 10 vezes mais rápido, e você pode continuar usando seu navegador de internet sem nenhum travamento na máquina.

---

## 5. Resolução de Problemas Rápida (FAQ)

**1. O download do YouTube travou ou deu "Erro na extração"!**
O YouTube altera seu sistema semanalmente para bloquear aplicativos. **Apenas feche o Lyra e tente no dia seguinte, ou atualize o seu pacote**. A equipe de desenvolvedores da ferramenta que usamos costuma consertar isso em poucas horas.

**2. Quero colar vários áudios num vídeo, posso?**
Sim! Na aba "Avançado", na guia de "Legendas e Áudio", você pode adicionar músicas MP3. Elas vão tocar juntas ou poderão ser escolhidas no controle remoto da sua TV.

**3. Marquei H.264 NVENC e recebi uma mensagem vermelha de erro ao iniciar!**
Isso acontece se o seu computador for antigo ou usar placas da Intel/AMD. O NVENC é exclusivo para placas da NVIDIA. Se não for seu caso, volte para `Padrão (CPU)`.

---

🎉 *Pronto! Você já é um mestre no uso do Lyra Multimedia Converter. Aproveite suas mídias!*
