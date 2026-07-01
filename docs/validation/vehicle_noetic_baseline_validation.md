# 车机 Noetic 基线验证记录

## 当前状态

- 记录日期: 2026-07-01
- 硬件状态: SCOUT MINI、PiPER 和传感器实物已到。
- 连接状态: 传感器线束已连接到车机并上胶固定，本机不作为真实传感器直连测试环境。
- 已验证流程: 已按 `tzb2026/readme-2451.txt` 在车机执行厂商 ROS Noetic 流程测试，当前反馈为无问题。

## 验证边界

- 该记录只覆盖厂商原始 Ubuntu 20.04 + ROS Noetic 工作区和手册流程。
- 该记录不代表 Ubuntu 22.04 + ROS2 Humble、Nav2、slam_toolbox、MoveIt2、`ros2_control` 或本仓库 ROS2 主线已完成实车验收。
- 本机侧验证默认限于构建、静态检查、mock/sim、文档一致性和可离线运行的测试。
- 真实底盘、PiPER、雷达、相机、IMU、TF 外参和 rosbag 记录需要部署到车机或 ROS2 主控后执行。

## 后续要求

- ROS2 单硬件 bringup 通过后，需要为底盘、PiPER、雷达、相机和 IMU 分别补充验收记录。
- 每次修改车机系统、CAN 配置、udev 规则、网络配置、启动入口或传感器安装状态后，都应更新本记录或新增对应验证记录。
- 厂商 Noetic 流程保留为硬件 fallback，不在其中继续加入任务主线逻辑。
