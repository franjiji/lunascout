# Developed with assistance from Claude (Anthropic). Reviewed and integrated by the LunaScout team.
"""
Quick test: Sun and Earth positions seen from a lunar site (JPL Horizons).
Usage:  pip install requests matplotlib
        python horizons_test.py
"""
import re
from datetime import datetime

import matplotlib.pyplot as plt
import requests

API = "https://ssd.jpl.nasa.gov/api/horizons.api"

# --- Configure here ---
SITE = "Shackleton"
LAT, LON = -89.67, 129.78          # verify in Quickmap
START, STOP, STEP = "2027-01-01", "2027-02-01", "1h"


def ephemeris(target: str) -> list[tuple[datetime, float, float]]:
    """target: '10' = Sun, '399' = Earth. Returns [(datetime, azimuth, elevation)]."""
    params = {
        "format": "text",
        "COMMAND": f"'{target}'",
        "CENTER": "'coord@301'",            # observer on the Moon
        "COORD_TYPE": "'GEODETIC'",
        "SITE_COORD": f"'{LON},{LAT},0'",   # note: longitude first
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'",
        "START_TIME": f"'{START}'",
        "STOP_TIME": f"'{STOP}'",
        "STEP_SIZE": f"'{STEP}'",
        "QUANTITIES": "'4'",                # azimuth and elevation
    }
    txt = requests.get(API, params=params, timeout=60).text
    block = txt.split("$$SOE")[1].split("$$EOE")[0]
    rows = []
    for line in block.strip().splitlines():
        m = re.match(r"\s*(\d{4}-\w{3}-\d{2} \d{2}:\d{2}).*?(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$", line)
        if m:
            when = datetime.strptime(m.group(1), "%Y-%b-%d %H:%M")
            rows.append((when, float(m.group(2)), float(m.group(3))))
    return rows


def hours_visible(rows, step_h=1.0):
    # Flat horizon (no terrain). Later replaced by the LOLA horizon mask.
    return sum(step_h for _, _, el in rows if el > 0)


if __name__ == "__main__":
    sun, earth = ephemeris("10"), ephemeris("399")
    print(f"{SITE}: Sun visible {hours_visible(sun):.0f} h | Earth visible {hours_visible(earth):.0f} h "
          f"(of {len(sun)} h, flat horizon)")
    print(f"Max Sun elevation: {max(e for *_, e in sun):.2f}°")

    plt.figure(figsize=(11, 4))
    plt.plot([f for f, *_ in sun], [e for *_, e in sun], label="Sun", color="orange")
    plt.plot([f for f, *_ in earth], [e for *_, e in earth], label="Earth", color="royalblue")
    plt.axhline(0, color="gray", ls="--", lw=1, label="Horizon (flat)")
    plt.title(f"Sun and Earth elevation from {SITE} ({LAT}, {LON})")
    plt.ylabel("Elevation (°)")
    plt.legend()
    plt.tight_layout()
    plt.show()
