# 探索导航避障设计方案

本文定义 LunarSeeker 在 ROS2 Humble 主线中的探索、路径规划、局部避障和导航恢复方案。本文是阶段 4“导航与越障”的设计入口，也约束阶段 2 mock/sim 中的导航验证方式。

当前方案以 SCOUT MINI + PiPER 为平台基线，导航主链路固定使用 Nav2、slam_toolbox、robot_localization 和 ROS2 标准 topic/action。本文所有速度、距离、代价地图和恢复阈值均为初始设计值，未完成实车验证前必须保持“待验证”状态。

## 目标与边界

目标:

- 在 600 秒任务约束内完成离开基地、搜索、目标接近、返回基地和到达放置区。
- 使用 frontier exploration 选择未知区域边界作为探索候选目标。
- 使用 Nav2 完成全局路径规划、局部避障、速度控制和恢复行为。
- 在导航失败时执行有限恢复，并能切换 frontier 或提前返回。
- 保持 `/goal_pose` mock 调试入口，同时为正式流程建立 `/navigate_to_pose` action 协调入口。

非目标:

- 不自研完整全局规划器、局部控制器或代价地图框架。
- 不把 ROS1 `move_base` 参数原样迁入 ROS2 主线。
- 不在 `algo_navigation` 中直接读取 CAN、雷达私有驱动或底盘硬件接口。
- 不把 mock frontier 可视化结果视为实车可达性结论。

## 系统分层

```text
base_mission
`-- algo_navigation
    |-- navigation_coordinator           已实现，正式 Nav2 action 协调入口
    |-- search_strategy                  已实现，frontier 候选选择
    |-- target_approach_strategy         已有几何初版，待接入 TF 和 costmap 验证
    |-- navigation_visualizer            已实现，RViz 调试可视化
    `-- mock_navigation                  已实现，mock /goal_pose 调试出口

Nav2
|-- bt_navigator
|-- planner_server       全局规划
|-- controller_server    局部跟踪和避障
|-- smoother_server      路径平滑，待验证
|-- behavior_server      恢复动作
|-- local_costmap
`-- global_costmap
```

职责边界:

| 模块 | 职责 | 不负责 |
| --- | --- | --- |
| `base_mission` | 决定任务阶段、超时、是否继续搜索或返回 | 不直接发布速度控制 |
| `algo_navigation` | 选择探索目标、目标接近点、返回点，调用 Nav2 action，记录导航结果 | 不实现底盘驱动和传感器驱动 |
| Nav2 | 规划、避障、路径跟踪、恢复动作 | 不决定科学目标是否可采样 |
| `algo_localization` | 提供 `/map`、`/odom`、`/tf`、定位质量 | 不选择任务目标 |
| 底盘 bringup | 提供 `/cmd_vel` 响应和 `/odom` | 不参与任务策略 |

## 输入输出接口

### 输入

| 名称 | 类型 | 生产者 | 用途 | 状态 |
| --- | --- | --- | --- | --- |
| `/mission/state` | `base_interfaces/MissionState` | `base_mission` | 驱动导航模式切换 | 已定义 |
| `/map` | `nav_msgs/OccupancyGrid` | `slam_toolbox` 或 mock map | frontier、global costmap | mock 已验证，实车待验证 |
| `/tf`, `/tf_static` | `tf2_msgs/TFMessage` | localization / description | 坐标转换 | 外参待验证 |
| `/odom` 或 `/odometry/filtered` | `nav_msgs/Odometry` | 底盘 / `robot_localization` | 控制器速度估计 | 实车待验证 |
| `/scan` | `sensor_msgs/LaserScan` | LiDAR 驱动 | obstacle layer 和避障 | 实车待验证 |
| `/target_detections` | `base_interfaces/ScienceTargetArray` | 感知定位 | 目标接近点生成 | mock/实车待验证 |

### 输出

| 名称 | 类型 | 消费者 | 用途 | 状态 |
| --- | --- | --- | --- | --- |
| `/navigate_to_pose` | Nav2 action | Nav2 | 正式单目标导航入口 | 待接入 |
| `/cmd_vel` | `geometry_msgs/Twist` | SCOUT MINI 底盘 | 底盘速度控制 | 由 Nav2 输出，实车待验证 |
| `/goal_pose` | `geometry_msgs/PoseStamped` | RViz / mock Nav2 | 调试目标点 | 已有 mock 出口 |
| `/navigation/search_path` | `nav_msgs/Path` | RViz | frontier 候选排序显示 | 已实现 |
| `/navigation/search_markers` | `visualization_msgs/MarkerArray` | RViz | 搜索、目标和恢复可视化 | 已实现 |
| `/navigation/status` | `base_interfaces/NavigationStatus` | `base_mission` / 日志 | 导航模式、目标类型、Nav2 action 结果和恢复摘要 | P2 输出 |

接口原则:

- `/goal_pose` 保留为调试出口，不作为正式任务状态机的唯一控制接口。
- 正式自主任务由 `algo_navigation` 内的协调节点调用 `/navigate_to_pose`，并将成功、失败、取消、超时原因反馈给 `base_mission`。
- `/navigation/status` 为 P2 自定义状态消息；后续字段变更必须同步 `base_interfaces`、本文和团队接口表。

## 坐标系与地图前提

基础 TF:

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

约束:

- Nav2 全局规划使用 `map` frame。
- 底盘或仿真世界发布 `odom -> base_footprint`；URDF 和 `robot_state_publisher` 发布 `base_footprint -> base_link` 及传感器、轮系 TF。
- 局部控制和障碍观测以 `base_link` / `base_footprint` 为机器人基准，具体 frame 需与 URDF 和 Nav2 参数一致。
- mock 调试可继续使用 `odom` 作为 `map_frame_id`，接入 slam_toolbox 后切换到 `map`。
- 目标检测如果在相机 frame 下输出，必须先经 TF 转换到导航可消费 frame，再生成接近点。

## 总体导航状态机

导航子系统内部建议使用以下状态，不替代 `base_mission` 的全局任务阶段:

```text
IDLE
`-- WAIT_FOR_LOCALIZATION
    `-- DEPART_BASE
        `-- EXPLORE
            |-- APPROACH_TARGET
            |-- SWITCH_FRONTIER
            |-- RETURN_HOME
            `-- NAV_RECOVERY
                |-- CLEAR_COSTMAP
                |-- BACKUP_OR_WAIT
                |-- RETRY_GOAL
                `-- FAIL_GOAL
```

状态说明:

| 状态 | 进入条件 | 动作 | 退出条件 |
| --- | --- | --- | --- |
| `WAIT_FOR_LOCALIZATION` | 任务启动后 | 检查 TF、地图、odom、scan | 核心输入稳定 |
| `DEPART_BASE` | `DEPARTURE` 阶段 | 导航到基地出口点 | 到达或失败 |
| `EXPLORE` | `EXPLORATION` 阶段 | 选择 frontier 并调用 Nav2 | 发现目标、无候选、超时 |
| `APPROACH_TARGET` | 有可采样目标 | 导航到 standoff 接近点 | 到达、目标丢失或失败 |
| `SWITCH_FRONTIER` | frontier 导航失败或候选失效 | 标记候选为暂不可用，选择下一个 | 新目标可用或候选耗尽 |
| `RETURN_HOME` | 采样完成或剩余时间不足 | 导航回基地或放置区 | 到达或失败 |
| `NAV_RECOVERY` | Nav2 返回失败/卡住/超时 | 清 costmap、退避、等待、重试 | 恢复成功或失败升级 |

## 探索目标选择

当前主线已经采用 frontier exploration。算法输入为 `/map`，从已知自由区和未知区边界提取 frontier cluster，并按任务区域偏置排序。

候选选择规则:

1. 只从已知 free cell 中选择与 unknown cell 相邻的 frontier cell。
2. 使用 8 连通聚类形成 frontier cluster。
3. 过滤小于 `frontier.min_cluster_size` 的碎片。
4. 对每个 cluster 选择代表点:
   - 有任务区域时，优先选离任务区域最近且离机器人较近的点。
   - 无任务区域时，使用 cluster 中心。
5. 评分:
   - 机器人距离越近越优。
   - 离任务区域越近越优。
   - 位于任务区域内有额外加分。
6. 选择排序第一的 candidate 作为 Nav2 目标。

探索候选需要增加的运行期约束:

| 约束 | 说明 | 初始建议 |
| --- | --- | --- |
| reachability check | 发送 Nav2 前先用 global costmap 或 planner 试算路径 | 待实现 |
| blacklist TTL | 失败 frontier 暂时拉黑，避免原地反复失败 | 30 秒，待验证 |
| minimum separation | 新 frontier 与上一个失败目标距离太近时跳过 | 0.5 m，待验证 |
| goal tolerance | frontier 目标允许到达附近，不要求压到边界点 | 0.3-0.5 m，待验证 |
| time budget | 剩余时间不足时停止探索并返回 | 180 秒阈值待验证 |

## 目标接近策略

目标接近不直接导航到科学目标中心，而是生成 standoff 接近点。

流程:

1. 从 `/target_detections` 选取 `selected_for_sampling=true` 且 pose frame 有效的目标。
2. 将目标 pose 转换到 `map` 或 `odom` frame。
3. 以目标与机器人连线方向生成接近点，距离目标 `target_standoff_m`。
4. 检查接近点是否在 free space 内。
5. 若接近点不可达，围绕目标生成多个候选角度。
6. 按路径可达性、接近角、机械臂工作空间和安全距离排序。
7. 调用 Nav2 导航到最佳接近点。

初始参数:

| 参数 | 初始值 | 状态 |
| --- | --- | --- |
| `target_standoff_m` | 0.45 m | 待验证 |
| 接近点候选角度 | 目标方向、左右 30 度、左右 60 度 | 待验证 |
| 接近成功容差 | 0.10-0.20 m | 待验证 |
| 接近 yaw | 朝向目标 | 待验证 |

## 返回基地与放置区策略

返回策略必须优先于继续探索，尤其接近 600 秒任务上限时。

建议定义三个固定任务点:

| 点位 | 用途 | 来源 | 状态 |
| --- | --- | --- | --- |
| `base_exit` | 离开基地后的第一个可导航点 | 实测地图或场地坐标 | 待测量 |
| `base_return` | 返回基地入口点 | 实测地图或场地坐标 | 待测量 |
| `sample_drop_zone` | 放置目标的底盘停靠点 | 实测地图或场地坐标 | 待测量 |

返回触发条件:

- 已成功采样至少 1 个目标。
- 剩余时间低于返回预算阈值。
- frontier 候选耗尽。
- 定位质量下降且继续探索风险过高。
- 导航连续失败超过阈值。

返回预算建议:

```text
return_budget_sec =
  estimated_return_path_length_m / conservative_speed_mps
  + placement_time_sec
  + recovery_margin_sec
```

初始取值待验证:

- `conservative_speed_mps`: 0.25 m/s
- `placement_time_sec`: 60 s
- `recovery_margin_sec`: 60 s

## Nav2 组件选择

第一阶段优先使用 Nav2 标准插件，避免新增第三方导航依赖。

| 能力 | 推荐组件 | 理由 | 备选 |
| --- | --- | --- | --- |
| 全局规划 | NavFn 或 Smac 2D | NavFn 配置简单；Smac 2D 对代价更敏感 | 待仿真对比 |
| 局部控制 | Regulated Pure Pursuit | 适合低速服务机器人，能按曲率和障碍距离降速 | DWB |
| 行为树 | Nav2 默认 `navigate_to_pose_w_replanning_and_recovery.xml` | 自带重规划和恢复框架 | 后续裁剪 |
| 代价地图 | `static_layer`、`obstacle_layer`、`inflation_layer` | RoboSense 点云转 `/scan` 后复用 LaserScan 避障链路 | voxel layer，若后续直接使用点云 |
| 定位建图 | `slam_toolbox` + `robot_localization` | 符合项目基线 | AMCL，若使用固定地图 |
| 速度平滑 | `nav2_velocity_smoother` | 限制加速度和突变 | 底盘驱动限速 |

选择原则:

- mock/sim 阶段先跑通 NavFn + RPP。
- 如果 NavFn 路径贴障明显或转角不稳，再对比 Smac 2D。
- 如果 RPP 在窄空间跟踪不稳定，再对比 DWB。
- 不在未完成仿真和实车对比前引入 MPPI 等更重配置。
- ROS2 Humble 的插件 ID 必须以本机 `/opt/ros/humble/share` 中的插件 XML 和 `nav2_bringup` 示例为准；本机当前 NavFn 为 `nav2_navfn_planner/NavfnPlanner`，Smac 2D 为 `nav2_smac_planner/SmacPlanner2D`，DWB 为 `dwb_core::DWBLocalPlanner`，RPP 为 `nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController`。

## 代价地图设计

### Global Costmap

用途:

- 基于静态地图或 SLAM 地图完成全局路径规划。
- 为 frontier 可达性检查提供规划依据。

建议层:

```text
global_costmap:
  plugins:
    - static_layer
    - obstacle_layer
    - inflation_layer
```

说明:

- `static_layer` 使用 `/map`。
- `obstacle_layer` 接入 `/scan`，用于动态障碍或 SLAM 未及时固化的障碍。
- `inflation_layer` 作为最后一层，提供安全边界。

### Local Costmap

用途:

- 跟踪路径时实时避障。
- 处理临时障碍、目标附近低速接近和窄空间修正。

建议层:

```text
local_costmap:
  rolling_window: true
  plugins:
    - obstacle_layer
    - inflation_layer
```

### 机器人 footprint

SCOUT MINI 参考尺寸为 612 mm x 580 mm。由于机械臂、相机、雷达和补光灯支架会改变外廓，Nav2 footprint 必须以最终装配尺寸复核。

初始 footprint 仅作仿真和保守避障参考:

```text
[ [0.36, 0.34], [0.36, -0.34], [-0.36, -0.34], [-0.36, 0.34] ]
```

状态: 待测量。

### 初始参数建议

| 参数 | 初始值 | 说明 | 状态 |
| --- | --- | --- | --- |
| global resolution | 0.05 m | 与常见 2D 栅格地图一致 | 待验证 |
| local width/height | 3.0 m / 3.0 m | 覆盖低速避障视野 | 待验证 |
| robot footprint padding | 0.03 m | 给结构误差留余量 | 待测量 |
| inflation radius | 0.35-0.45 m | 依据车宽和场地通道调整 | 待验证 |
| cost scaling factor | 2.5-4.0 | 控制贴障程度 | 待验证 |
| obstacle range | 2.5-3.0 m | 依据雷达和场地设置 | 待验证 |
| raytrace range | 3.0-3.5 m | 清除远端自由空间 | 待验证 |

## 速度与运动约束

SCOUT MINI 参考最大速度很高，但比赛自主采样应采用低速保守策略。

建议任务模式速度:

| 模式 | 线速度上限 | 角速度上限 | 加速度上限 | 说明 |
| --- | --- | --- | --- | --- |
| `depart` | 0.25 m/s | 0.6 rad/s | 0.3 m/s^2 | 离开基地，避免初始碰撞 |
| `explore` | 0.35 m/s | 0.8 rad/s | 0.4 m/s^2 | 搜索巡航 |
| `approach` | 0.12 m/s | 0.4 rad/s | 0.2 m/s^2 | 目标附近精细接近 |
| `return` | 0.40 m/s | 0.8 rad/s | 0.4 m/s^2 | 路径稳定时返回 |
| `recovery` | 0.08 m/s | 0.3 rad/s | 0.15 m/s^2 | 退避和恢复 |

状态: 全部待实车验证。未验证前不得按 SCOUT MINI 厂商最大速度调参。

## 避障策略

避障分三层:

1. 规划层避障:
   - global costmap 膨胀障碍，尽量生成远离障碍的路径。
   - frontier 目标必须先做路径可达性检查。
2. 控制层避障:
   - local costmap 接入 `/scan`。
   - RPP/DWB 根据局部障碍降低速度或重选控制。
3. 任务层避障:
   - 连续失败时切换 frontier。
   - 目标附近低速接近，必要时放弃目标。
   - 返回阶段减少探索行为，优先保守到达基地。

障碍分类:

| 类别 | 来源 | 处理 |
| --- | --- | --- |
| 静态障碍 | 地图 / SLAM | global costmap 避障 |
| 临时障碍 | `/scan` | local obstacle layer 避障 |
| 未知区域边界 | `/map` unknown | frontier 选择可以接近，但 Nav2 不应穿越不可确认障碍 |
| 低矮/视觉可见障碍 | RGB-D 或人工场地记录 | 第一阶段只记录风险，不进入主线依赖 |
| 机械臂外伸导致外廓变化 | 机械臂状态 | 采样时底盘应停止；移动时机械臂保持收回位 |

## 恢复策略

恢复策略分为 Nav2 内部恢复和任务层恢复。

### Nav2 内部恢复

第一阶段使用默认行为树的重规划和恢复框架:

| 失败点 | 恢复动作 |
| --- | --- |
| 全局规划失败 | 清 global costmap，重试规划 |
| 路径跟踪失败 | 清 local costmap，重试跟踪 |
| 卡住或超时 | wait、backup、必要时 spin |

注意:

- SCOUT MINI 差速底盘可原地转向，但带机械臂和支架后 spin 是否安全待验证。
- 目标接近和窄空间内 backup 距离必须小，避免撞目标或基地结构。

### 任务层恢复

| 场景 | 第一次 | 第二次 | 第三次 |
| --- | --- | --- | --- |
| frontier 不可达 | 清 costmap 重试 | 拉黑该 frontier，选下一个 | 若候选耗尽则返回 |
| 路径跟踪超时 | 降速重试 | 退避后重试 | 切换 frontier |
| 目标接近失败 | 换接近角 | 放弃该目标，继续搜索 | 返回或故障 |
| 返回基地失败 | 清图重试 | 降速并使用备选返回点 | 进入 `FAULT` 或请求人工赛后处理 |
| 定位质量异常 | 等待和静止重定位 | 返回最近安全点 | 停止任务 |

建议阈值:

| 参数 | 初始值 | 状态 |
| --- | --- | --- |
| 单目标 Nav2 重试次数 | 2 | 待验证 |
| frontier blacklist TTL | 30 s | 待验证 |
| 路径跟踪无进展超时 | 10 s | 待验证 |
| 单次导航总超时 | 按路径长度估算，最低 20 s | 待验证 |
| 连续导航失败上限 | 3 | 待验证 |

## 时间预算策略

任务总时长为 600 秒，导航不能只追求探索覆盖。

建议预算:

| 阶段 | 预算 | 说明 |
| --- | --- | --- |
| bringup 后自检 | 30 s | 比赛计时前/后需按规则确认 |
| 离开基地 | 30-60 s | 待实测 |
| 探索与识别 | 240-300 s | 主要搜索窗口 |
| 接近与采样 | 120-180 s | 依赖机械臂速度 |
| 返回与放置 | 120-180 s | 必须保守预留 |

返回触发建议:

```text
if remaining_time_sec < estimated_return_sec + placement_time_sec + recovery_margin_sec:
    stop_exploration()
    navigate_return_home()
```

估算值必须由实车 rosbag 和演练记录更新。

## 实施路线

### P0: 设计冻结与 mock 合同

产物:

- 本文档。
- `algo_navigation` 保持唯一 frontier 策略入口。
- 明确 `/goal_pose` 为 mock 调试出口，`/navigate_to_pose` 为正式 Nav2 入口。

验收:

- 文档入口可被团队引用。
- 当前 frontier 单测继续通过。

### P1: Nav2 参数与 launch 初版

产物:

- `src/base_bringup/config/nav2_params.yaml`，已新增。
- `src/base_bringup/launch/nav2_bringup.launch.py`，已新增。
- 参数覆盖 planner、controller、costmap、behavior、bt navigator、velocity smoother。

验收:

- 仿真或 mock 地图下 Nav2 lifecycle 能启动。
- `/map`、`/tf`、`/odom`、`/scan` 输入缺失时有明确错误。
- RViz 可看到 global/local costmap 和规划路径。

### P2: Nav2 action 协调节点

产物:

- `algo_navigation` 新增正式协调节点 `navigation_coordinator`。
- 输入 `/mission/state`、`/target_detections`、`/map`。
- 输出 `/navigate_to_pose` action goal 和 `base_interfaces/NavigationStatus` 导航状态。

验收:

- exploration 阶段能选择 frontier 并发送 Nav2 goal。
- approach 阶段能从目标检测生成接近点。
- return 阶段能导航到返回点。
- 失败时能切换候选或返回。

### P3: 仿真验证

产物:

- `src/base_bringup/launch/nav2_sim_validation.launch.py`，P3 一键仿真验收入口。
- `src/algo_navigation/rviz/nav2_sim_validation.rviz`，P3 RViz 可视化布局。
- `src/algo_navigation/algo_navigation/navigation_sim_world.py`，轻量 2D 仿真世界，发布 `/map`、`/tf`、`/odom`、`/scan`、`/joint_states` 并订阅 `/cmd_vel`。
- `src/algo_navigation/algo_navigation/navigation_scenario_driver.py`，任务场景驱动，发布 `/mission/state` 和 `/target_detections`，监听 `/navigation/status`。
- `src/algo_navigation/config/navigation_sim_scenarios.yaml`，简化场地地图、静态障碍、动态障碍和目标点场景配置。
- `docs/validation/navigation_sim_validation.md`，rosbag 和验证记录。

验证链路:

```text
navigation_sim_world
|-- /map
|-- /tf, /tf_static
|-- /odom
|-- /scan
`-- /joint_states

navigation_scenario_driver
|-- /mission/state
`-- /target_detections

navigation_coordinator
`-- /navigate_to_pose

Nav2
`-- /cmd_vel

navigation_sim_world
`-- 根据 /cmd_vel 更新 /odom、/tf、/scan 和 /joint_states
```

P3 的 TF 链路为 `map -> odom -> base_footprint -> base_link`。`navigation_sim_world` 只发布 `odom -> base_footprint`，`base_footprint -> base_link`、传感器 link 和轮子 link 由 `robot_state_publisher` 根据 URDF 和 `/joint_states` 发布。

场景:

| 场景 | 用途 | 预期 |
| --- | --- | --- |
| `nominal` | 成功闭环 | 完成 `base_exit -> frontier -> target_approach -> base_return` |
| `frontier_unreachable` | frontier 不可达 | frontier 失败后进入 blacklist，候选耗尽时发布 `STATUS_RETURN_RECOMMENDED` |
| `local_obstacle_blocked` | 局部障碍 | 动态障碍出现在 `/scan` 中，触发恢复反馈或导航失败 |
| `target_approach_failed` | 目标接近失败 | selected target 的 standoff 接近点被阻断，发布目标接近失败状态 |

推荐命令:

```bash
ros2 launch base_bringup nav2_sim_validation.launch.py scenario:=nominal
ros2 launch base_bringup nav2_sim_validation.launch.py scenario:=nominal use_rviz:=false
ros2 launch base_bringup nav2_sim_validation.launch.py scenario:=frontier_unreachable
ros2 launch base_bringup nav2_sim_validation.launch.py scenario:=local_obstacle_blocked
ros2 launch base_bringup nav2_sim_validation.launch.py scenario:=target_approach_failed
```

rosbag 记录:

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

验收:

- 可完成离开基地、frontier 搜索、接近点导航、返回基地。
- 至少验证三类失败: frontier 不可达、局部障碍、目标接近失败。
- 每个场景保留 rosbag 路径、启动命令、commit、期望结果、实际结果和待验证问题。
- RViz 重点查看 `Robot Model`、TF、`Sim Map`、`LaserScan`、`Nav2 Plan`、global/local costmap 和 `Odom Trail`。当前 RPP 控制器不发布 DWB trajectory 调试 topic，手动添加 `Trajectory` 显示项时报错不作为 P3 失败依据。
- P3 结果只代表轻量仿真闭环，不代表实车定位、避障、底盘响应或采样成功。

### P4: 实车低速验证

产物:

- 车机或 ROS2 主控上的 Nav2 bringup 记录。
- TF、地图、costmap、路径、cmd_vel、odom rosbag。
- 参数变更记录。

验收:

- 低速 `/cmd_vel` 可控且急停有效。
- 机器人能到达 2-3 个短距离目标点。
- 局部障碍出现时能停止或绕行。
- 失败恢复不会造成明显碰撞风险。

### P5: 搜索与返回闭环

产物:

- 搜索区参数、返回点和放置点实测坐标。
- 时间预算更新。
- 导航失败恢复策略复盘记录。

验收:

- 能在限定区域内搜索并返回基地。
- 至少完成多次 600 秒内演练，记录耗时和失败点。

## 验证清单

### 静态检查

- `robot_profile.yaml` 中 topic 和本文一致。
- `architecture.md` 中导航接口和本文一致。
- 新增 launch、参数或节点后同步更新 README / docs。
- 新增依赖后同步更新 `package.xml`、`setup.py` 或 `CMakeLists.txt`。

### Mock/sim 检查

- `python3 -m pytest src/algo_navigation/test`
- `colcon build --symlink-install`
- `ros2 launch algo_navigation navigation_visualization.launch.py`
- Nav2 参数接入后补充 `ros2 launch base_bringup nav2_bringup.launch.py`

### 实车检查

- `ros2 topic hz /odom`
- `ros2 topic hz /scan`
- `ros2 run tf2_tools view_frames`
- RViz 检查 TF、map、global costmap、local costmap、planned path。
- 低速目标点测试前确认急停和人工接管流程。

## 风险与待验证项

| 风险 | 影响 | 应对 | 状态 |
| --- | --- | --- | --- |
| RoboSense 点云到 `/scan` 转换未验证 | Nav2 obstacle layer 输入可能变化 | 先验证 `rslidar_sdk`、`/rslidar_points`、pointcloud-to-scan 和 scan frame，再评审是否需要点云 costmap | 待验证 |
| 外参未标定 | costmap 障碍位置错误 | 先完成 TF/URDF 实测 | 待测量 |
| footprint 未复核 | 贴障或误判不可通行 | 以最终装配外廓重算 footprint | 待测量 |
| 地图漂移 | frontier 选择和返回失败 | slam_toolbox/robot_localization 联调，必要时使用固定地图定位 | 待验证 |
| 目标附近障碍复杂 | 接近点不可达或碰撞 | 多角度接近点和低速模式 | 待验证 |
| 默认恢复动作过激 | 原地旋转或退避造成风险 | 限制 recovery 速度和距离，实车前单独测试 | 待验证 |
| 时间预算过乐观 | 采样后无法返回 | 保守返回阈值，优先拿到有效得分 | 待验证 |

## 资料依据

- 本仓库 [总体架构](architecture.md)。
- 本仓库 [系统基线](system_baseline.md)。
- 本仓库 [定位建图与 SLAM 专项设计方案](localization_slam.md)。
- 本仓库 [研发路线](../planning/roadmap.md)。
- 本仓库 [导航搜索可视化](../engineering/navigation_visualization.md)。
- Nav2 官方 Planner Server 文档: https://docs.nav2.org/configuration/packages/configuring-planner-server.html
- Nav2 官方 Controller Server 文档: https://docs.nav2.org/configuration/packages/configuring-controller-server.html
- Nav2 官方 Costmap 2D 文档: https://docs.nav2.org/configuration/packages/configuring-costmaps.html
- Nav2 官方 Behavior Tree 恢复流程文档: https://docs.nav2.org/behavior_trees/overview/detailed_behavior_tree_walkthrough.html
- Nav2 官方 SLAM 导航教程: https://docs.nav2.org/tutorials/docs/navigation2_with_slam.html
