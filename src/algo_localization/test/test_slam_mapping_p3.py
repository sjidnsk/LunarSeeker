from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SLAM_MAPPING_CONFIG = PACKAGE_ROOT / "config" / "slam_toolbox_mapping.yaml"
SLAM_MAPPING_LAUNCH = PACKAGE_ROOT / "launch" / "slam_mapping.launch.py"
PACKAGE_XML = PACKAGE_ROOT / "package.xml"


def _slam_mapping_params():
    config = yaml.safe_load(SLAM_MAPPING_CONFIG.read_text(encoding="utf-8"))
    return config["slam_toolbox"]["ros__parameters"]


def test_slam_toolbox_mapping_config_matches_p3_contract():
    params = _slam_mapping_params()

    assert params["mode"] == "mapping"
    assert params["map_frame"] == "map"
    assert params["odom_frame"] == "odom"
    assert params["base_frame"] == "base_footprint"
    assert params["scan_topic"] == "/scan"
    assert params["resolution"] == 0.05
    assert params["map_update_interval"] == 2.0
    assert params["transform_publish_period"] == 0.02
    assert params["min_laser_range"] == 0.2
    assert params["max_laser_range"] == 20.0


def test_slam_mapping_launch_exposes_single_p3_mapping_entrypoint():
    text = SLAM_MAPPING_LAUNCH.read_text(encoding="utf-8")

    for expected in (
        "slam_toolbox",
        "async_slam_toolbox_node",
        "slam_toolbox_mapping.yaml",
        "params_file",
        "scan_topic",
        "map_frame",
        "odom_frame",
        "base_frame",
        "use_sim_time",
        "log_level",
        'default_value="false"',
        "ParameterValue(scan_topic, value_type=str)",
        "ParameterValue(use_sim_time, value_type=bool)",
    ):
        assert expected in text


def test_slam_toolbox_runtime_dependency_is_declared():
    text = PACKAGE_XML.read_text(encoding="utf-8")

    assert "<exec_depend>slam_toolbox</exec_depend>" in text
