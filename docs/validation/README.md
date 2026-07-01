# 验证记录

本目录保存可追溯的验证记录，包括构建、mock/sim、车机、单硬件和端到端联调结果。

记录原则:

- 每份记录说明日期、环境、输入命令或流程来源、通过项、未测项和验证边界。
- 厂商手册、设计文档和命令说明只作为来源或操作指引；验证记录用于说明实际执行结果。
- 未实测的硬件能力、参数、外参、重量和性能指标必须继续标注待验证或待测量。
- 真实硬件记录应区分 Noetic 厂商基线、ROS2 单硬件 bringup 和 ROS2 端到端联调。

当前记录:

- [Mock/sim 验证记录](mock_bringup_validation.md)
- [P3 Nav2 仿真验证记录](navigation_sim_validation.md)
- [车机 Noetic 基线验证记录](vehicle_noetic_baseline_validation.md)
