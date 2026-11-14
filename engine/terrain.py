# Developed with assistance from Claude (Anthropic). Reviewed and integrated by the LunaScout team.
"""DEM access: LOLA 5 m/px surface height and slope (PGDA, Barker et al. 2021).

The DEM is loaded once (singleton) as float32 arrays. Pixel values are at pixel centers
(GMT pixel registration, see the PGDA README). Heights are meters relative to the
1,737,400 m reference sphere; slopes are degrees.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from scipy import ndimage

from . import geo

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEM_DIR = REPO_ROOT / "data" / "raw"

# Preferred first. Site20v2 = "Leibnitz beta plateau, extended boundaries" (26 x 26 km).
DEM_CANDIDATES = [
    ("Site20v2", "LOLA 5 m/px LDEM — Site20v2 (Mons Mouton / Leibnitz beta plateau)"),
    ("Site20", "LOLA 5 m/px LDEM — Site20 (Mons Mouton)"),
]


class Terrain:
    """A height raster (and optional slope raster) on a regular north-up map grid."""

    def __init__(self, surf, slp=None, *, x_min: float, y_max: float, pixel_m: float,
                 name: str = "synthetic", site_id: str = "synthetic"):
        self.surf = np.asarray(surf, dtype=np.float32)
        self.slp = None if slp is None else np.asarray(slp, dtype=np.float32)
        self.ny, self.nx = self.surf.shape
        self.pixel_m = float(pixel_m)
        self.x_min = float(x_min)
        self.y_max = float(y_max)
        self.x_max = self.x_min + self.nx * self.pixel_m
        self.y_min = self.y_max - self.ny * self.pixel_m
        self.name = name
        self.site_id = site_id

    # ------------------------------------------------------------------ basic info
    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """(x_min, y_min, x_max, y_max) of the raster outer edges, meters."""
        return (self.x_min, self.y_min, self.x_max, self.y_max)

    @property
    def center_xy(self) -> tuple[float, float]:
        return (0.5 * (self.x_min + self.x_max), 0.5 * (self.y_min + self.y_max))

    def _rowcol(self, x, y):
        col = (np.asarray(x, dtype=np.float64) - self.x_min) / self.pixel_m - 0.5
        row = (self.y_max - np.asarray(y, dtype=np.float64)) / self.pixel_m - 0.5
        return row, col

    def _sample(self, arr, x, y):
        row, col = self._rowcol(x, y)
        shape = np.broadcast(row, col).shape
        coords = np.stack([np.broadcast_to(row, shape).ravel(), np.broadcast_to(col, shape).ravel()])
        out = ndimage.map_coordinates(arr, coords, order=1, mode="constant", cval=np.nan,
                                      output=np.float64, prefilter=False)
        return out.reshape(shape)

    # ------------------------------------------------------------------ queries
    def height_at(self, x, y):
        """Bilinear terrain height (m) at map coordinates; NaN outside the grid."""
        return self._sample(self.surf, x, y)

    def slope_at(self, x, y):
        """Bilinear slope (degrees) at map coordinates; NaN outside the grid."""
        if self.slp is None:
            raise RuntimeError("No slope raster loaded")
        return self._sample(self.slp, x, y)

    def in_coverage(self, x, y, margin_m: float = 0.0):
        """True where the point is inside the DEM and at least margin_m away from its edge."""
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        return ((x >= self.x_min + margin_m) & (x <= self.x_max - margin_m)
                & (y >= self.y_min + margin_m) & (y <= self.y_max - margin_m))

    def max_distance_from(self, x: float, y: float) -> float:
        """Largest map distance from (x, y) to a DEM corner (upper bound for ray length)."""
        dx = max(abs(x - self.x_min), abs(x - self.x_max))
        dy = max(abs(y - self.y_min), abs(y - self.y_max))
        return float(np.hypot(dx, dy))

    # ------------------------------------------------------------------ hillshade
    def hillshade_bounds(self, max_px: int = 2048) -> list[float]:
        """[x_min, y_min, x_max, y_max] of the hillshade image written by make_hillshade()."""
        f = max(1, int(np.ceil(max(self.ny, self.nx) / float(max_px))))
        ny, nx = (self.ny // f) * f, (self.nx // f) * f
        return [self.x_min, self.y_max - ny * self.pixel_m, self.x_min + nx * self.pixel_m, self.y_max]

    def make_hillshade(self, out_png, max_px: int = 2048, azimuth_deg: float = 315.0,
                       altitude_deg: float = 45.0, z_factor: float = 1.0):
        """Write a grayscale hillshade PNG and return its bounds [x_min, y_min, x_max, y_max].

        The light comes from azimuth_deg measured clockwise from map-up (+y), i.e. 315 = upper left.
        This is a display product only (it is not the real Sun direction).
        """
        from PIL import Image

        f = int(np.ceil(max(self.ny, self.nx) / float(max_px)))
        f = max(f, 1)
        ny, nx = (self.ny // f) * f, (self.nx // f) * f
        z = self.surf[:ny, :nx].astype(np.float32)
        if f > 1:
            z = z.reshape(ny // f, f, nx // f, f).mean(axis=(1, 3))
        cell = self.pixel_m * f
        zf = np.where(np.isfinite(z), z, np.nanmean(z))
        d_row, d_col = np.gradient(zf * z_factor, cell)
        dzdx, dzdy = d_col, -d_row                      # rows grow toward -y
        az, alt = np.radians(azimuth_deg), np.radians(altitude_deg)
        lx, ly, lz = np.sin(az) * np.cos(alt), np.cos(az) * np.cos(alt), np.sin(alt)
        norm = np.sqrt(dzdx ** 2 + dzdy ** 2 + 1.0)
        shade = (-dzdx * lx - dzdy * ly + lz) / norm
        shade = np.clip(shade, 0.0, 1.0)
        img = (255.0 * shade + 0.5).astype(np.uint8)
        out_png = Path(out_png)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(img, mode="L").save(out_png, optimize=True)
        return self.hillshade_bounds(max_px)


# --------------------------------------------------------------------------- loading
def find_dem_files(dem_dir=None):
    """Return (site_id, name, surf_path, slp_path) for the best DEM present in dem_dir."""
    dem_dir = Path(dem_dir or os.environ.get("LUNASCOUT_DEM_DIR") or DEFAULT_DEM_DIR)
    for site_id, name in DEM_CANDIDATES:
        surf = dem_dir / f"{site_id}_final_adj_5mpp_surf.tif"
        slp = dem_dir / f"{site_id}_final_adj_5mpp_slp.tif"
        if surf.exists():
            return site_id, name, surf, (slp if slp.exists() else None)
    raise FileNotFoundError(
        f"No Site20 DEM found in {dem_dir}. Run: python scripts/prepare_dem.py"
    )


def load_terrain(dem_dir=None, with_slope: bool = True) -> Terrain:
    """Read the GeoTIFFs with rasterio, set the map CRS in engine.geo, return a Terrain."""
    import rasterio

    site_id, name, surf_path, slp_path = find_dem_files(dem_dir)
    with rasterio.open(surf_path) as ds:
        surf = ds.read(1).astype(np.float32)
        if ds.nodata is not None and not np.isnan(ds.nodata):
            surf[surf == ds.nodata] = np.nan
        tr = ds.transform
        crs = ds.crs
        if abs(tr.b) > 1e-9 or abs(tr.d) > 1e-9 or abs(tr.a + tr.e) > 1e-6:
            raise ValueError(f"Unexpected DEM geotransform (rotated or non-square pixels): {tuple(tr)}")
        x_min, y_max, pixel = tr.c, tr.f, tr.a
    slp = None
    if with_slope and slp_path is not None:
        with rasterio.open(slp_path) as ds:
            if (ds.width, ds.height) != (surf.shape[1], surf.shape[0]) or tuple(ds.transform) != tuple(tr):
                raise ValueError("Slope raster grid does not match the surface raster")
            slp = ds.read(1).astype(np.float32)
            if ds.nodata is not None and not np.isnan(ds.nodata):
                slp[slp == ds.nodata] = np.nan
    geo.configure(crs)
    return Terrain(surf, slp, x_min=x_min, y_max=y_max, pixel_m=pixel, name=name, site_id=site_id)


_TERRAIN: Terrain | None = None


def get_terrain() -> Terrain:
    """The process-wide DEM (loaded on first use)."""
    global _TERRAIN
    if _TERRAIN is None:
        _TERRAIN = load_terrain()
    return _TERRAIN


def set_terrain(terrain: Terrain | None) -> None:
    """Replace the process-wide DEM (used by tests with synthetic terrain)."""
    global _TERRAIN
    _TERRAIN = terrain


def height_at(x, y):
    return get_terrain().height_at(x, y)


def slope_at(x, y):
    return get_terrain().slope_at(x, y)


def in_coverage(x, y, margin_m: float = 0.0):
    return get_terrain().in_coverage(x, y, margin_m)


def make_hillshade(out_png, max_px: int = 2048):
    return get_terrain().make_hillshade(out_png, max_px=max_px)
