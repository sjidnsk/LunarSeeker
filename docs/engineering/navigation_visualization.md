# 导航搜索可视化

本文档记录 `algo_navigation` 的 RViz 调试可视化。当前探索策略为 frontier exploration：从 `/map` 中寻找“已知自由区”和“未知区”的边界，并优先选择靠近或位于指定任务区域的 frontier。该能力只用于导航搜索算法开发和 topic 契约检查，不代表实车 Nav2、定位、避障或硬件 bringup 已完成。

## 启动命令

构建并加载工作区后运行:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch algo_navigation navigation_visualization.launch.py
```

默认会启动:

- `/mock_frontier_map`
- `/mock_navigation`
- `/navigation_visualizer`
- `/rviz2_navigation_search`

默认 `map_frame_id` 为 `odom`，用于匹配当前 mock 地图和 mock 导航输出。接入 Nav2、slam_toolbox 或真实定位后，可显式切换到 `map`:

```bash
ros2 launch algo_navigation navigation_visualization.launch.py map_frame_id:=map
```

如只需要 topic，不启动 RViz:

```bash
ros2 launch algo_navigation navigation_visualization.launch.py use_rviz:=false
```

如使用真实 `/map` 或 rosbag 回放地图，可关闭 mock 地图:

```bash
ros2 launch algo_navigation navigation_visualization.launch.py use_mock_map:=false
```

指定任务区域可在启动时显式覆盖:

```bash
ros2 launch algo_navigation navigation_visualization.launch.py \
  task_area.min_x:=1.6 task_area.max_x:=3.2 \
  task_area.min_y:=-0.8 task_area.max_y:=0.8
```

## Topic

| Topic | 类型 | 说明 |
| --- | --- | --- |
| `/map` | `nav_msgs/msg/OccupancyGrid` | frontier 输入地图；mock 启动时由 `/mock_frontier_map` 发布 |
| `/navigation/search_path` | `nav_msgs/msg/Path` | 按优先级排序的 frontier 候选中心，用于 RViz Path 显示 |
| `/navigation/search_markers` | `visualization_msgs/msg/MarkerArray` | 任务区域、frontier 候选、当前目标、目标检测点和接近点 |
| `/goal_pose` | `geometry_msgs/msg/PoseStamped` | 仍由 `mock_navigation` 发布，是导航目标的唯一 mock 出口 |
| `/mock/navigation_status` | `std_msgs/msg/String` | mock 导航阶段和目标摘要 |
| `/target_detections` | `base_interfaces/msg/ScienceTargetArray` | 目标检测输入；当前若无发布者，RViz 只显示搜索路径和当前目标 |

## Marker 含义

| Namespace | 含义 |
| --- | --- |
| `task_area_fill` | 指定任务区域半透明填充，frontier 选择会优先靠近该区域；参数待实测复核 |
| `task_area_border` | 指定任务区域粗边框 |
| `task_area_label` | 指定任务区域文字标签 |
| `frontier_candidates` | 从 `/map` 中提取并排序的 frontier 候选 |
| `frontier_labels` | frontier 候选编号 |
| `current_goal` | 当前 `/goal_pose` 高亮箭头 |
| `target_detection` | 已收到的目标检测点 |
| `approach_goal` | 对选中目标计算出的 standoff 接近目标 |

## 限制

- 该可视化不控制机器人，也不替代 Nav2 行为树、全局规划器或局部规划器。
- 任务区域、frontier 聚类阈值、占用阈值和 standoff 距离均为 mock 调试参数，尚未完成场地、底盘和相机坐标实测。
- RViz 中看到 frontier、路径和 marker 只说明算法意图与 topic 发布正常，不代表真实底盘可达、避障可用或采样成功。
