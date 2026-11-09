# QoS contract

| Interface | Reliability | Durability | Depth | Notes |
|---|---|---|---|---|
| `/scan`, `/imu`, `/odom` | Best effort | Volatile | SensorDataQoS | Do not block sensor producers |
| `/diagnostics` | Reliable | Volatile | 10 | Sensor monitor to aggregator |
| `/robot_health`, `/fault_events` | Reliable | Volatile | 10 | Fault events publisher not yet implemented |

Monitor and aggregator use single-threaded executors by default; locks protect samples for future multithreaded executors. Timer scheduling uses ROS clock for timestamp arithmetic, but wall timer for periodic execution; paused sim time is not yet handled correctly.
