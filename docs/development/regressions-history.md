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
