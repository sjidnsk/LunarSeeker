# P3 Nav2 仿真验证记录

## 验证环境

- 日期: 2026-07-01
- 系统基线: Ubuntu 22.04 + ROS2 Humble + Python 3.10
- commit: `1d5041c` + 当前 P3 工作区改动
- 目标: 在轻量 2D 仿真中验证 P1 Nav2 栈和 P2 `navigation_coordinator` 的正式 `/navigate_to_pose` 闭环。

## 启动命令

成功闭环，默认打开 RViz:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch base_bringup nav2_sim_validation.launch.py scenario:=nominal
```

如需在录制 rosbag 或无图形环境中关闭 RViz:

```bash
ros2 launch base_bringup nav2_sim_validation.launch.py scenario:=nominal use_rviz:=false
```

失败场景:

```bash
ros2 launch base_bringup nav2_sim_validation.launch.py scenario:=frontier_unreachable
ros2 launch base_bringup nav2_sim_validation.launch.py scenario:=local_obstacle_blocked
ros2 launch base_bringup nav2_sim_validation.launch.py scenario:=target_approach_failed
```

## 关键 Topic

| Topic | 类型 | 用途 |
| --- | --- | --- |
| `/map` | `nav_msgs/msg/OccupancyGrid` | 简化场地地图 |
| `/tf`, `/tf_static` | `tf2_msgs/msg/TFMessage` | `map -> odom -> base_footprint -> base_link` 和 URDF TF |
| `/odom` | `nav_msgs/msg/Odometry` | 仿真底盘里程计，`child_frame_id` 为 `base_footprint` |
| `/joint_states` | `sensor_msgs/msg/JointState` | P3 仿真轮系关节状态，用于 RViz Robot Model |
| `/scan` | `sensor_msgs/msg/LaserScan` | 静态和动态障碍物观测 |
| `/mission/state` | `base_interfaces/msg/MissionState` | P3 场景阶段驱动 |
| `/target_detections` | `base_interfaces/msg/ScienceTargetArray` | selected target 接近点输入 |
| `/navigation/status` | `base_interfaces/msg/NavigationStatus` | P2 协调节点结构化状态 |
| `/navigate_to_pose/_action/status` | `action_msgs/msg/GoalStatusArray` | Nav2 action 状态 |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | Nav2 输出的最终速度命令 |

## Rosbag 记录命令

```bash
ros2 bag record -o bags/p3_nominal \
  /mission/state \
  /navigation/status \
  /map \
  /tf \
  /tf_static \
  /odom \
  /joint_states \
  /scan \
  /cmd_vel \
  /target_detections \
  /navigate_to_pose/_action/status
```

失败场景建议输出目录:

```text
bags/p3_frontier_unreachable
bags/p3_local_obstacle_blocked
bags/p3_target_approach_failed
```

## RViz 可视化注意事项

- P3 RViz 重点查看 `Robot Model`、TF、`Sim Map`、`LaserScan`、`Nav2 Plan`、`Global Costmap`、`Local Costmap` 和 `Odom Trail`。
- `Robot Model` 长期报 `front_left_wheel_link`、`front_right_wheel_link`、`rear_left_wheel_link`、`rear_right_wheel_link` 或 `base_footprint` 到 `map` 无 TF 时，先检查 `/joint_states`、`map -> base_footprint` 和 `map -> base_link`。
- 当前局部控制器是 RPP，不发布 DWB trajectory 调试 topic。RViz 中手动添加 `Trajectory` 显示项后出现 topic 缺失或类型错误，不作为 P3 验收失败依据；用 `Odom Trail` 和 `/cmd_vel` 判断实际运动。

## 场景记录

| 场景 | 期望结果 | rosbag | 结果 |
| --- | --- | --- | --- |
| `nominal` | 完成离开基地、frontier 搜索、目标接近、返回基地 | 未录制 | 通过，`navigation_scenario_driver` 输出 `passed: nominal navigation sequence completed` |
| `frontier_unreachable` | frontier 失败后进入 blacklist，候选耗尽时建议返回 | 未录制 | 通过，Nav2 planner 报不可达，最终输出 `passed: frontier unreachable produced return recommendation` |
| `local_obstacle_blocked` | 动态局部障碍触发恢复反馈或导航失败 | 未录制 | 通过，RPP 报 `detected collision ahead`，最终输出 `passed: local obstacle triggered Nav2 recovery feedback` |
| `target_approach_failed` | 目标接近点被阻断并发布失败状态 | 未录制 | 通过，局部控制和恢复失败后输出 `passed: target approach goal failed as expected` |

## 本轮执行的检查

```bash
python3 -m pytest src/base_interfaces src/algo_navigation/test src/base_bringup/test
colcon build --symlink-install --packages-select base_interfaces algo_navigation base_bringup
ros2 launch base_bringup nav2_sim_validation.launch.py --show-args
ros2 launch base_bringup nav2_sim_validation.launch.py scenario:=nominal nav2_log_level:=warn
ros2 launch base_bringup nav2_sim_validation.launch.py scenario:=frontier_unreachable nav2_log_level:=warn
ros2 launch base_bringup nav2_sim_validation.launch.py scenario:=local_obstacle_blocked nav2_log_level:=warn
ros2 launch base_bringup nav2_sim_validation.launch.py scenario:=target_approach_failed nav2_log_level:=warn
```

## 待验证和限制

- P3 地图、目标、障碍物和速度均为轻量仿真夹具，全部待实车复核。
- P3 只验证 Nav2 action 闭环、状态发布、场景失败处理和 rosbag 记录流程，不代表真实底盘、LiDAR、SLAM 或外参已经通过。
- 若 `local_obstacle_blocked` 只产生失败而没有 `recovery_count` 增加，需要结合 Nav2 日志确认是局部控制失败、规划失败还是行为树恢复配置未触发。
- 若 P3 与实车表现不一致，以实车低速验证和现场 rosbag 为准更新参数。
