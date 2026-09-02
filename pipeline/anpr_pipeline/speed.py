"""Speed estimation from track history.

Uses the camera's calibrated meters_per_pixel (from its config) and the
track's positional history over the last window. This is planar-approximation
speed — adequate for alerting; certified enforcement requires per-site
homography calibration, which plugs in here later.
"""

import math

from anpr_pipeline.track import Track


def estimate_speed_kmh(
    track: Track, meters_per_pixel: float | None, min_window_s: float = 0.3
) -> float | None:
    if not meters_per_pixel or meters_per_pixel <= 0 or len(track.history) < 2:
        return None
    t0, x0, y0 = track.history[0]
    t1, x1, y1 = track.history[-1]
    dt = t1 - t0
    if dt < min_window_s:
        return None
    pixels = math.hypot(x1 - x0, y1 - y0)
    meters_per_second = (pixels * meters_per_pixel) / dt
    kmh = meters_per_second * 3.6
    if kmh > 400:  # implausible: calibration or tracking error
        return None
    return round(kmh, 1)
