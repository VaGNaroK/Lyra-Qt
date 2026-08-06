# Regras de UX e UI (Experiência do Usuário)

O Lyra-Qt segue diretrizes rigorosas de design para garantir que uma ferramenta complexa de mídia pareça simples e "blindada".

## 1. Interface Responsiva ("Blindada")
- **Regra de Ouro**: A interface **nunca** deve congelar. Todos os processamentos, downloads e detecções (ex: Auto-Crop) devem ocorrer fora da thread principal usando `QProcess` ou threads secundárias.
- **Feedback Constante**: Sempre forneça feedback visual (mudança de texto de botões, barras de progresso ativas, logs rodando). O usuário precisa saber que o app está trabalhando e não travou.

## 2. Tipografia e Ícones Emojis
- A interface utiliza amplamente emojis padrão do sistema (`🚀`, `🛑`, `📂`, `🎬`, `🖼️`, etc.) nos títulos, abas e botões para tornar o software visualmente atraente e menos intimidador, dispensando a necessidade imediata de ícones externos pesados.
- **Fontes**: Em blocos de código/log (ex: Log do FFmpeg, Info de Mídia), utilize fontes `monospace` (tamanho menor, ex: 11px a 13px) para fácil leitura técnica.

## 3. Padrões de Layout e Cores
- **Botões de Ação Primária** (ex: "🚀 Converter", "📥 Iniciar Download"): Devem usar cores destacadas (Verde `#2E7D32` ou Azul `#0277BD`) e fonte em negrito.
- **Botões de Cancelamento**: Devem ser vermelhos (`#C62828`).
- **Estados Visuais**: Desabilite (gray-out) opções conflitantes automaticamente (ex: desativar opções de bitrate se "CRF" for selecionado).

## 4. Comunicação Humanizada
- Traduções técnicas do FFprobe devem ser renderizadas de forma humanizada (ex: `get_human_media_info()` deve exibir tamanho em MB, duração amigável).
- Nomes técnicos nos combos (ex: `libx264`) devem preferencialmente ser sucedidos por uma descrição se necessário, ou as opções de qualidade devem informar seu impacto: `23 (Qualidade Normal)`, `0 (Sem Perdas)`.

## 5. Bandeja do Sistema e Notificações
- Suporte a `QSystemTrayIcon`. Se fechado enquanto trabalha, o app vai para o background.
- Notificações enviadas ao sistema nativo alertando término de processos.
- **Fallbacks de Notificação (`notify-send`)**: Ao usar chamadas em subprocesso para emitir notificações no sistema nativo, **nunca** dependa de ícones soltos (ex: `-i lyra`). Sempre forneça o **caminho absoluto** do ícone `.svg` embutido nos assets do projeto para garantir que o gerenciador de área de trabalho exiba a notificação corretamente.
