# Handoff：生图质量与 Provider 边界

目标：完善质量指标、评估版本、失败证据和返工阶段。默认 Python 工作流只输出类型化计划；
真实 Provider 必须显式调用，生产环境推荐由 Rust 管理凭据、费用和 artifact。

写入范围：本目录所属 Agent 的 `quality.py`、契约和测试。验收：`python -m unittest discover -s tests -p "test_*.py"`。

状态：`completed`（2026-08-30）。质量评估契约为 `image-quality-evaluation/v1`；指标与阈值
依据记录在 `story_image_agent/quality.py`，失败证据与返工阶段已由测试覆盖。

验证：`python -m unittest discover -s tests -p "test_*.py"` 通过（12 tests）。提交：`eb16316`、
`c76bbde`（后者已推送且 CI success）。

后续更新（2026-09-01）：已新增显式 `DashScopeImageProvider`，用于复用 BugleCat 的阿里
百炼配置；采用异步提交、轮询和下载流程。Mock 保持为 CI 默认 Provider。未决：真实 API 的
带费用 smoke 尚未执行；真实 Provider 的费用元数据仍为运行时占位值。
