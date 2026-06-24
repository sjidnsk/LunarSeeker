# LunarSeeker（月洞探岩）

LunarSeeker（月洞探岩）是面向“月球熔岩洞机器人智能自主采样任务”的 ROS2 Humble 单仓库工作区。项目固定以 **SCOUT MINI + PiPER** 为移动采样平台，在 Ubuntu 22.04、ROS2 Humble、Python 3.10 环境下开发全程自主的目标识别、导航避障、机械臂抓取、携带返回和指定区域放置能力。

> [!IMPORTANT]
> 当前仓库处于项目初始化阶段。重量、尺寸、传感器安装、线束和支架方案必须经过实物测量和复核后，才能作为参赛状态结论。

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

- 仿真 / mock bringup: `ros2 launch tzb_lunar_bringup sim_bringup.launch.py`
- 任务配置: [src/tzb_lunar_bringup/config/robot_profile.yaml](src/tzb_lunar_bringup/config/robot_profile.yaml)
- 任务接口: [src/tzb_lunar_interfaces](src/tzb_lunar_interfaces)
- 任务说明: [docs/mission_brief.md](docs/mission_brief.md)
- 系统基线: [docs/system_baseline.md](docs/system_baseline.md)
- 总体架构: [docs/architecture.md](docs/architecture.md)
- 重量预算: [docs/weight_budget.md](docs/weight_budget.md)
- AgileX 平台参数归档: [docs/vendor_agilex_platform_parameters.md](docs/vendor_agilex_platform_parameters.md)
- 研发路线: [docs/roadmap.md](docs/roadmap.md)
- 团队协作: [docs/team_workflow.md](docs/team_workflow.md)
- 仓库协作规则: [AGENTS.md](AGENTS.md)

## ROS2 环境构建

在 Ubuntu 22.04 + ROS2 Humble 环境中执行:

```bash
vcs import . < dependencies.repos
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 launch tzb_lunar_bringup sim_bringup.launch.py
```

## 目录结构

```text
.
|-- AGENTS.md
|-- dependencies.repos
|-- README.md
|-- docs/
    |-- architecture.md
    |-- mission_brief.md
    |-- roadmap.md
    |-- system_baseline.md
    |-- team_workflow.md
    `-- weight_budget.md
`-- src/
    |-- tzb_lunar_bringup/
    |-- tzb_lunar_description/
    |-- tzb_lunar_interfaces/
    `-- tzb_lunar_mission/
```

第三方驱动源码不直接提交到本仓库，后续在 ROS2 环境中通过 `vcs import . < dependencies.repos` 拉取 `scout_ros2`、`piper_ros` humble 和 `piper_sdk`。

## 资料来源状态

- 本地赛题 PDF: `D:/存储库/项目/挑战杯2026/官方文件/XH-202605_月球熔岩洞机器人智能自主采样任务.pdf`。
- AgileX SCOUT MINI + PiPER 语雀手册: 已读取参数表，归档见 [docs/vendor_agilex_platform_parameters.md](docs/vendor_agilex_platform_parameters.md)，待离线保存。
- `scout_ros2`: 已写入 [dependencies.repos](dependencies.repos)，分支 / commit 仍需在硬件 bringup 阶段锁定。
- `piper_ros` humble: 已写入 [dependencies.repos](dependencies.repos)，commit 仍需在硬件 bringup 阶段锁定。
- 语雀手册链接: 已通过浏览器读取，仍需人工离线归档原始页面或官方副本。
