cases = load_cases(patterns, key)
    if not cases:
        raise SystemExit("no cases loaded from tests/diff/cases/*.jsonl: the witness is blind")
