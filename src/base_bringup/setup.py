from glob import glob
from setuptools import setup

package_name = "base_bringup"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/config", glob("config/*.yaml")),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="TZB Lunar Team",
    maintainer_email="tzb-lunar-team@example.com",
    description="Launch and configuration package for the lunar sampling robot.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "mock_base_sensors = base_bringup.mock_base_sensors:main",
        ],
    },
)
