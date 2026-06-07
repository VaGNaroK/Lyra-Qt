# Software Design Document (SDD) - Lyra-Qt

## 1. Introdução
Este documento serve como índice mestre de design do projeto Lyra-Qt. Ele unifica e padroniza a arquitetura, regras operacionais de UI/UX, e as diretrizes de código que devem guiar futuras adições de funcionalidades ao Lyra.

## 2. Índice de Especificações
Todo o projeto deve estar submetido às regras descritas na documentação vinculada abaixo. As alterações e propostas de PR (Pull Request) devem respeitar as metodologias e padrões em:

- 🏛️ **Arquitetura Geral**: Ver [`docs/arquitetura.md`](../docs/arquitetura.md)
- 📦 **Descrição dos Módulos**: Ver [`docs/modulos.md`](../docs/modulos.md)
- 🎨 **Regras de Interface (UX/UI)**: Ver [`docs/ux-rules.md`](../docs/ux-rules.md)
- 🏎️ **Aceleração e Hardware (GPU)**: Ver [`docs/gpu-pipeline.md`](../docs/gpu-pipeline.md)
- 📝 **Padrões de Escrita (Coding Standards)**: Ver [`docs/coding-standards.md`](../docs/coding-standards.md)
- 🐛 **Histórico de Regressões e Bugs Notórios**: Ver [`docs/regressions-history.md`](../docs/regressions-history.md)

## 3. Estado Atual do Sistema
O sistema encontra-se numa arquitetura PySide6 unindo múltiplas ferramentas GNU (FFmpeg, yt-dlp) e engines multimídia nativos (MPV). 
O SDD reforça que as implementações respeitem o paradigma `Model-View-Controller`, delegando UI para `LyraMainWindow` (e seus componentes acopláveis, como `MPVPlayerWidget`) e processamento para `FFmpegEngine` e `YTDLPEngine`. O motor FFmpeg foi projetado para operações MUX não-destrutivas (preservando legendas originais nativamente) usando a flag de mapeamento acumulativo seletivo (`-map 0:v:0`, `-map 0:s?`), suportando múltiplas injeções de faixas sem perdas estruturais ou bugs com imagens de capa, e incluindo injeção dinâmica de filtros temporais (`adelay`, `atrim`). Adicionalmente, adota-se o recurso de Mapeamento Negativo (`-map -0:X?`) alimentado pelo `ffprobe` para descarte cirúrgico de trilhas indesejadas pelo usuário. A arquitetura de áudio conta com um *Pipeline* de Tempo Real que espelha os filtros libavfilter (`volume`, `dynaudnorm`, `arnndn`) da interface direto para a instância do `libmpv`, garantindo fidelidade total entre preview e conversão. Dependências externas mutáveis (como `yt-dlp` e bibliotecas dinâmicas C como `libmpv`) devem ser estritamente gerenciadas dentro do ambiente virtual (`venv`) e rastreadas via `requirements.txt`, com a respectiva injeção standalone em binários (PyInstaller) ou scripts de compilação.

## 4. Evolução
O projeto é vivo. Adições futuras de motores (Ex: Integração com bibliotecas AI de Upscaling, ou APIs externas) devem gerar um novo arquivo de "Engine" no repositório `/core`, expondo um contrato de Slots/Signals transparente compatível com o estipulado na documentação do projeto.
