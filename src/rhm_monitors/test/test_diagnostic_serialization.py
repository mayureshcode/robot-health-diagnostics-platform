"""Regression test: DiagnosticStatus.level is an IDL byte in ROS 2 Jazzy.

An integer is accepted by some Python-side code but crashes the C serialization
path with `PyBytes_Check(field)` when the diagnostic array is published.
"""

import pytest
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus
from rclpy.serialization import deserialize_message, serialize_message

from rhm_monitors.logic.health import Status
from rhm_monitors.sensor_monitor import diagnostic_level_byte


@pytest.mark.parametrize('status', list(Status))
def test_jazzy_diagnostic_level_serializes(status: Status) -> None:
    """All four levels must round-trip through Jazzy's actual ROS serializer."""
    level = diagnostic_level_byte(status)
    assert isinstance(level, bytes)
    assert len(level) == 1
    assert level == bytes((int(status),))

    status_msg = DiagnosticStatus(
        level=level,
        name='mobile/sensor/scan',
        message=status.name,
        hardware_id='mobile',
    )
    outbound = DiagnosticArray(status=[status_msg])
    encoded = serialize_message(outbound)
    decoded = deserialize_message(encoded, DiagnosticArray)
    assert decoded.status[0].level == level
    assert decoded.status[0].message == status.name
