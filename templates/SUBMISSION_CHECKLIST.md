# 提交检查清单

- [ ] 输入文件中的 100 个 handle 均出现在 `results.jsonl` 中
- [ ] 每个 handle 恰好一条结果，无重复、无遗漏
- [ ] `results.jsonl` 每一行都是合法 JSON
- [ ] `follower_count` 为非负整数或 `null`
- [ ] `language` 为 ISO 639-1 两字母代码或 `und`
- [ ] `language_confidence` 在 0 到 1 之间
- [ ] `status=ok` 的结果包含可复核的公开来源 URL
- [ ] 空 bio 与采集失败已明确区分
- [ ] `not_found`、`private`、`blocked` 和 `error` 的含义清晰
- [ ] 成功下载的头像位于 `avatars/`，路径为相对路径
- [ ] `report.json` 的结果数量和各状态数量一致
- [ ] README 包含安装、运行、架构、限速、重试和断点续跑说明
- [ ] 至少 3 个自动化测试可以运行通过
- [ ] 已提交 `AI_USAGE.md`
- [ ] 代码、日志和结果中不含 Cookie、Token、API Key 或代理凭证
- [ ] 已在全新环境中按 README 完整运行一次
