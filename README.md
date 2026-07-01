# LunarSeeker（月洞探岩）

LunarSeeker（月洞探岩）是面向“月球熔岩洞机器人智能自主采样任务”的 ROS2 Humble 单仓库工作区。项目固定以 **SCOUT MINI + PiPER** 为移动采样平台，在 Ubuntu 22.04、ROS2 Humble、Python 3.10 环境下开发全程自主的目标识别、导航避障、机械臂抓取、携带返回和指定区域放置能力。

> [!IMPORTANT]
> 当前仓库已完成阶段 0 基础文档和 ROS2 工作区构建验收，`colcon build --symlink-install` 已在 Ubuntu 22.04 + ROS2 Humble 环境中确认通过。由于小车尚未到位，阶段 1 实车硬件 Bringup 暂缓，当前先推进 mock/sim 仿真链路。重量、尺寸、传感器安装、线束和支架方案仍必须经过实物测量和复核后，才能作为参赛状态结论。

## 比赛目标

机器人需要在禁止远程干预的条件下自主完成以下流程：

1. 离开基地。
2. 在场地中识别科学目标。
3. 使用机械臂取下目标。
4. 携带至少 1 个目标返回基地。
5. 将目标放置到指定区域。

## 硬约束

- 总重不大于 30 kg。
- 出发尺寸不超过 800 x 800 x 800 mm。
- 单次任务时长 600 秒。
- 每队两次出发机会。
- 全程自主运行，禁止远程干预。

## 系统基线

- 操作系统: Ubuntu 22.04
- ROS: ROS2 Humble
- Python: 3.10
- 底盘: AgileX SCOUT MINI
- 机械臂: AgileX / PiPER
- 传感器: RGB-D 相机、2D LiDAR、IMU
- 辅助硬件: 补光灯、支架、供电与线束
- ROS 组件: Nav2、slam_toolbox、robot_localization、ros2_control

## 开发入口

- 仿真 / mock bringup: `ros2 launch base_bringup sim_bringup.launch.py`
- 任务配置: [src/base_bringup/config/robot_profile.yaml](src/base_bringup/config/robot_profile.yaml)
- 任务接口: [src/base_interfaces](src/base_interfaces)
- 文档地图: [docs/README.md](docs/README.md)
- 任务说明: [docs/planning/mission_brief.md](docs/planning/mission_brief.md)
- 系统基线: [docs/design/system_baseline.md](docs/design/system_baseline.md)
- 总体架构: [docs/design/architecture.md](docs/design/architecture.md)
- 重量预算: [docs/planning/weight_budget.md](docs/planning/weight_budget.md)
- 第三方依赖: [docs/references/third_party_dependencies.md](docs/references/third_party_dependencies.md)
- AgileX 平台参数归档: [docs/references/vendor_agilex_platform_parameters.md](docs/references/vendor_agilex_platform_parameters.md)
- 研发路线: [docs/planning/roadmap.md](docs/planning/roadmap.md)
- 团队协作: [docs/engineering/team_workflow.md](docs/engineering/team_workflow.md)
- 仓库协作规则: [AGENTS.md](AGENTS.md)

## 当前推进状态

- 阶段 0 初始化: 基础文档、ROS2 工作区骨架、接口包、bringup 包、description 包和任务状态机包已建立；`colcon build --symlink-install` 已确认通过。
- 当前推进路径: 小车尚未到位，暂时跳过实车硬件 Bringup，先验证 mock/sim 启动、任务状态机和基础 topic 链路。
- Mock/sim 验证: 当前可发布 mock 目标、mock 导航状态和基础传感器 topic，验证记录见 [docs/engineering/mock_bringup_validation.md](docs/engineering/mock_bringup_validation.md)。
- 阶段 1 硬件 Bringup: 待小车和硬件到位后启动，需验证 SCOUT MINI、PiPER、RGB-D、LiDAR、IMU、基础 TF、URDF 和启动文件。
- 未关闭风险: 重量、出发尺寸、传感器安装、线束、供电、支架和第三方驱动 commit 仍待实测、待归档或待硬件验证锁定。

## ROS2 环境构建

在 Ubuntu 22.04 + ROS2 Humble 环境中执行:

```bash
vcs import . < dependencies.repos
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 launch base_bringup sim_bringup.launch.py
```

## 目录结构

```text
.
|-- AGENTS.md
|-- dependencies.repos
|-- README.md
|-- docs/
    |-- README.md
    |-- design/              # 架构、系统基线
    |-- engineering/         # 协作流程、命令、验证记录
    |-- planning/            # 任务目标、路线、预算
    `-- references/          # 第三方依赖、厂商资料、扫描报告
`-- src/
    |-- base_bringup/            # 启动、launch、参数配置
    |-- base_description/        # URDF、xacro、TF 外参、模型
    |-- base_interfaces/         # msg / srv / action 接口
    |-- base_mission/            # 任务状态机和流程调度
    |-- algo_perception/         # 目标检测、分类、RGB-D 3D 位姿
    |-- algo_localization/       # LiDAR、IMU、里程计融合辅助
    |-- algo_navigation/         # 搜索、接近、返回和 Nav2 协调
    `-- algo_manipulation/       # PiPER 采样、抓取、放置和夹爪
```

第三方驱动源码不直接提交到本仓库，后续在 ROS2 环境中通过 `vcs import . < dependencies.repos` 拉取 `scout_ros2`、`ugv_sdk`、`piper_ros` humble 和 `piper_sdk`。当前导入版本和验证状态见 [docs/references/third_party_dependencies.md](docs/references/third_party_dependencies.md)。

## 资料来源状态

- 本地赛题 PDF: `D:/存储库/项目/挑战杯2026/官方文件/XH-202605_月球熔岩洞机器人智能自主采样任务.pdf`。
- AgileX SCOUT MINI + PiPER 语雀手册: 已读取参数表，归档见 [docs/references/vendor_agilex_platform_parameters.md](docs/references/vendor_agilex_platform_parameters.md)，待离线保存。
- `scout_ros2`、`ugv_sdk`、`piper_ros`、`piper_sdk`: 已写入 [dependencies.repos](dependencies.repos)，当前 commit 记录见 [docs/references/third_party_dependencies.md](docs/references/third_party_dependencies.md)，仍需在硬件 bringup 阶段验证后锁定。
- 语雀手册链接: 已通过浏览器读取，仍需人工离线归档原始页面或官方副本。
