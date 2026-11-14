# LunaScout — Project Context (read before doing anything)

Background for every agent working on LunaScout. `CONTRACT.md` defines the interfaces; this file explains the **why**, the decisions already made and the facts already verified, so nobody re-litigates them.

## 1. Event & team
- **NASA Space Apps Challenge 2026**, Nov 14–15, 2026. **Submission deadline: Sunday Nov 15, 23:59 local time** (Uruguay, UTC−3). Resubmitting is allowed; only the last submission counts.
- Team: 4 Systems Engineering students from ORT Uruguay (Montevideo). We build with AI assistance (Claude); each person supervises one agent and must understand its output.
- Challenge: **"Lunar Landing Site Navigator"** (Advanced): https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/
- Judging criteria: **Impact, Creativity, Validity, Relevance, Presentation**. Most of the score comes from the project page; the demo (≤30 s video or ≤7 slides) mainly affects Presentation.

## 2. What the challenge asks (summary)
Build an intuitive tool so mission planners, educators and the public can quickly compare lunar landing sites and dates, visualizing **Sun and Earth positions relative to the horizon** to assess **solar power** and **direct-to-Earth communication**. Focus: the **lunar south pole**. The brief stresses:
- Missions slip (hardware, launch delays), so alternatives must be re-evaluated **fast**.
- Existing tools (Quickmap, Moon Trek, JPL Horizons) are powerful but hard to use for quick scenario comparison.
- Time remaining until sunset/Earthset.
- Real topography (LOLA); no atmosphere (no refraction); libration.
- Steep slopes and deep craters at the south pole; coordinating science and engineering teams; educational value.
- Resources given: JPL Horizons, LROC Quickmap, Moon Trek, CSA Moon Exploration.

## 3. Problems → our idea
Problems the team identified: **sunlight** (power), **temperature** (no sun means about −170 °C; electronics die without heater power), **communication** (direct-to-Earth, or relay), **terrain** (safe touchdown, and it blocks the Sun and Earth), **delays** (any engineering issue shifts the landing date).

**Key insight (the team's choice):** a lander never touches down exactly on its target. Near the south pole the Sun stays only a few degrees above the horizon, so **a few hundred meters can separate sunlight from deadly shadow**. Existing tools and most competitors evaluate a single exact point. LunaScout evaluates the **whole landing ellipse** and answers: *"What is the probability my mission survives where it will actually land?"*

**Real-world hook (verified, see §6):** IM-2 "Athena" (March 6, 2025) landed ~250 m from its target inside a shadowed crater near Mons Mouton, on its side; sunlight couldn't reach its solar cells and the mission ended in about 13 hours.

## 4. Product scope (MVP, decided)
**One single screen.** No multi-page app, no modes or tabs, nothing Athena-specific hard-coded: users enter any scenario manually (we'll reproduce Athena by typing its data).
- **Left:** settings: target lat/lon, landing date-time (UTC), mission duration, landing ellipse (semi-major, semi-minor, orientation), max darkness (battery h), max comms gap (h), min % time with Earth visible, max slope; Run analysis.
- **Center:** real Moon map (LOLA hillshade) centered on the target; ellipse with points colored **green viable / amber risky / red not viable** (with shapes ● ▲ ✕); target marker; legend. Below it, a **mission timeline chart**: Sun and Earth elevation vs. the terrain horizon over time.
- **Right:** survival probability, metric checks with PASS/FAIL, launch-delay tolerance, recommended nearby targets (click to re-run).
- **About & method** modal: problem, method, data, assumptions, AI-use statement.
- **Live computation:** changing coordinates, date or limits recomputes on the server (FastAPI). Target response < 3 s.

Requirements are tracked in a team spreadsheet (Problems → 26 needs N1–N26 → 46 functional requirements RF01–RF46, with MVP flags). The MVP covers: settings (RF01, RF03–RF08), sunlight (RF10–RF15), comms (RF20–RF23, RF25), terrain + ellipse probability (RF26–RF33), delays (RF36–RF38), viability classification (RF41), reproducing a real mission (RF43).

## 5. Technical decisions (already made, don't change without the team)
| Topic | Decision |
|---|---|
| Stack | Python engine (numpy, scipy, rasterio, pyproj) + FastAPI; frontend in plain HTML/CSS/JS + Chart.js; Canvas map |
| Hosting | Google Cloud Run (min 1 instance, no cold start), Firebase Hosting for the frontend with `/api/**` rewrites to Cloud Run; free custom domain (GoDaddy Registry offer via Porkbun); FortiGuard classification request |
| Region / DEM | **Mons Mouton**, PGDA LOLA 5 m/px **Site20 ("Leibnitz beta plateau")**, `Site20v2` if available |
| Ephemeris | Horizons queried once (2025–2028, hourly) at a reference site, stored as Moon-fixed (ME) unit vectors; per-point az/el computed geometrically. The app never calls Horizons live |
| Horizon | Great-circle ray marching on the DEM with exact spherical curvature, 1° azimuth bins; **precomputed grid every 50 m** (fallback 100 m) + on-the-fly for small ellipses and for the target |
| Time step | 1 hour |
| Lit rule | Sun center above the local terrain horizon at the Sun's azimuth; observer 2 m above the ground |
| Probability | Fraction of viable points, assuming a uniform landing distribution inside the ellipse (stated in the UI) |
| Classification | Exact rules in CONTRACT §4.4 (slope, darkness vs. battery, comms gap, Earth %, Sun at touchdown; risky = within the risk margin or a sunset during the mission) |
| Earth metric | **% of mission time with Earth visible** + **longest comms gap**. NOT "hours per day": at the pole, Earth is visible for ~2 weeks, then hidden for ~2 weeks (libration) |
| Colors | Sun yellow `#FFE066`, Earth blue `#8CC4FF`, viable `#3DDC84` ●, risky `#FF9F43` ▲, not viable `#FF6B6B` ✕ |
| Design | Reference mockup in `docs/design/Main.dc.html` (visual reference only; its data and logic are fake) |

## 6. Verified facts (use these; cite the sources)
- **Horizons works for lunar sites** with `CENTER='coord@301'`, `COORD_TYPE='GEODETIC'`, `SITE_COORD='lon,lat,alt_km'` (longitude first), `QUANTITIES='4'`. Header shows `Atmos refraction: NO (AIRLESS)` and `Center pole/equ: MEAN_ME`.
- **Shackleton** (lat −89.67, lon 129.78), 2027-01-01 00:00 UT: Sun az **133.339447°**, el **0.787435°**. In January 2027 at Shackleton (flat horizon): Sun between ~0° and ~1.2°; Earth oscillates between about −7° and +6° (~27-day cycle) and is visible only ~Jan 11–23.
- **Max Sun elevation** at latitude φ ≈ (90 − |φ|) + 1.54° (lunar axial tilt ~1.54°).
- **Athena (IM-2):** landed March 6, 2025 (~12:30 p.m. EST), 250 m from its intended site in the Mons Mouton region, inside a crater, on its side; mission ended ~13 h after landing; NASA said "more than 400 m" from target. Sources: https://spacepolicyonline.com/news/im-2-mission-ends-one-day-after-lunar-landing/ , https://www.collectspace.com/news/news-030625a-intuitivie-machines-im2-athena-moon-landing.html. Its **exact coordinates are not yet verified**, and it's **not yet confirmed that Site20 covers the Athena site**: the validation agent must check.
- **JAXA SLIM** (Jan 2024) landed upside down and regained power ~9 days later when the Sun angle changed (Scientific American, Jan 29, 2024). Possible extra replay case.
- **PGDA LOLA DEMs:** 5 m/px GeoTIFFs, south polar stereographic meters, MOON_ME (DE421); per site: `_surf.tif`, `_slp.tif`, `_toterr.tif`, 100 clones. Sites include Connecting Ridge (Site01), Shackleton Rim (Site04), Nobile Rim 1 (Site06), Peak near Shackleton (Site07), de Gerlache Rim (Site11), **Leibnitz beta plateau (Site20)**, Malapert Massif (Site23). Height RMS error ~0.3–0.5 m. https://pgda.gsfc.nasa.gov/products/78

## 7. Known limitations (be honest about them everywhere)
- Horizon only as far as the DEM extent (~16 km tile): distant peaks are missed. State it as a warning.
- 5 m DEM misses boulders smaller than ~5 m, so tip-over risk is captured only through slope.
- No thermal model (darkness duration is the proxy for cold).
- Uniform landing distribution; 1 h time step; center-of-disk sunlight rule.
- Relay satellites, descent lighting for navigation, launch-window orbital constraints and eclipses are **out of MVP scope** (mention them as future work).

## 8. Space Apps rules that affect everyone
- **All submitted content in English** (the video may be Spanish with English subtitles).
- **Disclose AI use:** header comment in every AI-assisted code file (CONTRACT §7), a "Use of AI" README section, watermarks on AI-generated images/video. AI must not be what came up with the idea; the team owns the concept and must be able to explain everything.
- No NASA logos, insignia or mission patches; no images, video or voice of anyone under 18.
- Use and declare NASA data (Horizons, LOLA/PGDA). List all libraries and sources.
- Public links with no login. Demo ≤ 30 s video or ≤ 7 slides, or the project is not eligible for global judging.
- **Never present sample or made-up data as real.** Sample data is always labeled.

## 9. Where things live
- `CONTRACT.md`: interfaces (binding)
- `CONTEXT.md`: this file
- `docs/design/`: UI mockup (reference)
- `scripts/horizons_test.py`: first working Horizons query + plot (Shackleton, Jan 2027)
- Team prompts for each agent: `../prompts/` (outside the repo)
