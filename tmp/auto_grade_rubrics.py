"""Attach keyword rubrics to selected subjective questions for ch 1-3.

Run via: .venv/Scripts/python.exe tmp/auto_grade_rubrics.py
The rubrics are intentionally lenient — partial credit for any reasonable
answer that mentions the right concepts, with a `min_words` floor so a
1-word answer ('idk') falls through to teacher review.
"""
import sys
from pathlib import Path

# Allow running as a plain script.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db.session import SessionLocal  # noqa: E402
from app.models.question import Question  # noqa: E402


RUBRICS = {
    # Ch 3 — Q #295 "Suggest a balanced one-day meal plan" (3 marks)
    295: {
        "method": "keywords",
        "min_words": 8,
        "groups": [
            {
                "label": "Carbohydrate / grain",
                "any_of": ["roti", "rice", "chapati", "paratha", "bread", "idli", "poha", "wheat", "millet"],
                "marks": 1,
            },
            {
                "label": "Protein",
                "any_of": ["dal", "egg", "paneer", "milk", "curd", "yoghurt", "yogurt", "lentil", "chana", "peanut", "tofu", "fish", "chicken"],
                "marks": 1,
            },
            {
                "label": "Vitamins / vegetables / fruit",
                "any_of": ["vegetable", "veggie", "salad", "spinach", "carrot", "fruit", "banana", "apple", "orange", "tomato", "cucumber", "leafy"],
                "marks": 1,
            },
            {
                "label": "Hydration",
                "any_of": ["water", "buttermilk"],
                "marks": 0,
            },
        ],
    },
    # Ch 3 — Q #299 "Mention any two ways an animal..." (varies). Skipped — wrong chapter.
    # Ch 3 — Q #316 "Design a poster..." (10 marks): keywords for healthy eating themes.
    316: {
        "method": "keywords",
        "min_words": 15,
        "groups": [
            {"label": "Whole grains", "any_of": ["roti", "rice", "whole grain", "millet", "wheat", "oats", "brown"], "marks": 2},
            {"label": "Protein", "any_of": ["dal", "egg", "paneer", "milk", "lentil", "chana", "peanut", "fish"], "marks": 2},
            {"label": "Fruits and vegetables", "any_of": ["fruit", "vegetable", "salad", "spinach", "leafy", "veggie"], "marks": 2},
            {"label": "Hydration / avoid sugary", "any_of": ["water", "no sugar", "less sugar", "avoid sugary", "no soft drinks", "limit"], "marks": 2},
            {"label": "Variety / balance message", "any_of": ["balanced", "variety", "every nutrient", "rainbow", "all groups", "balance"], "marks": 2},
        ],
    },
    # Ch 1 — Q #322 "Describe scientific method steps..." (5 marks)
    322: {
        "method": "keywords",
        "min_words": 20,
        "groups": [
            {"label": "Observation", "any_of": ["observ", "notic", "watch", "see"], "marks": 1},
            {"label": "Question", "any_of": ["question", "ask", "why", "how"], "marks": 1},
            {"label": "Hypothesis", "any_of": ["hypothes", "guess", "predict", "explan"], "marks": 1},
            {"label": "Experiment / Test", "any_of": ["experiment", "test", "try"], "marks": 1},
            {"label": "Conclusion / Sharing", "any_of": ["conclu", "result", "record", "share", "find"], "marks": 1},
        ],
    },
    # Ch 1 — Q #323 "Design a fair experiment for cotton vs polyester..." (5 marks)
    323: {
        "method": "keywords",
        "min_words": 20,
        "groups": [
            {"label": "Mentions both fabrics", "any_of": ["cotton", "polyester"], "marks": 1},
            {"label": "Same conditions / fair test", "any_of": ["same", "equal", "identical", "fair"], "marks": 1},
            {"label": "Submerge / water", "any_of": ["water", "soak", "dip", "submerge"], "marks": 1},
            {"label": "Measure / weigh", "any_of": ["weigh", "measur", "balance", "weight", "gram"], "marks": 1},
            {"label": "Compare / repeat", "any_of": ["compar", "repeat", "average", "again"], "marks": 1},
        ],
    },
    # Ch 2 — Q #325 "Explain plant classification..." (5 marks)
    325: {
        "method": "keywords",
        "min_words": 20,
        "groups": [
            {"label": "Herbs", "any_of": ["herb", "tulsi", "mint", "soft stem", "small plant"], "marks": 1},
            {"label": "Shrubs", "any_of": ["shrub", "rose", "lemon", "branch", "medium"], "marks": 1},
            {"label": "Trees", "any_of": ["tree", "mango", "neem", "wood", "tall", "thick stem"], "marks": 1},
            {"label": "Stem feature", "any_of": ["stem", "hard", "soft", "woody"], "marks": 1},
            {"label": "Examples given", "any_of": ["example", "such as", "e.g.", "like", "for example"], "marks": 1},
        ],
    },
    # Ch 2 — Q #327 "Why protect biodiversity..." (10 marks)
    327: {
        "method": "keywords",
        "min_words": 30,
        "groups": [
            {"label": "Definition / variety of life", "any_of": ["biodivers", "variety", "many kinds", "different species"], "marks": 2},
            {"label": "Food / pollinat", "any_of": ["food", "pollinat", "bee", "crop"], "marks": 2},
            {"label": "Medicine", "any_of": ["medicine", "drug", "neem", "tulsi"], "marks": 2},
            {"label": "Ecosystem balance", "any_of": ["balance", "ecosystem", "rain", "soil", "forest"], "marks": 2},
            {"label": "Practical actions", "any_of": ["plant tree", "avoid plastic", "protect", "conserv", "save"], "marks": 2},
        ],
    },
    # Ch 2 — Q #217 "Imagine all bees disappear..." (10 marks)
    217: {
        "method": "keywords",
        "min_words": 25,
        "groups": [
            {"label": "Pollination loss", "any_of": ["pollinat", "flower", "fertilis"], "marks": 2},
            {"label": "Less fruits / seeds", "any_of": ["fruit", "seed", "crop"], "marks": 2},
            {"label": "Affected food / humans", "any_of": ["food", "human", "people", "diet"], "marks": 2},
            {"label": "Other species affected", "any_of": ["bird", "monkey", "animal", "depend"], "marks": 2},
            {"label": "Connectedness lesson", "any_of": ["connect", "depend", "balance", "ecosystem"], "marks": 2},
        ],
    },
    # Ch 3 — Q #328 "Explain food components..." (5 marks)
    328: {
        "method": "keywords",
        "min_words": 25,
        "groups": [
            {"label": "Carbohydrate role", "any_of": ["carb", "energy", "rice", "roti"], "marks": 1},
            {"label": "Protein role", "any_of": ["protein", "build", "grow", "repair", "dal", "egg", "milk"], "marks": 1},
            {"label": "Fat role", "any_of": ["fat", "ghee", "butter", "long-lasting", "warmth"], "marks": 1},
            {"label": "Vitamin / mineral role", "any_of": ["vitamin", "mineral", "protect", "calcium", "iron"], "marks": 1},
            {"label": "Source examples", "any_of": ["spinach", "fruit", "milk", "vegetable", "egg", "ghee", "rice", "dal"], "marks": 1},
        ],
    },
    # Ch 3 — Q #329 "Tired 12-year-old, suggest reasons + plan" (5 marks)
    329: {
        "method": "keywords",
        "min_words": 25,
        "groups": [
            {"label": "Anaemia / iron deficiency", "any_of": ["anaemia", "anemia", "iron"], "marks": 1},
            {"label": "Iron-rich food", "any_of": ["spinach", "leafy", "dal", "ragi", "jaggery"], "marks": 1},
            {"label": "Vitamin C / absorption", "any_of": ["vitamin c", "lemon", "orange", "amla"], "marks": 1},
            {"label": "Balanced meal plan", "any_of": ["breakfast", "lunch", "dinner", "balanced", "balance"], "marks": 1},
            {"label": "Hydration / water", "any_of": ["water", "fluid", "drink"], "marks": 1},
        ],
    },
}


def main() -> None:
    with SessionLocal() as db:
        for qid, rubric in RUBRICS.items():
            q = db.get(Question, qid)
            if q is None:
                print(f"  qid={qid} not found, skipping")
                continue
            q.auto_grade = rubric
            print(f"  qid={qid} ch={q.chapter_id} marks={q.marks} rubric attached")
        db.commit()
    print(f"done. {len(RUBRICS)} rubrics applied.")


if __name__ == "__main__":
    main()
