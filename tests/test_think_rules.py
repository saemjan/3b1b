from pathlib import Path
def test_every_rule_has_a_machine_check():
    rules = Path("THINK.md").read_text().split("## 2.")[1].split("## 3.")[0]
    for ln in rules.splitlines():
        if ln.strip().startswith("- R"):
            assert "[check:" in ln or "[tests/" in ln or "[workflow" in ln.lower(), \
                f"Rule without machine check: {ln[:50]}"
