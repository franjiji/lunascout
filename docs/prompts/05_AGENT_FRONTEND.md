# Agent 05 — Frontend (single-screen web app)

**Recommended model:** Claude Sonnet 5.5 (switch to Claude Opus 5.5 if the map gets stuck) · **Effort:** high
**Attach:** `01_CONTRACT.md` **and** the design reference folder `LunaScout — Landing-site checker-html/` (file `Main.dc.html`). Give the agent access to the repo folder `lunascout/`.
**Supervisor:** Person C

---

## Prompt (copy everything below this line)

You are the frontend developer on a 4-person team at the NASA Space Apps Challenge 2026 (48-hour hackathon; final deadline Sunday Nov 15 23:59; the UI must be demo-ready by **Sunday 14:00**). Our project, **LunaScout**, is a single-screen web app for lunar south pole landing planning. A lander never touches down exactly on its target, so LunaScout shows the **whole landing ellipse** on a real map of the Moon, colors each sample point viable / risky / not viable using real NASA data (LOLA topography + JPL Horizons), and gives a survival probability, key metrics and better nearby targets. The audience: mission planners first, but also educators and the curious public, so it must be **precise and also understandable at a glance**. It also has to **sell our idea** in a 30-second demo video.

The attached `CONTRACT.md` defines the API you consume (`GET /api/meta`, `POST /api/analyze`) and the response shape. The attached `Main.dc.html` is a **design mockup** from our design tool: treat it as the visual reference (layout, colors, typography, spacing), **not** as code to copy. Its data and logic are fake. Reply to me in Spanish; all UI text, code and comments in English.

### Tech
- **Plain HTML + CSS + JavaScript (ES modules)** in `web/`: `index.html`, `styles.css`, `app.js` (split into modules if it helps: `api.js`, `map.js`, `chart.js`, `ui.js`). No build step required. If you want Vite, it must still output static files to `web/dist`, but plain files are preferred.
- **Chart.js** (via a pinned CDN URL, or vendored in `web/vendor/`) for the mission time-series chart. **No other dependencies** unless strictly needed.
- The map is drawn on an **HTML Canvas** (or SVG): hillshade image + points + ellipse + target + grid + scale bar.
- API base URL: `const API_BASE = window.LUNASCOUT_API ?? "/api";` (same origin in production via Firebase rewrites; `http://localhost:8000/api` in dev via a `config.js` override).

### Layout (single screen, desktop-first 1440 px; must not break at 1280 px; stack vertically on mobile)
Follow `Main.dc.html`: header · left settings panel · center map · right results + recommendations · footer.

**Header:** "LUNASCOUT" wordmark, subtitle "Landing-site checker · Lunar south pole", last-run time, and an "About & method" button that opens a modal (see below). Show the badge "SAMPLE DATA — API OFFLINE" **only** when the data comes from the fixture.

**Left panel: Mission settings** (fields → request JSON per the contract)
- Target latitude (°), Target longitude (°E) → `target.lat/lon`
- Landing date & time (UTC) → `landing_utc` (use `datetime-local` and convert to ISO `Z`; label "UTC" clearly)
- Mission duration (days) → `mission_days`
- Landing ellipse: semi-major (m), semi-minor (m), orientation (° from north) → `ellipse.*` (default semi-minor = 0.6 × semi-major; a "lock ratio" toggle is optional)
- Max tolerable darkness (battery hours) → `limits.max_dark_h`
- Max comms gap (hours) → `limits.max_comm_gap_h`
- Min mission time with Earth visible (%) → `limits.min_earth_pct`
- Max safe slope (°) → `limits.max_slope_deg`
- "Advanced" collapsible: risk margin (%) → `options.risk_margin`; delay range (days) → `options.delay_days_max`; observer height (m) → `options.observer_height_m`
- A "Curated sites" dropdown filled from `/api/meta.curated_sites` (fills lat/lon)
- **Run analysis** button. When inputs change after a run, show "Settings changed — run to update" (as in the mockup). Validate ranges from `/api/meta.input_limits` before sending, with inline messages.
- Defaults come from `/api/meta.defaults`.

**Center: map**
- Title: the target name if it matches a curated site, else "Custom target", then coordinates + landing time.
- Canvas: draw `hillshade_url` positioned by `hillshade_bounds_xy_m`, viewport = `view_bounds_xy_m`. World xy (m) → canvas px with a uniform scale; **y goes up in map space**, so flip for canvas.
- Draw the 1 km grid with labels (−2 km … +2 km relative to the target), the scale bar, the ellipse outline (`ellipse_polygon_xy_m`, dashed), the target crosshair, and each point by class: **viable = green circle**, **risky = amber triangle**, **not viable = red ✕**. Shape plus color, so it is never color alone.
- Hover a point → tooltip: class, reasons in plain words (e.g., "Too steep (9.2° > 8°)", "Dark for 63 h, battery lasts 50 h"), and its metrics. Click → pin the tooltip.
- Small overlay (top-left): Sun az/el and Earth az/el **at touchdown** for the target (from `timeseries[0]`).
- **Fix these issues from the design review:** the "TARGET" label must not cover points (offset it with a leader line, or show it on hover); overlays must not overlap the grid labels or the scale bar; keep a consistent margin.
- Legend under the map: Viable · Risky · Not viable · Landing ellipse · Target, plus the line "Assumes the lander is equally likely to land anywhere inside the ellipse."
- Keyboard: arrow keys pan, +/− zoom, `0` reset view (nice-to-have: mouse wheel zoom + drag pan).

**Below the map (use the empty space the mockup left): Mission timeline chart** (Chart.js, target point)
- X: hours since touchdown (label days). Y: elevation (°).
- Lines: Sun elevation (gold), Earth elevation (blue), "terrain horizon toward the Sun" (gray filled area below it) and "terrain horizon toward Earth" (dashed gray).
- Shade the intervals where `sun_lit` = 0 (dark) and mark where `earth_visible` = 0. Vertical marker at the first sunset.
- Caption (plain language): "The Sun barely rises here: a small hill can block it. When the gold line drops below the gray area, the lander is in shadow."

**Right panel: results**
- **Survival probability**, big number (`summary.survival_probability` as %), subtitle "of landing points inside the ellipse are viable", a stacked bar viable / risky / not viable with counts, and "Including risky points: X%". Verdict chip for the target (viable / risky / not viable).
- **Metrics list** from `target_metrics` (render exactly what the API sends, in order): label, big value (`display`), limit line (`limit_display`), PASS / FAIL badge (✓ / ✕); `pass: null` → neutral "INFO" badge. Footer: "N of M checks pass against your settings."
- **Delay tolerance:** the `delay_tolerance` metric plus a small sparkline of `delay_curve` (survival vs. days of delay), with the caption "Launch slipped? See how long this target stays viable."
- **Recommended nearby:** cards from `recommendations` (probability, name, coordinates, distance, "+N pts"). Click → set lat/lon, run the analysis, recenter. If empty: "No better target found within 3 km."
- Every metric has an ⓘ tooltip in plain language, for the educators/public audience (e.g., "Longest darkness period: the longest stretch without sunlight. Solar-powered landers must survive it on batteries.").

**Footer:** data sources from `response.sources` (JPL Horizons; LRO LOLA via NASA GSFC PGDA) + "LunaScout — NASA Space Apps Challenge 2026".

**About & method modal** (important for the judges): the problem (Athena, ~250 m off target, shadowed crater, mission ended in ~13 h), how LunaScout works (5 short steps: DEM → horizon mask per point → Sun/Earth from Horizons → hourly simulation → classification), the data sources with links, the key assumptions and limitations (from `warnings` + the uniform-ellipse assumption + horizon limited to the DEM extent), and an **"Use of AI" statement**: "Parts of this software were developed with assistance from Claude (Anthropic). The concept, requirements and validation are the team's work." The team will confirm the final wording.

### Visual style (from the mockup; extract exact values from its inline styles)
- Dark, high contrast, "mission control" but clean. Use the mockup's fonts (**Barlow** and **Barlow Semi Condensed** from Google Fonts, system sans-serif fallback; a monospace for numbers) and its palette and spacing: background `#0a0a0a`/`#141416`, borders `#3a3a3f`, secondary text `#a0a0a8`, primary text `#ffffff`/`#f0f0fa`.
- **Fixed semantic colors** (Sun and "risky" must not look alike):
  - Sun = yellow `#FFE066`
  - Earth = blue `#8CC4FF`
  - Viable = green `#3DDC84` + ●
  - Risky = orange `#FF9F43` + ▲
  - Not viable = red `#FF6B6B` + ✕

  Check WCAG AA contrast for all text.
- No NASA logos, insignia or mission patches anywhere.

### States & robustness
- Loading: disable Run, show "Analyzing…" with a subtle progress indicator on the map; keep the previous result dimmed.
- API error 400 `out_of_coverage`: friendly message plus a button "Go to suggested target" (uses `suggested_target`). 422: highlight the offending field. 500 / network: toast + offer "Load sample result".
- **Offline fallback:** if `/api/meta` fails on load, use built-in defaults + `fixtures/sample_response.json` (copy it to `web/fixtures/`) and show the SAMPLE DATA badge. Never show fixture data without that badge.
- Remember the last inputs in `localStorage` (wrapped in try/catch).
- Performance: smooth on a mid-range laptop; redraw the canvas only on data or view change.

### Accessibility
Semantic HTML, labels on all inputs, focus states, keyboard-reachable controls, `aria-live` for the results update, tooltips also reachable by focus, and color never the only signal.

### Deliverables
- `web/index.html`, `web/styles.css`, `web/app.js` (+ modules), `web/config.js`, `web/fixtures/sample_response.json`, `web/vendor/` if used
- `web/README.md`: how to run locally (`python -m http.server` in `web/` + API on :8000), how to point to production
- Screenshots `docs/ui-desktop.png` and `docs/ui-mobile.png` (with real API data if available)

### Rules
- Every code file starts with the AI-use header (CONTRACT §7).
- Only render what the API returns. **Never hard-code or invent numbers.** Labels can be static; values can't.
- Don't change the contract; if you need a field that's missing, tell me in Spanish and propose it.
- Start against the fixture immediately (the API agent is building a stub). Switch to the live API when Person B says Phase 1 is up.
- Report to me in Spanish when it works with the fixture, and again with the live API (include screenshots).
