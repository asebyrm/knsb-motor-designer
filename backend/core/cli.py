"""Terminal entry point for the physics core (Section 15, phases 1-2 self-check).

    python -m core.cli example reference      # run the Section 13.1 reference case
    python -m core.cli examples               # list bundled examples
    python -m core.cli propellants            # list propellant YAML files
    python -m core.cli grains                 # list registered grain geometries
    python -m core.cli simulate --propellant knsb --grain bates \\
        --do 0.054 --core 0.020 --seg-len 0.09 --segments 3 \\
        --throat 0.0135 --eps 5 [--meop-bar 70]

No web or DB imports here - this must run from a bare checkout of ``core/``.
"""

from __future__ import annotations

import argparse
import sys

from core.ballistics import simulate
from core.examples import ALL_EXAMPLES, load_example
from core.grains.base import available_grains, make_grain
from core.nozzle import ErosionParams, Nozzle
from core.propellant import available_propellants, load_propellant
from core.units import bar_to_pa


def _print_result(res, name: str) -> None:
    s = res.summary
    print(f"\n=== {name} ===")
    print(f"  designation           {s['designation']}")
    print(f"  total impulse         {s['total_impulse']:.1f} N·s")
    print(f"  average thrust        {s['average_thrust']:.1f} N")
    print(f"  peak thrust           {s['peak_thrust']:.1f} N")
    print(f"  burn time             {s['burn_time']:.3f} s")
    print(f"  peak p (no erosion)   {s['peak_pressure_no_erosion_bar']:.2f} bar")
    print(f"  specific impulse      {s['specific_impulse']:.1f} s")
    print(f"  propellant mass       {s['propellant_mass'] * 1000:.1f} g")
    print(f"  min J (port/throat)   {s['min_j']}")
    print(f"  L*                    {s['lstar_mm']:.0f} mm")
    print(f"  dt used / converged   {s['dt_used']:.2e} s / {s['converged']}")
    if res.warnings:
        print("  warnings:")
        for w in res.warnings:
            print(f"    [{w.level.value:7}] {w.code}  {w.params}")
    else:
        print("  warnings:              none")


def _cmd_example(args: argparse.Namespace) -> int:
    ex = load_example(args.key)
    res = simulate(
        ex.grain, ex.propellant, ex.nozzle,
        ambient_pressure=ex.ambient_pressure,
        chamber_volume=ex.chamber_volume,
        meop_pa=ex.meop_pa,
    )
    _print_result(res, ex.name)
    if ex.note:
        print(f"\n  note: {ex.note}")
    return 0


def _cmd_simulate(args: argparse.Namespace) -> int:
    prop = load_propellant(args.propellant)
    if args.grain == "bates":
        grain = make_grain("bates", outer_diameter=args.do, core_diameter=args.core,
                           segment_length=args.seg_len, segment_count=args.segments,
                           segment_spacing=args.seg_spacing)
    elif args.grain == "tubular":
        grain = make_grain("tubular", outer_diameter=args.do, core_diameter=args.core,
                           length=args.seg_len, segment_count=args.segments)
    elif args.grain == "endburner":
        grain = make_grain("endburner", outer_diameter=args.do, length=args.seg_len)
    else:  # pragma: no cover - argparse choices guard this
        raise SystemExit(f"unknown grain {args.grain}")

    nozzle = Nozzle(
        throat_diameter=args.throat,
        expansion_ratio=args.eps,
        divergence_half_angle_deg=args.half_angle,
        efficiency=args.nozzle_eff,
        erosion=ErosionParams(enabled=args.erosion, coefficient_mm_s=args.erosion_k),
    )
    res = simulate(
        grain, prop, nozzle,
        ambient_pressure=bar_to_pa(args.ambient_bar),
        meop_pa=bar_to_pa(args.meop_bar) if args.meop_bar else None,
    )
    _print_result(res, f"{args.propellant} / {args.grain}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="core.cli", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    pe = sub.add_parser("example", help="run a bundled example motor")
    pe.add_argument("key", choices=sorted(ALL_EXAMPLES))
    pe.set_defaults(func=_cmd_example)

    sub.add_parser("examples", help="list bundled examples").set_defaults(
        func=lambda a: (print("\n".join(sorted(ALL_EXAMPLES))) or 0))
    sub.add_parser("propellants", help="list propellant YAML files").set_defaults(
        func=lambda a: (print("\n".join(available_propellants())) or 0))
    sub.add_parser("grains", help="list registered grain geometries").set_defaults(
        func=lambda a: (print("\n".join(available_grains())) or 0))

    ps = sub.add_parser("simulate", help="simulate a custom motor")
    ps.add_argument("--propellant", default="knsb")
    ps.add_argument("--grain", default="bates", choices=["bates", "tubular", "endburner"])
    ps.add_argument("--do", type=float, required=True, help="grain outer diameter [m]")
    ps.add_argument("--core", type=float, default=0.0, help="core diameter [m]")
    ps.add_argument("--seg-len", type=float, required=True,
                    help="BATES segment length / tube length / end-burner length [m]")
    ps.add_argument("--segments", type=int, default=1)
    ps.add_argument("--seg-spacing", type=float, default=0.0)
    ps.add_argument("--throat", type=float, required=True, help="throat diameter [m]")
    ps.add_argument("--eps", type=float, default=4.0, help="expansion ratio A_e/A_t")
    ps.add_argument("--half-angle", type=float, default=15.0)
    ps.add_argument("--nozzle-eff", type=float, default=0.95)
    ps.add_argument("--ambient-bar", type=float, default=1.01325)
    ps.add_argument("--meop-bar", type=float, default=0.0)
    ps.add_argument("--erosion", action="store_true")
    ps.add_argument("--erosion-k", type=float, default=0.05)
    ps.set_defaults(func=_cmd_simulate)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
