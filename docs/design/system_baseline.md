# 系统基线

## 固定平台

本项目以 SCOUT MINI 移动底盘和 PiPER 机械臂作为硬件基线，围绕 ROS2 Humble 构建自主采样系统。

| 类别 | 基线配置 | 状态 |
| --- | --- | --- |
| 底盘 | AgileX SCOUT MINI | 实物已到；厂商 Noetic 流程车机测试通过；ROS2 bringup 待验证 |
| 机械臂 | PiPER | 实物已到；厂商 Noetic 流程车机测试通过；ROS2 Humble 驱动待验证 |
| 主视觉 | RealSense D435i 级 RGB-D 相机 | 线束已接入车机并固定；型号、安装位和 ROS2 标定待验证 |
| 导航传感器 | 2D LiDAR / 厂商雷达配置参考 | 线束已接入车机并固定；型号、安装位和 ROS2 外参待验证 |
| 姿态传感器 | IMU | 线束已接入车机并固定；型号、安装位和 ROS2 外参待验证 |
| 辅助照明 | 补光灯 | 亮度、供电和重量待核算 |
| 结构件 | 相机、雷达、机械臂、灯具支架 | 待设计和称重 |

验证边界: 2026-07-01 记录，已按 `tzb2026/readme-2451.txt` 在车机执行厂商 ROS Noetic 流程测试，当前反馈为无问题。本机无法直接连接已固定到车机的传感器，因此本机验证限于 ROS2 构建、静态检查、mock/sim 和可离线测试项；真实硬件验证需部署到车机或 ROS2 主控执行。

## 供应商手册参考参数

AgileX 语雀手册参数已归档到 [../references/vendor_agilex_platform_parameters.md](../references/vendor_agilex_platform_parameters.md)。手册参考配置包括 Scout Mini、PiPER、Nvidia Jetson Orin Nano、奥比中光 dabai、Livox Mid360、超核电子 CH110 和 HUAWEI 4G 路由器。

这些参数当前仅作为供应商手册参考值，仍需完成离线资料归档、实物称重、装配尺寸测量、CAN bringup 和传感器标定后，才能作为项目最终配置。特别是手册记录的 Livox Mid360 与当前 2D LiDAR 导航基线不完全一致，需要单独评审 Nav2、slam_toolbox 和点云处理方案。

## 软件基线

| 项目 | 版本 / 组件 |
| --- | --- |
| OS | Ubuntu 22.04 |
| ROS | ROS2 Humble |
| Python | Python 3.10 |
| 构建系统 | colcon |
| 导航 | Nav2 |
| 建图 | slam_toolbox |
| 状态估计 | robot_localization |
| 控制 | ros2_control |
| 底盘驱动 | `scout_ros2` + `ugv_sdk`，来源见 `dependencies.repos` 和 [../references/third_party_dependencies.md](../references/third_party_dependencies.md)，commit 待硬件验证锁定 |
| 机械臂驱动 | `piper_ros` humble + `piper_sdk`，来源见 `dependencies.repos` 和 [../references/third_party_dependencies.md](../references/third_party_dependencies.md)，commit 待硬件验证锁定 |

## 坐标系约定

建议使用以下基础 TF 树，后续以实测外参和 URDF 为准:

```text
map
`-- odom
    `-- base_link
        |-- base_footprint
        |-- lidar_link
        |-- imu_link
        |-- rgbd_camera_link
        |-- fill_light_link
        |-- piper_base_link
        `-- sample_bin_link
```

## 基础能力目标

- 底盘: 发布里程计，接收速度控制，支持急停和低速精细运动。
- 机械臂: 支持关节状态、末端控制、预设位和抓取动作。
- RGB-D: 输出彩色图、深度图、相机内参和点云。
- 2D LiDAR: 输出稳定 `LaserScan`，用于建图、定位和避障。
- IMU: 输出角速度、线加速度和姿态估计输入。
- 补光灯: 支持固定照明或任务状态机控制。

## 待验证清单

- SCOUT MINI 驱动与 ROS2 Humble 的接口兼容性。
- PiPER 驱动、机械臂控制器和 ros2_control 接入方式。
- 传感器型号、安装高度、视场遮挡和 ROS2 外参标定。
- 供电、电磁干扰、线束运动余量和防脱落固定。
- 总重和出发尺寸是否满足赛题硬约束。
