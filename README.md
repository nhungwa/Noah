# Noah — KoboToolbox "Capture All Facility" + On-Site (GPS) Facility Report

Two ready-to-deploy **KoboToolbox XLSForms** for mapping every facility in your
LGA/Ward/Community, protected with **per-collector passwords**, plus a second
**GPS-geofenced report form** that can only be submitted while the collector is
physically **at the facility** (within a configurable radius).

| | |
|---|---|
| **Form 1 — `forms/Capture_All_Facilities.xlsx`** | Registers (captures) each facility: collector name + password, GPS, LGA, Ward, Community, facility name/type, picture of the facility. |
| **Form 2 — `forms/Facility_Report_Geofenced.xlsx`** | The "report" form: collector name + password, pick the facility, **GPS check (must be within 100 m)**, then facility status/condition/notes/photo. |
| **`data/enumerators.csv`** | Collector names **and their passwords** (external file, easy to edit). |
| **`data/locations.csv`** | Your LGA → Ward → Community list (cascading dropdowns). |
| **`data/facilities.csv`** | The facility register: every facility with its GPS coordinates (feeds Form 2). |
| **`scripts/build_forms.py`** | Re-builds the two `.xlsx` forms and validates them with pyxform (the converter KoboToolbox itself uses). |
| **`scripts/export_facilities.py`** | Turns a Kobo data export of Form 1 into an updated `facilities.csv` for Form 2. |

---

## 1. Form 1 — Capture All Facilities (what you asked for)

| Your requirement | Field in the form | Type |
|---|---|---|
| Name who collect | `collector` — "Name of collector" | Dropdown of people from `enumerators.csv` |
| **Password** | `access_code` — private code per collector | Text, characters **masked** in KoboCollect, wrong code blocks the form |
| GPS | `facility_gps` | Device GPS (waits for ≤ 10 m accuracy, warns above 50 m) |
| LGA | `lga_sel` | Dropdown (cascading) |
| Ward | `ward_sel` | Dropdown (filtered by LGA) |
| Community | `community_sel` | Dropdown (filtered by LGA + Ward) |
| FACILITY | `facility_name` + `facility_type` | Text + dropdown |
| Picture of Facility | `facility_photo` | Camera photo (required, max 1600 px) |
| Who/when/where | `start`, `end`, `deviceid`, `username` | Automatic metadata in every submission |

Sections of the form:

1. **Access** — collector selects their name, types their access code.
2. **Location** — LGA → Ward → Community + GPS.
3. **Facility** — name, type, picture.
4. **Review and submit** — summary of everything entered.

> **Why Form 1 does not block on "being at the facility":** when you are
> *capturing a brand-new facility*, its coordinates do not exist yet — the GPS
> point you record in Form 1 **becomes** the facility's official location.
> The "you must be at the facility" rule is enforced by **Form 2** (and any
> future report), which uses those captured coordinates as the fence.

---

## 2. Form 2 — Facility Report (must be on site: the GPS gate)

How the geofence works, step by step:

1. Collector picks the facility from `facilities.csv` (also shown as markers on a map in KoboCollect).
2. The form pulls that facility's **registered latitude/longitude** from the CSV.
3. The form captures the collector's **current GPS position**.
4. It computes `distance(current position, facility coordinates)` with the
   XLSForm `distance()` function and **requires the distance ≤ 100 metres**:
   * a **constraint** on the GPS question refuses the position if too far away
     ("You must be within 100 metres of the selected facility…"),
   * a live note shows the exact distance: *"Distance from the facility: 37 metres (allowed radius: 100 m)"*,
   * the **report questions only unlock** once the collector is inside the radius.
5. Report fields (sample — extend as you like): operational status, condition,
   observations, extra photo.

**Changing the radius:** edit `GEOFENCE_RADIUS_M = 100` in
`scripts/build_forms.py`, re-run the build (see §6), re-upload the `.xlsx`,
redeploy.

**Field notes:**

* **Use the KoboCollect Android app for enforcement.** In *web forms* (Enketo)
  the respondent can drop a pin anywhere on the map or type coordinates — the
  distance check still runs, but the position itself is self-declared. In
  KoboCollect the position comes from the device GPS automatically.
* GPS is weaker **indoors** — the form says to stand at the facility or its
  gate. Accuracy targets are `capture-accuracy=10` (wait for a ≤ 10 m fix) and
  `warning-accuracy=50` (warn if worse than 50 m); tune `GPS_PARAMS` in the
  build script if your area needs it.
* Every registry row in `facilities.csv` **must** have valid `latitude` /
  `longitude` — rows without coordinates are skipped by the export script
  precisely because the gate needs them.

---

## 3. Passwords (per collector)

Passwords live in **`data/enumerators.csv`**:

```csv
name,label,password
adeyemi_a,Adenike Adeyemi,CHANGE-ME-001
musa_b,Baba Musa,CHANGE-ME-002
```

* `name` — unique id, **no spaces** (this is what gets stored in the data).
* `label` — the name shown in the dropdown.
* `password` — that person's private access code.

The form checks the typed code against the row of the selected name
(`pulldata()`), shows *"Wrong access code…"* on a mismatch, and hides every
other section of the form until the correct code is entered.

**To change passwords:** edit the CSV → KoboToolbox **Settings → Media** →
re-upload `enumerators.csv` → redeploy. No rebuild of the Excel form needed.

### Be honest about what this protects

* The access code is checked **inside the form**, so anyone who downloads the
  form's files could read the CSV/XML. Treat it as **access control + audit**
  (you know *who* collected each record, and casual users cannot enter), not
  as encryption.
* For real security also: give each collector their own KoboToolbox login
  (the `username` metadata is recorded automatically), keep the project
  private ("Only logged-in users can view/submit" — turn OFF public links),
  and prefer the KoboCollect app with a logged-in account.
* `appearance="masked"` (asterisks while typing) works in **KoboCollect**; in
  web forms the code is visible while typing.
* **Advanced (Collect only):** KoboToolbox lets you upload a *blank*
  `enumerators.csv` to the server and copy the real file onto each device
  manually, so the passwords never leave your hands (see Kobo's
  "Pulling data from an external CSV → Protecting sensitive data").

> ⚠️ The sample passwords (`CHANGE-ME-…`) are placeholders — replace them
> before you deploy for real.

---

## 4. Deploy on KoboToolbox (first time)

1. **Prepare your data files** (edit before anything else):
   * `data/locations.csv` — replace the `EXAMPLE_…` rows with your real
     LGA / Ward / Community list (one row per community).
   * `data/enumerators.csv` — your collectors and their passwords.
2. **Rebuild the forms** so they include your locations list:
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   .venv/bin/python scripts/build_forms.py
   ```
   (This also validates both forms with pyxform — you should see
   `[pyxform OK]` twice.)
3. In KoboToolbox create a **project for Form 1** → **New project → Upload
   XLSForm** → upload `forms/Capture_All_Facilities.xlsx` → **Deploy**.
4. In that project: **Settings → Media** → upload **`enumerators.csv`** →
   redeploy if asked.
5. Repeat for **Form 2**: new project → upload
   `forms/Facility_Report_Geofenced.xlsx` → **Settings → Media** → upload
   **`enumerators.csv` and `facilities.csv`** → Deploy.
6. Test both forms with **Preview** (wrong password must be refused; in the
   report form, try submitting from more than 100 m away — it must refuse).
7. Collect in the field either through the **web form link** (share
   carefully — see §3) or **KoboCollect** app (recommended: open the app →
   server settings → your Kobo URL → *Get Blank Form*).

**Media file names must match exactly** (`enumerators.csv`, `facilities.csv`)
or the form will report "CSV file cannot be found".

---

## 5. The ongoing workflow (capture → register → on-site report)

```
 ┌────────────────────────┐     ┌──────────────────────────┐
 │ FORM 1 (field)         │     │ KoboToolbox              │
 │ Capture_All_Facilities │ --> │ Data → Download → CSV    │
 │ GPS + photo + LGA/ward │     └────────────┬─────────────┘
 └────────────────────────┘                  │
                                             ▼
 ┌────────────────────────┐     ┌──────────────────────────┐
 │ FORM 2 (field)         │ <-- │ data/facilities.csv      │
 │ Report, GPS-geofenced  │     │ (built from the export)  │
 │ only inside 100 m      │     └──────────────────────────┘
 └────────────────────────┘               ▲
                                          │
                     python scripts/export_facilities.py export.csv
```

1. Collectors run **Form 1** over your LGA and capture every facility
   (GPS + picture).
2. In KoboToolbox: **Data → Downloads → CSV** (with *values* or *labels* —
   both work) and save the export.
3. ```bash
   .venv/bin/python scripts/export_facilities.py path/to/export.csv
   ```
   * **appends** new facilities to `data/facilities.csv`,
   * **skips** duplicates (same facility name + LGA already registered),
   * **skips** rows with no valid GPS (the geofence needs coordinates),
   * renumbers ids (`FAC001`, `FAC002`, …).
4. Upload the updated `facilities.csv` to **Settings → Media** of the
   *report* project and **redeploy**.
5. Collectors now run **Form 2** for their on-site reports — the facility
   dropdown is up to date and the 100 m gate is active.

---

## 6. Customising the forms

Everything lives in the build script — change it, rebuild, re-upload:

```bash
.venv/bin/python scripts/build_forms.py
```

| What you want to change | Where |
|---|---|
| LGA / Ward / Community list | `data/locations.csv` → rebuild |
| Collector names & passwords | `data/enumerators.csv` → re-upload to Media (no rebuild) |
| Facility type options | `FACILITY_TYPES` in `scripts/build_forms.py` |
| Report questions (status, condition, notes…) | `build_report_form()` in `scripts/build_forms.py` |
| Geofence radius | `GEOFENCE_RADIUS_M` in `scripts/build_forms.py` |
| GPS accuracy targets | `GPS_PARAMS` in `scripts/build_forms.py` |
| Password message / wording | labels & `constraint_message` rows in `scripts/build_forms.py` |

After editing the `.xlsx` settings sheet, bump `version` so KoboToolbox and
devices pick up the new revision.

**Important:** the id stored in submitted data is generated from the names in
`locations.csv` (e.g. `EXAMPLE_Ward_A1`). Do not rename or re-sort rows after
you have started collecting — add new rows at the end instead.

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| "CSV file cannot be found" when opening the form | Upload the CSV in **Settings → Media** with the exact file name, then redeploy. |
| Access code always rejected | Check `data/enumerators.csv` has columns `name,label,password`; the `name` must match the dropdown value exactly; no stray spaces in the password cell. |
| Password visible while typing | You are using a web form — the `masked` appearance works in KoboCollect only (§3). |
| Report form says "You must be within 100 metres…" though you are there | Stand outdoors for a better fix; check the facility's coordinates in `facilities.csv` (a wrong registry point moves the fence); the live distance note shows how far the form thinks you are. |
| Report section never appears | You are still outside the radius (or the registry row has no coordinates). Watch the distance note. |
| GPS takes a long time to record | Expected under roofs/trees — `capture-accuracy=10` waits for a 10 m fix; relax it in `GPS_PARAMS` and rebuild if needed. |
| Deploy fails after an edit | Run `.venv/bin/python scripts/build_forms.py` — pyxform prints the exact row/column causing the error. |
| Web-form link was shared too widely | Turn off public access in project **Settings → Sharing**; require logins. |

---

## 8. Repository layout

```
├── README.md                      ← you are here
├── requirements.txt               ← pyxform + openpyxl (to rebuild the forms)
├── data/
│   ├── enumerators.csv            ← names + passwords (upload as media)
│   ├── locations.csv              ← LGA / Ward / Community (baked into forms)
│   └── facilities.csv             ← facility register w/ GPS (upload as media)
├── forms/
│   ├── Capture_All_Facilities.xlsx        ← Form 1 (upload to Kobo)
│   └── Facility_Report_Geofenced.xlsx     ← Form 2 (upload to Kobo)
└── scripts/
    ├── build_forms.py             ← regenerate + validate both forms
    ├── export_facilities.py       ← Kobo export → facilities.csv
    └── common.py                  ← shared lists/helpers
```
