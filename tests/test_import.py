"""Smoke test: the package and every submodule import cleanly."""

import importlib

import pytest

SUBMODULES = [
    "io",
    "calibration",
    "simulation",
    "spectral",
    "baseline",
    "conformal",
    "fairness",
    "fusion",
    "evaluation",
]


def test_package_imports():
    import hemosight

    assert hemosight.__version__


@pytest.mark.parametrize("name", SUBMODULES)
def test_submodule_imports(name):
    module = importlib.import_module(f"hemosight.{name}")
    assert module.__doc__, f"hemosight.{name} must document what it owns"
