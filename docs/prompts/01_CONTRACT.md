# LunaScout — Shared Contract (v1.0)

This file is the single source of truth that connects all parts of LunaScout. Every agent must follow it exactly. If a change is unavoidable, bump `schema_version`, update this file, and tell the whole team.

## 1. Product in one paragraph
LunaScout is a single-screen web app for the lunar south pole. A lander never touches down exactly on its target, so the user enters a target, a landing date, a mission duration, a landing ellipse and mission limits. The backend evaluates every sample point inside the ellipse using **real LOLA topography** (horizon mask + slope) and **real JPL Horizons ephemerides** (Sun and Earth positions). It returns each point as viable / risky / not viable, a survival probability, target-point metrics, a time series of Sun/Earth elevation vs. the local horizon, a launch-delay tolerance curve, and better nearby targets.

## 2. Conventions (non-negotiable)
| Topic | Convention |
|---|---|
| Latitude | Degrees, south negative (`-84.6`) |
| Longitude | Degrees **east-positive**, range [-180, 180] |
| Time | UTC, ISO 8601 with `Z` (`2027-03-10T14:00:00Z`). Internal sampling step: **1 hour** |
| Azimuth | Degrees, **clockwise from local north**, [0, 360) |
| Elevation | Degrees above the local horizontal plane (plane perpendicular to the local radius of the reference sphere) |
| Distances / heights | Meters. Heights are relative to the **1,737,400 m reference sphere** (LOLA convention) |
| Map coordinates | South polar stereographic, meters, read from the DEM GeoTIFF's own CRS (spherical Moon, R = 1,737,400 m). Named `x_m`, `y_m` |
| Body-fixed frame | Moon **Mean Earth / polar axis (ME)** frame, which both Horizons topocentric output and the PGDA DEMs use |
| Moon radius | `R_MOON = 1737400.0` m |
| "Sun lit" | Sun center elevation > local terrain horizon elevation at the Sun's azimuth. Also compute `sun_visible_fraction` of the solar disk (angular radius 0.2665°) for display, but classification uses the center rule |
| "Earth visible" | Earth center elevation > local terrain horizon elevation at Earth's azimuth |
| Observer height | Default 2.0 m above the terrain (solar array / antenna height) |
| Rounding in JSON | Angles 3 decimals, hours 1 decimal, probabilities 3 decimals (0–1), coordinates 5 decimals |

## 3. Data sources
- **JPL Horizons API** — `https://ssd.jpl.nasa.gov/api/horizons.api`. Topocentric az/el from a lunar site works with: `CENTER='coord@301'`, `COORD_TYPE='GEODETIC'`, `SITE_COORD='<lon_east>,<lat>,<alt_km>'` (**longitude first**), `QUANTITIES='4'`, `EPHEM_TYPE='OBSERVER'`, targets `'10'` (Sun) and `'399'` (Earth). The output header states `Atmos refraction: NO (AIRLESS)` and `Center pole/equ: MEAN_ME`.
  - Verified example: Shackleton (lat -89.67, lon 129.78), `2027-01-01 00:00 UT` → Sun az 133.339447°, el 0.787435°.
- **LOLA 5 m/px south pole site DEMs** (Barker et al. 2021, NASA GSFC PGDA): `https://pgda.gsfc.nasa.gov/products/78`, data in `https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/`. Per site: `*_surf.tif` (height, m), `*_slp.tif` (slope, °), `*_toterr.tif` (height RMS error, m), `Clones/` (100 DEM realizations). GeoTIFFs in south polar stereographic meters. **Primary site: Site20 "Leibnitz beta plateau" = Mons Mouton** (use `Site20v2` if available). Citation: Barker, M. K., et al. (2021), *Planetary and Space Science* 203, 105119, doi:10.1016/j.pss.2020.105119.

## 4. API

Base path: `/api`. JSON only. CORS enabled for the frontend origin(s) and `http://localhost:*`.

### 4.1 `GET /api/health`
`200 {"status":"ok","engine_ready":true,"schema_version":"1.0"}`

### 4.2 `GET /api/meta`
Lets the frontend set defaults, limits and the map.
```json
{
  "schema_version": "1.0",
  "coverage": {
    "dem_name": "LOLA 5 m/px LDEM — Site20 (Mons Mouton)",
    "bounds_xy_m": [-0.0, -0.0, 0.0, 0.0],
    "center_lat": 0.0,
    "center_lon": 0.0,
    "approx_bounds_latlon": {"lat_min": 0.0, "lat_max": 0.0, "lon_min": 0.0, "lon_max": 0.0}
  },
  "ephemeris_range_utc": ["2025-01-01T00:00:00Z", "2028-12-31T23:00:00Z"],
  "map": {
    "hillshade_url": "/api/static/hillshade.png",
    "hillshade_bounds_xy_m": [0.0, 0.0, 0.0, 0.0],
    "crs_proj4": "+proj=stere +lat_0=-90 ... +R=1737400 +units=m"
  },
  "curated_sites": [
    {"id": "mons_mouton_center", "name": "Mons Mouton (DEM center)", "lat": 0.0, "lon": 0.0}
  ],
  "defaults": {
    "landing_utc": "2027-03-10T14:00:00Z",
    "mission_days": 7,
    "ellipse": {"semi_major_m": 1000, "semi_minor_m": 600, "azimuth_deg": 0},
    "limits": {"max_dark_h": 50, "max_comm_gap_h": 72, "min_earth_pct": 50, "max_slope_deg": 8},
    "options": {"risk_margin": 0.2, "delay_days_max": 30, "include_recommendations": true, "observer_height_m": 2.0}
  },
  "input_limits": {
    "mission_days": [1, 30], "semi_major_m": [50, 5000], "semi_minor_m": [50, 5000],
    "max_dark_h": [1, 400], "max_comm_gap_h": [1, 400], "min_earth_pct": [0, 100], "max_slope_deg": [1, 30],
    "delay_days_max": [0, 60]
  }
}
```
(Values shown as `0.0` are filled from the real DEM.)

### 4.3 `POST /api/analyze`
**Request**
```json
{
  "target": {"lat": -84.6, "lon": 31.2},
  "landing_utc": "2027-03-10T14:00:00Z",
  "mission_days": 7,
  "ellipse": {"semi_major_m": 1000, "semi_minor_m": 600, "azimuth_deg": 0},
  "limits": {"max_dark_h": 50, "max_comm_gap_h": 72, "min_earth_pct": 50, "max_slope_deg": 8},
  "options": {"risk_margin": 0.2, "delay_days_max": 30, "include_recommendations": true, "observer_height_m": 2.0}
}
```
- `ellipse.azimuth_deg`: direction of the semi-major axis, clockwise from local north at the target.
- `limits.max_dark_h`: longest continuous period without sunlight the lander survives (battery).
- `limits.max_comm_gap_h`: longest continuous period without direct-to-Earth visibility tolerated.
- `limits.min_earth_pct`: minimum % of mission hours with Earth visible.
- `options.risk_margin`: fraction of a limit that counts as "close to failing" (0.2 = within 20% of a limit → risky).
- `options` may be omitted (defaults apply).

**Response 200**
```json
{
  "schema_version": "1.0",
  "is_sample": false,
  "computed_utc": "2026-11-15T14:03:22Z",
  "compute_ms": 1840,
  "inputs": { "...": "echo of the normalized request" },
  "coverage": {"in_coverage": true, "dem_name": "LOLA 5 m/px LDEM — Site20 (Mons Mouton)", "message": null},

  "target": {"lat": -84.6, "lon": 31.2, "x_m": 0.0, "y_m": 0.0, "elevation_m": 0.0, "slope_deg": 3.1},

  "summary": {
    "n_points": 118,
    "viable": 64, "risky": 34, "not_viable": 20,
    "survival_probability": 0.542,
    "survival_probability_incl_risky": 0.831,
    "checks_passed": 5, "checks_total": 7,
    "verdict": "risky"
  },

  "target_metrics": [
    {"id": "sun_at_touchdown",   "label": "Sun at touchdown",          "value": 1,     "unit": "bool", "display": "Yes · el 1.4°", "limit_display": "Required",                 "pass": true},
    {"id": "sun_hours",          "label": "Hours of sunlight",         "value": 121.0, "unit": "h",    "display": "121 h / 168 h", "limit_display": "≥ 60% of mission",         "pass": true},
    {"id": "longest_dark",       "label": "Longest darkness period",   "value": 41.0,  "unit": "h",    "display": "41 h",          "limit_display": "≤ 50 h (battery)",         "pass": true},
    {"id": "earth_pct",          "label": "Mission time with Earth visible", "value": 58.0, "unit": "%", "display": "58%",        "limit_display": "≥ 50%",                    "pass": true},
    {"id": "longest_comm_gap",   "label": "Longest comms gap",         "value": 96.0,  "unit": "h",    "display": "4 d 0 h",       "limit_display": "≤ 72 h",                   "pass": false},
    {"id": "hours_until_sunset", "label": "Time until sunset",         "value": 78.0,  "unit": "h",    "display": "3 d 6 h",       "limit_display": "≥ mission (7 d 0 h)",      "pass": false},
    {"id": "hours_until_earthset","label": "Time until Earthset",      "value": 30.0,  "unit": "h",    "display": "1 d 6 h",       "limit_display": "Reference",                "pass": null},
    {"id": "area_over_slope",    "label": "Ellipse area over max slope","value": 6.0,  "unit": "%",    "display": "6% > 8°",       "limit_display": "≤ 20% of ellipse",         "pass": true},
    {"id": "delay_tolerance",    "label": "Launch-delay tolerance",    "value": 9,     "unit": "days", "display": "9 days",        "limit_display": "Days the target stays viable", "pass": null}
  ],

  "points": [
    {
      "id": 0, "x_m": 0.0, "y_m": 0.0, "lat": -84.6, "lon": 31.2,
      "class": "viable",
      "reasons": [],
      "slope_deg": 3.2, "sun_hours": 130.0, "longest_dark_h": 12.0,
      "earth_pct": 60.0, "longest_comm_gap_h": 40.0,
      "hours_until_sunset": 168.0, "sun_at_touchdown": true
    }
  ],

  "timeseries": {
    "t0_utc": "2027-03-10T14:00:00Z",
    "step_h": 1,
    "n": 168,
    "sun_az_deg": [], "sun_el_deg": [], "horizon_at_sun_deg": [], "sun_lit": [],
    "earth_az_deg": [], "earth_el_deg": [], "horizon_at_earth_deg": [], "earth_visible": []
  },

  "horizon_profile": {"az_step_deg": 1.0, "elevation_deg": []},

  "delay_curve": [{"delay_days": 0, "survival_probability": 0.542, "target_viable": true}],
  "delay_tolerance_days": 9,

  "recommendations": [
    {"name": "1.0 km N of target", "lat": -84.59, "lon": 31.2, "distance_km": 1.0, "survival_probability": 0.84, "delta_pts": 30}
  ],

  "map": {
    "hillshade_url": "/api/static/hillshade.png",
    "hillshade_bounds_xy_m": [0.0, 0.0, 0.0, 0.0],
    "view_bounds_xy_m": [0.0, 0.0, 0.0, 0.0],
    "ellipse_polygon_xy_m": [[0.0, 0.0]]
  },

  "warnings": ["Horizon beyond the DEM edge (~8 km) is not modeled; distant peaks may block additional sunlight."],
  "sources": [
    "JPL Horizons System (Solar System Dynamics Group, NASA JPL) — Sun and Earth topocentric positions",
    "LRO LOLA 5 m/px LDEM, Site20 (Barker et al. 2021, NASA GSFC PGDA)"
  ]
}
```

Field rules:
- `points[].class` ∈ `"viable" | "risky" | "not_viable"`.
- `points[].reasons` ⊆ `["slope", "darkness", "comms_gap", "earth_time", "sunset", "no_sun_at_touchdown"]`. It lists the criteria that failed (not_viable) or are within the risk margin (risky).
- `summary.verdict` ∈ `"viable" | "risky" | "not_viable"`. It is the target point's class.
- `target_metrics[].pass` is `true`, `false` or `null` (informational). `checks_passed` and `checks_total` count only non-null metrics.
- `timeseries` arrays all have length `n` = `mission_days * 24`, for the **target point**. `sun_lit` and `earth_visible` are 0/1 integers.
- `horizon_profile.elevation_deg` has `360 / az_step_deg` values for the target point, starting at az 0.
- `delay_curve` has one entry per day from 0 to `delay_days_max`. The landing time shifts by that many days and everything is recomputed. `delay_tolerance_days` = the largest d such that the target stays viable (class viable or risky) for every delay 0..d. If the target is already not viable at 0 days, it is -1.
- `recommendations`: up to 3, only those with `survival_probability` greater than the current one, sorted descending. Empty list if none.
- `map.view_bounds_xy_m`: suggested view window (target-centered, ≥ 5 km wide, aspect 3:2).

### 4.4 Classification rules (engine must implement exactly)
For each point, with mission window `[landing, landing + mission_days)` sampled hourly:
- **not_viable** if any of:
  - `slope_deg > max_slope_deg` → `slope`
  - `longest_dark_h > max_dark_h` → `darkness` (a dark run that starts at touchdown counts)
  - `longest_comm_gap_h > max_comm_gap_h` → `comms_gap`
  - `earth_pct < min_earth_pct` → `earth_time`
  - Sun not lit at the touchdown hour → `no_sun_at_touchdown`
- **risky** if it is not not_viable and any of:
  - `slope_deg > (1 - risk_margin) * max_slope_deg`
  - `longest_dark_h > (1 - risk_margin) * max_dark_h`
  - `longest_comm_gap_h > (1 - risk_margin) * max_comm_gap_h`
  - `earth_pct < min_earth_pct * (1 + risk_margin)` (clipped at 100)
  - `hours_until_sunset < mission_hours` → `sunset` (the mission will experience a sunset)
- **viable** otherwise.
- `survival_probability = viable / n_points`. `survival_probability_incl_risky = (viable + risky) / n_points`. **Assumption to state in the UI: landing is uniformly distributed inside the ellipse.**

### 4.5 Errors
| Status | Body | When |
|---|---|---|
| 400 | `{"error":"out_of_coverage","message":"Target is outside the loaded DEM (Site20 Mons Mouton). Try a point near lat …, lon …","suggested_target":{"lat":…,"lon":…}}` | Target or most of the ellipse outside the DEM |
| 400 | `{"error":"out_of_ephemeris_range","message":"…"}` | Landing date (plus delay range) outside the precomputed ephemeris |
| 422 | FastAPI validation error | Bad or out-of-range inputs |
| 500 | `{"error":"internal","message":"…"}` | Bug |

### 4.6 Performance
`POST /api/analyze` must answer in **< 3 s** for the default request on the deployed server (2 vCPU) with recommendations on, and in **< 1.5 s** without recommendations. Identical requests are cached.

## 5. Python engine interface (shared by 02, 03, 04)
```python
# engine/ephemeris.py   (owner: 02)
def load_ephemeris(path="data/ephemeris/sun_earth_vectors.npz") -> "Ephemeris": ...
class Ephemeris:
    t_unix: "np.ndarray[int64]"        # hourly UTC timestamps
    sun_vec: "np.ndarray[float64]"      # (N, 3) unit vectors, Moon ME frame
    earth_vec: "np.ndarray[float64]"    # (N, 3) unit vectors, Moon ME frame
    def window(self, start_utc: "datetime", hours: int) -> tuple["np.ndarray", "np.ndarray", "np.ndarray"]: ...  # (t, sun_vec, earth_vec)
def local_az_el(vecs: "np.ndarray", lat_deg: "np.ndarray", lon_deg: "np.ndarray") -> tuple["np.ndarray", "np.ndarray"]:
    """vecs (T,3); lat/lon (P,) → az, el arrays of shape (P, T) in degrees."""

# engine/analyze.py     (owner: 03)
def get_meta() -> dict: ...                   # body of GET /api/meta
def analyze(request: dict) -> dict: ...       # body of POST /api/analyze (raises engine.errors.EngineError(code, message, extra))
```

## 6. Fixture
`fixtures/sample_response.json` must always be a valid example of section 4.3 with `"is_sample": true`. The frontend uses it when the API is unreachable and shows a visible "Sample data — API offline" banner.

## 7. AI-use header (every code file)
```
# Developed with assistance from Claude (Anthropic). Reviewed and integrated by the LunaScout team.
```
(Use `//` or `<!-- -->` as the language requires.)
