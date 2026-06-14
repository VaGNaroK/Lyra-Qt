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

## 🛠️ Pré-requisitos (Ambiente de Desenvolvimento)

Para executar o código-fonte na sua máquina, certifique-se de ter instalado:

1. **Python 3.10** ou superior.
2. Bibliotecas Python detalhadas no `requirements.txt` (incluindo `PySide6` e `python-mpv`).
3. **FFmpeg** e **FFprobe** (instalados e disponíveis no PATH do seu sistema).
4. **yt-dlp** (instalado e disponível no PATH do seu sistema).
5. **libmpv** (Exigido para o player da aba Sincronia. Instale via `sudo apt install libmpv-dev` no Ubuntu/Mint ou `sudo pacman -S mpv` no Arch).

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

## 🐧Linux: Pacote Debian (.deb) para Ubuntu/Mint/Debian

O script package.sh extrai a versão atual diretamente do código, estrutura os diretórios do sistema e gera o instalador.

## Como compilar:

Conceda permissão de execução ao script:

   chmod +x package.sh

## Execute o script:

Bash
   ./package.sh

## Como instalar:

Após a compilação, o pacote .deb estará na raiz do projeto. Para instalá-lo, utilize o apt (que resolve automaticamente dependências do sistema, se houver):

sudo apt install ./lyra-*.deb

## 📦 Linux: Pacote Universal (Flatpak Standalone)

Para gerar um pacote universal isolado (Sandbox) que roda em qualquer distribuição Linux, utilizaremos o manifesto YAML do projeto.

## Como compilar (Requer flatpak-builder):

Compile e exporte para um repositório local (execute estando na pasta raiz do Lyra-Qt):

   flatpak-builder --repo=lyra-repo --force-clean diretorio-build build_scripts/com.github.vagnarok.lyra.yml

Gere o arquivo instalável .flatpak (Bundle):

   flatpak build-bundle lyra-repo Lyra-Qt.flatpak com.github.vagnarok.lyra stable

## Como instalar:

Dê dois cliques no arquivo Lyra-Qt.flatpak ou instale via terminal:

flatpak install --user Lyra-Qt.flatpak

## ⚠️ Solução de Problemas (Erro de Runtime Ausente):

Como o pacote standalone não possui acesso à internet para baixar a sua própria base automaticamente, você pode receber o erro: "requer o runtime org.kde.Platform... que não foi localizado".

**Para corrigir:** Basta instalar a plataforma base do KDE via Flathub antes de instalar o aplicativo:

flatpak remote-add --if-not-exists flathub [https://flathub.org/repo/flathub.flatpakrepo](https://flathub.org/repo/flathub.flatpakrepo)
flatpak install flathub org.kde.Platform/x86_64/6.7

> *(Nota: Ajuste a versão `6.7` para a versão exata que o terminal solicitar).*

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