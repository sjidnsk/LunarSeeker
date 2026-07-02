# 定位建图与 SLAM 专项设计方案

本文定义 LunarSeeker 在 ROS2 Humble 主线中的定位建图、SLAM、状态估计和 TF 交付方案。本文是阶段 4“导航与越障”中 `slam_toolbox`、`robot_localization`、LiDAR、IMU、里程计和 TF 稳定性的专项设计入口。

当前状态:

- `algo_localization` 目前仅为空壳包，尚未提供可运行的定位建图节点、参数文件或 launch。
- `base_bringup` 的 Nav2 P1/P3 只验证了外部 `/map`、`/tf`、`/odom`、`/scan` 输入契约，不代表真实 SLAM、外参或传感器数据已通过。
- 2026-07-02 车机 ROS Noetic P1 只读检查已通过: `can0`、`/odom`、`/rslidar_points`、`/scan`、`/imu/data_raw`、TF 链和 rosbag 记录均正常；该结果只证明厂商 Noetic 链路可用，不代表 ROS2 Humble 主线已完成接入。
- 真实硬件验证必须部署到车机或 ROS2 主控后执行；本机只能完成文档、静态检查、mock/sim 和可离线验证项。
- 本文所有外参、协方差、频率、速度、地图质量和定位漂移指标均为初始设计或验收门槛，未实测前保持“待测量”或“待验证”状态。

## 目标与边界

目标:

- 为 Nav2 提供稳定 `/map`、`map -> odom`、`odom -> base_footprint`、`/odometry/filtered` 和 `/scan`。
- 使用 `robot_localization` 融合 wheel odom 与 IMU，形成连续、低跳变的局部里程计。
- 使用 `slam_toolbox` 完成比赛场地建图、回环检查、地图保存和固定地图定位。
- 建立可执行的实车检查步骤、rosbag 记录内容和故障判据。
- 明确 TF 唯一发布者，避免重复发布 `map -> odom` 或 `odom -> base_footprint`。

非目标:

- 不自研 SLAM、点云里程计、激光里程计或滤波框架。
- 不把 ROS1 `gmapping`、`move_base` 或厂商 launch 原样迁入 ROS2 主线。
- 不把 mock/sim 中的 `/map`、`/tf` 和 `/odom` 结论视为实车定位结论。
- 不在未确认许可证和必要性前引入 `rf2o_laser_odometry` 等替代依赖。
- 不让导航、感知或机械臂模块直接读取底层 CAN、串口或私有传感器接口。

## 系统分层

```text
base_bringup
|-- SCOUT MINI driver          提供 /odom 和 /cmd_vel 响应，是否发布 TF 必须显式配置
|-- LiDAR driver               提供 /scan 或经转换后的 LaserScan
|-- IMU driver                 提供 /imu/data
`-- robot_state_publisher      发布 URDF 静态/关节 TF

algo_localization              待实现
|-- robot_localization EKF     融合 /odom 和 /imu/data
|-- slam_toolbox               建图、定位和 map -> odom
`-- localization checks        质量检查和记录脚本，待实现

algo_navigation / Nav2
|-- 只消费 /map、/tf、/odometry/filtered 或 /odom、/scan
`-- 不直接管理 SLAM、传感器驱动或 TF 外参
```

职责边界:

| 模块 | 职责 | 不负责 |
| --- | --- | --- |
| `base_bringup` | 启动底盘、雷达、IMU、URDF、传感器 TF | 不选择搜索目标，不保存 SLAM 地图 |
| `algo_localization` | 状态估计、建图、固定地图定位、定位质量检查 | 不发布 `/cmd_vel`，不实现 Nav2 策略 |
| `algo_navigation` | 消费地图和 TF，调用 Nav2，处理导航失败 | 不读取原始 CAN/串口，不修正外参 |
| `base_description` | URDF、link 命名、静态外参初值 | 不根据运行时数据修正定位漂移 |

## 输入输出接口

### 输入

| 名称 | 类型 | 生产者 | 用途 | 状态 |
| --- | --- | --- | --- | --- |
| `/odom` | `nav_msgs/Odometry` | SCOUT MINI 底盘驱动 | wheel odom 输入、速度连续性检查 | Noetic P1 已验证约 50 Hz；ROS2 接入待验证 |
| `/scan` | `sensor_msgs/LaserScan` | RoboSense RSHELIOS_16P 点云转 LaserScan | `slam_toolbox` 建图定位、Nav2 obstacle layer | Noetic P1 已验证约 9.98 Hz，`frame_id=rslidar`；ROS2 接入待验证 |
| `/imu/data` | `sensor_msgs/Imu` | IMU 驱动 | yaw rate、姿态辅助、滤波输入 | Noetic P1 实测为 `/imu/data_raw` 约 200 Hz；ROS2 需映射到 `/imu/data` |
| `/tf_static` | `tf2_msgs/TFMessage` | `robot_state_publisher` / 静态 TF | 传感器外参和机器人结构 | 外参待测量 |
| `/tf` | `tf2_msgs/TFMessage` | `slam_toolbox`、`robot_localization`、底盘或仿真 | 动态坐标链路 | Noetic P1 链路连通；ROS2 发布权待确认 |

### 输出

| 名称 | 类型 | 消费者 | 用途 | 状态 |
| --- | --- | --- | --- | --- |
| `/map` | `nav_msgs/OccupancyGrid` | Nav2、frontier 搜索、RViz | 全局规划和探索目标选择 | 实车待验证 |
| `map -> odom` | TF | Nav2、感知、任务记录 | 全局定位修正 | 由 `slam_toolbox` 发布，待实现 |
| `/odometry/filtered` | `nav_msgs/Odometry` | Nav2、记录系统 | 融合里程计 | 待实现 |
| `odom -> base_footprint` | TF | 全系统 | 局部连续位姿 | 推荐由 `robot_localization` 发布，待验证 |
| 定位质量检查结果 | 文档记录或后续 topic | P0、B、C | 判断是否允许导航 | 待实现 |

接口原则:

- 正式定位链路优先让 `robot_localization` 发布 `odom -> base_footprint`，原始底盘驱动只发布 `/odom`，不发布同名 TF。
- 若实车驱动无法关闭 `odom -> base_footprint`，则第一轮 bringup 可临时由底盘驱动作为 TF 权威，`robot_localization` 只发布 `/odometry/filtered`，但必须记录限制和迁移计划。
- `slam_toolbox` 是 `map -> odom` 的唯一发布者；Nav2、mock 节点和手写脚本不得同时发布该 transform。
- `base_footprint -> base_link`、传感器 link 和机械臂 link 由 URDF 与 `robot_state_publisher` 维护。
- `/odom` 保留为原始底盘里程计；Nav2 实车参数最终应优先消费 `/odometry/filtered`，但切换前必须通过短距离低速测试。

## 坐标系与 TF 权威

推荐 TF 树:

```text
map
`-- odom
    `-- base_footprint
        `-- base_link
            |-- front_left_wheel_link
            |-- front_right_wheel_link
            |-- rear_left_wheel_link
            |-- rear_right_wheel_link
            |-- lidar_link
            |-- imu_link
            |-- rgbd_camera_link
            `-- piper_base_link
```

TF 发布权:

| Transform | 推荐发布者 | 说明 | 状态 |
| --- | --- | --- | --- |
| `map -> odom` | `slam_toolbox` | 建图/定位对 odom 漂移做全局修正 | 待实现 |
| `odom -> base_footprint` | `robot_localization` | 融合 wheel odom 与 IMU 后输出连续局部位姿 | 待实现 |
| `base_footprint -> base_link` | `robot_state_publisher` | 来自 URDF，不应由定位节点重复发布 | mock/sim 已验证，实车待验证 |
| `base_link -> lidar_link` | `robot_state_publisher` / 静态 TF | 外参必须实测 | 待测量 |
| `base_link -> imu_link` | `robot_state_publisher` / 静态 TF | 外参和方向必须实测 | 待测量 |
| `base_link -> rgbd_camera_link` | `robot_state_publisher` / 静态 TF | 影响目标位姿转换 | 待测量 |
| `base_link -> piper_base_link` | `robot_state_publisher` / 静态 TF | 影响抓取坐标转换 | 待测量 |

启动前必须确认:

- 同一个 child frame 只有一个动态 TF 发布者。
- `/odom.header.frame_id` 为 `odom`。
- `/odom.child_frame_id` 为 `base_footprint` 或 `base_link`，最终需统一到 `base_footprint`。
- `/scan.header.frame_id` 必须能通过 TF 连到 `base_link` 或 `base_footprint`；Noetic P1 实测为 `rslidar`，ROS2 主线需决定保留 `rslidar` 或统一到 `lidar_link`。
- `/imu/data.header.frame_id` 与 TF 中的 `imu_link` 一致；Noetic P1 实测话题为 `/imu/data_raw`，ROS2 主线需映射到 `/imu/data`。
- `base_footprint` 不是 joint，不应通过 `/joint_states` 发布。

## 数据质量准入

在启动 `robot_localization` 和 `slam_toolbox` 前，必须完成只读数据检查。

### Topic 存活与频率

```bash
ros2 topic list
ros2 topic hz /odom
ros2 topic hz /scan
ros2 topic hz /imu/data
ros2 topic echo /odom --once
ros2 topic echo /scan --once
ros2 topic echo /imu/data --once
```

验收门槛:

| 项目 | 门槛 | 状态 |
| --- | --- | --- |
| `/odom` | 连续发布，无时间戳倒退，速度符号与车体运动一致 | Noetic P1 已验证约 50 Hz；运动方向仍待 P2 低速验证 |
| `/scan` | 连续发布，非全 NaN/Inf，角度范围与雷达安装一致 | Noetic P1 已验证约 9.98 Hz，`ranges` 有效；角度范围待建图验证 |
| `/imu/data` | 连续发布，静止时角速度接近 0，重力方向合理 | Noetic P1 已验证 `/imu/data_raw` 约 200 Hz；ROS2 话题映射待实现 |
| frame_id | 与 TF 树一致，不出现空 frame | Noetic P1 已验证 `odom`、`base_footprint`、`rslidar`、`imu_link` 连通 |
| 协方差 | 未实测前不得写成可信精度；缺省值需记录来源 | 待测量 |

### TF 检查

```bash
ros2 run tf2_tools view_frames
ros2 run tf2_ros tf2_echo odom base_footprint
ros2 run tf2_ros tf2_echo map odom
ros2 run tf2_ros tf2_echo map base_footprint
ros2 run tf2_ros tf2_echo base_link lidar_link
ros2 run tf2_ros tf2_echo base_link imu_link
```

验收门槛:

- TF 树无断链。
- `map -> odom -> base_footprint -> base_link` 可连续查询。
- 不出现两个节点同时发布 `map -> odom`。
- 不出现两个节点同时发布 `odom -> base_footprint` 或 `odom -> base_link`。
- RViz `Robot Model` 中底盘、轮子、LiDAR、IMU、相机和 PiPER 基座能解析到固定 frame。

### LiDAR 安装和遮挡

检查内容:

- 雷达安装高度、朝向、前向零角度和遮挡范围，全部待测量。
- 实车雷达为 RoboSense RSHELIOS_16P；车机 Noetic P1 已验证 `rslidar_sdk` 的 `/rslidar_points` 输出和点云到 `/scan` 的转换链路。
- 转换后的 `/scan` 在 Noetic P1 中已确认 `frame_id=rslidar` 且 `ranges` 有效；截取高度、角分辨率、range_min、range_max 和滤波规则仍需在 ROS2 主线和建图阶段复核。

不得把点云输入直接写入 Nav2 或 `slam_toolbox` 主线，除非同步补充依赖、参数、launch、测试和文档。

## `robot_localization` 设计

第一阶段使用单 EKF，融合 wheel odom 与 IMU，输出 `/odometry/filtered` 和推荐的 `odom -> base_footprint`。

计划入口:

```text
src/algo_localization/config/ekf.yaml          待实现
src/algo_localization/launch/localization.launch.py  待实现
```

推荐配置意图:

| 参数 | 初始建议 | 说明 | 状态 |
| --- | --- | --- | --- |
| `frequency` | 30 Hz | 输出频率，需匹配底盘和 Nav2 | 待验证 |
| `two_d_mode` | true | 比赛场地按 2D 导航处理 | 待验证 |
| `map_frame` | `map` | 全局 frame，仅由 SLAM 修正 | 待验证 |
| `odom_frame` | `odom` | 连续局部 frame | 待验证 |
| `base_link_frame` | `base_footprint` | 与 Nav2/URDF 链路统一 | 待验证 |
| `world_frame` | `odom` | 单 EKF 不发布 map 修正 | 待验证 |
| `odom0` | `/odom` | 底盘 wheel odom | 待验证 |
| `imu0` | `/imu/data` | yaw rate 和姿态辅助 | 待验证 |
| `publish_tf` | true | 作为推荐 `odom -> base_footprint` 权威 | 待验证 |

融合原则:

- `/odom` 可用于 x、y、yaw、vx、vyaw；具体启用字段需根据 SCOUT MINI 驱动输出实测确认。
- `/imu/data` 第一阶段只建议使用 yaw rate 和姿态相关字段；磁力计或绝对航向未验证前不得作为稳定真值。
- 若 IMU 姿态方向或坐标轴不确定，先只录 bag，不接入 EKF。
- 协方差不得凭经验写成已验证精度；初值必须标注待测量，并通过静止、直线、原地转向数据修正。
- `robot_localization` 的输出不得与底盘驱动重复发布同一 TF。

最小验收:

```bash
ros2 topic hz /odometry/filtered
ros2 topic echo /odometry/filtered --once
ros2 run tf2_ros tf2_echo odom base_footprint
```

通过条件:

- 静止 60 秒内 `/odometry/filtered` 无明显跳变。
- 低速直行时 x 方向单调变化，横向漂移可解释并记录。
- 原地转向时 yaw 连续，无突然翻转。
- TF 查询连续，RViz 中 `Odom Trail` 不断裂。

## `slam_toolbox` 设计

第一阶段使用 `slam_toolbox` 在线异步建图，完成场地地图建立、回环检查和地图保存；比赛前优先使用确认过的固定地图定位。

计划入口:

```text
src/algo_localization/config/slam_toolbox_mapping.yaml       待实现
src/algo_localization/config/slam_toolbox_localization.yaml  待实现
src/algo_localization/launch/slam_mapping.launch.py          待实现
src/algo_localization/launch/slam_localization.launch.py     待实现
```

推荐配置意图:

| 参数 | 初始建议 | 说明 | 状态 |
| --- | --- | --- | --- |
| `mode` | `mapping` / `localization` 分文件 | 建图和固定地图定位分入口 | 待实现 |
| `odom_frame` | `odom` | 与 EKF 输出一致 | 待验证 |
| `map_frame` | `map` | Nav2 全局规划 frame | 待验证 |
| `base_frame` | `base_footprint` | 与 TF 权威链路一致 | 待验证 |
| `scan_topic` | `/scan` | 2D LaserScan 输入 | 待验证 |
| `resolution` | 0.05 m | 与 Nav2 global costmap 初值一致 | 待验证 |
| `map_update_interval` | 2.0 s | 初始建图更新周期 | 待验证 |
| `transform_publish_period` | 0.02-0.05 s | 需结合 CPU 和 TF 稳定性调整 | 待验证 |

建图流程:

1. 完成只读 topic、TF 和急停检查。
2. 启动底盘、传感器、URDF、`robot_localization`。
3. 启动 `slam_toolbox` mapping 入口。
4. RViz 查看 `/map`、`/scan`、TF、机器人模型和轨迹。
5. 以低速沿基地、搜索区、放置区和主要通道闭环行驶。
6. 每次回环后观察地图是否撕裂、重影或整体跳变。
7. 保存地图和序列化 pose graph。
8. 记录 rosbag、地图文件名、commit、参数文件和场地条件。

地图保存建议:

```bash
ros2 service list | rg "map|slam|serialize|save"
# 以下为计划命令，需以实际 slam_toolbox 服务名和 map_saver 安装情况为准。
ros2 run nav2_map_server map_saver_cli -f maps/field_initial
ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph "{filename: 'maps/field_initial'}"
```

地图验收门槛:

| 项目 | 通过条件 | 状态 |
| --- | --- | --- |
| 基地出口 | 地图中可辨识，无遮挡伪影不阻断通行 | 待验证 |
| 搜索区 | 主要通道和障碍边界连续 | 待验证 |
| 放置区 | 返回和停靠区域清晰 | 待验证 |
| 回环 | 回到基地附近时无明显撕裂或双墙 | 待验证 |
| 分辨率 | 与 Nav2 global costmap 一致或有明确理由 | 待验证 |
| 版本记录 | 地图、参数、rosbag、commit 可追溯 | 待实现 |

## 固定地图定位与 Nav2 联调

比赛前优先使用经过验证的固定地图定位，不在正式任务中依赖临时建图结果，除非现场规则或地图变化要求重新建图。

固定地图定位流程:

1. 启动底盘、传感器、URDF、`robot_localization`。
2. 启动 `slam_toolbox` localization 入口并加载已验收地图。
3. 确认 `/map`、`map -> odom`、`/odometry/filtered` 连续。
4. 启动 `base_bringup` Nav2 P1 入口。
5. 在 RViz 设置短距离目标点，低速验证规划、控制和 costmap。
6. 再启动 `navigation_coordinator` 或 P3 后续实车场景入口。

Nav2 接入要求:

- Nav2 global frame 使用 `map`。
- Nav2 robot base frame 与 TF 链路一致，推荐 `base_link` 或按现有 Nav2 参数保持，TF 必须能解析到 `base_footprint`。
- Nav2 odom topic 最终应切换到 `/odometry/filtered`；切换前保留 `/odom` 的对照测试记录。
- `/map` 的 QoS、更新频率和 frame 必须能被 global costmap 正常消费。
- local/global costmap 的 obstacle layer 与 `/scan` frame 一致。

## 实施路线

### P0: 静态检查和权威定义

产物:

- 本文档。
- 传感器型号、topic、frame 和 TF 发布权检查记录。
- RoboSense RSHELIOS_16P 的 `/rslidar_points`、`rslidar` frame、点云转 `/scan` 和 TF 发布权检查记录。

参考厂商基础代码后，P0 暂定必须确认以下信息。表中“厂商线索”只能作为实车排查起点，不等同于 ROS2 Humble 主线已验证参数。

| 类别 | 厂商基础代码线索 | P0 需要确认的信息 | 确认结果记录 |
| --- | --- | --- | --- |
| 雷达型号 | `rslidar_sdk/config/config.yaml` 中 `lidar_type: RSHELIOS_16P` | 实车铭牌、网页配置或驱动日志是否一致 | 2026-07-02 实车已确认为 RSHELIOS_16P |
| 雷达数据源 | `msg_source: 1`，表示在线雷达包输入 | ROS2 驱动是否直接从实车收包，而不是 rosbag/pcap 回放 | Noetic P1 已通过在线点云发布间接验证；ROS2 待验证 |
| 点云输出 | `send_point_cloud_ros: true`，点云 topic 为 `/rslidar_points` | ROS2 下 `/rslidar_points` 是否稳定发布，消息类型、频率和 frame 是否正确 | Noetic P1 已验证约 9.973 Hz，`frame_id=rslidar`；ROS2 待验证 |
| packet 话题 | `/rslidar_packets`，默认 `send_packet_ros: false` | 是否需要记录 packet bag 作为雷达排障证据 | 待验证 |
| 网络端口 | MSOP `6699`，DIFOP `7788`，`wait_for_difop: true` | 实车雷达 IP、主机 IP、端口、防火墙和网卡是否匹配 | Noetic P1 已通过点云发布间接验证；网络参数仍需归档 |
| 雷达 frame | `ros_frame_id: rslidar` | 项目 TF 是否保留 `rslidar`，或静态转换到 `lidar_link` 后统一消费 `lidar_link` | Noetic P1 已验证 `rslidar` 并连通 TF；ROS2 命名待决策 |
| 点云距离范围 | `min_distance: 0.2`，`max_distance: 200` | 近场盲区是否影响 5 cm 目标物块和低矮障碍检测 | 待验证 |
| 点云转 `/scan` | `point_to_scan.launch` 从 `/rslidar_points` 转换 | ROS2 版 `pointcloud_to_laserscan` 是否可用，输出 topic 是否为 `/scan` | Noetic P1 已验证约 9.98 Hz，`frame_id=rslidar`，`ranges` 有效；ROS2 待验证 |
| scan 高度切片 | 厂商 ROS1 launch 使用 `min_height: -0.2`，`max_height: 1.0` | 以 `base_footprint` 或 `lidar_link` 为准重新定义 SLAM scan 和低矮障碍 scan 的高度范围 | 待测量 |
| scan 角度范围 | 厂商 ROS1 launch 使用 `angle_min: -1.78`，`angle_max: 1.78`，`angle_increment: 0.007` | 是否需要 360 度建图 scan，还是保留前向局部避障 scan | 待验证 |
| scan 距离范围 | 厂商 ROS1 launch 使用 `range_min: 0.2`，`range_max: 100` | 结合场地尺寸、近场障碍和 Nav2 costmap 调整有效范围 | 待验证 |
| 雷达到车体 TF | `open_rslidar.launch` 静态 TF: `base_link -> rslidar` 为 `[0.22, 0.0, 0.15]` | 实车实际安装高度、俯仰角、横向偏置和遮挡；当前项目初值不得直接当实测外参 | 待测量 |
| 底盘 odom | `scout_mini_base.launch` 发布 `/odom`，`odom_frame=odom`，`base_frame=base_footprint`，`pub_tf=false` | ROS2 底盘驱动是否发布 `/odom`，是否关闭 TF，`child_frame_id` 是否统一到 `base_footprint` | Noetic P1 已验证 `/odom` 约 50 Hz，唯一 publisher，`child_frame_id=base_footprint`；ROS2 待验证 |
| 激光里程计 | `open_rslidar.launch` 启动 `rf2o_laser_odometry` 并发布 TF | 因 GPL v3 和 ROS1 API，不进入主线；若要替代 EKF 必须先做许可证和方案评审 | 不采用 |
| 点云/scan 坐标链 | 厂商链路为 `/rslidar_points -> /scan -> rf2o/gmapping` | 项目链路应拆成 SLAM scan、local costmap 近场障碍和目标识别协同，避免单层 scan 负责全部感知 | Noetic P1 输入链路已通；建图、避障和目标协同仍待设计验证 |

命令:

```bash
rg -n "scan_topic|imu_topic|odometry_topic|slam|localization|tf" src/base_bringup/config docs
ros2 pkg list | rg "slam_toolbox|robot_localization|nav2_map_server"
```

验收:

- 明确 `/scan` 是否真实存在。
- 明确 `odom -> base_footprint` 的唯一发布者。
- 未测量外参全部保持“待测量”。

### P1: 只读数据质量检查

产物:

- 车机 rosbag。
- topic 频率、frame_id、时间戳和 TF 树截图或文本记录。

ROS2 主线部署后的目标命令:

```bash
ros2 topic hz /odom
ros2 topic hz /scan
ros2 topic hz /imu/data
ros2 topic echo /odom --once
ros2 topic echo /scan --once
ros2 topic echo /imu/data --once
ros2 run tf2_tools view_frames
```

车机 ROS Noetic P1 已执行检查:

```bash
rostopic hz /odom
rostopic hz /rslidar_points
rostopic hz /scan
rostopic hz /imu/data_raw
rostopic echo -n 1 /odom
rostopic echo -n 1 /rslidar_points/header
rostopic echo -n 1 /scan/header
rostopic echo -n 1 /imu/data_raw
rosrun tf tf_echo odom base_footprint
rosrun tf tf_echo base_footprint base_link
rosrun tf tf_echo base_link rslidar
rosrun tf tf_echo base_link imu_link
rosbag record -O ~/agilex_ws/p1_bags/localization_p1_noetic.bag \
  /tf \
  /odom \
  /rslidar_points \
  /scan \
  /imu/data_raw
```

2026-07-02 车机 Noetic P1 结果:

| 检查项 | 结果 | 状态 |
| --- | --- | --- |
| `can0` | 有持续数据流 | 通过 |
| `/odom` | 唯一 publisher，约 50 Hz，`header.frame_id=odom`，`child_frame_id=base_footprint` | 通过 |
| `/rslidar_points` | 有 publisher，约 9.973 Hz，`frame_id=rslidar`，时间戳非 0 | 通过 |
| `/scan` | 有 publisher，约 9.98 Hz，`frame_id=rslidar`，`ranges` 非全 `inf`、非全 `nan`、非全 0 | 通过 |
| `/imu/data_raw` | 有 publisher，约 200 Hz，`header.frame_id=imu_link`，静止角速度无明显乱跳 | 通过 |
| TF | `odom -> base_footprint -> base_link -> rslidar/imu_link` 连通 | 通过 |
| rosbag | 包含 `/tf`、`/odom`、`/rslidar_points`、`/scan`、`/imu/data_raw` | 通过 |

结论: Noetic P1 通过。可进入 P2 EKF 参数开发；P3 建图输入条件已具备，但正式建图仍建议等待 P2 里程计链路确认。

验收:

- 不需要移动底盘即可确认传感器稳定发布。
- TF 无断链，无重复动态 transform。
- 发现异常时不得继续启动 Nav2 实车运动。

### P2: EKF 融合验证

产物:

- `robot_localization` 参数文件和 launch，待实现。
- 静止、低速直行、原地转向 rosbag。
- `/odometry/filtered` 与 `/odom` 对比记录。

建议动作:

1. 静止 60 秒。
2. 低速前进 0.5-1.0 m。
3. 低速后退 0.3-0.5 m。
4. 原地左右转向各一次。

验收:

- `/odometry/filtered` 连续，无明显跳变。
- `odom -> base_footprint` 发布权唯一。
- 实车动作全程可急停。

### P3: SLAM 建图验证

产物:

- `slam_toolbox` mapping 参数和 launch，待实现。
- 初版场地地图、pose graph、rosbag 和 RViz 截图。

建议动作:

1. 基地内短距离移动。
2. 离开基地并沿搜索区边界低速绕行。
3. 返回基地附近形成回环。
4. 保存地图并记录版本。

验收:

- `/map` 连续更新。
- 回环后地图无明显重影。
- 地图可被 Nav2 global costmap 读取。

### P4: 固定地图定位与短程导航

产物:

- `slam_toolbox` localization 参数和 launch，待实现。
- Nav2 短目标点测试记录。

建议动作:

1. 加载 P3 验收地图。
2. 静止定位稳定后发送 2-3 个短距离目标点。
3. RViz 查看 `/plan`、costmap、TF 和轨迹。
4. 记录失败原因和参数调整。

验收:

- 机器人能低速到达短距离目标点。
- 定位不因短时遮挡或局部障碍出现不可恢复跳变。
- Nav2 失败时能停止或进入有限恢复，不继续盲动。

### P5: 搜索与返回闭环

产物:

- 基地出口、搜索区、返回点、放置区坐标记录。
- 600 秒任务预算下的返回路径验证记录。
- 定位异常处理复盘。

验收:

- 能稳定离开基地并到达搜索点。
- 能在 600 秒约束下规划返回基地路径。
- 定位质量异常时可停止、等待或触发返回策略。

## Rosbag 记录

SLAM 和定位专项 rosbag:

```bash
ros2 bag record -o bags/localization_slam_check \
  /tf \
  /tf_static \
  /odom \
  /odometry/filtered \
  /scan \
  /imu/data \
  /map \
  /cmd_vel
```

Nav2 联调扩展 rosbag:

```bash
ros2 bag record -o bags/localization_nav2_check \
  /tf \
  /tf_static \
  /odom \
  /odometry/filtered \
  /scan \
  /imu/data \
  /map \
  /cmd_vel \
  /navigation/status \
  /navigate_to_pose/_action/status \
  /plan \
  /plan_smoothed
```

记录要求:

- 每个 bag 记录启动命令、commit、参数文件、地图文件、场地条件和操作人员。
- 低速运动前确认急停和人工接管。
- 图像或点云数据如需记录，另开 bag 或降频记录，避免影响 SLAM 实时性。
- 未实测的地图、外参、协方差和定位指标不得在记录中标成已通过。

## 故障判据与处理

| 故障 | 判据 | 第一处理 | 升级处理 |
| --- | --- | --- | --- |
| `/scan` 缺失 | topic 无发布或 frame 不存在 | 停止 SLAM，检查雷达驱动和 TF | 若为 3D LiDAR，评审点云转 LaserScan |
| `/imu/data` 异常 | 静止角速度明显漂移或方向不确定 | 暂不接入 EKF，只录 bag | 校准安装方向和驱动参数 |
| `/odom` 异常 | 时间戳倒退、速度符号错误、frame 不一致 | 停止导航，检查底盘驱动 | 回退到只读 bringup 排查 |
| TF 重复发布 | `view_frames` 或日志显示同 child 多发布者 | 关闭底盘或 EKF 中一个 TF 发布 | 重新定义 TF 权威 |
| `map -> odom` 跳变 | RViz 中机器人全局位置突跳 | 停止导航，保存 bag | 调整 SLAM 参数或改固定地图定位 |
| 地图重影 | 回环后墙体双层或基地错位 | 降速重建图，检查 `/scan` 外参 | 重新标定雷达安装位 |
| Nav2 costmap 偏移 | 障碍显示与实物不一致 | 检查 `lidar_link` 外参和 scan frame | 禁止继续实车避障测试 |
| 定位质量下降 | TF 查询不连续或轨迹漂移不可解释 | 停止任务，等待静止重定位 | 返回最近安全点或进入 `FAULT` |

## 参数调试记录模板

每次参数变化必须记录:

```text
日期:
操作者:
commit:
机器人硬件状态:
地图文件:
rosbag:
修改参数:
修改原因:
测试动作:
通过/失败:
失败现象:
下一步:
```

推荐保存位置:

```text
docs/validation/localization_slam_validation.md  待创建
bags/localization_slam_check/                    不提交大文件
maps/                                            地图文件提交策略待确认
```

## 与导航模块的交付关系

C 定位建图负责人向 B 导航负责人交付:

- `/map` 可被 frontier 和 global costmap 消费。
- `/scan` 可被 local/global obstacle layer 消费。
- `map -> odom -> base_footprint -> base_link` 连续可查询。
- `/odometry/filtered` 或 `/odom` 与 Nav2 参数一致。
- 定位异常时的停机、等待或返回建议。

B 导航负责人不得假设:

- mock `/map` 等同于真实 SLAM 地图。
- P3 仿真通过等同于实车 TF、雷达、IMU、外参通过。
- 未验证的地图可直接用于 600 秒比赛任务。

## 验证清单

### 静态检查

- `docs/README.md` 已加入本文入口。
- `docs/design/navigation_planning.md` 已引用本文。
- `robot_profile.yaml` 中 `/odom`、`/scan`、`/imu/data`、`/tf` 与本文一致。
- 新增 launch、参数或依赖时同步更新 `package.xml`、`setup.py`、README 和相关 docs。

### 本机检查

```bash
git diff --check
rg -n "localization_slam|slam_toolbox|robot_localization|map -> odom|base_footprint" docs
python3 -m pytest src/base_bringup/test src/algo_navigation/test
```

### 实车检查

```bash
ros2 topic hz /odom
ros2 topic hz /scan
ros2 topic hz /imu/data
ros2 run tf2_tools view_frames
ros2 run tf2_ros tf2_echo map base_footprint
ros2 run tf2_ros tf2_echo odom base_footprint
ros2 topic hz /odometry/filtered
ros2 topic hz /map
```

## 风险与待验证项

| 风险 | 影响 | 应对 | 状态 |
| --- | --- | --- | --- |
| ROS2 RoboSense 点云转 `/scan` 接入未验证 | `slam_toolbox` 和 Nav2 obstacle layer 输入可能变化 | Noetic P1 已验证 `/rslidar_points` 和 `/scan` 稳定发布；下一步验证 ROS2 `pointcloud_to_laserscan`、scan frame 和 costmap 消费 | Noetic P1 通过，ROS2 待验证 |
| 外参未测量 | 地图重影、costmap 障碍偏移 | 先完成雷达、IMU、相机、机械臂外参测量 | 待测量 |
| 底盘和 EKF 重复发 TF | Nav2 和 RViz 坐标跳变 | 明确 `odom -> base_footprint` 唯一发布者 | 待验证 |
| IMU 坐标轴不一致 | EKF yaw 错误，地图扭曲 | 静止和原地转向 bag 校验后再接入 | 待验证 |
| 协方差不可信 | 滤波过度相信错误输入 | 从保守初值开始，用实车 bag 调整 | 待测量 |
| 建图速度过快 | 回环失败或地图撕裂 | 建图阶段限制低速，优先质量 | 待验证 |
| 地图版本不可追溯 | 比赛现场参数混乱 | 固定地图、参数、commit 和验证记录 | 待实现 |

## 资料依据

- 本仓库 [总体架构](architecture.md)。
- 本仓库 [系统基线](system_baseline.md)。
- 本仓库 [探索导航避障设计方案](navigation_planning.md)。
- 本仓库 [团队协作](../engineering/team_workflow.md)。
- 本仓库 [终端命令](../engineering/terminal_commands.md)。
- 本仓库 [P3 Nav2 仿真验证记录](../validation/navigation_sim_validation.md)。
