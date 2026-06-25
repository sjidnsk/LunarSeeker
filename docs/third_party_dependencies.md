# 第三方依赖管理

## 管理原则

- 第三方源码不直接提交到本仓库。
- 第三方仓库统一记录在根目录 [dependencies.repos](../dependencies.repos)。
- 本地源码默认导入到 `src/third_party/`，该目录已加入 `.gitignore`。
- 当前小车尚未到位，以下 commit 仅作为当前导入版本记录，状态均为待硬件验证，不等同于已锁定参赛版本。
- 硬件 Bringup 通过后，再将 `dependencies.repos` 中对应 `version` 从分支名改为已验证 commit。

## 当前导入版本

| 依赖 | 用途 | 来源 | 分支 | 当前本地 commit | 状态 |
| --- | --- | --- | --- | --- | --- |
| `scout_ros2` | SCOUT MINI ROS2 底盘驱动 | `https://github.com/agilexrobotics/scout_ros2.git` | `humble` | `bdbb90471613831fb0b2ec01fecac043445313c4` | 当前导入版本，待底盘 CAN、`/cmd_vel`、`/odom` 验证 |
| `ugv_sdk` | `scout_ros2` 依赖的 UGV SDK | `https://github.com/agilexrobotics/ugv_sdk.git` | `main` | `c3dfaf444f9bae10757e546acae055aaf4a13de7` | 当前导入版本，待随 `scout_ros2` 一起验证 |
| `piper_ros` | PiPER ROS2 驱动和 MoveIt 相关包 | `https://github.com/agilexrobotics/piper_ros.git` | `humble` | `017ffefa64511bc6325bd77ddc4e16065c152051` | 当前导入版本，待 `/joint_states` 和安全预设动作验证 |
| `piper_sdk` | PiPER Python SDK | `https://github.com/agilexrobotics/piper_sdk.git` | `master` | `c05c5454b1cf61c05ad26385e0c0a3aa6d3c7bad` | 当前导入版本，待 PiPER SDK 调试验证 |

## 本地操作建议

导入依赖:

```bash
vcs import . < dependencies.repos
```

查看第三方仓库状态:

```bash
vcs status src/third_party
```

记录当前 commit:

```bash
for repo in src/third_party/*; do
  [ -d "$repo/.git" ] && git -C "$repo" rev-parse HEAD
done
```

如果某个第三方仓库暂不参与 `colcon` 构建，可在对应目录本地添加 `COLCON_IGNORE`。该文件位于 `src/third_party/` 下，不随主仓库提交。
