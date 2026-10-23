import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SAEMCLI = ROOT / "build" / "saemcli"

def cli(*a):
    r = subprocess.run([str(SAEMCLI), *a], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)

def test_vectors_parity():
    """Hand-worked answers must match solve() — JS/C++ parity gate."""
    for entry in cli("vectors"):
        qid, params, want = entry[0], entry[1], entry[2]
        tol = entry[3] if len(entry) > 3 else 1e-9
        got = cli("solve", qid, json.dumps(params))
        if isinstance(want, (int, float)) and isinstance(got, (int, float)):
            assert abs(got - want) <= tol, (qid, got, want)
        else:
            assert str(got) == str(want), (qid, got, want)

def test_soul_stable():
    assert cli("soul")["soul"] == cli("soul")["soul"]

def test_topics_nonempty():
    assert len(cli("topics")) >= 1
