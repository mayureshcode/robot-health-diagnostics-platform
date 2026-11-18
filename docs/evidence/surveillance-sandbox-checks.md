# Surveillance adapter/dashboard — source-only authoring checks

This evidence **does not verify ROS 2, colcon, a real surveillance robot, or
web browser rendering**. It was collected in the authoring sandbox, not on
Ubuntu 24.04 / ROS Jazzy.

- Environment: Python **3.13.5**, pytest **9.0.2**, FastAPI **0.128.2**,
  Pydantic **2.13.5**. This is not the Ubuntu target environment and does not
  establish compatibility with the pinned requirements on Ubuntu.
- Command (from repo root):

```bash
PYTHONPATH=src/rhm_dashboard:src/rhm_surveillance_adapter \
  python3 -m pytest -q \
  src/rhm_surveillance_adapter/test/test_logic.py \
  src/rhm_dashboard/test/test_api.py \
  src/rhm_dashboard/test/test_store.py \
  src/rhm_dashboard/test/test_assets.py
```

- Exit code **0**, output excerpt: `19 passed in 0.77s`.
- Pure-logic + data-store coverage measured with the same four pytest files
  and `--cov=rhm_surveillance_adapter.logic --cov=rhm_dashboard.schema`: 91%
  combined (93% adapter logic, 90% dashboard store). This is **not** overall
  Python/ROS package coverage.
- `node --check src/rhm_dashboard/rhm_dashboard/static/app.js`: exit **0**.
- `bash -n scripts/run_surveillance.sh scripts/setup_dashboard.sh scripts/verify_surveillance.sh`: exit **0**.
- `python3 -m compileall -q src/rhm_dashboard src/rhm_surveillance_adapter`: exit **0**.
- ROS lifecycle, ROS serialization, colcon, Gazebo, surveillance topics,
  Browser WebSocket live runtime, Docker, GitHub CI: **NOT RUN**.

Scripts in `scripts/verify_surveillance.sh` record more complete evidence after
execution in the user's Ubuntu environment. Do not promote these checks to
runtime validation.
