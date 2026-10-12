#!/usr/bin/env python3
"""
Turn a KoboToolbox data export of the CAPTURE form into facilities.csv -
the facility register consumed by the geofenced REPORT form.

Workflow
--------
1. Deploy forms/Capture_All_Facilities.xlsx and collect data in the field.
2. In KoboToolbox: Data -> Downloads -> pick your submissions -> CSV (with labels
   or without - both work) and save the file, e.g. export.csv
3. Run:

       python scripts/export_facilities.py export.csv

   By default this MERGES new facilities into data/facilities.csv (existing
   entries are kept, duplicates are skipped, missing rows are appended).

4. Upload the updated data/facilities.csv in KoboToolbox
   -> Settings -> Media of the REPORT project and redeploy the form.

Rows that do not have valid GPS coordinates are skipped, because the report
form needs coordinates to enforce the on-site (geofence) check.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    FACILITIES_CSV,
    FACILITY_TYPE_LABELS,
    load_locations,
)

OUT_COLUMNS = [
    "name",
    "label",
    "facility_type",
    "lga",
    "ward",
    "community",
    "latitude",
    "longitude",
    "geometry",
]


def _clean(value: str) -> str:
    return (value or "").strip()


def find_gps(row: dict, gps_col: str) -> tuple[str, str] | None:
    """Return (latitude, longitude) from a Kobo geopoint export, or None."""
    # 1) Preferred: split columns exported by KoboToolbox for geopoints
    lat = _clean(row.get(f"{gps_col}_latitude", ""))
    lon = _clean(row.get(f"{gps_col}_longitude", ""))
    if lat and lon:
        candidate = (lat, lon)
    else:
        # 2) Fallback: the full "lat lon alt accuracy" column
        full = _clean(row.get(gps_col, ""))
        parts = re.split(r"[\s;,]+", full)
        if len(parts) >= 2:
            candidate = (parts[0], parts[1])
        else:
            return None

    try:
        lat_f, lon_f = float(candidate[0]), float(candidate[1])
    except ValueError:
        return None
    if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
        return None
    return f"{lat_f:.6f}", f"{lon_f:.6f}"


def detect_gps_column(fieldnames: list[str]) -> str | None:
    for f in fieldnames:
        if f == "facility_gps" or f.endswith("_gps") or "facility_gps" in f:
            if f"{f}_latitude" in fieldnames or f in fieldnames:
                return f
    # last resort: any column ending in _latitude
    for f in fieldnames:
        if f.endswith("_latitude"):
            return f[: -len("_latitude")]
    return None


def load_existing(path: Path) -> tuple[list[dict], set[str], int]:
    """Return (existing rows, dedupe keys, highest FAC number found)."""
    if not path.exists():
        return [], set(), 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = [dict(r) for r in reader]
    keys = {(r.get("label", "").strip(), r.get("lga", "").strip()) for r in rows}
    max_n = 0
    for r in rows:
        m = re.match(r"FAC(\d+)$", (r.get("name") or "").strip())
        if m:
            max_n = max(max_n, int(m.group(1)))
    return rows, keys, max_n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("export", type=Path, help="CSV exported from KoboToolbox (capture form)")
    ap.add_argument(
        "-o", "--output", type=Path, default=FACILITIES_CSV,
        help=f"facility register to update (default: {FACILITIES_CSV})",
    )
    args = ap.parse_args()

    locs = load_locations()

    with open(args.export, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows_in = list(reader)

    gps_col = detect_gps_column(fieldnames)
    missing = [c for c in ("facility_name", "lga_sel", "ward_sel", "community_sel") if c not in fieldnames]
    if missing:
        raise SystemExit(
            f"{args.export.name}: not a capture-form export? Missing columns: {', '.join(missing)}\n"
            f"Found columns: {', '.join(fieldnames)}"
        )

    existing, keys, next_num = load_existing(args.output)
    added = skipped_dup = skipped_gps = skipped_name = 0

    for row in rows_in:
        name = _clean(row.get("facility_name"))
        if not name:
            skipped_name += 1
            continue

        gps = find_gps(row, gps_col or "facility_gps")
        if gps is None:
            skipped_gps += 1
            continue
        lat, lon = gps

        lga_label = locs.label_by_id.get(_clean(row.get("lga_sel")), _clean(row.get("lga_sel")))
        ward_label = locs.label_by_id.get(_clean(row.get("ward_sel")), _clean(row.get("ward_sel")))
        community_label = locs.label_by_id.get(
            _clean(row.get("community_sel")), _clean(row.get("community_sel"))
        )
        type_id = _clean(row.get("facility_type"))
        type_label = FACILITY_TYPE_LABELS.get(type_id, type_id or "Other")

        key = (name, lga_label)
        if key in keys:
            skipped_dup += 1
            continue

        next_num += 1
        rec = {
            "name": f"FAC{next_num:03d}",
            "label": name,
            "facility_type": type_label,
            "lga": lga_label,
            "ward": ward_label,
            "community": community_label,
            "latitude": lat,
            "longitude": lon,
            "geometry": f"{lat} {lon} 0 0",
        }
        existing.append(rec)
        keys.add(key)
        added += 1

    if added:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=OUT_COLUMNS)
            writer.writeheader()
            writer.writerows(existing)

    print(f"Facility register : {args.output}")
    print(f"  added           : {added}")
    print(f"  skipped (already in register): {skipped_dup}")
    print(f"  skipped (no valid GPS)       : {skipped_gps}")
    print(f"  skipped (no facility name)   : {skipped_name}")
    if skipped_gps:
        print(
            "\nNOTE: rows without GPS were NOT added - the report form's "
            "on-site check needs coordinates."
        )
    print(
        "\nNext: upload the file in KoboToolbox -> Settings -> Media of the "
        "REPORT project, then redeploy."
    )


if __name__ == "__main__":
    main()
