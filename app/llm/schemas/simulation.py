from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ---------- match_pairs ----------

class MatchPair(BaseModel):
    term: str = Field(min_length=1, max_length=80)
    match: str = Field(min_length=3, max_length=240)


# ---------- categorize ----------

class CategorizeBin(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=240)


class CategorizeItem(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    correct_bin: str = Field(min_length=1, max_length=60)
    explanation: str | None = Field(default=None, max_length=240)


# ---------- timeline_order (2D) ----------

class TimelineEvent(BaseModel):
    """One step in a sequenced process. The `correct_position` is the
    1-indexed slot where this event belongs in the correct order — the
    template shuffles events for the student and grades against this.
    """

    label: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=240)
    correct_position: int = Field(ge=1, le=20)


# ---------- three_d_projectile ----------

class ProjectileConfig(BaseModel):
    """Initial conditions + ground for a 3D projectile-motion sim.

    Sliders in the template let the student vary `launch_speed_mps`,
    `launch_angle_deg`, `gravity_mps2` and `azimuth_deg` (compass
    direction in the horizontal plane). The trajectory animates in
    real time and the panel reports range, max height and time of
    flight.
    """

    launch_speed_mps: float = Field(default=20.0, ge=1.0, le=200.0)
    launch_angle_deg: float = Field(default=45.0, ge=0.0, le=89.9)
    gravity_mps2: float = Field(default=9.8, ge=0.5, le=30.0)
    azimuth_deg: float = Field(default=0.0, ge=0.0, le=360.0)
    # Display scale: how many scene units per metre. Helps keep big
    # ranges visible without zooming out.
    scene_units_per_metre: float = Field(default=0.5, ge=0.05, le=10.0)


# ---------- three_d_orbit ----------

class OrbitBody(BaseModel):
    """One orbiting body. Orbit radius is in scene units (cap 15).
    `period_seconds` sets the animation timing — smaller = faster.
    Inclination tilts the orbit from the equatorial (xz) plane.
    """

    name: str = Field(min_length=1, max_length=60)
    description: str = Field(min_length=5, max_length=300)
    radius: float = Field(ge=0.5, le=15.0, description="Orbit radius in scene units")
    period_seconds: float = Field(ge=1.0, le=120.0, description="Wall-clock seconds per orbit")
    size: float = Field(default=0.6, ge=0.1, le=3.0)
    color: str | None = Field(default=None, max_length=20, description="Hex like '#3b82f6'")
    inclination_deg: float = Field(default=0.0, ge=-89.0, le=89.0)
    phase_deg: float = Field(default=0.0, ge=0.0, le=360.0)


class OrbitScene(BaseModel):
    """The central body (e.g. Sun, nucleus) and the orbiting satellites."""

    central_name: str = Field(min_length=1, max_length=60)
    central_description: str = Field(min_length=5, max_length=300)
    central_size: float = Field(default=1.5, ge=0.2, le=4.0)
    central_color: str | None = Field(default=None, max_length=20)
    bodies: list[OrbitBody] = Field(min_length=1, max_length=10)


# ---------- three_d_field_lines ----------

class PointCharge(BaseModel):
    """One source for a 3D field-line plot. Position in scene units
    (cap 15). For an electric field, `magnitude` carries sign (+ /−);
    for gravitational fields keep it positive."""

    name: str = Field(min_length=1, max_length=60)
    x: float = Field(ge=-15.0, le=15.0)
    y: float = Field(ge=-15.0, le=15.0)
    z: float = Field(ge=-15.0, le=15.0)
    magnitude: float = Field(ge=-10.0, le=10.0, description="Sign carries field direction")
    label: str | None = Field(default=None, max_length=40)


class FieldLineScene(BaseModel):
    """Vector-field visualisation: 3D field lines streaming from
    point sources. `field_kind` controls colour / orientation
    semantics (electric flips on negative charges; gravitational
    always points inward; magnetic loops between poles).
    """

    field_kind: Literal["electric", "gravitational", "magnetic"]
    sources: list[PointCharge] = Field(min_length=1, max_length=8)
    line_density: int = Field(default=18, ge=6, le=48, description="Lines per source")
    line_length: float = Field(default=12.0, ge=2.0, le=30.0)


# ---------- three_d_wave ----------

class WaveScene(BaseModel):
    """Animated wave on a 1-D string in 3D. Sliders let the student
    vary amplitude, wavelength and frequency. `wave_kind` switches
    the visual mode: 'transverse' shows up/down displacement,
    'longitudinal' shows compressions / rarefactions, 'standing'
    shows superposition of two opposite travelling waves.
    """

    wave_kind: Literal["transverse", "longitudinal", "standing"] = "transverse"
    amplitude: float = Field(default=1.5, ge=0.1, le=4.0, description="Initial amplitude (scene units)")
    wavelength: float = Field(default=4.0, ge=0.5, le=20.0)
    frequency_hz: float = Field(default=0.5, ge=0.05, le=5.0)
    string_length: float = Field(default=20.0, ge=5.0, le=40.0)
    show_axes: bool = Field(default=True)


# ---------- graph_explorer (Math, Physics, Chem, Econ — universal) ----------

class GraphSlider(BaseModel):
    """One adjustable parameter shown as a slider. The `name` must
    match a free variable in the math expression. Sliders are evaluated
    in math.js syntax — safe, no JS eval at render time.
    """

    name: str = Field(min_length=1, max_length=20)
    label: str = Field(min_length=1, max_length=60)
    min: float
    max: float
    initial: float
    step: float = Field(default=0.1, gt=0.0)
    unit: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def _check_range(self) -> "GraphSlider":
        if self.max <= self.min:
            raise ValueError(f"slider {self.name!r}: max must be > min")
        if not (self.min <= self.initial <= self.max):
            raise ValueError(f"slider {self.name!r}: initial must lie in [min, max]")
        return self


class GraphExplorer(BaseModel):
    """Slider-driven function plotter. The expression is in math.js
    syntax (e.g. ``a * sin(b * x + c)``). Evaluation happens in the
    browser via the math.js library; no eval-style JS execution.
    """

    expression: str = Field(min_length=1, max_length=300)
    x_var: str = Field(default="x", min_length=1, max_length=20)
    x_min: float
    x_max: float
    x_label: str = Field(default="x", min_length=1, max_length=60)
    y_label: str = Field(default="y", min_length=1, max_length=60)
    sliders: list[GraphSlider] = Field(default_factory=list, max_length=8)
    constants: dict[str, float] | None = Field(
        default=None,
        description="Fixed values for symbols not exposed as sliders, e.g. {'g': 9.8}.",
    )
    samples: int = Field(default=200, ge=20, le=600)

    @model_validator(mode="after")
    def _check_x_range(self) -> "GraphExplorer":
        if self.x_max <= self.x_min:
            raise ValueError("x_max must be > x_min")
        return self


# ---------- labeled_hotspots (Bio anatomy, Chem apparatus, Geography, Languages) ----------

class Hotspot(BaseModel):
    """A circular click target on top of an image. Coordinates are
    percentages of the displayed image so the layout stays correct
    across screen sizes. `radius_pct` is half-width / 50.
    """

    label: str = Field(min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=300)
    x_pct: float = Field(ge=0.0, le=100.0)
    y_pct: float = Field(ge=0.0, le=100.0)
    radius_pct: float = Field(default=4.0, ge=1.0, le=15.0)


class LabeledHotspots(BaseModel):
    """Image with clickable hotspots. In `quiz_mode=True`, the labels
    are hidden and the student drags labels onto the right hotspots.

    ``image_url`` accepts either a normal http(s) URL OR a ``data:``
    URL with an inline SVG / PNG. Inline data URLs are preferred for
    diagrams the LLM authors itself, since they ship inside the
    artifact (no external dependency, no CSP / referrer issues, no
    upstream URL drift).
    """

    image_url: str = Field(min_length=1, max_length=200_000)
    image_alt: str = Field(default="Diagram", max_length=200)
    hotspots: list[Hotspot] = Field(min_length=2, max_length=30)
    quiz_mode: bool = Field(default=False)


# ---------- sentence_builder (Languages, Math proofs, Logic) ----------

class SentenceTile(BaseModel):
    """One movable tile. `correct_position` is 1-indexed."""

    text: str = Field(min_length=1, max_length=80)
    correct_position: int = Field(ge=1, le=40)


class SentenceBuilder(BaseModel):
    """Drag tiles into the correct order to form a sentence /
    expression / proof. `distractor_tiles` are extra tiles that do
    NOT belong — useful in language drills.
    """

    target_label: str | None = Field(
        default=None,
        max_length=240,
        description="What the student is building (e.g. an English translation).",
    )
    tiles: list[SentenceTile] = Field(min_length=2, max_length=20)
    distractor_tiles: list[str] | None = Field(default=None, max_length=10)


# ---------- vocab_pairs (Languages) ----------

class VocabCard(BaseModel):
    """One vocab card. `audio_url` and `image_url` are optional;
    when present, the renderer surfaces play and image tiles."""

    term: str = Field(min_length=1, max_length=80)
    translation: str = Field(min_length=1, max_length=120)
    audio_url: str | None = Field(default=None, max_length=2048)
    image_url: str | None = Field(default=None, max_length=2048)
    note: str | None = Field(default=None, max_length=200)


class VocabPairs(BaseModel):
    """A vocabulary practice mini-game. ``mode='pairs'`` shows
    two columns (term vs translation) and asks the student to draw
    matches. ``mode='memory'`` lays the cards face-down for a
    flip-and-find game.
    """

    cards: list[VocabCard] = Field(min_length=4, max_length=24)
    mode: Literal["pairs", "memory"] = "pairs"


# ---------- molecule_3d (Chemistry, Biology) ----------

class Atom(BaseModel):
    """One atom in a 3D molecule. ``element`` is the periodic-table
    symbol (e.g. ``H``, ``O``, ``C``). ``color`` overrides the
    default CPK colouring.
    """

    name: str = Field(min_length=1, max_length=20)
    element: str = Field(min_length=1, max_length=2)
    x: float = Field(ge=-15.0, le=15.0)
    y: float = Field(ge=-15.0, le=15.0)
    z: float = Field(ge=-15.0, le=15.0)
    color: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=240)


class Bond(BaseModel):
    """A bond between two atoms by ``name``. ``order`` is 1 (single),
    2 (double) or 3 (triple).
    """

    from_atom: str = Field(min_length=1, max_length=20)
    to_atom: str = Field(min_length=1, max_length=20)
    order: int = Field(default=1, ge=1, le=3)


class Molecule3D(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=5, max_length=600)
    atoms: list[Atom] = Field(min_length=2, max_length=80)
    bonds: list[Bond] = Field(default_factory=list, max_length=120)


# ---------- circuit_2d (Physics electricity) ----------

class CircuitComponent(BaseModel):
    """One drawn circuit component. ``kind`` controls the symbol the
    renderer draws; ``value`` carries the numerical parameter (Ω, V,
    F, ...) and ``unit`` overrides the default unit string.
    Coordinates are in scene grid cells (0..40 horizontally,
    0..24 vertically). Rotation in 90° steps."""

    kind: Literal[
        "battery", "resistor", "bulb", "switch", "capacitor",
        "ammeter", "voltmeter", "junction",
    ]
    name: str = Field(min_length=1, max_length=20)
    value: float | None = Field(default=None)
    unit: str | None = Field(default=None, max_length=20)
    x: float = Field(ge=0.0, le=40.0)
    y: float = Field(ge=0.0, le=24.0)
    rotation: int = Field(default=0)

    @model_validator(mode="after")
    def _check_rotation(self) -> "CircuitComponent":
        if self.rotation not in (0, 90, 180, 270):
            raise ValueError("rotation must be 0, 90, 180 or 270")
        return self


class CircuitWire(BaseModel):
    """Connection between two components by ``name``."""

    from_component: str = Field(min_length=1, max_length=20)
    to_component: str = Field(min_length=1, max_length=20)


class Circuit2D(BaseModel):
    """Schematic-style circuit with computed readouts.

    The renderer auto-computes total resistance / current for
    series-only and parallel-only resistor networks; for richer
    topologies it just labels each component with its declared
    value. Use ``analysis`` to pick which automatic computation to
    show: ``"series"``, ``"parallel"`` or ``"none"``.
    """

    description: str = Field(min_length=5, max_length=600)
    analysis: Literal["series", "parallel", "none"] = "none"
    components: list[CircuitComponent] = Field(min_length=2, max_length=20)
    wires: list[CircuitWire] = Field(default_factory=list, max_length=40)


# ---------- custom_html (Tier 2 escape hatch) ----------

class CustomHtml(BaseModel):
    """Custom, fully bespoke per-lesson simulation. The LLM (or a
    platform admin) authors a complete self-contained HTML document
    in ``html_body``. The renderer wraps it inside a parent page
    that contains a single ``<iframe sandbox="allow-scripts">`` whose
    ``srcdoc`` is the author's HTML.

    Security posture (matters because the body is arbitrary JS):
      - Sandbox is ``allow-scripts`` ONLY. No ``allow-same-origin``,
        ``allow-top-navigation``, ``allow-popups`` or ``allow-forms``.
      - The iframe runs as an opaque "null" origin: no cookies, no
        access to platform localStorage / sessionStorage, no DOM
        access into the parent page, no fetches with credentials.
      - The iframe CAN load CDN scripts (Three.js, d3, math.js, etc.)
        but cannot exfiltrate platform data because it has no access
        to it in the first place.
      - Status defaults to READY (not APPROVED) for LLM-generated
        rows; a platform admin must publish via the existing
        ``/generation/{id}/publish`` endpoint to expose to students.

    ``html_body`` MUST be a complete document (``<!DOCTYPE html>...``
    or at minimum ``<html>...</html>``). 200 KB cap is generous for
    even the most elaborate single-file simulations.
    """

    html_body: str = Field(
        min_length=20,
        max_length=200_000,
        description=(
            "Complete self-contained HTML document. Will run inside a "
            "sandboxed iframe; CDN script tags are permitted."
        ),
    )
    requires_libraries: list[str] = Field(
        default_factory=list,
        max_length=10,
        description=(
            "Optional, informational list of CDN libraries the body "
            "uses (e.g. ['three@0.164', 'd3@7']). The sandbox does "
            "NOT enforce this list — it's a hint for reviewers."
        ),
    )


# ---------- three_d_scene ----------

class SceneObject3D(BaseModel):
    """One object placed in a generic 3D educational scene.

    Position is in scene units in the range ``[-15, 15]`` on each axis. The
    LLM picks positions deliberately to express the chapter's structure —
    e.g. layers stacked vertically (varying ``y``), a network spread in the
    ``x``/``z`` plane, or a hub-and-spoke arrangement. There is no implied
    orbital or concentric layout.

    `kind` is a short label shown in the info panel ("Layer", "Organ",
    "Predator", "Stage", ...). It is purely informational and free-form.

    `color` is an optional hex string (e.g. "#3b82f6"); if omitted the
    renderer assigns from a high-contrast palette so each object on screen
    is visually distinct.
    """

    name: str = Field(min_length=1, max_length=60)
    kind: str = Field(
        default="node",
        min_length=1,
        max_length=30,
        description="Short type label shown in the info panel.",
    )
    description: str = Field(
        min_length=10,
        max_length=400,
        description="Age-appropriate 1-3 sentence description.",
    )
    fun_fact: str | None = Field(
        default=None,
        max_length=200,
        description="One memorable fact shown when the student clicks the object.",
    )

    x: float = Field(ge=-15, le=15, description="Horizontal position.")
    y: float = Field(
        ge=-15,
        le=15,
        description=(
            "Vertical position. Higher = up. Use this to encode hierarchy "
            "(e.g. predators above prey, sky above ground, leaves above roots)."
        ),
    )
    z: float = Field(ge=-15, le=15, description="Depth position.")
    size: float = Field(
        default=1.0,
        ge=0.2,
        le=5.0,
        description="Sphere radius in scene units. Bigger = more important / larger.",
    )
    color: str | None = Field(
        default=None,
        max_length=20,
        description="Hex like '#3b82f6'. Optional; renderer assigns one if omitted.",
    )


class SceneEdge3D(BaseModel):
    """A connection drawn between two scene objects.

    Use edges to express relationships: "eats", "evaporates to",
    "transforms into", "is part of". Each edge references both endpoints by
    object name (must match an object in `objects_3d` exactly). Optional
    `label` appears at the midpoint of the edge.
    """

    from_name: str = Field(min_length=1, max_length=60)
    to_name: str = Field(min_length=1, max_length=60)
    label: str | None = Field(default=None, max_length=60)


# ---------- combined output ----------

SimulationTemplate = Literal[
    "match_pairs",
    "categorize",
    "three_d_scene",
    "timeline_order",
    "three_d_projectile",
    "three_d_orbit",
    "three_d_field_lines",
    "three_d_wave",
    "graph_explorer",
    "labeled_hotspots",
    "sentence_builder",
    "vocab_pairs",
    "molecule_3d",
    "circuit_2d",
    "custom_html",
]


class SimulationOutput(BaseModel):
    """Parameters for a simulation template.

    Exactly one set of template-specific fields must be populated, selected by
    the `template` discriminator. Adding a new template is a drop-in: add a
    Literal value, the matching optional field(s), and a branch in the
    validator below.
    """

    template: SimulationTemplate
    title: str = Field(min_length=5, max_length=200)
    instructions: str = Field(min_length=10, max_length=500)
    outcome_codes_covered: list[str] = Field(default_factory=list)

    pairs: list[MatchPair] | None = None
    bins: list[CategorizeBin] | None = None
    items: list[CategorizeItem] | None = None
    objects_3d: list[SceneObject3D] | None = None
    edges_3d: list[SceneEdge3D] | None = None
    # New 2D template
    events_timeline: list[TimelineEvent] | None = None
    # New 3D templates
    projectile: ProjectileConfig | None = None
    orbit: OrbitScene | None = None
    field_lines: FieldLineScene | None = None
    wave: WaveScene | None = None
    # Cross-subject expansion (Tier 1):
    graph: GraphExplorer | None = None
    hotspots: LabeledHotspots | None = None
    sentence: SentenceBuilder | None = None
    vocab: VocabPairs | None = None
    molecule: Molecule3D | None = None
    circuit: Circuit2D | None = None
    # Tier 2 escape hatch — bespoke per-lesson HTML, run sandboxed.
    custom: CustomHtml | None = None

    @model_validator(mode="after")
    def _check_template_fields(self) -> "SimulationOutput":
        if self.template == "match_pairs":
            if not self.pairs or len(self.pairs) < 4:
                raise ValueError("match_pairs requires at least 4 pairs")
        elif self.template == "categorize":
            if not self.bins or len(self.bins) < 2:
                raise ValueError("categorize requires at least 2 bins")
            if not self.items or len(self.items) < 4:
                raise ValueError("categorize requires at least 4 items")
            bin_names = {b.name for b in self.bins}
            for item in self.items:
                if item.correct_bin not in bin_names:
                    raise ValueError(
                        f"categorize item '{item.name}' has correct_bin "
                        f"'{item.correct_bin}' not in bins {sorted(bin_names)}"
                    )
        elif self.template == "timeline_order":
            if not self.events_timeline or len(self.events_timeline) < 3:
                raise ValueError("timeline_order requires at least 3 events")
            positions = [e.correct_position for e in self.events_timeline]
            n = len(self.events_timeline)
            expected = set(range(1, n + 1))
            if set(positions) != expected:
                raise ValueError(
                    f"timeline_order positions must be a permutation of "
                    f"1..{n}; got {sorted(positions)}"
                )
        elif self.template == "three_d_projectile":
            if self.projectile is None:
                raise ValueError("three_d_projectile requires the `projectile` field")
        elif self.template == "three_d_orbit":
            if self.orbit is None:
                raise ValueError("three_d_orbit requires the `orbit` field")
        elif self.template == "three_d_field_lines":
            if self.field_lines is None:
                raise ValueError("three_d_field_lines requires the `field_lines` field")
        elif self.template == "three_d_wave":
            if self.wave is None:
                raise ValueError("three_d_wave requires the `wave` field")
        elif self.template == "graph_explorer":
            if self.graph is None:
                raise ValueError("graph_explorer requires the `graph` field")
        elif self.template == "labeled_hotspots":
            if self.hotspots is None:
                raise ValueError("labeled_hotspots requires the `hotspots` field")
        elif self.template == "sentence_builder":
            if self.sentence is None:
                raise ValueError("sentence_builder requires the `sentence` field")
            n = len(self.sentence.tiles)
            positions = [t.correct_position for t in self.sentence.tiles]
            if set(positions) != set(range(1, n + 1)):
                raise ValueError(
                    f"sentence_builder tiles' correct_position values must be a "
                    f"permutation of 1..{n}; got {sorted(positions)}"
                )
        elif self.template == "vocab_pairs":
            if self.vocab is None:
                raise ValueError("vocab_pairs requires the `vocab` field")
        elif self.template == "molecule_3d":
            if self.molecule is None:
                raise ValueError("molecule_3d requires the `molecule` field")
            atom_names = {a.name for a in self.molecule.atoms}
            if len(atom_names) != len(self.molecule.atoms):
                raise ValueError("molecule_3d atom names must be unique")
            for b in (self.molecule.bonds or []):
                if b.from_atom not in atom_names:
                    raise ValueError(f"bond from_atom {b.from_atom!r} not in atoms")
                if b.to_atom not in atom_names:
                    raise ValueError(f"bond to_atom {b.to_atom!r} not in atoms")
                if b.from_atom == b.to_atom:
                    raise ValueError(f"bond connects atom {b.from_atom!r} to itself")
        elif self.template == "circuit_2d":
            if self.circuit is None:
                raise ValueError("circuit_2d requires the `circuit` field")
            comp_names = {c.name for c in self.circuit.components}
            if len(comp_names) != len(self.circuit.components):
                raise ValueError("circuit_2d component names must be unique")
            for w in (self.circuit.wires or []):
                if w.from_component not in comp_names:
                    raise ValueError(f"wire from_component {w.from_component!r} not in components")
                if w.to_component not in comp_names:
                    raise ValueError(f"wire to_component {w.to_component!r} not in components")
        elif self.template == "custom_html":
            if self.custom is None:
                raise ValueError("custom_html requires the `custom` field")
            # Quick sanity-check that the body looks like HTML; full
            # validation is impossible without running it, and that's
            # what the iframe sandbox is for.
            body = self.custom.html_body.lstrip().lower()
            if not (body.startswith("<!doctype") or body.startswith("<html") or body.startswith("<body")):
                raise ValueError(
                    "custom_html: html_body should start with <!DOCTYPE html>, "
                    "<html> or <body> (a complete document or rooted fragment)"
                )
        elif self.template == "three_d_scene":
            if not self.objects_3d or len(self.objects_3d) < 3:
                raise ValueError("three_d_scene requires at least 3 objects")
            names = [o.name for o in self.objects_3d]
            if len(set(names)) != len(names):
                raise ValueError("three_d_scene object names must be unique")
            name_set = set(names)
            for edge in self.edges_3d or []:
                if edge.from_name not in name_set:
                    raise ValueError(
                        f"edge from_name '{edge.from_name}' is not an object name"
                    )
                if edge.to_name not in name_set:
                    raise ValueError(
                        f"edge to_name '{edge.to_name}' is not an object name"
                    )
                if edge.from_name == edge.to_name:
                    raise ValueError(
                        f"edge connects '{edge.from_name}' to itself"
                    )
        return self
