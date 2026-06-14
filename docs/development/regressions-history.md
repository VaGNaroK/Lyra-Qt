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
