#!/usr/bin/env python3
"""H1: cairo vs ManimGX on the 3 hottest primitives. Emits bench_report.{md,json}.
v3 (Gen-3 contract): the pre-registered verdict rule is now FULLY enforced —
ADOPT iff >=5x on >=2/3 prims AND frame diff < 8/255 (PPM-ruler, stdlib) AND
backend CI-installable. Rc!=0 renders produce no speedup (fail-closed).
selftest, ledger receipt, bounded timeouts, exit codes 0 ok / 1 drift / 2 env.
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    from tools.ledger import append as ledger_append
except ImportError:
    def ledger_append(entry):
        print(f"[bench] WARN ledger unavailable; entry dropped: {entry.get('op')}",
              file=sys.stderr)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 3
HOT = ["particle_gas", "random_walk", "two_path_interference"]
OUT = ROOT / "bench_out"
FRAME_DIFF_MAX = 8 / 255.0          # pre-registered visual-parity bound
SPEEDUP_MIN = 5.0
WINS_MIN = 2
RENDER_TIMEOUT = 600
FRAME_AT = 1.0                      # deterministic mid-scene sample (seed=7)

SCENE = '''
from manim import *
import random
class Bench(Scene):
    def construct(self):
        random.seed(7)
        prim = "{prim}"
        if prim == "particle_gas":
            box = Rectangle(6.8, 3.0)
            dots = VGroup(*[Dot(RIGHT*random.uniform(-3,3)+UP*random.uniform(-1.4,1.4), radius=.05) for _ in range(60)])
            self.add(box, dots)
            self.play(*[d.animate.shift(RIGHT*random.uniform(-1,1)+UP*random.uniform(-1,1)) for d in dots[:20]], run_time=2)
        elif prim == "random_walk":
            pts=[ORIGIN]
            for _ in range(300): pts.append(pts[-1]+RIGHT*random.uniform(-.3,.3)+UP*random.uniform(-.3,.3))
            self.play(Create(VGroup(*[Line(a,b) for a,b in zip(pts,pts[1:])])), run_time=2)
        else:
            w1 = FunctionGraph(lambda x: 1.5*sin(5*x), x_range=[-3.5,3.5])
            w2 = FunctionGraph(lambda x: 1.5*sin(7*x+1), x_range=[-3.5,3.5])
            self.play(Create(w1), Create(w2), run_time=2)
'''
BACKENDS = {
    "cairo":   [sys.executable, "-m", "manim", "render", "-ql", "--fps", "15"],
    "manimgx": [sys.executable, "-m", "manimgx", "render", "-ql", "--fps", "15"],
}

# ---------------------------------------------------------------- pure rulers
def speedup_of(base_s, cand_s):
    """Speedup only exists when BOTH renders succeeded; anything else is None."""
    if base_s is None or cand_s is None or cand_s <= 0:
        return None
    return round(base_s / cand_s, 1)

def verdict_of(wins, total, frames_ok, installable):
    """The pre-registered rule, enforced as written. Fail-closed on every clause."""
    if wins >= WINS_MIN and frames_ok and installable:
        return "ADOPT manimgx for hot primitives"
    why = []
    if wins < WINS_MIN:
        why.append(f"speedup>={SPEEDUP_MIN:g}x on only {wins}/{total} prims")
    if not frames_ok:
        why.append("frame-diff witness missing or > 8/255")
    if not installable:
        why.append("backend not CI-installable")
    return "REJECT manimgx (" + "; ".join(why) + "; record numbers; next: H2/H5)"

# ---------------------------------------------------------------- PPM frame ruler (stdlib only)
def _read_p6(path):
    raw = Path(path).read_bytes()
    if not raw.startswith(b"P6"):
        raise ValueError("not a P6 ppm")
    idx, toks = 2, []
    while len(toks) < 3:
        while idx < len(raw) and raw[idx:idx + 1] in (b" ", b"\t", b"\n", b"\r"):
            idx += 1
        if idx < len(raw) and raw[idx:idx + 1] == b"#":
            while idx < len(raw) and raw[idx:idx + 1] != b"\n":
                idx += 1
            continue
        start = idx
        while idx < len(raw) and raw[idx:idx + 1] not in (b" ", b"\t", b"\n", b"\r"):
            idx += 1
        toks.append(int(raw[start:idx]))
    idx += 1  # single whitespace after maxval
    w, h, maxv = toks
    if maxv != 255:
        raise ValueError("only maxval 255 supported")
    px = raw[idx:idx + w * h * 3]
    if len(px) < w * h * 3:
        raise ValueError("truncated ppm")
    return w, h, px

def frame_diff_ppm(a, b):
    """Mean absolute per-channel difference in [0,1]; 1.0 on shape mismatch."""
    wa, ha, pa = _read_p6(a)
    wb, hb, pb = _read_p6(b)
    if (wa, ha) != (wb, hb):
        return 1.0
    total = sum(abs(x - y) for x, y in zip(pa, pb))
    return total / (len(pa) * 255.0)

def check_frames(cairo_vid, gx_vid, tag):
    """Visual-parity witness. Returns diff in [0,1], or None when unmeasurable.
    None is NOT a pass: the verdict rule requires a measured diff < 8/255."""
    if not (cairo_vid and gx_vid) or not shutil.which("ffmpeg"):
        return None
    outs = []
    try:
        for vid, name in ((cairo_vid, f"{tag}_cairo.ppm"), (gx_vid, f"{tag}_gx.ppm")):
            out = OUT / name
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(FRAME_AT),
                            "-i", vid, "-vframes", "1", "-f", "image2",
                            "-c:v", "ppm", str(out)],
                           check=True, capture_output=True, timeout=60)
            outs.append(out)
        return frame_diff_ppm(outs[0], outs[1])
    except Exception:
        return None

# ---------------------------------------------------------------- harness
def importable(mod):
    return subprocess.run([sys.executable, "-c", f"import {mod}"],
                          capture_output=True, timeout=60).returncode == 0

def run_backend(name, cmd, scene_py, tag):
    media = OUT / f"{tag}_{name}"
    t0 = time.perf_counter()
    try:
        r = subprocess.run(cmd + ["--media_dir", str(media), str(scene_py), "Bench"],
                           capture_output=True, text=True, timeout=RENDER_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"sec": None, "rc": -1, "err": f"timeout after {RENDER_TIMEOUT}s",
                "video": None}
    dt = time.perf_counter() - t0
    video = next(iter(sorted(media.rglob("Bench.mp4"))), None)
    ok = r.returncode == 0 and video is not None
    return {"sec": round(dt, 1) if ok else None, "rc": r.returncode,
            "err": "" if ok else (r.stderr[-300:] or "no mp4 produced"),
            "video": str(video) if video else None}

def main():
    if "--selftest" in sys.argv:
        return selftest()
    dry = "--dry-run" in sys.argv
    as_json = "--json" in sys.argv
    OUT.mkdir(exist_ok=True)

    # environment probes (exit-code 2 territory, recorded — never hidden)
    cairo_ok, gx_ok = importable("manim"), importable("manimgx")
    ffmpeg_ok = bool(shutil.which("ffmpeg"))
    if not cairo_ok:
        print("[bench] ENV: manim not importable — the baseline ruler is missing")
        return 2

    rows, baseline_broken = [], False
    for prim in HOT:
        sp = OUT / f"scene_{prim}.py"
        sp.write_text(SCENE.format(prim=prim), encoding="utf-8")
        if dry:
            print(f"[bench] dry: wrote {sp.name}")
            continue
        c = run_backend("cairo", BACKENDS["cairo"], sp, prim)
        g = run_backend("manimgx", BACKENDS["manimgx"], sp, prim) if gx_ok else \
            {"sec": None, "rc": -2, "err": "manimgx not importable", "video": None}
        if c["rc"] != 0:
            baseline_broken = True
        speed = speedup_of(c["sec"], g["sec"]) if (c["rc"] == 0 and g["rc"] == 0) else None
        fdiff = check_frames(c["video"], g["video"], prim) if speed else None
        row = {"primitive": prim, "cairo_s": c["sec"], "manimgx_s": g["sec"],
               "speedup": speed, "frame_diff": round(fdiff, 5) if fdiff is not None else None,
               "cairo_rc": c["rc"], "manimgx_rc": g["rc"],
               "cairo_err": c["err"], "manimgx_err": g["err"]}
        rows.append(row)
        print(f"[bench] {json.dumps(row)}")

    if dry:
        return 0
    wins = sum(1 for r in rows if (r["speedup"] or 0) >= SPEEDUP_MIN)
    measured = [r["frame_diff"] for r in rows if r["frame_diff"] is not None]
    frames_ok = ffmpeg_ok and len(measured) == len(rows) and \
        all(d < FRAME_DIFF_MAX for d in measured)
    verdict = verdict_of(wins, len(rows), frames_ok, gx_ok)

    report = {"schema_version": SCHEMA_VERSION, "rows": rows, "wins": wins,
              "frames_ok": frames_ok, "installable": gx_ok, "ffmpeg": ffmpeg_ok,
              "verdict": verdict}
    (OUT / "bench_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "bench_report.md").write_text(
        "| primitive | cairo s | manimgx s | speedup | frame diff |\n"
        "|---|---|---|---|---|\n"
        + "\n".join(f"| {r['primitive']} | {r['cairo_s']} | {r['manimgx_s']} | "
                    f"{r['speedup']} | {r['frame_diff']} |" for r in rows)
        + f"\n\n**Verdict (vs pre-registered rule):** {verdict}\n", encoding="utf-8")
    ledger_append({"op": "bench_render_backends", "schema_version": SCHEMA_VERSION,
                   "verdict": verdict, "wins": wins, "frames_ok": frames_ok,
                   "installable": gx_ok, "iso_ts": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                                  time.gmtime())})
    if as_json:
        print(json.dumps(report))
    print("\n", verdict, "\n→ distill into THINK.md §4/§5 (CODEX step 6-7)")
    if baseline_broken:
        print("[bench] FAIL: the cairo baseline itself failed a render — "
              "fix the ruler before trusting any verdict")
        return 1
    if not gx_ok or not ffmpeg_ok:
        return 2
    return 0

# ---------------------------------------------------------------- self-witnesses
def _write_p6(path, w, h, rgb):
    body = b"P6\n%d %d\n255\n" % (w, h) + bytes(rgb)
    Path(path).write_bytes(body)

SELFTEST = [
    ("verdict ADOPT needs all three clauses", lambda:
        verdict_of(2, 3, True, True).startswith("ADOPT")),
    ("verdict REJECT on speedup shortfall", lambda:
        verdict_of(1, 3, True, True).startswith("REJECT")),
    ("verdict REJECT without frame witness", lambda:
        verdict_of(3, 3, False, True).startswith("REJECT")),
    ("verdict REJECT when not installable", lambda:
        verdict_of(3, 3, True, False).startswith("REJECT")),
    ("speedup needs two honest renders", lambda:
        speedup_of(10, 2) == 5.0 and speedup_of(10, 0) is None
        and speedup_of(None, 2) is None),
    ("scene template is seeded and deterministic", lambda:
        SCENE.format(prim="particle_gas") == SCENE.format(prim="particle_gas")
        and "random.seed(7)" in SCENE),
]

def selftest():
    bad = 0
    tmp = OUT / "_selftest"
    tmp.mkdir(parents=True, exist_ok=True)
    # frame-ruler witnesses on synthetic PPMs
    _write_p6(tmp / "a.ppm", 2, 1, [0, 0, 0, 255, 255, 255])
    _write_p6(tmp / "a2.ppm", 2, 1, [0, 0, 0, 255, 255, 255])
    _write_p6(tmp / "b.ppm", 2, 1, [12, 0, 0, 255, 243, 255])   # mean diff 24/6 = 4 → 4/255
    _write_p6(tmp / "c.ppm", 1, 2, [0] * 6)                     # shape mismatch
    cases = SELFTEST + [
        ("identical frames diff to 0", lambda: frame_diff_ppm(tmp / "a.ppm", tmp / "a2.ppm") == 0.0),
        ("known frame diff is exact", lambda: abs(frame_diff_ppm(tmp / "a.ppm", tmp / "b.ppm") - 4 / 255) < 1e-9),
        ("shape mismatch fails closed to 1.0", lambda: frame_diff_ppm(tmp / "a.ppm", tmp / "c.ppm") == 1.0),
    ]
    for i, (name, fn) in enumerate(cases):
        try:
            ok = bool(fn())
        except Exception:
            ok = False
        if not ok:
            bad += 1
        print(f"[selftest] {name}: {'ok' if ok else 'DRIFT'}")
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    print(f"[selftest] {len(cases) - bad}/{len(cases)} passed")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
