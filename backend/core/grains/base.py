"""Abstract grain geometry + registry.

Every geometry exposes burn area, remaining volume, port area and total web as a
function of the burnt web distance ``x`` [m] (0 at ignition, ``web_thickness()`` at
burnout). All lengths/areas SI.

Registry
--------
``@register_grain("bates")`` adds a class under a string key. ``make_grain(key, **kw)``
builds one. ``available_grains()`` lists keys. The API/UI never import concrete
classes, only these three functions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from core.warnings import Warning

_REGISTRY: dict[str, type[GrainGeometry]] = {}


def register_grain(key: str) -> Callable[[type[GrainGeometry]], type[GrainGeometry]]:
    """Class decorator: register a geometry under ``key``."""

    def deco(cls: type[GrainGeometry]) -> type[GrainGeometry]:
        if key in _REGISTRY:
            raise KeyError(f"grain geometry {key!r} already registered")
        cls.registry_key = key
        _REGISTRY[key] = cls
        return cls

    return deco


def available_grains() -> list[str]:
    return sorted(_REGISTRY)


def make_grain(key: str, **kwargs) -> GrainGeometry:
    if key not in _REGISTRY:
        raise KeyError(f"unknown grain geometry {key!r}; have {available_grains()}")
    return _REGISTRY[key](**kwargs)


class GrainGeometry(ABC):
    """Base class for all grain geometries."""

    registry_key: str = ""

    # --- required surface -------------------------------------------------

    @abstractmethod
    def burn_area(self, web: float) -> float:
        """Instantaneous burning surface area [m^2] at burnt web distance ``web`` [m]."""

    @abstractmethod
    def volume(self, web: float) -> float:
        """Remaining solid propellant volume [m^3] at ``web``."""

    @abstractmethod
    def port_area(self, web: float) -> float:
        """Minimum free-flow cross-section (port) [m^2] at ``web``."""

    @abstractmethod
    def web_thickness(self) -> float:
        """Total burnable web [m] (burn ends when x reaches this)."""

    @abstractmethod
    def outer_diameter(self) -> float:
        """Overall grain outer diameter [m] (drives case inner-diameter fit)."""

    @abstractmethod
    def envelope_length(self) -> float:
        """Axial length of the fuel stack including inter-segment gaps [m]."""

    @abstractmethod
    def cross_section_svg(self, web: float) -> str:
        """Transverse cross-section as an SVG ``<g>`` fragment (viewBox 0 0 100 100)."""

    @abstractmethod
    def validate(self) -> list[Warning]:
        """Geometry-intrinsic warnings (progressive burn, oversized core, ...)."""

    # --- shared helpers -------------------------------------------------

    def initial_volume(self) -> float:
        return self.volume(0.0)

    def propellant_mass(self, density: float, web: float = 0.0) -> float:
        """Remaining propellant mass [kg] = density * volume(web)."""
        return density * self.volume(web)

    def kn(self, web: float, throat_area: float) -> float:
        """Klemmung K_n = A_b / A_t at ``web`` for a given throat area [m^2]."""
        return self.burn_area(web) / throat_area

    def volume_loading(self, chamber_volume: float) -> float:
        """Fraction of the chamber filled by solid propellant at ignition."""
        return self.initial_volume() / chamber_volume

    def sliver_volume(self) -> float:
        """Propellant still unburnt when the thinnest web is consumed [m^3]."""
        return max(self.volume(self.web_thickness()), 0.0)

    def to_dict(self) -> dict:
        """Serialisable parameter dump (concrete classes override with real fields)."""
        return {"type": self.registry_key}
