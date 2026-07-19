"""Independent re-validation for NIOS Sanskrit content bundles.

Checks each file given on the command line (or a default glob) for:
  * file exists and is UTF-8 JSON
  * passes the ContentBundle pydantic schema
  * exactly 140 questions with the expected type distribution
  * worksheet.total_marks equals the exact sum of worksheet question marks
  * every question.outcome_code is one of the 8 declared outcome codes
  * 8 learning outcomes, 6 topics

Run (Git Bash):
  PYTHONIOENCODING=utf-8 PYTHONPATH=. .venv/Scripts/python.exe -m scripts.validate_sanskrit_bundles \
      scripts/nios_class10_sanskrit/data/bundle_ch2_prerana.json ...
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from app.schemas.content_bundle import ContentBundle

EXPECTED_DIST = {
    "MCQ": 75,
    "TRUE_FALSE": 10,
    "FILL_BLANK": 15,
    "SHORT_ANSWER": 22,
    "LONG_ANSWER": 8,
    "CASE_BASED": 10,
}


def check(path: Path) -> list[str]:
    errs: list[str] = []
    if not path.exists():
        return [f"MISSING FILE: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return [f"JSON parse error: {type(e).__name__}: {e}"]
    try:
        ContentBundle.model_validate(data)
    except Exception as e:  # noqa: BLE001
        errs.append(f"SCHEMA INVALID: {str(e)[:300]}")

    qs = data.get("questions", [])
    if len(qs) != 140:
        errs.append(f"question count = {len(qs)} (expected 140)")
    dist = dict(Counter(q.get("type") for q in qs))
    if dist != EXPECTED_DIST:
        errs.append(f"type distribution {dist} != expected {EXPECTED_DIST}")

    outcomes = data.get("learning_outcomes", [])
    codes = {o.get("code") for o in outcomes}
    if len(outcomes) != 8:
        errs.append(f"{len(outcomes)} outcomes (expected 8)")
    bad = {q.get("outcome_code") for q in qs} - codes
    if bad:
        errs.append(f"question outcome_codes not declared: {sorted(bad)}")

    topics = data.get("topics", [])
    if len(topics) != 6:
        errs.append(f"{len(topics)} topics (expected 6)")

    ws = data.get("worksheet", {})
    ws_qs = ws.get("questions", [])
    ws_sum = sum(int(q.get("marks", 0)) for q in ws_qs)
    if ws.get("total_marks") != ws_sum:
        errs.append(f"worksheet total_marks {ws.get('total_marks')} != sum {ws_sum}")
    if len(ws_qs) != 10:
        errs.append(f"{len(ws_qs)} worksheet questions (expected 10)")

    return errs


def main() -> None:
    args = sys.argv[1:]
    paths = [Path(a) for a in args]
    if not paths:
        print("usage: validate_sanskrit_bundles.py <file.json> [...]")
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
            print(f"[VALID] {p.name}")
    print("\nRESULT:", "ALL VALID" if all_ok else "FAILURES PRESENT")
    raise SystemExit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
