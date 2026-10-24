def verify():
    """The binary must report the body the tree actually has."""
    sid = source_id()
    body = subprocess.run([os.path.join(OUT, "saem_cli"), "--source-id"],
                          capture_output=True, text=True).stdout.strip()
    if body != sid:
        raise SystemExit("[verify] STALE binary %s != tree %s" % (body[:12], sid[:12]))
    print("[verify] body ok %s" % sid[:12])
# and in the dispatch:  elif kind == "verify": verify()
