# 定位与 SLAM 验证记录

## 当前状态

- 记录日期: 2026-07-02
- 验证范围: 车机 ROS Noetic P2 `robot_localization` 影子模式验证。
- 验证边界: 本记录不代表 ROS2 Humble 主线、Nav2、slam_toolbox 或最终比赛定位链路已完成实车验收。
- 主线配置: ROS2 P2 配置已回流到 `src/algo_localization/config/ekf.yaml`，默认 `publish_tf=false`，仅消费 `/odom.twist.linear.x`、`/odom.twist.angular.z` 和 IMU yaw rate。

## 2026-07-02 P2 EKF 影子模式

### 配置结论

Noetic 车机 P2 调试暴露出厂商 `/odom.pose.covariance` 中 x、y、yaw pose 协方差为 0。为避免 EKF 过度相信不可信 pose，P2 第一轮配置不消费任何 `/odom.pose` 字段。

当前策略:

```text
odom0_config = [false, false, false,
                false, false, false,
                true,  false, false,
                false, false, true,
                false, false, false]
```

含义:

- 使用 `/odom.twist.linear.x`。
- 使用 `/odom.twist.angular.z`。
- 使用 `/imu/data_raw.angular_velocity.z`。
- 不使用 `/odom.pose.x`、`/odom.pose.y`、`/odom.pose.yaw`。
- 不让 EKF 发布 `odom -> base_footprint`，即 `publish_tf=false`。

### 已观测结果

| 检查项 | 结果 | 状态 |
| --- | --- | --- |
| `/odometry/filtered` 频率 | 约 30 Hz，处于诊断允许范围 | 通过 |
| `/odometry/filtered` frame | `header.frame_id=odom`，`child_frame_id=base_footprint` | 通过 |
| EKF diagnostics | `level=0`，`robot_localization` 报告 functioning properly | 静止影子模式通过 |
| IMU 时间戳 | `rostopic delay /imu/data_raw` 约 0.000 s，最大约 0.004 s | 通过 |
| `/odom.pose.covariance` | x、y、yaw pose 协方差为 0 | 源头待修正 |
| TF 接管 | 未启用，`publish_tf=false` | 待 P2 motion bag 通过后再评审 |

### 证据 bag

| bag | 大小 | 内容/用途 | 当前状态 |
| --- | --- | --- | --- |
| `tzb2026/bag/p2_ekf_static.bag` | 5.6 MB | 静止 P2 EKF 影子模式证据 | `rosbag info` 已归档，待回放分析 |
| `tzb2026/bag/p2_ekf_motion.bag` | 14.7 MB | 低速前进、后退、左转、右转动作证据 | `rosbag info` 已归档，待回放分析 |

本仓库 `.gitignore` 已忽略 `*.bag`，bag 文件不应提交到 Git。

#### `p2_ekf_static.bag`

| 项目 | 结果 |
| --- | --- |
| 路径 | `tzb2026/bag/p2_ekf_static.bag` |
| 时长 | 38.0 s |
| 起止时间 | 2026-07-02 18:32:23.41 - 18:33:01.40 |
| 消息数 | 13,330 |
| 压缩 | none |
| topic | `/diagnostics`: 37；`/imu/data_raw`: 7,593；`/odom`: 1,900；`/odometry/filtered`: 1,140；`/tf`: 2,660 |

#### `p2_ekf_motion.bag`

| 项目 | 结果 |
| --- | --- |
| 路径 | `tzb2026/bag/p2_ekf_motion.bag` |
| 时长 | 1:40 s |
| 起止时间 | 2026-07-02 18:35:29.23 - 18:37:09.92 |
| 消息数 | 35,331 |
| 压缩 | none |
| topic | `/diagnostics`: 99；`/imu/data_raw`: 20,130；`/odom`: 5,035；`/odometry/filtered`: 3,020；`/tf`: 7,047 |

### 待补充分析

建议对 motion bag 检查:

- `/odom.twist.linear.x` 前进/后退符号是否与实际动作一致。
- `/odom.twist.angular.z` 与 `/imu/data_raw.angular_velocity.z` 左右转符号是否一致。
- `/odometry/filtered` 在静止、直行、倒车、原地转向过程中是否连续无跳变。
- `/diagnostics` 是否保持 `level=0` 或仅有已记录且可解释的非阻塞警告。
- `publish_tf=false` 下是否无重复 `odom -> base_footprint` 发布者。

## 当前结论

P2 EKF 影子模式静止检查通过，motion bag 已录制但尚未完成回放分析。暂不允许开启 `publish_tf=true` 接管 `odom -> base_footprint`，也不应将该结果视为 P3 建图或 Nav2 实车联调已通过。
