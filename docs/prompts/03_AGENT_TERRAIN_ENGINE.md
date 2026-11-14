# Agent 03 — Terrain engine & analysis (the core)

**Recommended model:** Claude Fable 5.2 (alternative: Claude Opus 5.5) · **Effort:** high
**Attach:** `01_CONTRACT.md`. Give the agent access to the repo folder `lunascout/`.
**Supervisor:** Person A. You must understand the algorithm well enough to explain it to the judges.

---

## Prompt (copy everything below this line)

You are the lead scientific developer on a 4-person team at the NASA Space Apps Challenge 2026 (48-hour hackathon; final deadline Sunday Nov 15 23:59, **a working `analyze()` is needed by Sunday 11:00**). Our project, **LunaScout**, answers: *"Given where my lander is aimed, and that it will land somewhere inside its landing ellipse, what is the probability my mission survives?"* Survival depends on sunlight (power and heat), direct-to-Earth visibility (comms) and slope (safe touchdown). Near the lunar south pole the Sun stays a few degrees above the horizon at most, so terrain a few hundred meters away decides between light and deadly shadow. Example: in March 2025 the IM-2 "Athena" lander came down ~250 m from its target inside a shadowed crater (it also tipped over), and its mission ended in about 13 hours.

The attached `CONTRACT.md` is binding: conventions, API request/response, classification rules and the Python interface you must expose. Reply to me in Spanish; write all code, comments and docs in English.

### Inputs you have
- **DEM:** LOLA 5 m/px site DEMs from NASA GSFC PGDA (Barker et al. 2021): `https://pgda.gsfc.nasa.gov/products/78`, files under `https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/`. **Use Site20 ("Leibnitz beta plateau" = Mons Mouton); prefer `Site20v2` if listed.** Download `*_surf.tif` (height in m relative to the 1,737,400 m sphere) and `*_slp.tif` (slope, degrees). Optionally `*_toterr.tif`. Put them in `data/raw/` (git-ignored). Read the exact file names from the directory listing; don't guess.
- **Ephemeris:** `engine/ephemeris.py` + `data/ephemeris/sun_earth_vectors.npz` from Agent 02 (interface in CONTRACT §5). Until it lands, write against the interface and use a temporary stub that queries nothing (e.g., a synthetic Sun circling at 1.5° elevation, Earth oscillating ±7°) **only for tests**, clearly named `_stub`.

### What you must build

**1. `engine/geo.py`: coordinates**
- Read the CRS from the GeoTIFF with `rasterio` and build `pyproj` transformers xy ↔ lat/lon. If the file's CRS is missing or ambiguous, use `+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +R=1737400 +units=m +no_defs` **and verify** with a known point (e.g., check that the DEM center maps to a sensible Mons Mouton latitude around −84° to −85°, and cross-check one feature against LROC Quickmap).
- Helpers: `latlon_to_xy`, `xy_to_latlon`, `to_cartesian(lat, lon, height_m)` (Moon ME, R = 1,737,400 m), `destination(lat, lon, azimuth_deg, distance_m)` (spherical great-circle, vectorized).

**2. `engine/terrain.py`: DEM access**
- Load `surf` and `slp` once (singleton), as float32 arrays plus the affine transform. Handle nodata as NaN.
- `height_at(x, y)` and `slope_at(x, y)`: vectorized bilinear interpolation (`scipy.ndimage.map_coordinates`, order=1), NaN outside the grid.
- `in_coverage(x, y, margin_m)`.
- `make_hillshade(out_png, max_px=2048)`: downsample, hillshade (sun azimuth ~315° in map space, altitude 45°), grayscale PNG. Return the bounds in xy meters (needed by `/api/meta` and the frontend map).

**3. `engine/horizon.py`: horizon mask (the critical algorithm)**
For an observer at (lat0, lon0) standing `observer_height_m` above the terrain, for each azimuth α in 0..359° (step 1°):
- March along the great circle in direction α over distances `s` from 10 m to the DEM edge, with **geometric spacing** (≈ 300–500 samples, dense near the observer, sparse far away). Use `geo.destination` → xy → `terrain.height_at` (vectorized over all azimuths × samples at once).
- Elevation angle of each sample, with exact spherical curvature:
  `θ = atan2( (R+z)·cos(s/R) − (R+z0+h_obs), (R+z)·sin(s/R) )`, with R = 1,737,400 m.
- Horizon elevation at α = max θ over the samples that are inside the DEM. Track `max_reached_distance` per azimuth: if the ray exits the DEM before 10 km, that azimuth's horizon is **underestimated** (distant peaks missing). Report it and put a warning in the analysis response (CONTRACT `warnings`).
- Performance target: **one observer in < 30 ms** with numpy (all 360 azimuths × samples as one array op).
- Tests (`engine/tests/test_horizon.py`):
  - On a **synthetic flat sphere** DEM (all heights 0) the horizon must be ≈ −acos(R/(R+h_obs)) in degrees (≈ −0.087° for h = 2 m).
  - On a **synthetic wall** of height H at distance D, the horizon toward the wall must be ≈ atan2(H − h_obs − D²/(2R), D).
  - Symmetry test: a radially symmetric crater gives an azimuth-independent horizon at its center.

**4. Precomputed horizon grid: `scripts/precompute_horizons.py`** (run it Saturday night)
- Regular grid over the DEM (excluding a margin of ~1 km), **spacing 50 m** if compute allows (target < 2 h on a laptop using `multiprocessing`). Otherwise 100 m, and document the choice.
- For each node store: horizon elevations for 360 azimuths (float16, degrees), `max_reached_distance` per azimuth (uint16 in units of 10 m or float16 km), `height_m`, `slope_deg`, `lat`, `lon`.
- Save as `data/derived/horizon_grid.npz` (or chunked `.npy` + `meta.json`). Check the size: it must load in the API server's 2 GB RAM. Grids of 50 m over ~14 × 14 km ≈ 78k nodes × 360 × 2 bytes ≈ 56 MB. Fine.
- Resumable (process in tiles, skip tiles already done) and with a progress bar.

**5. `engine/analyze.py`: the analysis (CONTRACT §4.3–4.4 exactly)**
`analyze(request: dict) -> dict` and `get_meta() -> dict`.
1. **Validate & normalize** inputs (defaults from CONTRACT `/api/meta`). Coverage check: target inside the grid area and ≥ 80% of the ellipse inside, otherwise raise `EngineError("out_of_coverage", ...)` with `suggested_target` = DEM center. Ephemeris range check → `out_of_ephemeris_range`.
2. **Sample points:** grid nodes inside the ellipse (semi-axes `a`, `b`, rotated by `azimuth_deg` relative to local north at the target; note that local north in the stereographic plane points away from the pole, so compute the rotation from the actual north direction at the target, not the map's y-axis). If fewer than 40 nodes fall inside (small ellipse), compute horizons **on the fly** for a hex grid of ~60–120 points inside the ellipse with `horizon.py`. Cap at ~400 points by subsampling uniformly.
3. **Sun/Earth per point and hour:** `ephemeris.window(landing, hours)` with `hours = (mission_days + delay_days_max) * 24`. Then `local_az_el` for all points → arrays (P, T). Horizon elevation at the body's azimuth by **linear interpolation** between the 1° bins (with wrap-around). `sun_lit = sun_el > horizon_at_sun`, `earth_visible = earth_el > horizon_at_earth`.
4. **Per-point metrics** over the mission window `[0, mission_hours)`: `sun_hours`, `longest_dark_h` (longest run of `~sun_lit`, including a run starting at hour 0), `earth_pct`, `longest_comm_gap_h`, `hours_until_sunset` (first hour where lit→unlit; `mission_hours` if never), `sun_at_touchdown`, `slope_deg`. Vectorize run-length computations with numpy, with no Python loops over hours.
5. **Classify** with the exact rules of CONTRACT §4.4 and fill `reasons`.
6. **Summary**, **target_metrics** (exact ids, labels and pass semantics from the contract; `display` strings formatted like `"3 d 6 h"`), **timeseries** and **horizon_profile** for the target point (compute the target's horizon on the fly so it's exact, not snapped to the grid).
7. **Delay curve:** for d = 0..`delay_days_max`, shift the window start by `24·d` hours (reuse the same (P, T) arrays; just slice), reclassify, and record the survival probability and whether the target is viable or risky. Compute `delay_tolerance_days` per the contract.
8. **Recommendations** (if enabled): candidate targets on rings at 1, 2 and 3 km × 8 bearings (N, NE, …), plus `curated_sites` inside coverage. Evaluate each with a **coarser sampling** (every 2nd grid node, max ~60 points, no delay curve) and return the top 3 that beat the current survival probability, with names like `"2.0 km NE of target"`.
9. **Map block:** `hillshade_url`, `hillshade_bounds_xy_m`, a target-centered `view_bounds_xy_m` (≥ 5 km wide, 3:2, enlarged to fit the ellipse with margin), and `ellipse_polygon_xy_m` (72 vertices).
10. `warnings` (DEM edge, small ellipse fallback, any assumption) and `sources`.
11. **Performance:** default request < 3 s with recommendations on a 2-vCPU server. Profile it and report the timings. An LRU cache on normalized requests is welcome (the API may also cache).

**6. `get_meta()`:** fill CONTRACT §4.2 from the real DEM and ephemeris (coverage bounds, center lat/lon, ephemeris range, hillshade bounds). `curated_sites` = the DEM center plus 3–5 distinctive spots you identify in the terrain (e.g., the plateau top, a rim, a crater floor), named descriptively, e.g. "Mons Mouton plateau (high, flat)". **Do not invent official names.**

**7. Uncertainty (stretch goal, only if everything above works by Sunday 10:00):** use 10–20 of the PGDA DEM clones to recompute the target's horizon and report the spread of `sun_hours` as an extra warning or metric. Do not block the MVP on this.

### Engineering requirements
- Python 3.11+, deps: `numpy`, `scipy`, `rasterio`, `pyproj`, `Pillow`, `pytest` (+ `tqdm` optional). Pin versions in `engine/requirements.txt`.
- No Python loops over (points × hours) or (azimuths × samples). Vectorize.
- `engine/errors.py`: `class EngineError(Exception): code, message, extra`.
- Every code file starts with the AI-use header (CONTRACT §7).
- Also write `fixtures/sample_response.json` from a **real** `analyze()` run of the defaults (set `"is_sample": true` in the fixture copy, since the frontend uses it offline). Replace the placeholder fixture the other agents may have made.
- `engine/ENGINE.md`: the algorithm explained in plain English with one diagram (ASCII is fine), every assumption (uniform landing distribution, 2 m observer, 1 h step, horizon limited to the DEM extent, center-of-disk rule), test results, and the timings.

### Definition of done
- `pytest` passes (horizon synthetic tests, metrics on synthetic series, contract-shape test validating `analyze()` output keys and types).
- `python -c "from engine.analyze import analyze, get_meta; ..."` runs the default request in < 3 s locally and produces sensible results. Sanity checks: the maximum Sun elevation at the site never exceeds (90 − |lat|) + 1.54° + the local terrain effect; plateau tops have more sunlight than crater floors; changing the date shifts the results.
- Report to me in Spanish: what works, the timings, the grid spacing used, known limitations, and the 3 most interesting findings for the pitch (e.g., "within a 1 km ellipse, sunlight varies from X h to Y h").
