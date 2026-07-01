# scout_ros2 与 tzb2026 Scout 基础代码对比

扫描日期: 2026-07-01

## 1. 来源状态

| 来源 | 路径 / 链接 | 版本线索 | 状态 |
| --- | --- | --- | --- |
| AgileX 官方 ROS2 Scout 包 | `https://github.com/agilexrobotics/scout_ros2` | GitHub 页面显示 `humble` 分支；本地导入 commit `bdbb90471613831fb0b2ec01fecac043445313c4` | 已本地阅读，待车机 ROS2 实测 |
| 厂商小车基础代码 Scout 包 | `tzb2026/src/scout_ros` | 本地嵌套仓库 commit `7bfd74426a763a171b7f3c4c9e4efff4dc817da7`，分支 `dev` | 已按车机 Noetic 手册流程测试通过，ROS2 不直接复用 |
| 厂商手册 | `tzb2026/readme-2451.txt` | 本地文本 | 车机 Noetic 流程来源 |

说明:

- `scout_ros2` 是 ROS2/ament 包，面向 Scout、Scout Mini、Scout Mini Omni 的底盘控制、状态发布、消息和 URDF。
- `tzb2026/src/scout_ros` 是 ROS1/catkin 包集合，除底盘驱动外，还包含雷达、建图、导航、RViz、地图和若干传感器 TF 集成入口。
- 本文只对源码、launch、消息和依赖作静态对比；ROS2 底盘实机通信、里程计精度和 TF 行为仍待车机或 ROS2 主控验证。

## 2. 顶层结论

`scout_ros2` 适合作为本项目 ROS2 Humble 底盘驱动候选基线，但它不是 `tzb2026/src/scout_ros` 的完整 ROS2 替代品。

它覆盖:

- SCOUT / SCOUT MINI 底盘 CAN 通信。
- `/cmd_vel` 控制输入。
- `/odom` 里程计输出。
- `odom -> base_frame` TF 发布。
- `/scout_status`、`/rc_status` 等底盘状态。
- 基础 URDF 和 Scout 消息定义。

它不覆盖:

- `scout_bringup` 中的雷达启动。
- `pointcloud_to_laserscan`。
- `rf2o_laser_odometry`。
- ROS1 `gmapping`。
- ROS1 `move_base` / `amcl` / `map_server`。
- 厂商手册中的相机、IMU、PiPER 流程。
- 当前小车上已固定传感器的完整 TF 外参。

因此迁移策略应是: **用 `scout_ros2` 替换 ROS1 `scout_base` 的底盘控制层；不要试图用它整体替换厂商 `scout_bringup` 的导航和传感器集成。**

## 3. 包结构对比

| 维度 | 官方 `scout_ros2` | `tzb2026/src/scout_ros` | 迁移判断 |
| --- | --- | --- | --- |
| 构建系统 | `ament_cmake`、`colcon` | `catkin`、`catkin_make` | ROS2 主线使用官方包方向正确 |
| ROS 版本 | ROS2 Humble 分支 | ROS1 Noetic/catkin 语境 | 不能混编 |
| 顶层包 | `scout_base`、`scout_description`、`scout_msgs` | `scout_base`、`scout_bringup`、`scout_description`、`scout_msgs` | ROS2 官方少了 bringup 集成层 |
| 底盘节点 | `scout_base_node`，`rclcpp` | `scout_base_node`，`roscpp` | 角色相近，可作为迁移对象 |
| 导航/建图 | 无 | `gmapping.launch`、`navigation_4wd.launch`、地图和 move_base 参数 | ROS2 中改用 `slam_toolbox` 和 Nav2 |
| 传感器集成 | 无 | `open_rslidar.launch` 启动雷达、点云转 scan、静态 TF、rf2o | 只能作为拓扑参考 |
| URDF | Scout v2 基础模型 | Scout v2、Scout Mini、显示 launch、RViz 配置更多 | Scout Mini 实物模型需要继续核对 |
| 消息 | ROS2 `scout_msgs/msg/*` | ROS1 `scout_msgs/msg/*` | 字段不完全兼容，不建议桥接自定义消息作为首批目标 |

## 4. 启动入口对比

### 官方 ROS2 入口

| 文件 | 作用 | 关键默认参数 |
| --- | --- | --- |
| `scout_base/launch/scout_base.launch.py` | 普通 Scout 底盘节点 | `port_name=can0`、`is_scout_mini=false`、`is_omni_wheel=false`、`base_frame=base_link`、`odom_topic_name=odom` |
| `scout_base/launch/scout_mini_base.launch.py` | Scout Mini 底盘节点 | `port_name=can0`、`is_scout_mini=true`、`is_omni_wheel=false`、`base_frame=base_link`、`odom_topic_name=odom` |
| `scout_base/launch/scout_mini_omni_base.launch.py` | Scout Mini Omni 底盘节点 | `port_name=can0`、`is_scout_mini=true`、`is_omni_wheel=true` |

推荐本项目首选入口:

```bash
ros2 launch scout_base scout_mini_base.launch.py port_name:=can0
```

该入口只代表底盘驱动，不包含雷达、IMU、相机、Nav2 或任务系统。

### 厂商 ROS1 入口

| 文件 | 作用 | 迁移判断 |
| --- | --- | --- |
| `scout_base/launch/scout_mini_base.launch` | ROS1 Scout Mini 底盘节点 | 参数可参考，但不能直接用于 ROS2 |
| `scout_bringup/launch/scout_minimal.launch` | 底盘 + description | ROS2 中应拆成底盘 launch + `robot_state_publisher` |
| `scout_bringup/launch/open_rslidar.launch` | 雷达、点云转 scan、静态 TF、rf2o、模型显示 | 只作传感器拓扑参考 |
| `scout_bringup/launch/gmapping.launch` | ROS1 gmapping | ROS2 中不用，改 `slam_toolbox` |
| `scout_bringup/launch/navigation_4wd.launch` | ROS1 move_base、map_server、amcl、RViz、底盘 | ROS2 中不用，改 Nav2 |

## 5. 运行接口对比

| 接口 | 官方 `scout_ros2` | `tzb2026/src/scout_ros` | 注意事项 |
| --- | --- | --- | --- |
| 控制输入 | 订阅 `/cmd_vel`，`geometry_msgs/msg/Twist` | 订阅 `/cmd_vel`，`geometry_msgs/Twist` | 标准消息，适合作为 ROS1/ROS2 bridge 第一批接口 |
| 里程计 | 发布可配置 `odom_topic_name`，默认 `/odom` | 发布可配置 `odom_topic_name`，默认 `/odom` | 标准消息，适合作为第一批接口 |
| TF | ROS2 版每次发布 odom TF | ROS1 版有 `pub_tf` 参数，厂商 Scout Mini 默认 `false` | 需要统一谁发布 `odom -> base_link/base_footprint`，避免重复 TF |
| base frame | 默认 `base_link` | 厂商 `scout_mini_base.launch` 默认 `base_footprint` | 本项目需在 `base_description` 中统一 frame 约定 |
| 状态 | `/scout_status`、`/rc_status` | `/scout_status`、`/BMS_status` | 自定义消息字段不同，首阶段不建议依赖 |
| 灯光控制 | `/light_control`，`ScoutLightCmd.cmd_ctrl_allowed` | `/scout_light_control`，`ScoutLightCmd.enable_cmd_light_control` | topic 和字段名不同，不能直接桥接 |
| 发布频率 | 主循环 50 Hz | 主循环 50 Hz | 频率相近，实际稳定性待实测 |
| 协议 | 自动检测 AGX V1/V2，README 说明 V1/V2 仅 CAN 支持 | 也检测 AGX V1/V2 | 车机实测仍需确认 can0 和协议 |

## 6. 代码行为差异

### 6.1 ROS2 版更接近上游通用驱动

`scout_ros2` 的 `ScoutBaseRos` 节点参数集中在:

- `port_name`
- `odom_frame`
- `base_frame`
- `odom_topic_name`
- `is_scout_mini`
- `is_omni_wheel`
- `simulated_robot`
- `control_rate`

节点初始化时通过 `ugv_sdk` 的 `ProtocolDetector` 自动检测协议版本，然后创建 `ScoutRobot` 或 `ScoutMiniOmniRobot`。真实车连接只接受 CAN 口，`port_name` 不是 CAN 时会直接报错返回。

### 6.2 ROS1 厂商代码包含本地修改痕迹

`tzb2026/src/scout_ros` 的 `scout_base_node.cpp` 和 `scout_messenger.cpp` 除 ROS1 API 外，还有几个本地化点:

- `scout_base_node.cpp` 在协议检测阶段硬编码先连 `can0`，随后才读取 `port_name` 参数。
- `scout_mini_base.launch` 默认 `base_frame=base_footprint`，`pub_tf=false`。
- 里程计角速度积分中使用 `d_theta = angular_speed * 1.118 * dt`，这是厂商 ROS1 代码里的经验系数，未标注来源，不能直接迁入 ROS2。
- 发布 `/BMS_status`，但 BMS 字段赋值代码大部分处于注释状态。
- `scout_bringup` 许可证为 `TODO`，不宜直接纳入主线。

### 6.3 ROS2 版自定义消息不是 ROS1 消息的等价平移

典型差异:

| ROS1 字段 / topic | ROS2 字段 / topic | 影响 |
| --- | --- | --- |
| `ScoutStatus.base_state` | `ScoutStatus.vehicle_state` | 字段名变化 |
| `ScoutStatus.fault_code` | `ScoutStatus.error_code` | 字段名变化 |
| `ScoutMotorState[4] motor_states` + `ScoutDriverState[4] driver_states` | `ScoutActuatorState[4] actuator_states` | 结构变化 |
| `ScoutLightCmd.enable_cmd_light_control` | `ScoutLightCmd.cmd_ctrl_allowed` | 字段名变化 |
| `/scout_light_control` | `/light_control` | topic 名变化 |
| `/BMS_status` | 无直接对应 | ROS2 状态少一类 ROS1 topic |
| 无 `/rc_status` | `/rc_status` | ROS2 多 RC 状态 |

结论: 首阶段 bridge 和 ROS2 主线不应依赖 `scout_msgs` 自定义状态，只依赖 `/cmd_vel`、`/odom`、必要时 `/tf` 这类标准接口。

## 7. 对本项目的建议

### 7.1 可直接采用

- 将 `scout_ros2` 保持为 `dependencies.repos` 中的 ROS2 第三方依赖。
- ROS2 单底盘 bringup 首选 `scout_base scout_mini_base.launch.py`。
- 底盘公共契约采用标准接口:
  - 输入: `/cmd_vel`，`geometry_msgs/msg/Twist`
  - 输出: `/odom`，`nav_msgs/msg/Odometry`
  - TF: `odom -> base_link` 或 `odom -> base_footprint`，但必须统一一个权威约定

### 7.2 只作为参考

- ROS1 `scout_bringup/open_rslidar.launch` 中的雷达、相机、IMU 静态 TF，只能作为待测量初值。
- ROS1 `navigation_4wd.launch` 和 `scout_description/param/4wd` 只能作为 Nav2 调参参考，字段和插件必须重写。
- ROS1 里程计角速度系数 `1.118` 只能作为待验证现象，不能无说明移植。
- ROS1 `scout_msgs` 自定义状态可用于排查车机 Noetic 行为，但不要作为 ROS2 主线接口。

### 7.3 暂不采用

- 不迁移 ROS1 `gmapping`。
- 不迁移 ROS1 `move_base`、`amcl`、`map_server`。
- 不纳入 `rf2o_laser_odometry`，除非完成 GPL v3 合规和功能替代评估。
- 不把 `scout_bringup` 原样改写成 ROS2 大 launch；应拆成底盘、传感器、定位、导航的独立 bringup。

## 8. ROS2 底盘 bringup 验收建议

第一轮只验证底盘，不启动 Nav2:

1. 保留车机 Noetic 可回退环境。
2. 在 ROS2 环境准备 `scout_ros2` 和 `ugv_sdk`。
3. 确认 SocketCAN:

```bash
ip link show can0
candump can0
```

4. 启动 ROS2 Scout Mini 底盘:

```bash
ros2 launch scout_base scout_mini_base.launch.py port_name:=can0
```

5. 检查标准接口:

```bash
ros2 topic list
ros2 topic echo /odom --once
ros2 topic echo /scout_status --once
ros2 run tf2_ros tf2_echo odom base_link
```

6. 低速控制测试，必须有人工急停和空旷区域:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.05}, angular: {z: 0.0}}"
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

验收标准:

- `/odom` 连续发布，`header.frame_id` 和 `child_frame_id` 符合本项目 TF 约定。
- `/cmd_vel` 低速前进和停止可控。
- 停止命令有效，急停可用。
- 无重复发布 `odom -> base_link/base_footprint` TF。
- 记录 ROS2 rosbag 和测试日期。

## 9. 需补充到主线的后续工作

- 新增 ROS2 底盘 bringup 检查单，单独记录 `scout_ros2` 实车验收。
- 在 `base_description` 中统一 `base_link` 与 `base_footprint` 的关系，避免 ROS1 和 ROS2 frame 混用。
- 在 `robot_profile.yaml` 中保留 `can0`，但标注 ROS2 实测状态。
- 确认 `scout_ros2` 的 `scout_description` 是否足够描述当前 Scout Mini 实物；如不足，迁移厂商 ROS1 `scout_mini` URDF/mesh 时需标注来源和许可证。
- 完成底盘实测后，再决定是否让 ROS2 原生底盘替代 Noetic bridge 中的 `/cmd_vel`、`/odom` 通道。
