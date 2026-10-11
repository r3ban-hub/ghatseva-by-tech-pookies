# Visarjan Ghat Watch

Ranks Bhopal's seven idol-immersion ghats by water-quality risk ahead of **Durga visarjan on 20 October 2026**, using MPPCB's 2023–2025 visarjan reports. It also produces a dated action plan, one work order per ghat, an evidence table and a Hindi + English officer brief, and shows all of it in a bilingual web UI.

- **Track:** Claude Impact Lab × Cerebras, Bhopal — Track 2: Visarjan Ghat Watch
- **User:** the Bhopal Municipal Corporation (BMC) officer who plans Durga visarjan at the ghats
- **Spec:** the team's PRD v2 (an internal planning document, not published here); the UI cites its sections for rules and plan windows
- **Team name:** Tech Pookies

> **Status:** a tested Python backend (`ghatwatch/`) and a static Next.js web UI (`web/`) that shows only the backend's outputs. Nothing is live: all readings are historical (2023–2025). The cost estimator is a calculator with no rates supplied; it shows no cost figures unless an officer types in cited rates.

## Run it (5 steps)

1. Install **Python 3.13** and **Node.js 20 or later** (tested versions: see [Tested versions](#tested-versions)).
2. From the repository root: `python -m pip install -r requirements.txt`
3. Run the backend tests: `python -m pytest -q`
4. Install the UI: `cd web` then `npm ci`
5. Start the UI: `npm run dev`, then open http://localhost:3000 (English at `/en/`, Hindi at `/hi/`). For a static site, `npm run build` writes it to `web/out/`.

The UI reads `web/lib/data/generated/backend.json`, which is committed. After changing data, config or backend code, regenerate it with `python -m ghatwatch.export_web` (or `npm run export:data` from `web/`); a test fails if the committed file is out of date.

Backend outputs from the command line:

```
python -m ghatwatch.load                          # data validation summary
python -m ghatwatch.ranking                       # 7-ghat ranking with reasons
python -m ghatwatch.plan                          # dated plan, 11–27 Oct 2026
python -m ghatwatch.orders "Malikhedi kund"       # one work order (Markdown)
python -m ghatwatch.evidence evidence.csv         # evidence table (CSV)
python -m ghatwatch.brief en                      # officer brief (en | hi)
```

## What works and what doesn't

| Works | Does not exist yet |
|---|---|
| Loading and validating the supplied CSVs, and building the 1,638-cell expected grid | Sourced cost rates: the estimator is a calculator only, and briefs say "Not estimated" |
| CPCB Class B comparisons and the Class D severe-DO line | ZIP export, WhatsApp text, clickable PDF-page links |
| Deterministic ranking with tiers and flags | Any automatic sending of orders (by design, never) |
| Dated action plan from editable rules (`config/action_rules.csv`) | Full verification of page references against the PDFs (only a partial spot check, below) |
| Per-ghat work orders routed to roles (`config/ghat_assignments.csv`) | A fluent review of the Hindi text |
| Evidence CSV and Hindi + English briefs | Live or 2026 data |
| Web UI in English and Hindi: ranking, ghat detail with every reading, plan, draft work orders (print / copy), brief (print / Markdown download), estimator calculator, method page | |

## Ranking produced from the supplied data

| # | Ghat | Tier | High risk | DO < 5 mg/l | DO < 4 mg/l | BOD > 3 mg/l | pH outside 6.5–8.5 | Flags |
|---|---|---|---|---|---|---|---|---|
| 1 | Bairagarh (Sant Hirdaram) kund | 1 | yes | 11/13 | 6 | 13/13 | 0/13 | DO_SEVERE, DO_ZERO, DO_OFTEN_LOW, BOD_OFTEN_HIGH, DATA_GAP |
| 2 | Malikhedi kund | 1 | yes | 9/13 | 3 | 11/13 | 0/13 | DO_SEVERE, DO_OFTEN_LOW, BOD_OFTEN_HIGH, DATA_GAP |
| 3 | Khatlapura ghat | 2 | no | 8/18 | 0 | 15/17 | 1/18 | BOD_OFTEN_HIGH, PH_OUT, DATA_GAP |
| 4 | Rani Kamlapati ghat / Kamla Park kund | 2 | yes | 6/18 | 4 | 18/18 | 0/18 | DO_SEVERE, BOD_OFTEN_HIGH, SITE_IDENTITY |
| 5 | Shahpura lake ghat | 2 | yes | 5/18 | 3 | 18/18 | 0/18 | DO_SEVERE, BOD_OFTEN_HIGH |
| 6 | Prempura ghat | 2 | yes | 3/18 | 1 | 9/15 | 2/17 | DO_SEVERE, BOD_OFTEN_HIGH, PH_OUT, DATA_GAP |
| 7 | Hathaikheda dam / kund | 3 | no | 0/18 | 0 | 16/18 | 3/18 | BOD_OFTEN_HIGH, PH_OUT |

Counts are readings outside the limit / usable readings. Hathaikheda is ranked last, but that is **not** a clearance: BOD was above 3 mg/l in 16 of 18 readings (up to 22 mg/l) and pH reached 9.2.

## Data sources

All data comes from the Track 2 pack. **No extra data was added.**

| File | What it is |
|---|---|
| `data/bhopal_ghats_2023_2025.csv` | 1,524 readings: 7 ghats, 2023–2025, Ganesh and Durga, before / during / one week after |
| `data/sample_bhopal_2025.csv` | The 2025 rows of the file above |
| `data/cpcb_water_quality_criteria.csv` | CPCB water-quality criteria, classes A–E |
| `data/DATA_DICTIONARY.md` | Column meanings, codes and sources |

The files are byte-identical copies of the pack. `tests/test_pipeline.py` checks their SHA-256 hashes on every run.

Original reports, as listed in the data dictionary:

- [MPPCB Idol Immersion Report 2023 (CPCB format)](https://www.mppcb.mp.gov.in/proc/mon/Idol_immer._Report_23_CPCB.pdf)
- [MPPCB Ganesh and Durga Visarjan Report 2024](https://www.mppcb.mp.gov.in/proc/mon/Ganesh_and_Durga_visarjan_report-2024.pdf)
- [MPPCB Ganesh and Durga Visarjan Report 2025](https://www.mppcb.mp.gov.in/proc/mon/Ganesh_and_Durga_visarjan_report-2025.pdf)
- [CPCB water quality criteria](https://cpcb.gov.in/water-quality-criteria/)

The Python backend and the built site make no network calls, and nothing is scraped. Installing and building the UI downloads npm packages and two Google Fonts (Inter, Noto Sans Devanagari), which the built site then serves itself.

## Method

1. **Load and validate** (`ghatwatch/load.py`). Required columns and allowed values are checked; a bad file stops with an error that names the file, column and row.
   - Every cell gets exactly one state: `numeric`, `bdl`, `nd`, `not_sampled`, `no_table`, `unknown_flag` or `invalid_value`.
   - BDL is never 0. Missing readings are never 0.
   - The 114 cells with no table in any report become `no_table`.
   - A flag that conflicts with its printed text, or a negative reading, is reported as a data-quality issue.
2. **Compare with CPCB limits** (`ghatwatch/criteria.py`). Limits are read only from the criteria CSV.
   - **Class B** (outdoor bathing): DO ≥ 5 mg/l, BOD ≤ 3 mg/l, pH 6.5–8.5.
   - **Class D** DO ≥ 4 mg/l is used only as a "severe" line.
   - Values exactly on a limit pass. Only `numeric` cells are compared; everything else is `unassessable`, never a pass.
3. **Rank** (`ghatwatch/ranking.py`). Rates use usable numeric readings only.
   - Tier 1: DO below 5 in more than half of readings.
   - Tier 2: any DO below 5.
   - Tier 3: no DO failure, but BOD or pH failed.
   - Tier 4: no failure in any reading taken.
   - Ties break by DO fail rate, then DO-severe share, BOD fail rate, median BOD, and name.
   - A ghat is **high risk** if it has DO_SEVERE or DO_OFTEN_LOW.
   - Data gaps never lower a tier; they add a DATA_GAP flag.
   - Ranking refuses to run if the criteria CSV's limit directions contradict what the flags assume (DO a minimum, BOD a maximum, pH a range); the error names the parameter and the expected direction. Limit values are not restricted.
4. **Plan** (`ghatwatch/plan.py`). `config/action_rules.csv` maps flags to actions. Windows such as `D-3 to D+7` become real dates around D = 20 Oct 2026, and the plan runs 11–27 Oct 2026. DATA_GAP ghats always get sampling before 20 Oct; SITE_IDENTITY ghats always get a field check.
5. **Work orders** (`ghatwatch/orders.py`). Each ghat gets one page listing every planned action once, routed by task group to a **role** from `config/ghat_assignments.csv`. An unknown role prints `Assign: ________`.
6. **Evidence** (`ghatwatch/evidence.py`). One row per expected cell (1,638 rows): printed value, state, limits, results, source page and report.
7. **Brief** (`ghatwatch/brief.py`, `templates/`). Fixed prose with every figure, rank and date inserted by code, in English and Hindi.
8. **Web export** (`ghatwatch/export_web.py`). Writes the ranking, flag notes, every grid cell and reading, the 36 dated actions, targets and plan windows to `web/lib/data/generated/backend.json`.
9. **Web UI** (`web/`, Next.js static export). Reads only that export through `web/lib/data/backend.ts`; it never computes a ranking, flag, limit comparison, date or cost. Presentation text that is not data (Hindi site names, PRD rule and window descriptions, role examples) lives in `web/lib/data/static.ts`. The UI's Brief page assembles its own forwardable brief from the same data; `python -m ghatwatch.brief` produces the templated brief.

## Assumptions

- **Report pages.** `source_page` is taken as the 1-based PDF page in that year's report, and the year-to-report mapping comes from the data dictionary. Both were confirmed only for the pages in the spot check below.
- **BOD.** The data's `BOD` is taken to be the criteria file's "BOD (5 days 20C)". The data dictionary gives BOD the same Class B limit (3 or less), but the reports do not state the test method.
- **Units.** Units are the standard ones assumed by the data dictionary; the reports print none.
- **Sampling role.** Water sampling is routed to "MPPCB regional office, Bhopal". This is an **assumption**, marked "(assumed — confirm)" on every work order.
- **Actions.** All 8 action rules are **team recommendations**, not verified against CPCB or MPPCB guidelines. Each one carries "Recommendation — verify with MPPCB / CPCB guidelines."

## Source verification (partial)

On 11 Oct 2026, **8 report pages** were extracted with `pdftotext` (during an AI-assisted audit) and **12 readings** were compared with the data. All 12 matched. They are recorded in `verification/pdf_spot_checks.csv`. Every row is labelled "PARTIAL manual spot check", and the record is validated against the data whenever it is used: a page or printed value that disagrees stops with an error.

| Report | Pages | Readings checked |
|---|---|---|
| 2023 | 26, 60 | Bairagarh DO = 0 (three readings) and BOD 10 |
| 2024 | 69, 70 | Khatlapura DO 4, Prempura DO 3.9 |
| 2025 | 28, 29, 64, 65 | Bairagarh DO = 0, Malikhedi DO 0.6, Rani Kamlapati DO 2.5 / 2.4 / 2.6, Shahpura DO 2.5 |

A text search of the 2025 report found Bairagarh and Malikhedi only on Ganesh pages, which confirms that their Durga 2025 tables are absent.

**This is a spot check, not full verification.** The other pages have not been checked. The outputs mark only the 12 checked readings, never whole pages:

- **Evidence CSV (`page_verified`):** "spot-checked — this reading matched page N of the PDF in a partial manual check…" for the 12 readings; "no — … not yet checked against the PDF" for the other 1,512 rows with a page; blank for the 114 absent-table rows.
- **Work orders:** under each reason, a ✓ line lists that reason's checked readings. A note gives the size of the partial check and says all other page references are not yet checked.
- **Briefs:** a cited reading carries ✓ only if it is one of the 12. The limits section says how many readings and pages were checked and that the rest are not.

## Limitations

- **No total-coliform data.** No ghat can be confirmed as meeting Class B, and the tool never says it does.
- **No 2026 readings.** Current water quality is unknown.
- **Levels, not causes.** Readings show measured levels. BOD was already above 3 mg/l in 32 of 37 pre-immersion readings, so the data cannot show that immersion caused the results. The tool makes no health claims.
- **Site identity is unresolved.** "Rani Kamlapati ghat / Kamla Park kund" appears as a Kamla Park kund in Ganesh tables and as a Lower Lake ghat in Durga tables, and may be two places. The tool flags this and does not choose.
- **Gaps in the reports.** Bairagarh and Malikhedi have no Durga 2025 table, and suspended solids is missing from Durga 2023 and 2025.
- **Assignments are blank.** All zone / ward fields and 28 of 35 role assignments are empty, because they are not in the supplied data. The officer fills them in.
- **Name screening is a heuristic.** Phone numbers and emails are reliably rejected. Names are caught only when written with an honorific (Shri, Smt, Dr, Mr…). A bare name such as "R. Sharma" cannot be detected, so keep the file to role titles.
- **Hindi is provisional.** All Hindi text is marked as a provisional translation until a fluent reader reviews it.
- **The brief is long.** It is about 450 English prose words, above the one-page (~250 word) target.
- **Generation date.** The brief's date defaults to today. Pass `generated_on` for reproducible output.
- **The UI is static.** It shows the export committed with the code; it does not read files or fetch data at run time.

## Tests

```
python -m pytest -q                 # backend, from the repository root
cd web && npm run check             # UI: wording rules + lint + static build
```

Result on 11 Oct 2026: backend **447 passed**, no warnings (Python 3.13.7, pandas 3.0.6, numpy 2.3.0, pytest 9.1.1, Windows 11). UI: wording check passed (61 files, 11 rules), lint passed, and the static build produced 44 pages (Node.js 24.15.0, npm 11.12.1, Next.js 16.4.0).

`tests/test_pipeline.py` is the end-to-end check: everything is built from one load and cross-checked. Run it on its own with `python -m pytest tests/test_pipeline.py -v`.

### Tested versions

Only Python **3.13.7** with pandas **3.0.6** has been tested, and `requirements.txt` pins those versions. **Python 3.12 and pandas 2.x have not been tested.** The UI was built with Node.js 24.15.0 and npm 11.12.1, using the versions locked in `web/package-lock.json`.

## Project layout

| Path | What it holds |
|---|---|
| `ghatwatch/` | Backend modules: load, criteria, ranking, plan, orders, evidence, brief, export_web |
| `config/` | Editable action rules and role assignments (roles only) |
| `data/` | The supplied Track 2 files, unchanged |
| `templates/` | Brief templates (English and Hindi) |
| `verification/` | The partial manual PDF spot-check record |
| `tests/` | Backend test suite |
| `web/` | Next.js UI; `web/lib/data/generated/backend.json` is the backend export it reads |

## Privacy

No personal data is stored. `config/ghat_assignments.csv` holds role titles only. The loader rejects phone numbers, email addresses and honorific-prefixed names (see the limitation above). No secrets are needed or stored.

## License

Code: MIT; see [LICENSE](LICENSE). The files in `data/` are unchanged copies from the Bhopal Impact Lab 2026 Track 2 participant pack (https://github.com/Laaaaksh/bhopal-impact-lab-2026, `tracks/02-visarjan-ghat-watch/data`), derived from MPPCB and CPCB publications; they are not covered by this licence.
