# Native redesign source checks — sandbox evidence

The source below was checked in a Debian-based sandbox where **ROS 2 Jazzy,
colcon and Docker are absent**. These checks establish only parse/syntax and
pure-logic smoke behavior, not native ROS correctness.

| Command | Exit | Output excerpt |
|---|---:|---|
| `bash -n scripts/*.sh` | 0 | no syntax errors |
| `python3 -m compileall -q src/rhm_monitors src/rhm_bringup` | 0 | no syntax errors |
| `python3` ElementTree parse of all `src/*/package.xml` | 0 | all 4 package names matched directories |
| `python3` PyYAML parse of `.yaml` and `.yml` files | 0 | parsed without error |
| Python stdlib smoke assertions on `health.py` | 0 | `PASS pure-logic smoke assertions (stdlib only)` |
| `git diff --check` | 0 | no whitespace errors |

**Not run here:** rosdep, colcon build/test, ROS graph smoke, pytest with
Hypothesis, coverage gate, mypy, Ruff, cppcheck, Clang-Tidy, Gazebo, MoveIt 2,
GitHub Actions or Docker. There is no permission to mark those as passing.
