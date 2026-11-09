# Implemented parameters (native baseline, unverified revision)

| Node | Parameter | Startup default | Mutability | Behavior |
|---|---|---|---|---|
| `rhm_sensor_monitor` | `use_sim_time` | false | ROS node parameter | True only when /clock is available |
| `rhm_sensor_monitor` | `warn_age` | 0.5 seconds | read-only | WARN above threshold |
| `rhm_sensor_monitor` | `error_age` | 2.0 seconds | read-only | STALE above threshold |
| `rhm_aggregator` | `debounce_samples` | 3 | read-only | Consecutive observed samples before transition |
| `rhm_aggregator` | `stale_timeout` | 2.0 seconds | read-only | Missing diagnostics become STALE |

Thresholds require finite `0 <= warn_age < error_age`. Startup overrides are
validated before monitor resources are configured. An invalid override must
fail startup, rather than allowing silently incorrect status reports.

The parameters for all other planned monitors are **not** implemented yet.
