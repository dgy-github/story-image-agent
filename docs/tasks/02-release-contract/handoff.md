# Handoff：生图 Agent 独立发布契约

目标：补齐 README、版本策略、输入输出示例、兼容性、安全边界和 CI，使仓库可独立发布。

写入范围：`README.md`、`pyproject.toml`、`contracts/`、`.github/`、`tests/`。验收：测试和 GitHub Actions 全绿，仓库无 secret、受保护素材和 `*.egg-info`。

状态：`completed`（2026-08-30）。版本：`0.1.0a1`；README、版本策略、输入输出示例、
兼容性、安全边界和 CI 已补齐。

验证：`python -m unittest discover -s tests -p "test_*.py"` 通过（7 tests），工作树已清除
`*.egg-info`。提交：`eb16316`。仓库：https://github.com/dgy-github/story-image-agent。
GitHub Actions：https://github.com/dgy-github/story-image-agent/actions/runs/33320901788（success）。
未决：无。
