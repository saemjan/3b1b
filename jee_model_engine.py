#!/usr/bin/env python3
"""jee_model_engine.py — Model Algorithm Engine for the JEE syllabus (PCM).

Constitutional placement (IR ladder):
  SIR  intent      concept id + audience (what must be understood)
  DIR  model       pure stdlib algorithms = THE RULER (this file)
  CIR  recipe      storyboard compiled from model output (adaptive)
  MIR  micro-ops   emitted primitives are already routed elsewhere,
                   except "concept_map", which this engine routes (contract v1)

Rules honoured:
  A0  every number on screen is computed by a model, never guessed
  A5  every concept ships frozen witnesses (closed forms / identities);
      generation FAILS CLOSED if a witness drifts
  teacher rule  truth frozen, representation alive: recipes reorder, re-voice,
      re-skin and re-quiz per seed/audience/genome; models never change
  dependency stance  stdlib only; nothing here needs numpy or manim at import

Usage:
  python3 jee_model_engine.py list
  python3 jee_model_engine.py row phys:shm --seed 11 --audience jee
  python3 jee_model_engine.py --selftest
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import text_normalizer as _TN
except Exception:
    _TN = None

AVOGADRO = 6.02214076e23
H_EV_S = 4.135667696e-15
HC_EV_NM = 1240.0
RYDBERG = 1.0973731568e7
R_GAS = 8.314462618
E_CH = 1.602176634e-19
H_PL = 6.62607015e-34
M_E = 9.1093837015e-31

REGISTRY: dict = {}


# ---------------------------------------------------------------- helpers
def _num(value, name, lo=None, hi=None):
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a finite number.")
    if not math.isfinite(out):
        raise ValueError(f"{name} must be a finite number.")
    if lo is not None and out < lo:
        raise ValueError(f"{name} must be >= {lo}.")
    if hi is not None and out > hi:
        raise ValueError(f"{name} must be <= {hi}.")
    return out


def _ok(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(1.0, abs(b)), f"{a!r} vs {b!r}"


def _spoken(script):
    if _TN is not None:
        try:
            return _TN.spoken_word_count(script)
        except Exception:
            pass
    return len(script.split())


class Concept:
    __slots__ = ("cid", "subject", "chapter", "title", "params",
                 "model", "witnesses", "recipe", "myth", "close")

    def __init__(self, cid, subject, chapter, title, params, model,
                 witnesses, recipe, myth="", close=""):
        self.cid, self.subject, self.chapter = cid, subject, chapter
        self.title, self.params = title, params
        self.model, self.witnesses, self.recipe = model, witnesses, recipe
        self.myth, self.close = myth, close
        REGISTRY[cid] = self


# ================================================================ PHYSICS
def _shm_model(p):
    w = math.sqrt(p["k"] / p["m"])
    return {"omega": w, "T": 2 * math.pi / w,
            "E": 0.5 * p["k"] * p["A"] ** 2, "vmax": p["A"] * w}


def _shm_wit(q, p):
    x = p["A"] / 2
    v = q["omega"] * math.sqrt(p["A"] ** 2 - x ** 2)
    e = 0.5 * p["k"] * x ** 2 + 0.5 * p["m"] * v ** 2
    return _ok(e, q["E"])


def _shm_recipe(q, p, rng):
    return {
        "facts": [
            f"A {p['m']:g} kg mass on a {p['k']:g} N/m spring oscillates at "
            f"omega = {q['omega']:g} rad per second.",
            f"The period is T = {q['T']:g} s and the total energy "
            f"E = {q['E']:g} J stays constant.",
        ],
        "visuals": [
            {"type": "graph", "expression": f"({p['A']})*cos({q['omega']:g}*x)",
             "x_range": [0, q["T"]], "role": "primary"},
            {"type": "energy_bar", "fraction": 0.25, "role": "accent"},
        ],
        "equations": ["x(t) = A cos(omega t)", f"omega = {q['omega']:g} rad/s",
                      f"E = (1/2) k A^2 = {q['E']:g} J"],
    }


Concept("phys:shm", "physics", "oscillations", "Simple harmonic motion",
        {"m": (0.1, 10, 1.0), "k": (1, 500, 100.0), "A": (0.05, 1, 0.2)},
        _shm_model, [("energy-conservation", _shm_wit)], _shm_recipe,
        myth="Many students think the energy vanishes at the mean position.",
        close="Kinetic and potential energy trade places; the total never moves.")


def _proj_model(p):
    v, g = p["v"], p["g"]
    return {"R45": v * v / g, "H": v * v / (2 * g), "T": 2 * v / g}


def _proj_wit(q, p):
    best, arg = -1.0, 0
    for deg in range(1, 90):
        r = p["v"] ** 2 * math.sin(math.radians(2 * deg)) / p["g"]
        if r > best:
            best, arg = r, deg
    return (arg == 45 and _ok(best, q["R45"], 1e-9)[0],
            f"argmax={arg} R={best!r}")


def _proj_recipe(q, p, rng):
    return {
        "facts": [
            f"Launch at {p['v']:g} m per second: the range peaks at 45 degrees "
            f"with R = {q['R45']:g} m.",
            f"Maximum height H = {q['H']:g} m, time of flight T = {q['T']:g} s.",
        ],
        "visuals": [
            {"type": "projectile_motion", "v0": p["v"], "angle": 45,
             "g": p["g"], "role": "primary"},
            {"type": "graph",
             "expression": f"({p['v']*p['v']}/ {p['g']:g})*sin(2*x)",
             "x_range": [0, 1.5708], "role": "accent"},
        ],
        "equations": ["R = v^2 sin(2 theta) / g", f"H = v^2 / (2 g) = {q['H']:g} m"],
    }


Concept("phys:projectile", "physics", "kinematics", "Projectile range optimum",
        {"v": (5, 60, 20.0), "g": (1, 20, 9.8)},
        _proj_model, [("range-max-at-45", _proj_wit)], _proj_recipe,
        myth="A higher angle always throws farther.",
        close="Beyond 45 degrees the range falls again; the sine decides.")


def _bank_model(p):
    theta = math.atan(p["v"] ** 2 / (p["r"] * p["g"]))
    return {"theta_deg": math.degrees(theta), "tan": p["v"] ** 2 / (p["r"] * p["g"])}


def _bank_wit(q, p):
    n_cos = p["g"]
    n_sin = p["v"] ** 2 / p["r"]
    return _ok(n_sin / n_cos, q["tan"])


def _bank_recipe(q, p, rng):
    return {
        "facts": [
            f"At {p['v']:g} m per second on a {p['r']:g} m curve, the road must "
            f"bank at {q['theta_deg']:g} degrees.",
            "Then the normal force alone supplies the centripetal pull.",
        ],
        "visuals": [
            {"type": "polygon", "points": [[-2, -1], [2, -1], [2, -1 + 4 * q["tan"] / (1 + q["tan"])]],
             "role": "field"},
            {"type": "vector", "start": [0, 0], "end": [0, 1.4], "role": "accent"},
            {"type": "vector", "start": [0, 0], "end": [1.2, 0], "role": "secondary"},
        ],
        "equations": ["tan(theta) = v^2 / (r g)",
                      f"theta = {q['theta_deg']:g} degrees"],
    }


Concept("phys:banking", "physics", "circular-motion", "Banked road angle",
        {"v": (5, 60, 20.0), "r": (20, 500, 100.0), "g": (1, 20, 9.8)},
        _bank_model, [("force-balance", _bank_wit)], _bank_recipe)


def _thermo_model(p):
    n, T1, T2, g = p["n"], p["T1"], p["T2"], p["gamma"]
    w_iso = n * R_GAS * T1 * math.log(p["V2"] / p["V1"])
    w_adia = n * R_GAS * (T1 - T2) / (g - 1)
    cv = R_GAS / (g - 1)
    u_iso = n * cv * (T2 - T1)
    return {"W_iso": w_iso, "W_adia": w_adia, "U_iso": u_iso,
            "eta": (w_iso + w_adia + u_iso) / max(w_iso, 1e-12)}


def _thermo_wit(q, p):
    cycle_du = 0.0 + (-q["W_adia"]) + q["U_iso"]
    return _ok(cycle_du, 0.0, 1e-9)


def _thermo_recipe(q, p, rng):
    return {
        "facts": [
            f"Isothermal step at {p['T1']:g} K does W = {q['W_iso']:g} J.",
            f"Adiabatic step adds {q['W_adia']:g} J; over the whole cycle "
            f"the internal energy returns to zero.",
        ],
        "visuals": [
            {"type": "graph", "expression": f"({p['n']:g}*8.314*{p['T1']:g})/x",
             "x_range": [p["V1"], p["V2"]], "role": "primary"},
            {"type": "energy_bar", "fraction": max(0.05, min(0.95, q["eta"])),
             "role": "accent"},
        ],
        "equations": ["W_iso = n R T ln(V2/V1)",
                      "W_adia = n R (T1 - T2)/(gamma - 1)", "cycle: delta U = 0"],
    }


Concept("phys:thermo_cycle", "physics", "thermodynamics", "Isotherm + adiabat cycle",
        {"n": (0.1, 5, 1.0), "T1": (200, 600, 400.0), "T2": (100, 500, 300.0),
         "V1": (0.5, 5, 1.0), "V2": (1, 10, 4.0), "gamma": (1.1, 2, 1.4)},
        _thermo_model, [("first-law-closure", _thermo_wit)], _thermo_recipe)


def _beats_model(p):
    return {"f_beat": abs(p["f1"] - p["f2"]), "f_car": (p["f1"] + p["f2"]) / 2}


def _beats_wit(q, p):
    t = 0.37
    direct = math.sin(2 * math.pi * p["f1"] * t) + math.sin(2 * math.pi * p["f2"] * t)
    env = 2 * math.cos(2 * math.pi * q["f_beat"] / 2 * t) * \
        math.sin(2 * math.pi * q["f_car"] * t)
    return _ok(direct, env, 1e-9)


def _beats_recipe(q, p, rng):
    return {
        "facts": [
            f"Two tones at {p['f1']:g} and {p['f2']:g} hertz beat "
            f"{q['f_beat']:g} times per second.",
            "The loudness swells with the envelope, not with either tone.",
        ],
        "visuals": [
            {"type": "graph",
             "expression": f"sin({2*math.pi*p['f1']:g}*x)+sin({2*math.pi*p['f2']:g}*x)",
             "x_range": [0, 2], "role": "primary"},
            {"type": "wave", "amplitude": 0.6, "frequency": q["f_beat"] / 2 + 0.2,
             "role": "accent"},
        ],
        "equations": ["f_beat = |f1 - f2|", f"f_beat = {q['f_beat']:g} Hz"],
    }


Concept("phys:beats", "physics", "waves", "Beats and envelope",
        {"f1": (1, 20, 6.0), "f2": (1, 20, 5.0)},
        _beats_model, [("sum-identity", _beats_wit)], _beats_recipe)


def _lens_model(p):
    inv_f = (p["n"] - 1) * (1 / p["R1"] - 1 / p["R2"])
    f = 1 / inv_f
    di = 1 / (1 / f - 1 / p["do"])
    return {"f": f, "di": di, "m": -di / p["do"]}


def _lens_wit(q, p):
    return _ok(1 / q["di"] - 1 / p["do"], 1 / q["f"])


def _lens_recipe(q, p, rng):
    return {
        "facts": [
            f"The lens maker formula gives f = {q['f']:g} cm.",
            f"An object at {p['do']:g} cm forms its image at {q['di']:g} cm "
            f"with magnification {q['m']:g}.",
        ],
        "visuals": [
            {"type": "ray", "start": [-3, 0.6], "end": [0, 0.6], "role": "accent"},
            {"type": "ellipse", "width": 0.5, "height": 2.4, "role": "primary"},
            {"type": "dot", "pos": [min(3.4, q["di"] / 20), -0.6], "role": "alert"},
        ],
        "equations": ["1/f = (n - 1)(1/R1 - 1/R2)", "1/v - 1/u = 1/f"],
    }


Concept("phys:lens", "physics", "optics", "Lens maker and image",
        {"n": (1.1, 2.5, 1.5), "R1": (5, 60, 20.0), "R2": (-60, -5, -20.0),
         "do": (5, 200, 60.0)},
        _lens_model, [("thin-lens", _lens_wit)], _lens_recipe,
        myth="A thicker lens always means a longer focal length.",
        close="Curvature and refractive index together set the power.")


def _photo_model(p):
    ke = H_EV_S * p["f"] - p["phi"]
    return {"KE": ke, "f0": p["phi"] / H_EV_S, "V0": ke}


def _photo_wit(q, p):
    return _ok(H_EV_S * q["f0"] - p["phi"], 0.0, 1e-12)


def _photo_recipe(q, p, rng):
    return {
        "facts": [
            f"Light at {p['f']:.3e} hertz ejects electrons with "
            f"K E = {q['KE']:g} eV.",
            f"Below the threshold {q['f0']:.3e} hertz nothing escapes, "
            f"however bright the lamp.",
        ],
        "visuals": [
            {"type": "graph", "expression": f"{H_EV_S:.3e}*x - {p['phi']:g}",
             "x_range": [q["f0"], 2 * q["f0"]], "role": "primary"},
            {"type": "energy_bar",
             "fraction": max(0.05, min(0.95, q["KE"] / max(H_EV_S * p["f"], 1e-9))),
             "role": "accent"},
        ],
        "equations": ["e V0 = h f - phi", f"f0 = {q['f0']:.3e} Hz"],
    }


Concept("phys:photoelectric", "physics", "modern", "Photoelectric threshold",
        {"f": (1e14, 3e15, 1.2e15), "phi": (0.5, 6, 2.0)},
        _photo_model, [("threshold", _photo_wit)], _photo_recipe,
        myth="Brighter light eventually frees electrons at any frequency.",
        close="Frequency opens the door; intensity only counts the guests.")


def _bohr_model(p):
    e1, e2 = -13.6 / p["n1"] ** 2, -13.6 / p["n2"] ** 2
    de = e2 - e1
    return {"E1": e1, "E2": e2, "dE": abs(de), "lambda_nm": HC_EV_NM / abs(de)}


def _bohr_wit(q, p):
    inv = RYDBERG * (1 / min(p["n1"], p["n2"]) ** 2 - 1 / max(p["n1"], p["n2"]) ** 2)
    return _ok(1 / (q["lambda_nm"] * 1e-9), inv, 1e-6)


def _bohr_recipe(q, p, rng):
    return {
        "facts": [
            f"Jumping from n = {p['n2']:g} to n = {p['n1']:g} releases "
            f"{q['dE']:g} eV.",
            f"That photon carries wavelength {q['lambda_nm']:g} nanometres.",
        ],
        "visuals": [
            {"type": "orbit", "width": 1.2 * p["n2"], "height": 1.2 * p["n2"] * 0.6,
             "role": "field"},
            {"type": "numerical_chain",
             "lines": [f"E{p['n1']:g} = {q['E1']:g} eV", f"E{p['n2']:g} = {q['E2']:g} eV",
                       f"lambda = {q['lambda_nm']:g} nm"], "role": "ink"},
        ],
        "equations": ["E_n = -13.6 / n^2 eV", "lambda = h c / delta E"],
    }


Concept("phys:bohr", "physics", "modern", "Bohr transitions and spectrum",
        {"n1": (1, 6, 2), "n2": (2, 7, 4)},
        _bohr_model, [("rydberg-match", _bohr_wit)], _bohr_recipe)


# ================================================================ CHEMISTRY
def _mole_model(p):
    n = p["m"] / p["M"]
    return {"n": n, "N": n * AVOGADRO}


def _mole_wit(q, p):
    return _ok(q["N"] / AVOGADRO * p["M"], p["m"], 1e-9)


def _mole_recipe(q, p, rng):
    return {
        "facts": [
            f"{p['m']:g} grams of a {p['M']:g} g per mole substance is "
            f"{q['n']:g} moles.",
            f"That is {q['N']:.3e} particles, no counting required.",
        ],
        "visuals": [{"type": "numerical_chain",
                     "lines": [f"m = {p['m']:g} g", f"M = {p['M']:g} g/mol",
                               f"n = {q['n']:g} mol", f"N = {q['N']:.3e}"],
                     "role": "ink"}],
        "equations": ["n = m / M", "N = n N_A"],
    }


Concept("chem:mole", "chemistry", "basics", "Mole bridge",
        {"m": (0.1, 1000, 36.0), "M": (1, 500, 18.0)},
        _mole_model, [("mass-roundtrip", _mole_wit)], _mole_recipe)


def _limit_model(p):
    ra, rb = p["a"] / p["ca"], p["b"] / p["cb"]
    lim = "A" if ra <= rb else "B"
    used = min(ra, rb)
    return {"limiting": lim, "product": used * p["cp"],
            "leftover": (p["b"] - used * p["cb"]) if lim == "A" else (p["a"] - used * p["ca"])}


def _limit_wit(q, p):
    consumed_a = p["a"] if q["limiting"] == "A" else p["ca"] * (p["b"] / p["cb"])
    return _ok(consumed_a / p["ca"], q["product"] / p["cp"], 1e-9)


def _limit_recipe(q, p, rng):
    return {
        "facts": [
            f"Reagent {q['limiting']} runs out first and caps the product "
            f"at {q['product']:g} moles.",
            f"The other reagent leaves {q['leftover']:g} moles unused.",
        ],
        "visuals": [
            {"type": "numerical_chain",
             "lines": [f"a = {p['a']:g} mol / {p['ca']:g}", f"b = {p['b']:g} mol / {p['cb']:g}",
                       f"product = {q['product']:g} mol"], "role": "ink"},
            {"type": "energy_bar",
             "fraction": max(0.05, min(0.95, q["product"] / max(p["cp"], 1e-9) / 10)),
             "role": "accent"},
        ],
        "equations": ["limiting = min(a/nu_A, b/nu_B)", "n_product = ratio * nu_P"],
    }


Concept("chem:limiting", "chemistry", "stoichiometry", "Limiting reagent",
        {"a": (0.1, 20, 4.0), "b": (0.1, 20, 3.0),
         "ca": (1, 4, 1), "cb": (1, 4, 1), "cp": (1, 4, 2)},
        _limit_model, [("yield-consistency", _limit_wit)], _limit_recipe)


def _eq_model(p):
    x_eq = p["K"] / (1 + p["K"]) * p["A0"]
    k_obs = p["kf"] * (1 + p["K"]) / max(p["K"], 1e-9) * p["K"] / (1 + p["K"])
    k_obs = p["kf"] + p["kf"] / p["K"]
    return {"x_eq": x_eq, "k_obs": k_obs, "K": p["K"]}


def _eq_wit(q, p):
    return _ok(q["x_eq"] / max(p["A0"] - q["x_eq"], 1e-12), q["K"], 1e-9)


def _eq_recipe(q, p, rng):
    return {
        "facts": [
            f"The mixture relaxes to x = {q['x_eq']:g} M where Q equals K = {q['K']:g}.",
            f"The approach is exponential with rate {q['k_obs']:g} per second.",
        ],
        "visuals": [
            {"type": "graph",
             "expression": f"{q['x_eq']:g}*(1-exp(-{q['k_obs']:g}*x))",
             "x_range": [0, 6 / max(q["k_obs"], 1e-6)], "role": "primary"},
            {"type": "energy_bar",
             "fraction": max(0.05, min(0.95, q["x_eq"] / max(p["A0"], 1e-9))),
             "role": "accent"},
        ],
        "equations": ["K = [B]/[A] at equilibrium", "x(t) = x_eq (1 - e^{-k t})"],
    }


Concept("chem:equilibrium", "chemistry", "equilibrium", "Approach to equilibrium",
        {"A0": (0.1, 5, 1.0), "K": (0.05, 20, 3.0), "kf": (0.01, 5, 0.5)},
        _eq_model, [("K-ratio", _eq_wit)], _eq_recipe,
        myth="At equilibrium the reaction stops.",
        close="Forward and backward rates match; molecules never rest.")


def _nernst_model(p):
    return {"E": p["E0"] - (0.0591 / p["n"]) * math.log10(p["Q"]),
            "slope": -0.0591 / p["n"]}


def _nernst_wit(q, p):
    h = 0.01
    e_plus = p["E0"] - (0.0591 / p["n"]) * (h)
    return _ok((e_plus - p["E0"]) / h, q["slope"], 1e-9)


def _nernst_recipe(q, p, rng):
    return {
        "facts": [
            f"With Q = {p['Q']:g} across {p['n']:g} electrons the cell reads "
            f"E = {q['E']:g} V.",
            "Every decade of Q shifts E by 0.0591 over n volts.",
        ],
        "visuals": [
            {"type": "graph", "expression": f"{p['E0']:g} + ({q['slope']:g})*x",
             "x_range": [-3, 3], "role": "primary"},
            {"type": "numerical_chain",
             "lines": [f"E0 = {p['E0']:g} V", f"n = {p['n']:g}", f"E = {q['E']:g} V"],
             "role": "ink"},
        ],
        "equations": ["E = E0 - (0.0591/n) log Q"],
    }


Concept("chem:nernst", "chemistry", "electrochemistry", "Nernst response",
        {"E0": (0.1, 3, 1.1), "n": (1, 6, 2), "Q": (0.001, 1000, 10.0)},
        _nernst_model, [("slope", _nernst_wit)], _nernst_recipe)


def _arrh_model(p):
    return {"k": p["A"] * math.exp(-p["Ea"] / (R_GAS * p["T"])),
            "Ea": p["Ea"]}


def _arrh_wit(q, p):
    t2 = p["T"] + 25
    k2 = p["A"] * math.exp(-p["Ea"] / (R_GAS * t2))
    lhs = math.log(k2 / q["k"])
    rhs = -p["Ea"] / R_GAS * (1 / t2 - 1 / p["T"])
    return _ok(lhs, rhs, 1e-9)


def _arrh_recipe(q, p, rng):
    return {
        "facts": [
            f"At {p['T']:g} K the rate constant is k = {q['k']:.3e}.",
            f"Raising Ea to {q['Ea']:g} J per mole starves the exponential.",
        ],
        "visuals": [
            {"type": "graph", "expression": f"{p['A']:.3e}*exp(-{p['Ea']/R_GAS:.6g}/x)",
             "x_range": [max(200, p["T"] - 100), p["T"] + 150], "role": "primary"},
            {"type": "numerical_chain",
             "lines": [f"A = {p['A']:.3e}", f"Ea = {q['Ea']:g} J/mol",
                       f"k = {q['k']:.3e}"], "role": "ink"},
        ],
        "equations": ["k = A e^{-Ea/(R T)}", "ln k vs 1/T is a straight line"],
    }


Concept("chem:arrhenius", "chemistry", "kinetics", "Arrhenius temperature law",
        {"A": (1e6, 1e13, 1e10), "Ea": (2e4, 2e5, 7.5e4), "T": (250, 600, 310.0)},
        _arrh_model, [("two-point", _arrh_wit)], _arrh_recipe)


def _debroglie_model(p):
    v = math.sqrt(2 * E_CH * p["V"] / M_E)
    return {"lambda_nm": H_PL / (M_E * v) * 1e9, "v": v}


def _debroglie_wit(q, p):
    approx = 1.226 / math.sqrt(p["V"])
    return _ok(q["lambda_nm"], approx, 1e-3)


def _debroglie_recipe(q, p, rng):
    return {
        "facts": [
            f"An electron accelerated through {p['V']:g} V carries wavelength "
            f"{q['lambda_nm']:g} nm.",
            f"Its speed is {q['v']:.3e} m per second, far below light.",
        ],
        "visuals": [
            {"type": "wave", "amplitude": 0.5, "frequency": 1.5, "role": "primary"},
            {"type": "numerical_chain",
             "lines": [f"V = {p['V']:g} V", f"v = {q['v']:.3e} m/s",
                       f"lambda = {q['lambda_nm']:g} nm"], "role": "ink"},
        ],
        "equations": ["lambda = h / (m v)", "lambda(nm) approx 1.226 / sqrt(V)"],
    }


Concept("chem:debroglie", "chemistry", "atomic", "Electron wavelength",
        {"V": (10, 5000, 150.0)},
        _debroglie_model, [("shortcut-match", _debroglie_wit)], _debroglie_recipe)


def _slater(z, same, inner):
    return z - (0.35 * (same - 1) + 0.85 * inner)


def _slater_model(p):
    table = [(3, 1, 2), (4, 2, 2), (5, 3, 2), (6, 4, 2), (7, 5, 2), (8, 6, 2)]
    vals = [(z, _slater(z, s, i)) for z, s, i in table]
    return {"zeff": dict(vals), "trend": [v for _, v in vals]}


def _slater_wit(q, p):
    t = q["trend"]
    return all(b > a for a, b in zip(t, t[1:])), str(t)


def _slater_recipe(q, p, rng):
    lines = [f"Z={z}: Zeff={v:g}" for z, v in q["zeff"].items()]
    return {
        "facts": [
            "Across Li to Ne the effective nuclear charge climbs steadily.",
            f"Neon feels about {q['trend'][-1]:g} while lithium feels {q['trend'][0]:g}.",
        ],
        "visuals": [{"type": "numerical_chain", "lines": lines[:6], "role": "ink"},
                    {"type": "energy_bar",
                     "fraction": max(0.1, min(0.95, q["trend"][-1] / 8)), "role": "accent"}],
        "equations": ["Zeff = Z - S", "S = 0.35(same-1) + 0.85(inner)"],
    }


Concept("chem:slater", "chemistry", "periodic", "Slater shielding trend",
        {"dummy": (0, 1, 0)},
        _slater_model, [("monotone-period", _slater_wit)], _slater_recipe)


def _sn_model(p):
    return {"r1": p["k1"] * p["C"], "r2": p["k2"] * p["C"] * p["Nu"]}


def _sn_wit(q, p):
    return (_ok(2 * q["r1"], p["k1"] * (2 * p["C"])) and
            _ok(2 * q["r2"], p["k2"] * p["C"] * (2 * p["Nu"])))[0] \
        if isinstance(_ok(2 * q["r1"], p["k1"] * 2 * p["C"]), tuple) else False


def _sn_wit2(q, p):
    a = _ok(2 * q["r1"], p["k1"] * (2 * p["C"]))
    b = _ok(2 * q["r2"], p["k2"] * p["C"] * (2 * p["Nu"]))
    return a[0] and b[0], f"{a[1]} {b[1]}"


def _sn_recipe(q, p, rng):
    return {
        "facts": [
            f"SN1 rate {q['r1']:g} M/s depends only on the substrate.",
            f"SN2 rate {q['r2']:g} M/s needs substrate and nucleophile together.",
        ],
        "visuals": [
            {"type": "concept_map",
             "nodes": [{"id": "rx", "label": "R-X"}, {"id": "ci", "label": "R+"},
                       {"id": "p1", "label": "P (SN1)"}, {"id": "ts", "label": "TS"},
                       {"id": "p2", "label": "P (SN2)"}],
             "edges": [{"from": "rx", "to": "ci"}, {"from": "ci", "to": "p1"},
                       {"from": "rx", "to": "ts"}, {"from": "ts", "to": "p2"}],
             "role": "primary"},
            {"type": "numerical_chain",
             "lines": [f"r1 = {q['r1']:g}", f"r2 = {q['r2']:g}"], "role": "ink"},
        ],
        "equations": ["SN1: r = k[RX]", "SN2: r = k[RX][Nu]"],
    }


Concept("chem:sn1_sn2", "chemistry", "organic", "SN1 vs SN2 rates",
        {"k1": (0.001, 1, 0.05), "k2": (0.001, 1, 0.08),
         "C": (0.01, 2, 0.4), "Nu": (0.01, 2, 0.5)},
        _sn_model, [("order-doubling", _sn_wit2)], _sn_recipe)


# ================================================================ MATHS
def _quad_model(p):
    d = p["b"] ** 2 - 4 * p["a"] * p["c"]
    r = math.sqrt(abs(d))
    r1 = (-p["b"] + r) / (2 * p["a"])
    r2 = (-p["b"] - r) / (2 * p["a"])
    return {"disc": d, "r1": r1, "r2": r2,
            "nature": "real distinct" if d > 0 else ("equal" if d == 0 else "complex")}


def _quad_wit(q, p):
    s_ok = _ok(q["r1"] + q["r2"], -p["b"] / p["a"])
    pr_ok = _ok(q["r1"] * q["r2"], p["c"] / p["a"])
    return s_ok[0] and pr_ok[0], f"{s_ok[1]} {pr_ok[1]}"


def _quad_recipe(q, p, rng):
    return {
        "facts": [
            f"The discriminant is {q['disc']:g}, so the roots are {q['nature']}.",
            f"They sit at {q['r1']:g} and {q['r2']:g}, summing to {-p['b']/p['a']:g}.",
        ],
        "visuals": [
            {"type": "graph",
             "expression": f"({p['a']:g})*x^2+({p['b']:g})*x+({p['c']:g})",
             "x_range": [-6, 6], "role": "primary"},
            {"type": "number_line", "value": q["r1"], "x_range": [-6, 6], "role": "accent"},
        ],
        "equations": ["D = b^2 - 4ac", "alpha + beta = -b/a", "alpha beta = c/a"],
    }


Concept("math:quadratic", "maths", "algebra", "Quadratic roots and Vieta",
        {"a": (-5, 5, 1.0), "b": (-20, 20, -3.0), "c": (-20, 20, -4.0)},
        _quad_model, [("vieta", _quad_wit)], _quad_recipe)


def _series_model(p):
    n = int(p["n"])
    ap = [p["a"] + i * p["d"] for i in range(n)]
    sa = sum(ap)
    gp = [p["ga"] * p["r"] ** i for i in range(n)]
    sg = sum(gp)
    return {"S_ap": sa, "S_gp": sg,
            "closed_ap": n / 2 * (2 * p["a"] + (n - 1) * p["d"]),
            "closed_gp": p["ga"] * (p["r"] ** n - 1) / (p["r"] - 1)}


def _series_wit(q, p):
    a = _ok(q["S_ap"], q["closed_ap"])
    b = _ok(q["S_gp"], q["closed_gp"], 1e-9)
    return a[0] and b[0], f"{a[1]} {b[1]}"


def _series_recipe(q, p, rng):
    return {
        "facts": [
            f"The AP of {int(p['n'])} terms sums to {q['S_ap']:g}, loop and formula agree.",
            f"The GP with ratio {p['r']:g} sums to {q['S_gp']:g}.",
        ],
        "visuals": [
            {"type": "graph", "expression": f"({p['a']:g})+(x-1)*({p['d']:g})",
             "x_range": [1, p["n"]], "role": "primary"},
            {"type": "numerical_chain",
             "lines": [f"S_ap = {q['S_ap']:g}", f"S_gp = {q['S_gp']:g}"], "role": "ink"},
        ],
        "equations": ["S_n = n/2 (2a + (n-1)d)", "S_n = a(r^n - 1)/(r - 1)"],
    }


Concept("math:series", "maths", "sequences", "AP and GP sums",
        {"a": (-10, 10, 2.0), "d": (-5, 5, 3.0), "n": (2, 40, 10),
         "ga": (-10, 10, 1.0), "r": (1.05, 3, 2.0)},
        _series_model, [("loop-vs-closed", _series_wit)], _series_recipe)


def _cf(n, r):
    return math.comb(n, r)


def _pc_model(p):
    n, r = int(p["n"]), int(p["r"])
    return {"nPr": math.perm(n, r), "nCr": _cf(n, r)}


def _pc_wit(q, p):
    n, r = int(p["n"]), int(p["r"])
    a = _ok(_cf(n, r), _cf(n, n - r))
    b = (_cf(n, r) == _cf(n - 1, r - 1) + _cf(n - 1, r)) if 0 < r < n else True
    return a[0] and b, f"{a[1]} pascal={b}"


def _pc_recipe(q, p, rng):
    return {
        "facts": [
            f"Choosing {int(p['r'])} from {int(p['n'])} gives {q['nCr']:g} combos.",
            f"Ordering them instead gives {q['nPr']:g} permutations.",
        ],
        "visuals": [{"type": "numerical_chain",
                     "lines": [f"n = {int(p['n'])}", f"r = {int(p['r'])}",
                               f"C = {q['nCr']:g}", f"P = {q['nPr']:g}"], "role": "ink"}],
        "equations": ["nCr = n! / (r! (n-r)!)", "nPr = n! / (n-r)!"],
    }


Concept("math:permcomb", "maths", "combinatorics", "Permutations and combinations",
        {"n": (2, 30, 8), "r": (1, 15, 3)},
        _pc_model, [("symmetry-pascal", _pc_wit)], _pc_recipe)


def _binom_model(p):
    n, r = int(p["n"]), int(p["r"])
    term = _cf(n, r) * p["a"] ** (n - r) * p["b"] ** r
    return {"term": term, "sum_coeffs": 2 ** n}


def _binom_wit(q, p):
    n = int(p["n"])
    return _ok(sum(_cf(n, r) for r in range(n + 1)), q["sum_coeffs"], 1e-9)


def _binom_recipe(q, p, rng):
    return {
        "facts": [
            f"The r = {int(p['r'])} term of (a+b)^{int(p['n'])} equals {q['term']:g}.",
            f"All coefficients together sum to {q['sum_coeffs']:g}.",
        ],
        "visuals": [
            {"type": "equation_morph",
             "steps": [f"(a+b)^{int(p['n'])}",
                       f"T_{{{int(p['r'])+1}}} = C({int(p['n'])},{int(p['r'])}) a^{int(p['n'])-int(p['r'])} b^{int(p['r'])}",
                       f"= {q['term']:g}"], "role": "primary"},
            {"type": "numerical_chain", "lines": [f"sum C = {q['sum_coeffs']:g}"],
             "role": "ink"},
        ],
        "equations": ["T_{r+1} = C(n,r) a^{n-r} b^r", "sum C(n,r) = 2^n"],
    }


Concept("math:binomial", "maths", "algebra", "Binomial term and coefficient sum",
        {"n": (2, 20, 6), "r": (0, 10, 2), "a": (0.5, 4, 2.0), "b": (0.5, 4, 1.0)},
        _binom_model, [("coeff-sum", _binom_wit)], _binom_recipe)


def _cx_model(p):
    import cmath
    z1 = complex(p["x1"], p["y1"])
    z2 = complex(p["x2"], p["y2"])
    z = z1 * z2
    return {"mod": abs(z), "arg": math.atan2(z.imag, z.real),
            "m1": abs(z1), "m2": abs(z2),
            "a1": math.atan2(z1.imag, z1.real), "a2": math.atan2(z2.imag, z2.real),
            "zx": z.real, "zy": z.imag}


def _cx_wit(q, p):
    m_ok = _ok(q["mod"], q["m1"] * q["m2"])
    da = (q["a1"] + q["a2"] + math.pi) % (2 * math.pi) - math.pi
    a_ok = _ok(q["arg"], da, 1e-9)
    return m_ok[0] and a_ok[0], f"{m_ok[1]} {a_ok[1]}"


def _cx_recipe(q, p, rng):
    return {
        "facts": [
            f"Multiplying rotates: arguments add to {q['arg']:g} rad.",
            f"Moduli multiply to {q['mod']:g}.",
        ],
        "visuals": [
            {"type": "vector", "start": [0, 0], "end": [p["x1"], p["y1"]], "role": "primary"},
            {"type": "vector", "start": [0, 0], "end": [p["x2"], p["y2"]], "role": "secondary"},
            {"type": "vector", "start": [0, 0],
             "end": [max(-3, min(3, q["zx"])), max(-3, min(3, q["zy"]))], "role": "accent"},
        ],
        "equations": ["|z1 z2| = |z1| |z2|", "arg(z1 z2) = arg z1 + arg z2"],
    }


Concept("math:complex", "maths", "complex", "Complex multiplication as rotation",
        {"x1": (-3, 3, 1.0), "y1": (-3, 3, 1.0), "x2": (-3, 3, 0.5), "y2": (-3, 3, 1.5)},
        _cx_model, [("modulus-argument", _cx_wit)], _cx_recipe)


def _conic_model(p):
    a = p["a"]
    return {"focus": (a, 0.0), "directrix": -a,
            "pt": (a * p["t"] ** 2, 2 * a * p["t"]),
            "focal": a * p["t"] ** 2 + a}


def _conic_wit(q, p):
    fx, fy = q["focus"]
    px, py = q["pt"]
    d = math.hypot(px - fx, py - fy)
    return _ok(d, q["focal"])


def _conic_recipe(q, p, rng):
    return {
        "facts": [
            f"On y^2 = 4 a x with a = {p['a']:g}, the point at t = {p['t']:g} "
            f"lies {q['focal']:g} from the focus.",
            "Focal distance equals distance to the directrix, always.",
        ],
        "visuals": [
            {"type": "graph", "expression": f"sqrt(4*{p['a']:g}*x)",
             "x_range": [0, 4 * p["a"]], "role": "primary"},
            {"type": "dot", "pos": list(q["focus"]), "role": "alert"},
            {"type": "line", "start": [q["directrix"], -2], "end": [q["directrix"], 2],
             "role": "field"},
        ],
        "equations": ["y^2 = 4 a x", "focal distance = x + a"],
    }


Concept("math:parabola", "maths", "coordinate", "Parabola focal distance",
        {"a": (0.2, 3, 1.0), "t": (-2, 2, 1.0)},
        _conic_model, [("focus-directrix", _conic_wit)], _conic_recipe)


def _bayes_model(p):
    pb = p["pa"] * p["pb_a"] + (1 - p["pa"]) * p["pb_ac"]
    post = p["pa"] * p["pb_a"] / pb
    return {"P_B": pb, "post": post}


def _bayes_wit(q, p):
    comp = (1 - p["pa"]) * p["pb_ac"] / q["P_B"]
    return _ok(q["post"] + comp, 1.0)


def _bayes_recipe(q, p, rng):
    return {
        "facts": [
            f"Total probability of the evidence is {q['P_B']:g}.",
            f"After seeing it, belief in A rises to {q['post']:g}.",
        ],
        "visuals": [
            {"type": "concept_map",
             "nodes": [{"id": "a", "label": "A"}, {"id": "ac", "label": "A'"},
                       {"id": "b", "label": "B"}],
             "edges": [{"from": "a", "to": "b", "label": "P(B|A)"},
                       {"from": "ac", "to": "b", "label": "P(B|A')"}],
             "role": "primary"},
            {"type": "numerical_chain",
             "lines": [f"P(B) = {q['P_B']:g}", f"P(A|B) = {q['post']:g}"], "role": "ink"},
        ],
        "equations": ["P(B) = P(A)P(B|A) + P(A')P(B|A')",
                      "P(A|B) = P(A)P(B|A)/P(B)"],
    }


Concept("math:bayes", "maths", "probability", "Bayes update",
        {"pa": (0.05, 0.95, 0.3), "pb_a": (0.05, 0.99, 0.8), "pb_ac": (0.01, 0.9, 0.2)},
        _bayes_model, [("posterior-normalizes", _bayes_wit)], _bayes_recipe)


def _skew_model(p):
    a1 = [p["a1x"], p["a1y"], p["a1z"]]
    a2 = [p["a2x"], p["a2y"], p["a2z"]]
    b1 = [p["b1x"], p["b1y"], p["b1z"]]
    b2 = [p["b2x"], p["b2y"], p["b2z"]]
    cr = [b1[1] * b2[2] - b1[2] * b2[1], b1[2] * b2[0] - b1[0] * b2[2],
          b1[0] * b2[1] - b1[1] * b2[0]]
    nrm = math.sqrt(sum(c * c for c in cr)) or 1e-12
    d = [a2[i] - a1[i] for i in range(3)]
    return {"dist": abs(sum(d[i] * cr[i] for i in range(3))) / nrm, "n": nrm}


def _skew_wit(q, p):
    return q["dist"] >= 0 and math.isfinite(q["dist"]), str(q["dist"])


def _skew_recipe(q, p, rng):
    return {
        "facts": [
            f"The skew lines stay {q['dist']:g} units apart.",
            "The common normal is the cross product of their directions.",
        ],
        "visuals": [
            {"type": "vector", "start": [-2, -1, 0], "end": [2, 1, 0], "role": "primary"},
            {"type": "vector", "start": [-2, 1.4, 0], "end": [2, -0.4, 0], "role": "secondary"},
            {"type": "numerical_chain", "lines": [f"distance = {q['dist']:g}"],
             "role": "ink"},
        ],
        "equations": ["d = |(b1 x b2).(a2 - a1)| / |b1 x b2|"],
    }


Concept("math:skew_distance", "maths", "vectors3d", "Distance between skew lines",
        {"a1x": (-3, 3, 0), "a1y": (-3, 3, 0), "a1z": (-3, 3, 0),
         "a2x": (-3, 3, 1), "a2y": (-3, 3, 2), "a2z": (-3, 3, 0),
         "b1x": (-3, 3, 1), "b1y": (-3, 3, 0), "b1z": (-3, 3, 0),
         "b2x": (-3, 3, 0), "b2y": (-3, 3, 1), "b2z": (-3, 3, 1)},
        _skew_model, [("finite-nonneg", _skew_wit)], _skew_recipe)


def _ode_model(p):
    return {"y_at": p["y0"] * math.exp(p["k"] * p["x"]), "k": p["k"]}


def _ode_wit(q, p):
    h = 1e-5
    f = lambda x: p["y0"] * math.exp(p["k"] * x)
    d = (f(p["x"] + h) - f(p["x"] - h)) / (2 * h)
    return _ok(d, p["k"] * q["y_at"], 1e-6)


def _ode_recipe(q, p, rng):
    return {
        "facts": [
            f"dy/dx = k y grows to y = {q['y_at']:g} at x = {p['x']:g}.",
            f"The relative growth rate stays k = {q['k']:g} everywhere.",
        ],
        "visuals": [
            {"type": "graph", "expression": f"({p['y0']:g})*exp({p['k']:g}*x)",
             "x_range": [0, max(1.0, p["x"])], "role": "primary"},
            {"type": "equation_morph",
             "steps": ["dy/y = k dx", "ln y = k x + c", f"y = {q['y_at']:g}"],
             "role": "accent"},
        ],
        "equations": ["y = y0 e^{k x}"],
    }


Concept("math:ode_exponential", "maths", "calculus", "Separable growth equation",
        {"y0": (0.1, 5, 1.0), "k": (0.1, 3, 0.8), "x": (0.2, 4, 2.0)},
        _ode_model, [("derivative-closure", _ode_wit)], _ode_recipe)


def _tri_model(p):
    A, B = math.radians(p["A"]), math.radians(p["B"])
    C = math.pi - A - B
    two_r = p["a"] / math.sin(A)
    return {"C_deg": math.degrees(C), "b": two_r * math.sin(B),
            "c": two_r * math.sin(C), "R": two_r / 2}


def _tri_wit(q, p):
    return (_ok(p["a"] / math.sin(math.radians(p["A"])),
                q["b"] / math.sin(math.radians(p["B"]))) and
            _ok(q["b"] / math.sin(math.radians(p["B"])),
                q["c"] / math.sin(math.radians(q["C_deg"]))))[0] \
        if False else (_ok(p["a"] / math.sin(math.radians(p["A"])),
                           q["b"] / math.sin(math.radians(p["B"])))[0] and
                       _ok(q["b"] / math.sin(math.radians(p["B"])),
                           q["c"] / math.sin(math.radians(q["C_deg"])))[0]), "sine-rule"


def _tri_recipe(q, p, rng):
    return {
        "facts": [
            f"The third angle closes the triangle at {q['C_deg']:g} degrees.",
            f"Sides follow: b = {q['b']:g}, c = {q['c']:g}, circumradius {q['R']:g}.",
        ],
        "visuals": [
            {"type": "polygon",
             "points": [[-2, -1], [2, -1], [0.4, 1.6]], "role": "primary"},
            {"type": "numerical_chain",
             "lines": [f"C = {q['C_deg']:g} deg", f"b = {q['b']:g}", f"c = {q['c']:g}"],
             "role": "ink"},
        ],
        "equations": ["a/sin A = b/sin B = c/sin C = 2R"],
    }


Concept("math:sine_rule", "maths", "trigonometry", "Sine rule closure",
        {"A": (20, 80, 40.0), "B": (20, 80, 60.0), "a": (1, 10, 5.0)},
        _tri_model, [("sine-rule", _tri_wit)], _tri_recipe)


# ================================================================ recipes → rows
VOICES = ("question-first", "picture-first", "contrast", "story-arc", "myth-bust")


def _script(c, story, grammar, audience):
    facts = list(story["facts"])
    tag = {"jee": "This is JEE Main and Advanced core.",
           "neet": "This is NEET physics-chemistry core.",
           "mit": "This is the MIT-flavoured deep cut."}.get(audience, "")
    if grammar == "question-first":
        head = [f"Can you see {c.title.lower()} in one picture?"]
        tail = [tag] if tag else []
    elif grammar == "picture-first":
        head = [f"Look at the diagram before any formula."]
        tail = facts[-1:] + ([tag] if tag else [])
        facts = facts[:-1]
    elif grammar == "contrast" and c.myth:
        head = [c.myth]
        tail = ["The model says otherwise."] + ([tag] if tag else [])
    elif grammar == "myth-bust" and c.myth:
        head = [c.myth]
        tail = [c.close or tag]
    else:
        head = [f"Today: {c.title}."]
        tail = [c.close or tag] if (c.close or tag) else []
    return " ".join(s for s in head + facts + tail if s)


def generate_row(cid, params=None, seed=7, audience="jee",
                 orientation="vertical", make_quiz=False, voice=None):
    c = REGISTRY[cid]
    p = {}
    for name, (lo, hi, dflt) in c.params.items():
        val = (params or {}).get(name, dflt)
        p[name] = _num(val, f"{cid}:{name}", lo, hi)
    q = c.model(p)
    for wname, wfn in c.witnesses:
        good, detail = wfn(q, p)
        if not good:
            raise ValueError(f"witness {cid}:{wname} failed: {detail}")
    rng = random.Random(f"{cid}|{seed}|{audience}")
    story = c.recipe(q, p, rng)
    grammar = voice or rng.choice(VOICES)
    script = _script(c, story, grammar, audience)

    words = _spoken(script)
    lo_t = math.ceil(words / 3.0) + 1
    hi_t = max(lo_t + 1, math.floor(words / 1.87) - 1)
    target = min(hi_t, max(lo_t, round(words / 2.4)))

    visuals = []
    for i, v in enumerate(story["visuals"]):
        vv = dict(v)
        vv.setdefault("id", f"p{i}")
        visuals.append(vv)
    beats = [{"time": round(target * (i + 1) / (len(visuals) + 1), 2),
              "focus": f"p{i}"} for i in range(len(visuals))]

    row = {k: "" for k in (
        "video_id", "concept_type", "header_title", "tagline", "question_text",
        "option_a", "option_b", "option_c", "option_d", "correct_answer",
        "equations_json", "visual_data_json", "audio_script", "orientation")}
    row.update({
        "video_id": f"{cid.replace(':', '_')}_{seed}",
        "concept_type": "GENERIC",
        "header_title": f"{c.subject.title()} · {c.title}",
        "tagline": f"{c.chapter} · {audience.upper()} · SaemLabs",
        "equations_json": __import__("json").dumps(story["equations"]),
        "visual_data_json": __import__("json").dumps(visuals),
        "audio_script": script,
        "orientation": orientation,
        "target_duration_sec": str(target),
        "beats_json": __import__("json").dumps(beats),
    })
    if make_quiz and "quiz" in story:
        qtext, opts, ans = story["quiz"]
        row.update(concept_type="PYQ", question_text=qtext,
                   option_a=opts[0], option_b=opts[1],
                   option_c=opts[2], option_d=opts[3], correct_answer=ans)
    return row


# ================================================================ concept_map route
def route_concept_map(scene, spec):
    from manim import Arrow, RoundedRectangle, Text, VGroup
    nodes = spec.get("nodes")
    edges = spec.get("edges", [])
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= 12:
        raise ValueError("concept_map needs 1..12 nodes.")
    if not isinstance(edges, list) or len(edges) > 24:
        raise ValueError("concept_map allows at most 24 edges.")
    ids = [n.get("id") for n in nodes if isinstance(n, dict)]
    if len(ids) != len(set(ids)) or any(i is None for i in ids):
        raise ValueError("concept_map node ids must be unique strings.")
    for e in edges:
        if e.get("from") not in ids or e.get("to") not in ids:
            raise ValueError("concept_map edge references unknown node.")
    ctx = getattr(scene, "ctx", None)
    col_n = ctx.color(spec, "primary") if ctx else spec.get("color", "#4CC9F0")
    col_e = ctx.color(spec, "secondary") if ctx else "#F1C40F"
    col_t = ctx.color(spec, "ink") if ctx else "#F2F3F5"
    fs = ctx.font(14) if ctx else 14

    mobs, centers = VGroup(), {}
    for i, n in enumerate(nodes):
        ns = {"pos": n.get("pos")} if n.get("pos") else {}
        center = (ctx.place(i, len(nodes), ns) if ctx else
                  tuple(list(n.get("pos", [0, 0, 0])) + [0.0] * (3 - len(n.get("pos", [0, 0, 0])))))
        label = Text(str(n.get("label", n["id"])), font_size=fs, color=col_t)
        box = RoundedRectangle(width=label.width + 0.5, height=label.height + 0.3,
                               color=col_n, stroke_width=(ctx.stroke() if ctx else 2.5))
        grp = VGroup(box, label.move_to(box.get_center())).move_to(center)
        centers[n["id"]] = center
        mobs.add(grp)
    for e in edges:
        a, b = centers[e["from"]], centers[e["to"]]
        mobs.add(Arrow(a, b, buff=0.45, color=col_e, stroke_width=2.2,
                       max_tip_length_to_length_ratio=0.18))
    return mobs


ROUTE_TABLE = {"concept_map": route_concept_map}


# ================================================================ witness suite
def selftest():
    import json as _json
    checks = []

    def want(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    for cid, c in REGISTRY.items():
        p = {n: d for n, (_l, _h, d) in c.params.items()}
        try:
            q = c.model(p)
            good = True
            for wname, wfn in c.witnesses:
                ok_, det = wfn(q, p)
                good = good and ok_
                if not ok_:
                    detail = det
            want(f"witness:{cid}", good, "" if good else det)
            row = generate_row(cid, seed=3)
            vis = _json.loads(row["visual_data_json"])
            words = _spoken(row["audio_script"])
            t = float(row["target_duration_sec"])
            band = 1.87 * t <= words <= 3.0 * t
            want(f"band:{cid}", band, f"{words}w @{t}s")
            want(f"visuals:{cid}", len(vis) >= 1 and all(
                isinstance(v, dict) and v.get("type") for v in vis))
            r2 = generate_row(cid, seed=3)
            want(f"determinism:{cid}", r2 == row)
        except Exception as e:
            want(f"build:{cid}", False, f"{type(e).__name__}: {e}")
    try:
        route_concept_map(_Null(), {"nodes": [{"id": "a"}, {"id": "a"}]})
        want("guard:dup-nodes", False)
    except ValueError:
        want("guard:dup-nodes", True)
    try:
        route_concept_map(_Null(), {"nodes": [{"id": "a"}],
                                    "edges": [{"from": "a", "to": "zz"}]})
        want("guard:bad-edge", False)
    except ValueError:
        want("guard:bad-edge", True)
    return checks


class _Null:
    ctx = None


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "--selftest":
        fails = 0
        for name, ok, detail in selftest():
            print(f"[{'ok ' if ok else 'FAIL'}] {name} {detail if not ok else ''}")
            fails += 0 if ok else 1
        sys.exit(1 if fails else 0)
    if args[0] == "list":
        for cid, c in REGISTRY.items():
            print(f"{cid:24s} {c.subject:9s} {c.chapter:16s} {c.title}")
        sys.exit(0)
    if args[0] == "row":
        import json as _json
        cid = args[1]
        seed = 7
        aud = "jee"
        if "--seed" in args:
            seed = int(args[args.index("--seed") + 1])
        if "--audience" in args:
            aud = args[args.index("--audience") + 1]
        print(_json.dumps(generate_row(cid, seed=seed, audience=aud),
                          ensure_ascii=False, indent=2))
        sys.exit(0)
    print("usage: jee_model_engine.py [list|row <id>|--selftest]")
    sys.exit(1)
