from glob import glob
from setuptools import setup

package_name = "algo_localization"

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
    description="Localization and mapping support for LiDAR, IMU, and odometry fusion.",
    license="Apache-2.0",
    tests_require=["pytest"],
)
