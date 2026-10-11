# Visarjan Ghat Watch — web UI

Next.js frontend for the Bhopal Municipal Corporation officer who plans Durga visarjan (20 Oct 2026). It follows the team's PRD v2 (an internal planning document, not published in this repository): **Rank → Flag → Recommend → Plan → Assign → Estimate → Brief**.

> **Shows backend output only.** Every figure, flag, reading, grid cell, action and date comes from the Python backend in the repository root, exported to `lib/data/generated/backend.json`. Readings are historical (2023–2025); there are no 2026 measurements. Report page references are only partly checked against the PDFs (see the root README).

## Run it

1. Install Node.js 20 or later.
2. `npm ci`
3. `npm run dev`, then open http://localhost:3000 (redirects to `/en/`; Hindi at `/hi/`).
4. Static build: `npm run build` writes the site to `out/`. Serve it with any static server, e.g. `npx serve out`.

Checks: `npm run check:wording` (banned wording) and `npm run check` (wording + lint + build).

## Screens

| Screen | Route | What it shows |
|---|---|---|
| Overview (Rank, Flag) | `/[lang]/` | Backend ranking, tiers, flags, headline counts, data gaps |
| Ghat detail (Flag → Recommend) | `/[lang]/ghats/[siteId]/` | Flag notes with page references, every expected cell of the reading grid, recommended actions, 27 Oct target |
| Action plan | `/[lang]/plan/` | The backend's dated plan, 11–27 Oct, with filters by ghat and task group |
| Work orders (Assign) | `/[lang]/orders/`, `/[lang]/orders/[siteId]/` | Draft A4 orders to print or copy; roles, zone and report-back date left blank for the officer |
| Cost estimator | `/[lang]/estimate/` | Quantity × rate calculator. No rates are supplied and none are invented |
| Brief | `/[lang]/brief/` | Forwardable brief (print, Markdown download); no cost figures |
| Method & limitations | `/[lang]/method/` | Criteria, value states, ranking rules, coverage, limitations |

## Where the data comes from

All screens read data only through `lib/data/index.ts`, which uses the backend source in `lib/data/backend.ts`.

| Tag shown in the UI | Meaning | Files |
|---|---|---|
| Backend output | Computed by the Python backend from the supplied track CSV and CPCB criteria file | `lib/data/generated/backend.json` (generated; do not edit by hand) |
| PRD v2 | Rule or plan-window descriptions from the PRD, not data | `lib/data/static.ts` |
| Not assigned | Intentionally empty until an officer fills it in | work orders, plan, estimator |

`lib/data/static.ts` holds presentation text only: Hindi site and water-body names, PRD rule and window descriptions, role examples and estimator line items.

**Regenerating the data.** From the repository root run `python -m ghatwatch.export_web`, or `npm run export:data` from this folder. A backend test fails if the committed export is out of date.

**Build-time checks.** `lib/data/backend.ts` stops the build if the export names a site without a label in `static.ts`, lacks a grid cell, or has a different number of plan windows from the PRD descriptions.

**Reading grid.** Each ghat page shows the 6 seasons × 3 phases × 13 parameters grid from the backend evidence table. Cells with no row in the CSV appear as **No table in report**, never as passing. Display states follow the backend's value states: Reading, BDL, ND, Not sampled, No table in report, Unresolved flag, and Not a possible reading.

**Page references.** A reference is marked as matched only when every reading it cites was matched in the partial manual PDF spot check (`verification/pdf_spot_checks.csv`). All other references say "page not yet checked".

## Known issues

- **PRD v2 discrepancy, needs an explicit correction in the source document.** §6.5 says "High risk (6 of 7): all except Hathaikheda". The PRD's own high-risk rule (§6.3: any DO below 4 mg/l, or DO below 5 mg/l in more than half of readings) applied to its per-ghat evidence gives **5 of 7**. Khatlapura's lowest DO is 4.0 and 8 of 18 readings were below 5, so it meets neither condition. The backend applies the stated rule and also gives 5 of 7. The PRD has not been edited here.
- **Hindi text is provisional.** It is a translation pending review by a fluent reader.
- **Page references are only partly checked.** Only a partial manual spot check against the PDFs has been done.
