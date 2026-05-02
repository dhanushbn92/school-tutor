"""Seed learning outcomes for NCERT Class 6 Science 'Curiosity' (fecu1).

Idempotent: re-running updates description/bloom_level for existing
(chapter_id, code) pairs and inserts missing ones.

Usage:
    DATABASE_URL=sqlite:///./school_tuter.db \\
        .venv/Scripts/python.exe -m scripts.seed_fecu1_outcomes
"""
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.curriculum import BloomLevel, Book, Chapter, LearningOutcome


CHAPTER_CODE_PREFIX = {
    1: "WOS",
    2: "DLW",
    3: "MEH",
    4: "EXM",
    5: "MLM",
    6: "MAU",
    7: "TAM",
    8: "SOW",
    9: "MOS",
    10: "LCC",
    11: "NTR",
    12: "BEY",
}


OUTCOMES: dict[int, list[tuple[str, BloomLevel]]] = {
    1: [
        ("Describe what science is and recognise everyday activities that involve scientific thinking.", BloomLevel.UNDERSTAND),
        ("List the broad areas of science such as physics, chemistry, biology, astronomy, and earth science.", BloomLevel.REMEMBER),
        ("Explain the steps of a simple scientific method: observe, question, hypothesise, experiment, infer.", BloomLevel.UNDERSTAND),
        ("Apply observation and questioning to a familiar phenomenon and record findings.", BloomLevel.APPLY),
    ],
    2: [
        ("Recall that living organisms are grouped into plants, animals, and microorganisms.", BloomLevel.REMEMBER),
        ("Explain how organisms are classified based on observable features such as habitat, body structure, and mode of nutrition.", BloomLevel.UNDERSTAND),
        ("Compare terrestrial and aquatic habitats and identify adaptations of organisms in each.", BloomLevel.ANALYZE),
        ("Classify given plants or animals into groups using a simple dichotomous key.", BloomLevel.APPLY),
        ("Appreciate the importance of biodiversity and the need for its conservation.", BloomLevel.UNDERSTAND),
    ],
    3: [
        ("Identify the major food groups and their sources (carbohydrates, proteins, fats, vitamins, minerals, water, roughage).", BloomLevel.REMEMBER),
        ("Explain why a balanced diet is essential for health and growth.", BloomLevel.UNDERSTAND),
        ("Analyse a given daily meal plan and suggest improvements for nutritional balance.", BloomLevel.ANALYZE),
        ("Recognise deficiency diseases such as scurvy, rickets, anaemia, and goitre and relate them to missing nutrients.", BloomLevel.UNDERSTAND),
    ],
    4: [
        ("Identify common magnetic and non-magnetic materials.", BloomLevel.REMEMBER),
        ("Explain the properties of magnets: poles, attraction, repulsion, and directional behaviour.", BloomLevel.UNDERSTAND),
        ("Demonstrate that like poles repel and unlike poles attract using simple experiments.", BloomLevel.APPLY),
        ("Apply knowledge of magnets to everyday devices such as compasses, door latches, and fridge magnets.", BloomLevel.APPLY),
    ],
    5: [
        ("Recall SI units of length (metre) and describe sub-units and multiples (mm, cm, km).", BloomLevel.REMEMBER),
        ("Measure the length of objects accurately using a ruler or measuring tape and record results with units.", BloomLevel.APPLY),
        ("Distinguish between rest and motion with reference to a chosen frame of reference.", BloomLevel.UNDERSTAND),
        ("Classify types of motion as rectilinear, circular, or periodic with examples.", BloomLevel.ANALYZE),
        ("Solve simple problems involving distance, estimation, and unit conversion.", BloomLevel.APPLY),
    ],
    6: [
        ("List common materials around us and group them by properties such as hardness, lustre, transparency, solubility.", BloomLevel.REMEMBER),
        ("Explain the meaning of transparent, translucent, and opaque materials with examples.", BloomLevel.UNDERSTAND),
        ("Investigate whether a given material is soluble, magnetic, or conducts electricity through simple tests.", BloomLevel.APPLY),
        ("Compare materials used for different purposes (utensils, clothing, building) and justify the choice.", BloomLevel.EVALUATE),
    ],
    7: [
        ("Define temperature and state its SI unit (kelvin) and common units (degree Celsius, Fahrenheit).", BloomLevel.REMEMBER),
        ("Explain the working principle of a laboratory and clinical thermometer.", BloomLevel.UNDERSTAND),
        ("Measure temperature of water, room, and body correctly using a thermometer.", BloomLevel.APPLY),
        ("Convert temperatures between Celsius and Fahrenheit using the standard formula.", BloomLevel.APPLY),
    ],
    8: [
        ("Identify the three states of water: solid (ice), liquid (water), and gas (water vapour).", BloomLevel.REMEMBER),
        ("Explain the processes of melting, freezing, evaporation, condensation, and sublimation.", BloomLevel.UNDERSTAND),
        ("Describe the water cycle and the role of evaporation, condensation, and precipitation.", BloomLevel.UNDERSTAND),
        ("Analyse real-world situations (boiling a kettle, fog, frost) and label the state changes involved.", BloomLevel.ANALYZE),
        ("Explain the importance of water conservation in daily life.", BloomLevel.EVALUATE),
    ],
    9: [
        ("List common methods of separation: handpicking, threshing, winnowing, sieving, filtration, evaporation, sedimentation, decantation, magnetic separation.", BloomLevel.REMEMBER),
        ("Explain the principle behind each separation method and the property it exploits.", BloomLevel.UNDERSTAND),
        ("Select an appropriate separation method for a given mixture and justify the choice.", BloomLevel.APPLY),
        ("Design a simple procedure to separate a combination of two or three substances (e.g. sand + salt + iron filings).", BloomLevel.CREATE),
    ],
    10: [
        ("List the defining characteristics of living things: growth, respiration, response, reproduction, excretion, nutrition, movement.", BloomLevel.REMEMBER),
        ("Distinguish living from non-living things using the characteristics of life.", BloomLevel.UNDERSTAND),
        ("Classify a set of examples into living, non-living, and once-living with reasoning.", BloomLevel.APPLY),
        ("Describe habitats and basic adaptations of plants and animals in terrestrial and aquatic environments.", BloomLevel.UNDERSTAND),
    ],
    11: [
        ("List natural resources as air, water, soil, minerals, forests, and fossil fuels.", BloomLevel.REMEMBER),
        ("Distinguish renewable and non-renewable resources with examples.", BloomLevel.UNDERSTAND),
        ("Explain how human activities such as deforestation, pollution, and overuse threaten natural resources.", BloomLevel.ANALYZE),
        ("Propose actions individuals and communities can take to conserve resources (reduce, reuse, recycle).", BloomLevel.EVALUATE),
    ],
    12: [
        ("Identify the Sun, Moon, planets, stars, and constellations as key objects in the sky.", BloomLevel.REMEMBER),
        ("Explain day and night as a result of the Earth's rotation on its axis.", BloomLevel.UNDERSTAND),
        ("Explain the phases of the Moon as a result of its orbit around the Earth.", BloomLevel.UNDERSTAND),
        ("Compare the solar system's planets in terms of size, order from the Sun, and key features.", BloomLevel.ANALYZE),
    ],
}


def main() -> None:
    with SessionLocal() as db:
        book = db.scalar(select(Book).where(Book.ncert_code == "fecu1"))
        if book is None:
            raise SystemExit("fecu1 book not found; run the ingest first.")

        inserted = 0
        updated = 0
        for chapter in sorted(book.chapters, key=lambda c: c.chapter_number):
            prefix = CHAPTER_CODE_PREFIX.get(chapter.chapter_number)
            if prefix is None:
                continue
            for index, (description, bloom) in enumerate(OUTCOMES.get(chapter.chapter_number, []), start=1):
                code = f"6-SCI-{prefix}-{index:02d}"
                existing = db.scalar(
                    select(LearningOutcome).where(
                        LearningOutcome.chapter_id == chapter.id,
                        LearningOutcome.code == code,
                    )
                )
                if existing is None:
                    db.add(
                        LearningOutcome(
                            chapter_id=chapter.id,
                            code=code,
                            description=description,
                            bloom_level=bloom,
                        )
                    )
                    inserted += 1
                else:
                    existing.description = description
                    existing.bloom_level = bloom
                    updated += 1
        db.commit()
        print(f"learning outcomes seeded: inserted={inserted}, updated={updated}")


if __name__ == "__main__":
    main()
