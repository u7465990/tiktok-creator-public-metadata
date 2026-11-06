# 达人公开元信息采集笔试题（允许使用 AI）

## 题目说明

我们提供 100 个达人 handle。请设计并实现一个可重复运行的数据采集程序，仅利用公网可访问的信息，补全这些达人的公开元信息。

这是一道允许借助 AI 工具完成的笔试题，重点考察数据采集、数据质量、异常处理、工程化能力，以及对 AI 工具的合理使用。建议实际编码时间不超过 6 小时；未完成全部功能时，请优先保证数据真实、过程可复现，并在 README 中说明取舍。

输入文件位于 [`input/creator_handles_100.csv`](input/creator_handles_100.csv)。

## 任务目标

对输入中的每个 handle 生成且仅生成一条结果。结果使用 JSON Lines 格式，每行一个 JSON 对象，保存为 `results.jsonl`。

至少采集以下字段：

| 字段 | 类型 | 要求 |
|---|---|---|
| `handle` | string | 原始输入，不得丢失或静默修改 |
| `normalized_handle` | string | 规范化后的 handle |
| `profile_url` | string/null | 最终确认的公开主页 URL |
| `display_name` | string/null | 达人展示名 |
| `avatar_url` | string/null | 头像原始 URL |
| `avatar_file` | string/null | 下载后的本地相对路径；无法下载时说明原因 |
| `bio` | string/null | 公开个人简介；空简介与采集失败需要区分 |
| `follower_count` | integer/null | 粉丝数，统一转成非负整数 |
| `language` | string | ISO 639-1 代码；无法判断时填 `und` |
| `language_confidence` | number | 0 到 1 |
| `language_evidence` | object/null | 语言判断使用的公开证据和方法 |
| `source_urls` | string[] | 支撑结果的公开来源 URL |
| `collected_at` | string | UTC ISO 8601 时间 |
| `status` | string | `ok`、`not_found`、`private`、`blocked` 或 `error` |
| `error` | string/null | 失败原因，不能包含 Cookie、Token 等敏感信息 |

可选字段包括 `following_count`、`likes_count`、`video_count`、公开地区、最近发帖时间，以及字段级来源信息。

结果对象的 JSON Schema 位于 [`schemas/result.schema.json`](schemas/result.schema.json)，格式示例位于 [`examples/results.sample.jsonl`](examples/results.sample.jsonl)。示例仅用于说明结构，不代表真实采集结果。

## 语言识别要求

语言不能只依据地区猜测。建议按以下优先级取证：

1. 公开 bio；
2. 最近最多 3 条公开内容的标题或描述；
3. 其他可说明来源的公开文本。

可以使用大模型进行语言判断，但必须输出置信度和简要证据。证据不足时返回 `und`，不得编造。

## 技术与合规约束

- 只能采集无需登录即可访问的公开信息。
- 不得绕过验证码、访问控制、付费墙或平台的安全限制。
- 遵守目标站点条款、robots 规则和合理的请求频率；实现限速、超时和有限重试。
- 可以使用公开网页、搜索引擎结果、公开第三方页面和无登录浏览器自动化，但必须记录实际来源。
- 不得使用或猜测招聘方的内部接口，也不得复用招聘方内部达人数据作为答案。
- 不得把 Cookie、代理凭证、API Key 或个人密钥提交到代码仓库或交付物中。
- 一个来源被阻断时，应返回明确状态并保留可诊断信息，不能伪造成功数据。

## AI 工具使用说明

允许并鼓励使用 ChatGPT、Claude、Gemini、Cursor、Codex 等 AI 工具辅助完成代码生成、页面结构理解、字段清洗、语言识别和调试。你仍需对最终实现和数据真实性负责。

请基于 [`templates/AI_USAGE.md`](templates/AI_USAGE.md) 提交 `AI_USAGE.md`，说明使用了哪些工具、AI 参与了哪些环节、如何校验输出，以及哪些关键逻辑由人工确认。评估关注使用方式是否可靠、可审计，而不是是否使用 AI。

## 交付物

请提交一个 ZIP 或一个可访问的代码仓库，至少包含：

1. 可运行的源代码及依赖锁文件；
2. `README.md`：安装、运行、架构、来源选择、限速和失败策略；
3. `results.jsonl`：100 行结果，每个输入 handle 一行；
4. `avatars/`：成功下载的头像；
5. `report.json`：总体成功数、各状态数量、字段覆盖率、耗时和来源分布；
6. `AI_USAGE.md`；
7. 至少 3 个自动化测试，覆盖数量解析、语言结果规范化和异常状态映射。

建议提供一条命令完成采集，例如：

```bash
./run.sh input/creator_handles_100.csv
```

程序重复执行时应复用缓存或支持断点续跑，避免无意义地重复请求公网来源。

`report.json` 的最小结构示例位于 [`examples/report.sample.json`](examples/report.sample.json)。提交前可使用 [`templates/SUBMISSION_CHECKLIST.md`](templates/SUBMISSION_CHECKLIST.md) 自检。

## 验收要求

- 输入的 100 个 handle 在结果中全部出现且无重复；
- `status=ok` 的记录必须具有可访问的公开来源，不允许伪造或用内部数据补齐；
- 所有粉丝数均为整数或 `null`，能够正确解析 `1.2K`、`3.4M` 等格式；
- 明确区分空 bio、主页不存在、账号私密、访问受限和程序错误；
- 抽样复核账号时，来源、头像、bio 和粉丝数应与采集时公开页面一致；
- 日志和结果中不得出现密钥、Cookie 或完整代理凭证。

公网状态可能变化，因此不会仅以绝对成功率判定结果。对不可访问账号给出真实、可复现的失败状态，优于返回未经验证的数据。

## 评估重点

- 数据真实性与字段正确性；
- 多来源回退、状态分类、重试和断点续跑；
- 工程结构、可运行性、测试、日志和配置管理；
- 来源 URL、采集时间、语言证据和错误可诊断性；
- AI 工具使用的可靠性、验证方式和成本意识；
- 公开信息边界、限速和敏感信息保护。

如对题目边界存在疑问，请在提交说明中写明你的理解和假设，不要通过绕过访问控制来补齐数据。
