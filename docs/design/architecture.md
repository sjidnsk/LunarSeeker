# 总体架构

## 架构目标

系统围绕“自主搜索、识别、取样、返回、放置”闭环设计。架构优先保证任务流程可恢复、状态可追踪、接口可替换，并把重量、尺寸、光照、越障和抓取可靠性作为一级工程风险。

## 功能分层

```text
base_mission
|-- algo_perception
|-- algo_localization
|-- algo_navigation
|-- algo_manipulation
|-- safety_monitor
`-- base_bringup
```

## 接口冻结原则

跨模块接口以 `src/base_bringup/config/robot_profile.yaml`、`src/base_interfaces` 和本文档为准。任务分工、接口生产者/消费者和分支策略见 [../engineering/team_workflow.md](../engineering/team_workflow.md)。

任何 topic、frame、消息字段或 action 名称变更，都必须同步更新:

- `src/base_interfaces`
- `src/base_bringup/config/robot_profile.yaml`
- 本文档中的接口表
- [../engineering/team_workflow.md](../engineering/team_workflow.md) 中的责任人和验收标准

## 感知

感知模块负责从 RGB-D 相机和补光灯环境中识别科学目标，并输出目标位姿和抓取候选。

建议职责:

- 图像采集、深度对齐和相机标定加载。
- 科学目标检测、分类和置信度输出。
- 目标 3D 位姿估计。
- 可抓取性评估，包括距离、角度、遮挡和工作空间约束。
- 将目标观测写入任务黑板或目标列表。

建议 topic / interface:

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `/camera/color/image_raw` | `sensor_msgs/Image` | 彩色图 |
| `/camera/depth/image_rect_raw` | `sensor_msgs/Image` | 深度图 |
| `/camera/color/camera_info` | `sensor_msgs/CameraInfo` | 相机内参 |
| `/target_detections` | `base_interfaces/ScienceTargetArray` | 目标检测结果 |
| `/perception/grasp_candidates` | 待定义 | 抓取候选 |

## 定位与建图

定位建图模块基于 2D LiDAR、IMU 和底盘里程计建立或加载场地地图，为 Nav2 提供 `map -> odom -> base_link` 变换。

建议组件:

- `slam_toolbox`: 建图和定位。
- `robot_localization`: 融合 wheel odom 与 IMU。
- TF 静态外参: LiDAR、IMU、相机、机械臂基座。

建议 topic / interface:

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `/scan` | `sensor_msgs/LaserScan` | 2D LiDAR |
| `/imu/data` | `sensor_msgs/Imu` | IMU |
| `/odom` | `nav_msgs/Odometry` | 底盘里程计 |
| `/odometry/filtered` | `nav_msgs/Odometry` | 融合里程计 |
| `/map` | `nav_msgs/OccupancyGrid` | 地图 |
| `/tf`, `/tf_static` | `tf2_msgs/TFMessage` | 坐标变换 |

## 导航

导航模块使用 Nav2 完成离开基地、搜索巡航、目标接近、返回基地和到达放置区域。

建议职责:

- 全局路径规划和局部避障。
- 任务点管理: 基地出口、搜索点、目标接近点、返回点、放置点。
- 低速精细接近目标。
- 导航失败恢复: 清 costmap、重新规划、退避、切换候选目标。

建议 topic / interface:

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `/cmd_vel` | `geometry_msgs/Twist` | 底盘速度控制 |
| `/goal_pose` | `geometry_msgs/PoseStamped` | Nav2 目标点 |
| `/navigate_to_pose` | action | Nav2 单目标导航 |
| `/local_costmap/costmap` | `nav_msgs/OccupancyGrid` | 局部代价地图 |

## 操控与采样

操控采样模块负责 PiPER 机械臂初始化、预设位切换、目标接近、抓取、携带保持和放置。

建议职责:

- 机械臂安全上电、回零或就绪检查。
- 末端执行器状态管理。
- 从目标位姿生成抓取位姿。
- 抓取动作序列: 预抓取、接近、闭合、抬升、收回。
- 放置动作序列: 到达放置点、伸臂、下降、释放、回收。

建议 topic / interface:

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `/joint_states` | `sensor_msgs/JointState` | 关节状态 |
| `/arm_controller/follow_joint_trajectory` | action | 关节轨迹 |
| `/gripper/command` | 待定义 | 夹爪控制 |
| `/manipulation/status` | 待定义 | 操控状态 |

## 任务状态机

建议以明确状态机承载 600 秒任务流程，避免模块间隐式耦合。

当前骨架包 `base_mission` 固定以下阶段值，后续算法实现必须保持与 `base_interfaces/msg/MissionState.msg` 一致:

```text
IDLE -> READY -> DEPARTURE -> EXPLORATION -> APPROACH -> SAMPLE -> RETURN -> UNLOAD -> COMPLETE
FAULT 可由任意阶段进入
```

对外接口:

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `/mission/state` | `base_interfaces/MissionState` | 当前任务阶段、估计得分、剩余时间和故障信息 |
| `/execute_mission` | `base_interfaces/ExecuteMission` action | 启动一次完整自主任务 |

失败恢复建议:

- 导航失败: 重试、清图、退避、切换搜索点。
- 识别失败: 调整视角、补光、继续搜索。
- 抓取失败: 重试有限次数，切换候选目标。
- 时间不足: 优先返回基地，避免超时后无有效得分动作。

## Bringup

bringup 应分阶段启动:

1. 基础安全: 急停、供电、底盘、机械臂禁动检查。
2. 传感器: LiDAR、IMU、RGB-D、补光灯。
3. TF 与 URDF: 静态外参和 robot_state_publisher。
4. 状态估计: robot_localization。
5. 建图 / 定位: slam_toolbox。
6. 导航: Nav2。
7. 操控: PiPER 控制和采样动作。
8. 任务: `base_mission` 状态机。

## 日志与可观测性

- 关键 topic 录制 rosbag: 图像可按需要降频或仅记录关键片段。
- 每次任务记录状态机转移、失败原因、耗时和恢复动作。
- 比赛前固定参数版本、地图版本、模型版本和依赖 commit。

## 跨模块交付边界

- A/C 对 B 交付 `/odom`、`/scan`、`/imu/data`、`/tf`，B 不直接读取底层 CAN 或传感器私有接口。
- D/E 对 B/F 交付 `/target_detections`，B/F 不直接依赖检测模型内部输出。
- F 对任务状态机交付机械臂动作成功/失败状态，任务状态机不直接管理单关节控制细节。
- P0 维护 `/mission/state` 和 `/execute_mission`，各模块通过任务状态而不是临时脚本串联。
