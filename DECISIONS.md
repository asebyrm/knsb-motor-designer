# Design Decisions

One line per decision made where the specification was ambiguous or silent.
Reviewed once at the end of the project.

## Environment / tooling

- **Python 3.11.15** used via `.venv` (spec asks 3.11+); system default is 3.10, an isolated venv avoids touching it.
- **Package layout**: `backend/` is the Python project root (`pyproject.toml` lives there); `core`, `services`, `api`, `models` are top-level importable packages, matching Section 4's `python -m core.cli`.

## Physics core

- **Equilibrium density term**: the spec formula `p_c = (rho * eta * a_SI * c_star * K_n)^(1/(1-n))`
  uses `rho` = actual cast density (`density_ideal * density_factor`), not ideal density.
- **Multiple self-consistent roots** (negative-n bands): pick the locally stable crossing
  (dR/dp < 0); among those the lowest pressure. Falls back to Brent on the residual otherwise.
- **Extrapolation warning** is only raised for the quasi-steady phase (t >= 50 ms ignition
  window, before burnout) — the ignition ramp and tail-off legitimately dip below table range
  and would otherwise always trip it.
- **Burn time `t_b`** defined NAR-style: ignition to the last instant thrust >= 5% of peak.
  `F_avg = I_t / t_b`.
- **Reference case D_o = 85.8 mm** (Section 13.1 gives A_t, r_p0, L but not the tube OD).
  Chosen so the correctly-progressive tube peaks at 21.99 bar, matching the İTÜ PARS report's
  ~22 bar. Reference MEOP set to 15 bar so `WARN_MEOP_EXCEEDED` fires as the test requires.
- **`estimate_chamber_volume`** (used only when no assembly is supplied) = OD bounding cylinder
  over the grain envelope * 1.05 ullage. L* and tau_c use the *free* volume
  (chamber_volume - grain solid volume at ignition).
- **Tail-off** cut off when chamber pressure drops below 2% of the burnout pressure; a final
  (t, 0) sample is appended so `.eng` export ends exactly at zero thrust.
- **Cf during tail-off**: chamber pressure floored at 1.2 * p_ambient for the Cf evaluation
  only (avoids a divergent momentum term), thrust still scales with the real decaying p_c.
- **`ErosionParams` default** K = 0.05 mm/s, m = 0.8 (graphite mid-range); `WARN_UNREALISTIC_EROSION`
  at K > 0.3 mm/s per Section 5.3.

## Analysis layer (Phase 2)

- **Case-material strength knock-down**: each material carries a baseline
  `print_direction_factor`; the structural analysis overrides it with the chosen print
  method's factor (FDM 0.5, SLS 0.9, machined 1.0) per Section 5.6.
- **Thick-wall Von Mises** uses the full 3-principal-stress form with radial stress -p at the
  bore; thin-wall keeps the 2-term plane-stress form (radial stress negligible).
- **Fastener sizing**: default bolt Ø4 mm, shear strength 200 MPa (~class-4.8 steel, 0.6·Sy),
  single shear, minimum 2 bolts, target FoS = wall min FoS (2.0).
- **Liner is mandatory** whenever the case is structural: no liner ⇒ `WARN_NO_LINER` (danger)
  and `is_safe = False`, matching Section 5.7.
- **Semi-infinite soak** uses the *un-ablated* remaining liner thickness as the conduction
  path and holds the liner inner face at the full flame temperature (conservative).
- **1-DOF flight**: ISA troposphere only (≤11 km), RK4 dt = 0.01 s, drag uses `v*|v|` so it
  always opposes motion; integration stops at first apogee after burnout.
- **Apogee uncertainty band** reported as ±18 % (mid of the spec's "typically 15-25 %");
  every mission candidate reports `apogee_low`/`apogee_high`, never a bare number.
- **Solver**: `differential_evolution` (maxiter 30, popsize 10, Sobol init) with a wall-clock
  callback that stops at 70 % of the time budget, then a Nelder-Mead polish; fast passes use
  dt = 2 ms and skip dt-convergence, the shortlist is re-scored at dt = 1 ms.
- **`estimate_chamber_volume`** stays the ballistics fallback; the solver and API pass the real
  `assembly.free_volume(0) + grain.initial_volume()` as `chamber_volume`.
- **BOM TOTAL row** = sum of the *rounded* per-part masses (not `round(total)`), so the table is
  self-consistent to the last digit and `.eng`/`.rse` take their header mass from
  `assembly.bom_total_mass()` verbatim (acceptance criterion 11).
