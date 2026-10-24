#!/usr/bin/env python3
"""Append one distill line to THINK.md §3 (the run log).

v2.1 (after runs #161 and #168): arguments are OPTIONAL and every input
has a default, so a bare call can never IndexError again. Run #168 proved
the v1 file was still live and its crash was hidden by `|| true` — a
blind governance witness (R22). When defaults are used, this prints a
WARN line so the log itself records that the caller was implicit;
workflow v3.1 (which passes run# and gate explicitly and drops || true)
removes the warning.

    python3 tools/think_loop.py                    # fully defaulted
    python3 tools/think_loop.py 169 failure ci     # explicit

Defaults: run   = argv[1] or $GITHUB_RUN_NUMBER or last §3 row + 1
          gate  = argv[2] or $STUDIO_GATE or ("ci" if in CI else "local")
          render= $STUDIO_RENDER or "skipped"
          sigs  = $STUDIO_SIGS or "clean"
Line format matches existing §3 rows:
    #<run> gate=<g> render=<r> <date> wall=- sigs=<s> [note]
Append-only: inserted after the last '#<n>' row of §3.
"""
import os
import re
import sys
import time
from pathlib import Path

THINK = Path(__file__).resolve().parents[1] / "THINK.md"
ROW = re.compile(r"^#(\d+)\s")


def last_run(text):
    nums = [int(m.group(1)) for m in (ROW.match(l) for l in text.splitlines()) if m]
    return max(nums) if nums else 0


def main(run=None, gate=None, *note):
    text = THINK.read_text(encoding="utf-8") if THINK.exists() else "# THINK.md\n"
    in_ci = bool(os.environ.get("GITHUB_RUN_NUMBER"))
    defaulted = not (run and gate)
    run = int(run) if run else int(os.environ.get("GITHUB_RUN_NUMBER", "0")
                                   or last_run(text) + 1)
    gate = gate or os.environ.get("STUDIO_GATE") or ("ci" if in_ci else "local")
    render = os.environ.get("STUDIO_RENDER", "skipped")
    sigs = os.environ.get("STUDIO_SIGS", "clean")
    date = time.strftime("%Y-%m-%d")
    line = (f"#{run} gate={gate} render={render} {date} wall=- sigs={sigs}"
            + (" " + " ".join(note) if note else ""))
    lines = text.splitlines()
    idxs = [i for i, l in enumerate(lines) if ROW.match(l)]
    pos = (idxs[-1] + 1) if idxs else len(lines)
    lines.insert(pos, line)
    THINK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[think] appended: {line}")
    if defaulted:
        print("[think] WARN: caller passed no status; apply workflow v3.1 "
              "so gate/render arrive explicitly (R38)")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
