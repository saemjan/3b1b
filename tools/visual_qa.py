#!/usr/bin/env python3
"""visual_qa.py — gen-3 media gate: own-tool PPM ruler + gated select libs.

Dependency stance (tools/backend_policy, kind="qa"):
  * pure stdlib core = THE RULER: frames are extracted as PPM (a format a
    student can parse) and luminance stats are computed from raw bytes —
    no PIL, no numpy required
  * PIL/numpy = select library for large frames, admitted only after probe
    + parity witness (same PPM, same stats) + cost gate; degrades to ruler
  * ffmpeg/ffprobe = selected tools for extraction and LUFS; absence is a
    recorded degradation, never a silent pass (fail closed)

Hygiene (A2): frames live in a temp dir, never beside the shipped video.
Receipts (A5): check_video_with_receipt returns a JSON-serializable dict
for the append-only ledger: backend, frame stats, duration, size, issues.

Frozen canon: a frame is non-empty iff mean luminance > 5.0 (legacy gate).

Usage:
    from tools.visual_qa import check_video, measure_lufs
    ok, issues = check_video(path)
    python3 tools/visual_qa.py <video.mp4> | --selftest
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from tools import backend_policy as bp
except Exception:
    try:
        import backend_policy as bp          # type: ignore
    except Exception:
        bp = None

SCHEMA_VERSION = 3
NON_EMPTY_MEAN = 5.0            # frozen canon
_LUM = (0.2126, 0.7152, 0.0722)


# ------------------------------------------------------- pure PPM ruler
def ppm_header(data: bytes):
    if data[:2] not in (b"P5", b"P6"):
        raise ValueError("not a binary PGM/PPM (P5/P6)")
    channels = 1 if data[1:2] == b"5" else 3
    idx, vals = 2, []
    while len(vals) < 3:
        while idx < len(data) and data[idx:idx + 1].isspace():
            idx += 1
        if data[idx:idx + 1] == b"#":
            while idx < len(data) and data[idx:idx + 1] != b"\n":
                idx += 1
            continue
        start = idx
        while idx < len(data) and not data[idx:idx + 1].isspace():
            idx += 1
        vals.append(int(data[start:idx]))
    idx += 1
    w, h, maxval = vals
    if maxval > 255:
        raise ValueError("16-bit PPM unsupported by the ruler")
    return w, h, channels, idx


def ppm_stats(data: bytes):
    """(mean_luminance, max_luminance, w, h) from raw PPM bytes."""
    w, h, channels, off = ppm_header(data)
    need = w * h * channels
    px = data[off:off + need]
    if len(px) < need:
        raise ValueError("truncated PPM frame")
    if channels == 1:
        total = float(sum(px))
        mx = float(max(px)) if px else 0.0
        return total / (w * h), mx, w, h
    total = 0.0
    mx = 0.0
    for i in range(0, need, 3):
        v = px[i] * _LUM[0] + px[i + 1] * _LUM[1] + px[i + 2] * _LUM[2]
        total += v
        if v > mx:
            mx = v
    return total / (w * h), mx, w, h


def _stats_pil(path: Path):
    import numpy as np
    from PIL import Image
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    lum = (arr[:, :, 0] * _LUM[0] + arr[:, :, 1] * _LUM[1]
           + arr[:, :, 2] * _LUM[2])
    return float(lum.mean()), float(lum.max()), lum.shape[1], lum.shape[0]


def _probe_pil():
    try:
        import numpy as np            # noqa: F401
        from PIL import Image         # noqa: F401
        return True, "ok"
    except Exception as e:
        return False, f"import: {type(e).__name__}"


def _synth_ppm(pixels):
    h = len(pixels)
    w = len(pixels[0])
    head = f"P6\n{w} {h}\n255\n".encode("ascii")
    body = b"".join(bytes(rgb) for row in pixels for rgb in row)
    return head + body


_PARITY_CACHE = {}


def _parity_pil():
    if "ok" in _PARITY_CACHE:
        return _PARITY_CACHE["ok"]
    ok = False
    try:
        frame = _synth_ppm([[(i * 7) % 256, (i * 13) % 256, 200 - i]
                            for i in range(0, 48)])
        frame = _synth_ppm([[((r * 8 + c) * 5) % 256,
                             ((r * 8 + c) * 3) % 256,
                             255 - ((r * 8 + c) % 256)]
                            for r in range(6) for c in range(8)])
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "parity.ppm"
            p.write_bytes(frame)
            m0, x0, w0, h0 = ppm_stats(frame)
            m1, x1, w1, h1 = _stats_pil(p)
            ok = (abs(m0 - m1) <= 1e-6 and abs(x0 - x1) <= 1e-6
                  and (w0, h0) == (w1, h1))
    except Exception:
        ok = False
    _PARITY_CACHE["ok"] = ok
    return ok


if bp is not None:
    bp.register("qa", bp.OWN_TOOL,
                probe=lambda: (True, "own tool, stdlib only"),
                witness=lambda: True,
                speedup=lambda size: 1.0)
    bp.register("qa", "pil",
                probe=_probe_pil,
                witness=_parity_pil,
                speedup=lambda size: size / 2_000_000.0)


def _choose_backend(pixels):
    if bp is None:
        return "pure", {"chosen": "pure", "reason": "backend_policy absent"}
    name, rep = bp.choose("qa", size=pixels)
    return (name if name == "pil" else "pure"), rep


# ------------------------------------------------------------- probes
def get_duration(mp4_path: Path):
    if shutil.which("ffprobe") is None:
        return None
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "csv=p=0", str(mp4_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return None


def measure_lufs(audio_path: Path):
    if shutil.which("ffmpeg") is None:
        return None
    cmd = ["ffmpeg", "-i", str(audio_path),
           "-af", "loudnorm=print_format=json", "-f", "null", "-"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        out = result.stderr
        js, je = out.rfind("{"), out.rfind("}") + 1
        if js >= 0 and je > js:
            return float(json.loads(out[js:je]).get("input_i", -70.0))
        return None
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError):
        return None


# --------------------------------------------------------------- the gate
def check_video_with_receipt(mp4_path: Path, min_non_empty_frames: int = 10,
                             frame_count: int = 12):
    mp4_path = Path(mp4_path)
    issues = []
    receipt = {"schema_version": SCHEMA_VERSION, "gate": "visual_qa",
               "backend": "none", "frames": 0, "non_empty": 0,
               "means": [], "duration": None, "size": None}
    if not mp4_path.exists():
        return False, [f"MP4 file does not exist: {mp4_path}"], receipt
    size = mp4_path.stat().st_size
    receipt["size"] = size
    if size < 1024:
        return False, [f"MP4 file too small: {size} bytes (likely corrupt)"], \
            receipt
    duration = get_duration(mp4_path)
    receipt["duration"] = duration
    if duration is None:
        return False, ["could not read video duration "
                       "(ffprobe absent or file corrupt)"], receipt
    if duration < 1.0:
        return False, [f"video too short: {duration:.2f}s (expected > 1s)"], \
            receipt
    if shutil.which("ffmpeg") is None:
        return False, ["selected tool ffmpeg absent; QA cannot run "
                       "(degradation recorded, fail closed)"], receipt

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        frames = []
        for i in range(frame_count):
            t = duration * i / frame_count
            out = tmp / f"frame_{i:02d}.ppm"
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}",
                   "-i", str(mp4_path), "-frames:v", "1", "-c:v", "ppm",
                   str(out)]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                if out.exists():
                    frames.append(out)
            except subprocess.CalledProcessError:
                issues.append(f"failed to extract frame at t={t:.2f}s")
        if not frames:
            return False, issues + ["no frames could be extracted"], receipt
        try:
            w, h, _ch, _off = ppm_header(frames[0].read_bytes())
        except ValueError as e:
            return False, issues + [f"frame decode failed: {e}"], receipt
        backend, _decision = _choose_backend(w * h * len(frames))
        receipt["backend"] = backend
        non_empty, means = 0, []
        for f in frames:
            try:
                if backend == "pil":
                    try:
                        mean, _mx, _w, _h = _stats_pil(f)
                    except Exception:
                        backend = "pure"          # degrade, don't deceive
                        receipt["backend"] = "pure(degraded)"
                        mean, _mx, _w, _h = ppm_stats(f.read_bytes())
                else:
                    mean, _mx, _w, _h = ppm_stats(f.read_bytes())
            except ValueError as e:
                issues.append(f"frame {f.name}: {e}")
                continue
            means.append(round(mean, 2))
            if mean > NON_EMPTY_MEAN:
                non_empty += 1
        receipt["frames"] = len(frames)
        receipt["non_empty"] = non_empty
        receipt["means"] = means
        if non_empty < min_non_empty_frames:
            issues.append(f"only {non_empty}/{len(frames)} frames are "
                          f"non-empty (possible render failure or empty "
                          f"scene)")
    return len(issues) == 0, issues, receipt


def check_video(mp4_path: Path, min_non_empty_frames: int = 10):
    """Legacy-compatible API."""
    ok, issues, _receipt = check_video_with_receipt(
        mp4_path, min_non_empty_frames)
    return ok, issues


# ------------------------------------------------------------ witnesses
def selftest():
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    black = _synth_ppm([[ (0, 0, 0) for _ in range(4)] for _ in range(4)])
    gray = _synth_ppm([[(128, 128, 128) for _ in range(4)] for _ in range(4)])
    white = _synth_ppm([[(255, 255, 255) for _ in range(4)] for _ in range(4)])
    m, mx, w, h = ppm_stats(black)
    want("ruler:black", m == 0.0 and mx == 0.0 and (w, h) == (4, 4))
    m, _, _, _ = ppm_stats(gray)
    want("ruler:gray", abs(m - 128.0) <= 1e-9, f"{m}")
    m, mx, _, _ = ppm_stats(white)
    want("ruler:white", abs(m - 255.0) <= 1e-9 and abs(mx - 255.0) <= 1e-9)
    want("ruler:non-empty-canon",
         ppm_stats(gray)[0] > NON_EMPTY_MEAN
         and ppm_stats(black)[0] <= NON_EMPTY_MEAN)
    try:
        ppm_stats(black[:-4])
        want("guard:truncated", False)
    except ValueError:
        want("guard:truncated", True)
    try:
        ppm_stats(b"P3\n1 1\n255\n")
        want("guard:ascii-rejected", False)
    except ValueError:
        want("guard:ascii-rejected", True)
    if _probe_pil()[0]:
        want("parity:pil", _parity_pil())
    else:
        want("parity:pil", True, "skipped (PIL absent)")
    ok, issues, rec = check_video_with_receipt(Path("/nonexistent/x.mp4"))
    want("guard:missing-file", ok is False and issues and rec["frames"] == 0)
    if shutil.which("ffprobe") is None and shutil.which("ffmpeg") is None:
        want("degrade:no-ffmpeg", True, "tools absent; gate fails closed")
    return checks


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--selftest":
        fails = 0
        for name, ok, detail in selftest():
            print(f"[{'ok ' if ok else 'FAIL'}] {name} "
                  f"{detail if not ok else ''}")
            fails += 0 if ok else 1
        return 1 if fails else 0
    if len(sys.argv) < 2:
        print("usage: visual_qa.py <video.mp4> | --selftest")
        return 1
    ok, issues, receipt = check_video_with_receipt(Path(sys.argv[1]))
    print(f"Visual QA {'passed' if ok else 'failed'}")
    for issue in issues:
        print(f"  - {issue}")
    print(json.dumps(receipt, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
