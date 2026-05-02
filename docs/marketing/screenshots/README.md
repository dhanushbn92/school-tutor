# Stakeholder brochure — screenshot guide

Drop screenshots into this folder using the **exact filenames** below, then
re-run the brochure generator:

```bash
.venv/Scripts/python.exe scripts/generate_platform_brochure.py
```

The brochure script picks up whichever files exist and skips the rest —
you can iterate, capturing one or two screenshots at a time and re-running.

## Capture tips

- **Window size**: maximise the browser to ~1440 x 900 (or 1600 x 900). Wider
  is fine; narrower than 1280 will start hiding sidebar labels.
- **Tool**: Windows → `Win + Shift + S` (Snipping Tool) is fastest. Capture
  the **whole browser content area** including the sidebar, *not* the URL bar.
- **Keep the sidebar visible** in every shot so the audience can see which
  role / view is active.
- **Don't include private data**. Use the demo accounts seeded in the local
  DB, not real students or staff names.
- **PNG only**, please. JPEGs will work but look blurrier on print.
- **Aspect ratio**: roughly 16:9 or wider works best — the brochure scales
  each shot to ~16.5 cm wide so very tall screenshots will look squashed.

## Files (capture as many as you want — missing ones are skipped)

### Platform admin

| Filename | What to capture |
|---|---|
| `01_platform_generate.png` | Sign in as `platform.team@anaadi.org` (or `admin@anaadi.demo`), open **Generate**. Pick Class 6 → Science → any chapter → Simulation (HTML). Capture before clicking Generate so the form is visible. |
| `02_question_bank.png` | **Question bank**, status filter set to **Approved** (so you can show several real questions). Make sure at least 2-3 question cards are visible with their bucket badges. |
| `03_tenants_schools.png` | **Tenants** → **Schools** tab. Should show the two demo schools with their student / teacher / section counts. |
| `04_tenant_school_detail.png` | Click into one of the schools (e.g. Anaadi Demo School). Capture the header with its stat cards + the **Disable school** button visible. |

### School admin

| Filename | What to capture |
|---|---|
| `05_manage_school_teachers.png` | Sign in as `admin@anaadi.demo`. **Manage school → Teachers**. Click **Edit subjects** on Priya so the inline editor is visible. Capture the row + editor + the chip showing assigned subjects. |
| `06_school_report.png` | **School report**. Make sure the **Weak topics** card is visible with at least one topic showing the Factual / Understanding / Application chips. (Take any quiz first if you don't have data — see step 10.) |

### Teacher

| Filename | What to capture |
|---|---|
| `07_teacher_dashboard.png` | Sign in as `priya.sharma@anaadi.demo` (after assignment). **Dashboard**. Show the class + subject picker plus the Weak Topics card. |
| `08_teacher_learn.png` | **Learn**. Should show only Class 6 + Science (because of strict scoping). |
| `09_new_quiz.png` | **Assessments → New quiz**. Section + Subject + Chapter pickers visible, with the difficulty / cognitive mix presets shown. |

### Student

| Filename | What to capture |
|---|---|
| `10_take_quiz.png` | Sign in as a student (`student01@anaadi.demo`). Take a quiz. Capture the question + answer-choices view *or* the post-submission feedback. |
| `11_report_card.png` | **Report card** — overall mastery + cognitive bucket breakdown. |
| `12_ai_tutor_chat.png` | Open AI tutor chat from a chapter. Send one on-topic question and one off-topic question (so the polite refusal shows). Capture the conversation. |

### Individual learner

| Filename | What to capture |
|---|---|
| `13_individual_dashboard.png` | Sign up a new individual learner (or use an existing one). Capture their dashboard. |
| `14_quick_quiz.png` | The **Start a quiz** flow — class + subject + chapter pickers + presets. |

### Highlights (cross-cutting, optional but high-impact)

These render in their own "Highlights" section near the front of the PDF.

| Filename | What to capture |
|---|---|
| `15_3d_simulation.png` | Open any approved simulation artefact in a new tab. Take the screenshot when the 3D scene is rendered with all labels visible. |
| `16_content_library.png` | Content library with several artefacts visible across types. |
| `17_diagram_svg.png` | Any approved SVG diagram (concept map / flow diagram) opened in a new tab. |
| `18_chapter_topics.png` | A chapter detail page with topics list, summary, mind map, and the simulation/diagram tiles visible. |

## Expected output

After re-running the script:
- Each role page in `platform_overview.pdf` will have its screenshots embedded inline below the bullet list.
- The "Highlights" section will appear after the role pages with the four cross-cutting screenshots.
- Total page count will grow from ~10 to ~14-18 depending on how many screenshots are present.
