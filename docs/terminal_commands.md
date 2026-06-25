# 终端命令速查

本文档整理 LunarSeeker（月洞探岩）项目常用终端命令。默认环境为 Ubuntu 22.04 + ROS2 Humble + Python 3.10。

## 1. 环境检查

如果终端处于 conda `base` 环境，先退出:

```bash
conda deactivate
```

检查 Python、ROS2、colcon 和 Git:

```bash
which python3
python3 --version
which ros2
ros2 --version
which colcon
git --version
```

期望结果:

- `python3` 优先来自系统路径，例如 `/usr/bin/python3`。
- Python 版本为 3.10。
- `ROS_DISTRO` 为 `humble`。

```bash
echo $ROS_DISTRO
```

## 2. ROS2 环境加载

每个新终端都需要先加载 ROS2:

```bash
source /opt/ros/humble/setup.bash
```

项目构建完成后，再加载本工作区:

```bash
source install/setup.bash
```

## 3. 首次获取项目

```bash
git clone https://github.com/sjidnsk/LunarSeeker.git
cd LunarSeeker
```

## 4. 安装基础工具

```bash
sudo apt update
sudo apt install python3-colcon-common-extensions python3-vcstool python3-rosdep
```

初始化 rosdep。若提示已经初始化过，可以跳过:

```bash
sudo rosdep init
rosdep update
```

## 5. 导入第三方依赖

项目的第三方仓库记录在 `dependencies.repos`:

```bash
vcs import . < dependencies.repos
```

第三方源码会导入到 `src/third_party/`，该目录不直接提交到主仓库。当前导入版本和待验证状态见 [third_party_dependencies.md](third_party_dependencies.md)。

## 6. 安装 ROS 依赖

```bash
rosdep install --from-paths src --ignore-src -r -y
```

## 7. 构建项目

完整构建:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

只构建指定包:

```bash
colcon build --symlink-install --packages-select base_interfaces
colcon build --symlink-install --packages-select base_bringup
colcon build --symlink-install --packages-select base_mission
```

## 8. 运行 Mock Bringup

硬件未到位时，先运行 mock/sim 启动入口:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch base_bringup sim_bringup.launch.py
```

该启动入口会运行 `robot_state_publisher`、`mission_state_machine`，并在 `use_mock_hardware:=true` 时启动 `mock_base_sensors`，发布 `/odom`、`/scan`、`/imu/data`、`/joint_states` 和空的 `/target_detections`。

指定参数:

```bash
ros2 launch base_bringup sim_bringup.launch.py
use_mock_hardware:=true mission_time_limit_sec:=600
```

## 9. 查看接口

```bash
ros2 interface show base_interfaces/msg/MissionState
ros2 interface show base_interfaces/msg/ScienceTarget
ros2 interface show base_interfaces/msg/ScienceTargetArray
ros2 interface show base_interfaces/action/ExecuteMission
```

## 10. 查看 Topic

列出所有 topic:

```bash
ros2 topic list
```

查看关键 topic:

```bash
ros2 topic echo /mission/state
ros2 topic echo /odom
ros2 topic echo /scan
ros2 topic echo /imu/data
ros2 topic echo /joint_states
ros2 topic echo /target_detections
```

查看发布频率:

```bash
ros2 topic hz /odom
ros2 topic hz /scan
ros2 topic hz /imu/data
ros2 topic hz /joint_states
ros2 topic hz /target_detections
```

## 11. 查看节点

```bash
ros2 node list
ros2 node info /mission_state_machine
ros2 node info /mock_base_sensors
```

## 12. 调用任务 Action

查看 action:

```bash
ros2 action list
ros2 action info /execute_mission
```

发送一次 mock 任务目标:

```bash
ros2 action send_goal /execute_mission base_interfaces/action/ExecuteMission "{run_index: 1, use_mock_hardware: true, profile_name: 'mock'}"
```

## 13. TF 检查

生成 TF 树:

```bash
ros2 run tf2_tools view_frames
```

查看关键坐标变换:

```bash
ros2 run tf2_ros tf2_echo odom base_link
ros2 run tf2_ros tf2_echo base_link rgbd_camera_link
ros2 run tf2_ros tf2_echo base_link lidar_link
ros2 run tf2_ros tf2_echo base_link piper_base_link
```

## 14. 录制与回放 Rosbag

录制关键 topic:

```bash
ros2 bag record /mission/state /tf /tf_static /odom /scan /imu/data /target_detections
```

指定输出目录:

```bash
ros2 bag record -o bags/mock_run_001 /mission/state /tf /tf_static /odom /scan /imu/data /joint_states /target_detections
```

查看 bag 信息:

```bash
ros2 bag info bags/mock_run_001
```

回放:

```bash
ros2 bag play bags/mock_run_001
```

## 15. 测试

运行全部测试:

```bash
colcon test
colcon test-result --verbose
```

只测试指定包:

```bash
colcon test --packages-select base_mission
colcon test --packages-select base_bringup
colcon test-result --verbose
```

## 16. CAN 检查，硬件到位后使用

查看 CAN 设备:

```bash
ip link show
ip -details link show can0
ip -details link show can1
```

配置 CAN 示例。具体 bitrate 必须按 SCOUT MINI / PiPER 手册确认:

```bash
sudo ip link set can0 down
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up
```

如果有 `can-utils`:

```bash
sudo apt install can-utils
candump can0
```

## 17. Git 日常

查看状态:

```bash
git status
git log --oneline --decorate -5
git remote -v
```

更新代码:

```bash
git pull
```

创建功能分支:

```bash
git checkout -b simulation/mock-bringup
```

提交变更:

```bash
git add README.md docs/team_workflow.md
git commit -m "Update mock bringup workflow"
git push -u origin simulation/mock-bringup
```

## 18. 常用分支名

```text
simulation/mock-bringup
simulation/mock-sensors
mission/mock-flow
nav/mock-nav2
perception/offline-detection
perception/target-pose
manipulation/mock-piper
```

## 19. 不建议随手执行的命令

不要随手执行批量删除命令，例如:

```bash
rm -rf build install log
```

如果确实需要清理构建产物，先确认 `build/`、`install/`、`log/` 中没有需要保留的日志、rosbag 或实验结果，再按团队文件管理规则处理。

## 20. 当前阶段最常用命令

硬件未到位时，最常用的是:

```bash
source /opt/ros/humble/setup.bash
vcs import . < dependencies.repos
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 launch base_bringup sim_bringup.launch.py
```
