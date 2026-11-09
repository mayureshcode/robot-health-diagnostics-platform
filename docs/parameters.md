# Parameters (unverified)

| Node | Parameter | Default | Meaning |
|---|---|---|---|
| sensor_monitor | warn_age | 0.5 s | WARN when sensor age exceeds threshold |
| sensor_monitor | error_age | 2.0 s | STALE when sensor age exceeds threshold |
| aggregator | debounce_samples | 3 | Consecutive observations for status transition |
| aggregator | stale_timeout | 2.0 s | Diagnostic freshness timeout |

Sensor timestamps use ROS clock. Runtime parameter validation is implemented for these values; other requested monitor parameters are not implemented.
