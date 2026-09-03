"""Grain geometries.

Import this package for its side effect of registering the built-in geometries
(BATES, tubular, end-burner). Add a geometry by subclassing
:class:`core.grains.base.GrainGeometry` and decorating it with ``@register_grain``;
no core engine code changes.
"""

from core.grains import bates, endburner, tubular  # noqa: F401  (registration side effect)
from core.grains.base import (  # noqa: F401
    GrainGeometry,
    available_grains,
    make_grain,
    register_grain,
)
