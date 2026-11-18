"""Install FastAPI dashboard alongside ROS 2 packages."""

from glob import glob

from setuptools import setup

setup(
    name="rhm_dashboard",
    version="0.1.0",
    packages=["rhm_dashboard"],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/rhm_dashboard"]),
        ("share/rhm_dashboard", ["package.xml"]),
        ("share/rhm_dashboard/static", glob("rhm_dashboard/static/*")),
    ],
    package_data={"rhm_dashboard": ["static/*.html", "static/*.css", "static/*.js"]},
    include_package_data=True,
    install_requires=["setuptools"],
    extras_require={"test": ["pytest", "fastapi", "httpx"]},
    zip_safe=True,
    maintainer="RHM contributors",
    maintainer_email="maintainer@example.invalid",
    description="Read-only robot telemetry dashboard",
    license="MIT",
    entry_points={"console_scripts": ["dashboard = rhm_dashboard.server:main"]},
)
