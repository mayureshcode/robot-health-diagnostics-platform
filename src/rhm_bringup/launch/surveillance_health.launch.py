"""Read-only health integration for a separately running ROS 2 surveillance robot."""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    """Start surveillance topic adapter and shared aggregator; no robot control."""
    profile_default = os.environ.get("RHM_PROFILE_PATH", "")
    if not profile_default:
        profile_default = PathJoinSubstitution([
            FindPackageShare("rhm_surveillance_adapter"), "config", "surveillance.yaml",
        ])
    return LaunchDescription([
        DeclareLaunchArgument("profile", default_value=profile_default),
        DeclareLaunchArgument("use_sim_time", default_value=os.environ.get("RHM_USE_SIM_TIME", "true")),
        Node(
            package="rhm_surveillance_adapter", executable="surveillance_monitor",
            output="screen", parameters=[{
                "profile_path": LaunchConfiguration("profile"),
                "use_sim_time": LaunchConfiguration("use_sim_time"),
            }],
        ),
        Node(
            package="rhm_aggregator", executable="health_aggregator",
            output="screen", parameters=[{"use_sim_time": LaunchConfiguration("use_sim_time")}],
            remappings=[("/diagnostics", "/rhm/surveillance/diagnostics")],
        ),
    ])
