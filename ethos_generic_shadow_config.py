"""Default-disabled configuration for future generic shadow observation.

These entries describe no enforcement settings.  Enabling a future stream must
remain a separately authorized integration step; importing this module has no
side effects and activates no regulator.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ShadowConfiguration:
    regulator: str
    enabled: bool = False
    storage_root: Path = Path("evidence/generic_shadow")

    def __post_init__(self) -> None:
        if self.regulator not in {"wrath", "gluttony", "lust"}:
            raise ValueError("unsupported generic shadow regulator")
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be boolean")


SHADOW_CONFIGURATIONS = {
    "wrath": ShadowConfiguration("wrath"),
    "gluttony": ShadowConfiguration("gluttony"),
    "lust": ShadowConfiguration("lust"),
}


def configured_shadow(regulator: str, *, enabled: bool, storage_root: Path | None = None) -> ShadowConfiguration:
    """Return one explicitly requested shadow-only configuration.

    This does not mutate the default-disabled registry or start any runner.
    """
    default = SHADOW_CONFIGURATIONS.get(regulator)
    if default is None:
        raise ValueError("unsupported generic shadow regulator")
    return ShadowConfiguration(regulator, enabled=enabled, storage_root=storage_root or default.storage_root)
