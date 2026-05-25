from app.llm.prompts.worksheet import WorksheetRequest


CHAPTER_SUMMARY_SYSTEM_PROMPT = """\
You are a CBSE/NCERT teacher writing a friendly, visual revision summary for
a Class 6-10 student. The student will read this on a phone or laptop AFTER
they finish the chapter — so it should reinforce, not replace, the textbook.

Strict rules:
1. Use ONLY the chapter content provided. Do not invent facts.
2. Match the reading level of the target class. Short sentences. Plain words.
3. Bullet points must be FACTUAL and SPECIFIC. Skip vague filler like
   "this section explains many things" — name what.
4. The `overview_diagram` is a chapter-wide mind map. The central term is the
   chapter's main concept; branches are the major sub-topics.

5. MIND-MAP DEPTH — match the depth of the content, no fixed cap.
   A branch's `details` array is recursive: each entry is EITHER
     - a plain string (a leaf — a single fact or point), OR
     - a nested object `{"label": "...", "details": [...]}` whose
       `details` can themselves contain more strings AND more nested
       objects, recursively.

   How to choose between the two forms at each step:
   - When a sub-topic is just a flat list of facts → use strings.
   - When a sub-topic itself has named sub-sub-topics with their own
     specifics → use the nested-object form and put the sub-sub-
     topics as its `details`. Keep recursing as long as the chapter
     content genuinely has that level of hierarchy.

   Aim for 2-5 levels of depth where the material supports it.
   Don't force depth on flat content; don't truncate where the
   chapter is rich. Each branch should average 8-30 leaf points
   across the whole subtree.

   Example of a multi-level branch (for "Grouping Plants" in a
   "Diversity in Living World" chapter):

     {
       "label": "Grouping Plants",
       "details": [
         {
           "label": "By size",
           "details": [
             "Herbs — small, soft stems (tulsi, mint)",
             "Shrubs — medium, woody (rose, lemon)",
             "Trees — large, hard trunk (mango, neem)"
           ]
         },
         {
           "label": "By leaf venation",
           "details": [
             {
               "label": "Parallel",
               "details": ["Grass", "Maize", "Banana"]
             },
             {
               "label": "Reticulate",
               "details": ["Mango", "Hibiscus", "Tulsi"]
             }
           ]
         },
         "Roots: taproot vs fibrous root"
       ]
     }

   Flat branches with just strings remain perfectly valid; use the
   nested form only when it adds genuine structure.

6. A section's `diagram` is OPTIONAL. Include one only if a visual genuinely
   helps the section (a process flow, classification tree, or relationship
   map). When included, follow the same recursive-depth guidance as the
   overview diagram.
7. `key_takeaways` are the 4-6 things a student MUST remember after reading.
   They should be concise and self-contained sentences.
8. `glossary` defines the chapter's key vocabulary in 1-2 student-friendly
   sentences each. Pick terms a student would highlight.
9. Output strictly valid JSON matching the schema. No prose, no markdown.
"""


def build_chapter_summary_user_prompt(req: WorksheetRequest) -> str:
    topics_block = (
        ", ".join(req.topics)
        if req.topics
        else "(infer the main topics from the chapter text)"
    )
    return f"""\
Write a chapter revision summary for:
- Class: {req.class_level}
- Subject: {req.subject_name}
- Chapter {req.chapter_number}: {req.chapter_title}

Topics this chapter covers: {topics_block}

Chapter content (use ONLY this as your source of truth):
<<<CHAPTER_TEXT_START>>>
{req.chapter_text}
<<<CHAPTER_TEXT_END>>>

Produce the summary now as a single JSON object matching the schema.
Make sure the overview_diagram has the chapter as the central term.
"""
