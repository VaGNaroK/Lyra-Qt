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