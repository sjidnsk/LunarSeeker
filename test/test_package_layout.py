from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

PYTHON_PACKAGES = {
    "base_bringup": "Launch and configuration package for the lunar sampling robot.",
    "base_mission": "Mission state machine skeleton for autonomous lunar sampling.",
    "algo_perception": "Perception algorithms for target detection and RGB-D localization.",
    "algo_localization": "Localization and mapping support for LiDAR, IMU, and odometry fusion.",
    "algo_navigation": "Navigation strategy nodes for search, approach, return, and Nav2 coordination.",
    "algo_manipulation": "Manipulation algorithms for PiPER sampling, grasping, and unloading.",
}

CMAKE_PACKAGES = {
    "base_description": "Robot description for the SCOUT MINI plus PiPER lunar sampling platform.",
    "base_interfaces": "ROS2 interfaces for the lunar lava tube autonomous sampling mission.",
}

REMOVED_PACKAGE_DIRS = (
    "tzb_lunar_bringup",
    "tzb_lunar_description",
    "tzb_lunar_interfaces",
    "tzb_lunar_mission",
    "perception",
    "localization",
    "navigation",
    "manipulation",
)


def test_python_packages_use_category_prefixes():
    for package_name, description in PYTHON_PACKAGES.items():
        package_dir = SRC / package_name
        module_dir = package_dir / package_name

        assert package_dir.is_dir()
        assert (module_dir / "__init__.py").is_file()
        assert (package_dir / "resource" / package_name).is_file()
        assert (package_dir / "setup.py").is_file()
        assert (package_dir / "setup.cfg").is_file()
        assert (package_dir / "package.xml").is_file()

        package_xml = ET.parse(package_dir / "package.xml").getroot()
        assert package_xml.findtext("name") == package_name
        assert package_xml.findtext("description") == description
        assert package_xml.find("buildtool_depend").text == "ament_python"
        assert package_xml.find("export/build_type").text == "ament_python"

        setup_py = (package_dir / "setup.py").read_text(encoding="utf-8")
        assert f'package_name = "{package_name}"' in setup_py
        assert f'packages=[package_name]' in setup_py


def test_cmake_packages_use_category_prefixes():
    for package_name, description in CMAKE_PACKAGES.items():
        package_dir = SRC / package_name

        assert package_dir.is_dir()
        assert (package_dir / "CMakeLists.txt").is_file()
        assert (package_dir / "package.xml").is_file()

        package_xml = ET.parse(package_dir / "package.xml").getroot()
        assert package_xml.findtext("name") == package_name
        assert package_xml.findtext("description") == description
        assert package_xml.find("buildtool_depend").text == "ament_cmake"
        assert package_xml.find("export/build_type").text == "ament_cmake"

        cmake_lists = (package_dir / "CMakeLists.txt").read_text(encoding="utf-8")
        assert f"project({package_name})" in cmake_lists


def test_old_package_directories_are_removed_after_rename():
    for package_name in REMOVED_PACKAGE_DIRS:
        assert not (SRC / package_name).exists()
