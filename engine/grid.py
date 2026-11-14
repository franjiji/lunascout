# Developed with assistance from Claude (Anthropic). Reviewed and integrated by the LunaScout team.
"""Access to the precomputed horizon grid (written by scripts/precompute_horizons.py)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GRID_DIR = REPO_ROOT / "data" / "derived" / "horizon_grid"


class HorizonGrid:
    """Regular grid of horizon masks. Node (j, i) is at x = x0 + i*spacing, y = y0 + j*spacing."""

    def __init__(self, meta: dict, horizon_deg, reach_10m, height_m, slope_deg, lat, lon):
        self.meta = meta
        self.nx, self.ny = int(meta["nx"]), int(meta["ny"])
        self.x0, self.y0 = float(meta["x0"]), float(meta["y0"])
        self.spacing = float(meta["spacing_m"])
        self.observer_height_m = float(meta["observer_height_m"])
        self.n_az = int(meta.get("n_az", 360))
        self.reach_unit_m = float(meta.get("reach_unit_m", 10.0))
        self.horizon_deg = horizon_deg       # (ny, nx, n_az) float16
        self.reach_10m = reach_10m           # (ny, nx, n_az) uint16 or None
        self.height_m = height_m             # (ny, nx)
        self.slope_deg = slope_deg
        self.lat = lat
        self.lon = lon

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """(x_min, y_min, x_max, y_max) of the node area."""
        return (self.x0, self.y0, self.x0 + (self.nx - 1) * self.spacing, self.y0 + (self.ny - 1) * self.spacing)

    def contains(self, x, y):
        x0, y0, x1, y1 = self.bounds
        x, y = np.asarray(x), np.asarray(y)
        return (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)

    def node_xy(self, jj, ii):
        return self.x0 + np.asarray(ii) * self.spacing, self.y0 + np.asarray(jj) * self.spacing

    def nodes_in_bbox(self, x_min, y_min, x_max, y_max):
        """Index arrays (jj, ii) of all nodes inside the box (flattened meshgrid)."""
        i0 = max(0, int(np.ceil((x_min - self.x0) / self.spacing - 1e-9)))
        i1 = min(self.nx - 1, int(np.floor((x_max - self.x0) / self.spacing + 1e-9)))
        j0 = max(0, int(np.ceil((y_min - self.y0) / self.spacing - 1e-9)))
        j1 = min(self.ny - 1, int(np.floor((y_max - self.y0) / self.spacing + 1e-9)))
        if i1 < i0 or j1 < j0:
            return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)
        jj, ii = np.meshgrid(np.arange(j0, j1 + 1), np.arange(i0, i1 + 1), indexing="ij")
        return jj.ravel(), ii.ravel()

    def horizons(self, jj, ii) -> np.ndarray:
        """(P, n_az) float32 horizon elevations of the given nodes."""
        return np.asarray(self.horizon_deg[np.asarray(jj), np.asarray(ii)], dtype=np.float32)


def load_grid(grid_dir=None) -> HorizonGrid | None:
    """Load the grid, or return None if it has not been computed yet."""
    grid_dir = Path(grid_dir or os.environ.get("LUNASCOUT_GRID_DIR") or DEFAULT_GRID_DIR)
    meta_file = grid_dir / "meta.json"
    if not meta_file.exists() or not (grid_dir / "horizon_deg.npy").exists():
        return None
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    mmap = "r" if os.environ.get("LUNASCOUT_GRID_MMAP") == "1" else None
    horizon_deg = np.load(grid_dir / "horizon_deg.npy", mmap_mode=mmap)     # ~166 MB in RAM by default
    reach_file = grid_dir / "reach_10m.npy"
    reach = np.load(reach_file, mmap_mode="r") if reach_file.exists() else None   # rarely read: keep on disk
    return HorizonGrid(
        meta, horizon_deg, reach,
        np.load(grid_dir / "height_m.npy"), np.load(grid_dir / "slope_deg.npy"),
        np.load(grid_dir / "lat.npy"), np.load(grid_dir / "lon.npy"),
    )
