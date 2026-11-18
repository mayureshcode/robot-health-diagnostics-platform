"""ROS 2 Python package for the standalone surveillance diagnostic adapter."""

from setuptools import setup

setup(
    name="rhm_surveillance_adapter",
    version="0.1.0",
    packages=["rhm_surveillance_adapter"],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/rhm_surveillance_adapter"]),
        ("share/rhm_surveillance_adapter", ["package.xml"]),
        ("share/rhm_surveillance_adapter/config", ["config/surveillance.yaml"]),
    ],
    install_requires=["setuptools", "PyYAML"],
    extras_require={"test": ["pytest"]},
    zip_safe=True,
    maintainer="RHM contributors",
    maintainer_email="maintainer@example.invalid",
    description="Read-only ROS 2 surveillance health adapter",
    license="MIT",
    entry_points={
        "console_scripts": ["surveillance_monitor = rhm_surveillance_adapter.node:main"],
    },
)
