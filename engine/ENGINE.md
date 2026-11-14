<!-- Developed with assistance from Claude (Anthropic). Reviewed and integrated by the LunaScout team. -->
# LunaScout terrain engine

The engine answers one question: **given where the lander is aimed, and that it will touch down
somewhere inside its landing ellipse, what fraction of the ellipse lets the mission survive?**
Survival needs sunlight (power, heat), direct-to-Earth visibility (comms) and a safe slope.

Interfaces are fixed by `CONTRACT.md`: `engine.analyze.analyze(request) -> dict` and
`engine.analyze.get_meta() -> dict`.

> **Status of the ephemeris.** `engine/ephemeris.py` and `data/ephemeris/sun_earth_vectors.npz`
> (JPL Horizons, owned by the ephemeris agent) are not merged yet. Until they are, the engine only
> runs with `LUNASCOUT_ALLOW_STUB=1`, which uses `engine/_ephemeris_stub.py`: **synthetic** Sun and
> Earth positions. Every response produced that way has `"is_sample": true` and a warning. The
> terrain side (DEM, slopes, horizon masks) is real data.

## 1. The idea in one picture

```
                          Sun, 0 to 6 deg above the horizontal
                              .
                         .          terrain skyline seen from the lander
                    .           /\        (horizon elevation, one value per azimuth)
               .               /  \____
          .   theta           /        \___      .
   [lander]------------------/-------------\----------- local horizontal plane
      |  2 m             ___/               \___
   ___|_________________/                       \________  DEM surface (LOLA, 5 m/px)

   Sun is "lit"        <=>  Sun elevation   > horizon elevation at the Sun's azimuth
   Earth is "visible"  <=>  Earth elevation > horizon elevation at Earth's azimuth
```

Near the south pole the Sun never rises more than `(90 - |lat|) + 1.54` degrees (6.1 degrees at
the DEM center), so a hill a few hundred meters away is enough to hide it.

## 2. Data

| File | What | In git? |
|---|---|---|
| `data/raw/Site20v2_final_adj_5mpp_surf.tif`, `_slp.tif` | LOLA 5 m/px height and slope, PGDA "Site20v2: Leibnitz beta plateau, extended boundaries" (108 MB each) | no (ignored) |
| `data/derived/dem_meta.json` | coverage, CRS, center, source URLs | yes |
| `data/derived/hillshade.png` | 1733 x 1733 px shaded relief for the map (display only) | yes (1.7 MB) |
| `data/derived/horizon_grid/*.npy` + `meta.json` | precomputed horizon masks (339 MB) | only `meta.json` |
| `data/derived/horizon_tiles/` | per-row working files of the precompute (423 MB, can be deleted) | no (ignored) |

DEM facts (read from the GeoTIFF, see `dem_meta.json`):

- 5200 x 5200 px at 5 m = 26 x 26 km, no empty pixels. Map bounds x 60,000..86,000 m, y 105,000..131,000 m.
- CRS: south polar stereographic on the 1,737,400 m sphere, `lat_0=-90`, `lon_0=0`, true scale at the
  pole. Same as the contract's fallback. The closed-form projection used in the hot loops matches
  pyproj to better than 1 mm (checked at load time and in `test_geo.py`).
- Center: **lat -85.42658, lon 31.74276 E**, height 6398.7 m. Latitude range -86.01 to -84.84,
  longitude range 24.6 to 39.3 E. Heights 1330 to 6788 m.
- Source: Barker, M. K., et al. (2021), *Planetary and Space Science* 203, 105119,
  doi:10.1016/j.pss.2020.105119. https://pgda.gsfc.nasa.gov/products/78

### How to regenerate the large files

```
pip install -r engine/requirements.txt
python scripts/prepare_dem.py            # downloads the two GeoTIFFs from PGDA (about 6 min), writes dem_meta.json + hillshade.png
python scripts/precompute_horizons.py    # 50 m horizon grid: 8.5 min with 12 processes on a 16-core laptop
```

The precompute is resumable: it writes one file per grid row and skips the rows that already exist,
so it can be stopped and restarted. For a server build, either run both scripts in the image build
or copy `data/raw/*.tif` and `data/derived/horizon_grid/` into the image (they are too large for
git: GitHub rejects files over 100 MB).

## 3. Modules

| Module | Role |
|---|---|
| `geo.py` | lat/lon <-> map x/y, great-circle helpers, local north/east in the map plane |
| `terrain.py` | loads the DEM once; `height_at`, `slope_at` (bilinear), `in_coverage`, `make_hillshade` |
| `horizon.py` | horizon mask of one observer (the core algorithm) |
| `grid.py` | loads the precomputed horizon grid |
| `metrics.py` | per-point mission metrics and the classification rules of CONTRACT 4.4 |
| `analyze.py` | `analyze()` and `get_meta()` |
| `_ephemeris_stub.py` | synthetic Sun/Earth for development and tests only |
| `make_fixture.py` | `python -m engine.make_fixture` writes `fixtures/sample_response.json` |

## 4. Horizon mask (`horizon.py`)

For an observer standing `h_obs` (default 2 m) above the terrain, and for each of 360 azimuths
(1 degree bins, clockwise from local north):

1. Walk along the great circle that leaves the observer in that direction. Sample distances start
   at 10 m and grow as `step = max(5 m, 1% of the distance)`: 5 m steps near the lander, about
   100 m steps at 10 km. This gives about 460 samples for a ray that reaches the far DEM corner.
2. Read the terrain height `z` at every sample (bilinear inside 1 km, nearest 5 m pixel beyond).
3. Convert it to an elevation angle with exact spherical geometry (no flat-Moon approximation):

   `theta = atan2( (R+z) cos(s/R) - (R + z0 + h_obs),  (R+z) sin(s/R) )`

   `R` = 1,737,400 m, `s` = ground distance, `z0` = terrain height under the observer. The term
   `cos(s/R)` is the curvature drop: 7 m at 5 km, 29 m at 10 km.
4. The horizon elevation at that azimuth is the largest `theta` over the samples inside the DEM.
   The distance of the last sample inside the DEM (`reach`) is stored too: if a ray leaves the DEM
   early, more distant peaks are missing and the horizon may be underestimated.

All 360 azimuths x 460 samples of one observer are one numpy array operation (no Python loop).
Measured: **14 to 20 ms per observer** on the real DEM (target was < 30 ms).

Why 1% spacing: 1 degree azimuth bins are 1.7% of the distance apart sideways, so sampling the
ray much finer than that along its length would not add accuracy. Worst-case angular error from
the ray spacing on a 30 degree slope is about 0.17 degrees; from the nearest-pixel read beyond
1 km, less than 0.08 degrees. The Sun's disk is 0.53 degrees wide.

### Precomputed grid (`scripts/precompute_horizons.py`)

- Regular grid, **50 m spacing**, 1 km margin from the DEM edge: 481 x 481 = **231,361 nodes**.
- Per node: 360 horizon elevations (float16), 360 reach values (uint16, units of 10 m), height,
  5 m slope, lat, lon. 339 MB on disk; the API keeps the horizon array (167 MB) in RAM and
  memory-maps the reach array.
- 8.5 minutes with 12 worker processes (28 ms per node per core under load).
- Observer height is fixed at 2 m in the grid. A request with a different `observer_height_m`
  is computed on the fly instead (about 65 points, with a warning).

## 5. Analysis (`analyze.py`)

1. **Normalize** the request (defaults of CONTRACT 4.2; the landing time is floored to the hour).
2. **Coverage**: the target must be inside the analyzable area (DEM minus the 1 km margin) and at
   least 80% of the ellipse area must be inside it; otherwise `out_of_coverage` with the DEM center
   as `suggested_target`. The landing time plus mission plus delay range must be inside the
   ephemeris; otherwise `out_of_ephemeris_range`.
3. **Sample points**: the 50 m grid nodes inside the ellipse. The ellipse azimuth is measured from
   *local* north at the target, which in a polar stereographic map points away from the pole, not
   along the map's y axis. More than 400 nodes are thinned to a regular sub-lattice (71 m, 100 m,
   141 m, ...). Fewer than 40 nodes (small ellipse) switches to about 70 points on a hexagonal
   grid whose horizons are computed on the fly.
4. **Sun and Earth** azimuth/elevation at every point and hour (`local_az_el`), compared with the
   point's horizon at that azimuth (linear interpolation between the 1 degree bins, wrapping at
   360). The target itself always gets its own exact horizon, not the nearest grid node.
5. **Metrics per point** over the mission window: sunlit hours, longest darkness, % of time with
   Earth visible, longest comms gap, hours until sunset, Sun at touchdown, slope. Run lengths are
   computed with cumulative numpy operations.
6. **Classification** exactly as CONTRACT 4.4. `survival_probability = viable / n_points`.
7. **Delay curve**: the same (points x hours) arrays are sliced 24 h later for each delay day and
   reclassified. `delay_tolerance_days` is the last day up to which the target stays viable or risky.
8. **Recommendations**: 24 candidates on rings at 1, 2 and 3 km (8 bearings) plus the curated
   sites, each evaluated on a coarser sample (up to 60 grid nodes); the best 3 that beat the current
   probability are returned.
9. Identical requests are served from a 32-entry cache.

Extra field (not in the contract example, allowed by CONTRACT section 2):
`timeseries.sun_visible_fraction`, the fraction of the solar disk above the horizon, for display.
Classification uses the center-of-disk rule only.

`coverage.bounds_xy_m` in `get_meta()` is the **analyzable area** (x 61,000..85,000, y
106,000..130,000), i.e. where a target is accepted; `map.hillshade_bounds_xy_m` is the full image.

### Curated sites

Chosen from the horizon grid with geometry only (no ephemeris): 350 m mean slope, and the fraction
of azimuths where an idealized Sun (`elevation = colatitude * cos(azimuth) + season`, season =
+1.54 / 0 / -1.54 degrees) clears the terrain horizon. The labels are descriptive, not official names.

| id | Label | lat, lon | Why |
|---|---|---|---|
| `mons_mouton_center` | Mons Mouton (DEM center) | -85.42658, 31.74276 | center of the DEM; sits on a slope rising to the north (8 degree horizon there) |
| `summit_plateau` | Summit plateau (high, flat, long sunlight) | -85.47628, 31.39691 | 6311 m, slope 4 degrees, horizon below 3.8 degrees in every direction |
| `western_bench` | Western bench (flat, Earth in view) | -85.39890, 29.95361 | slope 2 degrees, low horizon toward Earth |
| `crater_floor` | Crater floor (shadowed) | -85.23787, 33.95403 | flat floor, horizon up to 16 degrees, never clears the idealized Sun |
| `sunlit_slope` | Sunlit slope (steep) | -85.48962, 30.66935 | well lit but 12 degree slope |

## 6. Assumptions

- Landing point **uniformly distributed** inside the ellipse (stated in every response).
- Observer (solar array / antenna) **2 m** above the terrain.
- **1 hour** time step; a sunset between two samples is located to the hour.
- **Center-of-disk** rule for sunlight; no penumbra in the classification.
- Horizon known **only as far as the DEM edge**.
- No atmosphere, so no refraction (correct for the Moon).
- Slope is the PGDA 5 m slope product; boulders and craters smaller than about 5 m are not seen.
- One Sun/Earth direction for the whole DEM at each hour: the parallax across 26 km is 0.004
  degrees for Earth and negligible for the Sun.

## 7. Known limitations

- **Distant terrain is missing.** From the summit plateau the rays reach 11 to 20 km; near the edge
  of the analyzable area only 1 km in the worst direction. Each response reports the reach of the
  target and the share of directions under 10 km. A wider, coarser DEM (for example the LOLA
  20 m/px polar mosaic) for the far field would remove this.
- **Coverage is one 26 x 26 km tile.** Latitudes north of -84.84 are outside it. That includes the
  example target of the contract (-84.6, 31.2); the validation agent must check whether the IM-2
  landing site is inside before planning the replay on this DEM.
- **Rough terrain.** Only 23% of the tile has a 5 m slope under 8 degrees, so slope is the most
  common reason for "not viable".
- No thermal model (darkness duration is the proxy), no relay satellites, no eclipses, no descent
  trajectory constraints.
- Recommendations use a coarser sample than the main analysis, so their probability is comparable
  to, not identical with, a full run on that target.
- DEM height error (0.3 to 0.5 m RMS) is not propagated; the 100 PGDA clones could be used for that.

## 8. Tests

`python -m pytest engine/tests -q` : **35 passed** (27 s; the two tests that need the real DEM are
skipped when it is not downloaded).

| Test | Expected | Result |
|---|---|---|
| Flat sphere, h = 2 m | horizon = -acos(R/(R+h)) = -0.0869 degrees | within 0.0002 degrees at all 360 azimuths |
| Ring wall, H = 200 m at D = 2 km | atan2(H - h - D^2/2R, D) = 5.62 degrees | within 0.1 degrees (default sampling), 0.03 degrees (fine sampling), never above the analytic value |
| Wall 60 m at 5 km | curvature term changes the answer by 0.08 degrees | matches the formula with curvature to 0.01 degrees |
| Wall only to the east | high at azimuth 90, flat at 0 / 180 / 270 | passes (azimuth is clockwise from north) |
| Symmetric bowl | horizon independent of azimuth | spread under 0.03 degrees (0.01 with bilinear sampling throughout) |
| Classification | every rule of CONTRACT 4.4, limits and margins | passes |
| Contract shape | keys, types, lengths, consistency of `analyze()` output | passes in grid mode, on-the-fly mode and without a grid |
| Physical sanity (synthetic) | crater floor darker than the open plain; Sun never above (90 - lat) + 1.54 | passes |
| Ellipse orientation | azimuth 0 elongates the ellipse along local north | passes |

## 9. Timings

Laptop, 16 cores, Python 3.13, default request (7 days, 1000 x 600 m ellipse, 30 delay days,
384 points) at the summit plateau. The engine itself uses one core.

| Case | Time | Contract target |
|---|---|---|
| Warm, with recommendations | **300 ms** (max 318) | < 3 s |
| Warm, without recommendations | **195 ms** (max 213) | < 1.5 s |
| Identical request (cache) | 5 ms | |
| Cold: first request of a new process (loads DEM + grid) | 2.2 to 3.4 s, of which 0.3 s is analysis | call `get_meta()` at API start-up |
| Small ellipse 100 x 100 m (on the fly), first time | 1.3 s | |
| Same small ellipse, new date (horizons cached) | 80 ms | |
| Largest request: 30 days, 60 delay days, 5 x 5 km | 1.2 s | |
| Horizon of one observer | 14 to 20 ms | < 30 ms |

Memory: about 400 MB (two 108 MB rasters + 167 MB horizon array).

## 10. Environment variables

| Variable | Effect |
|---|---|
| `LUNASCOUT_ALLOW_STUB=1` | allow the synthetic ephemeris when the real one is missing (development only) |
| `LUNASCOUT_DEM_DIR` | folder with the GeoTIFFs (default `data/raw`) |
| `LUNASCOUT_GRID_DIR` | folder with the horizon grid (default `data/derived/horizon_grid`) |
| `LUNASCOUT_GRID_MMAP=1` | memory-map the horizon array instead of loading it into RAM |
