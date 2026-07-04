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
