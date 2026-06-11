import os
import re
import time
import subprocess
import tempfile
import json
from PySide6.QtCore import QObject, Signal, QProcess

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

        import sys
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

    def format_time(self, seconds):
        """
        Converte uma quantidade de segundos brutos para o formato legível HH:MM:SS.
        """
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02}:{m:02}:{s:02}"

    def get_media_duration(self, file_path):
        """
        Executa ffprobe para obter a duração total do arquivo multimídia em segundos.
        
        Returns:
            float: Duração em segundos, ou 0.0 se falhar.
        """
        try:
            cmd = [self.ffprobe_bin, "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", file_path]
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
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
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
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
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, startupinfo=startupinfo)
            if result.returncode != 0:
                return "❌ Erro ao ler informações da mídia."

            data = json.loads(result.stdout)
            out = []
            
            ext_destino = os.path.splitext(file_path)[1].lower().replace(".", "")
            is_image = ext_destino in ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp", "yuv"]

            out.append("📄 INFORMAÇÕES GERAIS")
            format_info = data.get("format", {})
            out.append(f"Arquivo: {os.path.basename(file_path)}")
            
            size_mb = int(format_info.get("size", 0)) / (1024 * 1024)
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
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
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
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5, startupinfo=startupinfo)
            data = json.loads(result.stdout)
            tracks = []
            for stream in data.get("streams", []):
                global_idx = stream.get("index")
                lang = stream.get("tags", {}).get("language", "ND").upper()
                tracks.append((global_idx, f"Faixa {global_idx} - Legenda ({lang})"))
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
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
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
        """
        if not value: return None
        try:
            txt = str(value).lower().strip().replace(" ", "")
            if not txt or txt == "default": return None
            txt = txt.replace("kbps", "k").replace("mbps", "m").replace("bps", "")
            if txt.endswith("m"): return int(float(txt[:-1]) * 1000)
            elif txt.endswith("k"): return int(float(txt[:-1]))
            else: return int(float(txt))
        except (ValueError, TypeError):
            return None

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

        if options.get("two_pass") and vcodec in ["libx264", "libx265"]:
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
        # 1. Base Configuration
        ffmpeg_bin = options.get("ffmpeg_path", "ffmpeg")
        cmd = [ffmpeg_bin, "-y", "-hide_banner"]

        ext_destino = os.path.splitext(output_file)[1].lower().replace(".", "")
        is_image = ext_destino in ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp", "yuv"]
        is_audio_only = ext_destino in ["mp3", "ogg", "wav", "aac", "flac", "wma", "ac3", "opus", "m4a"]
        is_subtitle_only = ext_destino in ["srt", "ass", "vtt"]

        if is_subtitle_only:
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

        if not is_image and not is_audio_only and "nvenc" in vcodec:
            cmd.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])

        # 2. Input File and Subtitles
        cmd.extend(["-i", input_file])
        vf_filters = []
        af_filters = []

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
                cmd.extend(["-map", f"-0:{track}?"])

        # 3.4. Áudios Externos mapeados sequencialmente
        for i in range(len(valid_audios)):
            cmd.extend(["-map", f"{1 + i}:a:0?"])
            
        # 3.5. Legendas Externas mapeadas sequencialmente
        if softsubs_added > 0:
            start_sub_idx = 1 + len(valid_audios)
            for i in range(softsubs_added):
                cmd.extend(["-map", f"{start_sub_idx + i}:0?"])
            
            cmd.extend(["-c:s", "mov_text" if ext_destino == "mp4" else "srt"])

        # 4. Audio Filters
        audio_offset_ms = options.get("audio_offset_ms", 0)
        if audio_offset_ms != 0 and options.get("acodec", "default") == "copy":
            options["acodec"] = "aac" if ext_destino == "mp4" else "default"
            self.log_updated.emit("⚠️ Sincronia de Áudio ativada: O áudio não pode ser 'copy'. Alterado para recodificação.\n")
            
        noise_reduction = options.get("noise_reduction", False)
        if noise_reduction and options.get("acodec", "default") == "copy":
            options["acodec"] = "aac" if ext_destino == "mp4" else "default"
            self.log_updated.emit("⚠️ Redução de Ruído ativada: O áudio não pode ser 'copy'. Alterado para recodificação.\n")
            
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

        if vol != 100 and not is_audio_copy:
            af_filters.append(f"volume={vol/100.0}")
        if options.get("audio_drc") and not is_audio_copy:
            af_filters.append("pan=stereo|FL=0.5*FC+0.707*FL+0.707*BL+0.5*LFE|FR=0.5*FC+0.707*FR+0.707*BR+0.5*LFE,dynaudnorm")

        # 5. Video Filters
        if options.get("deinterlace"):
            vf_filters.append("yadif_cuda" if "nvenc" in vcodec else "yadif")

        rotate = options.get("rotate", "Normal")
        if rotate == "90° Horário": vf_filters.append("transpose=1")
        elif rotate == "90° Anti-horário": vf_filters.append("transpose=2")
        elif rotate == "180°": vf_filters.append("transpose=2,transpose=2")
        elif rotate == "Espelhar Horizontal": vf_filters.append("hflip")
        elif rotate == "Espelhar Vertical": vf_filters.append("vflip")

        crop = options.get("crop", {})
        if crop.get("enabled"):
            t, b, l, r = crop["t"], crop["b"], crop["l"], crop["r"]
            vf_filters.append(f"crop=iw-{l}-{r}:ih-{t}-{b}:{l}:{t}")

        pad = options.get("pad", {})
        if pad.get("enabled"):
            t, b, l, r = pad["t"], pad["b"], pad["l"], pad["r"]
            vf_filters.append(f"pad=iw+{l}+{r}:ih+{t}+{b}:{l}:{t}:black")

        fade_dur = options.get("fade_dur", 0)
        fade_pos = options.get("fade_pos", "Nenhum")
        fade_type = options.get("fade_type", "Vídeo e Áudio")
        if fade_dur > 0 and fade_pos != "Nenhum":
            do_video = fade_type in ["Vídeo e Áudio", "Somente Vídeo"]
            do_audio = (fade_type in ["Vídeo e Áudio", "Somente Áudio"]) and not is_audio_copy
            if fade_pos in ["No início", "Ambos"]:
                if do_video: vf_filters.append(f"fade=t=in:st=0:d={fade_dur}")
                if do_audio: af_filters.append(f"afade=t=in:st=0:d={fade_dur}")
            if fade_pos in ["No final", "Ambos"] and self.current_duration > 0:
                out_start = max(0, self.current_duration - fade_dur)
                if do_video: vf_filters.append(f"fade=t=out:st={out_start}:d={fade_dur}")
                if do_audio: af_filters.append(f"afade=t=out:st={out_start}:d={fade_dur}")

        # 6. Build the Final Output Strategy (Image / Audio / Video)
        if is_image:
            img_size = options.get("img_size", "default")
            if img_size != "default":
                width = img_size.split(' ')[0].split('x')[0]
                vf_filters.append(f"scale={width}:-2")
            cmd.extend(["-q:v", str(options.get("img_quality", 2))])
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
            cmd.extend(["-vn"])
            if af_filters: cmd.extend(["-af", ",".join(af_filters)])

        else:
            if vcodec != "default":
                cmd.extend(["-c:v", vcodec])
                if "nvenc" in vcodec:
                    cmd.extend(["-preset", "p7", "-profile:v", "high", "-tune", "hq", "-cq", "18", "-spatial-aq", "1", "-temporal-aq", "1", "-rc-lookahead", "32", "-b_ref_mode", "2"])

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
                if "nvenc" in vcodec:
                    if orig_w > 0 and orig_h > 0:
                        calculated_h = int((target_w * orig_h) / orig_w)
                        target_h = calculated_h + 1 if calculated_h % 2 != 0 else calculated_h
                    vf_filters.append(f"scale_cuda={target_w}:{target_h}")
                else:
                    vf_filters.append(f"scale={target_w}:-2:flags=lanczos,setsar=1")

            vfps = options.get("vfps", "default")
            if vfps != "default":
                if "nvenc" in vcodec: cmd.extend(["-r", str(vfps)])
                else: vf_filters.append(f"fps={vfps}")

            if vf_filters: cmd.extend(["-vf", ",".join(vf_filters)])
            if af_filters: cmd.extend(["-af", ",".join(af_filters)])

        extra = options.get("extra_args", "")
        if extra: cmd.extend(extra.split(" "))

        if pass_num == 1:
            cmd.extend(["-pass", "1", "-passlogfile", options.get("passlog_prefix"), "-an", "-sn", "-f", "null", "/dev/null"])
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