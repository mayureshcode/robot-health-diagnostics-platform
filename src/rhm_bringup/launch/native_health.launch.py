"""Native ROS 2 bringup of health nodes; transitions are explicit/operator-managed."""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description() -> LaunchDescription:
    """Launch health nodes without commanding a robot or moving a simulated asset."""
    monitor_config = PathJoinSubstitution([
        FindPackageShare('rhm_monitors'), 'config', 'monitors.yaml',
    ])
    return LaunchDescription([
        Node(
            package='rhm_monitors', executable='sensor_monitor',
            output='screen', parameters=[monitor_config],
        ),
        Node(
            package='rhm_aggregator', executable='health_aggregator',
            output='screen', parameters=[{'use_sim_time': False}],
        ),
    ])
