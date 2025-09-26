# src/app/filters/categories.py
ALL_CATEGORIES = [
    "restaurant","cafe","bar",
    "activity","attraction","exhibit",
    "walk","view","nature",
    "shopping","performance",
]

INDOOR_STRICT = {"restaurant","cafe","bar","shopping","performance"}
OUTDOOR_STRICT = {"walk","nature"}
MIXED = {"view","attraction","activity","exhibit"}

assert set(ALL_CATEGORIES) == INDOOR_STRICT | OUTDOOR_STRICT | MIXED
