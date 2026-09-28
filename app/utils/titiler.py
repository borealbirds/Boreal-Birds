"""
The TiTiler mapping gateway: part of the data access layer for the BAM dashboard backend.

Main Capabilities
-----------------
* Monitors the dynamic cloud raster tiler API health status.
"""

import requests
import time

# Live Posit Connect Cloud dynamic map tiler base domain address
PRODUCTION_TILER_BASE = "https://019e4735-507f-07a0-1ae5-b96da68b058b.share.connect.posit.cloud"

# cache to check titiler API health status
TILER_HEALTH_TTL = 30

_tiler_health_cache = {
    "timestamp": 0,
    "healthy": False
}


def tiler_is_healthy() -> bool:
    """
    Check the health status of the remote TiTiler API gateway.

    Uses a basic Time-To-Live (TTL) caching mechanism to prevent spamming
    the health endpoint on rapid UI reactive invalidations.

    Returns
    -------
    bool
        True if the tiler endpoint responds with a status code of 200 and an
        'ok' status payload, False otherwise.

    Notes
    -------
    The cache state is managed globally by the `_tiler_health_cache` dictionary
    using the window duration defined in `TILER_HEALTH_TTL`.
    """
    now = time.time()

    if now - _tiler_health_cache["timestamp"] < TILER_HEALTH_TTL:
        return _tiler_health_cache["healthy"]

    try:
        r = requests.get(
            f"{PRODUCTION_TILER_BASE}/health",
            timeout=10
        )

        healthy = (
            r.status_code == 200 and
            r.json().get("status") == "ok"
        )

    except Exception:
        healthy = False

    _tiler_health_cache["healthy"] = healthy
    _tiler_health_cache["timestamp"] = now

    return healthy
