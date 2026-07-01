# tzb2026 厂商基础代码扫描分析报告

扫描日期: 2026-07-01

## 1. 结论摘要

`tzb2026/` 是厂商提供的小车基础代码集合，内容覆盖 SCOUT MINI 底盘、PiPER 机械臂、RealSense 相机、RoboSense 16 线雷达、串口 IMU、gmapping 建图、move_base 导航和 MoveIt 1 机械臂规划。该目录不是本仓库 ROS2 Humble 原生代码，整体更接近 ROS1 Noetic/catkin 工作区源码包。

本次扫描显示:

- 目录体积约 621MB，文件约 2506 个。
- 发现 53 个 `package.xml`，全部声明 `catkin` 构建工具。
- 仅 `rslidar_sdk` 在 `package.xml` 中同时带有 `catkin` 与 `ament_cmake` 条件，具备一定 ROS1/ROS2 双栈线索，但仍需单独编译验证。
- 厂商目录内嵌 6 个独立 `.git` 仓库: `Piper_ros`、`navigation`、`realsense-ros`、`rslidar_sdk`、`scout_ros`、`ugv_sdk`。
- 8 个 ROS 包许可证字段仍为 `TODO`，`rf2o_laser_odometry` 为 GPL v3。源码归档与复用前必须完成许可证确认，当前标记为待归档、待验证。
- 厂商手册明确写明运行环境为 ROS Noetic，和本项目 Ubuntu 22.04 + ROS2 Humble 基线不一致，不能直接并入主工程编译。

建议将 `tzb2026/` 作为本地厂商参考资料保存，不纳入 Git；需要使用其中能力时，按模块迁移到本仓库 ROS2 包，而不是整体复制编译。

## 2. 来源与归档状态

本报告仅基于本地 `tzb2026/` 目录静态扫描，未联网校验上游最新版本，未执行硬件联调，未执行完整构建。

| 来源目录 | 上游线索 | 当前提交/分支线索 | 状态 |
| --- | --- | --- | --- |
| `tzb2026/readme-2451.txt` | 厂商随包手册 | 本地文本 | 待归档 |
| `tzb2026/src/Piper_ros` | `https://github.com/agilexrobotics/Piper_ros.git` | `c1b78fd`, `ros-noetic-no-aloha` | 待验证 |
| `tzb2026/src/navigation` | `https://gitee.com/agilexrobotics/navigation.git` | `5c7a79d`, `master` 本地领先 1 | 待验证 |
| `tzb2026/src/realsense-ros` | `https://github.com/IntelRealSense/realsense-ros.git` | `e4938bb`, `development` | 待验证 |
| `tzb2026/src/rslidar_sdk` | `https://github.com/RoboSense-LiDAR/rslidar_sdk.git` | `11c89b8`, `main` | 待验证 |
| `tzb2026/src/scout_ros` | `https://github.com/westonrobot/scout_base.git` | `7bfd744`, `dev` | 待验证 |
| `tzb2026/src/ugv_sdk` | `https://github.com/agilexrobotics/ugv_sdk.git` | `012a9aa`, `main` | 待验证 |

注意: 上述嵌套仓库均有本地改动痕迹，不能简单视为上游原版。若后续需要形成正式第三方归档，应先保留压缩包校验值、来源链接、下载日期、许可证和厂商交付记录。

## 3. 顶层结构

| 路径 | 作用判断 | ROS/构建属性 |
| --- | --- | --- |
| `tzb2026/src/Piper_ros` | PiPER 机械臂 ROS1 驱动、消息、URDF/Gazebo 描述 | catkin |
| `tzb2026/src/piper_moveit` | PiPER MoveIt 配置、控制脚本、内置 MoveIt 1.1.11 源码 | catkin，MoveIt 1 |
| `tzb2026/src/scout_ros` | SCOUT/SCOUT MINI 底盘驱动、bringup、描述、消息 | catkin |
| `tzb2026/src/ugv_sdk` | AgileX/Weston UGV 底层 SDK | catkin + C++ SDK |
| `tzb2026/src/rslidar_sdk` | RoboSense 雷达驱动 | 条件支持 ROS1/ROS2，需验证 |
| `tzb2026/src/realsense-ros` | Intel RealSense ROS1 wrapper | catkin、nodelet |
| `tzb2026/src/navigation` | gmapping、pointcloud_to_laserscan、rf2o、RViz 多目标插件 | catkin |
| `tzb2026/src/imu` | 串口 IMU 驱动和 launch | catkin |
| `tzb2026/src/can_tool` | CAN 口配置脚本 | shell |
| `tzb2026/src/robot_ros` | 简单集成 launch 与 C++ 节点 | catkin |

## 4. ROS 包清单

### 4.1 车辆与底盘

| 包 | 版本 | 作用 | 关键依赖/接口 |
| --- | --- | --- | --- |
| `scout_base` | 0.3.3 | SCOUT 底盘节点 | `scout_msgs`, `ugv_sdk`, `sensor_msgs`, `controller_manager`, `topic_tools` |
| `scout_bringup` | 0.0.0 | 底盘、雷达、建图、导航启动集合 | `roscpp`, `rospy`, `std_msgs` |
| `scout_description` | 0.4.2 | SCOUT/SCOUT MINI URDF、mesh、地图、导航参数 | `urdf`, `xacro`, `lms1xx` |
| `scout_msgs` | 0.3.3 | SCOUT 自定义消息 | `message_generation`, `std_msgs` |
| `ugv_sdk` | 0.1.6 | UGV 底层通信 SDK | `asio` |

关键 launch:

- `scout_base/launch/scout_mini_base.launch`: 启动 `scout_base_node`，默认 `port_name=can0`、`is_scout_mini=true`、`pub_tf=false`，发布 `odom`。
- `scout_bringup/launch/open_rslidar.launch`: 启动 `rslidar_sdk`、`pointcloud_to_laserscan`、雷达/相机/IMU 静态 TF、`rf2o_laser_odometry` 和 SCOUT MINI 显示模型。
- `scout_bringup/launch/gmapping.launch`: 启动 ROS1 `gmapping/slam_gmapping`，使用 `base_footprint`、`odom`、`map`。
- `scout_bringup/launch/navigation_4wd.launch`: 启动 `move_base`、`map_server`、`amcl`、RViz，并 include `scout_mini_base.launch`。

迁移判断:

- ROS2 中底盘驱动不应直接复用 ROS1 `scout_base_node`，应优先评估是否已有 ROS2 AgileX/ugv SDK 驱动，或编写 `rclcpp`/`ros2_control` 硬件接口。
- `move_base`、`amcl`、`map_server` 需替换为 Nav2 对应组件。
- `tf` 包的 `static_transform_publisher` 语法需迁移到 ROS2 `tf2_ros`。

### 4.2 导航与建图

| 包 | 版本 | 作用 | 风险 |
| --- | --- | --- | --- |
| `openslam_gmapping` | 0.2.1 | OpenSLAM gmapping 库 catkin 化 | ROS1 生态 |
| `gmapping` | 1.4.1 | ROS1 gmapping wrapper/nodelet | ROS2 不直接适用 |
| `slam_gmapping` | 1.4.1 | gmapping metapackage | ROS1 不直接适用 |
| `pointcloud_to_laserscan` | 1.4.0 | 点云转 LaserScan | 该版本是 ROS1 nodelet 包 |
| `rf2o_laser_odometry` | 1.0.0 | 2D 激光里程计 | GPL v3，需许可证确认 |
| `navi_multi_goals_pub_rviz_plugin` | 0.0.0 | RViz 多目标点插件 | ROS1 RViz 插件，Qt/rviz API 需迁移 |

本项目 ROS2 Humble 基线下，建议:

- 建图优先使用 `slam_toolbox`。
- 定位与导航优先使用 Nav2 的 `map_server`、`amcl`、planner/controller/smoother/behavior tree。
- 点云转 scan 可评估 ROS2 版 `pointcloud_to_laserscan`，不要直接迁移 nodelet 写法。
- `rf2o_laser_odometry` 因 GPL v3 许可证和 ROS1 API 双重原因，暂不建议进入主线源码；如确需使用，先做许可证和功能替代评估。

### 4.3 雷达

`rslidar_sdk` 版本 1.5.16，`config/config.yaml` 默认配置:

- `lidar_type: RSHELIOS_16P`
- `msop_port: 6699`
- `difop_port: 7788`
- `ros_frame_id: rslidar`
- 点云输出话题: `/rslidar_points`
- 数据来源: 在线雷达

`package.xml` 带条件依赖:

- ROS1: `catkin`, `roscpp`, `roslib`, `pcl_ros`
- ROS2: `ament_cmake`, `rclcpp`, `rslidar_msg`
- 通用: `libpcap`, `sensor_msgs`, `std_msgs`, `yaml-cpp`

迁移判断:

- 这是厂商目录中最接近 ROS2 可直接验证的模块，但仍需在 Ubuntu 22.04 + ROS2 Humble 下单独 `colcon build` 实测。
- 配置中的 IP、端口、frame 和 topic 可以作为本项目 ROS2 雷达接入参数参考，实际网络和设备状态待测量。

### 4.4 RealSense 相机

| 包 | 版本 | 作用 |
| --- | --- | --- |
| `realsense2_camera` | 2.3.2 | RealSense ROS1 wrapper |
| `realsense2_description` | 2.3.2 | 相机 URDF/xacro 描述 |

厂商手册给出两台相机序列号示例:

- 底盘相机: `344322074615`
- 机械臂相机: `408322071302`

这些序列号来自本地手册，是否对应当前实物待测量、待验证。ROS2 中应优先使用 ROS2 版 `realsense2_camera`，参数名称、命名空间、TF 发布行为需重新核对。

### 4.5 IMU

| 包 | 版本 | 作用 |
| --- | --- | --- |
| `imu_launch` | 0.0.0 | IMU 启动包 |
| `serial_imu` | 0.0.0 | 串口 IMU 驱动 |

厂商手册写明 IMU 端口为 `/dev/ttyUSB0`，启动命令为 `roslaunch imu_launch imu_msg.launch`，查看话题为 `/imu/data_raw`。该端口绑定和设备权限需要在实车上重新验证，不能直接写成已满足。

### 4.6 PiPER 机械臂

| 包 | 版本 | 作用 | 关键接口 |
| --- | --- | --- | --- |
| `piper` | 0.0.0 | PiPER ROS1 控制节点 | `joint_states`, `arm_status`, `end_pose`, `enable_srv` |
| `piper_msgs` | 0.0.0 | PiPER 自定义消息/服务 | `actionlib`, `control_msgs`, `trajectory_msgs` |
| `piper_description` | 1.0.0 | URDF/xacro/mesh/Gazebo 控制配置 | `robot_state_publisher`, `rviz`, `gazebo` |
| `moveit_ctrl` | 0.0.0 | MoveIt 控制脚本和服务 | `moveit_commander`, `moveit_ros_planning_interface` |
| `piper_with_gripper_moveit` | 0.3.0 | 带夹爪 MoveIt 配置 | MoveIt 1 |
| `piper_no_gripper_moveit` | 0.3.0 | 无夹爪 MoveIt 配置 | MoveIt 1 |

关键 launch:

- `Piper_ros/src/piper/launch/start_single_piper.launch`: 默认 `can_port=can_piper`、`auto_enable=true`，启动 `piper_ctrl_single_node.py`。
- `Piper_ros/src/piper/launch/start_single_piper_rviz.launch`: 用于 RViz 控制场景。
- `piper_with_gripper_moveit/launch/demo.launch`、`piper_no_gripper_moveit/launch/demo.launch`: ROS1 MoveIt demo。

厂商文档中的关节范围和速度加速度参数可作为参考，但未实测，需标注待测量。ROS2 迁移应优先走 MoveIt 2 + `ros2_control`，把 CAN 控制、状态反馈和夹爪接口抽象成 ROS2 控制器或硬件接口。

### 4.7 内置 MoveIt 1.1.11

`tzb2026/src/piper_moveit/moveit-1.1.11` 内置完整 MoveIt 1.1.11 源码，但目录顶层存在 `CATKIN_IGNORE`，厂商 README 也说明默认不会编译它。

判断:

- 对 ROS2 Humble 项目不建议引入该 MoveIt 1 源码。
- 只建议参考 PiPER SRDF、joint_limits、controllers、kinematics 等配置，再迁移到 MoveIt 2 配置格式。

## 5. 厂商手册中的运行流程

`readme-2451.txt` 给出的典型流程如下，均为 ROS1 命令:

1. 网络与设备:
   - 本机 IP: `192.168.1.102`
   - 雷达 IP: `192.168.1.200`
   - 路由器 IP: `192.168.1.1`
   - Wi-Fi: `agilex-2451`
   - 密码信息存在于本地手册，正式文档不建议继续明文扩散。
2. CAN:
   - `cd ~/agilex_ws/src/can_tool/`
   - `./can_config.sh`
   - `candump can_piper`
   - `candump can0`
3. 建图:
   - `roslaunch scout_bringup open_rslidar.launch`
   - `roslaunch scout_bringup gmapping.launch`
   - `rosrun map_server map_saver -f map`
4. 导航:
   - `roslaunch scout_bringup navigation_4wd.launch`
5. 相机:
   - `roslaunch realsense2_camera rs_camera.launch camera:=cam_1 serial_no:=344322074615`
   - `roslaunch realsense2_camera rs_camera.launch camera:=cam_2 serial_no:=408322071302`
6. IMU:
   - `sudo chmod 777 /dev/ttyUSB0`
   - `roslaunch imu_launch imu_msg.launch`
7. 机械臂:
   - `roslaunch piper start_single_piper_rviz.launch`

迁移到本仓库时，上述流程只能作为硬件拓扑和话题意图参考。ROS2 版本应改写为 `ros2 launch`、Nav2、slam_toolbox、MoveIt 2、`ros2_control` 和 ROS2 参数文件。

## 6. 与本项目基线的差异

| 维度 | 厂商目录 | 本项目基线 | 影响 |
| --- | --- | --- | --- |
| Ubuntu | 文档标识 20.04/Noetic 语境，部分第三方说明甚至含 14.04/16.04 | Ubuntu 22.04 | 系统依赖需重新确认 |
| ROS | ROS Noetic、catkin、roslaunch、rospy/roscpp | ROS2 Humble、ament/colcon、rclpy/rclcpp | 不能直接编译或启动 |
| 导航 | `move_base`, `amcl`, `map_server`, `gmapping` | Nav2, `slam_toolbox` | 导航栈需重构 |
| TF | ROS1 `tf` 与旧 `static_transform_publisher` | ROS2 `tf2_ros` | launch 与 TF 参数需迁移 |
| 机械臂 | MoveIt 1 + `moveit_commander` | MoveIt 2 + `ros2_control` | 控制接口需重新设计 |
| 感知 | ROS1 RealSense nodelet | ROS2 RealSense composable/node | 参数和 topic 需核对 |
| 驱动 | 多数为 ROS1 驱动 | ROS2 驱动优先 | 应避免原样纳入 |

## 7. 许可证与合规风险

扫描 `package.xml` 发现:

- `BSD`: 41 处
- `Apache 2.0`: 4 处
- `BSD 3-Clause`: 1 处
- `GPL v3`: 1 处，位于 `rf2o_laser_odometry`
- `TODO`: 8 处

许可证为 `TODO` 的包:

- `piper`
- `piper_msgs`
- `imu_launch`
- `serial_imu`
- `navi_multi_goals_pub_rviz_plugin`
- `moveit_ctrl`
- `robot_ros`
- `scout_bringup`

结论: 不能把 `tzb2026/` 作为可直接发布或再分发的源码纳入主仓库。若必须复用其中代码，需要逐包确认许可证、上游来源、修改记录和二进制/模型资源授权。

## 8. 推荐迁移路线

### 8.1 只做参考保留

- 保留 `tzb2026/` 在工作区本地，加入 `.gitignore`。
- 报告、迁移记录、参数摘录进入 `docs/`。
- 不提交厂商源码、嵌套 `.git`、大模型/mesh、图片、PDF、zip 等大体积资源。

### 8.2 底盘

- 短期: 参考 `scout_mini_base.launch` 的 CAN 口、frame、odom topic 设置，确认 SCOUT MINI 实车 CAN 通信。
- 中期: 使用或实现 ROS2 SCOUT MINI 驱动节点，统一输出 `/odom`、`/tf`、`/cmd_vel`。
- 长期: 接入 `ros2_control`，使底盘控制和状态反馈进入统一控制框架。

### 8.3 导航

- 用 `slam_toolbox` 替代 `gmapping`。
- 用 Nav2 替代 `move_base`、ROS1 `amcl`、ROS1 `map_server`。
- 迁移 `scout_description/param/4wd` 中 costmap、planner 参数时，只保留数值参考；字段名和插件名需按 Nav2 重写。

### 8.4 雷达

- 单独抽取 `rslidar_sdk` 或安装官方 ROS2 驱动，在 Humble 下验证。
- 先确认网络配置、雷达型号 `RSHELIOS_16P`、端口 `6699/7788`、frame `rslidar`。
- 把点云话题统一纳入本项目传感器命名规范，再决定是否需要 pointcloud-to-scan。

### 8.5 相机

- 使用 ROS2 版 RealSense wrapper。
- 手册中的双相机序列号仅作待验证记录。
- 明确底盘相机和机械臂相机 TF 链路，避免和厂商 launch 中的静态 TF 重复发布。

### 8.6 IMU

- 确认设备型号、串口绑定规则、波特率和消息坐标系。
- 优先输出标准 `sensor_msgs/msg/Imu`。
- 如要接入 `robot_localization`，需实测协方差和 TF，当前均为待测量。

### 8.7 机械臂

- 复用 PiPER URDF/xacro、mesh、SRDF、joint limits 作为参考。
- 迁移到 MoveIt 2 配置包。
- 将 `can_piper` 控制逻辑拆成 ROS2 硬件接口或控制节点，避免继续依赖 ROS1 `rospy`、`moveit_commander`。

## 9. 可复用资产清单

优先级高:

- SCOUT MINI URDF/mesh: `scout_ros/scout_description/urdf`、`meshes`
- PiPER URDF/mesh: `Piper_ros/src/piper_description/urdf`、`meshes`
- PiPER MoveIt 配置: `piper_with_gripper_moveit/config`、`piper_no_gripper_moveit/config`
- RoboSense 参数: `rslidar_sdk/config/config.yaml`
- 厂商手册: `readme-2451.txt`

优先级中:

- `scout_description/param/4wd` 导航参数，可作为 Nav2 调参初值参考。
- `open_rslidar.launch` 中的雷达、相机、IMU 静态 TF，可作为初始安装位姿参考，但必须待测量。
- `can_tool` 中 CAN 初始化脚本，可参考 CAN 设备名和波特率配置。

不建议直接复用:

- ROS1 `move_base`、`gmapping`、`amcl` launch。
- MoveIt 1.1.11 源码。
- ROS1 RealSense nodelet 代码。
- `rf2o_laser_odometry` 源码，除非完成 GPL v3 合规确认。

## 10. 后续检查清单

- 待归档: 保存厂商原始交付包、校验值、交付日期和版本说明。
- 待验证: 在 Ubuntu 22.04 + ROS2 Humble 上单独验证 `rslidar_sdk` ROS2 构建。
- 待验证: 确认 SCOUT MINI 底盘 CAN 口 `can0`、PiPER CAN 口 `can_piper` 的 udev/SocketCAN 配置。
- 待测量: 雷达、相机、IMU、机械臂相对 `base_link` 的实际安装位姿。
- 待测量: PiPER 关节限位、夹爪行程、速度、加速度是否与厂商文档一致。
- 待验证: 两台 RealSense 序列号是否对应当前实物。
- 待验证: 厂商 `map.yaml` 是否只是示例地图，不能直接作为比赛地图使用。
- 待验证: 所有 `TODO` 许可证包是否允许再分发和改造。

## 11. Git 处理建议

本次已将 `tzb2026/` 加入仓库根 `.gitignore`。原因:

- 目录体积大，包含源码、图片、PDF、zip、mesh 等大资源。
- 内嵌多个 `.git` 仓库，直接提交会造成来源混乱。
- 多个包许可证待确认，不宜进入主仓库。
- 代码主体系为 ROS1/catkin，与本项目 ROS2 Humble 基线不一致。

后续如需保存少量参数或配置，应摘录到 `docs/` 或迁移后的 ROS2 包中，并标明来源、日期和验证状态。
