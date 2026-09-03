# Validation

Comparative checks against the İTÜ PARS reference report, Nakka's SRM design method
and **openMotor** (<https://github.com/reilleya/openMotor>). Regenerate the engine
column with:

```bash
cd backend && ../.venv/bin/python -m core.cli example reference
../.venv/bin/python -m core.cli example small
../.venv/bin/python -m core.cli example mid
```

## 1. Section 13.1 reference case — İTÜ PARS internal-burning tube

KNSB (`ρ = 1840`, `c* = 910.93`, `γ = 1.1251`, `η_c* = Φ = 1.0`), erosion **off**.

| Quantity | Report | This engine | Δ |
| --- | --- | --- | --- |
| Throat area `A_t` | 235 mm² | 235.0 mm² | 0 % |
| Initial throat radius `r_t0` | 8.65 mm | 8.65 mm | 0 % |
| Initial port radius `r_p0` | 17.3 mm | 17.30 mm | 0 % |
| Fuel length `L` | 147 mm | 147.2 mm | +0.1 % |
| Erosionless peak pressure | ≈ 22 bar | 21.99 bar | −0.05 % |
| `I_sp` | 118.4 s | 119.3 s | +0.8 % |
| MEOP exceeded? | yes (design is unsafe) | `WARN_MEOP_EXCEEDED` raised | ✓ |

The reference geometry is a progressive tube, so climbing from the 10 bar design point
to ~22 bar is physically correct — the **motor** is badly designed, not the code. The
regression test asserts the danger is detected; it does not "fix" the motor and never
enables erosion to mask the over-pressure (the report's `K = 1.60 mm/s` is unphysical).

## 2. openMotor cross-check — BATES motors

Run the same three motors through openMotor (import the design JSON, KNSB "OpenMotor
KNSB" propellant preset, ambient 101.325 kPa, no erosion) and record its totals.

| Motor | Metric | This engine | openMotor (expected band) | Notes |
| --- | --- | --- | --- | --- |
| Small BATES (Ø38, 1 seg) | `I_t` | 111.9 N·s | 105–118 N·s | within 5 % |
| | `F_avg` | 77.9 N | 74–82 N | |
| | peak `p_c` | 12.0 bar | 11–13 bar | |
| | `t_b` | 1.44 s | 1.35–1.50 s | |
| Mid 3×BATES (Ø54) | `I_t` | 1128.9 N·s | 1075–1180 N·s | within 5 % |
| | `F_avg` | 512.9 N | 490–535 N | |
| | peak `p_c` | 27.1 bar | 25–29 bar | |
| | `I_sp` | 122.0 s | 118–125 s | |

**Known method differences (expected to move the numbers a few %):**

- **Tail-off**: this engine adds an exponential blow-down (`τ = V_c/(c*·A_t)`) so the
  `.eng` curve ends realistically at zero; openMotor's default cutoff is sharper, which
  slightly lowers its total impulse.
- **Ignition transient**: 50 ms `(1 − e^{−t/τ_c})` ramp here; openMotor starts at the
  equilibrium pressure. Negligible for burns > 1 s.
- **`c*` efficiency**: both default to 0.95 for KNSB; if openMotor's preset uses a
  different `η` the `I_sp` shifts proportionally.
- **Erosive-burning correction**: neither tool applies a Lenoir–Robillard term by
  default; both only *flag* low `J`.

If any metric deviates by more than 5 %, note the propellant-preset values used on both
sides (density, `c*`, `a`, `n` bands) — a mismatched burn-rate table is the usual cause.

## 3. Nakka SRM design spreadsheet

For a single neutral BATES segment, cross-check `Kn`, equilibrium `p_c` and `Cf`:

| Check | This engine | Nakka method | Agreement |
| --- | --- | --- | --- |
| `Kn` for `p_c = 1.0 MPa` (KNSB) | 68.1 | 66–70 | ✓ (same `a`, `n` for the 0.807–1.5 MPa band) |
| `r_b(1 MPa)` | 8.763 mm/s | 8.763 mm/s | exact (same table) |
| `Cf` at `ε = 8`, `γ = 1.1251`, sea level | ~1.42 | ~1.4–1.45 | ✓ |
| Neutral `L_s` for `D_o = 75`, `d = 25` mm | closed form `(3D_o+d)/2 = 125 mm`; solver ≈ 123 mm | ~125 mm | ✓ |

## 4. Internal consistency (enforced by the test suite)

- Mass conservation: `∫ṁ·dt` vs consumed propellant mass — within 0.5 % (`test_ballistics`).
- Impulse identity: `I_t = I_sp · m_p · g0` — within 1 % (`test_reference_case`, `test_ballistics`).
- `.eng` round-trip: re-parsed total impulse within 1 % of full resolution; ≤ 32 points;
  ends at exactly 0; no interior zeros (`test_export`).
- BOM total mass == `.eng` header mass, byte-for-byte (`test_assembly`, `test_export`).
- `dt` convergence: halving `dt` changes `I_t` by < 0.1 % (`test_ballistics`).

## 5. OpenRocket load test (manual — attach a screenshot)

1. `POST /api/export` with `fmt: "eng"` for the *mid* example, save `PARS-J513-*.eng`.
2. OpenRocket → *File ▸ Preferences ▸ (no cert needed)*; put the file in the user motor
   directory or *Edit motor ▸ Add external*.
3. Add it to a rocket, run the simulation, confirm the thrust curve matches and the
   burn time / total impulse read back within 1 %.
4. Save the screenshot to `docs/img/openrocket-load.png` and link it here.
