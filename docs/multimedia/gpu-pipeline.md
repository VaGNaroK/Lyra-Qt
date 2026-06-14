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

## 3. Filtros e Fluxo de Memória
A filosofia original incentivava o uso do `scale_cuda` para redimensionamento. Porém, a compilação cruzada (ex: Flatpak) demonstrou forte quebra nesse filtro sem a presença massiva de bibliotecas LLVM. Portanto, a **nova diretriz arquitetural** determina:
- **Escalonamento (Resize)**: O uso de `scale_cuda` está DEPRECIADO. Todo redimensionamento deve utilizar o filtro universal `scale`.
- **Roteamento de Frames**: Para que o `scale` funcione, o frame precisa estar na RAM (CPU). Assim, a flag `-hwaccel_output_format cuda` DEVE ser ejetada da linha de comando dinamicamente sempre que houver manipulação das dimensões do vídeo.

## 4. Cuidados e Fallbacks (Incompatibilidade)
Se ocorrer filtragem pesada (como legendas embutidas, *cropping* nativo ou escalonamento via software):
- **Obrigatório**: Remover a restrição de frame formatado (`-hwaccel_output_format cuda`). Isso força a VRAM da GPU a entregar a imagem decodificada de volta para a RAM do host, fazer o filtro matematicamente lá, para então o encoder (`h264_nvenc`) enviar a imagem tratada de volta para a GPU na fase de compactação final.
