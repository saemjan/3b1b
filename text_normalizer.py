#!/usr/bin/env python3
"""text_normalizer.py — narration text gate for XTTS (engine 1/N).

Factory role (README §4.2):
    raw audio_script -> normalize() -> spoken English -> XTTS-v2 -> master -> ledger

Contract:
    * pure + deterministic + stdlib-only (same input -> same output forever)
    * ships a frozen self-witness: selftest() -> [(name, ok, detail)]
      so tools/engine_check.py and golden fixtures can prove no-drift (A5).

Fixes vs previous revision: F1..F10 from the audit (space after "power of",
space-optional operators, general number->words, extended units/symbols,
LaTeX frac/sqrt, abbreviation-safe chunking, word-aware hard wrap,
uppercase Greek, spoken-word-count helper for the duration gates).
"""
from __future__ import annotations

import re

# --------------------------------------------------------------------------
# number -> spoken words (F3)
# --------------------------------------------------------------------------
_ONES = ["", "one", "two", "three", "four", "five", "six", "seven", "eight",
         "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
         "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
         "eighty", "ninety"]
_SCALE = ["", "thousand", "million", "billion", "trillion"]
_DIGIT_WORDS = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
                "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"}


def _chunk_words(c: int) -> str:
    out = []
    if c >= 100:
        out.append(_ONES[c // 100] + " hundred")
        c %= 100
    if c >= 20:
        t = _TENS[c // 10]
        if c % 10:
            t += " " + _ONES[c % 10]
        out.append(t)
    elif c:
        out.append(_ONES[c])
    return " ".join(out)


def int_to_words(n: int) -> str:
    if n == 0:
        return "zero"
    if n < 0:
        return "minus " + int_to_words(-n)
    parts, i = [], 0
    while n:
        c = n % 1000
        if c:
            w = _chunk_words(c)
            if _SCALE[i]:
                w += " " + _SCALE[i]
            parts.append(w)
        n //= 1000
        i += 1
    return " ".join(reversed(parts))


# --------------------------------------------------------------------------
# spoken replacements
# --------------------------------------------------------------------------
_ABBREV = [  # before any sentence logic (F7)
    (r"\be\.g\.\s*", "for example, "), (r"\bi\.e\.\s*", "that is, "),
    (r"\betc\.\s*", "and so on. "), (r"\bvs\.\s*", "versus "),
    (r"\bEq\.\s*", "Equation "), (r"\bEqs\.\s*", "Equations "),
    (r"\bFig\.\s*", "Figure "), (r"\bNo\.\s*", "Number "),
    (r"\bapprox\.\s*", "approximately "), (r"\bcf\.\s*", "compare "),
]

_LATEX_NAMED = r"(alpha|beta|gamma|Gamma|delta|Delta|epsilon|zeta|eta|theta|Theta|iota|kappa|lambda|Lambda|mu|nu|xi|Xi|pi|Pi|rho|sigma|Sigma|tau|upsilon|phi|Phi|chi|psi|Psi|omega|Omega)"

_SYMBOLS = [  # order matters: longer first (F6)
    ("°C", " degrees celsius "), ("≠", " is not equal to "),
    ("≈", " is approximately "), ("≤", " is less than or equal to "),
    ("≥", " is greater than or equal to "), ("±", " plus or minus "),
    ("∞", " infinity "), ("∛", " cube root of "), ("√", " square root of "),
    ("∫", " the integral of "), ("∂", " partial "), ("∝", " is proportional to "),
    ("→", " tends to "), ("·", " times "), ("−", " minus "),
    ("Ω", " ohms "), ("°", " degrees "), ("%", " percent "),
    ("µ", " micro "), ("″", " double prime "), ("′", " prime "),
]

_GREEK = {  # F9: both cases
    "α": "alpha", "β": "beta", "γ": "gamma", "Γ": "gamma", "δ": "delta",
    "Δ": "delta", "ε": "epsilon", "ζ": "zeta", "η": "eta", "θ": "theta",
    "Θ": "theta", "ι": "iota", "κ": "kappa", "λ": "lambda", "Λ": "lambda",
    "μ": "mu", "ν": "nu", "ξ": "xi", "Ξ": "xi", "π": "pi", "Π": "pi",
    "ρ": "rho", "σ": "sigma", "Σ": "sigma", "τ": "tau", "υ": "upsilon",
    "φ": "phi", "Φ": "phi", "χ": "chi", "ψ": "psi", "Ψ": "psi",
    "ω": "omega", "Ω": "omega",
}

_SUP = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
        "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "⁻": "-"}

_UNITS = [  # ordered: compound -> prefixed -> bare (F4)
    (r"(\d+(?:\.\d+)?)\s*m/s\^2\b", "meters per second squared"),
    (r"(\d+(?:\.\d+)?)\s*m/s²\b", "meters per second squared"),
    (r"(\d+(?:\.\d+)?)\s*m/s\b", "meters per second"),
    (r"(\d+(?:\.\d+)?)\s*km/h\b", "kilometers per hour"),
    (r"(\d+(?:\.\d+)?)\s*N/m\b", "newtons per meter"),
    (r"(\d+(?:\.\d+)?)\s*rad/s\b", "radians per second"),
    (r"(\d+(?:\.\d+)?)\s*°C\b", "degrees celsius"),
    (r"(\d+(?:\.\d+)?)\s*[µμ]m\b", "micrometers"),
    (r"(\d+(?:\.\d+)?)\s*mm\b", "millimeters"),
    (r"(\d+(?:\.\d+)?)\s*cm\b", "centimeters"),
    (r"(\d+(?:\.\d+)?)\s*km\b", "kilometers"),
    (r"(\d+(?:\.\d+)?)\s*nm\b", "nanometers"),
    (r"(\d+(?:\.\d+)?)\s*ms\b", "milliseconds"),
    (r"(\d+(?:\.\d+)?)\s*kg\b", "kilograms"),
    (r"(\d+(?:\.\d+)?)\s*mg\b", "milligrams"),
    (r"(\d+(?:\.\d+)?)\s*eV\b", "electron volts"),
    (r"(\d+(?:\.\d+)?)\s*GHz\b", "gigahertz"),
    (r"(\d+(?:\.\d+)?)\s*MHz\b", "megahertz"),
    (r"(\d+(?:\.\d+)?)\s*kHz\b", "kilohertz"),
    (r"(\d+(?:\.\d+)?)\s*Hz\b", "hertz"),
    (r"(\d+(?:\.\d+)?)\s*kPa\b", "kilopascals"),
    (r"(\d+(?:\.\d+)?)\s*Pa\b", "pascals"),
    (r"(\d+(?:\.\d+)?)\s*kW\b", "kilowatts"),
    (r"(\d+(?:\.\d+)?)\s*mV\b", "millivolts"),
    (r"(\d+(?:\.\d+)?)\s*dB\b", "decibels"),
    (r"(\d+(?:\.\d+)?)\s*m\b", "meters"),
    (r"(\d+(?:\.\d+)?)\s*s\b", "seconds"),
    (r"(\d+(?:\.\d+)?)\s*g\b", "grams"),
    (r"(\d+(?:\.\d+)?)\s*N\b", "newtons"),
    (r"(\d+(?:\.\d+)?)\s*J\b", "joules"),
    (r"(\d+(?:\.\d+)?)\s*K\b", "kelvin"),
    (r"(\d+(?:\.\d+)?)\s*W\b", "watts"),
    (r"(\d+(?:\.\d+)?)\s*V\b", "volts"),
    (r"(\d+(?:\.\d+)?)\s*T\b", "tesla"),
    (r"(\d+(?:\.\d+)?)\s*C\b", "coulombs"),
    (r"(\d+(?:\.\d+)?)\s*A\b", "amperes"),
    (r"(\d+(?:\.\d+)?)\s*%", "percent"),
    (r"(\d+(?:\.\d+)?)\s*°", "degrees"),
    (r"(\d+(?:\.\d+)?)\s*Ω", "ohms"),
]


# --------------------------------------------------------------------------
# normalize
# --------------------------------------------------------------------------
def normalize(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r"\s+", " ", text).strip()

    # 0. abbreviations -> spoken (F7)
    for pat, rep in _ABBREV:
        t = re.sub(pat, rep, t)

    # 1. pauses
    t = t.replace(" — ", ", ").replace(" – ", ", ").replace("--", ", ")

    # 2. LaTeX, structured first (F5)
    t = re.sub(r"\\frac\s*\{([^}]*)\}\s*\{([^}]*)\}", r"(\1 over \2)", t)
    t = re.sub(r"\\sqrt\s*\{([^}]*)\}", r"(square root of \1)", t)
    t = re.sub(r"\\(" + _LATEX_NAMED + r")\b",
               lambda m: " " + m.group(1).lower() + " ", t)
    t = re.sub(r"\\(times|cdot)\b", " times ", t)
    t = re.sub(r"\\div\b", " divided by ", t)
    t = re.sub(r"\\(approx|simeq)\b", " is approximately ", t)
    t = re.sub(r"\\(leq|le)\b", " is less than or equal to ", t)
    t = re.sub(r"\\(geq|ge)\b", " is greater than or equal to ", t)
    t = re.sub(r"\\(neq|ne)\b", " is not equal to ", t)
    t = re.sub(r"\\infty\b", " infinity ", t)
    t = re.sub(r"\\pm\b", " plus or minus ", t)
    t = re.sub(r"\\propto\b", " is proportional to ", t)
    t = re.sub(r"\\(to|rightarrow)\b", " tends to ", t)

    # 3. superscripts -> ^n, drop subscripts
    t = re.sub(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+",
               lambda m: "^" + "".join(_SUP[c] for c in m.group(0)), t)
    t = re.sub(r"_\{?[^}\s]*\}?", " ", t)

    # 4. remaining macros / braces
    t = re.sub(r"\\[a-zA-Z]+", " ", t)
    t = re.sub(r"[{}]", " ", t)

    # 5. unicode symbols (F6), then Greek (F9)
    for lit, rep in _SYMBOLS:
        if lit in t:
            t = t.replace(lit, rep)
    for lit, rep in _GREEK.items():
        if lit in t:
            t = t.replace(lit, " " + rep + " ")

    # 6. scientific notation, space fixed (F1), exponent spoken
    def _sci(m):
        mant = m.group(1)
        e = int(m.group(2))
        ew = ("minus " + int_to_words(-e)) if e < 0 else int_to_words(e)
        return f"{mant} times ten to the power of {ew}"
    t = re.sub(r"(\d+(?:\.\d+)?)\s*[×xX]\s*10\^?(-?\d+)", _sci, t)

    # 7. units (F4)
    for pat, rep in _UNITS:
        t = re.sub(pat, lambda m, r=rep: f"{m.group(1)} {r}", t)

    # 8. plain fractions and ranges
    t = re.sub(r"(?<=\d),(?=\d)", "", t)                 # 1,234 -> 1234
    t = re.sub(r"(\d+)\s*/\s*(\d+)", r"(\1 over \2)", t)  # 1/2
    t = re.sub(r"(\d)\s*-\s*(\d)", r"\1 to \2", t)        # 3-5 -> 3 to 5

    # 9. operators, space-optional (F2)
    t = re.sub(r"={2,}", " equals ", t)
    t = re.sub(r"\s*=\s*", " equals ", t)
    t = re.sub(r"\s*\+\s*", " plus ", t)
    t = re.sub(r"\s*×\s*", " times ", t)
    t = re.sub(r"\s*÷\s*", " divided by ", t)
    t = re.sub(r"(?<=\s)-(?=\s)", " minus ", t)
    t = re.sub(r"(?<![\w])-(?=\d)", "minus ", t)

    # 10. powers
    t = re.sub(r"\^\s*2\b", " squared ", t)
    t = re.sub(r"\^\s*3\b", " cubed ", t)
    t = re.sub(r"\^\s*\{?(-?\d+)\}?",
               lambda m: " to the power of " + int_to_words(int(m.group(1))) + " ", t)
    t = t.replace("^", " ")

    # 11. numbers -> words (F3)
    t = re.sub(r"\b(\d+)\.(\d+)\b",
               lambda m: int_to_words(int(m.group(1))) + " point " +
                         " ".join(_DIGIT_WORDS[d] for d in m.group(2)), t)
    t = re.sub(r"\b\d+\b", lambda m: int_to_words(int(m.group(0))), t)

    # 12. typography cleanup
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s+([,.;:!?)])", r"\1", t)
    t = re.sub(r"\(\s+", "(", t)
    t = re.sub(r"\s+\)", ")", t)
    t = t.strip()
    if t and t[-1] not in ".!?":
        t += "."
    return t


def spoken_word_count(text: str) -> int:
    """Word count of what XTTS will actually say (F10)."""
    return len(normalize(text).split())


# --------------------------------------------------------------------------
# chunker (F7/F8)
# --------------------------------------------------------------------------
def _wrap(s: str, max_chars: int):
    cur = ""
    for w in s.split():
        cand = (cur + " " + w).strip()
        if len(cand) > max_chars and cur:
            yield cur
            cur = w
        else:
            cur = cand
    if cur:
        yield cur


def chunk_for_xtts(text: str, max_chars: int = 280) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", normalize(text).strip())
    chunks, cur = [], ""
    for s in sentences:
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

    final: list[str] = []
    for c in chunks:
        if len(c) <= max_chars:
            final.append(c)
            continue
        for piece in re.split(r"(?<=[,;])\s+", c):
            if len(piece) <= max_chars:
                final.append(piece)
            else:                      # F8: word-aware hard wrap
                final.extend(_wrap(piece, max_chars))
    return final or [text.strip()]


# --------------------------------------------------------------------------
# frozen witness (A5): engine_check / golden call this
# --------------------------------------------------------------------------
def selftest():
    checks = []

    def want(name, got, exp):
        checks.append((name, got == exp, f"got={got!r} want={exp!r}"))

    def ok(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    want("sci-space(F1)", normalize("2 x 10^3"),
         "two times ten to the power of three.")
    want("frac(F5)", normalize(r"\frac{1}{2}"), "(one over two).")
    want("ops-no-space(F2)", normalize("E=mc^2"), "E equals m c squared.")
    want("units(F4)", normalize("3.5 m"), "three point five meters.")
    want("percent", normalize("50%"), "fifty percent.")
    want("range", normalize("2-3 s"), "two to three seconds.")
    want("big-int(F3)", normalize("2025"), "two thousand twenty five.")
    ok("no-digits-left",
       not any(ch.isdigit() for ch in
               normalize("E = 9.81 m/s^2, v = 3 x 10^8 m/s, T = 300 K, f = 50 Hz")),
       "digits leaked into spoken text")
    ok("determinism", normalize("a = 1 m/s^2") == normalize("a = 1 m/s^2"))
    long_s = "word " * 120
    ok("chunk-bound(F8)", all(len(c) <= 280 for c in chunk_for_xtts(long_s)),
       "chunk exceeded max_chars")
    ok("abbrev(F7)", len(chunk_for_xtts("Eq. 4 shows e.g. masses. Fig. 1 too.")) >= 1
       and "Eq." not in normalize("Eq. 4"), "abbreviation leaked")
    return checks


if __name__ == "__main__":
    import sys
    fails = 0
    for name, good, detail in selftest():
        print(f"[{'ok ' if good else 'FAIL'}] {name} {detail if not good else ''}")
        fails += 0 if good else 1
    if sys.argv[1:]:
        raw = " ".join(sys.argv[1:])
        n = normalize(raw)
        print(f"IN : {raw}\nOUT: {n}  ({spoken_word_count(raw)} spoken words)")
        for i, c in enumerate(chunk_for_xtts(n), 1):
            print(f"  chunk {i} ({len(c)} chars): {c}")
    sys.exit(1 if fails else 0)
