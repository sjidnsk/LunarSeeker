# 车机 Noetic 基线验证记录

## 当前状态

- 记录日期: 2026-07-02
- 硬件状态: SCOUT MINI、PiPER 和传感器实物已到。
- 连接状态: 传感器线束已连接到车机并上胶固定，本机不作为真实传感器直连测试环境。
- 已验证流程: 已按 `tzb2026/readme-2451.txt` 在车机执行厂商 ROS Noetic 流程测试；2026-07-02 已完成定位/SLAM P1 只读数据质量检查，并完成 P2 EKF 影子模式静止检查和 motion bag 录制。

## 2026-07-02 P1 只读检查结果

本次检查只覆盖厂商车机 ROS Noetic 工作区，不启动 Nav2、SLAM、导航目标或机械臂，不发送 `/cmd_vel`。

| 检查项 | 观测结果 | 结论 |
| --- | --- | --- |
| 底盘 CAN | `can0` 有持续数据流 | 底盘 CAN 通信正常 |
| `/odom` | 有且只有一个 publisher，频率约 50 Hz，`header.frame_id=odom`，`child_frame_id=base_footprint` | 可作为 P2 EKF 输入候选 |
| `/rslidar_points` | 有 publisher，频率约 9.973 Hz，`frame_id=rslidar`，时间戳非 0 | RoboSense 点云输入通过 Noetic P1 |
| `/scan` | 有 publisher，频率约 9.98 Hz，`frame_id=rslidar`，`ranges` 非全 `inf`、非全 `nan`、非全 0 | 点云转 LaserScan 通过 Noetic P1 |
| `/imu/data_raw` | 有 publisher，频率约 200 Hz，`header.frame_id=imu_link`，静止角速度无明显乱跳 | 可作为 P2 EKF 输入候选，ROS2 主线需映射到 `/imu/data` |
| TF | `odom -> base_footprint -> base_link -> rslidar/imu_link` 连通 | P1 TF 链通过 |
| rosbag | 包含 `/tf`、`/odom`、`/rslidar_points`、`/scan`、`/imu/data_raw` | P1 证据包已具备 |

P1 结论: 通过。可以进入 P2 `robot_localization` 参数开发和低风险离线/只读验证；P3 建图输入条件已具备，但正式建图仍建议在 P2 里程计链路确认后执行。

## P2 EKF 影子模式索引

2026-07-02 已在车机 Noetic 工作区完成 P2 `robot_localization` 影子模式静止检查，并录制静止与低速动作 bag。详细记录见 [定位与 SLAM 验证记录](localization_slam_validation.md)。

关键边界:

- Noetic EKF 只作为参数初调和实车输入质量证据，ROS2 主线配置以 `src/algo_localization/config/ekf.yaml` 为准。
- 因厂商 `/odom.pose.covariance` 中 x、y、yaw pose 协方差为 0，P2 初值只消费 `/odom.twist.linear.x`、`/odom.twist.angular.z` 和 IMU yaw rate。
- motion bag 尚未完成回放分析，暂不允许开启 `publish_tf=true` 接管 `odom -> base_footprint`。

## 验证边界

- 该记录只覆盖厂商原始 Ubuntu 20.04 + ROS Noetic 工作区和手册流程。
- 该记录不代表 Ubuntu 22.04 + ROS2 Humble、Nav2、slam_toolbox、MoveIt2、`ros2_control` 或本仓库 ROS2 主线已完成实车验收。
- Noetic P1 中 `/scan.frame_id` 为 `rslidar`，ROS2 主线后续需决定继续消费 `rslidar`，或通过静态 TF/配置统一到 `lidar_link`。
- Noetic P1 中 IMU 话题为 `/imu/data_raw`，ROS2 主线后续需映射或桥接到设计约定的 `/imu/data`。
- 本机侧验证默认限于构建、静态检查、mock/sim、文档一致性和可离线运行的测试。
- 真实底盘、PiPER、雷达、相机、IMU、TF 外参和 rosbag 记录需要部署到车机或 ROS2 主控后执行。

## 后续要求

- ROS2 单硬件 bringup 通过后，需要为底盘、PiPER、雷达、相机和 IMU 分别补充验收记录。
- 每次修改车机系统、CAN 配置、udev 规则、网络配置、启动入口或传感器安装状态后，都应更新本记录或新增对应验证记录。
- 厂商 Noetic 流程保留为硬件 fallback，不在其中继续加入任务主线逻辑。
