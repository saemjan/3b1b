#!/usr/bin/env python3
"""text_normalizer.py — Prep narration text for XTTS."""
from __future__ import annotations
import re

_UNIT_AFTER_NUMBER = [
    (r"(\d+(?:\.\d+)?)\s*m/s\^2\b", r"\1 meters per second squared"),
    (r"(\d+(?:\.\d+)?)\s*m/s²\b",   r"\1 meters per second squared"),
    (r"(\d+(?:\.\d+)?)\s*m/s\b",    r"\1 meters per second"),
    (r"(\d+(?:\.\d+)?)\s*km/h\b",   r"\1 kilometers per hour"),
    (r"(\d+(?:\.\d+)?)\s*N/m\b",    r"\1 newtons per meter"),
    (r"(\d+(?:\.\d+)?)\s*rad/s\b",  r"\1 radians per second"),
    (r"(\d+(?:\.\d+)?)\s*kg\b",     r"\1 kilograms"),
    (r"(\d+(?:\.\d+)?)\s*N\b",      r"\1 newtons"),
    (r"(\d+(?:\.\d+)?)\s*J\b",      r"\1 joules"),
    (r"(\d+(?:\.\d+)?)\s*K\b",      r"\1 kelvin"),
    (r"(\d+(?:\.\d+)?)\s*W\b",      r"\1 watts"),
    (r"(\d+(?:\.\d+)?)\s*V\b",      r"\1 volts"),
    (r"(\d+(?:\.\d+)?)\s*Pa\b",     r"\1 pascals"),
    (r"(\d+(?:\.\d+)?)\s*GHz\b",    r"\1 gigahertz"),
    (r"(\d+(?:\.\d+)?)\s*MHz\b",    r"\1 megahertz"),
    (r"(\d+(?:\.\d+)?)\s*Hz\b",     r"\1 hertz"),
    (r"(\d+(?:\.\d+)?)\s*km\b",     r"\1 kilometers"),
    (r"(\d+(?:\.\d+)?)\s*cm\b",     r"\1 centimeters"),
    (r"(\d+(?:\.\d+)?)\s*mm\b",     r"\1 millimeters"),
    (r"(\d+(?:\.\d+)?)\s*nm\b",     r"\1 nanometers"),
    (r"(\d+(?:\.\d+)?)\s*A\b",      r"\1 amperes"),
]

NUM_WORDS = {
    "1200": "one thousand two hundred",
    "600": "six hundred", "300": "three hundred", "100": "one hundred",
    "90": "ninety", "80": "eighty", "70": "seventy",
    "60": "sixty", "50": "fifty", "40": "forty",
    "30": "thirty", "20": "twenty",
    "19": "nineteen", "18": "eighteen", "17": "seventeen",
    "16": "sixteen", "15": "fifteen", "14": "fourteen",
    "13": "thirteen", "12": "twelve", "11": "eleven",
    "10": "ten",
    "9": "nine", "8": "eight", "7": "seven", "6": "six",
    "5": "five", "4": "four", "3": "three", "2": "two",
    "1": "one", "0": "zero",
}

_DIGITS = {"0": "zero", "1": "one", "2": "two", "3": "three",
           "4": "four", "5": "five", "6": "six", "7": "seven",
           "8": "eight", "9": "nine"}

_GREEK = {
    "Δ": "delta", "δ": "delta", "π": "pi",    "Π": "pi",
    "θ": "theta", "ω": "omega", "Ω": "omega", "λ": "lambda",
    "μ": "mu",    "φ": "phi",   "Φ": "phi",   "ψ": "psi",   "Ψ": "psi",
    "α": "alpha", "β": "beta",  "γ": "gamma", "ε": "epsilon",
    "σ": "sigma", "τ": "tau",   "ρ": "rho",   "ν": "nu",
    "η": "eta",   "ζ": "zeta",  "ξ": "xi",
}


def normalize(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace(" — ", ", ").replace(" – ", ", ").replace("--", ", ")

    text = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", "", text)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = re.sub(r"[{}]", "", text)

    for sym, name in _GREEK.items():
        if sym in text:
            text = text.replace(sym, f" {name} ")

    def _sci(m):
        mantissa = m.group(1)
        exp = m.group(2).replace("-", " minus ")
        return f"{mantissa} times ten to the power of{exp}"
    text = re.sub(r"(\d+(?:\.\d+)?)\s*[×x]\s*10\^?(-?\d+)", _sci, text)

    for pattern, spoken in _UNIT_AFTER_NUMBER:
        text = re.sub(pattern, spoken, text)

    def _dec(m):
        w, f = m.group(1), m.group(2)
        return f"{NUM_WORDS.get(w, w)} point " + " ".join(_DIGITS[d] for d in f)
    text = re.sub(r"\b(\d+)\.(\d+)\b", _dec, text)

    text = re.sub(r"\b(\d+)\b",
                  lambda m: NUM_WORDS.get(m.group(0), m.group(0)),
                  text)

    text = (text.replace("^2", " squared")
                .replace("^3", " cubed")
                .replace(" = ", " equals ")
                .replace(" + ", " plus ")
                .replace(" × ", " times ")
                .replace(" ÷ ", " divided by "))

    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+,", ",", text)
    if text and text[-1] not in ".!?":
        text += "."
    return text.strip()


def chunk_for_xtts(text: str, max_chars: int = 280) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks, cur = [], ""
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        cand = (cur + " " + s).strip() if cur else s
        if len(cand) > max_chars and cur:
            chunks.append(cur)
            cur = s
        else:
            cur = cand
    if cur:
        chunks.append(cur)

    final = []
    for c in chunks:
        if len(c) <= max_chars:
            final.append(c)
            continue
        parts = re.split(r"(?<=[,;])\s+", c)
        sub = ""
        for p in parts:
            cand = (sub + " " + p).strip() if sub else p
            if len(cand) > max_chars and sub:
                final.append(sub)
                sub = p
            else:
                sub = cand
        if sub:
            final.append(sub)
    return final or [text.strip()]


if __name__ == "__main__":
    import sys
    raw = " ".join(sys.argv[1:]) or \
        "A block of 5 kg at 10 m/s^2 has N = 50 N and K = 300 K."
    n = normalize(raw)
    print(f"IN : {raw}\nOUT: {n}")
    for i, c in enumerate(chunk_for_xtts(n)):
        print(f"  chunk {i+1} ({len(c)} chars): {c}")
