"""Static regression checks for the Phase 2 mobile simulation contract."""

import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml
from launch import LaunchDescription


SRC = Path(__file__).resolve().parents[2]


def test_world_has_sensor_systems_and_obstacles() -> None:
    """Warehouse world must load required system plugins and static geometry."""
    path = SRC / 'rhm_sim/worlds/warehouse.sdf'
    root = ET.parse(path).getroot()
    plugins = {p.attrib['filename'] for p in root.findall('.//world/plugin')}
    assert {
        'gz-sim-physics-system', 'gz-sim-sensors-system',
        'gz-sim-imu-system', 'gz-sim-user-commands-system',
    } <= plugins
    assert root.find('.//world').attrib['name'] == 'rhm_warehouse'
    assert len(root.findall('.//world/model')) >= 3


def test_robot_joint_frames_and_sensors() -> None:
    """Xacro source defines the dynamics and sensor-frame naming contract."""
    path = SRC / 'rhm_description/urdf/rhm_mobile.urdf.xacro'
    root = ET.parse(path).getroot()
    assert root.attrib['name'] == 'rhm_mobile'
    joint_names = {j.get('name') for j in root.findall('joint')}
    assert {'caster_joint', 'lidar_joint', 'imu_joint'} <= joint_names
    text = path.read_text()
    for expected in (
        'left_wheel_joint', 'right_wheel_joint',
        'gz-sim-diff-drive-system', 'gz_frame_id', '/wheel/odom',
        '/scan', '/imu', '0.3',
    ):
        assert expected in text


def test_bridge_directions_and_single_tf_owner() -> None:
    """Gazebo produces sensors; only the EKF publishes ROS odom-to-base TF."""
    path = SRC / 'rhm_sim/config/bridge.yaml'
    records = yaml.safe_load(path.read_text())
    by_name = {item['ros_topic_name']: item for item in records}
    assert {'/clock', '/scan', '/imu', '/wheel/odom', '/joint_states',
            '/rhm/cmd_vel'} == set(by_name)
    assert all(by_name[key]['direction'] == 'GZ_TO_ROS'
               for key in ('/clock', '/scan', '/imu', '/wheel/odom', '/joint_states'))
    assert by_name['/rhm/cmd_vel']['direction'] == 'ROS_TO_GZ'
    assert '/tf' not in by_name


def test_ekf_config() -> None:
    """EKF owns filtered odometry and explicitly runs on ROS simulated time."""
    path = SRC / 'rhm_sim/config/ekf.yaml'
    values = yaml.safe_load(path.read_text())['ekf_filter_node']['ros__parameters']
    assert values['use_sim_time'] is True
    assert values['publish_tf'] is True
    assert values['odom0'] == '/wheel/odom'
    assert values['imu0'] == '/imu'
    assert values['base_link_frame'] == 'base_link'
    assert values['world_frame'] == 'odom'


def test_sim_launch_constructs() -> None:
    """A single launch description must include the configured sim stack."""
    path = SRC / 'rhm_bringup/launch/mobile_sim.launch.py'
    spec = importlib.util.spec_from_file_location('rhm_mobile_sim_launch', path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    description = module.generate_launch_description()
    assert isinstance(description, LaunchDescription)
    assert len(description.entities) >= 10
