# 连通性自检工具

两个脚本，功能一样，按你的系统选一个跑。**只读**：不发请求之外的任何动作，不采集、不保存业务数据、不带 Cookie。

| 系统 | 脚本 | 运行方式 |
|---|---|---|
| Windows | `check-connectivity.ps1` | 右键"使用 PowerShell 运行"，或见下方命令 |
| macOS / Linux | `check-connectivity.sh` | `chmod +x check-connectivity.sh && ./check-connectivity.sh` |

## 运行

Windows（在 `tools` 目录下打开 PowerShell）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-connectivity.ps1
```

macOS / Linux：

```bash
chmod +x check-connectivity.sh
./check-connectivity.sh
```

全程约 1–2 分钟（含 2 秒礼让间隔）。结束时退出码：`0` = 可用，`1` = 能连但有障碍，`2` = 环境不可达。

## 它会检查什么

| # | 检查 | 想确认的事 |
|---|---|---|
| 0 | `curl` 是否可用 | 工具本身没问题 |
| 1 | `example.com` 是否 200 | **对照组**：证明"不是整台机器断网" |
| 2 | `www.tiktok.com` 的 DNS | 解析到的是不是公网地址（污染会解析到私网/保留地址） |
| 3 | 无登录打开 `@tiktok` 主页 | 状态码、是否跳登录、有没有验证码、体积是否过小 |
| 4 | 页面里有没有结构化数据 | `__UNIVERSAL_DATA_FOR_REHYDRATION__` / `SIGI_STATE` |
| 5 | 页面里有没有关键字段 | `followerCount` / `og:title` |
| 6 | 不存在的账号返回什么 | 是 404 还是 200 + "找不到"文案 |
| 7 | `robots.txt` | 原文里的 Disallow 行，以及是否禁止 `/@` |
| 8 | 头像 CDN 能否匿名下载 | 状态码与 Content-Type 是否 `image/*` |

## 怎么读结果

脚本最后会给一句判定，对照下表：

| 判定 | 含义 | 你该做什么 |
|---|---|---|
| 可用：可采集 | 页面能打开且含数据 | 可以开始做骨架；按提示选 JSON 或 og 兜底 |
| DNS 被污染：拿到的是假地址 | 解析结果指向 Facebook/Meta 等无关网段 | 重试、换 UA、降速都没用；换环境 |
| 环境不可达：DNS/连接层被拦 | 这台机器到不了 TikTok | 换境外云主机，或向招聘方申请环境 |
| IP 被限流/封禁 | 403/429 | 降速、换出口；如实记 `blocked` |
| 需要登录才能看主页 | 被重定向到登录 | 按题面记 `blocked`，不要加 Cookie |
| 页面可访问但未找到数据 | 改版或软拦截（空壳页） | 把 `check-output/profile.body.html` 发回来 |
| 本机网络整体异常 | 连 `example.com` 都不通 | 先排查本机网络/代理，与 TikTok 无关 |

## 产物

全部在 `tools/check-output/`：

- `connectivity-report.txt` —— 完整报告（就是屏幕上那份）；
- `profile.body.html` —— 主页原始页面（**最有价值的证据**）；
- `robots.txt` 对应的 body、`notfound.body.html`、各请求的 `*.headers.txt`；
- `avatar.probe.bin` —— 头像探测下载的前 4KB。

把这些文件发回来，就能判断"解析该怎么写"。**里面不含任何 Cookie、Token 或个人凭据**，页面内容本身是公开信息。

## 如果本机到不了 TikTok：开一台境外机器

自检判定"DNS 被污染 / 环境不可达"时，下一步是**把程序放到能访问 TikTok 的机器上跑**。用这个向导：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\vps-wizard.ps1
```

它带你走 6 步，每步都告诉你点哪里、填什么：

| 阶段 | 做什么 | 产出 |
|---|---|---|
| 1 | 在腾讯云/阿里云买一台新加坡或日本的轻量服务器（Ubuntu 22.04，最低配） | 一台运行中的机器 |
| 2 | 记下公网 IP、登录名、密码 | `tools/vps.env` |
| 3 | 生成 SSH 密钥并装到服务器（只输一次密码） | 之后免密登录 |
| 4 | 上传并运行 `check-connectivity.sh` | `captured/connectivity-report.txt` |
| 5 | 抓 `@tiktok` 的主页并存回来 | `captured/profile.html` ← **最重要** |
| 6 | 删掉明文密码、提醒关机/释放 | — |

成本：轻量服务器最低配约几元到几十元/月；按量付费更便宜，但**不用了必须释放**，否则持续计费。全程 20–40 分钟。

注意事项：

- `vps.env` 里是明文密码，**不要提交到任何仓库**，向导最后会提示删除；
- 机房 IP 也可能被 TikTok 判定为爬虫，第 4 步会直接告诉你结论；
- 这不是"翻墙工具"，是正常的境外云服务采购；国内站买境外地域同样走支付宝和实名。

## 常见问题

**Q：报 TLS 握手失败（curl 退出码 35），但我浏览器能上网？**
A：多半是公司代理/杀毒软件在做 TLS 拦截，或者本机走了不透明的代理。先关掉代理软件或换网络再跑一次。

**Q：Windows 提示"无法加载文件，因为在此系统上禁止运行脚本"？**
A：就是上面命令里的 `-ExecutionPolicy Bypass` 参数在起作用，用完整命令运行即可，不需要改系统设置。

**Q：中文显示成乱码？**
A：Windows 用 `powershell`（5.1）跑脚本时，确保终端代码页是 65001：先执行 `chcp 65001`。脚本文件本身是 UTF-8 BOM。

**Q：为什么有 2 秒的等待？**
A：避免连续请求触发限流，让"是否被拦"的结论更真实。

**Q：需要装什么吗？**
A：不需要。Windows 10/11 自带 `curl.exe`；macOS/Linux 自带 `curl`。没有 Python、没有爬虫框架、没有第三方包。
