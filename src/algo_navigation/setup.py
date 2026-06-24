from setuptools import setup

package_name = "algo_navigation"

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
    description="Navigation strategy nodes for search, approach, return, and Nav2 coordination.",
    license="Apache-2.0",
    tests_require=["pytest"],
)
