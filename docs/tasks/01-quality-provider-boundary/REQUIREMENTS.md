# 生图任务 01：质量与 Provider 边界

完善候选图片的质量指标、评估版本、失败证据和返工阶段；Python 只返回类型化计划，真实 provider、凭据、费用和 artifact 仍由主项目 Rust 负责。

写入范围：`story_image_agent/quality.py`、对应契约和 `tests/`。

验收：`python -m unittest discover -s tests -p "test_*.py"`。
