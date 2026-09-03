"""Pure physics core for KNSB solid rocket motor design.

This package must not import FastAPI, SQLAlchemy, HTTP libraries or anything web/DB
related. Everything here is plain functions + dataclasses so the engine can be tested
in isolation and later packaged as a desktop/CLI tool.

All internal quantities are SI: metre, kilogram, second, pascal, newton, kelvin.
Unit conversion happens only at the I/O boundary (see :mod:`core.units`).
"""

__version__ = "0.1.0"
