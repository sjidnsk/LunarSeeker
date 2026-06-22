from setuptools import setup

package_name = "tzb_lunar_mission"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="TZB Lunar Team",
    maintainer_email="tzb-lunar-team@example.com",
    description="Mission state machine skeleton for autonomous lunar sampling.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "mission_state_machine = tzb_lunar_mission.mission_state_machine:main",
        ],
    },
)
