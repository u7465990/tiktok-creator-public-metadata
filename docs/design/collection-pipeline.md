# 实现级模块边界设计（Deep Modules）

> 配套文档：[GLOSSARY.md](../../GLOSSARY.md)（术语）、[ADR 0001–0008](../adr/)（语义决策）、[调研报告](../research/tiktok-public-meta-feasibility.md)（可行性）。
> 本文只回答一个问题：**代码应该切成哪几个模块，每个模块的接口长什么样，缝（seam）开在哪里。**

---

## 1. 问题空间

任何接口都必须同时满足六个约束：

| 约束 | 对接口的直接影响 |
|---|---|
| 100 个 handle 必须各出一行，失败也出 | 采集中断要变成一条 Record，而不是异常冒泡 |
| 五态区分（ok/not_found/private/blocked/error） | "观察到的信号 → Status"必须只有一个决定点 |
| 无登录、合规 | 抓取器不能有"带凭据"的配置项，连参数都不该存在 |
| 可断点续跑 | 缓存粒度决定接口粒度：抓取必须返回可落盘的原始物 |
| 可审计 | 每个字段要能回指 source URL 与快照文本 |
| 6 小时内可完成 | 缝的数量必须极少，宁缺毋滥 |

依赖按 `DEEPENING.md` 分类：

| 依赖 | 类别 | 处理 |
|---|---|---|
| HTML/JSON 解析、状态映射、数值解析、语言规则判定 | 1. In-process | 直接做成纯模块，不抽象 |
| 快照文件系统 | 2. Local-substitutable | 真实临时目录即可测试，不设 port |
| 语言大模型（可选） | 4. True external | 注入 port，测试用录制结果 |
| TikTok 公网 HTTP | 4. True external | 注入 port，测试用快照重放 |

> 没有"远程但自有"的依赖——这是单机批处理，别按微服务那套设计。

---

## 2. 模块地图

```
cli/run.py                     ← 薄 adapter（argv/env → CollectionSpec）
  └─ pipeline.run_collection   ← 顶层深模块（编排 + 产物落盘）
       ├─ resolve.resolve_profile     ← 深模块：handle → Resolution
       │    ├─ PageFetcher (port)     ← 缝：live / replay 两个 adapter
       │    └─ tiktok.parse_profile   ← 纯模块：Snapshot → ProfileFacts
       ├─ language.detect_language    ← 深模块：证据 → Verdict
       │    └─ LanguageJudge (port)   ← 缝：rule / model 两个 adapter
       ├─ avatar.store_avatar         ← 深模块：URL → AvatarOutcome
       ├─ record.assemble             ← 纯模块：五态优先级 + 三值 bio + Provenance
       ├─ record.validate             ← 纯模块：Schema + 业务断言
       └─ report.build                ← 纯模块：Record[] → report.json
```

### 2.1 `run_collection` — 顶层深模块

```python
@dataclass(frozen=True)
class CollectionSpec:
    input_csv: Path
    out_dir: Path
    force_refresh: bool = False       # 默认复用快照
    only_status: set[Status] | None = None  # None = 全量；{error, blocked} = 只补失败
    now: Callable[[], datetime] = utcnow    # 传参而非 Clock 端口；测试传固定 lambda

def run_collection(spec: CollectionSpec, snapshots: SnapshotStore) -> RunSummary: ...
```

- 接口只有 1 个函数 + 1 个 spec；调用方（CLI）不知道重试、并发、缓存、报告的任何细节。
- **隐藏**：读 CSV → 逐条 resolve → 解析 → 语言 → 头像 → assemble → validate → 写 results.jsonl / report.json / avatars/ 的全过程，以及"失败不中断批次"的兜底。
- **不变量**：返回时 `result_count == input_count`，且每个输入 handle 出现且仅出现一次（失败即 `error` 记录）。
- 输入文件里没有的 handle 不会出现在输出里，反之亦然。

### 2.2 `resolve_profile` — 最深的模块

```python
@dataclass(frozen=True)
class Resolution:
    normalized: str
    profile_url: str | None
    status: Status                  # ok / not_found / private / blocked / error
    snapshot: Snapshot | None       # status=ok 或 private 时通常有
    attempts: list[Attempt]         # 每个 URL 的状态码、耗时、被拒原因
    source_urls: list[str]

def resolve_profile(handle: str, fetcher: PageFetcher, policy: FetchPolicy) -> Resolution: ...
```

- 调用者只给一个字符串，拿到"这个 handle 到底怎么了"的完整判断。
- **隐藏**：候选 URL 的生成与排序（规范主页 → 搜索引擎回退 → 已确认的第三方页）、robots 预检、限速等待、重试退避、检查点保存、以及最重要的**状态判定**。
- 这里是全项目唯一允许出现"403/429/404 → Status"映射的地方（ADR-0003）。
- 为什么深：删掉它，候选生成、退避、状态判定会立刻散进 `run_collection`、CLI 和测试，且每加一个来源就要改三处。

### 2.3 `PageFetcher` — 唯一的"真"抓取缝

```python
class PageFetcher(Protocol):
    def get(self, url: str) -> Snapshot: ...   # 不抛 4xx/5xx；状态码在 Snapshot 里
```

- 两个 adapter：`LiveHttpFetcher`（限速、UA、超时、重试）、`SnapshotReplayFetcher`（测试，按 URL 返回 fixture）。
- `get` **不抛 HTTP 错误**：404 也是合法结果，否则状态映射会被 try/except 撕碎。
- 一个 adapter 只是假缝；这里是"生产 + 测试"两个真实 adapter，够格。
- 收敛后（见 [8.4](#84-最终形态收敛结果)）：端口扩为 `SnapshotStore`，同时承担 `fetch(request)` 与 `read(snapshot_id)`，把"抓取"和"可审计的快照读取"放进同一个真缝。

### 2.4 `parse_profile` — 纯函数，平台耦合的唯一入口

```python
def parse_profile(snapshot: Snapshot) -> ProfileFacts: ...
# ProfileFacts: display_name, bio: str | None, follower_count: int | None,
#               avatar_url, recent_captions: list[str], raw_provenance: dict[str, TextLoc]
```

- **输入是 Snapshot 而不是 URL**——这一点让整条链路可以完全离线测试，且不需要为解析器开任何缝。
- **隐藏**：内嵌 JSON 的定位、多种载荷形态的回退、字段缺失与空串的区分、`bio` 的 HTML 转义还原、粉丝数原文的保留。
- 解析顺序按调研结论设计：`__UNIVERSAL_DATA_FOR_REHYDRATION__` → `SIGI_STATE`（旧）→ `og:title / og:description / og:image` 三个 meta 兜底。**meta 兜底是抗改版的最小可用集**，即使主 JSON 键名漂移也能拿到展示名与简介。
- 换平台时只改这一个文件（外加 URL 模板），`resolve` 与 `assemble` 不动。

### 2.5 `detect_language` — 证据优先级被固化在接口里

```python
@dataclass(frozen=True)
class LanguageVerdict:
    language: str            # ^([a-z]{2}|und)$
    confidence: float        # 0..1，夹取
    evidence: LanguageEvidence | None

class LanguageJudge(Protocol):
    def judge(self, texts: list[EvidenceText]) -> JudgeOutput: ...

def detect_language(facts: ProfileFacts, judge: LanguageJudge, threshold: float = 0.6) -> LanguageVerdict: ...
```

- **隐藏**：证据优先级（bio → 最近 ≤3 条内容 → 其他文本）、证据不足降级为 `und`、置信度夹取、模型失败时回退规则判定。
- 缝在这里成立的理由：规则判定（离线、可解释、逐字节可复现）与模型判定（在线、高召回）是**两个都会真正使用的 adapter**，不是为测试造出来的。默认走规则（见 [ADR-0007](../adr/0007-language-default-offline.md)）；启用模型必须显式开关，并把模型名与版本写进 `language_evidence`，否则重放失效。
- 关键不变量：`language == "und"` ⇒ `evidence` 不得声称有强证据；`confidence` 永远在 [0,1]；判定器内部不得读取时钟、随机数或网络。

### 2.6 `store_avatar` — 带失败原因的下载

```python
@dataclass(frozen=True)
class AvatarOutcome:
    relative_path: str | None   # "avatars/<slug>.jpg"
    reason: str | None          # 仅失败时；不含任何凭据
```

- 隐藏文件名生成（规范化 handle 的 slug 化 + 冲突后缀）、下载上限、content-type 校验、幂等（已存在则跳过）。
- 三个重点：**相对路径**（验收要求）、**原因可读**（题目要求"说明原因"）、**不得把 URL 里的签名参数写进日志**。

### 2.7 `assemble` — 五态与三值的唯一决定点

```python
def assemble(handle: str, resolution: Resolution, facts: ProfileFacts | None,
             verdict: LanguageVerdict | None, avatar: AvatarOutcome | None) -> Record: ...
```

- 纯函数，无 I/O。负责：状态优先级、`bio` 三值（"" / null / 值）、全部 null 策略、`collected_at`、`source_urls` 去重、Provenance 装配。
- 它看起来像"字段搬运"，实际承载了 ADR-0003/0004/0006 三条语义；删掉它，三条语义会分散到三个调用点，且测试无法一次断言整行。
- 取舍：参数偏多（5 个）。若继续膨胀，应引入 `CollectionAttempt` 聚合对象，而不是加参数——这是本设计中唯一已知的"薄"处。

### 2.8 其余纯模块

| 模块 | 接口 | 深在哪 |
|---|---|---|
| `validate` | `records, schema → ValidationReport` | Schema 校验 + 业务断言（空串只在 ok、null 只在非 ok、ok 必有 source、URL 去重）一处集中 |
| `report` | `records, window, snapshots → dict` | 覆盖率口径、状态计数一致性、来源分布归一化 |
| `parse_count` | `str → int \| None` | `1.2K/3.4M/12,345/1.2万` 全格式 + 空值语义 |
| `normalize_handle` | `str → str` | 规则唯一出口，保证 `handle` 原值不被改写 |

### 2.9 建议的文件布局

| 模块 | 落点 | 备注 |
|---|---|---|
| `run_collection` | `pipeline.py` | 唯一编排点 |
| `resolve_profile` | `resolve.py` | 含候选生成与状态判定 |
| `PageFetcher` 端口 | `fetch/port.py` | Protocol + `Snapshot` |
| 实时抓取 | `fetch/http.py` | 限速、UA、超时、退避 |
| 快照重放 | `fetch/replay.py` | 测试专用 |
| 快照存储 | `fetch/store.py` | 内容寻址 |
| TikTok URL 规则 | `platform/tiktok/urls.py` | 换平台只改这里 |
| TikTok 解析 | `platform/tiktok/parser.py` | 纯函数，输入 Snapshot |
| 语言判定 | `language.py` | 证据优先级 + 两个 judge |
| 头像 | `avatar.py` | 下载与命名 |
| 装配 / 校验 | `record.py` | 五态 × 三值 × Provenance |
| 报告 | `report.py` | 聚合 |
| 领域类型 | `types.py` | `Status` / `Record` / `Snapshot` / `Provenance` |
| CLI | `cli.py` | 只做 argv → Spec → 退出码 |
| 测试夹具 | `tests/fixtures/*.html` | 真实响应快照，脱敏后入库 |

### 2.10 并发、限速与失败隔离归谁管

| 关注点 | 归属 | 理由 |
|---|---|---|
| 单请求超时 / 退避 / 重试次数 | `PageFetcher` 实现内部 | 它才看得见状态码与传输错误 |
| 全局请求速率（令牌桶 / 间隔） | `PageFetcher` 的装饰器 | 跨 handle 共享一个桶，必须在唯一出口处串起来 |
| 并发度（同时跑几个 handle） | `run_collection` | 与业务顺序、断点续跑、产物写入耦合 |
| 单条失败隔离 | `run_collection` 的外层 `try` | 保证"一条炸了不影响 99 条"，并落成 `error` 记录 |
| "重试几次后算 `blocked` 而不是 `error`" | `FetchPolicy` 的显式配置 | 该判断决定五态语义，不能藏在 fetcher 的魔法常数里 |

关键取舍：**限速放在 fetcher，并发放在编排层**。如果把并发也塞进 fetcher，fetcher 就从"一次请求"变成"一个调度器"，接口立刻变脏；反之把限速放到编排层，每加一个入口（比如头像下载）都要重新实现限速。

### 2.11 启动前置自检（把"环境不可达"变成设计）

调研发现：本机访问 TikTok 在 **DNS 层**就被拦截，5 次抓取全部在建立连接前失败——这种情况下再好的解析器也只会产出 100 条 `error`。因此 `run_collection` 第一步是一次廉价自检：

```python
Preflight = {"robots": "ok|unreachable", "profile_probe": "ok|unreachable", "egress_ip": str | None}
```

1. 拉一次 `robots.txt`，用 `urllib.robotparser` 建规则表（同时完成 robots 守卫，见调研 §3.1）；
2. 对一个确定存在的 handle 做一次探针请求；
3. 结果写进 `report.json` 的 `environment` 段。

**默认行为**：自检不可达 → 立即退出并给出可操作提示（不要静默产出 100 条 `error` 假装跑完了）；`--force-run` 才继续产出，此时每一行都是诚实的 `error`。这样"环境问题"与"账号问题"在交付物里永远不会被混为一谈。

---

## 3. 缝的决策表

| 候选缝 | Adapter 数 | 结论 |
|---|---|---|
| 抓取器 | 2（live / replay） | ✅ 保留 |
| 语言判定器 | 2（rule / model） | ✅ 保留 |
| 时钟 | 0（用默认参数） | ❌ 不开缝：`now` 只是带默认值的参数，测试传 `lambda: FIXED`；单为它建 Protocol 是假 seam |
| 快照存储 | 1（文件系统） | ❌ 不开缝：临时目录就是测试替身（local-substitutable） |
| 解析器 | 1（TikTok） | ❌ 不开缝：单平台，开缝等于提前为假想需求付费 |
| 报告/校验 | 0 | ❌ 纯函数，直接测 |
| robots 策略 | 1 | ❌ 不做接口；作为 `resolve` 内部实现，可注入静态白名单用于测试 |

**判据**：只有一个 adapter 的缝是间接层，不是缝。

---

## 4. 删除测试（每个模块是否在挣饭吃）

- 删 `resolve_profile` → 候选生成 + 退避 + 状态判定扩散到 3 个调用点 → **保留**。
- 删 `parse_profile` → 解析逻辑要么进 fetcher（污染 I/O），要么进 assemble（污染纯函数）→ **保留**。
- 删 `assemble` → 三条 ADR 语义分散，逐行断言失效 → **保留**。
- 删 `report` → 聚合逻辑进 CLI，测试只能端到端跑一遍 → **保留**。
- 删 `CollectionSpec`（把参数摊平到函数签名）→ 调用点 8 个位置参数 → **保留**。
- 删 `validate` → 断言散进测试与 CI 脚本 → **保留**，但保持只做校验、不修复。

---

## 5. 测试策略：接口就是测试面

| 测试层 | 依赖 | 断言什么 |
|---|---|---|
| 纯函数单测 | 无 | `parse_count` 表驱动；`normalize_handle` 边界；`assemble` 五态 × 三值矩阵 |
| 解析器测试 | 快照 fixture | 同一次真实响应 → 稳定 `ProfileFacts`；缺字段回退 |
| 解析→状态映射 | 快照 fixture（故意构造 404/私密/验证码页） | 每条 fixture 落到唯一 Status，且 `error` 不出现在正常页 |
| 端到端（离线） | `SnapshotReplayFetcher` + 临时目录 | 3–5 个 handle 跑完整 `run_collection`，产物齐全、`result_count == input_count` |
| 契约测试 | 真实 Schema 文件 | 100 行 demo 输出逐行通过 JSON Schema |

三条不可省的用例（题面明确要求）：
1. 数量解析：`1.2K` / `3.4M` / `12,345` / `""` / `"1,2K"`（脏数据）→ 整数或 null；
2. 语言规范化：`zh` / `ZH` / `und` / 空证据 / 置信度越界 → 合法 code + [0,1]；
3. 异常状态映射：404 / 403 / 429 / 私密页 / 解析崩溃 → 分别落到 not_found / blocked / blocked / private / error。

---

## 6. 状态 × 字段矩阵（实现时的硬契约）

`assemble` 必须对任意状态产出符合下表的一行；任何一格不符都是 bug，且可以直接写成断言用例。

| 字段 | ok | not_found | private | blocked | error |
|---|---|---|---|---|---|
| `profile_url` | 必填 | null | 必填（账号存在） | null 或已确认地址 | null |
| `display_name` | 可 null | null | 可 null（平台可能仍展示） | null | null |
| `bio` | `""` 或原文 | null | 可见则填，否则 null（ADR-0008） | null | null |
| `follower_count` | int 或 null | null | 可见则填，否则 null（ADR-0008） | null | null |
| `avatar_url` / `avatar_file` | 可 null（下载失败） | null | null | null | null |
| `language` | 两字母码优先 | `und` | `und` | `und` | `und` |
| `language_confidence` | 0–1 | 0 | 0 | 0 | 0 |
| `source_urls` | ≥1 | 可为空（保留尝试地址） | ≥1 | 可为空（保留被拒地址） | 可为空 |
| `error` | null | 简短原因 | 简短原因 | 简短原因 | 简短原因 |

三条可断言的一致性规则：

1. `error == null` ⟺ `status == "ok"`；
2. `bio == ""` ⇒ `status == "ok"`；`bio == null` ⇒ `status != "ok"`；
3. `status == "ok"` ⇒ `len(source_urls) ≥ 1` 且每个非 null 字段都能在 Provenance 中找到来源（ADR-0006）。

---

## 7. 与"粗流水线"的差别

之前文档里的流水线图只说明了**顺序**，本文说明**所有权**：每个箭头都是一次跨缝调用，而跨缝处只有 2 个（抓取、语言判定——后者默认在进程内用规则实现）。其余全部是进程内纯函数——这意味着 100 条真实采集里唯一不确定的东西（网络）被压缩到了 1 个接口后面，测试因此可以完全不碰公网。

---

## 8. 设计三次：三个变体的对比与最终取舍

第 2 节的模块链是"第一版想法"。按 Design-It-Twice 的做法，另外两个独立设计被并行做出来，约束分别是「最小化接口」与「最大化弹性」。三个变体放在一起比较后，最终形态有调整（见 8.4）。

### 8.1 变体 M：最小接口 + 单一存储端口

```python
def harvest(handles: Iterable[str], *, snapshots: SnapshotStore) -> Iterator[Record]: ...

def live(root: Path, ...) -> SnapshotStore:       # adapter A：网络 + 落盘
def replay(corpus: Path, ...) -> SnapshotStore:   # adapter B：只读语料，缺则显式报错
```

- 入口 1 个，调用者只需认识 `Record` 与 `SnapshotStore`；"断点续跑"与"离线重放"都不是 API，而是换一个 adapter。
- 强论点：`replay` 与 `live` 的**失败语义不同**（live 可重试；replay 缺快照必须冒出来），这才让这个端口成为真缝，而不是给测试开的旁路。
- 确定性靠"整文件重写 + 终态冻结"实现：已得 ok/not_found/private 的 handle 不再发请求。
- 代价：没有单条重试钩子、限速与探测阶梯不可调、10 万条规模会破。

### 8.2 变体 R：Registry 驱动，最大弹性

```python
def harvest(handles, *, registry, fetcher, assets=None, policy=Policy()) -> Iterator[Record]: ...
```

- 平台 × 来源 × 字段 × 派生器 × 状态规则全部进 `Registry`；新来源 = 实现 `plan()/extract()` 两个纯函数并入注册表，核心零改动。
- 亮点：把"证据"与"证据→状态"分开——来源只报 `captcha / auth_wall / profile_absent`，五态映射归核心，避免每个来源各自解释状态。
- 代价：调用者要学 5 个参数；扩展者要同时理解 `stage / prior / evidence`；派生器要校验 DAG；`fields: Mapping` 的泛化与"15 个固定字段"的交付契约打架，序列化还要再写一层。

### 8.3 对比

| 维度 | M：最小端口 | R：Registry | P：模块链（第 2 节） |
|---|---|---|---|
| 入口数 | 1 | 1（+5 参数） | 1（+Spec） |
| 调用者需认识的类型 | 2 | 8+ | 4 |
| 真缝数量 | 1 | 3 | 2 |
| 新增一个来源的成本 | 改内部 | 加一个类 | 改内部 |
| 新增一个字段的成本 | 改内部 | 加一条声明 | 改内部 |
| 换平台成本 | 中（改解析） | 低（换注册表） | 中（改 platform/） |
| 6 小时内实现风险 | **低** | 高 | 中 |
| 100 → 10 万条 | 破 | 好 | 中 |
| 逐字节可复现 | **强** | 中（依赖注册表指纹） | 中 |

### 8.4 最终形态（收敛结果）

**采纳 M 的壳，保留 P 的内部模块，拒绝 R 的注册表。**

```python
def run_collection(spec: CollectionSpec, snapshots: SnapshotStore) -> RunSummary: ...
```

| 调整 | 来源 | 理由 |
|---|---|---|
| 抓取器与快照存储合并为 `SnapshotStore` 一个端口 | M | 少一个缝；`live`/`replay` 的失败语义差异证明它是真缝 |
| 断点续跑 = 重跑并整文件覆盖；终态不再请求 | M | 不需要增量协议，也就不会写错断点 |
| 时钟降级为 `now` 参数 | M / R | 单 adapter 的时钟端口是假 seam |
| 语言默认离线规则，模型可选 | M + ADR-0007 | 确定性优先 |
| 解析 / 装配 / 校验 / 报告保持独立纯模块 | P | 它们是测试面，且五态语义需要唯一决定点 |
| Record 保持 15 个显式字段（不做 `fields` 泛化） | P | 交付契约是固定 Schema，显式字段 + 稳定键序更不容易出错 |
| 拒绝 `Registry` / 派生器 DAG / 来源短路 | R | 单平台、6 小时，属于提前为不存在的需求付费 |

**一句话**：接口按 M 收窄（1 入口 + 1 端口 + 1 个可选 judge），内部按 P 拆分（纯模块承担语义与测试），弹性等真的需要第二个平台时再向 R 演进——那时改的是内部，不是调用者。

### 8.5 仍存在的两个薄处

1. 变体 M 的"终态冻结"与"结果可刷新"天然冲突。取舍：默认冻结（保证续跑不重复请求），`--refresh` 显式开启，且刷新写新的快照世代而不是覆盖旧世代。
2. `assemble` 的参数仍然偏多（5 个）。若实现时继续膨胀，应先引入 `CollectionAttempt` 聚合，而不是加第 6 个参数。

---

## 9. 落地顺序（6 小时内最省返工的路）

| 步骤 | 产出 | 为什么这个顺序 |
|---|---|---|
| 0 | 连通性自检 + `robots.txt` 原文 | 调研已证明本机对 TikTok 的 DNS 被污染；这一步决定"能不能开工"，必须先做 |
| 1 | `types.py` + `fetch/port.py` + `fetch/replay.py` | 先把"离线可跑"的地基打好，后面每一步都能测 |
| 2 | `platform/tiktok/parser.py` + 3 个真实快照 fixture | 平台耦合最先做，因为它决定字段口径；此时就能知道题能不能做 |
| 3 | `record.py`（assemble + validate） | 五态 × 三值矩阵可以先用手写数据测通，不依赖网络 |
| 4 | `resolve.py` + `fetch/http.py` | 接上真实网络，跑通 1 条端到端 |
| 5 | `pipeline.py` + `report.py` | 批量与产物 |
| 6 | `language.py`（先规则、后模型） | 规则版即可交付，模型版是加分 |
| 7 | 跑满 100 条 + 抽样复核 + `AI_USAGE.md` | 最后 1 小时，且必须留够 |

反面顺序（常见翻车）：先写 CLI 和报告 → 再想解析 → 最后才发现页面拿不到数据，前面全部白写。
