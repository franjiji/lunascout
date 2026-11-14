# Agent 02 — Ephemeris (JPL Horizons)

**Recommended model:** Claude Sonnet 5.5 · **Effort:** medium
**Attach:** `01_CONTRACT.md`. Give the agent access to the repo folder `lunascout/`.
**Supervisor:** Person B

---

## Prompt (copy everything below this line)

You are a scientific Python developer on a 4-person team at the NASA Space Apps Challenge 2026 (48-hour hackathon, deadline Sunday Nov 15 23:59). Our project, **LunaScout**, evaluates lunar south pole landing ellipses using real JPL Horizons ephemerides and real LOLA topography. The attached `CONTRACT.md` is the binding interface between all parts. Follow it exactly. Reply to me in Spanish; write all code, comments and docs in English.

### Your job
Produce a **precomputed, verified table of Sun and Earth directions in the Moon's body-fixed ME frame**, hourly from **2025-01-01T00:00Z to 2028-12-31T23:00Z**, plus the Python module `engine/ephemeris.py` that the terrain engine uses to get the Sun and Earth azimuth/elevation from **any point** in the south polar region at any hour. The app must never call Horizons during a user request: everything comes from your file, which keeps the demo fast and independent of Horizons' availability.

### Why this approach works (read carefully)
Horizons gives topocentric azimuth/elevation for one lunar surface site. Sun and Earth are so far away that their direction **in the Moon-fixed frame** is the same for every point within ~100 km (Earth parallax over 10 km ≈ 0.0015°). So:
1. Query Horizons once, for a **reference site** in the region.
2. Convert each az/el to a unit vector in the Moon ME frame using the reference site's local East-North-Up (ENU) basis.
3. For any other point, convert that vector back to that point's own ENU → its own az/el. This captures the ~0.33° elevation change per 10 km of latitude, which matters a lot here because the Sun is only ~1–7° above the horizon.

Horizons topocentric output for a lunar site uses the **MEAN_ME** pole/equator (it says so in the header), the same frame as the LOLA DEMs. Refraction is off (airless). Light-time and aberration corrections are included.

### Steps

**1. `scripts/fetch_ephemeris.py`**
- Endpoint: `https://ssd.jpl.nasa.gov/api/horizons.api`. Parameters (strings with single quotes, exactly like this; already verified working):
  ```
  format=text  COMMAND='10' (Sun) / '399' (Earth)
  CENTER='coord@301'  COORD_TYPE='GEODETIC'  SITE_COORD='<lon_east>,<lat>,0'   ← LONGITUDE FIRST
  MAKE_EPHEM='YES'  EPHEM_TYPE='OBSERVER'  QUANTITIES='4'
  START_TIME='YYYY-MM-DD'  STOP_TIME='YYYY-MM-DD'  STEP_SIZE='1h'
  CSV_FORMAT='YES'  ANG_FORMAT='DEG'
  ```
- **Reference site:** default to the center of the Site20 DEM (Mons Mouton). If the terrain agent hasn't provided it yet, use a CLI argument `--ref-lat --ref-lon` and ask Person B for the DEM center. Any reference within ~100 km of the analysis area is acceptable (verify in step 4).
- Request in chunks (e.g., 3 months per call) to stay under Horizons' output limits. Be polite: sequential requests, a small sleep between calls, and retries with backoff on HTTP errors.
- Parse only the lines between `$$SOE` and `$$EOE`. With `CSV_FORMAT='YES'` each line is comma-separated: date/time, solar-presence flag, interfering-body flag, azimuth, elevation (check the actual column order in the header and parse by position defensively). Assert there are no missing hours and timestamps are strictly increasing.
- Cache raw responses in `data/ephemeris/raw/` so re-runs don't hit the API.

**2. Conversion to Moon-fixed vectors**
For a site at latitude φ, longitude λ (east-positive), with azimuth `A` (clockwise from north) and elevation `h`:
```
e = cos(h)·sin(A)     n = cos(h)·cos(A)     u = sin(h)
X = -sin(λ)·e - sin(φ)·cos(λ)·n + cos(φ)·cos(λ)·u
Y =  cos(λ)·e - sin(φ)·sin(λ)·n + cos(φ)·sin(λ)·u
Z =               cos(φ)·n       + sin(φ)·u
```
Normalize. Inverse for any point (φ', λ'): `e = -sin λ'·X + cos λ'·Y`, `n = -sin φ'·cos λ'·X - sin φ'·sin λ'·Y + cos φ'·Z`, `u = cos φ'·cos λ'·X + cos φ'·sin λ'·Y + sin φ'·Z`; then `el = asin(u)`, `az = atan2(e, n) mod 360`.

**3. Output file `data/ephemeris/sun_earth_vectors.npz`**
Arrays: `t_unix` (int64, hourly UTC seconds), `sun_vec` (N×3 float64), `earth_vec` (N×3 float64). Metadata as 0-d string arrays: `ref_lat`, `ref_lon`, `frame="MOON_ME (Horizons MEAN_ME)"`, `source="JPL Horizons API, DE441"`, `created_utc`, `step="1h"`. Expected N = 35,064.

**4. `engine/ephemeris.py`** exactly as in CONTRACT section 5:
- `load_ephemeris(path)` → `Ephemeris` with `t_unix`, `sun_vec`, `earth_vec`.
- `Ephemeris.window(start_utc, hours)` → hourly slice starting at the hour of `start_utc` (round down). Raise `ValueError` if out of range.
- `local_az_el(vecs, lat_deg, lon_deg)` → `(az, el)` of shape (P, T), fully vectorized with numpy (no Python loops over points or times). It must handle P ≈ 1,000 points × T ≈ 1,000 hours in well under 1 s.
- Optional helper `sun_disk_visible_fraction(sun_el, horizon_el)`: the fraction of a 0.2665°-radius disk above a flat local horizon line; linear approximation is fine.

**5. Verification (mandatory; put it in `engine/tests/test_ephemeris.py` with pytest)**
- **Known value:** reference test from a real Horizons query. Shackleton (lat -89.67, lon 129.78), `2027-01-01 00:00 UT` → Sun az 133.339447°, el 0.787435°. Query Horizons directly for that site (in the test setup, cached), then reproduce it via your vector table (reference site elsewhere) + `local_az_el`. Tolerance: **Sun ≤ 0.01°**, **Earth ≤ 0.05°** in both az and el. If Shackleton is too far from your reference for that tolerance, also test a point ~10–20 km from the reference and report the error vs. distance.
- **Round trip:** az/el → vector → az/el at the same site, error < 1e-9°.
- **Physics sanity:** at latitude φ (south), the Sun's maximum elevation over a year must be ≈ (90 − |φ|) + 1.54° (lunar axial tilt). Check for the reference site and report.
- **Earth libration sanity:** at the reference site, Earth's elevation must oscillate with a ~27.3-day period (libration in latitude, amplitude ≈ 6.7°) and drift only slowly in azimuth, never circling the sky. Report the period you measure and plot it.

**6. Diagnostics** — save `docs/ephemeris_check.png`: Sun and Earth elevation at the reference site for 2027-01 to 2027-03, plus the Shackleton 2027-01 curve (it should match our earlier plot: Sun ≈ 0.8–1.2°, Earth −7° to +6°, Earth visible ≈ Jan 11–23).

### Deliverables
1. `scripts/fetch_ephemeris.py` (CLI: `--start --end --ref-lat --ref-lon --out`)
2. `data/ephemeris/sun_earth_vectors.npz` (commit it if < 50 MB; it should be ~2 MB)
3. `engine/ephemeris.py`, `engine/tests/test_ephemeris.py` (all passing)
4. `docs/ephemeris_check.png`
5. `engine/EPHEMERIS.md`: method, frame, verification results (numbers), limitations

### Rules
- Every code file starts with the AI-use header from CONTRACT section 7.
- No fabricated numbers: every value comes from Horizons or your computation. If something can't be verified, say so.
- Do not change the contract. If you think it's wrong, explain why to me in Spanish and propose the change.
- Dependencies: `numpy`, `requests`, `pytest`, `matplotlib` only. Python 3.11+.
- When done, give me a short report in Spanish: what you produced, the verification numbers, and anything the terrain agent must know.
