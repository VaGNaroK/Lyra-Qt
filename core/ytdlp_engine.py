import sys
import os
from PySide6.QtCore import QObject, Signal, QProcess

class YTDLPEngine(QObject):
    """
    Motor assíncrono responsável por gerenciar downloads via yt-dlp.
    Usa QProcess para executar yt-dlp em background e captura os logs nativamente.
    """
    log_updated = Signal(str)
    process_finished = Signal(int)
    error_occurred = Signal(str)

    def __init__(self, resource_dir):
        """
        Inicializa o motor configurando os caminhos corretos do binário yt-dlp.
        
        Args:
            resource_dir (str): Diretório base de recursos para achar os binários no Windows.
        """
        super().__init__()
        self.resource_dir = resource_dir
        self.process = None
        if sys.platform == "win32":
            self.ytdlp_bin = os.path.join(self.resource_dir, "assets", "bin", "yt-dlp.exe")
        else:
            # Verifica se há um yt-dlp no mesmo diretório do Python atual (ex: dentro do venv)
            venv_ytdlp = os.path.join(os.path.dirname(sys.executable), "yt-dlp")
            if os.path.isfile(venv_ytdlp):
                self.ytdlp_bin = venv_ytdlp
            else:
                self.ytdlp_bin = "yt-dlp"

    def start_download(self, url: str, dest_path: str, mode: int, options: dict):
        # ✅ FIX: Validar URL antes de passar para o yt-dlp
        from urllib.parse import urlparse
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            self.error_occurred.emit(
                f"URL inválida: apenas URLs http/https são permitidas. Recebido: '{url[:60]}'"
            )
            return
        """
        Inicia o download de uma URL com os parâmetros especificados pelo usuário.
        
        Args:
            url (str): Link do vídeo ou áudio.
            dest_path (str): Pasta onde o arquivo final será salvo.
            mode (int): Modo de download (0 para Vídeo, 1 para Áudio).
            options (dict): Dicionário contendo filtros e formatos (resolução, bitrate, etc).
        """
        self.process = QProcess(self)
        cmd = [self.ytdlp_bin, "--newline", "--ignore-errors", "--no-playlist", "-o", os.path.join(dest_path, "%(title)s.%(ext)s")]

        if mode == 1:
            cmd.extend(["-x", "--audio-format", options.get("a_fmt", "mp3"), "--audio-quality", options.get("a_bitrate", "128K")])
        else:
            fmt = options.get("v_fmt", "mp4")
            res_text = options.get("v_res", "Melhor Disponível")
            height_map = {
                "Melhor Disponível": "", "2160p (4K)": "[height<=2160]", "1440p (QuadHD)": "[height<=1440]",
                "1080p (FullHD)": "[height<=1080]", "720p (HD)": "[height<=720]", "480p (SD)": "[height<=480]"
            }
            res_filter = height_map.get(res_text, "")
            format_str = f"bestvideo{res_filter}+bestaudio/best{res_filter}"
            self.log_updated.emit(f"🔍 Filtro yt-dlp aplicado: {format_str}\n")
            cmd.extend(["-f", format_str, "--merge-output-format", fmt])

        cmd.append(url)
        self.process.setProgram(cmd[0])
        self.process.setArguments(cmd[1:])
        self.process.readyReadStandardOutput.connect(self._on_stdout)
        self.process.readyReadStandardError.connect(self._on_stderr)
        self.process.errorOccurred.connect(self._on_error)
        self.process.finished.connect(self._on_finished)
        self.process.start()

    def stop(self):
        """
        Cancela o download forçadamente matando o processo atual do yt-dlp.
        """
        if self.process and self.process.state() == QProcess.Running:
            self.process.kill()

    def _on_stdout(self):
        """
        Lê e decodifica a saída padrão do processo yt-dlp em tempo real.
        Emite o texto lido para o sinal log_updated da GUI.
        """
        text = self.process.readAllStandardOutput().data().decode("utf-8", "replace")
        self.log_updated.emit(text)

    def _on_stderr(self):
        """
        Lê e decodifica os erros/avisos do processo yt-dlp em tempo real.
        """
        text = self.process.readAllStandardError().data().decode("utf-8", "replace")
        self.log_updated.emit(text)

    def _on_error(self, error):
        """
        Captura erros do próprio QProcess (ex: binário yt-dlp não encontrado).
        """
        self.error_occurred.emit(str(error))

    def _on_finished(self, exitCode, exitStatus):
        """
        Avisa a GUI quando o processo do yt-dlp terminar completamente.
        """
        self.process_finished.emit(exitCode)