"""Launch smoke: external surveillance monitor stays independent of robot bringup."""

import importlib.util
from pathlib import Path

from launch import LaunchDescription


def test_surveillance_launch_description_constructs() -> None:
    """Construct read-only adapter plus aggregator without Gazebo/nav actions."""
    path = Path(__file__).resolve().parents[1] / "launch" / "surveillance_health.launch.py"
    spec = importlib.util.spec_from_file_location("surveillance_health_launch", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    description = module.generate_launch_description()
    assert isinstance(description, LaunchDescription)
    assert len(description.entities) == 4  # two arguments and two ROS nodes
