#!/usr/bin/env python3
"""
Word-Level Sync: Aligns beat timeline to word-level timings from forced alignment.

This replaces the crude "equal beat slices" approach with phoneme-accurate sync.
Uses stable-ts (or whisper-timestamped) to get word-level timings, then aligns
beats to the words they reference.

Usage:
    from tools.word_sync import align_beats
    
    beats = [
        {"type": "hook", "focus": "mass_1", "time": 0.0},
        {"type": "equation_reveal", "focus": "eq_1", "time": 5.0}
    ]
    
    aligned = align_beats(audio_path, beats, script)
    # Now beats have accurate "time" fields based on word timings
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional


def align_beats(
    audio_path: Path,
    beats: List[Dict[str, Any]],
    script: str,
    fallback_to_equal: bool = True
) -> List[Dict[str, Any]]:
    """
    Align beat timeline to word-level timings from forced alignment.
    
    Args:
        audio_path: Path to the audio file (WAV)
        beats: List of beat dicts with "type", "focus", and "time" fields
        script: The narration script text
        fallback_to_equal: If True, fall back to equal slicing if alignment fails
    
    Returns:
        Beats with adjusted "time" fields based on word timings.
    """
    # Get word timings
    word_timings = get_word_timings(audio_path, script)
    
    if not word_timings and fallback_to_equal:
        # Fall back to equal slicing
        return equal_slice_beats(beats, audio_path)
    
    aligned = []
    for beat in beats:
        beat = dict(beat)  # Copy to avoid mutating input
        
        # Extract the focus word from the beat
        focus_word = extract_focus_word(beat, script)
        
        if focus_word and word_timings:
            # Find the time this word is spoken
            t = find_word_time(focus_word, word_timings)
            if t is not None:
                beat["time"] = t
                beat["aligned"] = True
            else:
                beat["aligned"] = False
        else:
            beat["aligned"] = False
        
        aligned.append(beat)
    
    # For beats that couldn't be aligned, use equal slicing
    if fallback_to_equal:
        unaligned = [b for b in aligned if not b.get("aligned")]
        if unaligned:
            equal_times = equal_slice_times(len(unaligned), audio_path)
            for i, beat in enumerate(unaligned):
                beat["time"] = equal_times[i]
    
    return aligned


def get_word_timings(audio_path: Path, script: str) -> List[Dict[str, Any]]:
    """
    Get word-level timings using stable-ts or whisper-timestamped.
    
    Args:
        audio_path: Path to the audio file
        script: The narration script (for reference)
    
    Returns:
        List of word timing dicts: [{"word": "Consider", "start": 0.0, "end": 0.5}, ...]
        Returns empty list if forced alignment fails.
    """
    # Try stable-ts first
    try:
        import stable_whisper
        
        model = stable_whisper.load_model("base")
        result = model.transcribe(str(audio_path))
        
        words = []
        for seg in result.segments:
            for word in seg.words:
                words.append({
                    "word": word.word.strip().lower(),
                    "start": word.start,
                    "end": word.end
                })
        
        return words
    
    except ImportError:
        pass
    except Exception as e:
        print(f"[word_sync] stable-ts failed: {e}")
    
    # Try whisper-timestamped
    try:
        import whisper_timestamped as whisper
        
        model = whisper.load_model("base")
        result = whisper.transcribe(model, str(audio_path))
        
        words = []
        for seg in result["segments"]:
            for word in seg["words"]:
                words.append({
                    "word": word["text"].strip().lower(),
                    "start": word["start"],
                    "end": word["end"]
                })
        
        return words
    
    except ImportError:
        pass
    except Exception as e:
        print(f"[word_sync] whisper-timestamped failed: {e}")
    
    # Fall back to empty list
    print("[word_sync] No forced alignment library available (install stable-ts or whisper-timestamped)")
    return []


def extract_focus_word(beat: Dict[str, Any], script: str) -> Optional[str]:
    """
    Extract the focus word from a beat's focus field.
    
    Args:
        beat: Beat dict with "focus" field (e.g., "mass_1", "eq_1")
        script: The narration script
    
    Returns:
        The focus word to search for, or None if no focus.
    """
    focus = beat.get("focus")
    
    if not focus:
        return None
    
    # Convert focus ID to a search term
    # e.g., "mass_1" -> "mass", "eq_1" -> "equation"
    if focus.startswith("mass"):
        return "mass"
    elif focus.startswith("eq"):
        return "equation"
    elif focus.startswith("vector"):
        return "vector"
    elif focus.startswith("wave"):
        return "wave"
    elif focus.startswith("particle"):
        return "particle"
    elif focus.startswith("field"):
        return "field"
    else:
        # Generic: strip numbers and underscores
        word = re.sub(r"[_\d]", " ", focus).split()[0] if focus else None
        return word.lower() if word else None


def find_word_time(
    target_word: str,
    word_timings: List[Dict[str, Any]]
) -> Optional[float]:
    """
    Find the time a word is spoken in the word timings.
    
    Args:
        target_word: The word to search for (lowercase)
        word_timings: List of word timing dicts
    
    Returns:
        The start time of the word, or None if not found.
    """
    target_word = target_word.lower()
    
    # Exact match first
    for wt in word_timings:
        if wt["word"] == target_word:
            return wt["start"]
    
    # Partial match (word contains target)
    for wt in word_timings:
        if target_word in wt["word"]:
            return wt["start"]
    
    # Fuzzy match (target contains word)
    for wt in word_timings:
        if wt["word"] in target_word:
            return wt["start"]
    
    return None


def equal_slice_beats(
    beats: List[Dict[str, Any]],
    audio_path: Path
) -> List[Dict[str, Any]]:
    """
    Fall back to equal slicing if forced alignment fails.
    
    Args:
        beats: List of beat dicts
        audio_path: Path to the audio file
    
    Returns:
        Beats with "time" fields set to equal intervals.
    """
    times = equal_slice_times(len(beats), audio_path)
    
    aligned = []
    for i, beat in enumerate(beats):
        beat = dict(beat)
        beat["time"] = times[i]
        beat["aligned"] = False
        aligned.append(beat)
    
    return aligned


def equal_slice_times(n_beats: int, audio_path: Path) -> List[float]:
    """
    Generate equal time intervals for beats.
    
    Args:
        n_beats: Number of beats
        audio_path: Path to the audio file
    
    Returns:
        List of time values in seconds.
    """
    # Get audio duration
    duration = get_audio_duration(audio_path)
    
    if n_beats == 0:
        return []
    
    if n_beats == 1:
        return [duration / 2]
    
    # Equal intervals
    interval = duration / n_beats
    return [i * interval for i in range(n_beats)]


def get_audio_duration(audio_path: Path) -> float:
    """
    Get audio duration in seconds using ffprobe.
    
    Args:
        audio_path: Path to the audio file
    
    Returns:
        Duration in seconds, or 180.0 if ffprobe fails (default 3 minutes).
    """
    import subprocess
    
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(audio_path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return 180.0  # Default 3 minutes


def main():
    """Test the word sync with sample data."""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python word_sync.py <audio.wav> <beats.json>")
        sys.exit(1)
    
    audio_path = Path(sys.argv[1])
    beats_path = Path(sys.argv[2])
    
    with open(beats_path) as f:
        beats = json.load(f)
    
    script = "Consider a mass m falling from height h. The potential energy converts to kinetic energy."
    
    aligned = align_beats(audio_path, beats, script)
    
    print("Aligned beats:")
    for beat in aligned:
        print(f"  {beat['type']} at t={beat['time']:.2f}s (aligned={beat.get('aligned', False)})")


if __name__ == "__main__":
    main()
