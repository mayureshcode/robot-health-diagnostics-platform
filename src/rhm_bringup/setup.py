"""Native launch-file package for the RHM diagnostics baseline."""

from glob import glob

from setuptools import setup

setup(
    name="rhm_bringup",
    version="0.1.0",
    packages=["rhm_bringup"],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/rhm_bringup"]),
        ("share/rhm_bringup", ["package.xml"]),
        ("share/rhm_bringup/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    # colcon uses this metadata to select pytest rather than setup.py unittest.
    extras_require={"test": ["pytest"]},
    zip_safe=True,
    maintainer="RHM contributors",
    maintainer_email="maintainer@example.invalid",
    description="Native lifecycle monitoring launch configuration",
    license="MIT",
)
