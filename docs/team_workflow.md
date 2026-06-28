# 团队任务划分与协作流程

## 组织原则

本项目按“可验收能力”分工，而不是按文件分工。当前 7 名成员按三条能力线推进：移动自主组负责 SLAM、探索、规划与控制；视觉感知组负责目标识别与感知输出；机械臂组负责 PiPER 采样、携带与放置。系统集成、接口冻结和阶段验收通过每周接口评审共同推进，后续可根据组会决定指定单独接口协调牵头人。

所有模块开发都必须围绕固定接口推进：能否按约定发布/订阅 topic、维护 TF、输出状态和被任务状态机调用，是判断模块完成度的主要标准。

## 任务分工

| 小组 | 成员 | 主责 | 关键交付 | 主要协作对象 |
| --- | --- | --- | --- | --- |
| 移动自主组 | 胡凯、李雨桐、吕思颐 | SLAM、探索策略、路径规划、局部避障、运动控制、返回基地 | `/map`、`/tf`、`/odom` 或 `/odometry/filtered`、导航目标状态、`/cmd_vel` 控制输出、导航失败恢复记录 | 视觉感知组、机械臂组、系统集成 |
| 视觉感知组 | 胡晟源、唐浩松 | RGB-D 采集、目标检测 / 分类 / 分割、目标空间定位、可采样性判断 | 目标类别、置信度、检测框或掩膜、`/target_detections`、必要时输出 `/perception/grasp_candidates` | 移动自主组、机械臂组、系统集成 |
| 机械臂组 | 吕森炜、陈秉民 | PiPER bringup、末端执行器、抓取、携带、放置、失败重试 | `/joint_states`、抓取序列、放置序列、`/manipulation/status`、抓取成功 / 失败结果 | 视觉感知组、移动自主组、系统集成 |
| 系统集成与接口协调 | 全员，后续组会确认牵头人 | 接口冻结、进度协调、集成验收、比赛材料总控 | 接口评审记录、每周集成目标、风险清单、提交包 | 全员 |

视觉感知组是移动自主组与机械臂组之间的接口桥梁，不能只输出“看见了目标”。视觉输出必须同时满足两类消费：移动自主组可据此生成目标接近点，机械臂组可据此验证抓取候选并执行采样动作。

## 小组划分

| 小组 | 成员 | 阶段目标 |
| --- | --- | --- |
| 移动自主组 | 胡凯、李雨桐、吕思颐 | 机器人能稳定离开基地、完成探索、避障、规划控制和返回基地 |
| 视觉感知组 | 胡晟源、唐浩松 | 能识别科学目标，并输出可用于导航接近和机械臂抓取的目标信息 |
| 机械臂组 | 吕森炜、陈秉民 | 能根据目标位姿完成抓取、携带和放置 |
| 系统集成 | 全员，后续组会确认牵头人 | 串通“离开-搜索-识别-抓取-返回-放置”全流程 |

## 接口约定

接口变更必须先由系统集成与接口协调牵头人组织评审；牵头人未指定前，由每周接口评审共同确认。确认后再改 `robot_profile.yaml`、接口定义和文档。任何模块不得私自更换 topic、frame 或消息字段。

| 接口 | 类型 | 生产者 | 消费者 | 验收标准 |
| --- | --- | --- | --- | --- |
| `/cmd_vel` | `geometry_msgs/Twist` | 移动自主组 | 底盘驱动 / bringup | 底盘能低速、可控、可急停地响应速度指令 |
| `/odom` | `nav_msgs/Odometry` | 底盘驱动 / bringup | 移动自主组 | 里程计连续、时间戳正常、frame 与 TF 一致 |
| `/scan` | `sensor_msgs/LaserScan` | LiDAR bringup | 移动自主组 | 雷达数据稳定，坐标系为 `lidar_link` |
| `/imu/data` | `sensor_msgs/Imu` | IMU bringup | 移动自主组 | IMU 方向、单位、频率经过记录和验证 |
| `/tf`、`/tf_static` | `tf2_msgs/TFMessage` | 移动自主组 / description | 全模块 | 至少包含 `map -> odom -> base_link` 和传感器/机械臂外参 |
| `/camera/color/image_raw` | `sensor_msgs/Image` | 视觉感知组 | 视觉感知组 | 彩色图稳定，曝光和补光策略可复现 |
| `/camera/depth/image_rect_raw` | `sensor_msgs/Image` | 视觉感知组 | 视觉感知组 | 深度图与彩色图对齐，可用于 3D 位姿估计 |
| `/target_detections` | `base_interfaces/ScienceTargetArray` | 视觉感知组 | 移动自主组、机械臂组、系统集成 | 每个目标包含类别、置信度、位姿、状态和可采样标记 |
| `/joint_states` | `sensor_msgs/JointState` | 机械臂组 | 机械臂组、系统集成 | PiPER 关节状态稳定发布 |
| `/mission/state` | `base_interfaces/MissionState` | 系统集成 / 任务状态机 | 全员、记录系统 | 能追踪阶段、得分、剩余时间和故障 |
| `/execute_mission` | `base_interfaces/ExecuteMission` action | 系统集成 / 任务状态机 | 比赛启动入口 | 可触发一次完整自主任务 |

## 开发分支

本仓库已初始化为 Git 仓库，建议按以下分支策略组织协作。

| 分支 | 用途 | 合入条件 |
| --- | --- | --- |
| `main` | 稳定可演示版本 | 通过集成验收，禁止直接开发 |
| `integration` | 每周整车联调基线 | 各模块负责人确认接口兼容 |
| `bringup/scout` | SCOUT MINI 底盘和 CAN | `/cmd_vel`、`/odom` 验收通过 |
| `localization/tf-slam` | TF、LiDAR、IMU、建图定位 | TF 树和定位数据验收通过 |
| `nav/nav2` | Nav2、避障、返回基地 | 能完成离开基地和返回基地 |
| `perception/detection` | RGB-D、补光、目标检测 | 能输出目标类别和置信度 |
| `perception/target-pose` | 3D 位姿、坐标转换、抓取候选 | `/target_detections` 可被移动自主组和机械臂组消费 |
| `manipulation/piper` | PiPER、末端执行器、抓取放置 | 静态目标抓取和放置验收通过 |
| `mission/state-machine` | 任务状态机、全流程调度 | 能串联 mock 或真实模块 |
| `docs/*` | 文档、报告、检查单 | 与代码和实测结果一致 |

合并规则：

- 每个分支必须说明影响的 topic、frame、参数和启动文件。
- 涉及接口变更时，必须同步修改 `src/base_interfaces`、`src/base_bringup/config/robot_profile.yaml` 和相关文档。
- 合入 `integration` 前至少完成本模块自测；合入 `main` 前必须完成整车或 mock 集成验收。
- 不提交 rosbag、大模型、构建产物、`build/`、`install/`、`log/`、`__pycache__/`。

## 集成节奏

| 节奏 | 目标 | 产物 |
| --- | --- | --- |
| 每日短会 | 暴露接口阻塞和硬件风险 | 3 条以内：昨天完成、今天目标、阻塞 |
| 每周接口评审 | 冻结本周 topic、frame、参数变化 | 更新 `robot_profile.yaml` 和文档 |
| 每周整车联调 | 验证跨模块链路 | rosbag、视频、问题清单 |
| 每阶段复盘 | 判断能否进入下一阶段 | 验收记录、风险关闭或接受 |

整车联调当天不开发新功能，只修启动、接口、参数、日志和安全问题。
