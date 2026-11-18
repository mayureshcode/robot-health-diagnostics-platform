"""Gazebo Harmonic mobile simulation with native ROS clock and health diagnostics.

All robot motion is simulated. Lifecycle transitions are initiated by the
scripts/run_native.sh entrypoint after both nodes appear.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    """Launch deterministic warehouse, simulated mobile robot and health nodes."""
    sim_share = FindPackageShare('rhm_sim')
    description_share = FindPackageShare('rhm_description')
    monitor_share = FindPackageShare('rhm_monitors')
    world = PathJoinSubstitution([sim_share, 'worlds', 'warehouse.sdf'])
    bridge = PathJoinSubstitution([sim_share, 'config', 'bridge.yaml'])
    ekf = PathJoinSubstitution([sim_share, 'config', 'ekf.yaml'])
    xacro_file = PathJoinSubstitution([
        description_share, 'urdf', 'rhm_mobile.urdf.xacro',
    ])
    robot_description = Command([FindExecutable(name='xacro'), ' ', xacro_file])
    sim_time = {'use_sim_time': True}
    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='false', description='Start optional Gazebo GUI'),
        DeclareLaunchArgument('spawn_x', default_value='0.0'),
        DeclareLaunchArgument('spawn_y', default_value='0.0'),
        DeclareLaunchArgument('spawn_yaw', default_value='0.0'),
        ExecuteProcess(cmd=['gz', 'sim', '-s', '-r', world], output='screen'),
        ExecuteProcess(cmd=['gz', 'sim', '-g'], output='screen', condition=IfCondition(
            LaunchConfiguration('gui'),
        )),
        Node(
            package='robot_state_publisher', executable='robot_state_publisher',
            output='screen', parameters=[{
                'robot_description': robot_description,
                'use_sim_time': True,
            }],
        ),
        # Allow the Gazebo world /create service to advertise before spawning.
        TimerAction(period=3.0, actions=[Node(
            package='ros_gz_sim', executable='create', output='screen',
            arguments=[
                '-world', 'rhm_warehouse', '-topic', 'robot_description',
                '-name', 'rhm_mobile',
                '-x', LaunchConfiguration('spawn_x'),
                '-y', LaunchConfiguration('spawn_y'),
                '-z', '0.25',
                '-Y', LaunchConfiguration('spawn_yaw'),
            ],
        )]),
        Node(
            package='ros_gz_bridge', executable='parameter_bridge',
            output='screen', parameters=[{'config_file': bridge}, sim_time],
        ),
        Node(
            package='robot_localization', executable='ekf_node',
            name='ekf_filter_node', output='screen', parameters=[ekf, sim_time],
        ),
        Node(
            package='rhm_monitors', executable='sensor_monitor',
            output='screen', parameters=[PathJoinSubstitution([
                monitor_share, 'config', 'monitors.sim.yaml',
            ])],
        ),
        Node(
            package='rhm_aggregator', executable='health_aggregator',
            output='screen', parameters=[sim_time],
        ),
    ])
