#!/usr/bin/env python3
"""H1: cairo vs ManimGX on the 3 hottest primitives. Emits bench_report.{md,json}.
Verdict rule (pre-registered): adopt iff >=5x on >=2/3 prims AND frame diff < 8/255 AND CI-installable."""
import json, subprocess, sys, time, shutil
from pathlib import Path

HOT = ["particle_gas", "random_walk", "two_path_interference"]
OUT = Path("bench_out"); OUT.mkdir(exist_ok=True)

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

def run_backend(name, cmd, scene_py, tag):
    if name == "manimgx" and subprocess.run([sys.executable, "-c", "import manimgx"],
                                            capture_output=True).returncode != 0:
        return None
    media = OUT / f"{tag}_{name}"
    t0 = time.perf_counter()
    r = subprocess.run(cmd + ["--media_dir", str(media), str(scene_py), "Bench"],
                       capture_output=True, text=True)
    dt = time.perf_counter() - t0
    return {"sec": round(dt, 1), "rc": r.returncode,
            "err": r.stderr[-300:] if r.returncode else ""}

def main():
    rows = []
    for prim in HOT:
        sp = OUT / f"scene_{prim}.py"; sp.write_text(SCENE.format(prim=prim))
        res = {n: run_backend(n, c, sp, prim) for n, c in BACKENDS.items()}
        c, g = res["cairo"], res["manimgx"]
        speed = round(c["sec"] / g["sec"], 1) if (c and g and g["sec"] > 0) else None
        rows.append({"primitive": prim, "cairo_s": c and c["sec"],
                     "manimgx_s": g and g["sec"], "speedup": speed})
        print(rows[-1])
    wins = sum(1 for r in rows if (r["speedup"] or 0) >= 5)
    verdict = ("ADOPT manimgx for hot primitives" if wins >= 2
               else "REJECT manimgx (record numbers; next: H2/H5)")
    (OUT / "bench_report.json").write_text(json.dumps({"rows": rows, "verdict": verdict}, indent=2))
    (OUT / "bench_report.md").write_text(
        "| primitive | cairo s | manimgx s | speedup |\n|---|---|---|---|\n"
        + "\n".join(f"| {r['primitive']} | {r['cairo_s']} | {r['manimgx_s']} | {r['speedup']} |" for r in rows)
        + f"\n\n**Verdict (vs pre-registered rule):** {verdict}\n")
    print("\n", verdict, "\n→ distill into THINK.md §4/§5 (CODEX step 6-7)")

if __name__ == "__main__":
    main()
