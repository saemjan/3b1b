#!/usr/bin/env python3
"""
Failure Ledger: Append-only record of render outcomes, primitive failures,
and audio measurements.

This is the machine cousin of THINK.md §3: replay the ledger and you get
the exact history of what worked and what didn't. The ledger tracks:
- Which primitives fail most often
- Which concepts produce empty scenes
- Audio LUFS measurements across renders
- Wall time and duration statistics

Usage:
    from tools.ledger import append, read, summarize
    
    # Append an outcome
    append({
        "video_id": "feynman_d1_01_atoms",
        "status": "ok",
        "duration_sec": 185.3,
        "audio_lufs": -14.2,
        "failed_primitives": [],
        "visual_qa_passed": True,
        "wall_sec": 923
    })
    
    # Read all entries
    entries = read()
    
    # Print summary
    summarize()
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict


LEDGER_PATH = Path("logs/render_ledger.jsonl")


def append(entry: Dict[str, Any]):
    """
    Append one outcome to the ledger.
    
    Args:
        entry: Dictionary with outcome data. Common fields:
            - video_id: str
            - status: "ok" | "error"
            - duration_sec: float
            - audio_lufs: float (measured LUFS)
            - failed_primitives: list[str]
            - visual_qa_passed: bool
            - wall_sec: float (wall time)
            - primitive_count: int (number of primitives in scene)
    """
    # Add timestamp
    entry["ts"] = time.time()
    entry["iso_ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(entry["ts"]))
    
    # Ensure logs directory exists
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Append to ledger
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read() -> List[Dict[str, Any]]:
    """
    Read all ledger entries.
    
    Returns:
        List of ledger entry dictionaries.
    """
    if not LEDGER_PATH.exists():
        return []
    
    out = []
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue
    
    return out


def summarize():
    """
    Print a summary of the ledger: most-failed primitives, worst LUFS,
    average duration, etc.
    """
    entries = read()
    
    if not entries:
        print("Ledger is empty.")
        return
    
    print(f"\n{'='*60}")
    print(f"RENDER LEDGER SUMMARY")
    print(f"{'='*60}")
    print(f"Total entries: {len(entries)}")
    print(f"Successful renders: {sum(1 for e in entries if e.get('status') == 'ok')}")
    print(f"Failed renders: {sum(1 for e in entries if e.get('status') == 'error')}")
    
    # Count primitive failures
    prim_failures = defaultdict(int)
    for e in entries:
        for prim in e.get("failed_primitives", []):
            prim_failures[prim] += 1
    
    if prim_failures:
        print(f"\nMost-failed primitives:")
        for prim, count in sorted(prim_failures.items(), key=lambda x: -x[1])[:10]:
            print(f"  {prim}: {count} failures")
    
    # Audio LUFS statistics
    lufs_values = [e.get("audio_lufs") for e in entries if "audio_lufs" in e]
    if lufs_values:
        print(f"\nAudio LUFS statistics:")
        print(f"  Min: {min(lufs_values):.1f} LUFS")
        print(f"  Max: {max(lufs_values):.1f} LUFS")
        print(f"  Mean: {sum(lufs_values)/len(lufs_values):.1f} LUFS")
        
        # Count how many are in the target range [-16, -12]
        in_range = sum(1 for v in lufs_values if -16 <= v <= -12)
        print(f"  In target range [-16, -12]: {in_range}/{len(lufs_values)}")
    
    # Duration statistics
    durations = [e.get("duration_sec") for e in entries if "duration_sec" in e]
    if durations:
        print(f"\nVideo duration statistics:")
        print(f"  Min: {min(durations):.1f}s")
        print(f"  Max: {max(durations):.1f}s")
        print(f"  Mean: {sum(durations)/len(durations):.1f}s")
    
    # Wall time statistics
    wall_times = [e.get("wall_sec") for e in entries if "wall_sec" in e]
    if wall_times:
        print(f"\nWall time statistics:")
        print(f"  Min: {min(wall_times):.1f}s ({min(wall_times)/60:.1f} min)")
        print(f"  Max: {max(wall_times):.1f}s ({max(wall_times)/60:.1f} min)")
        print(f"  Mean: {sum(wall_times)/len(wall_times):.1f}s ({sum(wall_times)/len(wall_times)/60:.1f} min)")
    
    # Visual QA pass rate
    qa_passed = [e.get("visual_qa_passed") for e in entries if "visual_qa_passed" in e]
    if qa_passed:
        pass_count = sum(1 for p in qa_passed if p)
        print(f"\nVisual QA pass rate: {pass_count}/{len(qa_passed)}")
    
    # Recent entries
    print(f"\nRecent entries (last 5):")
    for e in entries[-5:]:
        vid = e.get("video_id", "unknown")
        status = e.get("status", "unknown")
        ts = e.get("iso_ts", "unknown")
        print(f"  [{ts}] {vid}: {status}")
    
    print(f"{'='*60}\n")


def export_csv(output_path: Path):
    """
    Export ledger entries to CSV for analysis.
    
    Args:
        output_path: Path to write the CSV file
    """
    import csv
    
    entries = read()
    if not entries:
        print("Ledger is empty.")
        return
    
    # Collect all keys
    all_keys = set()
    for e in entries:
        all_keys.update(e.keys())
    
    # Sort keys for consistent column order
    fieldnames = sorted(all_keys)
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for e in entries:
            writer.writerow(e)
    
    print(f"Exported {len(entries)} entries to {output_path}")


def clear():
    """
    Clear the ledger (use with caution).
    """
    if LEDGER_PATH.exists():
        LEDGER_PATH.unlink()
        print("Ledger cleared.")
    else:
        print("Ledger is already empty.")


def main():
    """CLI interface for the ledger."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python ledger.py [summarize|export|clear]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "summarize":
        summarize()
    elif cmd == "export":
        output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("logs/ledger_export.csv")
        export_csv(output_path)
    elif cmd == "clear":
        clear()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
