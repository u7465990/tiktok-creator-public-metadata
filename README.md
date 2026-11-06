# 达人公开元信息采集（TikTok）

对给定的 100 个 handle，逐条采集**无需登录即可访问**的公开资料，产出 `results.jsonl`、`avatars/`、`report.json`。

- 语言：Python 3.10+，**只用标准库，无第三方依赖**
- 运行：一条命令，可重复执行、可断点续跑
- 本次运行：100 条中 `ok` 90、`not_found` 9、`private` 1、`blocked` 0、`error` 0

> 题目原文见 [README.assignment.md](README.assignment.md)。

---

## 快速开始

```bash
git clone <repo-url> && cd creator-public-data-written-test-candidate
./run.sh input/creator_handles_100.csv
```

> 如果提示 `Permission denied`，先执行一次 `chmod +x run.sh clean.sh`（在 Windows 上打包的 zip 会丢掉可执行位）。
> Windows 下用 Git Bash 运行同一条命令，或直接 `python -m collector --input input/creator_handles_100.csv --out .`。

等价写法（Windows 或没有 bash 时）：

```powershell
python -m collector --input input/creator_handles_100.csv --out .
```

运行约 6 分钟（100 次页面请求 + 91 张头像；单线程、间隔 3 秒）。

其余参数：

| 参数 | 作用 |
|---|---|
| `--limit N` | 只跑前 N 条（调试） |
| `--delay 3` | 请求间隔秒数（实际有 ±1s 抖动） |
| `--refresh` | 忽略快照缓存，重新抓取 |
| `--no-avatars` | 不下载头像 |

产物（都在当前目录）：

```
results.jsonl   每行一条，字段与 schemas/result.schema.json 对齐
report.json     状态分布、字段覆盖率、来源分布、耗时
avatars/        成功下载的头像（相对路径已写入 avatar_file）
cache/          HTTP 快照，断点续跑用（不是交付物，已 gitignore）
```

## 运行前置条件（很重要）

TikTok 网页端会按 User-Agent 做反爬判定，实测结果：

| 客户端 | 结果 |
|---|---|
| 桌面 Chrome（含完整浏览器头） | 返回 200，但只有 1.5KB 的 WAF 挑战页（`_wafchallengeid`） |
| **iPhone Safari** | 返回 200，约 230KB，含完整 `__UNIVERSAL_DATA_FOR_REHYDRATION__` |

因此采集统一使用 **iPhone Safari UA**。这不是伪造身份或破解挑战，而是请求平台同样公开提供的移动端页面；程序里保留了 WAF 页检测，一旦再次被拦就如实记为 `blocked`，不会重试到死。

另外：中国大陆家庭宽带对 `tiktok.com` 存在 DNS 污染（解析到 Facebook 网段），**必须**在能正常访问 TikTok 的网络中运行。本次实际运行环境为腾讯云轻量服务器（新加坡），完整过程见 [docs/research/tiktok-public-meta-feasibility.md](docs/research/tiktok-public-meta-feasibility.md)。

## 架构

```
collector/
├── cli.py        编排：读 CSV → 逐条采集 → 写产物
├── fetch.py      抓取：UA、限速、重试、快照缓存
├── parse.py      HTML → ProfileFacts（纯函数）
├── assemble.py   handle 规范化 + 状态判定 + 结果组装（纯函数）
├── language.py   bio 文本 → 语言 + 置信度 + 证据（纯函数）
├── count.py      展示型数字 → 整数（纯函数）
├── avatars.py    头像下载 + 类型校验
├── validate.py   Schema + 业务断言
└── report.py     聚合统计
```

设计要点：

- **网络只在一个地方**（`fetch.py`），解析、状态判定、组装全是纯函数，测试不需要联网；
- **按快照切分接口**：`parse_profile(html)` 收字符串而不是 URL，所以真实响应可以存成夹具离线重放；
- **状态只有一个决定点**：`assemble.decide_status`，禁止各处散落 `if 403: ...`。

## 状态判定

TikTok 对"账号不存在"也返回 **HTTP 200**，因此不能只看状态码：

| 观察到的信号 | status |
|---|---|
| 连接失败 / 超时 / DNS 失败 | `error` |
| HTTP 403 / 429 | `blocked` |
| 页面是 WAF 挑战页（`_wafchallengeid`） | `blocked` |
| HTTP 404，或 JSON `statusCode` ≠ 0（实测 10221 / 209002） | `not_found` |
| `privateAccount: true` | `private` |
| 其余（拿到 `userInfo.user`） | `ok` |

`private` 记录**保留仍然公开的**昵称、bio、粉丝数（账号私密只代表内容不可见），并在 `error` 里写明"账号私密"。

## 字段口径

| 字段 | 取法 |
|---|---|
| `handle` | 输入原样，逐字保留 |
| `normalized_handle` | 去协议/域名/查询串/`@`/末尾斜杠，转小写（`.` `_` 是合法字符，不动） |
| `profile_url` | 平台返回的 `uniqueId` 拼成规范地址 |
| `display_name` | `userInfo.user.nickname` |
| `bio` | `userInfo.user.signature`；**空简介记空串，未采到记 null** |
| `follower_count` | `userInfo.stats.followerCount`，JSON 里就是原始整数 |
| `avatar_url` | `avatarLarger`（CDN 链接含时效签名，过期属正常） |
| `avatar_file` | `avatars/<slug>.jpg`，下载失败则 null 并在 `error` 说明 |
| `language` / `confidence` / `evidence` | 见下节 |
| `source_urls` | 实际解析出字段的那个主页 URL |
| `collected_at` | UTC ISO 8601 |

`count.py` 仍实现 `1.2K` / `3.4M` / `1.2万` 等展示值解析，用于页面没有内嵌 JSON 时的兜底；本次主路径未触发。

## 语言判定

优先级：`bio` → 最近内容 → 其他公开文本。本次实测页面里 `itemList` 为空（视频列表走异步接口），因此**只有 bio 可用**。

规则：

1. 非拉丁文字系统（中日韩俄阿泰希印）按字符检测，置信度 0.6–0.95；
2. 拉丁字母按停用词投票，至少命中 2 个且明显领先才判定，置信度 0.35–0.9；
3. 证据不足返回 `und`，置信度 0.0–0.2，并在 `language_evidence` 写明原因。

结果：17% 判定成功，83% 为 `und`。这是刻意的——题目要求"证据不足返回 und，不得编造"，宁可少判不可错判。

## 缓存与断点续跑

- 每个 URL 的原始响应存为 `cache/<sha1(url)>.html` + `.json`（元数据）；
- 重跑默认命中缓存，不重复请求；`--refresh` 才重新抓取；
- 中断后直接重跑即可补齐，不需要额外协议；
- 缓存也是审计依据：任何一条结果都能回放到当时的页面。

## 限速与重试

- 单线程，请求间隔 3s + 0–1s 随机抖动（100 条约 6 分钟）；
- **单次请求**：连接层失败、429、5xx 会自动重试 2 次（退避 2s / 4s）；
- **整批跑完**：对 `status=error` 的记录自动补跑一轮（`--no-retry` 可关闭）——只重试连接层失败，不碰 `blocked` / `not_found` / `private`，因为后三者是确定性结果，重试只会增加对方压力；
- 403 与 WAF 页**不硬刚**，直接落 `blocked`；
- 不并发、不使用代理池、不带 Cookie。

## 合规边界

- 只访问**无需登录**的公开页面，不发 Cookie、不伪造登录态；
- 未绕过验证码、付费墙或访问控制；
- 已核对 `robots.txt`：`User-agent: *` 分组未禁止 `/@`（原文见 `tools/captured/robots.txt`）；
- 解析失败或页面结构变化时记 `error`，**绝不用猜测值填充**；
- 日志与结果中不含任何密钥、Token、Cookie。

## 已知限制

1. **语言覆盖率低**（17%）：页面不提供最近视频描述，只有 bio 可判；
2. **依赖移动端 UA**：平台若调整反爬策略，可能整体变为 `blocked`（程序会如实记录，不会伪造）；
3. **`avatar_url` 有时效签名**：几天后过期，但本地 `avatar_file` 已落地；
4. **`statusCode=209002` 归为 not_found**：该码在实测中同样表示"没有可用公开主页"，官方文档未确认其确切含义；
5. 账号改名后，两次采集会得到两条不同 handle 的记录（题目要求按 handle 输出，未做跨批次实体合并）。

## 本次运行结果

| 指标 | 值 |
|---|---|
| 输入 / 结果 | 100 / 100（一一对应、无重复） |
| 状态 | ok 90、not_found 9、private 1、blocked 0、error 0 |
| profile_url / display_name / avatar_url / follower_count | 91% |
| bio | 70%（其中 21 条为空串 = 确实没有简介） |
| 语言（非 und） | 17% |
| 头像文件 | 91 个 |

## 测试

```bash
python3 -m unittest discover -s tests -t . -v
```

19 个用例，覆盖题目要求的三类（数字解析、语言结果规范化、异常状态映射），另含真实页面夹具的解析测试（`ok` 与 `not_found` 各一份）。全部离线，不依赖网络。

## 清理与重跑

```bash
./clean.sh          # 删结果与头像，保留 cache/（重跑约 1 分钟）
./clean.sh --all    # 连 cache/ 一起删（彻底重来，约 6 分钟）
./clean.sh -n       # 只打印会删什么，不真删
```

删除范围：`results.jsonl`、`report.json`、`avatars/`、`out_test/`、`__pycache__`；加 `--all` 时再删 `cache/`。

典型用法：换一份输入做扩展（`./run.sh input/another.csv`），或想从零复现一次完整采集。

## 一键验收

跑完采集后：

```bash
python3 tools/verify_results.py
```

检查内容：与输入是否一一对应、有无重复、字段类型、五态语义、bio 三值、`source_urls` 与 `avatar_file` 是否齐备；同时打印状态分布、语言分布、字段覆盖率与头像文件数。退出码 `0` 表示全部通过。

```
记录条数 : 100      输入条数 : 100      一一对应 : 是      重复记录 : 无
状态分布 : {'ok': 90, 'not_found': 9, 'private': 1}
全部通过：字段合法、状态自洽、来源与头像齐备。
```

## 抽样复核方法

1. 取 `results.jsonl` 任意一条 `ok` 记录；
2. 打开其 `source_urls[0]`；
3. 对照 `display_name`、`bio`、`follower_count` 与 `avatar_file` 的图片；
4. 若要复原"采集当时"的页面，取 `cache/` 中对应快照（按 URL 的 sha1 命名）。

## 仓库内容说明（采集数据不入库）

`results.jsonl`、`report.json`、`avatars/`、`cache/` 是**运行产物**，因包含真实用户的公开资料且体积较大，已在 `.gitignore` 中排除。克隆后按「快速开始」跑一次即可重新生成。

`tests/fixtures/` 保留两页真实响应（@tiktok 官方账号、一个不存在的 handle），仅用于离线解析测试，不含本次 100 个账号的数据。

## 目录结构

```
collector/          采集器源码
tests/              单元测试 + 真实页面夹具
results.jsonl       交付物
report.json         交付物
avatars/            交付物
run.sh              一键运行入口
clean.sh            一键清理产物
input/              题目输入
schemas/            题目 Schema
examples/           题目示例
templates/          题目模板
docs/               可行性调研、术语表、ADR、模块设计（分析过程）
tools/              连通性自检、探测脚本、抓到的原始页面（辅助证据）
README.assignment.md  题目原文
AI_USAGE.md         AI 使用说明
```
