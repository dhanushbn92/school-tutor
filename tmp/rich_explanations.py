"""Add rich_explanation to a few long-answer questions for ch 1-3.

Run via: .venv/Scripts/python.exe -m tmp.rich_explanations
(or directly: python tmp/rich_explanations.py from the project root).
"""
from app.db.session import SessionLocal
from app.models.question import Question


RICH_BY_QID = {
    # Ch 1 — Scientific method explanation
    322: {
        "blocks": [
            {
                "type": "text",
                "content": (
                    "The scientific method is a step-by-step way of moving from "
                    "a curiosity to a confident answer. Each step builds on the "
                    "last, and you can loop back if your data doesn't support "
                    "your idea."
                ),
            },
            {
                "type": "flow_diagram",
                "data": {
                    "title": "Scientific Method",
                    "description": "Each step feeds into the next. If the data does not support your hypothesis, refine it and test again.",
                    "nodes": [
                        {"id": "obs",   "label": "Observe",        "kind": "start"},
                        {"id": "ques",  "label": "Ask a question", "kind": "step"},
                        {"id": "hyp",   "label": "Hypothesise",    "kind": "step"},
                        {"id": "exp",   "label": "Experiment",     "kind": "step"},
                        {"id": "rec",   "label": "Record data",    "kind": "step"},
                        {"id": "ana",   "label": "Analyse",        "kind": "step"},
                        {"id": "dec",   "label": "Supported?",     "kind": "decision"},
                        {"id": "share", "label": "Share findings", "kind": "end"},
                        {"id": "ref",   "label": "Refine",         "kind": "step"}
                    ],
                    "edges": [
                        {"src": "obs",  "dst": "ques"},
                        {"src": "ques", "dst": "hyp"},
                        {"src": "hyp",  "dst": "exp"},
                        {"src": "exp",  "dst": "rec"},
                        {"src": "rec",  "dst": "ana"},
                        {"src": "ana",  "dst": "dec"},
                        {"src": "dec",  "dst": "share", "label": "Yes"},
                        {"src": "dec",  "dst": "ref",   "label": "No"},
                        {"src": "ref",  "dst": "exp",   "label": "retry"}
                    ]
                }
            },
            {
                "type": "list",
                "title": "Worked example: 'Why do clothes dry faster on a windy day?'",
                "items": [
                    "Observe — clothes outside dry faster than clothes indoors.",
                    "Ask — does wind speed up evaporation?",
                    "Hypothesise — yes, more wind = faster drying.",
                    "Experiment — hang two same-sized cloths, one in front of a fan and one in still air.",
                    "Record — the time each took to dry.",
                    "Analyse — the cloth in the fan dried much faster.",
                    "Conclude — the data supports the hypothesis.",
                    "Share — explain the result so others can repeat the test."
                ]
            }
        ]
    },
    # Ch 2 — Plant classification explanation
    325: {
        "blocks": [
            {
                "type": "text",
                "content": (
                    "Plants are sorted by two main features: the height of the "
                    "plant and how hard or soft the stem is. The same plant can "
                    "also be examined for leaf venation, root system, and seed "
                    "structure."
                )
            },
            {
                "type": "mind_map",
                "data": {
                    "title": "How plants are grouped",
                    "central_term": "Plants",
                    "branches": [
                        {"label": "Herbs",  "details": ["Short", "Soft green stem", "Tulsi, mint"]},
                        {"label": "Shrubs", "details": ["Medium height", "Hard stem near base", "Rose, lemon"]},
                        {"label": "Trees",  "details": ["Tall", "Thick woody stem", "Mango, neem"]}
                    ]
                }
            },
            {
                "type": "flow_diagram",
                "data": {
                    "title": "Decision tree to classify any plant",
                    "nodes": [
                        {"id": "look",  "label": "Look at the plant",        "kind": "start"},
                        {"id": "tall",  "label": "Thick woody stem?",        "kind": "decision"},
                        {"id": "tree",  "label": "Tree",                     "kind": "end"},
                        {"id": "br",    "label": "Hard branching at base?",  "kind": "decision"},
                        {"id": "shrub", "label": "Shrub",                    "kind": "end"},
                        {"id": "soft",  "label": "Soft green stem?",         "kind": "decision"},
                        {"id": "herb",  "label": "Herb",                     "kind": "end"}
                    ],
                    "edges": [
                        {"src": "look",  "dst": "tall"},
                        {"src": "tall",  "dst": "tree",  "label": "Yes"},
                        {"src": "tall",  "dst": "br",    "label": "No"},
                        {"src": "br",    "dst": "shrub", "label": "Yes"},
                        {"src": "br",    "dst": "soft",  "label": "No"},
                        {"src": "soft",  "dst": "herb",  "label": "Yes"}
                    ]
                }
            }
        ]
    },
    # Ch 3 — Food components explanation
    328: {
        "blocks": [
            {
                "type": "text",
                "content": (
                    "Each food component does a different job. Some give energy, "
                    "some help us grow, and some protect us from disease. A "
                    "balanced diet has all of them in the right amounts."
                )
            },
            {
                "type": "mind_map",
                "data": {
                    "title": "Food components and their roles",
                    "central_term": "Balanced food",
                    "branches": [
                        {"label": "Energy",     "details": ["Carbohydrates - rice, roti, potato", "Fats - ghee, butter, nuts"]},
                        {"label": "Growth",     "details": ["Proteins - dal, eggs, paneer, milk"]},
                        {"label": "Protection", "details": ["Vitamins - fruits, vegetables", "Minerals - milk (calcium), spinach (iron)"]},
                        {"label": "Smooth digestion", "details": ["Roughage / fibre", "Whole grains, vegetables"]},
                        {"label": "Hydration",  "details": ["Water - in every body process"]}
                    ]
                }
            },
            {
                "type": "flow_diagram",
                "data": {
                    "title": "What happens to food after you eat it",
                    "nodes": [
                        {"id": "eat",     "label": "You eat",          "kind": "start"},
                        {"id": "digest",  "label": "Digestion",        "kind": "step"},
                        {"id": "absorb",  "label": "Absorption (gut)", "kind": "step"},
                        {"id": "energy",  "label": "Energy",           "kind": "end"},
                        {"id": "build",   "label": "Growth & repair",  "kind": "end"},
                        {"id": "protect", "label": "Protection",       "kind": "end"}
                    ],
                    "edges": [
                        {"src": "eat",    "dst": "digest"},
                        {"src": "digest", "dst": "absorb"},
                        {"src": "absorb", "dst": "energy",  "label": "carbs / fats"},
                        {"src": "absorb", "dst": "build",   "label": "proteins"},
                        {"src": "absorb", "dst": "protect", "label": "vitamins / minerals"}
                    ]
                }
            }
        ]
    }
}


def main() -> None:
    with SessionLocal() as db:
        for qid, blocks in RICH_BY_QID.items():
            q = db.get(Question, qid)
            if q is None:
                print(f"  qid={qid} not found, skipping")
                continue
            q.explanation_rich = blocks
            print(f"  qid={qid} ch={q.chapter_id} marks={q.marks} updated")
        db.commit()
    print("done.")


if __name__ == "__main__":
    main()
