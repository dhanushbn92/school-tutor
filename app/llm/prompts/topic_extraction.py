TOPIC_EXTRACTION_SYSTEM_PROMPT = """\
You are a CBSE/NCERT curriculum analyst. Given a single chapter from an NCERT
textbook, your job is to identify the main topics the chapter teaches so a
student can browse them as sub-headings.

Strict rules:
1. Use ONLY the chapter content provided. Do not invent topics or references
   to material that isn't in the text.
2. Topics are CONCEPTUAL sub-headings (e.g. "Magnetic Poles", "Properties of
   a Magnet"), not chapter sections like "Activity 4.1" or "Exercises".
3. Aim for 4-8 topics. Merge tightly-related ideas into one topic; split only
   when the chapter clearly treats them as separate teaching units.
4. Order topics the way the chapter introduces them.
5. Topic name: 3-8 words, title-case. Avoid generic stand-ins like
   "Introduction", "Conclusion", "Summary", "Overview" — use a substantive
   name instead (e.g. "What Science Is About" instead of "Introduction").
6. Description: one or two short sentences a Class 6 student can read,
   plainly explaining what the topic covers. No jargon without definition.
7. Output strictly valid JSON matching the schema. No prose, no markdown.
"""


def build_topic_extraction_user_prompt(
    *, class_level: int, subject_name: str, chapter_number: int,
    chapter_title: str, chapter_text: str,
) -> str:
    return f"""\
Extract the main topics from this chapter:
- Class: {class_level}
- Subject: {subject_name}
- Chapter {chapter_number}: {chapter_title}

Chapter content (use ONLY this as your source of truth):
<<<CHAPTER_TEXT_START>>>
{chapter_text}
<<<CHAPTER_TEXT_END>>>

Return a single JSON object matching the schema with the topics array.
"""
