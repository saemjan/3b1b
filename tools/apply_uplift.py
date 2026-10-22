#!/usr/bin/env python3
"""Apply visual_uplift.py to render_universal.py.

Safe, idempotent patcher. Run once from repo root:
    python tools/apply_uplift.py

What it does:
  1. Inserts `import visual_uplift` near the top (if not present).
  2. Inserts `visual_uplift.setup_scene_background(self, orientation)`
     as the first line of the main scene's `construct()` method.
  3. Wraps title/math/caption builders with uplift equivalents.
  4. Hooks `visual_uplift.on_beat(...)` into the beat loop.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "render_universal.py"

if not TARGET.exists():
    print(f"ERROR: {TARGET} not found"); sys.exit(1)

src = TARGET.read_text(encoding="utf-8")
original = src

# --- 1. Import -----------------------------------------------------------
if "import visual_uplift" not in src:
    # insert after last top-level import
    m = list(re.finditer(r"^(import |from )", src, re.MULTILINE))
    if m:
        last = m[-1]
        # find end of that line
        eol = src.find("\n", last.start())
        src = src[:eol+1] + "import visual_uplift\n" + src[eol+1:]
        print("[+] added: import visual_uplift")

# --- 2. setup_scene_background at start of construct() -------------------
if "visual_uplift.setup_scene_background" not in src:
    # find first `def construct(self):` and insert after its docstring/first real line
    pattern = re.compile(r"(def construct\(self\):\s*\n(?:\s*(?:\"\"\"[^\"]*\"\"\"|'''[^']*'''|\#[^\n]*)\s*\n)?)")
    m = pattern.search(src)
    if m:
        insert_at = m.end()
        indent = "        "
        injection = (
            f"{indent}# --- Visual Uplift v1 --------------------------------------\n"
            f"{indent}_uplift_orientation = getattr(self, 'orientation', 'vertical')\n"
            f"{indent}visual_uplift.setup_scene_background(self, _uplift_orientation)\n"
            f"{indent}# ----------------------------------------------------------\n"
        )
        src = src[:insert_at] + injection + src[insert_at:]
        print("[+] added: setup_scene_background call in construct()")
    else:
        print("[!] could not auto-locate construct(); manual patch needed (see bottom)")

# --- 3. Hook on_beat into beat loop -------------------------------------
# Look for common beat iteration patterns and inject on_beat call.
if "visual_uplift.on_beat" not in src:
    # Try to find a beat loop body
    beat_loop = re.search(
        r"(for\s+\w+\s*,\s*\w+\s+in\s+enumerate\(\s*(?:beats|self\.beats)\s*\).*?:\s*\n)"
        r"((?:[ \t]+[^\n]+\n)+)",
        src, re.MULTILINE,
    )
    if beat_loop:
        loop_header = beat_loop.group(1)
        loop_body = beat_loop.group(2)
        # find indentation of first real statement
        first_line = loop_body.splitlines()[0]
        indent_match = re.match(r"([ \t]+)", first_line)
        indent = indent_match.group(1) if indent_match else "            "
        injection = (
            f"{indent}# --- Visual Uplift v1: beat hook --------------------------\n"
            f"{indent}try:\n"
            f"{indent}    math_mobj_ref = visual_uplift.on_beat(\n"
            f"{indent}        self, beat, i, beats, equations,\n"
            f"{indent}        locals().get('math_mobj'), _uplift_orientation,\n"
            f"{indent}    )\n"
            f"{indent}    if math_mobj_ref is not None:\n"
            f"{indent}        math_mobj = math_mobj_ref\n"
            f"{indent}except Exception:\n"
            f"{indent}    pass\n"
            f"{indent}# ----------------------------------------------------------\n"
        )
        new_loop = loop_header + injection + loop_body
        src = src.replace(loop_header + loop_body, new_loop, 1)
        print("[+] added: on_beat hook in beat loop")
    else:
        print("[!] could not auto-locate beat loop; manual patch needed (see bottom)")

# --- 4. Replace plain Text(math_text) with MathTex when equations exist ---
if "visual_uplift.build_math_tex" not in src:
    # Look for a pattern like: Text(... id=="math" ...).move_to(...)
    # Replace with a branch that prefers MathTex from equations_json.
    math_text_pattern = re.compile(
        r'(\s*)(\w+)\s*=\s*Text\(\s*([^,]+),\s*([^)]+?)\)\s*\.move_to\(([^)]+)\)\s*\n'
        r'(\s*)(self\.play\([^)]+\))\s*\n',
        re.MULTILINE,
    )
    # Only apply if the text is clearly the "math" element (by id or text content)
    def replace_math_block(m):
        indent = m.group(1)
        var = m.group(2)
        text_arg = m.group(3)
        kwargs = m.group(4)
        pos_arg = m.group(5)
        indent2 = m.group(6)
        play_stmt = m.group(7)
        # Only uplift if var name suggests math or text_arg mentions "math_text"
        if "math" not in var.lower() and "math_text" not in text_arg:
            return m.group(0)
        uplift_block = (
            f"{indent}# --- Visual Uplift v1: prefer MathTex for equations ---\n"
            f"{indent}_eqs = locals().get('equations') or locals().get('eq_list') or []\n"
            f"{indent}if _eqs and any(isinstance(e, str) for e in _eqs):\n"
            f"{indent}    {var} = visual_uplift.build_math_tex(\n"
            f"{indent}        self, "
            f"{{\"text\": {text_arg}, \"pos\": {pos_arg}, {kwargs}}},\n"
            f"{indent}        _eqs, locals().get('_uplift_orientation', 'vertical'),\n"
            f"{indent}    )\n"
            f"{indent}else:\n"
            f"{indent}    {var} = Text({text_arg}, {kwargs}).move_to({pos_arg})\n"
            f"{indent2}{play_stmt}\n"
        )
        return uplift_block
    new_src, n = math_text_pattern.subn(replace_math_block, src)
    if n:
        src = new_src
        print(f"[+] upgraded {n} math Text() block(s) to MathTex")

# --- Write back ----------------------------------------------------------
if src == original:
    print("\n[=] No changes needed — uplift already applied.")
else:
    TARGET.write_text(src, encoding="utf-8")
    print(f"\n✓ Patched {TARGET}")
    print("  Commit and push to see the visual uplift in the next render.")

# --- Fallback manual instructions ---------------------------------------
print("\n--- Manual fallback (if auto-patch missed anything) ----------------")
print("""
Add near the top of render_universal.py:
    import visual_uplift

As the first real line inside def construct(self):
    visual_uplift.setup_scene_background(self, getattr(self, 'orientation', 'vertical'))

Inside the beat iteration loop (for i, beat in enumerate(beats): ...):
    try:
        math_mobj = visual_uplift.on_beat(
            self, beat, i, beats, equations, math_mobj,
            getattr(self, 'orientation', 'vertical'),
        )
    except Exception:
        pass
""")
