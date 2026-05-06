"""Final 3 subjective questions for ch238."""

from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.curriculum import LearningOutcome, BloomLevel
from app.models.question import Question, QuestionDifficulty, QuestionStatus, QuestionType


EXTRAS = [
    {
        "outcome_code": "10-CBSE-HIN-RLP-03",
        "question": "परशुराम के क्रोध के कारण क्या थे?",
        "answer": "परशुराम के क्रोध के मुख्य कारण थे: (१) शिव के परम भक्त होने के कारण शिव-धनुष का टूटना उन्हें अपने इष्टदेव का अपमान लगा। (२) धनुष-भंग की भयानक ध्वनि से उन्हें पता चला कि कुछ बहुत बड़ा हुआ है। (३) उन्होंने सोचा कि कोई अहंकारी क्षत्रिय ने यह अपराध किया है। (४) क्षत्रियों के प्रति उनका पूर्व-संचित क्रोध — पिता की हत्या से जागृत — जिसे वे क्षत्रिय-संहार से ही व्यक्त करते रहे। (५) उनके चरित्र का क्षात्र-तेज जो शीघ्र ही उग्र हो उठता है। पर उनका क्रोध केवल कोप नहीं — उसमें न्याय-स्थापना का भाव भी है।",
    },
    {
        "outcome_code": "10-CBSE-HIN-RLP-05",
        "question": "लक्ष्मण के साहस और तर्क का संगम कैसे प्रकट होता है?",
        "answer": "लक्ष्मण के व्यवहार में साहस और तर्क का अद्भुत संगम है। साहस — परशुराम जैसे प्रसिद्ध और प्रचंड ऋषि-योद्धा के सामने भी वे डरते नहीं — मुस्कुराते हुए तीखी बातें कहते हैं। तर्क — उनकी बातें सिर्फ आक्रोश नहीं — उनमें ठोस तर्क है। वे ब्राह्मण-धर्म और क्षत्रिय-धर्म की विसंगति की ओर इशारा करते हैं — जो शास्त्रीय सत्य है। साहस + तर्क का यह संगम लक्ष्मण को आदर्श युवा-वक्ता बनाता है — जो भय से नहीं, परंतु बुद्धिमत्ता से बात करता है। यह आज के विद्यार्थी और सामाजिक कार्यकर्ता के लिए मॉडल है।",
    },
    {
        "outcome_code": "10-CBSE-HIN-RLP-07",
        "question": "विश्वामित्र की प्रज्ञा का इस संवाद में क्या भूमिका है?",
        "answer": "विश्वामित्र की प्रज्ञा (बुद्धिमत्ता) इस संवाद की कुंजी है। (१) पात्र-पहचान — वे दोनों पक्षों की वास्तविकता जानते हैं। (२) समय का विवेक — वे तुरन्त हस्तक्षेप नहीं करते; पहले स्थिति को देखते हैं और जब टकराव बढ़ रहा होता है तब बोलते हैं। (३) सर्वोच्च तर्क — उन्होंने वही तर्क दिया जो परशुराम को रोक सकता था — कि राम विष्णु के अवतार हैं। (४) सेतु-निर्माण — वे क्रोध को शान्ति में बदलते हैं — यह बुद्धिमान मध्यस्थ की भूमिका है। (५) सम्मानित आदर — परशुराम को आदर देते हुए, पर उन्हें सत्य बताते हुए। उनकी प्रज्ञा हमें सिखाती है कि बुद्धिमान व्यक्ति की भूमिका विवादों में सेतु बनने की है — एक पक्ष लेने की नहीं।",
    },
]


def main():
    db = SessionLocal()
    try:
        om = {r.code: r.id for r in db.scalars(
            select(LearningOutcome).where(LearningOutcome.chapter_id == 238)).all()}
        ex = {r.text for r in db.scalars(
            select(Question).where(Question.chapter_id == 238)).all()}
        added = 0
        for q in EXTRAS:
            if q["question"] in ex: continue
            oc = q["outcome_code"]
            db.add(Question(
                chapter_id=238, topic_id=None,
                outcome_id=om.get(oc), outcome_code=oc,
                type=QuestionType("SHORT_ANSWER"),
                difficulty=QuestionDifficulty("MEDIUM"),
                status=QuestionStatus.APPROVED,
                cognitive_level=BloomLevel("analyze"),
                text=q["question"], options=None,
                correct_answer=q["answer"],
                explanation="Final topup.",
                marks=3, created_by_id=14))
            added += 1
        db.commit()
        print(f"  ch238: inserted {added} new subjective questions")
    finally:
        db.close()


if __name__ == "__main__":
    main()
