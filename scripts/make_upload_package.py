#!/usr/bin/env python3
"""
Package everything KoboToolbox needs into one upload-ready zip:

    Kobo_Upload_Package.zip
      forms/Capture_All_Facilities.xlsx
      forms/Facility_Report_Geofenced.xlsx
      data/enumerators.csv
      data/facilities.csv
      UPLOAD_TO_KOBO.txt

Usage:
    python scripts/make_upload_package.py
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FORMS_DIR, ROOT  # noqa: E402

PACKAGE = ROOT / "Kobo_Upload_Package.zip"

CONTENTS = [
    FORMS_DIR / "Capture_All_Facilities.xlsx",
    FORMS_DIR / "Facility_Report_Geofenced.xlsx",
    ROOT / "data" / "enumerators.csv",
    ROOT / "data" / "facilities.csv",
    ROOT / "UPLOAD_TO_KOBO.txt",
]


def main() -> None:
    missing = [p for p in CONTENTS if not p.exists()]
    if missing:
        raise SystemExit(
            "Missing file(s): " + ", ".join(str(p.relative_to(ROOT)) for p in missing)
            + "\nRun scripts/build_forms.py first."
        )

    with zipfile.ZipFile(PACKAGE, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in CONTENTS:
            zf.write(p, p.relative_to(ROOT))

    print(f"Created {PACKAGE.name}:")
    with zipfile.ZipFile(PACKAGE) as zf:
        for info in zf.infolist():
            print(f"  {info.file_size:>8,} bytes  {info.filename}")


if __name__ == "__main__":
    main()
