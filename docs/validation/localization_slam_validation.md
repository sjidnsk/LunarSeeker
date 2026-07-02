# 定位与 SLAM 验证记录

## 当前状态

- 记录日期: 2026-07-02
- 验证范围: 车机 ROS Noetic P2 `robot_localization` 影子模式和 TF 接管验证。
- 验证边界: 本记录不代表 ROS2 Humble 主线、Nav2、slam_toolbox 或最终比赛定位链路已完成实车验收。
- 主线配置: ROS2 P2 配置已回流到 `src/algo_localization/config/ekf.yaml`，默认 `publish_tf=false` 以避免误抢 TF；P3 前需在底盘 `pub_tf=false` 后显式启用 EKF `publish_tf=true`。

## 2026-07-02 P2 EKF 影子模式

### 配置结论

Noetic 车机 P2 调试暴露出厂商 `/odom.pose.covariance` 中 x、y、yaw pose 协方差为 0。为避免 EKF 过度相信不可信 pose，P2 第一轮配置不消费任何 `/odom.pose` 字段。

当前融合策略:

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
- 底盘 `pub_tf=false` 且 EKF `publish_tf=true` 时，由 EKF 发布 `odom -> base_footprint`。

### 已观测结果

| 检查项 | 结果 | 状态 |
| --- | --- | --- |
| `/odometry/filtered` 频率 | 影子模式和 TF 接管模式均约 30 Hz，处于诊断允许范围 | 通过 |
| `/odometry/filtered` frame | `header.frame_id=odom`，`child_frame_id=base_footprint` | 通过 |
| EKF diagnostics | 影子模式和 TF 接管 motion 分析均为 `level=0` | 通过 |
| IMU 时间戳 | `rostopic delay /imu/data_raw` 约 0.000 s，最大约 0.004 s | 通过 |
| `/odom.pose.covariance` | x、y、yaw pose 协方差为 0 | 源头待修正 |
| 影子模式 motion | odom 与 IMU 转向符号 mismatch ratio 为 0.006，滤波输出无跳变 | 通过 |
| TF 接管静止 | `odom -> base_footprint` broadcaster 为 `/ekf_localization`，平均约 30.120 Hz，最近 transform 约 0.022 s old | 通过 |
| TF 接管 motion | odom 与 IMU 转向符号 mismatch ratio 为 0.020，滤波输出无跳变，`base_footprint` parent 为 `odom` | 通过 |

### 证据 bag

| bag | 大小 | 内容/用途 | 当前状态 |
| --- | --- | --- | --- |
| `~/agilex_ws/p2_bags/p2_ekf_static.bag` | 5.6 MB | 静止 P2 EKF 影子模式证据 | `rosbag info` 已归档 |
| `~/agilex_ws/p2_bags/p2_ekf_motion.bag` | 14.7 MB | 影子模式低速前进、后退、左转、右转动作证据 | 分析通过 |
| `~/agilex_ws/p2_bags/p2_ekf_tf_takeover_static.bag` | 5.2 MB | EKF 接管 `odom -> base_footprint` 静止证据 | `rosbag info` 已归档 |
| `~/agilex_ws/p2_bags/p2_ekf_tf_takeover_motion.bag` | 16.5 MB | EKF 接管后的低速动作证据 | 分析通过 |

本仓库 `.gitignore` 已忽略 `*.bag`，bag 文件不应提交到 Git。

#### `p2_ekf_static.bag`

| 项目 | 结果 |
| --- | --- |
| 路径 | `~/agilex_ws/p2_bags/p2_ekf_static.bag` |
| 时长 | 38.0 s |
| 起止时间 | 2026-07-02 18:32:23.41 - 18:33:01.40 |
| 消息数 | 13,330 |
| 压缩 | none |
| topic | `/diagnostics`: 37；`/imu/data_raw`: 7,593；`/odom`: 1,900；`/odometry/filtered`: 1,140；`/tf`: 2,660 |

#### `p2_ekf_motion.bag`

| 项目 | 结果 |
| --- | --- |
| 路径 | `~/agilex_ws/p2_bags/p2_ekf_motion.bag` |
| 时长 | 1:40 s |
| 起止时间 | 2026-07-02 18:35:29.23 - 18:37:09.92 |
| 消息数 | 35,331 |
| 压缩 | none |
| topic | `/diagnostics`: 99；`/imu/data_raw`: 20,130；`/odom`: 5,035；`/odometry/filtered`: 3,020；`/tf`: 7,047 |

影子模式 motion 分析结果:

| 项目 | 结果 |
| --- | --- |
| `/odom.twist.linear.x` | min -0.638，max 0.386，正向样本 432，负向样本 509 |
| `/odom.twist.angular.z` | min -0.624，max 0.443，正向样本 809，负向样本 539 |
| `/imu/data_raw.angular_velocity.z` | min -0.685148，max 0.512037，正向样本 3,266，负向样本 2,178 |
| odom/IMU 转向符号 | checked 1,344，mismatch 8，mismatch ratio 0.006 |
| `/odometry/filtered` 位姿跳变 | max step xy 0.0230 m，`pose_jumps>0.10m=0` |
| `/odometry/filtered` yaw 跳变 | max step yaw 0.0254 rad，`yaw_jumps>0.20rad=0` |
| diagnostics | `levels={0: 198}` |
| TF parent | `base_footprint: {'odom': 5035}` |

#### `p2_ekf_tf_takeover_static.bag`

| 项目 | 结果 |
| --- | --- |
| 路径 | `~/agilex_ws/p2_bags/p2_ekf_tf_takeover_static.bag` |
| 时长 | 38.1 s |
| 起止时间 | 2026-07-02 19:22:51.96 - 19:23:30.03 |
| 消息数 | 11,830 |
| 压缩 | none |
| topic | `/diagnostics`: 37；`/imu/data_raw`: 7,606；`/odom`: 1,903；`/odometry/filtered`: 1,142；`/tf`: 1,142 |

TF 接管静止检查:

| 项目 | 结果 |
| --- | --- |
| TF | `odom -> base_footprint` |
| broadcaster | `/ekf_localization` |
| average rate | 30.120 Hz |
| most recent transform | 0.022 s old |
| 结论 | EKF 成为 `odom -> base_footprint` 权威发布者 |

#### `p2_ekf_tf_takeover_motion.bag`

| 项目 | 结果 |
| --- | --- |
| 路径 | `~/agilex_ws/p2_bags/p2_ekf_tf_takeover_motion.bag` |
| 时长 | 2:00 s |
| 起止时间 | 2026-07-02 19:23:57.10 - 19:25:57.68 |
| 消息数 | 37,480 |
| 压缩 | none |
| topic | `/diagnostics`: 118；`/imu/data_raw`: 24,097；`/odom`: 6,030；`/odometry/filtered`: 3,617；`/tf`: 3,618 |

TF 接管 motion 分析结果:

| 项目 | 结果 |
| --- | --- |
| `/odom.twist.linear.x` | min -0.522，max 0.324，正向样本 660，负向样本 435 |
| `/odom.twist.angular.z` | min -0.554，max 0.372，正向样本 457，负向样本 933 |
| `/imu/data_raw.angular_velocity.z` | min -0.605410，max 0.427614，正向样本 1,888，负向样本 3,792 |
| odom/IMU 转向符号 | checked 1,368，mismatch 28，mismatch ratio 0.020 |
| `/odometry/filtered` 位姿跳变 | max step xy 0.0207 m，`pose_jumps>0.10m=0` |
| `/odometry/filtered` yaw 跳变 | max step yaw 0.0222 rad，`yaw_jumps>0.20rad=0` |
| diagnostics | `levels={0: 236}` |
| TF parent | `base_footprint: {'odom': 3618}` |

注意: TF 接管 motion bag 中未记录到 `imu_link` 静态 TF；这不影响 EKF 接管结论，但 P3 建图启动前仍需确认运行时 `base_link -> imu_link` 和 `base_link -> rslidar` 连通。

## 当前结论

P2 Noetic 验证通过。`robot_localization` 可以在底盘 `pub_tf=false` 且 EKF `publish_tf=true` 的配置下作为 `odom -> base_footprint` 的权威发布者。

该结论允许进入 P3 `slam_toolbox` 建图准备；但它仍不代表 ROS2 Humble 主线、Nav2 实车导航、SLAM 建图质量或最终比赛定位链路已完成验收。P3 前必须重新确认 RoboSense `/scan`、`base_link -> rslidar`、`base_link -> imu_link` 和 EKF TF 发布权。
