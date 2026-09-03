# Physics reference

Every equation the engine uses, with units and sources. SI throughout the core
(`m, kg, s, Pa, N, K`); unit conversion happens only at the I/O boundary
(`core/units.py`).

## Sources

- Richard Nakka, *Solid Propellant Rocket Motor Design and Testing* — burn-rate data,
  BATES geometry, `Kn` method, `c*` and `Cf` treatment.
  <https://www.nakka-rocketry.net/>
- G. P. Sutton & O. Biblarz, *Rocket Propulsion Elements*, 9th ed. — nozzle theory,
  thrust coefficient, expansion, separation.
- ThrustCurve.org, *RASP `.eng` file format*. <https://www.thrustcurve.org/info/raspformat.html>
- İTÜ PARS Rocket Team internal-ballistics report — the Section 13.1 regression case
  (KNSB internal-burning tube, `A_t = 235 mm²`, `r_p0 = 17.3 mm`, `L = 147 mm`,
  erosionless peak ≈ 22 bar). The report's `K = 1.60 mm/s` throat-erosion "fix" is
  **not** reproduced; erosion is never a pressure-limiting device (spec Section 5.3).

## Propellant — piecewise Saint-Robert burn rate (`core/propellant.py`)

The tables give `r_b` in **mm/s** and `p_c` in **MPa**:

```
r_b[mm/s] = a · (p_c[MPa])^n
```

The core works in Pa, so the one conversion (done once, in `Propellant.burn_rate`):

```
r_b[m/s] = a · (p_c[Pa] / 1e6)^n / 1000
```

Outside the tabulated pressure band the law is extrapolated and the result is tagged
`WARN_EXTRAPOLATED_BURN_RATE`.

### Equilibrium chamber pressure

Mass balance between generation and nozzle exhaust:

```
ρ_p · A_b · r_b(p_c) = p_c · A_t / c*_eff        c*_eff = η_c* · c*_ideal
```

Per piecewise row this closes to

```
p_eq = (ρ_p · η_c* · a_SI · c*_ideal · K_n)^(1 / (1 − n))
```

Because `(a, n)` depend on pressure, the correct row is the **self-consistent** one:
solve each row, accept the result that lands inside that row's band. Where the
negative-`n` bands admit multiple crossings, the locally **stable** one
(`dR/dp < 0`, `R(p) = ρ_p · c*_eff · K_n · r_b(p) − p`) at the lowest pressure is
chosen. If no row is self-consistent, `scipy.optimize.brentq` finds the root of
`R(p)` directly.

## Grain geometry (`core/grains/`)

`x` = burnt web distance [m]. `A_b(x)`, `V(x)`, `A_port(x)`, `w = web_thickness()`.

### BATES (default, recommended)

```
core_r = d/2 + x
A_b(x) = N · [ 2π·core_r·(L_s − 2x)  +  2π·((D_o/2)² − core_r²) ]      (each term ≥ 0)
w      = min( (D_o − d)/2 , L_s/2 )
```

Neutral segment length (solved numerically, seed `L_s = (3·D_o + d)/2`):
`suggest_neutral_segment_length(D_o, d)` makes `A_b(0) = A_b(w)`.

### Tubular (internal-burning tube)

Ends and OD inhibited; `A_b = N·2π·r_p·L`, `r_p = d/2 + x`. Inherently **progressive**
→ always `WARN_PROGRESSIVE_GEOMETRY`.

### End-burner

`A_b = π·(D_o/2)²`, constant (neutral) but long burn and high `L/D` heat soak →
`WARN_ENDBURNER_THERMAL_SOAK`.

## Nozzle (`core/nozzle.py`)

Exit Mach from the area–Mach relation (supersonic branch):

```
A_e/A_t = (1/M)·[ (2/(γ+1))·(1 + (γ−1)/2·M²) ]^((γ+1)/(2(γ−1)))
```

Exit pressure isentropically: `p_e/p_c = (1 + (γ−1)/2·M_e²)^(−γ/(γ−1))`.

```
Cf_ideal = √( (2γ²/(γ−1))·(2/(γ+1))^((γ+1)/(γ−1))·(1 − (p_e/p_c)^((γ−1)/γ)) )
           + (p_e − p_a)/p_c · ε
λ_div    = (1 + cos α) / 2
Cf       = λ_div · η_nozzle · Cf_ideal
F        = Cf · p_c · A_t
```

- **Separation** (Summerfield): `p_e < 0.4·p_a` → `WARN_FLOW_SEPARATION`.
- **Optimum ε**: the value giving `p_e = p_a` at the design pressure.
- **Throat erosion** (default OFF): `dr_t/dt = K·(p_c[MPa])^m`, graphite `K ≈ 0.02–0.1 mm/s`,
  `m ≈ 0.8`. `K > 0.3 mm/s` → `WARN_UNREALISTIC_EROSION`. **MEOP is always judged on the
  erosionless curve.**

## Quasi-steady time march (`core/ballistics.py`, Section 5.4)

```
x = 0 ; r_t = r_t0 ; t = 0 ; I_t = 0
while x < w and t < t_max:
    A_b  = grain.burn_area(x)
    A_t  = π·r_t²
    K_n  = A_b / A_t
    p_c  = solve_equilibrium_pressure(K_n)          # erosion-influenced A_t
    r_b  = propellant.burn_rate(p_c)
    Cf   = nozzle.thrust_coefficient(p_c, p_a)
    F    = Cf · p_c · A_t
    ṁ    = p_c · A_t / c*_eff
    I_t += F · dt
    x   += r_b · dt
    r_t += erosion_rate(p_c) · dt
    t   += dt
```

- **dt convergence**: run at `dt` and `dt/2`; if `|ΔI_t|/I_t > 0.1 %` halve and repeat
  (≤ 4 times) → else `WARN_CONVERGENCE_NOT_REACHED`.
- **Ignition transient**: first 50 ms, `p_c ← p_eq·(1 − e^(−t/τ_c))`, `τ_c = V_c/(c*·A_t)`.
- **Tail-off**: after web-out, `p(t) = p_burnout·e^(−(t−t_bo)/τ)`; a final `(t, 0)` sample
  is appended so `.eng` ends at exactly zero.
- **Quasi-steady validity**: `τ_c/t_b > 0.01` → `WARN_QUASI_STEADY_INVALID`.
- **Erosive burning**: `J = A_port/A_t`; `J_min < 2` → `WARN_EROSIVE_BURNING`,
  `< 1.5` → `WARN_EROSIVE_BURNING_CRITICAL` (design unsafe).
- **`L* = V_c/A_t`** (free volume); outside 250–1000 mm for KNSB → `WARN_LSTAR_OUT_OF_RANGE`.

## Structure (`core/structure.py`, Section 5.6)

Thin wall (`t/r_i ≤ 0.1`):

```
σ_hoop  = p·r_i/t          σ_axial = p·r_i/(2t)
σ_vm    = √(σ_hoop² − σ_hoop·σ_axial + σ_axial²)
```

Thick wall (Lamé, evaluated at the bore):

```
σ_hoop  =  p·(r_o² + r_i²)/(r_o² − r_i²)
σ_axial =  p·r_i²/(r_o² − r_i²)
σ_radial = −p
σ_vm    =  √(½·[(σ_hoop−σ_axial)² + (σ_axial−σ_radial)² + (σ_radial−σ_hoop)²])
```

```
σ_allow = tensile_strength · strength_factor      # FDM 0.5 / SLS 0.9 / machined 1.0
FoS     = σ_allow / σ_vm                          # < 2.0 ⇒ UNSAFE, export locked
```

MEOP = erosionless peak pressure. Closure blow-out: `F_axial = p·π·r_i²`; shear bolts
each carry `τ_allow·π·d²/4`, minimum count `⌈F_axial·FoS / per_bolt⌉` (≥ 2).

## Thermal (`core/thermal.py`, Section 5.7)

Semi-infinite solid, liner inner face held at `T_flame`:

```
T(x, t) = T_i + (T_s − T_i)·erfc( x / (2·√(α·t)) )        α = k/(ρ·c_p)
```

`x` = un-ablated remaining liner thickness, `t` = burn time. `T_case > max_service_temp`
→ `WARN_THERMAL_LIMIT`. No liner on a structural case → `WARN_NO_LINER` (UNSAFE).
Recommended liner thickness = `min_thickness + f·ablation_rate·t_b`, `f = 1.5` for
`t_b > 3 s`.

## 1-DOF flight (`core/flight.py`, Section 6.1)

```
m(t) = m_dry + m_prop_remaining(t)
D    = ½·ρ_air(h)·v·|v|·Cd·A
a    = (F(t) − D)/m − g
```

ISA troposphere (≤ 11 km), RK4 `dt = 0.01 s`, integrated to first apogee after
burnout. Reported apogee is always a band (`±18 %`, spec says "typically 15–25 %").

## Motor designation

NAR impulse class from total impulse `I_t` [N·s] (upper bounds):
`A 2.5, B 5, C 10, D 20, E 40, F 80, G 160, H 320, I 640, J 1280, K 2560, L 5120,
M 10240, N 20480, O 40960` (doubling beyond). Format `{letter}{round(F_avg)}`, e.g.
`J240`; an optional user prefix gives `PARS-J240`.
