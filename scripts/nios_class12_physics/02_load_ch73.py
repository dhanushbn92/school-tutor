"""Load NIOS Class 12 Physics, Chapter 1 (Units, Dimensions and
Vectors): refresh full_text, insert topics + outcomes, load 130
questions, load + render 6 content blobs.

Run:
    PYTHONPATH=. .venv/Scripts/python.exe scripts/nios_class12_physics/02_load_ch73.py
"""

from pathlib import Path

from app.db.session import SessionLocal
from app.models.curriculum import BloomLevel

from scripts.nios_class12_physics.lib import (
    DATA_DIR,
    insert_outcomes,
    insert_topics,
    load_content_blobs,
    load_questions_from_file,
    update_chapter_full_text,
)


CHAPTER_ID = 73
PREFIX = "ch73"


TOPICS = [
    {
        "name": "Physical Quantities And Units",
        "description": (
            "Definition of a physical quantity, the role of units in a "
            "measurement, fundamental vs derived quantities, and the "
            "requirements of a good unit."
        ),
        "section_header": "1.1 PHYSICAL QUANTITIES AND UNITS",
        "next_section_header": "1.2 INTERNATIONAL SYSTEM OF UNITS (SI)",
    },
    {
        "name": "International System Of Units",
        "description": (
            "The seven SI base units, common derived units (newton, "
            "pascal, joule, watt, coulomb, hertz) and SI prefixes used "
            "to handle the wide range of magnitudes in physics."
        ),
        "section_header": "1.2 INTERNATIONAL SYSTEM OF UNITS (SI)",
        "next_section_header": "1.3 DIMENSIONS AND DIMENSIONAL ANALYSIS",
    },
    {
        "name": "Dimensions And Dimensional Analysis",
        "description": (
            "Dimensions of a quantity in terms of M, L, T, A, K, mol, "
            "cd; the principle of dimensional homogeneity; uses and "
            "limitations of dimensional analysis."
        ),
        "section_header": "1.3 DIMENSIONS AND DIMENSIONAL ANALYSIS",
        "next_section_header": "1.4 SIGNIFICANT FIGURES AND ERRORS",
    },
    {
        "name": "Significant Figures And Errors",
        "description": (
            "Significant figures in a measurement, kinds of errors "
            "(systematic, random, gross), absolute / relative / "
            "percentage error, and rules for combining errors."
        ),
        "section_header": "1.4 SIGNIFICANT FIGURES AND ERRORS",
        "next_section_header": "1.5 SCALARS AND VECTORS",
    },
    {
        "name": "Scalars And Vectors",
        "description": (
            "Definition of scalars and vectors, vector notation, "
            "magnitude, unit vectors, and the various types of "
            "vectors (zero, equal, negative, collinear, coplanar)."
        ),
        "section_header": "1.5 SCALARS AND VECTORS",
        "next_section_header": "1.6 VECTOR OPERATIONS",
    },
    {
        "name": "Vector Operations",
        "description": (
            "Addition by triangle and parallelogram laws, subtraction, "
            "resolution into components, magnitude of a sum, and the "
            "scalar (dot) and vector (cross) products with their "
            "physical interpretations."
        ),
        "section_header": "1.6 VECTOR OPERATIONS",
        "next_section_header": "SUMMARY",
    },
]


OUTCOMES = [
    {"code": "12-NIOS-PHY-UDV-01", "topic_name": "Physical Quantities And Units", "bloom": BloomLevel.REMEMBER,
     "description": "List the seven fundamental physical quantities and state the requirements of a good unit."},
    {"code": "12-NIOS-PHY-UDV-02", "topic_name": "International System Of Units", "bloom": BloomLevel.UNDERSTAND,
     "description": "State the seven SI base units, identify common derived units (N, Pa, J, W, C, Hz) in terms of base units, and apply standard SI prefixes."},
    {"code": "12-NIOS-PHY-UDV-03", "topic_name": "Dimensions And Dimensional Analysis", "bloom": BloomLevel.APPLY,
     "description": "Write the dimensional formula of a given physical quantity using M, L, T, A and apply the principle of homogeneity to check the consistency of an equation."},
    {"code": "12-NIOS-PHY-UDV-04", "topic_name": "Dimensions And Dimensional Analysis", "bloom": BloomLevel.EVALUATE,
     "description": "Justify the use and identify the limitations of dimensional analysis (cannot find dimensionless constants, cannot detect missing terms with the same dimensions, cannot determine functional form)."},
    {"code": "12-NIOS-PHY-UDV-05", "topic_name": "Significant Figures And Errors", "bloom": BloomLevel.APPLY,
     "description": "Determine the number of significant figures in a given measurement and apply the sig-fig rules for multiplication, division, addition and subtraction."},
    {"code": "12-NIOS-PHY-UDV-06", "topic_name": "Significant Figures And Errors", "bloom": BloomLevel.APPLY,
     "description": "Compute mean absolute, relative and percentage errors of a measurement, and apply the rules for combining errors in sums, products and powers."},
    {"code": "12-NIOS-PHY-UDV-07", "topic_name": "Scalars And Vectors", "bloom": BloomLevel.UNDERSTAND,
     "description": "Distinguish scalars from vectors, write a vector in component form using î, ĵ, k̂, and identify equal, zero, unit, collinear and coplanar vectors."},
    {"code": "12-NIOS-PHY-UDV-08", "topic_name": "Vector Operations", "bloom": BloomLevel.APPLY,
     "description": "Add and subtract vectors using the triangle and parallelogram laws, resolve a vector into components, and compute scalar (dot) and vector (cross) products."},
]


def main() -> None:
    full_text = (DATA_DIR / f"{PREFIX}_full_text.txt").read_text(encoding="utf-8")

    db = SessionLocal()
    try:
        update_chapter_full_text(db, CHAPTER_ID, full_text)
        topic_ids = insert_topics(
            db, chapter_id=CHAPTER_ID, full_text=full_text, topic_specs=TOPICS
        )
        insert_outcomes(
            db, chapter_id=CHAPTER_ID, outcome_specs=OUTCOMES, topic_id_by_name=topic_ids
        )
        db.commit()

        load_questions_from_file(db, chapter_id=CHAPTER_ID, filename=f"{PREFIX}_questions.json")
        db.commit()

        load_content_blobs(db, chapter_id=CHAPTER_ID, prefix=PREFIX)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
