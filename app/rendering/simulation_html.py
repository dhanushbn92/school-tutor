import html
import json
from pathlib import Path

from app.llm.schemas.simulation import SimulationOutput


_TEMPLATES_DIR = Path(__file__).parent.parent / "sims" / "templates"


def render_simulation_html(sim: SimulationOutput) -> bytes:
    """Load the template for `sim.template` and inject its parameters.

    Each template is a self-contained HTML file with `__PLACEHOLDER__` markers.
    Adding a new template is: drop a `foo.html` in `app/sims/templates/`,
    add the matching `Literal` + fields on `SimulationOutput`, and add a branch
    below that substitutes the right placeholders.
    """
    template_path = _TEMPLATES_DIR / f"{sim.template}.html"
    if not template_path.is_file():
        raise ValueError(f"Unknown simulation template: {sim.template}")

    raw = template_path.read_text(encoding="utf-8")
    filled = (
        raw.replace("__TITLE__", html.escape(sim.title))
        .replace("__INSTRUCTIONS__", html.escape(sim.instructions))
    )

    if sim.template == "match_pairs":
        pairs_payload = json.dumps([{"term": p.term, "match": p.match} for p in (sim.pairs or [])])
        filled = filled.replace("__PAIRS_JSON__", pairs_payload)

    elif sim.template == "categorize":
        bins_payload = json.dumps(
            [{"name": b.name, "description": b.description} for b in (sim.bins or [])]
        )
        items_payload = json.dumps(
            [
                {
                    "name": i.name,
                    "correct_bin": i.correct_bin,
                    "explanation": i.explanation,
                }
                for i in (sim.items or [])
            ]
        )
        filled = filled.replace("__BINS_JSON__", bins_payload).replace(
            "__ITEMS_JSON__", items_payload
        )

    elif sim.template == "three_d_scene":
        objects_payload = json.dumps(
            [
                {
                    "name": o.name,
                    "kind": o.kind,
                    "description": o.description,
                    "fun_fact": o.fun_fact,
                    "x": o.x,
                    "y": o.y,
                    "z": o.z,
                    "size": o.size,
                    "color": o.color,
                }
                for o in (sim.objects_3d or [])
            ]
        )
        edges_payload = json.dumps(
            [
                {
                    "from_name": e.from_name,
                    "to_name": e.to_name,
                    "label": e.label,
                }
                for e in (sim.edges_3d or [])
            ]
        )
        filled = filled.replace("__OBJECTS_JSON__", objects_payload).replace(
            "__EDGES_JSON__", edges_payload
        )

    elif sim.template == "timeline_order":
        events_payload = json.dumps(
            [
                {
                    "label": e.label,
                    "description": e.description,
                    "correct_position": e.correct_position,
                }
                for e in (sim.events_timeline or [])
            ]
        )
        filled = filled.replace("__EVENTS_JSON__", events_payload)

    elif sim.template == "three_d_projectile":
        proj = sim.projectile
        # `proj` is guaranteed by the schema validator at this point.
        config_payload = json.dumps(proj.model_dump() if proj else {})
        filled = filled.replace("__CONFIG_JSON__", config_payload)

    elif sim.template == "three_d_orbit":
        orbit = sim.orbit
        config_payload = json.dumps(orbit.model_dump() if orbit else {})
        filled = filled.replace("__ORBIT_JSON__", config_payload)

    elif sim.template == "three_d_field_lines":
        fl = sim.field_lines
        config_payload = json.dumps(fl.model_dump() if fl else {})
        filled = filled.replace("__FIELD_JSON__", config_payload)

    elif sim.template == "three_d_wave":
        w = sim.wave
        config_payload = json.dumps(w.model_dump() if w else {})
        filled = filled.replace("__WAVE_JSON__", config_payload)

    elif sim.template == "graph_explorer":
        g = sim.graph
        filled = filled.replace("__GRAPH_JSON__", json.dumps(g.model_dump() if g else {}))

    elif sim.template == "labeled_hotspots":
        h = sim.hotspots
        filled = filled.replace("__HOTSPOTS_JSON__", json.dumps(h.model_dump() if h else {}))

    elif sim.template == "sentence_builder":
        s = sim.sentence
        filled = filled.replace("__SENTENCE_JSON__", json.dumps(s.model_dump() if s else {}))

    elif sim.template == "vocab_pairs":
        v = sim.vocab
        filled = filled.replace("__VOCAB_JSON__", json.dumps(v.model_dump() if v else {}))

    elif sim.template == "molecule_3d":
        m = sim.molecule
        filled = filled.replace("__MOLECULE_JSON__", json.dumps(m.model_dump() if m else {}))

    elif sim.template == "circuit_2d":
        c = sim.circuit
        filled = filled.replace("__CIRCUIT_JSON__", json.dumps(c.model_dump() if c else {}))

    elif sim.template == "custom_html":
        # Wrap the LLM-authored HTML inside a sandboxed iframe via
        # srcdoc. We need to escape only `&` and `"` for use inside a
        # double-quoted attribute; the HTML parser then decodes those
        # back when populating the iframe's document.
        body = (sim.custom.html_body if sim.custom else "")
        srcdoc = body.replace("&", "&amp;").replace('"', "&quot;")
        # Library hint for the trust badge in the wrapper chrome.
        libs = ", ".join(sim.custom.requires_libraries) if sim.custom and sim.custom.requires_libraries else ""
        filled = (
            filled.replace("__SRCDOC__", srcdoc)
            .replace("__LIBS__", html.escape(libs))
        )

    else:
        raise ValueError(f"No renderer branch for template {sim.template!r}")

    return filled.encode("utf-8")
