"""Convert ``scripts/deploy.env`` (bash KEY=value format) to
``scripts/deploy.env.ps1`` (PowerShell ``$env:KEY = "value"`` format).

The two deploy script flavours (``.sh`` for bash, ``.ps1`` for
PowerShell) read from different files. This bridge lets a single
populated ``deploy.env`` drive both without duplication.

Run:
    .venv/Scripts/python.exe scripts/bash_env_to_ps1.py

Reads:  scripts/deploy.env
Writes: scripts/deploy.env.ps1   (overwrites if it exists)
"""

from pathlib import Path
import re


SRC = Path("scripts/deploy.env")
DST = Path("scripts/deploy.env.ps1")

LINE_RE = re.compile(r"^\s*([A-Z_][A-Z0-9_]*)\s*=(.*)$")


def main() -> int:
    if not SRC.exists():
        print(f"  {SRC} not found")
        return 1

    out_lines: list[str] = [
        "# Auto-generated from scripts/deploy.env by bash_env_to_ps1.py.",
        "# DO NOT commit (already gitignored).",
        "",
    ]
    converted = 0
    for raw in SRC.read_text(encoding="utf-8").splitlines():
        # Pass comments and blank lines through, just translated to PS-flavour.
        stripped = raw.strip()
        if not stripped:
            out_lines.append("")
            continue
        if stripped.startswith("#"):
            # PowerShell uses # for comments too — preserve as-is.
            out_lines.append(raw)
            continue
        m = LINE_RE.match(raw)
        if not m:
            out_lines.append(f"# unparseable bash line preserved verbatim: {raw}")
            continue
        key, value = m.group(1), m.group(2).strip()
        # Strip surrounding quotes the bash file might have.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        # Escape backticks (PS escape char) and double quotes.
        ps_value = value.replace("`", "``").replace('"', '`"')
        out_lines.append(f'$env:{key} = "{ps_value}"')
        converted += 1

    DST.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"  Wrote {DST} ({converted} env vars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
