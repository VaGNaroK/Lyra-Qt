# Histórico de Regressões e Fixes Comuns (Regressions History)

Este documento acompanha bugs e regressões resolvidos ao longo do projeto, para garantir que não retornem em versões futuras e servir de lição aprendida.

## 1. Sumiço de Abas na Main Window
- **Problema**: A aba "🎵 Áudio" desapareceu durante uma refatoração e otimização visual na criação das tabs.
- **Sintoma**: O usuário perdeu totalmente os controles de extração de áudio, codec e bitrate de som.
- **Fix (🔒)**: A chamada `self.tab_widget.addTab(tab, "🎵 Áudio")` havia sido excluída equivocadamente na versão anterior. Foi reinserida na função `create_audio_tab`.

## 2. Layout Quebrado em QGroupBox com Títulos Emojis
- **Problema**: O uso de emojis nos títulos (ex: `🛠️ Configurações do Download`) nos componentes `QGroupBox` sobrepunha a borda da caixa, ficando esteticamente quebrado dependendo do tema do SO.
- **Fix (🔒)**: Aplicado um stylesheet universal forçando margens: `group_config.setStyleSheet("QGroupBox::title { padding-right: 40px; }")`. Isso empurra o limite e compensa o render das fontes de sistema nativas.

## 3. Subprocess Travando a GUI ("Congelamento Negro")
- **Problema**: Inicialmente, rodar o `ffprobe` bloqueava o frame da interface do PySide6 enquanto sondava mídias lentas. Janelas pretas (CMD) piscavam agressivamente no Windows.
- **Fix**: Alteração para esconder a janela no Windows via `subprocess.STARTUPINFO` e `STARTF_USESHOWWINDOW`. Operações mais demoradas integraram `timeout=5`.

## 4. Erro de Execução de Audio Multi-Faixas em Atualizações (Event Block)
- **Problema**: Ao varrer metadados de novas mídias e popular a lista (`combo_audio_track.clear()`), o signal `currentIndexChanged` era disparado recursivamente acidentalmente.
- **Fix (🔒)**: Envolvido o repopulamento com `.blockSignals(True)` e `False` logo em seguida na função `on_file_selected_for_info`.

## 5. Falha ao Selecionar Diretório no Windows (QFileDialog)
- **Problema**: No ambiente Windows, o botão de procurar diretório (tanto para "Destino da conversão" quanto para "Adicionar Pasta") estava impossibilitado de confirmar a seleção de pastas. O diálogo não-nativo do Qt operava como seletor de arquivos.
- **Sintoma**: O usuário não conseguia configurar a pasta de destino porque o botão de confirmação ficava desativado, esperando a seleção de um arquivo.
- **Fix (🔒)**: O parâmetro padrão `QFileDialog.ShowDirsOnly` foi sobrescrito quando passamos explicitamente `options=QFileDialog.DontUseNativeDialog`. A correção consistiu em fazer a combinação das duas flags usando um bitwise OR (`|`): `options=QFileDialog.DontUseNativeDialog | QFileDialog.ShowDirsOnly`.

## 6. Diretório de Destino Não Salvo Entre Sessões
- **Problema**: O diretório escolhido pelo usuário para salvar os arquivos ("Destino da conversão") era redefinido para a pasta padrão do sistema (Ex: `~/Vídeos/Lyra`) toda vez que a aplicação era reiniciada.
- **Sintoma**: O usuário tinha que reconfigurar o diretório de destino a cada nova execução do software.
- **Fix (🔒)**: Implementação da classe `QSettings("Lyra", "Lyra-Qt")` para persistir o caminho e recuperá-lo no método de inicialização da UI de forma automática.

## 7. Falha Crítica do NVENC por Incompatibilidade de Drivers (BtbN)
- **Problema**: Inicialmente, os empacotadores (Flatpak e DEB) faziam o download forçado dos binários mestres pré-compilados do BtbN. Porém, devido ao BtbN embutir as versões mais recentes das bibliotecas da NVIDIA (API 13.1), o FFmpeg recusava-se a rodar o conversor NVENC em placas de vídeo com drivers minimamente desatualizados (Ex: série 610 ou 5xx).
- **Sintoma**: Ao usar a interface e apertar "Iniciar Conversão" com a aceleração NVIDIA H.264 ativa, o FFmpeg falhava com erros de inicialização silenciosa devido à divergência de versão do driver.
- **Fix (🔒)**: Substituído completamente o fornecedor. No pacote `.deb`, passamos a confiar no `ffmpeg` oficial estável dos repositórios nativos via dependência no APT (altamente testado pelas distribuidoras). No Windows, migramos para a ramificação `Essentials` do repositório `Gyan.dev`, que usa headers altamente retrocompatíveis. No Flatpak, passamos a compilar o FFmpeg nativamente a partir do código-fonte injetando cabeçalhos `n12.1.14.0` seguros.

## 8. Crash de Escalonamento NVENC (scale_cuda vs filter)
- **Problema**: Na tentativa de redimensionar o vídeo (Ex: baixar de 4K para 1080p), injetamos a flag nativa `-hwaccel_output_format cuda` combinada com a sintaxe `-vf scale_cuda`. Contudo, o filtro `scale_cuda` estava ausente nas compilações padrões de Linux e em compilações enxutas (Flatpak sem llvm). Ao recorrer ao `scale` (CPU), ocorria uma interrupção por hardware ("auto_scale_0" format unsupported format cuda).
- **Sintoma**: Ao escolher converter o tamanho do vídeo, ele iniciava e parava abruptamente.
- **Fix (🔒)**: O script Python `ffmpeg_engine.py` foi remodelado para aplicar roteamento dinâmico de frame. Se houver redimensionamento ativo (Ex: `vsize` diferente de Padrão), a engine intencionalmente suprime a flag `-hwaccel_output_format cuda`, forçando o FFmpeg a trazer o frame decodificado da GPU para a CPU, fazer o filtro matematicamente lá, e o próprio `h264_nvenc` empurra o resultado de volta para a GPU na fase final de encode.

## 9. Download da Web Falhando no Linux (Conflito yt-dlp APT x PIP)
- **Problema**: O pacote `.deb` criava um atalho Desktop apontando para o Python nativo do ambiente virtual (`venv`), mas sem exportar todo o `PATH`. Consequentemente, ao executar `QProcess("yt-dlp")`, o Lyra caía no fallback de localizar a versão depreciada do `yt-dlp` disponibilizada pelo sistema via APT, gerando falhas em bypass do YouTube. O Flatpak, curiosamente, funcionava porque seu Sandbox mascarava a versão global.
- **Sintoma**: O programa dava erro ao tentar buscar dados do vídeo no Debian/Ubuntu.
- **Fix (🔒)**: Implementação de detecção de ambiente real-time em `ytdlp_engine.py`: O Lyra intercepta `os.path.dirname(sys.executable)` e checa ativamente se o diretório host atual (o `venv` do Python) contém um binário `yt-dlp`. Se encontrar, força o bypass chamando ele com caminho absoluto em vez de delegar ao `PATH` do sistema.

## 10. Conflito de Processamento de Áudio (Volume vs Normalização e Preview Mudo)
- **Problema**: O motor de interface (`mpv_widget`) e o motor de renderização (`ffmpeg_engine`) aplicavam o filtro de aumento de volume de forma prematura na cadeia de eventos, antecedendo o compressor de alcance dinâmico (`dynaudnorm`). Além disso, o MPV recebia filtros proprietários do FFmpeg (como `arnndn` e `dynaudnorm`) diretamente em sua propriedade nativa de áudio, ignorando os filtros.
- **Sintoma**: O Slider de Volume parecia não fazer efeito prático se a caixa de "Normalizar Vozes" estivesse ativa, pois o compressor interpretava o ganho do usuário como ruído/explosão e esmagava o volume. Na aba "Sincronia", ao dar Play, as opções de limpeza de ruído não surtiam efeito audível em tempo real.
- **Fix (🔒)**: Ordem arquitetural estrita definida para áudio: RNNoise (Limpeza) -> DRC (Normalização) -> Volume (Ganho Final). No Player (`mpv_widget`), todos os filtros foram obrigatoriamente envelopados em uma única sintaxe acumulativa da ponte `lavfi=[...]` para que o libavfilter injetado do MPV atue corretamente.

## 11. Vazamento Oculto de Estados Residuais (State Leak de Presets)
- **Problema**: O seletor de "Carregar Preset" na interface não era intuitivo, e a função interna responsável por limpar a interface (`_reset_advanced_options`) estava varrendo apenas as abas de "Vídeo", "Áudio" e "Filtros". Consequentemente, sliders da aba "Imagem", temporizadores da aba "Corte" (`-ss` / `-to`) e milissegundos de correção da aba "Sincronia" sobreviviam à limpeza, injetando parâmetros alienígenas na conversão do próximo arquivo da fila (Ex: tentar converter um PNG com flags de `hevc_nvenc` vazadas ou cortes de tempo).
- **Sintoma**: FFmpeg abortava com o erro `Encoder not found` ao tentar salvar arquivos WebP de imagem ou vídeos sofriam cortes ou atrasos de áudio não solicitados porque herdavam os temporizadores do arquivo processado anteriormente.
- **Fix (🔒)**: Refatoração do design (UX): O índice 0 de presets foi renomeado de `Carregar Preset` para `"🟢 Padrão do Sistema (Automático)"` para comunicar a delegação ao FFmpeg. Um botão físico de Hard Reset (`🔄 Restaurar Padrões`) foi inserido na raiz do layout. Adicionalmente, a rotina `_reset_advanced_options` foi expandida em duas varreduras para alvejar os **25 campos** ocultos, limpando listas externas de legendas e de áudios secundários, checkboxes de vídeo (Corrigir Index, CRF, Somente Vídeo) e todos os `QComboBox`, `QSlider`, `QSpinBox` e `QTimeEdit` das abas de Corte, Sincronia e Imagem, zerando impiedosamente qualquer métrica não padrão.

## 12. Gatilho Fantasma de Eventos (PySide6 Signal Bypass)
- **Problema**: O botão de "Restaurar Padrões" dependia do mecanismo passivo do motor Qt: ele enviava o comando `setCurrentIndex(0)` para a Combobox de Presets, esperando que a combobox emitisse o sinal `currentIndexChanged`, que então invocaria a faxina total. No entanto, se o usuário modificasse abas manualmente sem selecionar um preset, o índice *já era* `0`. O motor do PySide6 otimizava isso como uma "não mudança", abortando a emissão do sinal.
- **Sintoma**: Clicar no botão "Restaurar Padrões" não produzia efeito algum caso o Preset já estivesse no "Padrão do Sistema".
- **Fix (🔒)**: A função anônima (`lambda`) do botão foi removida. Foi criado um método Bypass explícito (`_trigger_hard_reset`) que trava os sinais da combobox, injeta forçosamente o índice 0 na UI para manter a coerência visual, destrava a combobox e, finalmente, chama `_reset_advanced_options` diretamente com as próprias mãos. O Bypass desvincula a execução lógica do mecanismo frágil de "emissão por mudança" do Qt.

## 13. Armadilha do 2-Pass em Extensões Não-Vídeo (State Bleed)
- **Problema**: O gatilho principal de conversão (`start_conversion`) ativava o `pass_num = 1` baseando-se unicamente nas flags brutas da Interface ("Habilitar 2-Passos" checado e Codec = `libx264`). Ele não consultava o destino da conversão.
- **Sintoma**: Se o usuário tentasse converter uma Imagem (ex: `.webp`) ou Áudio (`.mp3`) mas deixasse as opções de 2-pass ativas na aba de vídeo, o FFmpeg tentava realizar uma codificação em duas fases em formatos que não geram logs temporários (`.log`). O processo abortava no meio com o erro `Input/output error` (pois o Passo 2 tentava ler um arquivo inexistente).
- **Fix (🔒)**: Foi introduzida a verificação estrita `is_video_format` na linha de frente do motor de processamento assíncrono. O `start_conversion` agora só permite engatilhar o particionamento em 2-passos se o Codec for elegível, a Caixa estiver checada **E** o arquivo de destino for comprovadamente um formato de Vídeo. Imagens e áudios com opções invasoras sofrem Bypass automático.

## 14. Falha de Auto-Seleção de Muxers de Imagens (Encoder Not Found)
- **Problema**: Após a blindagem do motor (`is_image`), as extensões de saída de imagem foram proibidas de usar codecs de vídeo da UI. Isso delegou ao FFmpeg a "Auto-Seleção" baseada na extensão final. Em alguns binários (como o do Flatpak), o default interno para `.webp` estava desabilitado, resultando em quebra imediata por falta de codec. Adicionalmente, forçar um encoder simples (`libwebp`) causaria a destruição de animações GIF para WebP.
- **Sintoma**: "Encoder not found" ao converter qualquer imagem para `.webp`.
- **Fix (🔒)**: A arquitetura de `is_image` foi refatorada. Em vez de depender do livre-arbítrio da compilação do FFmpeg do host, o aplicativo possui agora um **Dicionário Rígido de Codecs de Imagem**. Ele passa forçosamente o codec exato de acordo com a extensão (`mjpeg` para JPG, `libwebp_anim` para WEBP estáticos e animados, `png`, `gif`, `bmp`, `tiff`). O erro de dependência cega foi extirpado.

## 15. Áudio Mudo e Travamento do MPV no Sandbox (Flatpak)
- **Problema**: No ambiente Flatpak, o MPV Player iniciava mudo com o erro "Host is down" (sem permissões de socket de áudio) ou congelava inteiramente (Deadlock) na aba de Sincronia, tentando forçar aceleração por hardware (VA-API) ou contextos OpenGL puros sem sucesso.
- **Sintoma**: O reprodutor de pré-visualização crachava a interface inteira ao abrir ou não emitia som algum.
- **Fix (🔒)**: No manifesto YAML do Flatpak, foi inserida a permissão explícita `--filesystem=xdg-run/pipewire-0` para acesso ao áudio, e o código do player passou a declarar o fallback `ao=pulse`. O contexto de renderização do `mpv` foi estabilizado forçando `hwdec=no` e desacoplando a amarra do OpenGL puro em favor do renderizador XWayland flexível na sandbox.

## 16. Encerramento Fantasma pelo System Tray (App Zombie)
- **Problema**: O clique em "Sair" através do ícone da bandeja emitia o comando de finalização `QApplication.quit()`, o que engatilhava o `closeEvent` da janela. Porém, o `closeEvent` estava interceptando e cancelando o encerramento para apenas esconder a janela na bandeja, criando um loop morto infinito.
- **Sintoma**: A janela sumia, mas o processo `python3 main.py` continuava rodando secretamente no gerenciador de tarefas para sempre.
- **Fix (🔒)**: Injetada uma flag lógica `_force_quitting = True` antes de disparar o `quit()`. O `closeEvent` agora checa essa flag; se for verdadeira, ele faz o Bypass do cancelamento e permite que o evento de destruição (Accept) finalize o app limpamente.

## 17. Conflito Parental de Mensagens (Janela Surgindo Abruptamente)
- **Problema**: No Windows, ao gerar uma caixa de diálogo (`QMessageBox`) atrelada à Janela Principal (`parent=self`) durante o fechamento pelo Tray, o ambiente gráfico do SO automaticamente forçava a janela principal a se "desocultar" e reaparecer no centro da tela.
- **Sintoma**: Clicar com botão direito na bandeja e pedir para sair fazia o aplicativo dar um pulo assustador para o meio da tela.
- **Fix (🔒)**: O parentesco do `QMessageBox` na função de encerramento pelo tray foi desvinculado (`parent=None`), impedindo o sistema operacional de puxar a árvore hierárquica e forçar o *un-hide* da tela de fundo.

## 18. Interface Engessada em Arquivos Finalizados
- **Problema**: A fila de conversão aplicava o estado "Concluído" ou "Erro" de forma permanente a um item, exigindo que o usuário usasse os botões "Remover" e depois "Adicionar" se quisesse converter o mesmo vídeo novamente para outro formato.
- **Sintoma**: Tentar converter o mesmo vídeo duas vezes exigia intervenção braçal repetitiva do usuário.
- **Fix (🔒)**: Adicionada rotina na verificação de fila: antes de iniciar o loop, itens marcados na fila que possuam status `Concluído` ou `Erro` são automaticamente revertidos para o estado verde e neutro `Pronto`, permitindo re-conversões instantâneas.

## 19. Bug Crítico de Lógica Visual (Arquivos Existentes vs FFmpeg)
- **Problema**: A combobox de destino (Pular, Renomear, Sobrescrever) era apenas estética. No motor real de processamento, a flag `-y` (Overwrite) era passada incondicionalmente ao FFmpeg, esmagando arquivos de usuários sem dó e ignorando a escolha visual.
- **Sintoma**: Não importava o que o usuário escolhia, o arquivo original era destruído e o FFmpeg sempre sobrescrevia.
- **Fix (🔒)**: Implementada checagem via `os.path.exists()` na função `process_next_file`. A lógica de Pular (`continue` no loop de fila), Renomear (Loop iterativo gerando `arquivo_1.mp4`, `arquivo_2.mp4`) e Sobrescrever (manter `-y`) foi injetada no código *antes* de delegar a tarefa aos Motores de FFmpeg.
