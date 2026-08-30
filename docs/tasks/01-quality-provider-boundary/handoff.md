# Handoff：生图质量与 Provider 边界

目标：完善质量指标、评估版本、失败证据和返工阶段；Python 只输出类型化计划，Rust 负责真实 provider、凭据、费用和 artifact。

写入范围：本目录所属 Agent 的 `quality.py`、契约和测试。验收：`python -m unittest discover -s tests -p "test_*.py"`。

状态：`completed`（2026-08-30）。质量评估契约为 `image-quality-evaluation/v1`；指标与阈值
依据记录在 `story_image_agent/quality.py`，失败证据与返工阶段已由测试覆盖。

验证：`python -m unittest discover -s tests -p "test_*.py"` 通过（7 tests）。提交：`eb16316`；
未加入 provider 网络、shell、密钥或本地路径能力。未决：无。
