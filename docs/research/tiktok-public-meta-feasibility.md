# TikTok 公开元信息采集可行性调研

> 调研时间：2026-11-05（Asia/Shanghai）
> 调研执行者：数据采集可行性调研员（AI agent）
> 目标平台：题面代号 "Tt"，确认对象为 TikTok（依据：handle 形态 + 字段组合，见 §1）
> 证据分级：**【实测】**= 本次亲自抓取/命令输出；**【官方原文】**= 引用官方文档原句；**【社区说法】**= 博客/论坛/二手转述；**【推断】**= 由已知事实推导

---

## 0. 结论摘要（含可行性判定与预期成功率）

### 0.1 一句话结论

**这道题可以在 6 小时内跑通 100 条，但有一个硬前提：运行环境本身能访问 `www.tiktok.com`；在能访问的前提下，预期 `status=ok` 占比大约 60%–80%，其余是 `not_found`（约 10%–25%）、`private`（个位数）和 `blocked`（5%–15%，取决于限速是否克制）。**

### 0.2 本次调研最重要的发现（必须先看）

**本次调研环境无法访问 TikTok 主站——不是反爬拦截，是 DNS 层被拦截。**

- 对 `www.tiktok.com`、`tiktok.com`、`m.tiktok.com` 的抓取尝试全部在**建立连接之前**失败，报错固定为：`Error: URL hostname "www.tiktok.com" resolves to a non-public IP address`；`*.tiktok.com` 四个子域全部命中同一错误。**【实测】**
- 同一工具抓 `https://example.com` 返回 **HTTP 200**、抓 `https://www.baidu.com` 返回 **HTTP 200**、抓 `https://cn.bing.com/search?...` 返回 **HTTP 200**——**工具与出口网络是通的**，被拦的是特定域名。**【实测】**
- DNS 解析本身是污染/伪造的：`www.tiktok.com` 两次查询分别得到 `69.171.235.22`（Meta 的 IP 段）和 `174.132.167.252`，另有 `AAAA 2001::1`（Teredo 保留段）；`tiktok.com` 得到 `23.210.26.x`。**同一域名多次查询答案不一致 = 典型 DNS 污染特征**。**【实测】**
- 出口公网 IP 为 `112.10.196.22`（由 Cloudflare 拦截页回显）。**【实测】**

**这意味着：本报告第 2、3 节的"一手实测"任务我无法完成，第 4 节的字段路径也无法用真实 HTML 验证。** 我没有编造页面结构；所有无法验证的内容在正文中一律标注为【未验证】/【社区说法】，并附上"在你自己的机器上 5 分钟内复测"的可执行脚本（见 §11）。

> 这条发现对做题本身有直接价值：**如果你的开发机/CI 也处在这种网络环境（中国大陆直连、公司代理、云主机区域限制），你会得到 100 条 `blocked` 而不是 60–80% 成功。** 所以第一步不是写爬虫，是**先跑一次单 handle 连通性自检**，把结果写进 README 的"运行前置条件"。

### 0.3 各问题结论速览

| # | 问题 | 结论 | 证据等级 |
|---|---|---|---|
| 1 | 平台身份 | 确认为 TikTok；`https://www.tiktok.com/@<handle>` 为规范主页形态 | 【推断】+【社区说法】 |
| 2 | 无登录可访问性 | **本次无法实测**（域名被 DNS 拦截）；需在你侧复测 | 【实测失败】 |
| 3 | robots.txt | **未能取得原文**；不要在报告里引用未核实的行 | 【实测失败】 |
| 4 | 条款边界 | 官方条款页同样不可达；条文位置与核对方法见 §3.2 | 待核对 |
| 5 | 失败态区分 | 给出 6 个可观察信号 + 判定优先级（可离线实现的映射表） | 【推断】/【社区说法】 |
| 6 | 粉丝数格式 | 页面 `1.2K/3.4M/1.2B` 为展示值，内嵌 JSON 应为原始整数；解析策略见 §6.1 | 【社区说法】 |
| 7 | 头像 URL | 三档尺寸 `avatarLarger/avatarMedium/avatarThumb`，CDN 通常无 referer 校验，可匿名下载 | 【社区说法】待验证 |
| 8 | 限速 | 保守起点：单 IP 串行 1 请求 / 3–8 秒 + 抖动；社区常见 429/403/空页 | 【社区说法】 |
| 9 | 兜底来源 | 分三档：可用/慎用/不可用，见 §8 | 【推断】 |
| 10 | 可行性 | 能跑通，预期 60%–80% ok | 【推断】 |

---

## 1. 平台与 handle 规范

### 1.1 平台确认

题面只写 "Tt"，但输入 CSV 的 handle 形态（`sr.smits03`、`boo.licious`、`spencer_official_2.0`、`user6719638728`）、要求的字段（display_name / bio / follower_count / 头像 / 最近内容）与"达人"语境，只有 TikTok 同时满足。**【推断，高置信】**

**注意**：`Tt` 也可能是"头条/抖音/Twitter"等缩写，但 `.` `_` 混用 + 数字后缀 + `user<数字>` 这种自动生成 handle 的组合，与 TikTok 完全吻合；抖音的 handle 规则也允许 `.` `_`，但字段名与"达人"英文语境更贴 TikTok。**开工前应把这条假设写进 README 的 Assumptions 一节**，并在 6 小时预算里留 15 分钟做连通性验证。

### 1.2 handle 规范（需要你复核）

- **允许字符**：小写/大写字母 `a-z A-Z`、数字 `0-9`、下划线 `_`、句点 `.`。**【社区说法】**
- **长度**：2–24 个字符。输入 CSV 最长为 22 字符，与此上限自洽。**【社区说法 + 与输入数据自洽】**
- **不能包含**：`@`、空格、连字符 `-`、斜杠。**【社区说法】**
- **位置约束**：首尾不应为 `.` 或 `_`（平台侧会拒绝这种用户名）。**【推断】**
- **大小写**：**查询不敏感**（`TikTok.com/@SR.SMITS03` 与 `@sr.smits03` 指向同一账号），但平台保留用户的原始大小写用于展示。**【推断，需实测确认】**
- **规范主页 URL**：`https://www.tiktok.com/@<handle>`（`@` 是路径的一部分，不带 `@` 的 `https://www.tiktok.com/sr.smits03` 不是主页）。

**规范化建议**（题目要求 `normalized_handle` 且要求 `handle` 原样保留）：`trim` → 去掉 `@` 前缀 → 去掉 `https://www.tiktok.com/` 之类 URL 包装 → 去尾部 `/` 与 query → 转小写。**不要**动 `.` 和 `_`，它们是合法字符，不是分隔符。

### 1.3 哪些输入天然会失败

输入里有 `user6719638728`、`veritolashista2079`、`jesuslovesyou10160` 这类自动生成/长数字后缀的 handle，**大概率本来就不存在或已改名**。这是 `not_found` 的正常来源，**不要为了刷成功率去搜索引擎猜一个"像它"的账号补上**——题面明确把"未经验证的成功数据"列为倒扣项。

---

## 2. 无登录页面可访问性（实测记录：URL / 状态 / 是否含数据）

### 2.1 实测原始记录

下表是我**真实执行**的全部抓取尝试与返回。**没有一条拿到 TikTok 的 HTML**，因此"是否内嵌结构化 JSON"无法从本次调研得出。

| # | 目标 URL | 结果 | 原始错误/状态 | 是否含达人数据 |
|---|---|---|---|---|
| 1 | `https://www.tiktok.com/robots.txt` | 未建立连接 | `URL hostname "www.tiktok.com" resolves to a non-public IP address` | — |
| 2 | `https://www.tiktok.com/@sr.smits03` | 未建立连接 | 同上 | — |
| 3 | `https://tiktok.com/robots.txt` | 未建立连接 | `URL hostname "tiktok.com" resolves to a non-public IP address` | — |
| 4 | `https://m.tiktok.com/@sr.smits03` | 未建立连接 | `URL hostname "m.tiktok.com" resolves to a non-public IP address` | — |
| 5 | `https://r.jina.ai/https://www.tiktok.com/robots.txt`（公共阅读代理，试图绕过本机 DNS） | 未建立连接 | `URL hostname "r.jina.ai" resolves to a non-public IP address`（`r.jina.ai` 解析到 `128.242.240.221`，与 `urlebird.com` 的 `128.242.240.253` 同段，属拦截段） | — |
| 6 | `https://web.archive.org/web/2025/https://www.tiktok.com/@sr.smits03`（Wayback 存档） | 网络错误 | `web fetch failed: TypeError: fetch failed` | — |
| 7 | `https://html.duckduckgo.com/html/?q=...` | 未建立连接 | `resolves to a non-public IP address` | — |

**对照组（证明工具正常、出口可用）：**

| 目标 | 结果 | 说明 |
|---|---|---|
| `https://example.com` | **HTTP 200**，返回正文 | 抓取工具本身可用 |
| `https://www.baidu.com` | **HTTP 200** | 出口可访问部分公网 |
| `https://cn.bing.com/search?q=...` | **HTTP 200**，返回完整 SERP | 可用作检索，但结果为中国区本地化结果，质量差 |
| `https://tikwm.com/` | **HTTP 403** Cloudflare "Sorry, you have been blocked"，回显 `Your IP: 112.10.196.22` | 第三方站可达，但被 Cloudflare 挡 |
| `https://tikwm.com/api/user/info?unique_id=sr.smits03` | **HTTP 403** 同上 | 第三方 API 同样被挡 |
| `https://countik.com/` | **HTTP 403** "Just a moment..."（JS 挑战页） | 同上 |

### 2.2 结论（关于无登录可访问性）

- **我无法在本次环境中回答"无登录能否拿到主页 HTML"**。任何声称"未登录访问返回 200 且含 `__UNIVERSAL_DATA_FOR_REHYDRATION__`"的说法，在本报告中都属于**未验证**，请勿作为事实引用。
- 可以确认的是：**TikTok 的封禁发生在网络层而非应用层**——说明平台侧之外还存在"环境能否到达"这一前置变量，这在写 README 的"已知限制"时必须提到。
- 另有一个**间接旁证**：第三方 TikTok 数据站（tikwm、countik）从同一出口 IP 访问时被 Cloudflare 挑战——说明该出口 IP（`112.10.196.22`）信誉一般，**如果这个 IP 去请求 TikTok 主站，拿到 403/验证码的概率显著高于住宅 IP**。这是"限速也没用"的一类失败，必须靠 `blocked` 状态如实上报。**【实测 + 推断】**

### 2.3 你侧 5 分钟复测脚本（把这一步变成可交付证据）

```bash
# 1) 连通性 + 状态码 + 是否跳登录
curl -sS -o /tmp/p.html -D /tmp/h.txt -w '%{http_code} %{url_effective}\n' \
  -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36' \
  'https://www.tiktok.com/@sr.smits03'

# 2) 是否内嵌结构化 JSON
grep -o '__UNIVERSAL_DATA_FOR_REHYDRATION__' /tmp/p.html | head -1
grep -o 'SIGI_STATE' /tmp/p.html | head -1

# 3) 关键字段是否出现在原始 HTML 里
grep -o '"followerCount":[0-9]*' /tmp/p.html | head -3
grep -o '"privateAccount":[a-z]*' /tmp/p.html | head -3
```

**判读**：拿到 `200` 且 `grep` 命中 → 走 §4 的 JSON 解析路线；拿到 `200` 但无 JSON → 走 DOM/`og:` 标签兜底；拿到 `3xx` 跳 `login` → 记 `blocked`；`403/429` → `blocked`；`404` 或页面文案 "Couldn't find this account" → `not_found`。

---

## 3. robots.txt 与条款边界

### 3.1 robots.txt：**未能取得原文（如实记录）**

我对 `https://www.tiktok.com/robots.txt` 和 `https://tiktok.com/robots.txt` 各发起一次抓取，均在 DNS 层被拒（见 §2.1）。**因此本报告不引用任何 robots.txt 的具体 `Disallow`/`Allow` 行**——那样做就是编造。

**核对方法（请在你侧执行，并把结果贴进 README）：**

```bash
curl -sS 'https://www.tiktok.com/robots.txt' | tee robots.txt
grep -nE '^(User-agent|Allow|Disallow|Sitemap)' robots.txt
```

**判读要点（这是判断"是否被 robots 允许"的真正标准）：**

1. **找你的 User-Agent 命中的那一组**。TikTok 的 robots 通常按 UA 分组（`Googlebot`、`bingbot`、`*` 等），**只有 `User-agent: *` 组对你有效**，别拿 `Googlebot` 组的 `Allow` 当自己的许可。
2. **路径前缀匹配是最长匹配 + `Allow` 优先**：若同时存在 `Disallow: /` 与 `Allow: /@`，则 `/@` 下被允许；若只有 `Disallow: /api/`，则 `/@handle` 的 HTML 页面**在 robots 意义上并未被禁止**。**但这只是"robots 允许"，不等于"条款允许"（见 §3.2）。**
3. **`/api/` 被 Disallow 是极常见配置**：这意味着即便技术上能直接打 `https://www.tiktok.com/api/user/detail/?uniqueId=xxx`，也属于**明确违反 robots**，题面"遵守 robots"的红线会直接踩中。**不要走 `/api/` 路径。**
4. **robots 是" crawler 协议"而非法律授权**：robots 允许 ≠ 平台同意你抓；违 robots ≠ 一定违法。两个判断要分开写进 README。

**工程建议（在拿不到原文时也成立）**：实现里加一个**启动时抓一次 robots.txt 并用 `urllib.robotparser` 解析**的守卫，命中 `Disallow` 就拒绝请求并记 `blocked`（reason=`robots_disallow`）。这样即使平台改了规则，你的程序也自动合规，且**这本身就是评分点**（"遵守 robots"可被代码证明，而不是口头声明）。

### 3.2 服务条款：条文位置与核对清单（未能逐字核对）

TikTok 的条款页（`https://www.tiktok.com/legal/page/us/terms-of-service/en`）与开发者条款（`https://developers.tiktok.com/`）在本次环境中同样不可达。**以下为"该去哪一节找 + 找什么关键词"，不是引文，请勿当作原句引用。**

| 文档 | 大致位置 | 要找的关键词 | 为什么重要 |
|---|---|---|---|
| TikTok Terms of Service（US 版） | "Prohibited uses" / "Your use of the Services" 一节 | `robot`、`spider`、`crawler`、`scraper`、`automated means`、`harvest`、`circumvent` | 这是"自动化访问是否被禁"的主条款 |
| TikTok Terms of Service | "Our Content" / "Your Content" 与授权条款 | `license`、`publicly available`、`reproduce` | 决定"下载头像到本地"是否属于被禁止的复制 |
| TikTok Community Guidelines | 全篇 | `scraping`、`automation`、`bot` | 主要约束账号行为，对匿名抓取约束较弱，但需引用 |
| TikTok Developer Terms / API ToS | "Acceptable use" / "Restrictions" | `scrape`、`crawl`、`rate limit`、`not to access by any means other than the API` | **如果要打 `/api/`，这是最直接的禁令来源** |
| TikTok 隐私政策 | "How we share information" / "Your rights" | `public profile`、`personal data` | 抓 bio/头像属于处理个人数据，非商业研究也需说明 |

**结论（可写进 README 的措辞）**：

1. 平台条款几乎必然含"不得使用机器人/爬虫/自动化手段访问服务"的通用条款（这是 Meta/X/TikTok 一类 UGC 平台的标准配置），因此**严格按字面读，任何自动化抓取都处于"违反 ToS"的位置，无论是否登录、是否低频**。**【推断，但置信度高；务必在核对原文后改成引用】**
2. ToS 违约的后果主要是**民事/账号层面**（封 IP、封号、要求停止），与"绕过技术保护措施"（可能触及 CFAA/DMCA 类条款）性质不同。**本任务的关键分界线是：不做登录、不破验证码、不破付费墙、不伪造身份。** 只要守住这四条，"公开页面 + 低频 + 只取公开字段"属于风险最低的一档，但仍**不能声称"合规"**，只能声称"在公开边界内、已尽力克制"。
3. **不要在 README 里写"已获平台授权"或"符合 TikTok ToS"**——无法证实，且面试官一眼能看出是硬凑。

---

## 4. 页面数据结构与字段路径

> **本节全部为【未验证】。** 我没拿到任何 TikTok HTML，以下结构来自公开资料与同类实现的普遍描述，**必须在你侧用一条 grep 确认后才能写进代码注释或 README**。为降低误导，我给出"候选路径 + 一行验证命令"，而不是断言。

### 4.1 两种历史形态

| 形态 | 出现时期 | 特征 | 现状 |
|---|---|---|---|
| `SIGI_STATE` | 较早（约 2021–2022） | `<script id="SIGI_STATE" type="application/json">`，含 `UserModule.users.<handle>.stats` | **大概率已下线/仅部分页面保留**，不要作为主路径 |
| `__UNIVERSAL_DATA_FOR_REHYDRATION__` | 较新（2022 至今） | `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">`，`defaultScope` → `webapp.user-detail` | **应作为主路径**，但需实测 |

### 4.2 候选字段路径（待验证）

```
# 形态 A：__UNIVERSAL_DATA_FOR_REHYDRATION__
__DEFAULT_SCOPE__["webapp.user-detail"].userInfo.user   → { uniqueId, nickname, signature, avatarLarger, avatarMedium, avatarThumb, privateAccount, region, verified }
__DEFAULT_SCOPE__["webapp.user-detail"].userInfo.stats  → { followerCount, followingCount, heart/heartCount, videoCount }
# 形态 B：SIGI_STATE
UserModule.users["<handle>"].stats                        → { followerCount, followingCount, heartCount, videoCount }
UserModule.users["<handle>"].user                         → { nickname, signature, avatarLarger, privateAccount }
```

对应关系（题目字段 → 候选键）：

| 题目字段 | 候选键 | 备注 |
|---|---|---|
| `display_name` | `userInfo.user.nickname` | 也常在 `<title>` / `og:title` 里 |
| `bio` | `userInfo.user.signature` | 空简介会是 `""`，不是缺失 |
| `avatar_url` | `userInfo.user.avatarLarger` | 见 §7 |
| `follower_count` | `userInfo.stats.followerCount` | **应为整数** |
| `following_count` | `userInfo.stats.followingCount` | 可选字段 |
| `likes_count` | `userInfo.stats.heart` 或 `heartCount` | **键名两代不一致，必须两个都试** |
| `video_count` | `userInfo.stats.videoCount` | 可选字段 |
| 私密标志 | `userInfo.user.privateAccount` | 见 §5 |

### 4.3 一行验证命令（务必先跑）

```bash
python - <<'PY'
import json,re,sys
h=open('/tmp/p.html',encoding='utf-8',errors='ignore').read()
m=re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',h,re.S)
print("has_script:", bool(m))
if m:
    d=json.loads(m.group(1))
    def walk(o,p="",depth=0):
        if depth>6: return
        if isinstance(o,dict):
            for k,v in o.items():
                if k in ("webapp.user-detail","userInfo","stats","user"):
                    print("PATH", p+"/"+k, "->", list(v)[:12] if isinstance(v,dict) else type(v).__name__)
                walk(v,p+"/"+k,depth+1)
    walk(d)
PY
```

**若 `has_script: False`**：退回 DOM 解析（`h1[data-e2e="user-title"]`、`h2[data-e2e="user-bio"]`、`strong[data-e2e="followers-count"]` 一类的 `data-e2e` 属性，同样**待验证**），并同时读 `og:title` / `og:description` / `og:image` 三个 meta 作为最小可用集——这三者在 SSR 页面上通常稳定存在，是**最抗改版的兜底**。

---

## 5. 状态分类的可观察信号

五态映射是本题 20 分的大头（异常处理）+ 30 分（真实性）。下表是**可离线实现**的判定规则（信号本身待验证，但判定优先级可以直接用）。

| 状态 | HTTP | 页面/JSON 信号 | 判定要点 |
|---|---|---|---|
| `not_found` | **404**（有时 200 + 空数据） | 页面出现 `Couldn't find this account` / `找不到此账号`；JSON 里 `userInfo` 为 `null` 或整个 `webapp.user-detail` 键缺失 | **"200 但无 userInfo" 要判 not_found，不能判 ok** |
| `private` | **200** | `userInfo.user.privateAccount == true`；页面出现 `This account is private` / `私密账号`；`stats.videoCount` 可能仍 > 0 但视频列表为空；bio/粉丝数**仍然可见**（关键区别） | 私密账号的**元信息通常仍公开**，只是内容不可见 → 应记 `status=private`，但**仍可填 bio/follower**（是否填由你定，写进 README） |
| `blocked` | **403 / 429 / 5xx**，或 200 但内容是验证页 | 出现 `verify`、`captcha`、`请完成验证`、`Too many requests`；HTML 极短（< 5KB）且无 `__UNIVERSAL_DATA...`；跳转 `?lang=`/`/login` | **空壳页 + 无 JSON = blocked 而不是 ok**；**重试 2 次仍如此就停，不要硬刚** |
| `error` | 连接失败 / 超时 / DNS 失败 / JSON 解析异常 / 本地 IO 失败 | 异常类型（`ConnectionError`、`Timeout`、`JSONDecodeError`、`UnicodeDecodeError`） | **区分"平台拒绝"和"我的程序坏了"**：前者 blocked，后者 error。**本次调研的 DNS 失败就属于 error 类（环境问题），不是 blocked** |
| `ok` | 200 且 `userInfo.user` 存在且非空 | — | **只在拿到结构化数据时置 ok**，不要用 ok 兜底 |

**判定优先级（建议写成一个纯函数 + 表驱动测试）：**

```
异常(网络/DNS/解析/IO) → error
robots 禁止           → blocked(reason=robots_disallow)
HTTP 429/403/5xx      → blocked
HTTP 404              → not_found
200 且无 userInfo      → not_found
200 且 privateAccount  → private
200 且有 userInfo      → ok
其它                   → error（绝不 ok）
```

**两个易错点：**

1. **`private` 不等于"没有数据"**。私密账号的 nickname/bio/粉丝数在未登录页面通常仍可见，若你的代码把它当 `not_found` 处理，会白丢数据且分类错误。
2. **"空 bio" 与 "没采到 bio" 必须分开**：`signature == ""` → `status=ok, bio=""`；`userInfo` 缺失 → `bio=null`。题目 Schema 只有一个 `bio` 字段，靠 `status` 区分语义，这点必须写进 README。

---

## 6. 粉丝数与头像的处理要点

### 6.1 粉丝数：解析是纯函数，别在解析器里做网络

**页面展示值**：`1.2K`、`12.3K`、`3.4M`、`1.2B`、`12,345`、`1.2万`（中文界面）。**内嵌 JSON 应为原始整数**（`"followerCount": 12345`）——这是 TikTok 一类 SSR 页面的普遍行为，**但本次未验证**。

**解析策略（推荐，且可完全离线测试）：**

1. **优先取 JSON 整数**：`int(stats["followerCount"])`；若字段是字符串，先 `int()` 再兜底。
2. **只有拿不到 JSON 时才解析展示值**，规则：
   - 去空白、去千分位逗号、去 `粉丝`/`followers` 等词；
   - 正则 `^([\d.]+)\s*([KMB]?)$`，`K=1e3, M=1e6, B=1e9`（大小写都收，`k/m/b` 小写也常见）；
   - **四舍五入用 `round` 而非截断**：`1.25K → 1250`；`3.4M → 3_400_000`；
   - `1.2万` → `12000`（中文数量级要单独映射：`万=1e4`、`亿=1e8`）；
   - **解析失败返回 `None`，绝不返回 0**——`0` 会被误读成"这个达人真的没有粉丝"。
3. **展示值天然有损**：`1.2K` 的真实值可能是 1150–1249。若字段来自展示值，**在 `language_evidence`/`source_urls` 之外再加一个 `follower_count_precision: "approx"`**（Schema `additionalProperties: true` 允许），这是加分项。
4. `heart`/`likes` 的键名在不同版本可能是 `heart` 或 `heartCount`，两个都取。**【社区说法】**

**测试样例（必须进单元测试）：**

| 输入 | 期望 |
|---|---|
| `"1.2K"` | `1200` |
| `"3.4M"` | `3400000` |
| `"12.3K"` | `12300` |
| `"1.2B"` | `1200000000` |
| `"12,345"` | `12345` |
| `"1.2万"` | `12000` |
| `""` / `"—"` / `"N/A"` | `None` |
| `"-5"` | `None` |

### 6.2 头像 URL

- **形态**：CDN 域名形如 `https://p16-sign-va.tiktokcdn.com/...`（或 `p19-...`、`p16-sign-va.tiktokcdn-us.com`），路径含签名/过期参数。**【社区说法】**
- **三档尺寸**：`avatarLarger`（约 200×200）、`avatarMedium`（约 100×100）、`avatarThumb`（约 50×50）。**下载 `avatarLarger`**。**【社区说法】**
- **referer/签名限制**：普遍报告是**可匿名直接 GET**，但**不少 CDN 会对 `Referer` 或过期签名做校验**，表现为 `403` 或返回 1×1 占位图。**【社区说法】**
- **必须做的三件事**：(1) 下载时带 `User-Agent` 与 `Referer: https://www.tiktok.com/`；(2) **校验响应 `Content-Type` 以 `image/` 开头且字节数 > 1KB**（防占位图）；(3) `avatar_url` 存原始 URL（会过期），`avatar_file` 存本地相对路径。
- **格式**：多为 `jpeg`/`webp`，**不要硬编码 `.jpg` 扩展名**，按 `Content-Type` 决定，或统一存 `.webp` 并在 README 说明。
- 本次因 CDN 域名（`*.tiktokcdn*.com`）解析到拦截段，**未能实测下载**。

---

## 7. 反爬现实与限速建议

### 7.1 无登录高频请求的典型表现（社区汇总，按严重度）

| 表现 | 含义 | 应对 |
|---|---|---|
| `429 Too Many Requests` | 明确限流，通常带 `Retry-After` | 退避（指数 + 抖动），`Retry-After` 优先 |
| `403 Forbidden` + Cloudflare/验证页 | IP 被标记 | **停止**，换时间窗口，不要重试 |
| 200 但 HTML 极短、无 JSON | **软拦截**（最阴险） | 视为 `blocked`，绝不能当 `not_found` |
| 跳 `?lang=xx` 或 `/login` | 地域/风控重定向 | `blocked` |
| 验证码/滑块 | 需人机验证 | **绝不破解**，直接 `blocked` 并记录 |
| 空白页 / `Connection reset` | IP 级封禁前兆 | 立即降速/停跑 |
| 连续 200 但数据全空 | 可能是 A/B 或降级 | 抽样人工复核 |

### 7.2 请求间隔（社区公认区间）

- **串行单 IP：1 请求 / 3–8 秒**（即 7–20 请求/分钟）是保守安全区；**1 请求 / 1 秒**在很多报告里已经开始吃 429。**【社区说法】**
- 100 条 × 5 秒 ≈ **8–9 分钟纯抓取**，完全在 6 小时预算内——**所以没有任何理由冒险提速**。
- **加抖动**（`3 + random()*3` 秒）比固定间隔更像人；**并发度建议 = 1**，最多 2。
- 需要重试时：`429/5xx` 最多 2 次，退避 `5s → 15s`；`403/验证码` **不重试**。

### 7.3 必备请求头

```
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8
Accept-Language: en-US,en;q=0.9
Referer: https://www.tiktok.com/
```

- **不要伪造 `Googlebot` UA**：一旦被识别就是"伪装爬虫"，性质比普通 UA 更差，且违反题面"不绕限制"的精神。
- **不要带任何 Cookie / `msToken` / `ttwid`**：无登录就是无登录，带伪造 token 属于绕过。
- 用 `requests.Session` 复用连接，比每次新建 TLS 握手更省事也更像正常浏览。

---

## 8. 兜底来源评估（含"不可用"清单）

> 原则：**兜底来源只能"换一个公开入口"，不能"换一种绕过方式"。** 凡是需要过验证码、破解签名、伪造登录态的，一律归入"不可用"。

| 来源 | 能拿到什么 | 合法性风险 | 被封/失效概率 | 结论 |
|---|---|---|---|---|
| **TikTok 主站 `www.tiktok.com/@handle`** | 全字段 | 中（ToS 通用禁令），但属公开页面 | 中（IP 信誉差时高） | **首选** |
| **搜索引擎结果页**（Bing/Google 的 `site:tiktok.com` 摘要） | display_name、bio 片段、粉丝数片段 | 低（公开 SERP，但抓 SERP 本身可能违反引擎 ToS） | 中 | **可用于交叉验证**，不作主来源 |
| **Bing 缓存 / `cc.bingj.com`** | 历史 HTML 快照 | 低 | **高**（Bing 已大幅下线缓存） | 慎用，命中率低 |
| **Google 缓存** | — | — | **已停用（2024 年下线）** | **不可用** |
| **Wayback Machine** | 历史快照，含 `og:` 标签 | 低（公益存档，公开可访问） | 中（TikTok 页面存档稀疏、且常被 robots 排除） | 慎用，仅作"曾经存在"的证据 |
| **urlebird.com** 等第三方 viewer | bio、粉丝数、头像、最近视频 | **中高**：站点本身是未授权镜像，数据可能过期/错误；抓它属于"抓二手" | 高（Cloudflare） | **仅作最后兜底，且必须标注来源** |
| **tikwm.com `/api/user/info`** | 结构化 JSON | **高**：未授权第三方 API，其数据来源不明；部分接口要求 key/签名 | 高（本次实测直接 403） | **不建议作为交付依赖** |
| **Social Blade** | 粉丝数历史、排名 | 中（公开页，但 ToS 禁止抓取） | 中 | 仅作交叉验证 |
| **需要登录/验证码的镜像站、`tiktok.com/api/*` 直连、任何"签名算法"实现** | — | **违反题面红线** | — | **不可用（淘汰级）** |

**判定口径（写进 README）**：`status=ok` 时 `source_urls` 必须包含**你实际解析出字段的那个 URL**；如果字段来自第三方，必须在 `source_urls` 里出现该第三方 URL，并在 `error`/扩展字段注明"二手来源、可能过期"。**不要把第三方数据伪装成主站数据。**

---

## 9. 对实现方案的直接影响（必须做 / 必须避免）

### 9.1 必须做

1. **先做连通性自检**：启动时对 `https://www.tiktok.com/robots.txt` 发一次请求，失败就把原因写进 `report.json` 的 `environment` 段，并在 README 写"运行前置条件"。这能把本次调研遇到的"环境不可达"从事故变成设计。
2. **robots 守卫**：`urllib.robotparser` 解析 + 缓存，命中 Disallow → `blocked(robots_disallow)`。
3. **限速器**：全局串行、3–8 秒抖动、单域名令牌桶；**默认并发 1**。
4. **HTTP 快照缓存**：`cache/http/<sha256(url)>.json` 存 `{status, headers, body, fetched_at}`，断点续跑 + 可审计。
5. **五态映射纯函数 + 表驱动测试**（§5 的优先级表直接可测）。
6. **`parse_count` 纯函数 + §6.1 的测试表**。
7. **空 bio ≠ 失败**：`ok + bio=""`。
8. **`source_urls` 逐字段可追溯**，`collected_at` 统一 UTC ISO 8601。
9. **日志脱敏**：过滤 `Cookie|Authorization|token|proxy|msToken`。

### 9.2 必须避免

1. **不打 `https://www.tiktok.com/api/*`**（robots 大概率 Disallow，且题面禁止绕限制）。
2. **不伪造 UA 为搜索引擎爬虫**，不带任何伪造 Cookie/token。
3. **不碰验证码**：遇到即 `blocked`，不重试超过 2 次。
4. **不用 `ok` 兜底**：空壳页必须落 `blocked`/`error`。
5. **不为提升成功率去猜账号**（搜索"相似 handle"补数据 = 伪造）。
6. **不在交付物里写 "compliant with TikTok ToS"**——只写"仅访问无登录公开页面、遵守 robots、限速"。
7. **不把第三方数据当主站数据**且不标注。

---

## 10. 未验证事项与风险

| 项 | 状态 | 影响 | 建议 |
|---|---|---|---|
| TikTok 主站无登录可访问性（200？跳登录？） | **未验证（本次 DNS 层被拦）** | 决定整题可行性 | 你侧 5 分钟复测（§2.3） |
| `__UNIVERSAL_DATA_FOR_REHYDRATION__` 是否存在、键名 | **未验证** | 决定解析器写法 | 跑 §4.3 脚本 |
| `SIGI_STATE` 是否还在 | **未验证**，大概率已弃用 | 不要写主路径 | 只作 fallback |
| robots.txt 具体 Allow/Disallow 行 | **未验证（未取得原文）** | 决定"是否允许抓主页" | `curl` 后贴进 README |
| ToS 逐字条文 | **未验证（页面不可达）** | 报告不能引用原句 | 按 §3.2 核对后再引用 |
| 头像 CDN 是否校验 Referer | **未验证** | 决定下载成败 | 带 Referer + 校验 Content-Type |
| 私密账号的 bio/粉丝是否仍公开 | **未验证**（社区普遍说"部分仍可见"） | 影响 `private` 态字段填充 | 实测 1 个私密账号 |
| 展示值解析精度 | **已可用**（纯离线，可自测） | — | 直接写测试 |

**三个真正的风险：**

1. **环境风险（最高）**：你的运行环境可能像本次一样根本到不了 TikTok。**这会让"代码写得好"变成 0 分覆盖率**。→ 必须提前自检 + README 声明。
2. **IP 信誉风险**：本次出口 IP 在第三方站直接被 Cloudflare 拦。若 TikTok 也这样，`blocked` 会飙到 50%+。→ 降速无法解决，只能如实上报 + 换网络环境（不要用代理池对抗，属于"绕限制"）。
3. **页面改版风险**：TikTok 前端结构变动频繁，JSON 键名（`heart` vs `heartCount`）已出现过漂移。→ **多路径解析 + `og:` meta 兜底 + 解析失败即 `error` 而非静默 `null`**。

---

## 11. 附：30 分钟复测清单（把"未验证"变成"已验证"）

按顺序执行，每步把输出贴到 README 的"来源与验证"一节：

1. `curl -sS -w '%{http_code}\n' https://www.tiktok.com/robots.txt` → 保存原文，`grep -E 'User-agent|Allow|Disallow'`（§3.1）
2. `curl` 一个**确定存在**的 handle（如 `@tiktok`）→ 记录状态码、是否跳登录、HTML 大小
3. `grep '__UNIVERSAL_DATA_FOR_REHYDRATION__'` / `grep 'SIGI_STATE'` → 确认形态
4. 跑 §4.3 的 Python 脚本 → 打印真实键路径，回填 §4.2 的表
5. `curl` 一个**确定不存在**的 handle（如 `@zzzz_no_such_user_99999`）→ 记录 404 还是 200+文案
6. 找一个**私密账号** → 看 `privateAccount`、bio、粉丝数是否仍可见
7. 连续请求 5 次不 sleep → 观察是否出现 429/403/空页 → 定出你的安全间隔

做完这 7 步，本报告中所有【未验证】都能变成【实测】，那份 README 就是这道题最硬的部分。

---

### 引用来源说明

本次调研因网络层拦截，**未能打开任何 tiktok.com 官方页面**，故正文不列出未经核对的官方原句。需要在报告中引用的官方入口为：

- robots.txt：`https://www.tiktok.com/robots.txt`
- 服务条款（美国版）：`https://www.tiktok.com/legal/page/us/terms-of-service/en`
- 社区准则：`https://www.tiktok.com/community-guidelines/en/`
- 开发者条款/API 文档：`https://developers.tiktok.com/`

以上四者**均需在你侧打开后，把原文行贴进 README**，再在报告里标注【官方原文】。在此之前，任何"TikTok 条款第 X 条规定……"的表述都不应出现在交付物中。
