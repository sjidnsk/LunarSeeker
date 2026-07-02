from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
EKF_CONFIG = PACKAGE_ROOT / "config" / "ekf.yaml"
LOCALIZATION_LAUNCH = PACKAGE_ROOT / "launch" / "localization.launch.py"
PACKAGE_XML = PACKAGE_ROOT / "package.xml"
SETUP_PY = PACKAGE_ROOT / "setup.py"


def _ekf_params():
    config = yaml.safe_load(EKF_CONFIG.read_text(encoding="utf-8"))
    return config["ekf_filter_node"]["ros__parameters"]


def test_ekf_config_uses_shadow_mode_by_default():
    params = _ekf_params()

    assert params["frequency"] == 30.0
    assert params["two_d_mode"] is True
    assert params["publish_tf"] is False
    assert params["map_frame"] == "map"
    assert params["odom_frame"] == "odom"
    assert params["base_link_frame"] == "base_footprint"
    assert params["world_frame"] == "odom"


def test_ekf_config_matches_p2_topic_contract():
    params = _ekf_params()

    assert params["odom0"] == "/odom"
    assert params["imu0"] == "/imu/data"
    assert params["odom0_config"] == [
        False,
        False,
        False,
        False,
        False,
        False,
        True,
        False,
        False,
        False,
        False,
        True,
        False,
        False,
        False,
    ]
    assert params["imu0_config"] == [
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        True,
        False,
        False,
        False,
    ]


def test_localization_launch_exposes_single_p2_entrypoint():
    text = LOCALIZATION_LAUNCH.read_text(encoding="utf-8")

    for expected in (
        "robot_localization",
        "ekf_node",
        "ekf_filter_node",
        "ekf.yaml",
        "odom_topic",
        "imu_topic",
        "filtered_odom_topic",
        'default_value="/odometry/filtered"',
        'default_value="false"',
        "publish_tf",
        "ParameterValue(publish_tf, value_type=bool)",
    ):
        assert expected in text


def test_package_installs_p2_launch_and_config():
    text = SETUP_PY.read_text(encoding="utf-8")

    assert 'glob("config/*.yaml")' in text
    assert 'glob("launch/*.launch.py")' in text


def test_robot_localization_runtime_dependencies_are_declared():
    text = PACKAGE_XML.read_text(encoding="utf-8")

    for dependency in (
        "launch",
        "launch_ros",
        "robot_localization",
        "nav_msgs",
        "sensor_msgs",
        "tf2_ros",
    ):
        assert f"<exec_depend>{dependency}</exec_depend>" in text
