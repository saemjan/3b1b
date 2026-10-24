#!/usr/bin/env python3
"""
Visual QA: Checks that a rendered video is not empty or broken.

This is the second gate in the honest pipeline. After rendering, this checks:
1. MP4 file exists and is not corrupt
2. Video duration is reasonable (> 1 second)
3. At least 10 frames are non-empty (not all black)

Returns: (ok: bool, issues: list[str])

Usage:
    from tools.visual_qa import check_video
    ok, issues = check_video(Path("output_shorts/my_video_final.mp4"))
    if not ok:
        print(f"Visual QA failed: {issues}")
"""

import subprocess
import json
from pathlib import Path
from typing import Tuple, List


def check_video(mp4_path: Path, min_non_empty_frames: int = 10) -> Tuple[bool, List[str]]:
    """
    Check that a rendered video is not empty or broken.
    
    Args:
        mp4_path: Path to the MP4 file
        min_non_empty_frames: Minimum number of non-empty frames required
    
    Returns:
        (ok, issues) where ok is True if QA passed,
        and issues is a list of error messages.
    """
    issues = []
    
    # 1. Check file exists
    if not mp4_path.exists():
        return False, [f"MP4 file does not exist: {mp4_path}"]
    
    # 2. Check file size (corrupt files are often tiny)
    file_size = mp4_path.stat().st_size
    if file_size < 1024:  # Less than 1 KB
        issues.append(f"MP4 file too small: {file_size} bytes (likely corrupt)")
        return False, issues
    
    # 3. Get video duration
    duration = get_duration(mp4_path)
    if duration is None:
        issues.append("Could not read video duration (file may be corrupt)")
        return False, issues
    
    if duration < 1.0:
        issues.append(f"Video too short: {duration:.2f}s (expected > 1s)")
        return False, issues
    
    # 4. Extract 10 evenly-spaced frames and check if they're non-empty
    frames = []
    for i in range(10):
        t = duration * i / 10
        frame_path = mp4_path.parent / f"qa_frame_{i}.jpg"
        
        cmd = [
            "ffmpeg", "-ss", str(t), "-i", str(mp4_path),
            "-vframes", "1", "-q:v", "2", str(frame_path),
            "-y", "-loglevel", "error"
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            if frame_path.exists():
                frames.append(frame_path)
        except subprocess.CalledProcessError:
            issues.append(f"Failed to extract frame at t={t:.2f}s")
    
    # 5. Check if frames are non-empty (not all black)
    non_empty = 0
    for frame in frames:
        if is_non_empty(frame):
            non_empty += 1
        frame.unlink()  # cleanup
    
    if non_empty < min_non_empty_frames:
        issues.append(
            f"Only {non_empty}/10 frames are non-empty "
            f"(possible render failure or empty scene)"
        )
    
    return len(issues) == 0, issues


def get_duration(mp4_path: Path) -> float:
    """
    Get video duration in seconds using ffprobe.
    
    Returns:
        Duration in seconds, or None if ffprobe fails.
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(mp4_path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return None


def is_non_empty(image_path: Path) -> bool:
    """
    Check if image is not all black (mean pixel value > 5).
    
    Args:
        image_path: Path to the image file
    
    Returns:
        True if the image has content, False if it's all black.
    """
    try:
        # Try PIL + numpy if available
        from PIL import Image
        import numpy as np
        
        img = Image.open(image_path).convert("RGB")
        arr = np.array(img)
        
        # Mean pixel value > 5 means not all black
        # (black is 0,0,0; typical content has mean > 20)
        return arr.mean() > 5
    
    except ImportError:
        # Fallback: check file size (black frames are small after JPEG compression)
        # A 1080x1920 black frame is ~10-20 KB; content is 50-200 KB
        return image_path.stat().st_size > 10000


def measure_lufs(audio_path: Path) -> float:
    """
    Measure audio loudness in LUFS using ffmpeg.
    
    Args:
        audio_path: Path to the audio file (WAV or MP3)
    
    Returns:
        Loudness in LUFS, or None if measurement fails.
    """
    cmd = [
        "ffmpeg", "-i", str(audio_path),
        "-af", "loudnorm=print_format=json",
        "-f", "null", "-"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        # ffmpeg writes the JSON to stderr
        output = result.stderr
        
        # Find the JSON block in the output
        json_start = output.rfind("{")
        json_end = output.rfind("}") + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = output[json_start:json_end]
            data = json.loads(json_str)
            
            # input_i is the input integrated loudness in LUFS
            return float(data.get("input_i", -70.0))
        
        return None
    
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError):
        return None


def main():
    """Test the visual QA with a sample video."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python visual_qa.py <video.mp4>")
        sys.exit(1)
    
    mp4_path = Path(sys.argv[1])
    ok, issues = check_video(mp4_path)
    
    print(f"Visual QA {'passed' if ok else 'failed'}")
    if issues:
        print("Issues:")
        for issue in issues:
            print(f"  - {issue}")
    
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
