# 文档索引

本目录是对「Tt 达人公开元信息采集笔试题」的多层分析产物。五个文件回答五个不同的问题，建议按顺序读：

| 顺序 | 文档 | 回答什么问题 | 状态 |
|---|---|---|---|
| 1 | [项目理解.md](../项目理解.md) | 这道题是什么、要交什么、怎么判分 | 已完成 |
| 2 | [调研：TikTok 可行性](research/tiktok-public-meta-feasibility.md) | 这条路走不走得通、能期待多少成功率、红线在哪 | 已完成（受限：本机 DNS 无法到达 TikTok，未验证项均标注） |
| 3 | [GLOSSARY.md](../GLOSSARY.md) | 题面里那些被混用的词到底指什么 | 已完成 |
| 4 | [ADR 0001–0008](adr/) | 八个不可逆的语义决定及其代价 | 已完成 |
| 5 | [实现级模块边界设计](design/collection-pipeline.md) | 代码切成哪几块、接口长什么样、缝开在哪 | 已完成 |

## 调研的三条硬结论

1. **有条件下可行**：6 小时、只采公开无登录信息，预期 `ok` 占 60%–80%；但硬前提是运行环境能连到 `www.tiktok.com`。本机实测是 **DNS 层被污染**（5 次抓取全部在连接建立前失败，同期 `example.com` / `baidu.com` 返回 200），因此"能不能开工"这一步必须在你自己的机器上先跑一次自检。
2. **出口 IP 信誉是现实约束**：同一出口访问 tikwm / countik 直接 403，说明该 IP 在 Cloudflare 处已被标记；若 TikTok 也如此，`blocked` 会明显偏高，**降速救不了**，只能如实上报。
3. **失败分类的关键信号不是 HTTP 码，而是"200 但无 `userInfo`"**；且私密账号的昵称 / bio / 粉丝数通常**仍然公开**——这直接推出 [ADR-0008](adr/0008-private-records-keep-visible-fields.md)。

## 为什么需要第 3、4 层

题面把「handle / 账号 / 达人」「空 bio / 采集失败」「主页 / 来源」当同义词在用。这三组混用在实现时会直接变成三类 bug：

- 把 `normalized_handle` 当成平台标识 → 判重判错；
- 把 `bio=null` 同时用于"确实没有简介"和"没采到" → 违反验收项；
- 把 `profile_url` 复制进 `source_urls` 充数 → 可审计性归零。

所以先定词（GLOSSARY），再定不可逆的语义（ADR），最后才谈模块划分。

## 决策速查

| ADR | 一句话 |
|---|---|
| [0001](adr/0001-collect-only-public-logged-out-pages.md) | 只发匿名请求；被登录墙挡住就记 `blocked`，不加 Cookie |
| [0002](adr/0002-emit-a-record-for-every-handle.md) | 100 个 handle 就 100 行，失败的也写满字段 |
| [0003](adr/0003-blocked-vs-error-boundary.md) | `blocked` 是对方限制我们，`error` 是我们自己坏了 |
| [0004](adr/0004-empty-bio-vs-unknown-bio.md) | `bio=""` 表示确实为空，`bio=null` 表示没采到 |
| [0005](adr/0005-cache-snapshots-not-parsed-records.md) | 缓存原始响应，不缓存解析结果，才能重放与复核 |
| [0006](adr/0006-profile-url-vs-source-urls.md) | `profile_url` 是结论，`source_urls` 是证据，不可互替 |
| [0007](adr/0007-language-default-offline.md) | 语言默认离线规则判定；用模型必须记录版本，否则不可复现 |
| [0008](adr/0008-private-records-keep-visible-fields.md) | 私密账号也要保留仍公开可见的 bio / 粉丝数 |

## 已显式排除的做法

- 登录态 / Cookie 抓取（ADR-0001）；
- 需要密钥或来源不明的第三方聚合 API；
- 为"看起来成功率高"而用猜测值填充 null；
- 把解析结果直接当缓存（会固化旧 bug，且失去 Provenance）。
