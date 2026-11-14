# Agent 06 — Independent validation (and the Athena case study)

**Recommended model:** Claude Opus 5.5 · **Effort:** high
**Attach:** `01_CONTRACT.md`. Give access to the repo `lunascout/` and the API URL (local or deployed). Web search must be enabled.
**Supervisor:** Person D. Run this in a **fresh session** that did not write the engine, so the work isn't grading itself.

---

## Prompt (copy everything below this line)

You are the independent reviewer and test lead on a 4-person team at the NASA Space Apps Challenge 2026 (deadline Sunday Nov 15 23:59). Our project, **LunaScout**, evaluates lunar south pole landing ellipses: for every sample point inside the ellipse it computes a terrain horizon from real LOLA topography (5 m/px DEM, Site20 = Mons Mouton, NASA GSFC PGDA), Sun and Earth positions from JPL Horizons, and slope, then classifies points as viable / risky / not viable and gives a survival probability. The attached `CONTRACT.md` describes the conventions, the API and the classification rules. **You did not write this code. Your job is to find what's wrong before the judges do.** Reply to me in Spanish; write the report in English (it may be linked from our submission).

Judges score Impact, Creativity, **Validity**, Relevance and Presentation. Your work is our Validity score.

### Tasks (in this order; report progress after each)

**1. Athena case study: research (web search, cite everything)**
Find from primary or authoritative sources (NASA, Intuitive Machines, LROC/ASU image releases, reputable space press):
- IM-2 "Athena" **intended landing coordinates** (lat, lon) and **actual touchdown coordinates**. LROC published an image of the landing site; NASA/IM statements give the distance (IM said ~250 m; NASA said "more than 400 m").
- Touchdown time in UTC (reported around 12:30–12:32 p.m. EST on March 6, 2025 → ~17:30 UTC; verify).
- What ended the mission (shadowed crater, tipped over, solar panel orientation, cold) and when (~13 h after landing per SpacePolicyOnline).
Record each fact with its source URL and an exact short quote (< 15 words). If coordinates can't be found, say so plainly. **Never estimate them silently.**

**2. Athena case study: run LunaScout**
- Check whether the intended and actual sites lie inside our DEM coverage (`GET /api/meta`). If not, report it. That's critical for the pitch; propose an alternative (e.g., the larger PGDA mosaic, or presenting a synthetic "Athena-like" scenario honestly labeled as such).
- If covered, run `POST /api/analyze` with target = intended site, `landing_utc` = actual touchdown time, an ellipse that contains the actual site (state the size you chose and why), Athena-like limits (state assumptions), and also a run targeted at the actual site.
- Answer: did LunaScout flag risk? Was the actual site unlit at touchdown or soon after? What was the survival probability of the ellipse? Is the result consistent with what happened? **Report honestly even if it isn't.** Note that Athena also tipped over, which our model only partly captures (slope).

**3. Ephemeris cross-check**
For 3 sites (the DEM center, a point 5 km away, Shackleton −89.67/129.78) and 3 random hours in 2025–2028, query Horizons directly (`CENTER='coord@301'`, `COORD_TYPE='GEODETIC'`, `SITE_COORD='lon,lat,0'`, `QUANTITIES='4'`) and compare with `engine.ephemeris.local_az_el`. Tolerances: Sun ≤ 0.02°, Earth ≤ 0.05°. Known value: Shackleton 2027-01-01 00:00 UT → Sun az 133.339447°, el 0.787435°.

**4. Physics & sanity checks** (write them as pytest tests in `engine/tests/test_validation.py` where possible)
- Max Sun elevation at a site over a year ≈ (90 − |lat|) + 1.54° (geometric elevation, independent of terrain).
- Sun azimuth circles the full 360° over a lunar day (~29.5 days) at polar sites.
- Earth elevation oscillates with a ~27.3-day period.
- Horizon: flat-sphere synthetic test ≈ −0.087° at 2 m height; plateau tops get more sunlight hours than nearby crater floors.
- Changing `landing_utc` by ~14.75 days (half a synodic month) changes illumination substantially; changing it by ~29.5 days gives broadly similar illumination.
- Monotonicity: a stricter `max_slope_deg` never increases the survival probability; a larger `max_dark_h` never decreases it.
- `delay_curve[0].survival_probability == summary.survival_probability`.
- Contract shape: every field in CONTRACT §4.3 present with the right type; array lengths (`timeseries.n = mission_days*24`, `horizon_profile` length = 360/step).

**5. Independent illumination comparison**
Compare our results with an independent source for 2–3 dates:
- **LROC Quickmap** (https://quickmap.lroc.asu.edu/), which can display illumination/shadows: compare which areas of the Site20 region are lit vs. in shadow at the same UTC time; save screenshots side by side with our map. And/or
- **Published average-illumination maps** (Mazarico et al. 2011, Icarus 211, "Illumination conditions of the lunar polar regions using LOLA topography", or PGDA illumination products) for the % of time lit at a few points.
Quantify agreement where possible; describe it qualitatively otherwise.

**6. API & UI robustness**
- Edge cases: target outside coverage (expect 400 `out_of_coverage` with `suggested_target`), date outside the ephemeris (400), tiny ellipse (50 m: falls back to on-the-fly points, warning present), huge ellipse (5 km: performance), mission 30 days, risk_margin 0, invalid inputs (422).
- Timing: 10 calls to the deployed API with varied inputs. Report p50/p95 (the target is < 3 s).
- UI: open the deployed site in a **private window** (no login), on desktop and a phone width. Check the SAMPLE DATA badge appears only with fixture data, tooltips work, no overlapping labels, all text in English, no NASA logos, links in the About modal work.

**7. Claims audit**
Read `README.md`, the About modal text and `docs/submission/*` (if present). Flag every factual claim that isn't supported by a cited source or by our own reproducible output, and every number that differs from the latest results.

### Deliverables
- `docs/validation.md`: summary table (check · result · pass/fail · evidence), the Athena case study (facts with sources, our runs, interpretation), ephemeris errors, illumination comparison with images, robustness and timing results, **known limitations** (horizon limited to the DEM extent, 5 m DEM misses boulders < ~5 m, uniform-ellipse assumption, 1 h time step, no thermal model, center-of-disk rule, tip-over not modeled beyond slope), and a "Safe claims for the pitch" section listing exactly which statements we can make and how to word them.
- `docs/validation/` images (screenshots, plots).
- `engine/tests/test_validation.py`.
- Issues: a prioritized list (P0 = wrong results / broken demo, P1 = misleading, P2 = polish) with the file and a suggested fix. **Do not refactor the engine yourself**; small test-only changes are fine. For P0 bugs, propose a minimal patch and explain it, but let the owner apply it.

### Rules
- Cite sources for every external fact; quotes < 15 words.
- Separate clearly what you **measured** from what you **infer**.
- If a check can't be run, say why. Never mark it as passed.
- Report to me in Spanish with the top 5 findings first.
