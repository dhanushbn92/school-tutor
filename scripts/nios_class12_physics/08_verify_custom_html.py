"""Smoke-test the custom_html escape hatch:

  1. Validate a sample CustomHtml payload against the schema.
  2. Render it through render_simulation_html.
  3. Assert the output contains exactly one sandboxed iframe with the
     correct sandbox tokens (allow-scripts ONLY).
  4. Assert the body's `&` and `"` were escaped for srcdoc, but other
     characters (e.g. `<script>`, `</iframe>`) survive intact so the
     iframe sees the original document.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class12_physics/08_verify_custom_html.py
"""

import json
import re
import sys
from pathlib import Path

from app.llm.schemas.simulation import SimulationOutput
from app.rendering.simulation_html import render_simulation_html


SAMPLE_PATH = (
    Path(__file__).parent / "data" / "ch75_sim_custom_collision.json"
)


def main() -> int:
    payload = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    sim = SimulationOutput.model_validate(payload)
    rendered = render_simulation_html(sim).decode("utf-8")

    failures: list[str] = []

    # 1. Exactly one iframe.
    iframes = re.findall(r"<iframe\b[^>]*>", rendered, flags=re.I)
    if len(iframes) != 1:
        failures.append(f"expected exactly 1 iframe, found {len(iframes)}")

    # 2. Sandbox attribute is exactly "allow-scripts" — no allow-same-origin etc.
    iframe_tag = iframes[0] if iframes else ""
    sandbox_match = re.search(r'sandbox="([^"]*)"', iframe_tag, flags=re.I)
    if not sandbox_match:
        failures.append("iframe has no sandbox attribute")
    else:
        tokens = set(sandbox_match.group(1).split())
        if tokens != {"allow-scripts"}:
            failures.append(
                f"sandbox tokens must be exactly {{'allow-scripts'}}; got {tokens}"
            )
        # Defence-in-depth: catch any of the dangerous tokens explicitly.
        forbidden = {"allow-same-origin", "allow-top-navigation", "allow-popups", "allow-forms", "allow-modals", "allow-pointer-lock"}
        leaked = forbidden & tokens
        if leaked:
            failures.append(f"sandbox includes forbidden tokens: {leaked}")

    # 3. Body content survived: srcdoc must contain (HTML-escaped) tokens
    # from the LLM HTML body. Pick a few unique strings from our demo.
    must_contain_in_srcdoc = [
        "1D Collision sandbox",     # title inside the LLM doc
        "postCollision",             # function name in the LLM JS
        "&lt;canvas",                # < was NOT escaped (only & and ") so this should NOT appear
    ]
    if "1D Collision sandbox" not in rendered:
        failures.append("rendered output missing the body's title text")
    if "postCollision" not in rendered:
        failures.append("rendered output missing the body's JS")
    # The LLM body contains literal `<canvas` and `</script>`. Inside an
    # attribute value those are fine — they don't need to be escaped
    # because attributes don't break out on raw `<`. So they should
    # appear LITERALLY in the rendered output (inside srcdoc=""):
    if "<canvas" not in rendered:
        failures.append("rendered output stripped <canvas — over-escaping")

    # 4. The escaping rule: `&` -> `&amp;`, `"` -> `&quot;` for srcdoc.
    # Our LLM body has `&&` (JS short-circuit), which becomes `&amp;&amp;`.
    if "&amp;&amp;" not in rendered and "&&" in payload["custom"]["html_body"]:
        failures.append("expected '&&' in body to be escaped to '&amp;&amp;' in srcdoc")
    # Body has " (e.g. id="root"); double-quotes must be escaped.
    if 'id=&quot;root&quot;' not in rendered and 'id="root"' in payload["custom"]["html_body"]:
        failures.append("expected double-quotes in body to be escaped to &quot;")

    # 5. Wrapper chrome present.
    for marker in ('class="badge"', "Sandboxed", "Hide chrome"):
        if marker not in rendered:
            failures.append(f"wrapper chrome marker missing: {marker!r}")

    print(f"Rendered artifact size: {len(rendered):,} bytes ({len(rendered)/1024:.1f} KB)")
    if iframe_tag:
        # Print just the iframe attributes for quick visual confirmation.
        print(f"iframe tag: {iframe_tag[:120]}...")
    if failures:
        print()
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print()
    print("OK: custom_html renders cleanly with sandbox=\"allow-scripts\" only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
