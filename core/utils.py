def normalize_bitrate(raw_text: str) -> str:
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