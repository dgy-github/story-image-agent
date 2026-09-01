# Story Image Agent

独立的故事后续生图项目空间。默认工作流只生成可审计的图片生成请求，不伪造
provider 返回的图片；需要真实产物时可显式使用 DashScope Provider，生产集成仍推荐通过 Rust
typed capability 管理凭据、费用与 artifact。

核心保证：每次提示词修改创建新的 revision；每次生成创建新的 request，旧提示词和
旧图片引用永不覆盖。输入只允许来自已固定的 story package 场景/角色 span。

默认 prompt 同时描述人物身份、动作、竖屏构图、光线、情绪、跨镜连续性与负面约束，
避免只写画面主题而遗漏角色一致性和常见生成瑕疵。所有字段仍被压入可审计 revision，
不会直接调用 provider。

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

## 输入输出契约

Python 包只接收已固定场景数据和 `source_spans`，输出
`image-production-plan/v1`。计划包含候选生成请求、版本化质量评估结果以及最终请求；
示例见 `contracts/examples/`。所有 JSON Schema 位于 `contracts/media-agent/`。

质量评估使用 `image-quality-evaluation/v1`。四项分数都必须在 0 到 1 之间并达到阈值；
失败结果保留具体指标、原因、阈值、实际值（若有效）及确定性的返工阶段。

## 兼容性与版本策略

包版本遵循 SemVer；当前 `0.1.0a1` 是不稳定预发布。契约名称内的 `/v1` 是独立的
主版本：新增可选字段保持 v1，删除字段、改变字段含义或收紧已有输入需要发布 v2。
Python 3.11 及以上受支持。

## 离线功能测试

`MockImageProvider` 是内置的确定性 provider 替身：根据请求生成 Base64 编码的最小 PNG，费用为
0，结果符合 `media-gateway-response/v1`。它不访问网络、不读取文件、不需要凭据，适合 CI
和本地全链路测试。

## DashScope 生图

`DashScopeImageProvider` 可显式调用阿里百炼的 `wan2.2-t2i-flash`。它依次读取
`DASHSCOPE_WORKSPACE_KEY`、`DASHSCOPE_API_KEY`、`~/.nanocodex/config.toml` 中的
`dashscope_workspace_key` 和 `vl_api_key`，不会记录或输出密钥。调用采用异步任务协议：
提交、轮询任务状态、下载产物；仅接受 PNG、JPEG、WebP 响应。CI 始终使用 Mock，不会发生
外部调用或费用。

## 安全与 Provider 边界

默认工作流不会调用图片 provider，也不提供 shell 或本地路径能力。真实 Provider 只能显式
调用；凭据仅从环境变量或本地配置读取，不写入仓库、日志、请求结果或示例。生产环境仍推荐由
主项目 Rust typed capability 管理凭据、费用与 artifact。仓库和示例不得包含 secret 或受保护素材。
