"""Inverse design / mission solver (Section 6).

Given a mission (dry mass, body diameter, target apogee, launch constraints and the
3D-printed case the team already has) find BATES motors that reach it.

Decision vector ``x`` = [outer_diameter, core_diameter, segment_length,
segment_count, throat_diameter] (segment_count rounded to an int inside the
evaluator). Objective: relative apogee error. Constraints (Section 6) enter as
penalty terms: MEOP, FoS >= 2, J_min >= 2, rail-exit velocity, max acceleration,
L* range, and geometry (d < D_o, L_s >= d).

Search: ``differential_evolution`` (bounded, small population) then a Nelder-Mead
polish on the incumbent, inside a wall-clock budget. Always returns the best found;
if nothing is feasible it names the binding constraint and a one-click numeric
suggestion (constraint-relaxation scan).

``solve_mission`` is a top-level picklable function so the API can run it in a
``ProcessPoolExecutor`` (Section 12.2).
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

import numpy as np

from core.assembly import BulkheadSpec, CaseSpec, LinerSpec, MotorAssembly
from core.ballistics import simulate
from core.flight import FlightInput, simulate_flight
from core.grains.bates import BatesGrain
from core.materials import PrintMethod, load_case_material, load_liner_material
from core.nozzle import Nozzle
from core.propellant import load_propellant
from core.structure import analyse_structure
from core.thermal import analyse_thermal

_UNCERTAINTY = 0.18  # +/- band on the apogee estimate (spec: typically 15-25 %)


@dataclass
class MissionInput:
    dry_mass: float
    body_diameter: float
    target_apogee: float
    drag_coefficient: float = 0.55
    rail_length: float = 2.0
    launch_altitude: float = 0.0
    max_accel_g: float = 15.0
    min_rail_exit_velocity: float = 20.0
    case_inner_diameter: float = 0.075
    case_wall_thickness: float = 0.004
    case_material_id: str = "pa12"
    print_method: str = "sls"
    liner_material_id: str = "kraft_phenolic"
    liner_thickness: float = 0.003
    bulkhead_thickness: float = 0.010
    propellant_id: str = "knsb"
    meop_bar: float = 40.0
    ambient_pressure: float = 101_325.0
    lstar_range_mm: tuple[float, float] = (250.0, 1000.0)
    time_budget_s: float = 30.0


@dataclass
class MotorCandidate:
    outer_diameter: float
    core_diameter: float
    segment_length: float
    segment_count: int
    throat_diameter: float
    designation: str = ""
    apogee: float = 0.0
    apogee_low: float = 0.0
    apogee_high: float = 0.0
    peak_pressure_bar: float = 0.0
    fos: float = 0.0
    min_j: float = 0.0
    rail_exit_velocity: float = 0.0
    max_accel_g: float = 0.0
    thrust_to_weight: float = 0.0
    propellant_mass: float = 0.0
    motor_mass: float = 0.0
    total_length: float = 0.0
    total_impulse: float = 0.0
    burn_time: float = 0.0
    feasible: bool = False
    penalty: float = 1e9
    warnings: list[dict] = field(default_factory=list)
    thrust_curve: list[list[float]] = field(default_factory=list)  # [[t, F], ...] mini plot

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MissionResult:
    feasible: bool
    candidates: list[dict]
    binding_constraint: str | None = None
    suggestion: dict | None = None
    iterations: int = 0
    elapsed_s: float = 0.0
    uncertainty_fraction: float = _UNCERTAINTY
    note_key: str = "info.flight.scope"

    def to_dict(self) -> dict:
        return {
            "feasible": self.feasible,
            "candidates": self.candidates,
            "binding_constraint": self.binding_constraint,
            "suggestion": self.suggestion,
            "iterations": self.iterations,
            "elapsed_s": self.elapsed_s,
            "uncertainty_fraction": self.uncertainty_fraction,
            "note_key": self.note_key,
        }


def _bounds(cfg: MissionInput) -> list[tuple[float, float]]:
    d_max = cfg.case_inner_diameter - 2.0 * cfg.liner_thickness - 0.001
    return [
        (0.35 * d_max, d_max),                 # outer_diameter
        (0.004, 0.6 * d_max),                  # core_diameter
        (0.02, 0.35),                          # segment_length
        (1.0, 6.0),                            # segment_count (rounded)
        (0.004, 0.5 * cfg.case_inner_diameter),  # throat_diameter
    ]


def _evaluate(x: np.ndarray, cfg: MissionInput, *, fast: bool) -> MotorCandidate:
    d_o, d_core, l_s, n_seg_f, d_t = [float(v) for v in x]
    n_seg = int(round(n_seg_f))
    cand = MotorCandidate(d_o, d_core, l_s, n_seg, d_t)

    # hard geometry gates -> large penalty, cheap to reject
    if d_core >= d_o or l_s < d_core or n_seg < 1:
        cand.penalty = 5e6 + abs(d_core - d_o) + abs(l_s - d_core)
        return cand

    try:
        grain = BatesGrain(d_o, d_core, l_s, segment_count=n_seg, segment_spacing=0.003)
        nozzle = Nozzle(throat_diameter=d_t, expansion_ratio=5.0, throat_length=0.5 * d_t)
        prop = load_propellant(cfg.propellant_id)
        case_mat = load_case_material(cfg.case_material_id)
        liner = LinerSpec(load_liner_material(cfg.liner_material_id), cfg.liner_thickness)
        assembly = MotorAssembly(
            grain=grain, propellant=prop, nozzle=nozzle,
            case=CaseSpec(case_mat, cfg.case_inner_diameter, cfg.case_wall_thickness),
            bulkhead=BulkheadSpec(case_mat, cfg.bulkhead_thickness),
            liner=liner,
        )
        meop_pa = cfg.meop_bar * 1e5
        ball = simulate(
            grain, prop, nozzle,
            dt=0.002 if fast else 0.001,
            ambient_pressure=cfg.ambient_pressure,
            chamber_volume=assembly.free_volume(0.0) + grain.initial_volume(),
            meop_pa=meop_pa,
            lstar_range_mm=cfg.lstar_range_mm,
            check_convergence=not fast,
        )
        s = ball.summary
        struct = analyse_structure(assembly, s["peak_pressure_no_erosion_bar"] * 1e5,
                                   print_method=PrintMethod(cfg.print_method))
        therm = analyse_thermal(assembly, prop.flame_temperature, s["burn_time"])
        flight = simulate_flight(
            ball,
            FlightInput(
                dry_mass=cfg.dry_mass + assembly.inert_mass(),
                body_diameter=cfg.body_diameter,
                drag_coefficient=cfg.drag_coefficient,
                rail_length=cfg.rail_length,
                launch_altitude=cfg.launch_altitude,
                max_accel_g=cfg.max_accel_g,
            ),
        )
    except Exception:  # pragma: no cover - defensive, optimiser explores bad regions
        cand.penalty = 4e6
        return cand

    m_p = s["propellant_mass"]
    motor_mass = assembly.total_mass(0.0)
    launch_mass = cfg.dry_mass + motor_mass
    twr = s["average_thrust"] / (launch_mass * 9.80665) if launch_mass > 0 else 0.0

    cand.designation = s["designation"]
    cand.apogee = flight.apogee
    cand.apogee_low = flight.apogee * (1.0 - _UNCERTAINTY)
    cand.apogee_high = flight.apogee * (1.0 + _UNCERTAINTY)
    cand.peak_pressure_bar = s["peak_pressure_no_erosion_bar"]
    cand.fos = struct.wall.fos
    cand.min_j = s["min_j"] or 0.0
    cand.rail_exit_velocity = flight.rail_exit_velocity
    cand.max_accel_g = flight.max_acceleration_g
    cand.thrust_to_weight = twr
    cand.propellant_mass = m_p
    cand.motor_mass = motor_mass
    cand.total_length = assembly.total_length()
    cand.total_impulse = s["total_impulse"]
    cand.burn_time = s["burn_time"]

    ds = ball.downsampled(40)
    cand.thrust_curve = [[float(t), float(f)]
                         for t, f in zip(ds.time, ds.thrust, strict=False)]

    all_warn = list(ball.warnings) + struct.warnings + therm.warnings + assembly.validate_fit()
    cand.warnings = [w.to_dict() for w in all_warn]

    # objective + constraint penalties
    apo_err = abs(flight.apogee - cfg.target_apogee) / max(cfg.target_apogee, 1.0)
    pen = apo_err
    viol = {
        "meop": max(0.0, cand.peak_pressure_bar - cfg.meop_bar) / cfg.meop_bar,
        "fos": max(0.0, 2.0 - cand.fos) / 2.0,
        "min_j": max(0.0, 2.0 - cand.min_j) / 2.0,
        "rail_exit_velocity": max(0.0, cfg.min_rail_exit_velocity - cand.rail_exit_velocity)
        / cfg.min_rail_exit_velocity,
        "max_accel_g": max(0.0, cand.max_accel_g - cfg.max_accel_g) / cfg.max_accel_g,
        "lstar": max(0.0, cfg.lstar_range_mm[0] - s["lstar_mm"],
                     s["lstar_mm"] - cfg.lstar_range_mm[1]) / cfg.lstar_range_mm[1],
        "thermal": 0.0 if therm.is_safe else 1.0,
    }
    pen += 10.0 * sum(viol.values())
    cand.penalty = pen
    cand.feasible = all(v <= 1e-6 for v in viol.values())
    cand._violations = viol  # type: ignore[attr-defined]
    return cand


def _relaxation_suggestion(cfg: MissionInput, best: MotorCandidate) -> tuple[str, dict]:
    """Name the binding constraint and a single numeric change that would clear it."""
    v = getattr(best, "_violations", {})
    if not v:
        return "unknown", {}
    key = max(v, key=v.get)
    if key == "meop":
        return "meop", {"field": "meop_bar", "current": cfg.meop_bar,
                        "suggested": round(best.peak_pressure_bar * 1.15, 1)}
    if key == "fos":
        t_mm = cfg.case_wall_thickness * 1e3
        return "fos", {"field": "case_wall_thickness",
                       "current": round(t_mm, 2),
                       "suggested": round(t_mm * 2.1 / max(best.fos, 0.1), 2),
                       "unit": "mm"}
    if key == "min_j":
        return "min_j", {"field": "throat_diameter_hint",
                         "message_key": "solver.suggest.enlarge_throat_or_core"}
    if key == "rail_exit_velocity":
        return "rail_exit_velocity", {"field": "rail_length", "current": cfg.rail_length,
                                      "suggested": round(cfg.rail_length * 1.8, 2), "unit": "m"}
    if key == "max_accel_g":
        return "max_accel_g", {"field": "max_accel_g", "current": cfg.max_accel_g,
                               "suggested": round(best.max_accel_g * 1.1, 1)}
    if key == "lstar":
        return "lstar", {"field": "case_inner_diameter",
                         "message_key": "solver.suggest.resize_chamber"}
    if key == "thermal":
        return "thermal", {"field": "liner_thickness",
                           "current": round(cfg.liner_thickness * 1e3, 2),
                           "suggested": round(cfg.liner_thickness * 1e3 * 1.8, 2), "unit": "mm"}
    return key, {}


def solve_mission(cfg: MissionInput) -> MissionResult:
    """Run the solver. Picklable; safe to call inside a ProcessPoolExecutor."""
    from scipy.optimize import differential_evolution, minimize

    start = time.monotonic()
    bounds = _bounds(cfg)
    seen: list[MotorCandidate] = []
    iters = 0

    def obj(x: np.ndarray) -> float:
        nonlocal iters
        iters += 1
        c = _evaluate(np.asarray(x), cfg, fast=True)
        seen.append(c)
        return c.penalty

    budget = max(3.0, cfg.time_budget_s)

    def time_up(*_a, **_k) -> bool:
        # differential_evolution stops when the callback returns True
        return time.monotonic() - start > 0.7 * budget

    try:
        differential_evolution(
            obj, bounds, maxiter=30, popsize=10, tol=1e-3, seed=12345,
            mutation=(0.4, 1.0), recombination=0.8, polish=False,
            init="sobol", callback=time_up,
        )
    except Exception:  # pragma: no cover
        pass

    # Nelder-Mead polish on the incumbent, respecting the time budget
    if seen and time.monotonic() - start < budget:
        incumbent = min(seen, key=lambda c: c.penalty)
        x0 = np.array([incumbent.outer_diameter, incumbent.core_diameter,
                       incumbent.segment_length, incumbent.segment_count,
                       incumbent.throat_diameter])
        try:
            minimize(obj, x0, method="Nelder-Mead",
                     options={"maxiter": 120, "xatol": 1e-4, "fatol": 1e-4})
        except Exception:  # pragma: no cover
            pass

    elapsed = time.monotonic() - start

    # re-score the most promising unique points at full accuracy
    uniq: dict[tuple, MotorCandidate] = {}
    for c in sorted(seen, key=lambda c: c.penalty)[:12]:
        key = (round(c.outer_diameter, 4), round(c.core_diameter, 4),
               round(c.segment_length, 4), c.segment_count, round(c.throat_diameter, 4))
        if key not in uniq:
            uniq[key] = _evaluate(
                np.array([c.outer_diameter, c.core_diameter, c.segment_length,
                          c.segment_count, c.throat_diameter]), cfg, fast=False)
    scored = sorted(uniq.values(), key=lambda c: c.penalty)
    feasible = [c for c in scored if c.feasible]

    if feasible:
        lightest = min(feasible, key=lambda c: c.motor_mass)
        safest = min(feasible, key=lambda c: c.peak_pressure_bar)
        closest = min(feasible, key=lambda c: abs(c.apogee - cfg.target_apogee))
        picks: list[MotorCandidate] = []
        for c in (lightest, safest, closest):
            if c not in picks:
                picks.append(c)
        for c in feasible:  # pad to 3 if the picks overlapped
            if len(picks) >= 3:
                break
            if c not in picks:
                picks.append(c)
        return MissionResult(
            feasible=True,
            candidates=[c.to_dict() for c in picks[:3]],
            iterations=iters,
            elapsed_s=round(elapsed, 2),
        )

    best = scored[0] if scored else _evaluate(np.array([b[0] for b in bounds]), cfg, fast=False)
    binding, suggestion = _relaxation_suggestion(cfg, best)
    return MissionResult(
        feasible=False,
        candidates=[best.to_dict()],
        binding_constraint=binding,
        suggestion=suggestion,
        iterations=iters,
        elapsed_s=round(elapsed, 2),
    )
