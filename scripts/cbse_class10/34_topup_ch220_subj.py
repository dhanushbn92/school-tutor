"""Final top-up of subjective questions for ch220 to reach 30+ subjective."""

from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.curriculum import BloomLevel, LearningOutcome
from app.models.question import Question, QuestionDifficulty, QuestionStatus, QuestionType


def _options(q):
    return {"choices": list(q["options"])} if q.get("options") else None


def insert_for_chapter(db, chapter_id, supp):
    outcome_map = {r.code: r.id for r in db.scalars(
        select(LearningOutcome).where(LearningOutcome.chapter_id == chapter_id)).all()}
    existing = {r.text for r in db.scalars(
        select(Question).where(Question.chapter_id == chapter_id)).all()}
    added = 0
    for q in supp:
        if q["question"] in existing: continue
        oc = q.get("outcome_code")
        db.add(Question(
            chapter_id=chapter_id, topic_id=None,
            outcome_id=outcome_map.get(oc) if oc else None, outcome_code=oc,
            type=QuestionType(q["type"]), difficulty=QuestionDifficulty(q["difficulty"]),
            status=QuestionStatus.APPROVED,
            cognitive_level=BloomLevel(q["cognitive_level"].lower()),
            text=q["question"], options=_options(q), correct_answer=q["answer"],
            explanation=q.get("explanation"), marks=int(q.get("marks", 1)),
            created_by_id=14))
        added += 1
    db.commit()
    return added


EXTRA = [
    {"type":"SHORT_ANSWER","outcome_code":"10-CBSE-ENG-NM-09","difficulty":"MEDIUM","cognitive_level":"ANALYZE","marks":3,"question":"How does Mandela use the metaphor of the 'long walk' to describe his journey?","answer":"At the end of the excerpt, Mandela uses the title image of a LONG WALK with hills behind him and many more hills ahead. The metaphor describes his journey on several levels: (i) THE PERSONAL JOURNEY from a Transkei boyhood through 27 years of imprisonment to the presidency of South Africa. (ii) THE NATIONAL JOURNEY of South Africa from apartheid to democracy. (iii) THE UNIVERSAL JOURNEY of every people seeking freedom — slow, hill by hill, never finished. He says THERE CAN BE NO REST: to be FREE is not merely to cast off one's chains but to live in a way that respects and ENHANCES the freedom of others. The metaphor captures both the achievement (the long walk already done) and the work still to come.","explanation":"Long walk metaphor."},
    {"type":"SHORT_ANSWER","outcome_code":"10-CBSE-ENG-NM-02","difficulty":"MEDIUM","cognitive_level":"UNDERSTAND","marks":3,"question":"What was the role of the African National Congress (ANC) in Mandela's life and in the struggle against apartheid?","answer":"The AFRICAN NATIONAL CONGRESS (ANC), formed in 1912, was South Africa's oldest anti-apartheid party. Mandela JOINED THE ANC YOUTH LEAGUE as a young lawyer and rose through its ranks, eventually becoming its president. The ANC: (i) organised peaceful resistance — strikes, protests, defiance campaigns; (ii) when peaceful methods failed under brutal state response, Mandela helped form 'Umkhonto we Sizwe' ('Spear of the Nation'), the armed wing; (iii) after Mandela's arrest in 1962 and life sentence in 1964, the ANC continued from EXILE, mobilising international pressure (sanctions, sports boycotts); (iv) WON the first multi-racial democratic election in April 1994, with Mandela as its presidential candidate; (v) has remained South Africa's ruling party since 1994. For Mandela, the ANC was both POLITICAL HOME and MORAL FRAMEWORK — the institution through which he served both 'family and people'.","explanation":"ANC role."},
    {"type":"SHORT_ANSWER","outcome_code":"10-CBSE-ENG-TZ-04","difficulty":"MEDIUM","cognitive_level":"EVALUATE","marks":3,"question":"Why is 'A Tiger in the Zoo' more effective as an indirect critique than a direct one would be?","answer":"Norris does not lecture readers about the cruelty of zoos. Instead he SHOWS the tiger — pacing on pads of velvet, ignoring visitors, staring at brilliant stars — and lets the reader DRAW THE CONCLUSION. This is more effective for several reasons: (i) RESPECT for the reader — the poet trusts the audience to see what is happening. (ii) HARDER TO ARGUE WITH — a direct lecture invites disagreement; the IMAGE of a tiger gazing at stars is harder to dismiss. (iii) STAYS in memory — years later, one remembers the velvet pads and brilliant stars more than any thesis. (iv) UNIVERSAL APPLICATION — without naming humans, the poem connects to every prisoner, including Mandela on Robben Island. The indirectness is the technique. The poem 'feels' the cage rather than ARGUING about it — and feelings move more deeply than arguments.","explanation":"Power of indirectness."},
    {"type":"SHORT_ANSWER","outcome_code":"10-CBSE-ENG-NM-05","difficulty":"MEDIUM","cognitive_level":"EVALUATE","marks":3,"question":"In your own words, explain Mandela's deepest insight about freedom.","answer":"Mandela's deepest insight is that FREEDOM IS INDIVISIBLE. No one is truly free if any are unfree — and the OPPRESSOR is as unfree as the OPPRESSED, since both are imprisoned by hatred and prejudice. The white South African could not really live a free life either — he was trapped within a system that required him to TREAT FELLOW HUMANS AS LESS THAN HUMAN, to fear the people he oppressed, to teach his children unjust attitudes. To be FREE, Mandela writes, is not merely to cast off one's chains; it is to live in a way that RESPECTS and ENHANCES the freedom of others. So the only path to a really free society is one where everyone is free — and where each person, by their own actions, contributes to the freedom of others rather than restricting it.","explanation":"Indivisible freedom."},
    {"type":"LONG_ANSWER","outcome_code":"10-CBSE-ENG-NM-08","difficulty":"HARD","cognitive_level":"REMEMBER","marks":5,"question":"Trace Nelson Mandela's life journey in detail, from his boyhood to his presidency.","answer":"Born 18 July 1918 in the village of Mvezo in the Transkei region of South Africa, Mandela was the son of a Thembu chief. After his father's death he was raised in the household of the regent of the Thembu people. He attended local schools, then the University of Fort Hare, but was expelled for joining a student protest. He moved to JOHANNESBURG, completed his BA by correspondence, and qualified as a LAWYER, opening (with Oliver Tambo) the first black law firm in South Africa. He JOINED THE ANC YOUTH LEAGUE in 1944 and rose to become a key strategist in the campaign against apartheid. After the ANC was BANNED in 1960, Mandela helped form its armed wing 'Umkhonto we Sizwe' in 1961. He was arrested in 1962, charged with sabotage in the Rivonia Trial, and on 12 JUNE 1964 was sentenced to LIFE IMPRISONMENT. He spent the next 27 years in prison — most of it on ROBBEN ISLAND, doing hard labour in a quarry; later at Pollsmoor Prison and Victor Verster. Throughout he refused offers of conditional release and continued to be the international face of the anti-apartheid struggle. International pressure (sanctions, sports boycotts) and continued internal resistance forced the white government to negotiate. F.W. de KLERK announced the unbanning of the ANC in February 1990, and Mandela was RELEASED on 11 February 1990. He led the ANC into negotiations that resulted in apartheid laws being REPEALED in 1991, a new democratic constitution, and the FIRST MULTI-RACIAL DEMOCRATIC ELECTION on 27 April 1994. The ANC won; Mandela was inaugurated as the FIRST BLACK PRESIDENT of South Africa on 10 May 1994. He served ONE TERM (1994-99), refusing a second despite popular pressure, and oversaw the Truth and Reconciliation Commission led by Bishop Tutu. After leaving office he focused on HIV/AIDS advocacy and the Mandela Foundation. He died on 5 December 2013 at age 95. He was awarded the NOBEL PEACE PRIZE jointly with de Klerk in 1993 — and remains the world's leading symbol of moral leadership in the modern era.","explanation":"Detailed life timeline."},
]


def main():
    db = SessionLocal()
    try:
        n = insert_for_chapter(db, 220, EXTRA)
        print(f"  ch220: inserted {n} new questions (skipped {len(EXTRA) - n} as duplicates)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
