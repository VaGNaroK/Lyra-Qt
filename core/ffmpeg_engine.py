import os
import re
import sys
import time
import subprocess
import tempfile
import json
from PySide6.QtCore import QObject, Signal, QProcess
from core.utils import (
    IMAGE_EXTENSIONS, AUDIO_EXTENSIONS, SUBTITLE_EXTENSIONS,
    format_time_hms as _format_time_util,
    parse_bitrate_to_kbps as _parse_bitrate_util,
)

class FFmpegEngine(QObject):
    """
    Motor central assíncrono para processamento de conversões multimídia.
    Usa QProcess para invocar e gerenciar o binário do FFmpeg em background, 
    parseando o progresso e o log de saída para atualizar a interface gráfica.
    """
    progress_updated = Signal(int, int, str, str, str, str)
    log_updated = Signal(str)
    process_finished = Signal(int, int, bool)

    def __init__(self, resource_dir=None):
        """
        Inicializa o motor configurando o estado das conversões e resolvendo os binários.
        
        Args:
            resource_dir (str, optional): Caminho do diretório de recursos (assets).
        """
        super().__init__()
        self.resource_dir = resource_dir
        self.process = None
        self.conversion_start_time = 0.0
        self.current_duration = 0.0
        self.current_row = -1

        self.current_pass = 0
        self.current_input = ""
        self.current_output = ""
        self.current_options = {}

        self.ffmpeg_bin = "ffmpeg"
        self.ffprobe_bin = "ffprobe"

        if self.resource_dir:
            ext = ".exe" if sys.platform == "win32" else ""
            local_ffmpeg = os.path.join(self.resource_dir, "assets", "bin", f"ffmpeg{ext}")
            local_ffprobe = os.path.join(self.resource_dir, "assets", "bin", f"ffprobe{ext}")
            
            if os.path.isfile(local_ffmpeg):
                self.ffmpeg_bin = local_ffmpeg
            if os.path.isfile(local_ffprobe):
                self.ffprobe_bin = local_ffprobe

        # Detecta o melhor filtro de escala GPU disponível e cacheia para evitar
        # subprocess repetitivo durante a fila de conversões.
        self._cuda_scale_filter = self._detect_cuda_scale_filter()

    def _detect_cuda_scale_filter(self) -> str:
        """
        Detecta o melhor filtro de escala na GPU disponível em runtime.
        Executa `ffmpeg -filters` uma única vez na inicialização e cacheia o resultado.

        Hierarquia de preferência:
          1. scale_npp  — NVIDIA Performance Primitives, qualidade Super Sampling (BtbN)
          2. scale_cuda — CUDA nativo, Lanczos na VRAM (driver ≥ 396)
          3. cpu        — fallback: scale lavfi (comportamento original)

        Returns:
            str: 'scale_npp' | 'scale_cuda' | 'cpu'
        """
        try:
            result = subprocess.run(
                [self.ffmpeg_bin, "-hide_banner", "-filters"],
                capture_output=True, text=True, timeout=5,
                startupinfo=self._get_startupinfo()
            )
            output = result.stdout + result.stderr
            if "scale_npp" in output:
                return "scale_npp"
            if "scale_cuda" in output:
                return "scale_cuda"
        except Exception:
            pass
        return "cpu"

    def format_time(self, seconds) -> str:
        """
        Converte uma quantidade de segundos brutos para o formato legível HH:MM:SS.
        Delega para core.utils.format_time_hms para evitar duplicação.
        O formato HH:MM:SS com 3 grupos é o correto para exibição nos logs de progresso.
        """
        return _format_time_util(seconds)

    def _get_startupinfo(self):
        """
        Retorna um STARTUPINFO configurado para suprimir janelas de console no Windows.
        Retorna None em Linux/macOS.
        """
        if os.name == 'nt':
            info = subprocess.STARTUPINFO()
            info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            return info
        return None

    def get_media_duration(self, file_path):
        """
        Executa ffprobe para obter a duração total do arquivo multimídia em segundos.
        
        Returns:
            float: Duração em segundos, ou 0.0 se falhar.
        """
        try:
            cmd = [self.ffprobe_bin, "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", file_path]
            startupinfo = self._get_startupinfo()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, startupinfo=startupinfo)
            val = result.stdout.strip()
            return float(val) if val and val != 'N/A' else 0.0
        except Exception:
            return 0.0
            
    def get_video_resolution(self, file_path):
        """
        Executa ffprobe para identificar a resolução nativa do vídeo.
        
        Returns:
            tuple: (largura, altura) ou (None, None) em caso de erro.
        """
        try:
            cmd = [self.ffprobe_bin, "-v", "error", "-select_streams", "v:0",
                   "-show_entries", "stream=width,height",
                   "-of", "csv=p=0:s=x", file_path]
            startupinfo = self._get_startupinfo()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, startupinfo=startupinfo)
            res = result.stdout.strip().split('x')
            if len(res) == 2:
                return int(res[0]), int(res[1])
        except Exception:
            pass
        return 0, 0
    
    def get_human_media_info(self, file_path):
        """
        Extrai metadados variados do arquivo (streams de vídeo/áudio, codec, resolução)
        e os formata de maneira rica com emojis para exibição na interface gráfica.
        
        Returns:
            str: Texto formatado detalhando as informações da mídia.
        """
        if not os.path.exists(file_path):
            return "❌ Arquivo não encontrado."
        try:
            cmd = [self.ffprobe_bin, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path]
            startupinfo = self._get_startupinfo()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, startupinfo=startupinfo)
            if result.returncode != 0:
                return "❌ Erro ao ler informações da mídia."

            data = json.loads(result.stdout)
            out = []
            
            ext_destino = os.path.splitext(file_path)[1].lower().replace(".", "")
            is_image = ext_destino in IMAGE_EXTENSIONS

            out.append("📄 INFORMAÇÕES GERAIS")
            format_info = data.get("format", {})
            out.append(f"Arquivo: {os.path.basename(file_path)}")
            
            # fallback seguro de sistema se o ffprobe não trouxer size
            try:
                size_bytes = os.path.getsize(file_path)
            except Exception:
                size_bytes = int(format_info.get("size", 0))
                
            if size_bytes > 0 and size_bytes < 1024 * 1024:
                size_kb = size_bytes / 1024
                out.append(f"Tamanho: {size_kb:.2f} KB")
            else:
                size_mb = size_bytes / (1024 * 1024)
                out.append(f"Tamanho: {size_mb:.2f} MB")
            
            fmt_name = format_info.get("format_name", "Desconhecido").split(",")[0]
            out.append(f"Formato: {fmt_name}")
            
            if not is_image:
                duration = float(format_info.get("duration", 0))
                out.append(f"Duração: {self.format_time(duration)}")
                if "bit_rate" in format_info:
                    br_kbps = int(format_info.get("bit_rate", 0)) / 1000
                    out.append(f"Bitrate Total: {br_kbps:.0f} kbps")

            out.append("")
            
            streams = data.get("streams", [])
            for i, stream in enumerate(streams):
                codec_type = stream.get("codec_type", "unknown").upper()
                codec_name = stream.get("codec_name", "Desconhecido").upper()
                
                if codec_type == "VIDEO":
                    if is_image:
                        out.append(f"🖼️ IMAGEM (Faixa {i})")
                        out.append(f"Formato: {codec_name}")
                        out.append(f"Resolução: {stream.get('width', '?')}x{stream.get('height', '?')}")
                        
                        pix_fmt = stream.get("pix_fmt", "").lower()
                        if pix_fmt:
                            if "rgba" in pix_fmt or "bgra" in pix_fmt:
                                space = "RGBA (Com Transparência / Alpha)"
                            elif "rgb" in pix_fmt or "bgr" in pix_fmt:
                                space = "RGB (Cores Digitais)"
                            elif "cmyk" in pix_fmt:
                                space = "CMYK (Padrão de Impressão Gráfica)"
                            elif "gray" in pix_fmt or "mono" in pix_fmt:
                                space = "Escala de Cinza (Monocromático)"
                            elif "yuv" in pix_fmt:
                                space = "YUV / YCbCr (Padrão Fotográfico)"
                            else:
                                space = pix_fmt.upper()
                            out.append(f"Espaço de Cor: {space}")
                        
                        bits = stream.get("bits_per_raw_sample")
                        if bits:
                            out.append(f"Profundidade: {bits}-bit")
                            
                        profile = stream.get("profile")
                        if profile and profile.lower() != "unknown":
                            out.append(f"Perfil: {profile}")
                    else:
                        out.append(f"🎬 VÍDEO (Faixa {i})")
                        out.append(f"Codec: {codec_name}")
                        out.append(f"Resolução: {stream.get('width', '?')}x{stream.get('height', '?')}")
                        if "avg_frame_rate" in stream:
                            fr = stream["avg_frame_rate"]
                            if "/" in fr:
                                num, den = fr.split("/")
                                if den != "0":
                                    fps = float(num)/float(den)
                                    out.append(f"Framerate: {fps:.2f} FPS")
                        
                        bit_rate = stream.get("bit_rate") or stream.get("max_bit_rate")
                        if not bit_rate:
                            tags = stream.get("tags", {})
                            bps_keys = [k for k in tags.keys() if "BPS" in k.upper()]
                            if bps_keys:
                                bit_rate = tags[bps_keys[0]]

                        if bit_rate and str(bit_rate).isdigit():
                            br_mbps = int(bit_rate) / 1000000
                            out.append(f"Maximum bit rate: {br_mbps:.1f} Mb/s")
                            
                        dar = stream.get("display_aspect_ratio")
                        if dar:
                            out.append(f"Proporção tela: {dar}")
                    
                elif codec_type == "AUDIO":
                    out.append(f"🎵 ÁUDIO (Faixa {i})")
                    out.append(f"Formato: {codec_name.lower()}")
                    out.append(f"Codec: {codec_name}")
                    out.append(f"Canais: {stream.get('channels', '?')}")
                    out.append(f"Frequência: {stream.get('sample_rate', '?')} Hz")
                    tags = stream.get("tags", {})
                    if "language" in tags:
                        out.append(f"Idioma: {tags.get('language', 'ND').upper()}")
                        
                elif codec_type == "SUBTITLE":
                    out.append(f"📝 LEGENDA (Faixa {i})")
                    out.append(f"Formato: {codec_name}")
                    tags = stream.get("tags", {})
                    if "language" in tags:
                        out.append(f"Idioma: {tags.get('language', 'ND').upper()}")
                out.append("")
            return "\n".join(out)
        except Exception as e:
            return f"❌ Erro ao analisar mídia: {str(e)}"
    
    def get_media_specs(self, file_path):
        """
        Extrai configurações exatas de um arquivo de mídia para clonagem (smart analysis).
        
        Returns:
            dict: Dicionário contendo vcodec, vbitrate, vsize, vfps, acodec, abitrate, afreq, achannels.
        """
        specs = {
            "vcodec": "default",
            "vbitrate": "default",
            "vsize": "default",
            "vfps": "default",
            "acodec": "default",
            "abitrate": "default",
            "afreq": "default",
            "achannels": "default"
        }
        if not os.path.exists(file_path):
            return specs
            
        try:
            cmd = [self.ffprobe_bin, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path]
            startupinfo = self._get_startupinfo()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, startupinfo=startupinfo)
            if result.returncode != 0:
                return specs

            data = json.loads(result.stdout)
            format_info = data.get("format", {})
            streams = data.get("streams", [])
            
            for stream in streams:
                codec_type = stream.get("codec_type", "").lower()
                codec_name = stream.get("codec_name", "").lower()
                
                if codec_type == "video":
                    # Codec Mapping for NVENC
                    if "h264" in codec_name:
                        specs["vcodec"] = "libx264"
                    elif "hevc" in codec_name or "h265" in codec_name:
                        specs["vcodec"] = "libx265"
                    elif "vp9" in codec_name:
                        specs["vcodec"] = "libvpx-vp9"
                    elif "vp8" in codec_name:
                        specs["vcodec"] = "libvpx-vp8"
                    else:
                        specs["vcodec"] = "libx264"  # fallback
                    
                    # Resolution
                    w, h = stream.get("width"), stream.get("height")
                    if w and h:
                        specs["vsize"] = f"{w}x{h}"
                        
                    # FPS
                    fr = stream.get("avg_frame_rate", "0/0")
                    if "/" in fr:
                        num, den = fr.split("/")
                        if den != "0":
                            fps = round(float(num) / float(den), 3)
                            # Normaliza framerates comuns
                            if fps in [23.976, 24, 25, 29.97, 30, 50, 59.94, 60]:
                                specs["vfps"] = str(fps).replace(".0", "")
                            else:
                                specs["vfps"] = str(fps).replace(".0", "")

                    # Video Bitrate
                    bit_rate = stream.get("bit_rate") or stream.get("max_bit_rate")
                    if not bit_rate:
                        tags = stream.get("tags", {})
                        bps_keys = [k for k in tags.keys() if "BPS" in k.upper()]
                        if bps_keys:
                            bit_rate = tags[bps_keys[0]]
                    if not bit_rate:
                        # Fallback to general format bitrate if stream lacks it
                        bit_rate = format_info.get("bit_rate")
                    
                    if bit_rate and str(bit_rate).isdigit():
                        kbps = int(bit_rate) // 1000
                        specs["vbitrate"] = f"{kbps} kbps"

                elif codec_type == "audio":
                    # We only care about the first audio stream for cloning
                    if specs["acodec"] == "default":
                        # Codec Mapping
                        if "aac" in codec_name: specs["acodec"] = "aac"
                        elif "mp3" in codec_name: specs["acodec"] = "libmp3lame"
                        elif "vorbis" in codec_name: specs["acodec"] = "libvorbis"
                        elif "opus" in codec_name: specs["acodec"] = "libopus"
                        
                        # Audio Bitrate
                        bit_rate = stream.get("bit_rate")
                        if not bit_rate:
                            tags = stream.get("tags", {})
                            bps_keys = [k for k in tags.keys() if "BPS" in k.upper()]
                            if bps_keys: bit_rate = tags[bps_keys[0]]
                        if bit_rate and str(bit_rate).isdigit():
                            kbps = int(bit_rate) // 1000
                            specs["abitrate"] = f"{kbps} kbps"
                            
                        # Audio Sample Rate (Freq)
                        freq = stream.get("sample_rate")
                        if freq:
                            specs["afreq"] = f"{freq} Hz"
                            
                        # Channels
                        channels = stream.get("channels")
                        if channels:
                            if channels == 1: specs["achannels"] = "1 (Mono)"
                            elif channels == 2: specs["achannels"] = "2 (Stereo)"
                            elif channels == 6: specs["achannels"] = "6 (5.1)"

            return specs
        except Exception:
            return specs

    
    def get_audio_tracks(self, file_path):
        """
        Lista todas as faixas de áudio disponíveis dentro de um arquivo multimídia.
        
        Returns:
            list: Lista contendo dicionários com 'index' e 'label' de cada faixa.
        """
        if not os.path.exists(file_path):
            return []
        try:
            cmd = [self.ffprobe_bin, "-v", "quiet", "-print_format", "json", "-show_streams", "-select_streams", "a", file_path]
            startupinfo = self._get_startupinfo()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, startupinfo=startupinfo)
            data = json.loads(result.stdout)
            tracks = []
            for idx, stream in enumerate(data.get("streams", [])):
                codec = stream.get("codec_name", "ND").upper()
                lang = stream.get("tags", {}).get("language", "ND").upper()
                channels = stream.get("channels", "?")
                tracks.append((idx, f"Faixa {idx+1} - {codec} ({channels}ch, {lang})"))
            return tracks
        except Exception:
            return []

    def get_subtitle_tracks(self, file_path):
        """
        Lista todas as faixas de legenda disponíveis dentro de um arquivo multimídia.
        
        Returns:
            list: Lista contendo dicionários/tuplas com 'index' (global) e 'label' de cada faixa.
        """
        if not os.path.exists(file_path):
            return []
        try:
            cmd = [self.ffprobe_bin, "-v", "quiet", "-print_format", "json", "-show_streams", "-select_streams", "s", file_path]
            startupinfo = self._get_startupinfo()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, startupinfo=startupinfo)
            data = json.loads(result.stdout)
            tracks = []
            for idx, stream in enumerate(data.get("streams", [])):
                lang = stream.get("tags", {}).get("language", "ND").upper()
                tracks.append((idx, f"Faixa {idx+1} - Legenda ({lang})"))
            return tracks
        except Exception:
            return []
    
    def detect_crop(self, file_path):
        """
        Executa um filtro avançado (cropdetect) no FFprobe para analisar barras pretas
        na imagem/vídeo. Retorna coordenadas exatas para cropar o arquivo.
        
        Returns:
            dict: (top, bottom, left, right) em pixels para realizar o crop seguro.
        """
        if not os.path.exists(file_path):
            return None
        orig_w, orig_h = self.get_video_resolution(file_path)
        if orig_w == 0 or orig_h == 0:
            return None
        dur = self.get_media_duration(file_path)
        ss_val = "00:00:15" if dur > 20 else "00:00:00"
        cmd = [self.ffmpeg_bin, "-hide_banner", "-ss", ss_val, "-i", file_path, "-t", "2", "-vf", "cropdetect=24:16:0", "-f", "null", "-"]
        startupinfo = self._get_startupinfo()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, startupinfo=startupinfo)
            output = result.stderr
            matches = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", output)
            if matches:
                cw, ch, cx, cy = map(int, matches[-1])
                t = cy
                b = orig_h - (cy + ch)
                l = cx
                r = orig_w - (cx + cw)
                return {"t": max(0, t), "b": max(0, b), "l": max(0, l), "r": max(0, r)}
        except Exception:
            pass
        return None

    def parse_bitrate_to_kbps(self, value):
        """
        Converte strings de bitrate (ex: '2M', '500k') para valores float em kbps.
        Delega para core.utils.parse_bitrate_to_kbps para evitar duplicação.
        """
        return _parse_bitrate_util(value)

    def is_video_format(self, output_file) -> bool:
        """
        Verifica se a extensão final é um formato de vídeo genuíno
        (exclui imagens, áudios e legendas). Usa constantes de core.utils.
        """
        ext = os.path.splitext(output_file)[1].lower().replace(".", "")
        return ext not in (IMAGE_EXTENSIONS | AUDIO_EXTENSIONS | SUBTITLE_EXTENSIONS)

    def start_conversion(self, row, input_file, output_file, duration, options):
        """
        Configura e inicia a conversão de forma assíncrona. Se necessário 2 passos (ex: AV1 pass 1),
        iniciará a Pass 1 e delegará a Pass 2 ao terminar.
        
        Args:
            row (int): A linha da tabela na GUI correspondente a este arquivo.
            input_file (str): Caminho de origem.
            output_file (str): Caminho de destino.
            duration (float): Duração total para cálculo de progresso.
            options (dict): Opções de codificação geradas na interface gráfica.
        """
        self.current_row = row
        self.current_duration = duration
        self.conversion_start_time = time.time()
        self.current_input = input_file
        self.current_output = output_file
        self.current_options = options

        vcodec = options.get("vcodec", "default")
        if vcodec == "h.265 nvenc":
            vcodec = "hevc_nvenc"

        if options.get("two_pass") and vcodec in ["libx264", "libx265"] and self.is_video_format(output_file):
            self.current_pass = 1
            log_prefix = os.path.join(tempfile.gettempdir(), f"lyra_passlog_{row}_{int(time.time())}")
            self.current_options["passlog_prefix"] = log_prefix
        else:
            self.current_pass = 0

        cmd = self.build_ffmpeg_command(input_file, output_file, self.current_options, pass_num=self.current_pass)

        if self.current_pass == 1:
            self.log_updated.emit(f"\n{'='*40}\nIniciando Passo 1 da Codificação em 2 Passos: {os.path.basename(input_file)}\nLogs temporários em: {self.current_options.get('passlog_prefix')}\nComando: {' '.join(cmd)}\n{'='*40}\n")
        else:
            self.log_updated.emit(f"\n{'='*40}\nProcessando: {os.path.basename(input_file)}\nComando: {' '.join(cmd)}\n{'='*40}\n")

        self.process = QProcess(self)
        self.process.setProgram(cmd[0])
        self.process.setArguments(cmd[1:])
        self.process.readyReadStandardError.connect(self.read_ffmpeg_output)
        self.process.finished.connect(self.ffmpeg_process_finished)
        self.process.start()

    def ffmpeg_process_finished(self, exitCode, exitStatus):
        """
        Gerencia o fim da execução do FFmpeg. Se for uma conversão de 2 passos,
        inicia o Passo 2 ao finalizar o Passo 1. Caso contrário, emite sinal de conclusão para a GUI.
        """
        if self.current_pass == 1 and exitCode == 0:
            self.current_pass = 2
            cmd = self.build_ffmpeg_command(self.current_input, self.current_output, self.current_options, pass_num=2)
            self.log_updated.emit(f"\n{'='*40}\nIniciando Passo 2 da Codificação em 2 Passos...\nComando: {' '.join(cmd)}\n{'='*40}\n")
            self.process = QProcess(self)
            self.process.setProgram(cmd[0])
            self.process.setArguments(cmd[1:])
            self.process.readyReadStandardError.connect(self.read_ffmpeg_output)
            self.process.finished.connect(self.ffmpeg_process_finished)
            self.process.start()
        else:
            self.process_finished.emit(self.current_row, exitCode, False)

    def build_ffmpeg_command(self, input_file, output_file, options, pass_num=0):
        """
        Gera a linha de comando exata para ser executada pelo binário do FFmpeg.
        Resolve hardware acceleration, codecs, mapeamento de faixas, filtros de vídeo/áudio e afins.
        
        Returns:
            list: Array contendo o binário do ffmpeg seguido por todas as flags formatadas.
        """
        # ✅ FIX: Trabalhar sempre com cópia para evitar mutação do snapshot da fila de lote
        options = dict(options)
        # 1. Base Configuration
        ffmpeg_bin = options.get("ffmpeg_path", "ffmpeg")
        cmd = [ffmpeg_bin, "-y", "-hide_banner"]

        ext_destino = os.path.splitext(output_file)[1].lower().replace(".", "")
        is_image = ext_destino in IMAGE_EXTENSIONS
        is_audio_only = ext_destino in AUDIO_EXTENSIONS
        is_subtitle_only = ext_destino in SUBTITLE_EXTENSIONS

        if is_subtitle_only:
            input_ext = os.path.splitext(input_file)[1].lower().replace(".", "")
            if input_ext in ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp", "yuv", "mp3", "ogg", "wav", "aac", "flac", "wma", "ac3", "opus", "m4a"]:
                self.log_updated.emit(f"⚠️ Aviso de Blindagem: O arquivo original '{os.path.basename(input_file)}' é de uma mídia ({input_ext.upper()}) que nativamente não suporta legendas embutidas. A extração irá falhar.\n")
                
            # Configuração otimizada para extração limpa de legenda
            sub_track = options.get("extract_sub_track", 0)
            cmd.extend(["-i", input_file])
            cmd.extend(["-vn", "-an"]) # Desativa vídeo e áudio
            cmd.extend(["-map", f"0:s:{sub_track}?"]) # Seleciona a faixa específica
            cmd.extend(["-c:s", "srt" if ext_destino == "srt" else "copy"])
            extra = options.get("extra_args", "")
            if extra: cmd.extend(extra.split(" "))
            cmd.append(output_file)
            return cmd

        if ext_destino == "ogg" and options.get("acodec") == "libmp3lame":
            options["acodec"] = "libvorbis"
            self.log_updated.emit("⚠️ Aviso de Blindagem: O formato OGG não suporta o codec MP3 (libmp3lame). Alterado para Vorbis.\n")

        vcodec = options.get("vcodec", "default")
        if vcodec == "h.265 nvenc": vcodec = "hevc_nvenc"
        if vcodec == "libvpx-vp8": vcodec = "libvpx"
        
        if ext_destino in ["mp4", "avi"]:
            if vcodec in ["libvpx-vp9", "libvpx"]:
                vcodec = "default"
                self.log_updated.emit(f"⚠️ Aviso de Blindagem: O formato {ext_destino.upper()} não é compatível com o codec VP8/VP9. Alterado para padrão (H.264).\n")
            if options.get("acodec") == "libopus":
                options["acodec"] = "default"
                self.log_updated.emit(f"⚠️ Aviso de Blindagem: O formato {ext_destino.upper()} não suporta perfeitamente o codec OPUS. Alterado para padrão (AAC).\n")

        if not is_image and not is_audio_only and "nvenc" in vcodec:
            cmd.extend(["-hwaccel", "cuda"])
            # ✅ FIX: Sempre mantém hwaccel_output_format cuda quando há filtro GPU disponível.
            # Antes era desativado quando havia resize (vsize != default), forçando um
            # round-trip GPU → CPU → CPU-scale → GPU por cada frame.
            # scale_cuda/scale_npp operam diretamente na VRAM sem nenhuma cópia PCIe.
            # O flag é omitido apenas no fallback CPU (filter == 'cpu') para não
            # quebrar o pipeline quando watermark ou outros filtros lavfi estão ativos.
            has_watermark = bool(
                options.get("watermark", {}).get("enabled")
                and options.get("watermark", {}).get("image_path")
                and os.path.exists(options["watermark"]["image_path"])
            )
            if self._cuda_scale_filter != "cpu" and not has_watermark:
                cmd.extend(["-hwaccel_output_format", "cuda"])

        # 1.5 Cortes Temporais (Trimming)
        trim_enabled = options.get("trim_enabled", False)
        if trim_enabled:
            trim_start = options.get("trim_start", "00:00:00.000")
            trim_end = options.get("trim_end", "00:00:00.000")
            if trim_start != "00:00:00.000":
                cmd.extend(["-ss", trim_start])
            if trim_end != "00:00:00.000":
                cmd.extend(["-to", trim_end])

        # 2. Input File and Subtitles
        cmd.extend(["-i", input_file])
        vf_filters = []
        af_filters = []

        cover_path = options.get("metadata", {}).get("cover_path", "")
        has_cover = is_audio_only and cover_path and os.path.isfile(cover_path)
        if has_cover:
            cmd.extend(["-i", cover_path])

        sub_paths = options.get("sub_paths", [])
        audio_paths = options.get("audio_paths", [])
        sub_mode = options.get("sub_mode", 0)
        
        valid_audios = [p for p in audio_paths if os.path.isfile(p)]
        valid_subs = [p for p in sub_paths if os.path.isfile(p)]
        
        softsubs_added = 0

        if not is_image and not is_audio_only:
            # Inject external audios
            for audio in valid_audios:
                cmd.extend(["-i", audio])
            
            # Inject external subs
            if sub_mode == 0: # Softsub
                for sub in valid_subs:
                    cmd.extend(["-i", sub])
                    softsubs_added += 1
            elif sub_mode == 1 and valid_subs: # Hardsub
                escaped_sub = (valid_subs[0].replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'"))
                vf_filters.append(f"subtitles='{escaped_sub}'")

        # 3. Mapeamento (-map)
        audio_track = options.get("audio_track", -1)
        
        # 3.1. Vídeo Principal (Sempre o vídeo principal, ignorando capas/attached_pics)
        if not is_audio_only:
            cmd.extend(["-map", "0:v:0?"])
            
        # 3.2. Áudio Original
        if not is_image:
            if options.get("all_tracks"):
                cmd.extend(["-map", "0:a?"])
            elif audio_track != -1:
                cmd.extend(["-map", f"0:a:{audio_track}?"])
            else:
                cmd.extend(["-map", "0:a:0?"])
            
        # 3.3. Legendas Originais
        if not is_audio_only and not is_image:
            cmd.extend(["-map", "0:s?"]) # Preserva sempre as legendas originais
            
            # Remove faixas marcadas (Mapeamento Negativo)
            remove_tracks = options.get("remove_sub_tracks", [])
            for track in remove_tracks:
                cmd.extend(["-map", f"-0:s:{track}?"])

        # 3.4. Áudios Externos mapeados sequencialmente
        for i in range(len(valid_audios)):
            cmd.extend(["-map", f"{1 + i}:a:0?"])
            
        # 3.5. Legendas Externas mapeadas sequencialmente
        if softsubs_added > 0:
            start_sub_idx = 1 + len(valid_audios)
            for i in range(softsubs_added):
                cmd.extend(["-map", f"{start_sub_idx + i}:0?"])
            
        # Força o codec de legenda compatível com o contêiner
        if not is_audio_only and not is_image:
            cmd.extend(["-c:s", "mov_text" if ext_destino == "mp4" else ("copy" if ext_destino == "mkv" else ("webvtt" if ext_destino == "webm" else "srt"))])

        # 4. Audio Filters
        audio_offset_ms = options.get("audio_offset_ms", 0)
        if audio_offset_ms != 0 and options.get("acodec", "default") == "copy":
            options["acodec"] = "aac" if ext_destino == "mp4" else ("libopus" if ext_destino == "webm" else "default")
            self.log_updated.emit("⚠️ Sincronia de Áudio ativada: O áudio não pode ser 'copy'. Alterado para recodificação.\n")
            
        noise_reduction = options.get("noise_reduction", False)
        if noise_reduction and options.get("acodec", "default") == "copy":
            options["acodec"] = "aac" if ext_destino == "mp4" else ("libopus" if ext_destino == "webm" else "default")
            self.log_updated.emit("⚠️ Redução de Ruído ativada: O áudio não pode ser 'copy'. Alterado para recodificação.\n")
            
        speed_opt = options.get("speed", {"value": 1.0, "preserve_pitch": True})
        speed_val = speed_opt.get("value", 1.0)
        speed_preserve = speed_opt.get("preserve_pitch", True)
        
        if speed_val != 1.0 and options.get("acodec", "default") == "copy":
            options["acodec"] = "aac" if ext_destino == "mp4" else ("libopus" if ext_destino == "webm" else "default")
            self.log_updated.emit("⚠️ Velocidade alterada: O áudio não pode ser 'copy'. Alterado para recodificação.\n")
            
        is_audio_copy = (options.get("acodec", "default") == "copy")
        vol = options.get("volume", 100)
        
        if audio_offset_ms != 0 and not is_audio_copy:
            if audio_offset_ms > 0:
                af_filters.append(f"adelay=delays={int(audio_offset_ms)}:all=1")
            else:
                sec = abs(audio_offset_ms) / 1000.0
                af_filters.append(f"atrim=start={sec},asetpts=PTS-STARTPTS")
        
        if noise_reduction and not is_audio_copy:
            model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "models", "cb.rnnn")
            if os.path.exists(model_path):
                escaped_model_path = model_path.replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
                af_filters.append(f"arnndn=m='{escaped_model_path}'")
            else:
                self.log_updated.emit("❌ Erro: Arquivo de modelo de ruído 'cb.rnnn' não encontrado na raiz. O filtro foi ignorado.\n")

        if options.get("audio_drc") and not is_audio_copy:
            af_filters.append("pan=stereo|FL=0.5*FC+0.707*FL+0.707*BL+0.5*LFE|FR=0.5*FC+0.707*FR+0.707*BR+0.5*LFE")
            af_filters.append("loudnorm=I=-16:LRA=11:TP=-1.5")
            
        if vol != 100 and not is_audio_copy:
            af_filters.append(f"volume={vol/100.0}")

        # 5. Video Filters
        if options.get("deinterlace"):
            vf_filters.append("yadif_cuda" if "nvenc" in vcodec else "yadif")

        rotate = options.get("rotate", "normal")
        if rotate in ("90° Horário", "90_cw", "90_clockwise", "90° Clockwise"): vf_filters.append("transpose=1")
        elif rotate in ("90° Anti-horário", "90_ccw", "90_counterclockwise", "90° Counter-Clockwise", "90° Antihorario", "90° Anti-horaire"): vf_filters.append("transpose=2")
        elif rotate in ("180°", "180"): vf_filters.append("transpose=2,transpose=2")
        elif rotate in ("Espelhar Horizontal", "hflip", "horizontal_flip", "Horizontal Flip", "Voltear Horizontal", "Miroir horizontal", "Horizontal spiegeln", "Rifletti Orizzontale", "Отразить по горизонтали", "水平翻转", "左右反転"): vf_filters.append("hflip")
        elif rotate in ("Espelhar Vertical", "vflip", "vertical_flip", "Vertical Flip", "Voltear Vertical", "Miroir vertical", "Vertikal spiegeln", "Rifletti Verticale", "Отразить по вертикали", "垂直翻转", "上下反転"): vf_filters.append("vflip")

        crop = options.get("crop", {})
        if crop.get("enabled"):
            t, b, l, r = crop["t"], crop["b"], crop["l"], crop["r"]
            vf_filters.append(f"crop=iw-{l}-{r}:ih-{t}-{b}:{l}:{t}")

        pad = options.get("pad", {})
        if pad.get("enabled"):
            t, b, l, r = pad["t"], pad["b"], pad["l"], pad["r"]
            vf_filters.append(f"pad=iw+{l}+{r}:ih+{t}+{b}:{l}:{t}:black")

        fade_dur = options.get("fade_dur", 0)
        fade_pos = options.get("fade_pos", "none")
        fade_type = options.get("fade_type", "both")
        if fade_dur > 0 and fade_pos not in ("Nenhum", "none", "None", "Ninguno", "Aucun", "Keine", "Nessuna", "Нет", "无", "なし", ""):
            do_video = fade_type in ("Vídeo e Áudio", "Somente Vídeo", "both", "video", "Video and Audio", "Video Only", "Vídeo y Audio", "Solo Vídeo", "Vidéo et Audio", "Vidéo seule", "Video und Audio", "Nur Video", "Video e Audio", "Solo Video", "Видео и аудио", "Только видео", "视频与音频", "仅视频", "動画と音声", "動画のみ")
            do_audio = (fade_type in ("Vídeo e Áudio", "Somente Áudio", "both", "audio", "Video and Audio", "Audio Only", "Vídeo y Audio", "Solo Audio", "Vidéo et Audio", "Audio seul", "Video und Audio", "Nur Audio", "Video e Audio", "Solo Audio", "Видео и аудио", "Только аудио", "视频与音频", "仅音频", "動画と音声", "音声のみ")) and not is_audio_copy
            if fade_pos in ("No início", "Ambos", "start", "both", "At start", "Both", "Al inicio", "Au début", "Les deux", "Am Anfang", "Beide", "All'inizio", "Entrambi", "В начале", "В начале и конце", "片头淡入", "首尾两端", "開始時", "両方"):
                if do_video: vf_filters.append(f"fade=t=in:st=0:d={fade_dur}")
                if do_audio: af_filters.append(f"afade=t=in:st=0:d={fade_dur}")
            if fade_pos in ("No final", "Ambos", "end", "both", "At end", "Both", "Al final", "À la fin", "Les deux", "Am Ende", "Beide", "Alla fine", "Entrambi", "В конце", "В начале и конце", "片尾淡出", "首尾两端", "終了時", "両方") and self.current_duration > 0:
                out_start = max(0, self.current_duration - fade_dur)
                if do_video: vf_filters.append(f"fade=t=out:st={out_start}:d={fade_dur}")
                if do_audio: af_filters.append(f"afade=t=out:st={out_start}:d={fade_dur}")

        # Velocidade (Speed Control)
        if speed_val != 1.0:
            if not is_audio_only:
                vf_filters.append(f"setpts={1.0/speed_val}*PTS")
            if not is_audio_copy:
                if speed_preserve:
                    tempo = speed_val
                    while tempo < 0.5:
                        af_filters.append("atempo=0.5")
                        tempo /= 0.5
                    if tempo != 1.0:
                        af_filters.append(f"atempo={tempo}")
                else:
                    specs = self.get_media_specs(input_file)
                    afreq_str = specs.get("afreq", "44100 Hz")
                    try:
                        sample_rate = int(afreq_str.split(" ")[0])
                    except:
                        sample_rate = 44100
                    af_filters.append(f"asetrate={sample_rate * speed_val}")
                    af_filters.append(f"aresample={sample_rate}")

        # 6. Build the Final Output Strategy (Image / Audio / Video)
        if is_image:
            image_codecs = {
                "webp": "libwebp_anim",
                "jpg": "mjpeg",
                "jpeg": "mjpeg",
                "png": "png",
                "gif": "gif",
                "bmp": "bmp",
                "tiff": "tiff"
            }
            if ext_destino in image_codecs:
                cmd.extend(["-c:v", image_codecs[ext_destino]])

            img_size = options.get("img_size", "default")
            if img_size != "default":
                width = img_size.split(' ')[0].split('x')[0]
                vf_filters.append(f"scale={width}:-2")
            
            q_val = options.get("img_quality", 2)
            if ext_destino == "webp":
                # WebP usa escala de 0 a 100, onde 100 é a melhor qualidade.
                # O slider da UI envia de 2 (melhor) a 31 (pior).
                # Fórmula para converter (2-31) para (100-0).
                webp_q = max(0, min(100, int(100 - ((q_val - 2) * 100 / 29))))
                cmd.extend(["-q:v", str(webp_q)])
            else:
                cmd.extend(["-q:v", str(q_val)])
                
            if vf_filters: cmd.extend(["-vf", ",".join(vf_filters)])

        elif is_audio_only:
            acodec = options.get("acodec", "default")
            if acodec != "default": cmd.extend(["-c:a", acodec])
            abitrate = options.get("abitrate", "default")
            if abitrate != "default": cmd.extend(["-b:a", abitrate])
            freq = options.get("freq", "default")
            if freq != "default": cmd.extend(["-ar", freq])
            channels = options.get("channels", "default")
            if channels != "default": cmd.extend(["-ac", channels])
            
            cover_path = options.get("metadata", {}).get("cover_path", "")
            has_cover = cover_path and os.path.isfile(cover_path)
            if has_cover:
                cmd.extend(["-map", "1:v:0", "-c:v", "copy", "-disposition:v", "attached_pic"])
            else:
                cmd.extend(["-vn"])

            if af_filters: cmd.extend(["-af", ",".join(af_filters)])

        else:
            adv = options.get("video_advanced", {})
            if vcodec != "default":
                cmd.extend(["-c:v", vcodec])
                if "nvenc" in vcodec:
                    cmd.extend(["-preset", "p7", "-profile:v", "high", "-tune", "hq", "-cq", "18", "-spatial-aq", "1", "-temporal-aq", "1", "-rc-lookahead", "32", "-b_ref_mode", "2"])
                elif vcodec in ["libx264", "libx265"]:
                    # Injeção Handbrake
                    if adv:
                        preset = adv.get("preset", "medium")
                        if pass_num == 1 and adv.get("turbo_first_pass"):
                            cmd.extend(["-preset", "ultrafast"])
                        elif preset != "medium":
                            cmd.extend(["-preset", preset])
                            
                        tune = adv.get("tune", "none")
                        fast_dec = adv.get("fast_decode")
                        tunes = []
                        if tune != "none": tunes.append(tune)
                        if fast_dec and "fastdecode" not in tunes: tunes.append("fastdecode")
                        if tunes:
                            cmd.extend(["-tune", ",".join(tunes)])
                            
                        profile = adv.get("profile", "auto")
                        if profile != "auto":
                            cmd.extend(["-profile:v", profile])
                            
                        level = adv.get("level", "auto")
                        if level != "auto":
                            cmd.extend(["-level", level])
                            
                        x264_opts = adv.get("x264_opts", "")
                        if x264_opts:
                            if vcodec == "libx265": cmd.extend(["-x265-params", x264_opts])
                            else: cmd.extend(["-x264-params", x264_opts])
                            
            if adv.get("color_range") == "Limited":
                cmd.extend(["-color_range", "tv"])
            elif adv.get("color_range") == "Full":
                cmd.extend(["-color_range", "pc"])

            threads = options.get("threads", 0)
            if threads > 0 and vcodec in ("libx264", "libx265"):
                cmd.extend(["-threads:v", str(threads)])

            is_nvenc = "nvenc" in vcodec
            crf_enabled = options.get("crf_enabled", False)

            if crf_enabled and vcodec not in ("default", "copy", "mpeg4"):
                crf_val = str(options.get("crf_value", 23))
                if is_nvenc:
                    cmd.extend(["-cq", crf_val, "-qmin", crf_val, "-qmax", crf_val])
                else:
                    cmd.extend(["-crf", crf_val])
            else:
                vbitrate = options.get("vbitrate", "default")
                if vbitrate != "default":
                    cmd.extend(["-b:v", vbitrate])
                    kbps = self.parse_bitrate_to_kbps(vbitrate)
                    if is_nvenc:
                        cmd.extend(["-maxrate", vbitrate])
                    else:
                        if kbps is not None and kbps > 0:
                            cmd.extend(["-maxrate", vbitrate, "-bufsize", f"{kbps * 2}k"])

            acodec = options.get("acodec", "default")
            if acodec != "default": cmd.extend(["-c:a", acodec])
            abitrate = options.get("abitrate", "default")
            if abitrate != "default": cmd.extend(["-b:a", abitrate])
            freq = options.get("freq", "default")
            if freq != "default": cmd.extend(["-ar", freq])
            channels = options.get("channels", "default")
            if channels != "default": cmd.extend(["-ac", channels])

            vsize = options.get("vsize", "default")
            if vsize != "default":
                size_clean = vsize.split(' ')[0]
                target_w, target_h = (int(size_clean.split('x')[0]), int(size_clean.split('x')[1])) if "x" in size_clean else (1280, 720)
                orig_w, orig_h = self.get_video_resolution(input_file)
                if orig_w > 0 and orig_h > 0 and orig_h > orig_w and target_w > target_h:
                    target_w, target_h = target_h, target_w

                if "nvenc" in vcodec and self._cuda_scale_filter != "cpu" and not has_watermark:
                    # ✅ FIX: Pipeline de escala 100% GPU — zero cópias PCIe.
                    # Bug histórico: scale lavfi forçava GPU→CPU→CPU-scale→GPU por frame.
                    # scale_npp usa Super Sampling (melhor qualidade); scale_cuda usa Lanczos CUDA.
                    # A altura é calculada explicitamente (múltiplo par) para compatibilidade
                    # com versões antigas do FFmpeg que não suportam -2 em filtros CUDA.
                    # Watermark desativa o caminho GPU — bug 24 do project-memory:
                    # overlay lavfi (CPU) é incompatível com hwdec auto-safe.
                    if orig_w > 0 and orig_h > 0:
                        calculated_h = int((target_w * orig_h) / orig_w)
                        target_h = calculated_h + (calculated_h % 2)  # garante múltiplo par
                    if self._cuda_scale_filter == "scale_npp":
                        vf_filters.append(f"scale_npp={target_w}:{target_h}:interp=super")
                    else:  # scale_cuda
                        vf_filters.append(f"scale_cuda={target_w}:{target_h}:interp_algo=lanczos")
                else:
                    # Fallback CPU: comportamento original (watermark ativo ou GPU indisponível)
                    vf_filters.append(f"scale={target_w}:-2:flags=lanczos,setsar=1")

            vfps = options.get("vfps", "default")
            if vfps != "default":
                fps_mode = adv.get("fps_mode", "vfr") if 'adv' in locals() else "vfr"
                if fps_mode == "cfr":
                    cmd.extend(["-fps_mode", "cfr"])
                    if "nvenc" in vcodec: cmd.extend(["-r", str(vfps)])
                    else: vf_filters.append(f"fps={vfps}")
                elif fps_mode == "vfr":
                    cmd.extend(["-fps_mode", "vfr"])
                    # FFmpeg 7 proíbe o uso de -r ou -fpsmax com -fps_mode vfr
                    vf_filters.append(f"fps={vfps}")

            watermark = options.get("watermark", {})
            if watermark.get("enabled") and watermark.get("image_path") and os.path.exists(watermark["image_path"]):
                escaped_img = watermark["image_path"].replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
                size_factor = watermark.get("size", 100) / 100.0
                opacity = watermark.get("opacity", 100) / 100.0
                pos = watermark.get("position", "bottom_right")
                
                if pos in ("Superior esquerdo", "top_left", "Top-Left", "En haut à gauche", "Oben links", "In alto a sinistra", "Вверху слева", "左上角", "左上", "Superior izquierda"):
                    x, y = "10", "10"
                elif pos in ("Superior direito", "top_right", "Top-Right", "En haut à droite", "Oben rechts", "In alto a destra", "Вверху справа", "右上角", "右上", "Superior derecha"):
                    x, y = "W-w-10", "10"
                elif pos in ("Centro", "center", "Center", "Centre", "Mitte", "По центру", "居中", "中央"):
                    x, y = "(W-w)/2", "(H-h)/2"
                elif pos in ("Inferior esquerdo", "bottom_left", "Bottom-Left", "En bas à gauche", "Unten links", "In basso a sinistra", "Внизу слева", "左下角", "左下", "Inferior izquierda"):
                    x, y = "10", "H-h-10"
                else: # "Inferior direito", "bottom_right", etc.
                    x, y = "W-w-10", "H-h-10"
                wm_setup = f"movie='{escaped_img}',format=rgba[wm];[wm]scale=iw*{size_factor}:ih*{size_factor},colorchannelmixer=aa={opacity}[wm_mod]"
                
                if vf_filters:
                    base_vf = ",".join(vf_filters)
                    final_vf = f"{base_vf}[bg];{wm_setup};[bg][wm_mod]overlay={x}:{y}"
                else:
                    final_vf = f"{wm_setup};[in][wm_mod]overlay={x}:{y}"
                
                cmd.extend(["-vf", final_vf])
            elif vf_filters:
                cmd.extend(["-vf", ",".join(vf_filters)])
            if af_filters: cmd.extend(["-af", ",".join(af_filters)])

        metadata = options.get("metadata", {})
        if metadata.get("title"):
            cmd.extend(["-metadata", f"title={metadata['title']}"])
        if metadata.get("artist"):
            cmd.extend(["-metadata", f"artist={metadata['artist']}"])
        if metadata.get("album"):
            cmd.extend(["-metadata", f"album={metadata['album']}"])
        if metadata.get("year"):
            cmd.extend(["-metadata", f"date={metadata['year']}"])
        if metadata.get("genre"):
            cmd.extend(["-metadata", f"genre={metadata['genre']}"])
        if metadata.get("comment"):
            cmd.extend(["-metadata", f"comment={metadata['comment']}"])

        extra = options.get("extra_args", "")
        if extra:
            try:
                import shlex
                cmd.extend(shlex.split(extra, posix=(os.name != 'nt')))
            except ValueError as e:
                self.log_updated.emit(f"⚠️ Argumentos extras malformados e ignorados: {e}\n")

        if pass_num == 1:
            null_output = "NUL" if os.name == 'nt' else "/dev/null"
            cmd.extend(["-pass", "1", "-passlogfile", options.get("passlog_prefix"), "-an", "-sn", "-f", "null", null_output])
        elif pass_num == 2:
            cmd.extend(["-pass", "2", "-passlogfile", options.get("passlog_prefix"), output_file])
        else:
            cmd.append(output_file)

        return cmd

    def read_ffmpeg_output(self):
        """
        Lê nativamente os logs gerados pela saída padrão do FFmpeg (stderr), extraindo 
        velocidade e tempo via RegEx para calcular e emitir porcentagens precisas à interface.
        """
        if not self.process:
            return
        output = self.process.readAllStandardError().data().decode("utf-8", errors="replace")
        self.log_updated.emit(output)
        time_matches = re.findall(r"time=(\d+):(\d+):(\d+\.\d+)", output)
        size_matches = re.findall(r"size=\s*(\d+)([a-zA-Z]+)", output, re.IGNORECASE)
        if time_matches and self.current_duration > 0:
            last_time = time_matches[-1]
            current_sec = (float(last_time[0]) * 3600) + (float(last_time[1]) * 60) + float(last_time[2])
            progress = min(int((current_sec / self.current_duration) * 100), 100)
            elapsed_sec = time.time() - self.conversion_start_time
            rem_sec = max(0, ((elapsed_sec / current_sec) * self.current_duration) - elapsed_sec) if current_sec > 0 else 0
            size_str = f"{size_matches[-1][0]} {size_matches[-1][1]}" if size_matches else ""
            status_prefix = f"Passo {self.current_pass} | " if self.current_pass > 0 else ""
            self.progress_updated.emit(self.current_row, progress, self.format_time(elapsed_sec), self.format_time(rem_sec), size_str, f"{status_prefix}{progress}%")

    def stop_all(self):
        """
        Mata o processo em background cancelando a conversão instantaneamente.
        """
        if self.process and self.process.state() == QProcess.Running:
            self.process.kill()

    def shutdown_pc(self):
        """
        Delegador de compatibilidade — a lógica reside em core.utils.shutdown_pc.
        Mantido para não quebrar call sites existentes.
        """
        from core.utils import shutdown_pc as _shutdown
        _shutdown()

    def suspend_pc(self):
        """
        Delegador de compatibilidade — a lógica reside em core.utils.suspend_pc.
        Mantido para não quebrar call sites existentes.
        """
        from core.utils import suspend_pc as _suspend
        _suspend()