# Content Bundle Format (v1.0)

A single JSON file that loads any subset of a chapter's content into the
platform. Authors prepare one bundle per chapter and hand it to an admin
(or upload via the ingester script) — the system inserts only the parts
that are present in the JSON.

## When to use this

Anyone (subject teachers, content team, partners) preparing chapter
content for a board/class/subject the platform already knows about.

If the platform does NOT yet have the curriculum scaffold (the
`board`/`subject`/`book`/`chapter` rows), ask an admin to run the
scaffold step first. The ingester refuses to auto-create curriculum
hierarchy to avoid typo-driven duplicates.

## Quick start

1. Pick a starting point:
   - **Just want to add questions?** Copy `example_questions_only.json`.
     Only `subject`, `chapter_title` and `questions` needed.
   - **Loading multiple content blocks?** Copy `example_minimal.json` or
     `example_full.json`.
2. Edit the curriculum coordinates and any content you want to load.
3. Validate without writing to the DB:
   ```
   PYTHONPATH=. .venv/Scripts/python.exe -m scripts.ingest_content_bundle path/to/my_bundle.json --dry-run
   ```
4. When happy, run without `--dry-run` to actually load.

## Mandatory fields

Every bundle MUST have:

```json
{
  "schema_version": "1.0",
  "curriculum": {
    "subject": "Physics",                     // case-insensitive match against the DB
    "chapter_title": "Motion in a Plane"      // case-insensitive match against the DB
  }
}
```

That's it. The ingester finds the chapter by `(subject, chapter_title)`.

If the same `(subject, chapter_title)` exists in more than one place
(e.g. NIOS and CBSE both have "Physics" → "Motion in a Plane"), the
ingester returns an actionable error listing the candidates and asks you
to add one or more **disambiguators**:

| Disambiguator | Default | Purpose |
|---|---|---|
| `board` | (any) | One of CBSE, NIOS, ICSE, State Board, Other |
| `class_level` | (any) | Integer 1-12 |
| `chapter_number` | (any) | Integer; used as primary key inside the resolved book |
| `book_title` | (any) | Exact book title match |
| `language` | `"en"` | ISO language tag |
| `academic_year` | `"2026-27"` | Tag for `generated_contents` rows |

When you provide `chapter_number`, the lookup is by number and
`chapter_title` is just a sanity check (catches wrong-chapter uploads).

## Optional content blocks

Include any subset. Anything absent is silently ignored.

### `meta` — provenance (recommended)

```json
"meta": {
  "source": "NIOS Official",
  "author": "Platform Team",
  "notes": "Free-form notes for the audit log."
}
```

`source` is stored on every inserted/replaced `generated_contents.llm_provider`
column; `author` goes into `llm_model`. Use these to track where the
content came from.

### `chapter_text` — replaces `chapter.full_text`

```json
"chapter_text": "CHAPTER 4 — MOTION IN A PLANE\n\nIntroduction. ..."
```

Free-form string. Used by the topic-scoped AI tutor as the context
window. Replaces (not appends to) the existing chapter text.

### `topics` — inserted idempotently

```json
"topics": [
  {
    "name": "Projectile Motion",
    "description": "Motion under gravity in 2D...",
    "full_text": "Optional per-topic slice of the chapter text."
  }
]
```

Existing topics with the same name on the same chapter are left
untouched.

### `learning_outcomes` — inserted idempotently by code

```json
"learning_outcomes": [
  {
    "code": "12-NIOS-PHY-MIP-06",
    "description": "Apply the projectile-motion equations...",
    "bloom": "apply",                  // remember | understand | apply | analyze | evaluate | create
    "topic_name": "Projectile Motion"  // optional — must match a topic in this bundle or the DB
  }
]
```

Existing outcomes with the same code on the same chapter are left
untouched.

### `chapter_summary` — replaces the chapter summary

Schema: `ChapterSummaryOutput` (see `app/llm/schemas/chapter_summary.py`).
At a minimum:

```json
"chapter_summary": {
  "title": "...",
  "intro": "...",
  "overview_diagram": {
    "title": "...",
    "central_term": "...",
    "branches": [
      {"label": "Branch 1", "details": ["fact a", "fact b"]},
      {"label": "Branch 2", "details": ["fact c"]},
      {"label": "Branch 3", "details": ["fact d"]}
    ]
  },
  "sections": [
    {"heading": "First section", "bullets": ["b1", "b2", "b3"]}
  ],
  "key_takeaways": ["t1", "t2", "t3"],
  "glossary": [
    {"term": "Term A", "definition": "Definition of A (10+ chars)."},
    {"term": "Term B", "definition": "Definition of B."},
    {"term": "Term C", "definition": "Definition of C."}
  ]
}
```

Requires at least 3 sections, 3 takeaways, 3 glossary terms; each
section has 3-8 bullets. See the schema file for the full constraint
list. **Replaces** the existing chapter_summary row.

### `lesson_plan` — replaces the lesson plan

Schema: `LessonPlanOutput`. Includes `title`, `class_level`, `subject`,
`chapter_title`, `duration_minutes`, `objectives` (≥ 2), `activities`
(≥ 2, each with `phase`, `duration_minutes`, `description`,
`teacher_actions`), plus optional `prerequisites`, `materials`,
`key_vocabulary`, `homework`, `assessment_ideas`, `references`,
`outcome_codes_covered`. See `example_full.json`. **Re-rendered to DOCX**
on ingest.

### `worksheet` — replaces the worksheet

Schema: `WorksheetOutput`. `title`, `instructions`, `total_marks`
(MUST equal the sum of question marks), `questions` (1-30). Questions
support: MCQ (4 options), TRUE_FALSE (["True","False"]), FILL_BLANK,
SHORT_ANSWER, LONG_ANSWER, CASE_BASED. See `example_full.json`.
**Re-rendered to PDF** on ingest.

### `ppt` — replaces the slide deck

Schema: `PPTOutlineOutput`. 4-20 slides; first must be `TITLE`, last 1-2
must include `SUMMARY`. Slide types: `TITLE`, `OBJECTIVES`, `CONCEPT`,
`EXAMPLE`, `ACTIVITY`, `QUICK_CHECK`, `SUMMARY`. **Re-rendered to PPTX**
on ingest.

### `diagram` — replaces the concept-map diagram

Schema: `DiagramOutput`. Central term + 3-6 branches, each with up to 5
details. **Re-rendered to SVG** on ingest. *(Optional — leave out if not
preparing diagrams.)*

### `simulation` — replaces the interactive sim

Schema: `SimulationOutput`. Requires a `template` (`match_pairs`,
`categorize`, `timeline_order`, etc.) plus the matching template-
specific fields. **Re-rendered to HTML** on ingest. *(Optional — leave
out if not preparing sims.)*

### `questions` — inserted idempotently

```json
"questions": [
  {
    "type": "MCQ",                          // MCQ | TRUE_FALSE | FILL_BLANK | SHORT_ANSWER | LONG_ANSWER | CASE_BASED
    "question": "...",
    "options": ["a","b","c","d"],           // only for MCQ (4) or TRUE_FALSE (["True","False"])
    "answer": "...",
    "explanation": "...",                   // optional
    "marks": 1,
    "difficulty": "EASY",                   // EASY | MEDIUM | HARD
    "cognitive_level": "REMEMBER",          // REMEMBER | UNDERSTAND | APPLY | ANALYZE | EVALUATE | CREATE
    "outcome_code": "12-NIOS-PHY-MIP-06"    // optional
  }
]
```

Questions are deduped by exact `question` text on the chapter, so
re-running is safe.

## Replace vs append rules — summary

| Field | Behaviour |
|---|---|
| `chapter_text` | **Replaces** `chapter.full_text` |
| `topics` | **Inserts** new topics (skips if same name exists) |
| `learning_outcomes` | **Inserts** new outcomes (skips if same code exists) |
| `chapter_summary` | **Replaces** existing summary row |
| `lesson_plan` | **Replaces** existing lesson plan row + re-renders DOCX |
| `worksheet` | **Replaces** existing worksheet row + re-renders PDF |
| `ppt` | **Replaces** existing PPT row + re-renders PPTX |
| `diagram` | **Replaces** existing diagram row + re-renders SVG |
| `simulation` | **Replaces** existing simulation row + re-renders HTML |
| `questions` | **Inserts** new questions (skips if same text exists) |

## CLI usage

Single bundle:
```
PYTHONPATH=. .venv/Scripts/python.exe -m scripts.ingest_content_bundle scripts/content_bundle_examples/example_minimal.json
```

A whole folder of bundles:
```
PYTHONPATH=. .venv/Scripts/python.exe -m scripts.ingest_content_bundle path/to/bundles/
```

Validate only (no DB writes):
```
PYTHONPATH=. .venv/Scripts/python.exe -m scripts.ingest_content_bundle path/to/bundle.json --dry-run
```

Attribute rows to a specific user:
```
PYTHONPATH=. .venv/Scripts/python.exe -m scripts.ingest_content_bundle bundle.json --created-by-id 42
```

## Validation tips

- Use `--dry-run` first. Most errors caught at validation (bad enum
  values, missing required sub-fields, MCQ option mismatches) are
  reported with a precise field path.
- `total_marks` on the worksheet MUST equal the sum of its question
  marks. Pydantic refuses bundles where these don't match.
- The chapter title in `curriculum.chapter_title` is checked
  case-insensitively against what the DB has. A mismatch causes an
  error to catch wrong-chapter uploads.
- If you see `Subject not found: board=... class=... name=...`, the
  curriculum hasn't been scaffolded. Ask an admin.

## Adding a new optional content block

If a new content type is added later (e.g. `flow_diagram`):
1. Add the field to `app/schemas/content_bundle.py`.
2. Add an entry to `_BLOB_SPECS` in
   `app/services/content_bundle_service.py` with the appropriate
   renderer / extension.
3. Update this README.
4. Bump `schema_version` if existing bundles would now mean something
   different.
