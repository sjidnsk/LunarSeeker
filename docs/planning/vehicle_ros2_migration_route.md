# 车机 ROS2 迁移技术路线

## 1. 背景与目标

当前厂商基础代码和车机运行环境存在两套事实:

- 车机现状: Ubuntu 20.04 + ROS Noetic，能承接厂商原始驱动和手册流程。
- 项目目标: Ubuntu 22.04 + ROS2 Humble，作为本仓库主线开发、仿真、任务状态机、导航、感知和操控集成基线。

2026-07-01 硬件与验证状态记录:

- SCOUT MINI、PiPER 和传感器实物已到，传感器线束已连接到车机并上胶固定。
- 本机不具备直接连接传感器进行硬件实测的条件；真实硬件验证需要将代码部署到车机或 ROS2 主控执行。
- 已按 `tzb2026/readme-2451.txt` 在车机执行厂商 ROS Noetic 流程测试，当前反馈为无问题。
- 上述通过状态只代表厂商 Noetic 基线可用，不代表 ROS2 Humble 原生驱动、Nav2、slam_toolbox、MoveIt2 或 `ros2_control` 已完成实机验收。

ROS Noetic 已于 2025-05-31 结束官方生命周期，Ubuntu 20.04 标准支持也已于 2025-05-31 结束。ROS2 Humble 是 Ubuntu 22.04 上的 LTS 发行版，支持到 2027-05。来源:

- https://www.ros.org/blog/noetic-eol/
- https://discourse.openrobotics.org/t/ros-noetic-end-of-life-may-31-2025/43160
- https://ubuntu.com/about/release-cycle
- https://www.openrobotics.org/blog/2022/5/24/ros-2-humble-hawksbill-release

本路线目标不是逐行迁移 `tzb2026/` 厂商代码，而是形成可回滚、可验证、可逐步替换的 ROS2 化闭环:

1. 保留 Noetic 车机作为硬件 fallback。
2. 在 ROS2 Humble 主线建立统一接口和任务能力。
3. 通过最小桥接或双盘验证逐项打通硬件。
4. 将可替换模块迁移到 ROS2 原生驱动。
5. 最终切换到 Ubuntu 22.04 + ROS2 Humble 车机或 ROS2 主控。

## 2. 总体原则

- 不直接在生产车机上原地升级。
- 不直接把 `tzb2026/` 整体改成 ROS2。
- 不在 ROS1 Noetic 上继续开发任务主线。
- 先保命通路，再迁移能力；先可回滚，再切主系统。
- 每个硬件能力必须有独立验收记录，未实测内容保持“待验证”或“待测量”。
- ROS2 主线的 schema、topic、frame、launch 和依赖声明必须是唯一权威定义。

## 3. 推荐总体架构

过渡期采用“双层架构”:

```text
ROS2 主线层
|-- base_mission        任务状态机
|-- algo_perception     目标识别和 3D 位姿
|-- algo_navigation     Nav2 协调、搜索、接近、返回
|-- algo_manipulation   采样、抓取、放置策略
|-- base_bringup        ROS2 启动入口
`-- base_description    URDF、TF、外参

硬件适配层
|-- 方案 A: ROS2 原生驱动
|-- 方案 B: ROS1 Noetic 车机 + ros1_bridge
`-- 方案 C: ROS1 车机只保留为手动回退系统
```

主线策略:

- ROS2 层只消费标准化 topic/action/service。
- ROS1 层只做硬件驱动和最小桥接，不承载任务决策。
- 当某个 ROS2 原生驱动验证通过后，替换对应 ROS1 桥接通道。

## 4. 三阶段迁移路线

### 阶段 A: 车机保留 Noetic，建立 ROS2 主线闭环

适用场景:

- 小车刚到或已确认厂商原始能力，需要保留可回退的硬件基线。
- ROS2 驱动尚未全部确认。
- 比赛时间压力较大，需要保留回退方案。

工作内容:

1. 冻结车机 Noetic 环境。
   - 记录系统镜像、内核版本、ROS 包版本、厂商工作区路径。
   - 记录 CAN、串口、网卡、雷达 IP、相机序列号。
   - 已按 `tzb2026/readme-2451.txt` 验证的厂商流程作为回退基线记录，后续变更需重新留痕。
   - 不在 Noetic 中新增任务主线逻辑。
2. 在开发机或 ROS2 主控上运行本仓库。
   - 保持 Ubuntu 22.04 + ROS2 Humble。
   - 继续推进 mock/sim、任务状态机、Nav2、MoveIt2 设计。
3. 建立最小 ROS1/ROS2 桥接。
   - 仅桥接主线必需接口。
   - 优先使用标准消息，避免自定义消息穿桥。
   - 自定义接口确需桥接时，必须记录桥接构建方式和消息版本。

最小桥接建议:

| 方向 | ROS1 侧 | ROS2 侧 | 消息 | 状态 |
| --- | --- | --- | --- | --- |
| ROS2 -> ROS1 | `/cmd_vel` | `/cmd_vel` | `geometry_msgs/Twist` | 待验证 |
| ROS1 -> ROS2 | `/odom` | `/odom` | `nav_msgs/Odometry` | 待验证 |
| ROS1 -> ROS2 | `/tf`, `/tf_static` | `/tf`, `/tf_static` | `tf2_msgs/TFMessage` | 待验证 |
| ROS1 -> ROS2 | `/scan` | `/scan` | `sensor_msgs/LaserScan` | 待验证 |
| ROS1 -> ROS2 | `/imu/data_raw` | `/imu/data_raw` | `sensor_msgs/Imu` | 待验证 |
| ROS1 -> ROS2 | `/joint_states` | `/joint_states` | `sensor_msgs/JointState` | 待验证 |
| ROS1 -> ROS2 | 相机图像/深度 | ROS2 相机命名空间 | `sensor_msgs/Image` 等 | 待验证 |

阶段 A 验收:

- ROS2 主线可接收底盘 odom、scan、TF、IMU、joint_states。
- ROS2 可发低速 `/cmd_vel`，底盘有可控响应。
- 能录制 ROS2 rosbag，回放后可复现核心状态。
- Noetic 车机保留原厂启动流程，能随时回退。

### 阶段 B: 双盘或备用系统安装 Ubuntu 22.04 + ROS2 Humble

适用场景:

- 已确认 ROS2 主线接口。
- 需要评估车机是否能脱离 Noetic。
- 有备用 SSD、TF 卡、系统镜像或可恢复备份。

工作内容:

1. 制作原车机系统备份。
   - 完整镜像备份，记录恢复步骤。
   - 记录原厂工作区和关键配置文件。
2. 准备 Ubuntu 22.04 + ROS2 Humble 备用系统。
   - 不覆盖原 Noetic 盘。
   - 安装基础依赖、CAN 工具、udev 规则、ROS2 驱动。
3. 逐项验证硬件。
   - 先 CAN 和底盘。
   - 再雷达、IMU、相机。
   - 最后 PiPER 和 MoveIt2。
4. 建立 ROS2 bringup。
   - 单硬件 launch。
   - 组合 bringup launch。
   - 统一日志、rosbag 和检查命令。

硬件验证矩阵:

| 模块 | 首选方案 | fallback | 验收标准 |
| --- | --- | --- | --- |
| SCOUT MINI | `scout_ros2` + `ugv_sdk` | ROS1 `scout_base` + bridge | 低速 `/cmd_vel` 可控，`/odom` 稳定 |
| PiPER | ROS2 分支或 SDK 封装 | ROS1 `piper` + bridge | `/joint_states` 稳定，安全预设动作可执行 |
| 雷达 | ROS2 `rslidar_sdk` 或官方 ROS2 驱动 | ROS1 雷达驱动 + bridge | `/scan` 或点云稳定，frame 正确 |
| RealSense | ROS2 `realsense2_camera` | ROS1 wrapper + bridge | 彩色、深度、相机内参稳定 |
| IMU | ROS2 串口节点或驱动 | ROS1 `serial_imu` + bridge | `sensor_msgs/Imu` 稳定，协方差待标定 |
| TF/URDF | ROS2 `robot_state_publisher` | ROS1 TF bridge | TF 树无断链、无重复发布 |

阶段 B 验收:

- Ubuntu 22.04 车机系统可启动并识别全部关键设备。
- ROS2 单硬件 bringup 逐项通过。
- ROS2 组合 bringup 可运行 30 分钟以上无核心节点异常退出。
- 原 Noetic 系统可在 30 分钟内恢复启动。

### 阶段 C: ROS2 原生主系统切换

适用场景:

- 阶段 B 的关键硬件均通过。
- Nav2、slam_toolbox、MoveIt2 和任务状态机完成实车联调。
- 团队接受 Noetic 仅作为历史 fallback。

工作内容:

1. 固化 ROS2 系统镜像。
   - 记录 OS、ROS、依赖版本、第三方 commit。
   - 固定 udev、CAN、网络、启动服务。
2. 关闭 ROS1 桥接依赖。
   - 每关闭一个桥接 topic，必须有 ROS2 原生替代验收记录。
   - 不保留行为相同的双入口。
3. 固化比赛启动流程。
   - 开机检查。
   - 单硬件健康检查。
   - ROS2 bringup。
   - 任务启动。
   - 日志保存和复位。
4. 保留 Noetic 回退盘。
   - 只用于硬件排错或紧急回退。
   - 不继续接受主线功能开发。

阶段 C 验收:

- 无 ROS1 master 依赖即可完成主流程。
- 端到端任务链路可多次演练。
- 所有启动入口、文档、依赖和测试指向 ROS2 主线。
- Noetic 回退方案已记录，但不影响 ROS2 主线判断。

## 5. 模块迁移优先级

优先级 P0: 先保命、先闭环

- CAN 设备、底盘 `/cmd_vel`、`/odom`。
- 雷达 `/scan` 或点云。
- TF 树。
- rosbag 记录。
- 急停和低速安全控制。

优先级 P1: 支撑自主任务

- Nav2 + slam_toolbox。
- robot_localization。
- RealSense RGB-D。
- 目标识别和 3D 位姿。
- 任务状态机。

优先级 P2: 支撑采样闭环

- PiPER ROS2 控制。
- MoveIt2 配置。
- 夹爪和抓取动作。
- 底盘和机械臂互锁。

优先级 P3: 优化和替代

- 替换残留 ROS1 桥接。
- 优化 launch、参数、日志。
- 统一现场检查单。
- 移除重复入口和废弃脚本。

## 6. 不迁移清单

以下内容不建议从厂商目录逐行迁移:

- ROS1 `gmapping`: 用 `slam_toolbox` 替代。
- ROS1 `move_base`: 用 Nav2 替代。
- MoveIt 1.1.11 源码: 用 MoveIt2 替代。
- ROS1 RealSense nodelet: 用 ROS2 `realsense2_camera` 替代。
- ROS1 RViz 多目标插件: 除非形成明确需求，否则不进入主线。
- GPL v3 的 `rf2o_laser_odometry`: 未完成许可证确认前不进入主线。

可复用内容:

- URDF、mesh、SRDF、joint limits。
- 雷达型号、端口、frame、topic。
- CAN 口和启动顺序。
- 原厂手册中的排错流程。
- 导航参数作为 Nav2 初值参考，但字段必须重写。

## 7. 分支和代码组织

建议分支:

- `hardware/noetic-bridge`: ROS1/ROS2 桥接验证，不作为最终主线。
- `hardware/ros2-bringup`: ROS2 原生硬件 bringup。
- `integration/nav2-field-test`: Nav2 和定位实车参数。
- `integration/piper-moveit2`: PiPER + MoveIt2 采样链路。

目录原则:

- ROS2 主线代码进入 `src/` 对应包。
- 厂商源码保持在 ignored 目录或 `src/third_party/`，不直接提交。
- 桥接脚本进入 `tools/` 或明确实验目录，不能成为主入口。
- 部署检查单、镜像记录、硬件验证记录进入 `docs/engineering/`。

## 8. 测试与验收闭环

每个模块必须完成四类闭环:

1. 静态闭环
   - 依赖声明完整。
   - launch 文件存在。
   - 参数文件可被加载。
   - 本地 Markdown 链接和文档入口有效。
2. 单模块闭环
   - 单硬件节点能启动。
   - topic、frame、频率、消息类型符合约定。
   - 能录制最小 rosbag。
3. 集成闭环
   - 和上游/下游模块完成一次真实数据联调。
   - 失败模式有日志和恢复策略。
4. 任务闭环
   - 能进入任务状态机。
   - 有成功、失败、超时、回退路径。
   - 有复盘记录。

建议验收文件:

- `docs/engineering/hardware_bringup_log.md`
- `docs/engineering/ros1_bridge_validation.md`
- `docs/engineering/ros2_vehicle_installation.md`
- `docs/engineering/field_test_checklist.md`

上述文件尚未建立，状态为待编写。

## 9. 风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| ROS2 底盘驱动不稳定 | 无法安全移动 | 保留 ROS1 底盘 + bridge fallback |
| PiPER ROS2 控制不可用 | 无法采样 | 先用 ROS1 驱动桥接 joint_states，抓取控制另行评估 |
| 车机升级后 CAN 口变化 | 驱动不可用 | 固化 udev 规则，记录 `ip link` 和 `candump` 验证 |
| TF 重复发布 | Nav2/MoveIt2 行为异常 | 明确 TF 唯一发布者，启动前检查 `/tf_static` |
| 自定义消息穿桥困难 | 集成阻塞 | 主线接口优先使用标准消息，自定义接口留在 ROS2 内部 |
| Noetic fallback 长期存在 | 双主线分裂 | 设定阶段 C 验收后停止 ROS1 主线开发 |
| Humble 2027 EOL | 长期维护风险 | 项目后期预留升级到更新 ROS2 LTS 的接口边界 |

## 10. 最终判定标准

只有满足以下条件，才建议把车机主系统切到 Ubuntu 22.04 + ROS2 Humble:

- 原 Noetic 系统已完整备份，且可恢复。
- ROS2 底盘、雷达、IMU、相机、PiPER 均完成单模块验收。
- Nav2、slam_toolbox、MoveIt2 和任务状态机完成至少一次实车集成闭环。
- 不依赖 ROS1 master 也能完成比赛主流程。
- 启动入口唯一，README、docs、launch 和测试一致。
- 所有硬件参数、安装外参、重量和尺寸状态已标注“已验证”或保留明确风险接受记录。

如果上述条件未满足，应继续采用“ROS2 主线 + Noetic 硬件 fallback”的过渡架构。
