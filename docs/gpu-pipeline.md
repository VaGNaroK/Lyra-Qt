# Pipeline de GPU (Hardware Acceleration)

O Lyra-Qt tem como foco garantir o máximo de velocidade aproveitando a aceleração via hardware, com integração inicial muito forte para placas de vídeo NVIDIA (NVENC).

## 1. Ativação do Pipeline de Hardware
Quando o usuário seleciona um codec com suporte a hardware (como `h264_nvenc` ou `hevc_nvenc`), a `FFmpegEngine` deve automaticamente preparar o terreno para não apenas codificar, mas decodificar no hardware, se possível.
- Comandos injetados: `-hwaccel cuda` e `-hwaccel_output_format cuda`.

## 2. Ajustes de Qualidade NVENC (CQ)
Codificação via NVENC possui particularidades para manter qualidade equivalente a CPU. A pipeline do Lyra-Qt força o uso do modo Constant Quality (CQ) aprimorado:
- Injeção de presets de alta qualidade: `-preset p7`, `-profile:v high`, `-tune hq`, `-rc vbr`.
- Parâmetros AQ avançados: `-spatial-aq 1`, `-temporal-aq 1`.
- Aprimoramentos de ref: `-rc-lookahead 32`, `-b_ref_mode 2`.

## 3. Filtros Assistidos por Hardware (CUDA)
Para maximizar a eficiência, quando a pipeline de GPU está ativa, certos filtros do FFmpeg devem utilizar suas contrapartes otimizadas de CUDA para evitar tráfego desnecessário de frames entre VRAM e RAM:
- **Escalonamento**: Se houver redimensionamento de vídeo, substitua o filtro `scale` comum por `scale_cuda`. Exigência: cálculos precisos de altura para evitar alturas ímpares.
- **Desentrelaçamento**: Substitua o `yadif` comum por `yadif_cuda`.

## 4. Cuidados e Fallbacks
Se opções muito complexas (como legendas embutidas com `-vf subtitles` em hardsub) ou filtros pesados de CPU não-compatíveis com frames `cuda` entrarem no jogo, pode ser necessário remover `-hwaccel_output_format cuda` para forçar a transferência à memória da CPU, ou informar ao usuário incompatibilidades se surgirem no futuro.
