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

第三方源码会导入到 `src/third_party/`，该目录不直接提交到主仓库。当前导入版本和待验证状态见 [../references/third_party_dependencies.md](../references/third_party_dependencies.md)。

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

本机不直连已固定到车机的真实传感器时，先运行 mock/sim 启动入口:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch base_bringup sim_bringup.launch.py
```

该启动入口会运行 `robot_state_publisher`、`mission_state_machine`，并在 `use_mock_hardware:=true` 时启动 `mock_base_sensors`、`mock_navigation` 和 `mock_manipulation`。mock 节点发布 `/odom`、`/scan`、`/imu/data`、`/joint_states`、带语义的 `/target_detections`、`/goal_pose`、`/mock/navigation_status` 和 `/mock/manipulation_status`。

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
ros2 topic echo /goal_pose
ros2 topic echo /mock/navigation_status
ros2 topic echo /mock/manipulation_status
```

查看发布频率:

```bash
ros2 topic hz /odom
ros2 topic hz /scan
ros2 topic hz /imu/data
ros2 topic hz /joint_states
ros2 topic hz /target_detections
ros2 topic hz /goal_pose
ros2 topic hz /mock/navigation_status
ros2 topic hz /mock/manipulation_status
```

## 11. 查看节点

```bash
ros2 node list
ros2 node info /mission_state_machine
ros2 node info /mock_base_sensors
ros2 node info /mock_navigation
ros2 node info /mock_manipulation
```

## 12. 导航搜索可视化

启动 `algo_navigation` 的独立 RViz 调试入口:

```bash
ros2 launch algo_navigation navigation_visualization.launch.py
```

该入口只用于导航搜索算法调试，会启动 `mock_frontier_map`、`mock_navigation`、`navigation_visualizer` 和 RViz。当前探索策略为 frontier exploration：从 `/map` 中寻找已知自由区和未知区边界，并优先选择靠近或位于指定任务区域的 frontier。默认使用 `odom` 作为 mock 调试坐标系；接入 Nav2 / slam_toolbox / robot_localization 后再按实际 TF 切换到 `map`。

显式指定任务区域:

```bash
ros2 launch algo_navigation navigation_visualization.launch.py \
  task_area.min_x:=1.6 task_area.max_x:=3.2 \
  task_area.min_y:=-0.8 task_area.max_y:=0.8
```

查看可视化 topic:

```bash
ros2 topic echo /navigation/search_path
ros2 topic echo /navigation/search_markers
ros2 topic echo /map
```

更多说明见 [导航搜索可视化](navigation_visualization.md)。

## 13. 调用任务 Action

查看 action:

```bash
ros2 action list
ros2 action info /execute_mission
```

发送一次 mock 任务目标:

```bash
ros2 action send_goal /execute_mission base_interfaces/action/ExecuteMission "{run_index: 1, use_mock_hardware: true, profile_name: 'mock'}"
```

## 14. TF 检查

生成 TF 树:

```bash
ros2 run tf2_tools view_frames
```

查看关键坐标变换:

```bash
ros2 run tf2_ros tf2_echo odom base_link
ros2 run tf2_ros tf2_echo map odom
ros2 run tf2_ros tf2_echo base_link rgbd_camera_link
ros2 run tf2_ros tf2_echo base_link lidar_link
ros2 run tf2_ros tf2_echo base_link piper_base_link
```

## 15. 录制与回放 Rosbag

录制关键 topic:

```bash
ros2 bag record /mission/state /tf /tf_static /odom /scan /imu/data /joint_states /target_detections /goal_pose /mock/navigation_status /mock/manipulation_status
```

指定输出目录:

```bash
ros2 bag record -o bags/mock_run_001 /mission/state /tf /tf_static /odom /scan /imu/data /joint_states /target_detections /goal_pose /mock/navigation_status /mock/manipulation_status
```

查看 bag 信息:

```bash
ros2 bag info bags/mock_run_001
```

回放:

```bash
ros2 bag play bags/mock_run_001
```

## 16. 测试

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

## 16. CAN 检查，车机硬件验证时使用

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
git add README.md docs/engineering/team_workflow.md
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

本机开发和离线验证时，最常用的是:

```bash
source /opt/ros/humble/setup.bash
vcs import . < dependencies.repos
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 launch base_bringup sim_bringup.launch.py
```
