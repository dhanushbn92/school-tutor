"""Tiny final top-up to push Sanskrit ch256 + ch257 just past 100 obj + 30 subj."""

from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.curriculum import BloomLevel, LearningOutcome
from app.models.question import Question, QuestionDifficulty, QuestionStatus, QuestionType

CREATED_BY_ID = 14


def _q(qtype, text, answer, *, options=None, marks=1, difficulty="EASY", bloom="REMEMBER",
       outcome_code=None, explanation=""):
    return dict(qtype=qtype, text=text, answer=answer, options=options, marks=marks,
                difficulty=difficulty, bloom=bloom, outcome_code=outcome_code, explanation=explanation)


CH256 = [
    _q("MCQ", "अनुष्टुप् छन्द में प्रत्येक चरण में कितने अक्षर होते हैं?", "आठ",
       options=["छह", "सात", "आठ", "दस"], outcome_code="10-CBSE-SAN-SP-01",
       explanation="४ चरण × ८ अक्षर = ३२।"),
    _q("MCQ", "'अरण्य' किसका पर्याय है?", "वन",
       options=["जल", "वन", "पर्वत", "पुष्प"], outcome_code="10-CBSE-SAN-SP-03",
       explanation="वन।"),
    _q("MCQ", "'सरोवर' का अर्थ है—", "तालाब",
       options=["नदी", "तालाब", "कुआँ", "झरना"], outcome_code="10-CBSE-SAN-SP-03",
       explanation="तालाब।"),
    _q("SHORT_ANSWER", "'जल ही जीवन है' इस उक्ति को पाठ के संदर्भ में स्पष्ट कीजिए।",
       "जल जीवन का आधार है — पीने, खाना पकाने, कृषि, स्वच्छता सभी के लिए। पाठ कहता है कि स्वच्छ जल के बिना जीवन सम्भव नहीं। दूषित जल रोग देता है — हैज़ा, टायफॉइड, पीलिया। जल-संरक्षण ही जीवन-संरक्षण है। उपाय — वर्षा-जल-संचयन, जल-शोधन, अपव्यय रोकना। पाठ का संदेश — 'जलं वै प्राणाः' — जल ही प्राण है।",
       marks=3, difficulty="MEDIUM", bloom="EVALUATE", outcome_code="10-CBSE-SAN-SP-07",
       explanation="जल-दर्शन।"),
]

CH257 = [
    _q("MCQ", "पंचतन्त्र की मूल भाषा क्या है?", "संस्कृत",
       options=["प्राकृत", "पाली", "संस्कृत", "हिन्दी"],
       outcome_code="10-CBSE-SAN-BBS-01", explanation="संस्कृत।"),
    _q("MCQ", "शशक की मुख्य 'अस्त्र' क्या थी?", "बुद्धि और चातुर्य",
       options=["शस्त्र", "बुद्धि और चातुर्य", "शक्ति", "शाप"],
       outcome_code="10-CBSE-SAN-BBS-08", explanation="मानसिक-अस्त्र।"),
    _q("FILL_BLANK", "विष्णुशर्मा ने ____ को नीति-शास्त्र सिखाने हेतु पंचतन्त्र की रचना की।", "राजकुमारों",
       outcome_code="10-CBSE-SAN-BBS-01", explanation="अमर शक्ति के पुत्र।"),
    _q("SHORT_ANSWER", "'बुद्धिर्बलवती सदा' पाठ की दो आधुनिक प्रासंगिक उदाहरण दीजिए।",
       "(१) तकनीकी क्षेत्र — आज छोटी startup कम्पनियाँ अपनी 'बुद्धि' से बड़ी multinational कंपनियों को टक्कर देती हैं — जैसे Zoho, Zerodha। (२) खेल — David vs Goliath की कथा हर विश्व-कप में दिखती है — कमज़ोर टीम बुद्धि-रणनीति से बड़ी टीम को हराती है। (३) पर्यावरण — आज मनुष्य की 'अनियंत्रित शक्ति' सिंह जैसी; हमें शशक जैसी 'सूझबूझ' चाहिए। यह सिद्ध करता है कि कथा का संदेश आज भी शत प्रतिशत प्रासंगिक है।",
       marks=3, difficulty="MEDIUM", bloom="APPLY", outcome_code="10-CBSE-SAN-BBS-10",
       explanation="आधुनिक उदाहरण।"),
]


def main() -> None:
    db = SessionLocal()
    try:
        for cid, qlist in [(256, CH256), (257, CH257)]:
            outcome_map = {r.code: r.id for r in db.scalars(
                select(LearningOutcome).where(LearningOutcome.chapter_id == cid)).all()}
            existing_texts = {r.text for r in db.scalars(
                select(Question).where(Question.chapter_id == cid)).all()}
            added = 0
            for q in qlist:
                if q["text"] in existing_texts: continue
                oc = q.get("outcome_code")
                db.add(Question(
                    chapter_id=cid,
                    outcome_id=outcome_map.get(oc) if oc else None,
                    outcome_code=oc,
                    type=QuestionType(q["qtype"]),
                    difficulty=QuestionDifficulty(q["difficulty"]),
                    status=QuestionStatus.APPROVED,
                    cognitive_level=BloomLevel(q["bloom"].lower()),
                    text=q["text"],
                    options={"choices": list(q["options"])} if q.get("options") else None,
                    correct_answer=q["answer"],
                    explanation=q.get("explanation") or "",
                    marks=int(q.get("marks", 1)),
                    created_by_id=CREATED_BY_ID,
                ))
                added += 1
            db.commit()
            print(f"[ok] ch{cid}: added {added}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
