"""
Shared helpers for the KoboToolbox facility-capture package.

Used by:
  * scripts/build_forms.py      -> builds the two XLSForms
  * scripts/export_facilities.py -> turns a Kobo data export into facilities.csv
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
FORMS_DIR = ROOT / "forms"

ENUMERATORS_CSV = DATA_DIR / "enumerators.csv"
LOCATIONS_CSV = DATA_DIR / "locations.csv"
FACILITIES_CSV = DATA_DIR / "facilities.csv"

# Media files that must be uploaded in KoboToolbox -> Settings -> Media
MEDIA_FILES = ["enumerators.csv", "facilities.csv"]

# --------------------------------------------------------------------------- #
# XLSForm column machinery
# --------------------------------------------------------------------------- #
SURVEY_COLS = [
    "type",
    "name",
    "label",
    "relevant",
    "required",
    "constraint",
    "constraint_message",
    "calculation",
    "appearance",
    "parameters",
    "choice_filter",
    "hint",
]

CHOICES_COLS = ["list_name", "name", "label", "lga", "ward"]


def srow(**kw):
    """Build one survey row, aligned to SURVEY_COLS."""
    unknown = set(kw) - set(SURVEY_COLS)
    if unknown:
        raise ValueError(f"Unknown survey columns: {unknown}")
    return [kw.get(c, "") for c in SURVEY_COLS]


def crow(list_name, name, label, lga="", ward=""):
    """Build one choices row, aligned to CHOICES_COLS."""
    return [list_name, name, label, lga, ward]


def group(name, label, relevant=""):
    return srow(type="begin_group", name=name, label=label, relevant=relevant)


def end_group():
    return srow(type="end_group")


# --------------------------------------------------------------------------- #
# Controlled vocabularies (edit here, then re-run scripts/build_forms.py)
# --------------------------------------------------------------------------- #
# Shown in the CAPTURE form ("type of facility")
FACILITY_TYPES = [
    ("phc", "Primary Health Centre (PHC)"),
    ("dispensary", "Dispensary / Health Post"),
    ("maternity", "Maternity Home"),
    ("hospital", "Hospital"),
    ("pharmacy", "Pharmacy / Patent Medicine Vendor"),
    ("laboratory", "Laboratory / Diagnostic Centre"),
    ("other_health", "Other health facility"),
    ("school", "School"),
    ("water_point", "Water point / Borehole"),
    ("market", "Market"),
    ("office", "Government / Office building"),
    ("other", "Other (specify in observations)"),
]

# Shown in the REPORT form (operational status)
OPERATIONAL_STATUS = [
    ("open_full", "Open and fully functional"),
    ("open_partial", "Open but only partially functional"),
    ("temp_closed", "Temporarily closed"),
    ("not_open", "Not open / not operating"),
]

# Shown in the REPORT form (building condition)
CONDITION_RATINGS = [
    ("good", "Good"),
    ("fair", "Fair"),
    ("poor", "Poor"),
    ("critical", "Critical - requires immediate attention"),
]

FACILITY_TYPE_LABELS = dict(FACILITY_TYPES)


# --------------------------------------------------------------------------- #
# Slug generator: safe, stable choice ids from human names
# --------------------------------------------------------------------------- #
def slugify(text: str) -> str:
    """'Ward A1 (North)' -> 'Ward_A1_North'"""
    slug = re.sub(r"[^0-9A-Za-z]+", "_", (text or "").strip()).strip("_")
    return slug or "unnamed"


def _unique(slug: str, taken: set[str]) -> str:
    candidate = slug
    i = 2
    while candidate in taken:
        candidate = f"{slug}_{i}"
        i += 1
    taken.add(candidate)
    return candidate


# --------------------------------------------------------------------------- #
# Location hierarchy (LGA -> Ward -> Community)
# --------------------------------------------------------------------------- #
class Locations:
    def __init__(self):
        self.lgas = []          # [(id, label)]
        self.wards = []         # [(id, label, lga_id)]
        self.communities = []   # [(id, label, lga_id, ward_id)]
        self.label_by_id = {}   # id -> label (all three levels)


def load_locations(path: Path = LOCATIONS_CSV) -> Locations:
    """
    Read data/locations.csv (columns: lga, ward, community) and generate
    stable choice ids.  The ids are what gets stored in submitted data,
    so do not re-order or rename rows after you have gone to the field.
    """
    locs = Locations()
    lga_seen: set[str] = set()
    ward_seen: set[str] = set()
    comm_seen: set[str] = set()

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"lga", "ward", "community"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"{path.name}: missing column(s): {', '.join(sorted(missing))}")

        for i, r in enumerate(reader, start=2):
            lga_label = (r["lga"] or "").strip()
            ward_label = (r["ward"] or "").strip()
            comm_label = (r["community"] or "").strip()
            if not lga_label and not ward_label and not comm_label:
                continue  # skip fully blank lines

            lga_id = _unique(slugify(lga_label), lga_seen)
            if lga_label and lga_id not in [x[0] for x in locs.lgas]:
                locs.lgas.append((lga_id, lga_label))
                locs.label_by_id[lga_id] = lga_label

            ward_id = _unique(f"{lga_id}__{slugify(ward_label)}", ward_seen)
            if ward_label:
                locs.wards.append((ward_id, ward_label, lga_id))
                locs.label_by_id[ward_id] = ward_label

            comm_id = _unique(f"{ward_id}__{slugify(comm_label)}", comm_seen)
            if comm_label:
                locs.communities.append((comm_id, comm_label, lga_id, ward_id))
                locs.label_by_id[comm_id] = comm_label

    if not locs.lgas or not locs.wards or not locs.communities:
        raise SystemExit(f"{path.name}: need at least one lga/ward/community row")
    return locs


def check_media_csvs():
    """Fail early if the external CSVs the forms depend on are missing/malformed."""
    problems = []

    if not ENUMERATORS_CSV.exists():
        problems.append(f"missing {ENUMERATORS_CSV}")
    else:
        with open(ENUMERATORS_CSV, newline="", encoding="utf-8-sig") as f:
            header = set(csv.DictReader(f).fieldnames or [])
            need = {"name", "label", "password"}
            if not need <= header:
                problems.append(f"{ENUMERATORS_CSV.name}: needs columns {sorted(need)}")

    if not FACILITIES_CSV.exists():
        problems.append(f"missing {FACILITIES_CSV}")
    else:
        with open(FACILITIES_CSV, newline="", encoding="utf-8-sig") as f:
            header = set(csv.DictReader(f).fieldnames or [])
            need = {
                "name", "label", "facility_type", "lga", "ward",
                "community", "latitude", "longitude", "geometry",
            }
            if not need <= header:
                problems.append(
                    f"{FACILITIES_CSV.name}: needs columns {sorted(need)}"
                )

    if problems:
        raise SystemExit("Data problem(s):\n  - " + "\n  - ".join(problems))
