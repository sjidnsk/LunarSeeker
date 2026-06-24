# AgileX 平台参数归档

## 来源状态

- 来源标题: SCOUT MINI + PiPER 用户开发指导手册
- 来源链接: https://agilexsupport.yuque.com/staff-hso6mo/uvrydi/kxgnsa8bueub7vhh?singleDoc=%E6%89%93%E5%BC%80
- 读取日期: 2026-06-24
- 归档状态: 已从语雀页面读取参数表，待离线保存 PDF、截图或官方文件副本。
- 使用原则: 本文记录供应商手册参数，不能替代实物称重、装配尺寸测量、接口 bringup 和传感器标定。

## 手册参考配置

| 名称 | 型号 |
| --- | --- |
| 移动平台底盘 | Scout Mini |
| 机械臂 | PiPER |
| 工控机 | Nvidia Jetson Orin Nano |
| 视觉传感器（车体） | 奥比中光 dabai |
| 视觉传感器（手部） | 奥比中光 dabai |
| 路由器 | HUAWEI 4G 路由器 |
| 激光雷达 | Livox Mid360 |
| 惯性传感器 | 超核电子 CH110 |

> 注意: 当前仓库原基线使用 RGB-D 相机、2D LiDAR、IMU 的通用描述；手册记录的奥比中光 dabai、Livox Mid360 和 CH110 需要在硬件选型评审后决定是否替换项目基线。

## Scout Mini 底盘参数

| 类型 | 项目 | 手册值 | 项目状态 |
| --- | --- | --- | --- |
| 机械参数 | 长 x 宽 x 高 | 612 x 580 x 245 mm | 待实测包络 |
| 机械参数 | 轴距 | 451 mm | 待核对 |
| 机械参数 | 前 / 后轮距 | 490 mm | 待核对 |
| 机械参数 | 整备重量 | 23 kg | 待称重 |
| 机械参数 | 电池类型 | 锂电池 | 待核对实物 |
| 机械参数 | 电池参数 | 24 V 15 Ah | 待核对实物 |
| 机械参数 | 动力驱动电机 | 直流无刷 4 x 250 W（麦轮 150 W） | 待核对版本 |
| 机械参数 | 驱动形式 | 四轮独立驱动 | 待 bringup 验证 |
| 机械参数 | 驻车形式 | 伺服刹车 / 防撞管 | 待安全检查 |
| 机械参数 | 转向形式 | 四轮差速转向 | 待 bringup 验证 |
| 机械参数 | 悬挂形式 | 纵臂独立悬挂 | 待核对实物 |
| 机械参数 | 驱动电机减速比 | 1:4.3 | 待核对版本 |
| 机械参数 | 驱动电机传感器 | 霍尔 | 待核对版本 |
| 性能参数 | 防护等级 | IP22 | 待确认比赛环境适配 |
| 性能参数 | 最高速度 | 3 m/s | 比赛应限速调参 |
| 性能参数 | 最小转弯半径 | 0 mm | 待实测 |
| 性能参数 | 最大爬坡能力 | 30 deg | 待场地验证 |
| 性能参数 | 离地间隙 | 115 mm | 待实测 |
| 性能参数 | 最大续航时间 | 8 h | 待按比赛负载验证 |
| 性能参数 | 最大行程 | 10 km | 待按比赛负载验证 |
| 性能参数 | 充电时间 | 2 h | 待核对充电器 |
| 性能参数 | 工作温度 | -10 degC 至 40 degC | 待确认现场环境 |
| 控制参数 | 控制模式 | 遥控控制、指令控制模式 | 比赛需禁用远程干预依赖 |
| 控制参数 | 遥控器 | 2.4 G，遥控距离 50 m | 仅调试与安全使用 |
| 控制参数 | 通讯接口 | CAN | 待 CAN bringup |

## PiPER 机械臂参数

| 类型 | 项目 | 手册值 | 项目状态 |
| --- | --- | --- | --- |
| 结构参数 | 自由度 | 6 | 待 bringup 验证 |
| 结构参数 | 有效负载 | 1.5 kg | 待结合末端执行器验证 |
| 结构参数 | 本体重量 | 4.2 kg | 待称重 |
| 结构参数 | 重复定位精度 | +/- 0.1 mm | 待实测任务精度 |
| 结构参数 | 工作半径 | 626.75 mm | 待抓取可达性验证 |
| 结构参数 | 标准供电电压 | DC 24 V，工作范围 24-26 V | 待供电设计 |
| 结构参数 | 功耗 | 最大不超过 120 W，综合不超过 40 W | 待实测 |
| 结构参数 | 材质 | 铝合金骨架、塑料外壳 | 待核对实物 |
| 结构参数 | 控制器 | 集成 | 待驱动验证 |
| 结构参数 | 通讯方式 | CAN | 待 CAN bringup |
| 结构参数 | 控制方式 | 拖动示教 / 离线轨迹 / API / 上位机 | 比赛程序需采用自主 API 或轨迹执行 |
| 结构参数 | 外部接口 | 电源接口 x1，CAN 接口 x1 | 待线束设计 |
| 结构参数 | 底座安装尺寸 | 70 mm x 70 mm，M5 x4 | 待支架设计 |
| 结构参数 | 工作环境 | -20 至 50 degC，25%-85% RH，非冷凝 | 待现场环境确认 |
| 结构参数 | 噪音 | < 60 dB | 低风险 |
| 运动参数 | 关节运动范围 | J1 +/-154 deg；J2 0-195 deg；J3 -175-0 deg；J4 +/-102 deg；J5 +/-75 deg；J6 +/-120 deg | 待 MoveIt / 轨迹限位同步 |
| 运动参数 | 关节最大速度 | J1 180 deg/s；J2 195 deg/s；J3 180 deg/s；J4 225 deg/s；J5 225 deg/s；J6 225 deg/s | 比赛需限速调参 |

## 工控机参数

手册记录的工控机为 Nvidia Jetson Orin Nano。

| 类型 | 项目 | 手册值 | 项目状态 |
| --- | --- | --- | --- |
| 算力参数 | AI 算力 | 40 TOPS | 待确认具体模组和功耗模式 |
| 算力参数 | 显存带宽 | 68 GB/s | 待确认版本 |
| 算力参数 | CPU 频率 | 1.5 GHz 以上 | 待确认版本 |
| 算力参数 | CPU | 64 位 6 核 Arm Cortex-A78AE v8.2 | 待确认版本 |
| 算力参数 | GPU | Ampere 架构 1024 CUDA 核心和 32 Tensor Core | 待确认版本 |
| 其他参数 | 功耗 | 7-25 W | 待供电和散热验证 |
| 其他参数 | 显存 | 8 GB 128-bit LPDDR5 | 待确认版本 |

## 传感器参数

### Livox Mid360

| 类型 | 项目 | 手册值 | 项目状态 |
| --- | --- | --- | --- |
| 扫描参数 | FOV | 360 x 59 deg | 与 2D LiDAR 基线不一致，待确认导航方案 |
| 扫描参数 | 近处盲区 | 0.1 m | 待安装位验证 |
| 扫描参数 | 10% 反射率量程 | 40 m | 待场地验证 |
| 扫描参数 | 点频 | 200000 点/s | 待驱动和算力评估 |
| 其他参数 | 重量 | 265 g | 待称重 |
| 其他参数 | 尺寸 | 65 x 65 x 60 mm | 待实测含支架包络 |

### CH110 IMU

| 类型 | 项目 | 手册值 | 项目状态 |
| --- | --- | --- | --- |
| 陀螺仪 | 测量范围 | +/- 500 deg/s | 待驱动验证 |
| 陀螺仪 | 分辨率 | 0.01 deg/s | 待数据质量验证 |
| 陀螺仪 | 内部采样频率 | 1 kHz | 待实际发布频率确认 |
| 加速度计 | 测量范围 | +/- 8 G | 待驱动验证 |
| 加速度计 | 分辨率 | 1 uG | 待数据质量验证 |
| 加速度计 | 内部采样频率 | 1 kHz | 待实际发布频率确认 |

## 机械臂软件来源

| 内容 | 地址 | 项目状态 |
| --- | --- | --- |
| SDK | https://github.com/agilexrobotics/piper_sdk | 已列入 `dependencies.repos`，commit 待锁定 |
| SDK-DEMO | https://github.com/agilexrobotics/piper_sdk/tree/master/demo | 待调试参考 |
| SDK-UI | https://github.com/agilexrobotics/Piper_sdk_ui | 待人工评估 |
| ROS1-NOETIC | https://github.com/agilexrobotics/Piper_ros/tree/ros-noetic-no-aloha | 非项目基线 |
| ROS2-HUMBLE | https://github.com/agilexrobotics/Piper_ros/tree/ros-humble-no-aloha | 与项目 ROS2 Humble 基线相关，需核对仓库大小写和分支 |
| URDF | https://github.com/agilexrobotics/piper_ros/tree/noetic/src/piper_description/urdf | 待迁移或核对 Humble 可用版本 |
| MOVEIT2 | https://github.com/agilexrobotics/piper_ros/tree/humble/src/piper_moveit | 待验证 |
| MOVEIT | https://github.com/agilexrobotics/piper_ros/tree/noetic/src/piper_moveit | 非项目基线 |
| GAZEBO | https://github.com/agilexrobotics/piper_ros/tree/noetic/src/piper_sim/piper_gazebo | 非项目基线 |
| ISAAC SIM | https://github.com/agilexrobotics/piper_isaac_sim | 可作为仿真参考 |
| MUJOCO | https://github.com/agilexrobotics/piper_ros/tree/noetic/src/piper_sim/piper_mujoco | 可作为仿真参考 |

## 对项目的直接影响

- 重量风险更高: 仅 Scout Mini 23 kg、PiPER 4.2 kg、Livox Mid360 0.265 kg 的手册小计已达 27.465 kg，尚未包含相机、工控机、路由器、IMU、补光、末端执行器、支架、线束和紧固件。
- 出发包络需要重新核算: Scout Mini 手册尺寸为 612 x 580 x 245 mm，PiPER 工作半径 626.75 mm，装配后必须实测 800 x 800 x 800 mm 出发状态。
- 传感器基线需要评审: 手册记录 Livox Mid360，不是当前文档中泛化的 2D LiDAR；Nav2、slam_toolbox 和点云处理方案需确认。
- CAN 接口需要分配和验证: 底盘与 PiPER 均记录 CAN 通讯，当前 `robot_profile.yaml` 预设 `can0` 和 `can1`，实机 bringup 时需核对。
