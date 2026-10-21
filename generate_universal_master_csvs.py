def load_extra_specs():
    p = CONTENT_DIR / "specs.json"
    if not p.exists(): return [], []
    d = json.loads(p.read_text(encoding="utf-8"))
    return d.get("horizontal", []), d.get("vertical", [])

# inside main():
ex_h, ex_v = load_extra_specs()
horizontal_rows = [build_row("horizontal", s) for s in HORIZONTAL_SPECS + ex_h]
vertical_rows   = [build_row("vertical",   s) for s in VERTICAL_SPECS   + ex_v]
