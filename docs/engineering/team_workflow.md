# 团队任务划分与协作流程

## 组织原则

本项目按“可验收能力”分工，而不是按文件分工。7 名成员中，1 人负责系统协调与最终集成，6 人分别负责底盘导航、定位建图、感知识别和采样操控中的关键能力。

所有模块开发都必须围绕固定接口推进：能否按约定发布/订阅 topic、维护 TF、输出状态和被任务状态机调用，是判断模块完成度的主要标准。

## 角色分配

| 角色 | 主责 | 关键交付 | 主要协作对象 |
| --- | --- | --- | --- |
| P0 系统负责人 | 总体架构、接口冻结、进度协调、集成验收、比赛材料总控 | 接口评审记录、每周集成目标、风险清单、提交包 | 全员 |
| A 底盘负责人 | SCOUT MINI bringup、CAN、急停、低速控制 | `/cmd_vel` 可控、`/odom` 稳定、底盘测试记录 | B、C、P0 |
| B 导航负责人 | Nav2、路径规划、避障、返回基地、恢复策略 | 离开基地、搜索点巡航、返回基地、导航失败恢复 | A、C、F、P0 |
| C 定位建图负责人 | LiDAR、IMU、TF、slam_toolbox、robot_localization | `/scan`、`/imu/data`、`/tf`、地图和定位稳定性 | A、B、P0 |
| D 感知检测负责人 | RGB-D、补光、科学目标检测、置信度输出 | 图像采集、目标分类、检测结果 | E、P0 |
| E 目标位姿负责人 | 深度定位、坐标转换、抓取候选、接口桥接 | `/target_detections`、目标在 `base_link` 或 `piper_base_link` 下的 3D 位姿 | D、F、B、P0 |
| F 机械臂采样负责人 | PiPER bringup、末端执行器、抓取和放置动作 | `/joint_states`、抓取序列、放置序列、失败重试 | E、B、P0 |

E 是感知与机械臂之间的接口桥梁，不能只按视觉任务处理。E 输出的目标位姿必须能被 F 直接用于抓取规划，也要能被 B 用于目标接近点规划。

## 小组划分

| 小组 | 成员 | 阶段目标 |
| --- | --- | --- |
| 移动导航组 | A + B + C | 机器人能稳定离开基地、避障、返回基地 |
| 感知识别组 | D + E | 能识别科学目标，并输出可用于抓取的 3D 位姿 |
| 采样操控组 | E + F | 能根据目标位姿完成抓取、携带和放置 |
| 系统集成 | P0 + 各负责人 | 串通“离开-搜索-识别-抓取-返回-放置”全流程 |

## 接口约定

接口变更必须先由 P0 组织评审，再改 `robot_profile.yaml`、接口定义和文档。任何模块不得私自更换 topic、frame 或消息字段。

| 接口 | 类型 | 生产者 | 消费者 | 验收标准 |
| --- | --- | --- | --- | --- |
| `/cmd_vel` | `geometry_msgs/Twist` | B 导航 | A 底盘 | 底盘能低速、可控、可急停地响应速度指令 |
| `/odom` | `nav_msgs/Odometry` | A 底盘 | B、C | 里程计连续、时间戳正常、frame 与 TF 一致 |
| `/scan` | `sensor_msgs/LaserScan` | C 定位建图 | B、C | 雷达数据稳定，坐标系为 `lidar_link` |
| `/imu/data` | `sensor_msgs/Imu` | C 定位建图 | C | IMU 方向、单位、频率经过记录和验证 |
| `/tf`、`/tf_static` | `tf2_msgs/TFMessage` | C、description | 全模块 | 至少包含 `map -> odom -> base_footprint -> base_link` 和传感器/机械臂外参 |
| `/camera/color/image_raw` | `sensor_msgs/Image` | D 感知 | D、E | 彩色图稳定，曝光和补光策略可复现 |
| `/camera/depth/image_rect_raw` | `sensor_msgs/Image` | D 感知 | E | 深度图与彩色图对齐，可用于 3D 位姿估计 |
| `/target_detections` | `base_interfaces/ScienceTargetArray` | E 目标位姿 | B、F、P0 | 每个目标包含类别、置信度、位姿、状态和可采样标记 |
| `/navigation/status` | `base_interfaces/NavigationStatus` | B 导航 | P0、记录系统 | 能追踪当前导航目标、Nav2 action 状态、失败次数和恢复次数 |
| `/joint_states` | `sensor_msgs/JointState` | F 机械臂 | F、P0 | PiPER 关节状态稳定发布 |
| `/mission/state` | `base_interfaces/MissionState` | P0/任务状态机 | 全员、记录系统 | 能追踪阶段、得分、剩余时间和故障 |
| `/execute_mission` | `base_interfaces/ExecuteMission` action | P0/任务状态机 | 比赛启动入口 | 可触发一次完整自主任务 |

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
| `perception/target-pose` | 3D 位姿、坐标转换、抓取候选 | `/target_detections` 可被 B/F 消费 |
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
