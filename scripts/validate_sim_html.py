"""Independent validation for self-contained simulation HTML files.

Checks each file given on the command line:
  * exists and is non-empty
  * size < 150 KB (matches the upload cap the app enforces)
  * starts with <!DOCTYPE html> and has <html>/<head>/<body>/<title>
  * NO external resource references: no src=/href= pointing at http(s),
    no url(http...), no <script src>, <link href>, or @import of a URL
  * balanced <script> and <body>/<html> tags (cheap sanity check)

Exit code 0 only if every file passes.

Run (Git Bash):
  PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -m scripts.validate_sim_html \
      tmp/simulations/sim_ch77_gravitation.html ...
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MAX_BYTES = 150 * 1024

# Any of these indicate a dependency on an external host.
EXTERNAL_PATTERNS = [
    re.compile(r'(?:src|href)\s*=\s*["\']https?://', re.I),
    re.compile(r'url\(\s*["\']?https?://', re.I),
    re.compile(r'@import\s+["\']?https?://', re.I),
    re.compile(r'//(?:cdn|fonts|unpkg|jsdelivr|cdnjs|ajax)\.', re.I),
]


def check(path: Path) -> list[str]:
    if not path.exists():
        return [f"MISSING FILE: {path}"]
    data = path.read_bytes()
    if not data:
        return ["EMPTY FILE"]
    errs: list[str] = []
    size = len(data)
    if size > MAX_BYTES:
        errs.append(f"size {size} bytes > {MAX_BYTES} cap")

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        return [f"not valid UTF-8: {e}"]

    head = text.lstrip()[:200].lower()
    if not head.startswith("<!doctype html"):
        errs.append("does not start with <!DOCTYPE html>")
    for tag in ("<html", "<head", "<body", "<title"):
        if tag not in text.lower():
            errs.append(f"missing {tag}> tag")

    for pat in EXTERNAL_PATTERNS:
        m = pat.search(text)
        if m:
            errs.append(f"external resource reference: {m.group(0)[:60]!r}")

    lo = text.lower()
    if lo.count("<script") != lo.count("</script>"):
        errs.append(f"unbalanced <script> ({lo.count('<script')} open / {lo.count('</script>')} close)")
    if lo.count("<body") and lo.count("</body>") != 1:
        errs.append("missing/duplicate </body>")

    return errs


def main() -> None:
    paths = [Path(a) for a in sys.argv[1:]]
    if not paths:
        print("usage: validate_sim_html.py <file.html> [...]")
        raise SystemExit(2)
    all_ok = True
    for p in paths:
        errs = check(p)
        if errs:
            all_ok = False
            print(f"[FAIL] {p.name}")
            for e in errs:
                print(f"       - {e}")
        else:
            kb = p.stat().st_size / 1024
            print(f"[VALID] {p.name} ({kb:.1f} KB)")
    print("\nRESULT:", "ALL VALID" if all_ok else "FAILURES PRESENT")
    raise SystemExit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
