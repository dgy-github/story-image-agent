# Story Image Agent

独立的故事后续生图项目空间。默认工作流只生成可审计的图片生成请求，不伪造
provider 返回的图片；需要真实产物时可显式使用 DashScope Provider，生产集成仍推荐通过 Rust
typed capability 管理凭据、费用与 artifact。

核心保证：每次提示词修改创建新的 revision；每次生成创建新的 request，旧提示词和
旧图片引用永不覆盖。输入只允许来自已固定的 story package 场景/角色 span。

默认 prompt 同时描述人物身份、动作、竖屏构图、光线、情绪、跨镜连续性与负面约束，
避免只写画面主题而遗漏角色一致性和常见生成瑕疵。所有字段仍被压入可审计 revision；
只有显式调用 Provider 才会产生媒体请求。

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

## 输入输出契约

Python 包只接收已固定场景数据和 `source_spans`，输出
`image-production-plan/v1`。计划包含候选生成请求、版本化质量评估结果以及最终请求；
示例见 `contracts/examples/`。所有 JSON Schema 位于 `contracts/media-agent/`。

质量评估使用 `image-quality-evaluation/v1`。四项分数都必须在 0 到 1 之间并达到阈值；
失败结果保留具体指标、原因、阈值、实际值（若有效）及确定性的返工阶段。

## 基本用法

以下代码只生成计划，不会调用外部服务：

```python
from story_image_agent import ImagePromptWorkflow

workflow = ImagePromptWorkflow("beauty-shop-01")
plan = workflow.build_production_plan(
    {"location": "美容护理室", "characters": "狐狸院长、兔兔美容师、顾客",
     "action": "为顾客敷面膜", "mood": "轻松搞笑"},
    ["scene:episode-01:shot-01"],
    candidate_count=3,
)
# 将候选图分别评分后，只有全部指标过线才可生成 final_request。
final_request = workflow.finalize_candidate(
    plan,
    plan["candidates"][0]["request_id"],
    {"story_alignment": 0.9, "composition": 0.9,
     "identity_consistency": 0.9, "artifact_free": 0.9},
)
```

`source_spans` 必须非空，用于关联已固定的故事场景或角色资料；不可把未确认的自由文本当作
来源。每次创建或修改提示词都会形成新 revision，不能覆盖旧 revision。

## 兼容性与版本策略

包版本遵循 SemVer；当前 `0.1.0a1` 是不稳定预发布。契约名称内的 `/v1` 是独立的
主版本：新增可选字段保持 v1，删除字段、改变字段含义或收紧已有输入需要发布 v2。
Python 3.11 及以上受支持。

## 离线功能测试

`MockImageProvider` 是内置的确定性 provider 替身：根据请求生成 Base64 编码的最小 PNG，费用为
0，结果符合 `media-gateway-response/v1`。它不访问网络、不读取文件、不需要凭据，适合 CI
和本地全链路测试。

```python
from story_image_agent import MockImageProvider

artifact = MockImageProvider().generate(final_request)
assert artifact["provider"] == "mock"
```

## DashScope 生图

`DashScopeImageProvider` 可显式调用阿里百炼的 `wan2.2-t2i-flash`。它依次读取
`DASHSCOPE_WORKSPACE_KEY`、`DASHSCOPE_API_KEY`、`~/.nanocodex/config.toml` 中的
`dashscope_workspace_key` 和 `vl_api_key`，不会记录或输出密钥。调用采用异步任务协议：
提交、轮询任务状态、下载产物；仅接受 PNG、JPEG、WebP 响应。CI 始终使用 Mock，不会发生
外部调用或费用。

```python
from story_image_agent import DashScopeImageProvider

# 显式调用，可能产生模型费用；不要把密钥写入代码或提交到仓库。
provider = DashScopeImageProvider.from_nanocodex_config()
artifact = provider.generate(final_request)
```

Provider 会轮询最多 30 次、间隔 2 秒。`SUCCEEDED` 后返回 Base64 产物；`FAILED`、
`CANCELED`、`UNKNOWN` 立即报错，超时抛出 `TimeoutError`。真实调用前须确认账户权限、模型
可用性与费用；当前 `cost_cny_fen` 是运行时占位值，不可用于结算。

## 安全与 Provider 边界

默认工作流不会调用图片 provider，也不提供 shell 或本地路径能力。真实 Provider 只能显式
调用；凭据仅从环境变量或本地配置读取，不写入仓库、日志、请求结果或示例。生产环境仍推荐由
主项目 Rust typed capability 管理凭据、费用与 artifact。仓库和示例不得包含 secret 或受保护素材。

## 验证与交付状态

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q story_image_agent tests
git diff --check
```

当前测试覆盖 append-only revision、质量门禁、Mock Provider、DashScope 配置读取、异步任务
轮询、终态失败和 MIME 映射。它们不证明真实 DashScope 账户已成功出图；真实在线 smoke 需要
显式授权并可能产生费用。
