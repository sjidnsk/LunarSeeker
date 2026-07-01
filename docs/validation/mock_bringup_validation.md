# Mock Bringup 验证记录

## 验证环境

- 日期: 2026-06-25
- 系统基线: Ubuntu 22.04 + ROS2 Humble + Python 3.10
- 分支: `simulation/mock-bringup`
- 目标: 在本机不直连实车传感器的条件下，验证 mock/sim 启动、基础 TF、任务状态机、mock 目标、mock 导航状态和基础 rosbag。

## 启动命令

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch base_bringup sim_bringup.launch.py use_mock_hardware:=true mission_time_limit_sec:=600
```

## 启动节点

- `/robot_state_publisher`
- `/mission_state_machine`
- `/mock_base_sensors`
- `/mock_navigation`
- `/mock_manipulation`

## 关键 Topic

| Topic | 类型 | 验证结果 |
| --- | --- | --- |
| `/odom` | `nav_msgs/msg/Odometry` | 约 10 Hz，mock 数据 |
| `/scan` | `sensor_msgs/msg/LaserScan` | 约 10 Hz，mock 数据 |
| `/imu/data` | `sensor_msgs/msg/Imu` | 约 10 Hz，mock 数据 |
| `/joint_states` | `sensor_msgs/msg/JointState` | 约 10 Hz，mock 轮系关节 |
| `/target_detections` | `base_interfaces/msg/ScienceTargetArray` | 约 10 Hz，包含 2 个 mock 目标，其中 `mock_target_01` 被选中 |
| `/goal_pose` | `geometry_msgs/msg/PoseStamped` | 约 2 Hz，由 mock 导航按任务阶段发布，固定目标使用 `map` frame |
| `/mock/navigation_status` | `std_msgs/msg/String` | 约 2 Hz，由 mock 导航发布阶段和目标点状态 |
| `/mock/manipulation_status` | `std_msgs/msg/String` | 约 2 Hz，由 mock 操控发布预抓取、抓取、抬升、收回和放置状态 |
| `/mission/state` | `base_interfaces/msg/MissionState` | 状态机阶段可从 departure 推进到 complete |
| `/tf`、`/tf_static` | `tf2_msgs/msg/TFMessage` | 包含 `map -> odom -> base_link` 和 URDF 静态 TF |

## Mock 任务结果

执行命令:

```bash
ros2 action send_goal /execute_mission base_interfaces/action/ExecuteMission "{run_index: 4, use_mock_hardware: true, profile_name: 'mock'}"
```

结果:

```text
success: true
estimated_score: 50
collected_count: 1
summary: Mock mission completed with selected target mock_target_01.
fault_code: 0
status: SUCCEEDED
```

## Rosbag 摘要

本地验证包:

```text
bags/mock_run_004
```

该目录已被 `.gitignore` 忽略，不提交到 Git。

`ros2 bag info bags/mock_run_004` 摘要:

```text
Duration: 10.783117616s
Messages: 842
/scan: 108
/target_detections: 108
/odom: 108
/mock/manipulation_status: 22
/joint_states: 108
/imu/data: 108
/goal_pose: 22
/mission/state: 18
/tf: 216
/mock/navigation_status: 22
/tf_static: 2
```

## 待验证和限制

- 以上目标、导航、里程计、雷达、IMU 和关节状态均为 mock 数据，不代表实车能力。
- `mock_navigation` 只按任务阶段发布目标点和状态，不包含 Nav2 规划、局部避障或恢复行为。
- `/target_detections` 中的目标为固定 mock 位姿，尚未接入 RGB-D 感知、深度定位或误检处理。
- PiPER 抓取、放置、失败重试目前仅由 `/mock/manipulation_status` 表达状态序列，尚未接入真实 PiPER 驱动或轨迹控制。
- 当前硬件已到且传感器线束已固定到车机；真实底盘、PiPER、RGB-D、LiDAR、IMU 和外参仍需按阶段 1 部署到车机或 ROS2 主控重新验证。
