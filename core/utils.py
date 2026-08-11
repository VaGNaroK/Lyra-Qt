import os
import subprocess

# ==============================================================================
# Constantes de Extensão (Single Source of Truth)
# Evita triplicação das listas em ffmpeg_engine.py e facilita manutenção.
# ==============================================================================
IMAGE_EXTENSIONS = frozenset(["jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp", "yuv"])
AUDIO_EXTENSIONS = frozenset(["mp3", "ogg", "wav", "aac", "flac", "wma", "ac3", "opus", "m4a"])
SUBTITLE_EXTENSIONS = frozenset(["srt", "ass", "vtt"])


def normalize_bitrate(raw_text: str) -> str:
    """
    Normaliza a string de bitrate recebida da interface para o formato aceito pelo FFmpeg (ex: '320k', '2M').

    Args:
        raw_text (str): O texto bruto do bitrate inserido pelo usuário (ex: '320 kbps').

    Returns:
        str: A string formatada (ex: '320k') ou 'default' caso inválida.
    """
    if not raw_text:
        return "default"
    txt = (raw_text.lower().replace("kbps", "k").replace("mbps", "m").replace(" ", "").strip())
    if not txt or txt == "default":
        return "default"
    if txt.endswith("k") or txt.endswith("m"):
        return txt
    try:
        float(txt)
        return f"{txt}k"
    except ValueError:
        pass
    return txt


def format_time_hms(seconds) -> str:
    """
    Converte segundos para o formato HH:MM:SS sempre com 3 grupos.
    Usado nos logs de progresso do FFmpegEngine (ex: '01:23:45', '00:01:05').

    Args:
        seconds: Número de segundos (int ou float).

    Returns:
        str: Tempo no formato HH:MM:SS.
    """
    total = int(seconds) if seconds else 0
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_time_player(seconds) -> str:
    """
    Converte segundos para o formato MM:SS ou HH:MM:SS omitindo horas quando zero.
    Usado na interface do MPVPlayerWidget (ex: '01:05', '01:23:45').

    Args:
        seconds: Número de segundos (int ou float). None retorna '00:00'.

    Returns:
        str: Tempo formatado.
    """
    if seconds is None:
        return "00:00"
    total = int(seconds)
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def parse_bitrate_to_kbps(value) -> int | None:
    """
    Converte strings de bitrate (ex: '2M', '500k', '320 kbps') para valores inteiros em kbps.

    Args:
        value: String ou número representando o bitrate.

    Returns:
        int: Valor em kbps, ou None se inválido/vazio.
    """
    if not value:
        return None
    try:
        txt = str(value).lower().strip().replace(" ", "")
        if not txt or txt == "default":
            return None
        txt = txt.replace("kbps", "k").replace("mbps", "m").replace("bps", "")
        if txt.endswith("m"):
            return int(float(txt[:-1]) * 1000)
        elif txt.endswith("k"):
            return int(float(txt[:-1]))
        else:
            return int(float(txt))
    except (ValueError, TypeError):
        return None


# ==============================================================================
# Ações de Sistema (extraídas do FFmpegEngine para manter SRP)
# 🔒 FIX: Flatpak não permite shutdown direto; usa D-Bus (org.freedesktop.login1).
#         Bug 13 no project-memory.md
# ==============================================================================
def shutdown_pc():
    """Executa o desligamento do computador via sistema operacional ou D-Bus (Flatpak)."""
    is_flatpak = "FLATPAK_ID" in os.environ
    if os.name == 'nt':
        os.system("shutdown /s /t 0")
    else:
        if is_flatpak:
            subprocess.Popen([
                "dbus-send", "--system", "--print-reply",
                "--dest=org.freedesktop.login1",
                "/org/freedesktop/login1",
                "org.freedesktop.login1.Manager.PowerOff",
                "boolean:true"
            ])
        else:
            os.system("systemctl poweroff")


def suspend_pc():
    """Executa a suspensão do computador via sistema operacional ou D-Bus (Flatpak)."""
    is_flatpak = "FLATPAK_ID" in os.environ
    if os.name == 'nt':
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    else:
        if is_flatpak:
            subprocess.Popen([
                "dbus-send", "--system", "--print-reply",
                "--dest=org.freedesktop.login1",
                "/org/freedesktop/login1",
                "org.freedesktop.login1.Manager.Suspend",
                "boolean:true"
            ])
        else:
            os.system("systemctl suspend")