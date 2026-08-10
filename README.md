# 🌌 Lyra Multimedia Converter

O **Lyra Multimedia Converter** é uma interface gráfica (GUI) moderna, modular e de altíssimo desempenho para conversão de mídia e downloads da web. Desenvolvido em Python com PySide6, o aplicativo funciona como um "canivete suíço" multimídia, abstraindo toda a complexidade do **FFmpeg** e do **yt-dlp** em uma experiência de usuário fluida e blindada.

![Licença](https://img.shields.io/badge/License-GPLv3-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10+-yellow.svg)
![Plataforma](https://img.shields.io/badge/Plataforma-Linux%20%7C%20Windows-lightgrey.svg)

---

> [!TIP]
> 📖 **É novo por aqui ou não entende muito de vídeos?**  
> Preparamos um **[Manual do Usuário Passo-a-Passo](MANUAL_DE_USO.md)** super amigável para você aprender a extrair 100% do poder do Lyra!

## ✨ Principais Recursos

* 🎬 **Conversão Universal:** Suporte nativo para os formatos mais populares do mercado (MP4, MKV, AVI, MP3, OGG, WAV, JPG, PNG, WEBP, entre outros).
* 🧠 **Qualidade Inteligente (CRF / CQ):** Controle de qualidade visual constante sem a necessidade de adivinhar o bitrate manualmente, otimizado para CPU ou NVENC (Nvidia).
* ✂️ **Auto-Crop Mágico:** Detecção automática de bordas pretas (Letterbox) e preenchimento matemático dos parâmetros de corte.
* 🎛️ **Áudio de Cinema (DRC):** Downmix inteligente de 5.1/7.1 para Estéreo com normalização dinâmica (`dynaudnorm`), nivelando efeitos sonoros e vozes.
* 🌐 **Download da Web Integrado:** Motor do yt-dlp embutido para baixar vídeos e áudios com seleção cirúrgica de resolução e formato.
* 📝 **Multiplexação Avançada (MUX):** Injeção de múltiplas trilhas de áudios externos e dezenas de legendas (Softsub) de forma acumulativa, sem perder as faixas originais do contêiner nativo (MKV/MP4).
* 💾 **Sistema de Presets:** Salve, carregue e gerencie as suas configurações favoritas de renderização com um clique.
* ⚡ **Arquitetura Assíncrona:** Interface 100% responsiva (não congela) com feedback visual detalhado sobre o progresso, tempo restante e logs em tempo real.
---

## 🏗️ Arquitetura do Projeto

O Lyra-Qt foi desenhado sob uma arquitetura robusta baseada no **Paradigma MVC (Model-View-Controller)**, com foco extremo em concorrência (Assincronicidade) e separação estrita de responsabilidades. Isso garante que a interface gráfica (GUI) nunca congele, mesmo durante processamentos intensos (como encodes 4K em hardware ou downloads paralelos via yt-dlp).

* 🎨 **Interface (GUI) Isolada**: Toda a construção visual (PySide6) e o gerenciamento de estados (inputs de usuário) ficam contidos exclusivamente na pasta `gui/` (ex: `main_window.py`). A GUI *não* realiza nenhuma lógica bruta de parsing de dados, servindo apenas como controladora.
* ⚙️ **Motores (Core Engines)**: A lógica pesada de processamento reside na pasta `core/` (`ffmpeg_engine.py`, `ytdlp_engine.py`, `preset_manager.py`). Estes motores funcionam como "Backend" e se comunicam com a Interface de forma segura através do sistema nativo de **Signals e Slots** do Qt, trafegando apenas dados primitivos (dicionários, ints e strings limpas) para evitar falhas de ponteiro (C++).
* 🔧 **Processamento Nativo Constante (Sem Wrappers)**: O Lyra se recusa a usar wrappers engessados (como `ffmpeg-python`). Ele instila comandos nativos complexos e invoca os binários oficiais do **FFmpeg**, **FFprobe** e **yt-dlp** via `QProcess` e `subprocess`. O progresso é alimentado na interface capturando e realizando leitura ultra-rápida (Regex) de seus `stdouts`/`stderrs`.
* 🛡️ **Awareness de Sistemas e Sandbox**: O código gerencia de perto as peculiaridades do host, resolvendo dependências automaticamente e alterando dinamicamente o fluxo caso esteja rodando sob Sandboxes blindadas do Linux (ex: restrições Flatpak/Wayland, bypass de MPRIS, injeção de D-Bus) ou diretórios virtuais portáteis (PyInstaller no Windows, via injeção dinâmica no `%PATH%`).

---

## 🛠️ Pré-requisitos (Ambiente de Desenvolvimento)

Para executar o código-fonte na sua máquina, certifique-se de ter instalado:

1. **Python 3.10** ou superior.
2. Bibliotecas Python detalhadas no `requirements.txt` (incluindo `PySide6` e `python-mpv`).
3. **FFmpeg** e **FFprobe** (instalados e disponíveis no PATH do seu sistema).
4. **yt-dlp** (instalado e disponível no PATH do seu sistema).
5. **libmpv** (Exigido para o player da aba Sincronia. Instale via `sudo apt install libmpv-dev` no Ubuntu/Mint ou `sudo pacman -S mpv` no Arch).
6. **libxcb-cursor0** (Apenas no Linux, exigido pelo PySide6/Qt 6.5+ para iniciar a interface gráfica. Instale via `sudo apt install libxcb-cursor0` no Ubuntu/Mint).


---

## 💻 Como Executar o Código-Fonte

1. **Clone este repositório:**

   git clone [https://github.com/vagnarok/lyra.git](https://github.com/vagnarok/lyra.git)
   cd lyra

## Crie e ative um ambiente virtual (Recomendado):

   python3 -m venv venv
   source venv/bin/activate  # No Windows: .\venv\Scripts\activate

## Instale as dependências:

   pip install -r requirements.txt

## Inicie o aplicativo:

   python3 main.py

## 📦 Compilação e Instalação

O Lyra foi projetado para ser distribuído facilmente. Abaixo estão as instruções detalhadas para empacotar o projeto em diferentes formatos e como instalá-los. Execute os comandos de compilação sempre a partir da raiz do projeto.

## 🐧 Linux: Pacotes Debian (.deb) e Universal (Flatpak)

O Lyra-Qt possui um script unificado (`auto_build.sh`) que extrai a versão atual do código, resolve as dependências do sistema (como `flatpak-builder` e SDKs do KDE), estrutura os diretórios, compila e gera o instalador (.deb ou .flatpak) automaticamente.

### Como compilar e instalar:

Conceda permissão de execução ao script (necessário apenas na primeira vez):

```bash
chmod +x build_scripts/auto_build.sh
```

Execute o script interativo:

```bash
./build_scripts/auto_build.sh
```

O script perguntará:
1. Qual formato você deseja gerar (`1` para Flatpak ou `2` para Debian .deb).
2. Se você deseja realizar a instalação automática no sistema após a compilação.
3. (Apenas no Flatpak) Se a instalação deve ser feita para o usuário atual (`user`) ou para todos (`system`).

Ao final do processo, caso você escolha não instalar automaticamente, o pacote final (`.deb` ou `.flatpak`) será gerado na pasta raiz do projeto.

## ⚠️ Solução de Problemas Comuns (Flatpak)

### 1. Erro de Runtime Ausente na Instalação
Como o pacote standalone (`.flatpak`) do Lyra gerado localmente não possui acesso à internet para baixar a sua própria base automaticamente, você pode receber o erro: *"requer o runtime org.kde.Platform... que não foi localizado"*.

**Para corrigir:** Basta instalar a plataforma base do KDE via Flathub antes de instalar o aplicativo:
```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.kde.Platform/x86_64/6.7
```
> *(Nota: Ajuste a versão `6.7` para a versão exata que o terminal solicitar).*

### 2. Aceleração de Hardware (NVENC/CUDA) Falhando Após Atualizar o Linux
Se você usa placa de vídeo **NVIDIA**, atualizou o driver recentemente no seu sistema operacional (host) e o Lyra em Flatpak repentinamente começou a exibir o erro **`Cannot load libcuda.so.1`** ou **`Operation not permitted`** ao usar aceleração de hardware:

**Causa:** O ambiente isolado (Sandbox) do Flatpak possui uma cópia exata do driver de vídeo. Quando você atualiza o sistema, essa cópia fica defasada (Mismatch).
**Para corrigir:** Sempre que você atualizar o driver NVIDIA do seu computador, execute o comando de atualização do Flatpak no terminal para que ele baixe a extensão gráfica mais recente correspondente ao seu sistema:
```bash
flatpak update
```
*(Nota: Pode levar alguns dias até que novos drivers beta/recém-lançados sejam empacotados pela loja Flathub).*

---

### 🪟 Windows: Executável Autônomo (PyInstaller)

O script `build_scripts/build_windows.ps1` orquestra o PyInstaller para compilar o código, além de baixar as dependências automaticamente (FFmpeg e yt-dlp) e injetar os recursos visuais nativos na aplicação.

**Como compilar:**
1. Abra o **PowerShell** como Administrador (ou libere a execução de scripts na sessão atual) rodando:
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force
   ```
2. Execute o script de compilação a partir da raiz do projeto:
   ```powershell
   .\build_scripts\build_windows.ps1
   ```

**Como instalar (Uso):**

Não é necessária instalação tradicional (Setup). O projeto será compilado no modo "Standalone".
1. Vá até a pasta `dist/` gerada na raiz do projeto.
2. Você encontrará a pasta ou o executável final `Lyra.exe`. Basta copiar essa pasta para onde desejar (ex: `C:\Program Files\Lyra`) e criar um atalho na sua Área de Trabalho.

---

## 📄 Licença

Este projeto é licenciado sob a **GNU General Public License v3.0 (GPL-3.0)**. 
Isso significa que você é livre para usar, modificar e distribuir o software, contanto que as modificações e trabalhos derivados também sejam de código aberto e distribuídos sob a mesma licença.

Para mais detalhes, veja o arquivo `LICENSE` incluído neste repositório.

---
*Desenvolvido com ☕ e 💻 por VaGNaroK com Ajudinha de IA.*