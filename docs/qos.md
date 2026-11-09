# ROS 2 QoS and clock contract

| Interface | Reliability | Durability | Depth | Current status |
|---|---|---|---:|---|
| `/scan`, `/imu`, `/odom` | best effort | volatile | sensor data default | Input subscriptions implemented |
| `/diagnostics` | reliable | volatile | 10 | Lifecycle publisher implemented |
| `/robot_health` | reliable | volatile | 10 | C++ publisher implemented |
| `/fault_events` | reliable | volatile | 10 | Publisher declared; generation unimplemented |

Sensor reception timestamps and staleness comparisons use the **ROS clock**.
Do not set `use_sim_time: true` without a functioning `/clock` source.
`rhm_monitors/config/monitors.yaml` defaults to false for native tests;
`monitors.sim.yaml` is reserved for future Gazebo launches.

Executor: both standalone entrypoints use default **single-threaded**
executors. Mutable sensor samples are protected by `RLock`, and C++ diagnostic
samples by `std::mutex`, supporting future executor changes; no parallel
performance claim is made. The C++ snapshot scheduling uses a wall timer;
all sample age arithmetic uses ROS time. Its behavior during paused and
rewound simulations still requires an integration test.
