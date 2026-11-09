"""Verify native launch configuration can be constructed in the Jazzy environment."""

import importlib.util
from pathlib import Path

from launch import LaunchDescription


def test_native_launch_description_constructs() -> None:
    """Launch description should contain the two runtime components."""
    path = Path(__file__).resolve().parents[1] / 'launch' / 'native_health.launch.py'
    spec = importlib.util.spec_from_file_location('native_health_launch', path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    description = module.generate_launch_description()
    assert isinstance(description, LaunchDescription)
    assert len(description.entities) == 2
