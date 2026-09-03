"""Quasi-steady internal-ballistics time march - the main engine (Section 5.4).

For each step: burn area -> Klemmung -> equilibrium chamber pressure -> burn rate,
thrust coefficient, thrust, mass flow; integrate impulse; advance the burnt web and
(optionally) the eroding throat.

Extras required by the spec:

* automatic ``dt`` convergence check (halve until total impulse is stable < 0.1 %);
* exponential tail-off after web burnout, ``tau = V_c / (c* * A_t)``;
* simplified ignition transient over the first 50 ms;
* quasi-steady validity check ``tau_c / t_b > 0.01`` -> ``WARN_QUASI_STEADY_INVALID``;
* a companion **erosionless** pressure trace; MEOP is always judged on that one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from core.grains.base import GrainGeometry
from core.nozzle import Nozzle
from core.propellant import Propellant
from core.sampling import downsample_curve
from core.units import G0
from core.warnings import Warning, dedupe, make

_IGNITION_WINDOW = 0.050          # s
_MAX_DT_HALVINGS = 4
_CONVERGENCE_TOL = 0.001          # 0.1 % on total impulse
_TAILOFF_CUTOFF_FRACTION = 0.02   # stop tail-off when p drops below 2 % of burnout p


@dataclass
class BallisticsResult:
    time: np.ndarray
    chamber_pressure: np.ndarray            # Pa (with erosion + transients)
    chamber_pressure_no_erosion: np.ndarray  # Pa (worst case for MEOP)
    thrust: np.ndarray                      # N
    burn_rate: np.ndarray                   # m/s
    kn: np.ndarray                          # -
    burn_area: np.ndarray                   # m^2
    throat_area: np.ndarray                 # m^2
    port_area: np.ndarray                   # m^2
    mass_flow: np.ndarray                   # kg/s
    cumulative_impulse: np.ndarray          # N*s
    propellant_mass: np.ndarray             # kg
    web: np.ndarray                         # m
    warnings: list[Warning] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    converged: bool = True
    dt_used: float = 0.001

    def downsampled(self, max_points: int = 500) -> BallisticsResult:
        t, thr, extra = downsample_curve(
            self.time,
            self.thrust,
            max_points,
            extra={
                "chamber_pressure": self.chamber_pressure,
                "chamber_pressure_no_erosion": self.chamber_pressure_no_erosion,
                "burn_rate": self.burn_rate,
                "kn": self.kn,
                "burn_area": self.burn_area,
                "throat_area": self.throat_area,
                "port_area": self.port_area,
                "mass_flow": self.mass_flow,
                "cumulative_impulse": self.cumulative_impulse,
                "propellant_mass": self.propellant_mass,
                "web": self.web,
            },
        )
        return BallisticsResult(
            time=t, thrust=thr, **extra,
            warnings=self.warnings, summary=self.summary,
            converged=self.converged, dt_used=self.dt_used,
        )


def estimate_chamber_volume(grain: GrainGeometry, ullage_factor: float = 1.05) -> float:
    """Rough empty-case internal volume [m^3] when the assembly isn't supplied."""
    r = grain.outer_diameter() / 2.0
    return math.pi * r * r * grain.envelope_length() * ullage_factor


def _march_once(
    grain: GrainGeometry,
    propellant: Propellant,
    nozzle: Nozzle,
    *,
    dt: float,
    ambient_pressure: float,
    chamber_volume: float,
    t_max: float,
) -> dict:
    """Single fixed-dt integration. Returns raw numpy columns + scalars."""
    web_total = grain.web_thickness()
    a_t0 = nozzle.throat_area
    r_t0 = nozzle.throat_diameter / 2.0
    cstar = propellant.c_star_effective
    gamma = propellant.gamma

    x = 0.0
    r_t = r_t0
    t = 0.0
    impulse = 0.0

    cols: dict[str, list[float]] = {k: [] for k in (
        "time", "p", "p_noero", "F", "rb", "kn", "ab", "at", "ap", "mdot", "imp", "mp", "web")}

    p_extrap_lo = math.inf
    p_extrap_hi = -math.inf
    solver_warns: list[Warning] = []
    burnout_p = 0.0
    burnout_t = None

    step = 0
    max_steps = int(t_max / dt) + 5
    while t < t_max and step < max_steps:
        burning = x < web_total
        a_b = grain.burn_area(x) if burning else 0.0
        a_t = math.pi * r_t * r_t
        free_volume = max(chamber_volume - grain.volume(min(x, web_total)), 1e-9)
        tau_chamber = free_volume / (cstar * a_t)

        if burning:
            k_n = a_b / a_t
            sol = propellant.solve_equilibrium_pressure(k_n)
            p_eq = sol.pressure_pa
            for w in sol.warnings:
                if w.code not in {x.code for x in solver_warns}:
                    solver_warns.append(w)
            # erosionless companion
            k_n0 = a_b / a_t0
            p_noero = propellant.solve_equilibrium_pressure(k_n0).pressure_pa
            # ignition transient
            if t < _IGNITION_WINDOW:
                ramp = 1.0 - math.exp(-t / max(tau_chamber, 1e-6))
                p_c = p_eq * ramp
                p_noero *= ramp
            else:
                p_c = p_eq
            burnout_p = p_c
            burnout_t = t
        else:
            # exponential tail-off
            dt_since = t - (burnout_t if burnout_t is not None else t)
            p_c = burnout_p * math.exp(-dt_since / max(tau_chamber, 1e-6))
            p_noero = p_c
            if p_c < _TAILOFF_CUTOFF_FRACTION * max(burnout_p, 1.0):
                cols["time"].append(t)
                closing = {
                    "p": 0.0, "p_noero": 0.0, "F": 0.0, "rb": 0.0, "kn": 0.0,
                    "ab": 0.0, "at": a_t, "ap": grain.port_area(web_total),
                    "mdot": 0.0, "imp": impulse,
                    "mp": propellant.density * grain.sliver_volume(), "web": x,
                }
                for key, val in closing.items():
                    cols[key].append(val)
                break

        p_for_cf = max(p_c, 1.2 * ambient_pressure)
        cf = nozzle.thrust_coefficient(p_for_cf, ambient_pressure, gamma)
        thrust = max(cf * p_c * a_t, 0.0)
        mdot = p_c * a_t / cstar
        impulse += thrust * dt

        if burning and t >= _IGNITION_WINDOW and propellant.is_extrapolated(p_c):
            p_extrap_lo = min(p_extrap_lo, p_c)
            p_extrap_hi = max(p_extrap_hi, p_c)

        r_b = propellant.burn_rate(p_c) if burning else 0.0
        m_p = propellant.density * grain.volume(min(x, web_total))

        cols["time"].append(t)
        cols["p"].append(p_c)
        cols["p_noero"].append(p_noero)
        cols["F"].append(thrust)
        cols["rb"].append(r_b)
        cols["kn"].append(a_b / a_t if a_t else 0.0)
        cols["ab"].append(a_b)
        cols["at"].append(a_t)
        cols["ap"].append(grain.port_area(min(x, web_total)))
        cols["mdot"].append(mdot)
        cols["imp"].append(impulse)
        cols["mp"].append(m_p)
        cols["web"].append(x)

        x += r_b * dt
        r_t += nozzle.erosion_rate(p_c) * dt
        t += dt
        step += 1

    arr = {k: np.asarray(v, dtype=float) for k, v in cols.items()}
    warns = list(solver_warns)
    if math.isfinite(p_extrap_lo):
        warns.append(make("WARN_EXTRAPOLATED_BURN_RATE",
                          p_min_mpa=round(p_extrap_lo / 1e6, 3),
                          p_max_mpa=round(p_extrap_hi / 1e6, 3)))
    return {
        "arr": arr,
        "total_impulse": impulse,
        "burnout_time": burnout_t or 0.0,
        "web_total": web_total,
        "warnings": warns,
    }


def simulate(
    grain: GrainGeometry,
    propellant: Propellant,
    nozzle: Nozzle,
    *,
    dt: float = 0.001,
    ambient_pressure: float = 101_325.0,
    chamber_volume: float | None = None,
    t_max: float = 60.0,
    meop_pa: float | None = None,
    lstar_range_mm: tuple[float, float] = (250.0, 1000.0),
    check_convergence: bool = True,
) -> BallisticsResult:
    """Run the time march with automatic dt convergence and post-run diagnostics."""
    if chamber_volume is None:
        chamber_volume = estimate_chamber_volume(grain)

    run = _march_once(grain, propellant, nozzle, dt=dt, ambient_pressure=ambient_pressure,
                      chamber_volume=chamber_volume, t_max=t_max)
    dt_used = dt
    converged = True
    if check_convergence:
        halvings = 0
        while halvings < _MAX_DT_HALVINGS:
            finer = _march_once(grain, propellant, nozzle, dt=dt_used / 2.0,
                                ambient_pressure=ambient_pressure,
                                chamber_volume=chamber_volume, t_max=t_max)
            i0, i1 = run["total_impulse"], finer["total_impulse"]
            rel = abs(i1 - i0) / max(abs(i1), 1e-9)
            run, dt_used = finer, dt_used / 2.0
            halvings += 1
            if rel < _CONVERGENCE_TOL:
                break
        else:
            converged = False

    arr = run["arr"]
    warns: list[Warning] = list(run["warnings"])
    if not converged:
        warns.append(make("WARN_CONVERGENCE_NOT_REACHED", dt=dt_used))

    p_noero = arr["p_noero"]
    p_max_noero = float(p_noero.max()) if p_noero.size else 0.0
    p_max = float(arr["p"].max()) if arr["p"].size else 0.0

    # burn time: ignition to 5 % of peak thrust (NAR-style; also where .eng ends at 0)
    thrust = arr["F"]
    t_arr = arr["time"]
    if thrust.size:
        f_max = float(thrust.max())
        above = np.flatnonzero(thrust >= 0.05 * f_max)
        t_b = float(t_arr[above[-1]] - t_arr[above[0]]) if above.size else float(t_arr[-1])
    else:
        f_max = 0.0
        t_b = 0.0

    total_impulse = float(arr["imp"][-1]) if arr["imp"].size else 0.0
    m_p = float(arr["mp"][0] - arr["mp"][-1]) if arr["mp"].size else 0.0
    f_avg = total_impulse / t_b if t_b > 0 else 0.0
    isp = total_impulse / (m_p * G0) if m_p > 0 else 0.0

    # quasi-steady validity - uses the free (combustion-chamber) volume at ignition
    a_t0 = nozzle.throat_area
    free_volume_0 = max(chamber_volume - grain.initial_volume(), 1e-9)
    tau_c = free_volume_0 / (propellant.c_star_effective * a_t0)
    if t_b > 0 and tau_c / t_b > 0.01:
        warns.append(make("WARN_QUASI_STEADY_INVALID",
                          ratio=round(tau_c / t_b, 4), tau_c=round(tau_c, 4)))

    # L* and erosive burning (min J = min port area / throat area over the burn)
    lstar_mm = free_volume_0 / a_t0 * 1000.0
    if not (lstar_range_mm[0] <= lstar_mm <= lstar_range_mm[1]):
        warns.append(make("WARN_LSTAR_OUT_OF_RANGE", lstar_mm=round(lstar_mm, 1),
                          low=lstar_range_mm[0], high=lstar_range_mm[1]))
    if arr["ap"].size and arr["at"].size:
        j = arr["ap"] / arr["at"]
        j_min = float(j.min())
    else:
        j_min = math.inf
    if j_min < 1.5:
        warns.append(make("WARN_EROSIVE_BURNING_CRITICAL", j_min=round(j_min, 2)))
    elif j_min < 2.0:
        warns.append(make("WARN_EROSIVE_BURNING", j_min=round(j_min, 2)))

    # MEOP - always the erosionless peak
    if meop_pa is not None and p_max_noero > meop_pa:
        warns.append(make("WARN_MEOP_EXCEEDED",
                          p_max_bar=round(p_max_noero / 1e5, 2),
                          meop_bar=round(meop_pa / 1e5, 2)))

    warns += nozzle.validate(p_max_noero or 1e6, ambient_pressure, propellant.gamma)
    warns += grain.validate()

    designation = nar_designation(total_impulse, f_avg)
    summary = {
        "total_impulse": total_impulse,
        "average_thrust": f_avg,
        "peak_thrust": f_max,
        "burn_time": t_b,
        "peak_pressure_no_erosion_bar": p_max_noero / 1e5,
        "peak_pressure_bar": p_max / 1e5,
        "specific_impulse": isp,
        "propellant_mass": m_p,
        "min_j": j_min if math.isfinite(j_min) else None,
        "lstar_mm": lstar_mm,
        "designation": designation,
        "class_letter": designation[0] if designation else None,
        "dt_used": dt_used,
        "converged": converged,
    }

    return BallisticsResult(
        time=arr["time"],
        chamber_pressure=arr["p"],
        chamber_pressure_no_erosion=arr["p_noero"],
        thrust=arr["F"],
        burn_rate=arr["rb"],
        kn=arr["kn"],
        burn_area=arr["ab"],
        throat_area=arr["at"],
        port_area=arr["ap"],
        mass_flow=arr["mdot"],
        cumulative_impulse=arr["imp"],
        propellant_mass=arr["mp"],
        web=arr["web"],
        warnings=dedupe(warns),
        summary=summary,
        converged=converged,
        dt_used=dt_used,
    )


# --- NAR / Tripoli motor designation --------------------------------------

_NAR_UPPER_BOUNDS: list[tuple[str, float]] = [
    ("A", 2.5), ("B", 5), ("C", 10), ("D", 20), ("E", 40), ("F", 80), ("G", 160),
    ("H", 320), ("I", 640), ("J", 1280), ("K", 2560), ("L", 5120), ("M", 10240),
    ("N", 20480), ("O", 40960),
]


def nar_class_letter(total_impulse: float) -> str:
    """NAR impulse class letter for a total impulse [N*s]."""
    if total_impulse <= 1.25:
        return "-"
    for letter, upper in _NAR_UPPER_BOUNDS:
        if total_impulse <= upper:
            return letter
    # beyond O: keep going alphabetically
    letter_ord = ord("O")
    upper = 40960.0
    while total_impulse > upper:
        upper *= 2
        letter_ord += 1
    return chr(letter_ord)


def nar_designation(total_impulse: float, average_thrust: float) -> str:
    """e.g. ``"J240"`` - class letter + rounded average thrust [N]."""
    if total_impulse <= 0:
        return ""
    return f"{nar_class_letter(total_impulse)}{round(average_thrust)}"
