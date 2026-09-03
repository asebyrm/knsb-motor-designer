"""Curve downsampling that keeps the shape.

Two consumers:

* the API response, capped at ~500 points (Section 5.4);
* the ``.eng`` writer, capped at 32 points (Section 7.1).

Both must keep the ignition ramp, the pressure/thrust peak, curvature breaks and the
tail-off, and neither may shift total impulse by more than 1 % (Section 13.2). The
algorithm is a Ramer-Douglas-Peucker simplification on the (t, thrust) polyline with
the endpoints and the global ext​rema force-kept, followed by an area-error trim.
"""

from __future__ import annotations

import numpy as np


def _rdp_mask(x: np.ndarray, y: np.ndarray, epsilon: float) -> np.ndarray:
    """Boolean keep-mask from Ramer-Douglas-Peucker on the polyline (x, y)."""
    keep = np.zeros(x.size, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, x.size - 1)]
    while stack:
        i0, i1 = stack.pop()
        if i1 <= i0 + 1:
            continue
        x0, y0, x1, y1 = x[i0], y[i0], x[i1], y[i1]
        dx, dy = x1 - x0, y1 - y0
        norm = np.hypot(dx, dy) or 1.0
        seg = slice(i0 + 1, i1)
        dist = np.abs(dy * (x[seg] - x0) - dx * (y[seg] - y0)) / norm
        k = int(np.argmax(dist))
        if dist[k] > epsilon:
            idx = i0 + 1 + k
            keep[idx] = True
            stack.append((i0, idx))
            stack.append((idx, i1))
    return keep


def downsample_curve(
    t: np.ndarray,
    y: np.ndarray,
    max_points: int,
    *,
    extra: dict[str, np.ndarray] | None = None,
    area_tol: float = 0.01,
) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    """Reduce (t, y) to at most ``max_points`` samples, shape-preserving.

    ``extra`` columns are sampled at the same indices. The integral of ``y`` over
    ``t`` is held within ``area_tol`` (relative).
    """
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    extra = {k: np.asarray(v, dtype=float) for k, v in (extra or {}).items()}
    n = t.size
    if n <= max_points:
        return t, y, extra

    ref_area = float(np.trapezoid(y, t))
    yspan = float(y.max() - y.min()) or 1.0
    tspan = float(t.max() - t.min()) or 1.0
    # scale-invariant RDP: work in normalised coordinates
    xn, yn = (t - t.min()) / tspan, (y - y.min()) / yspan

    lo, hi = 1e-6, 1.0
    mask = np.ones(n, dtype=bool)
    for _ in range(40):
        eps = 0.5 * (lo + hi)
        m = _rdp_mask(xn, yn, eps)
        # always keep global extrema
        m[int(np.argmax(y))] = True
        m[int(np.argmin(y))] = True
        count = int(m.sum())
        if count > max_points:
            lo = eps
        else:
            mask = m
            hi = eps
            if count >= max_points - 2:
                break

    idx = np.flatnonzero(mask)
    # area correction check; if off, greedily re-add the worst-error points
    while True:
        approx_area = float(np.trapezoid(y[idx], t[idx]))
        if ref_area == 0 or abs(approx_area - ref_area) <= area_tol * abs(ref_area):
            break
        if idx.size >= min(n, max_points):
            break
        # insert the point with the largest local deviation from the linear interp
        interp = np.interp(t, t[idx], y[idx])
        err = np.abs(interp - y)
        err[idx] = -1.0
        idx = np.sort(np.append(idx, int(np.argmax(err))))

    out_extra = {k: v[idx] for k, v in extra.items()}
    return t[idx], y[idx], out_extra
