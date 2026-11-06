# profile_url 是结论，source_urls 是证据链，两者不可互相替代

`profile_url` 只放最终认定的那一个主页地址；`source_urls` 放所有支撑本 Record 字段取值的公开页面，允许包含搜索结果页、第三方页、以及最终主页。常见错误是把 `profile_url` 复制进 `source_urls` 当"已有来源"，或把抓过的所有 URL（包括 404 的）都塞进 `source_urls` 造成"来源很多"的假象。这个边界一旦糊掉，可审计性（15 分）就无从谈起。

## Consequences

- 硬约束：`status=ok` 时 `source_urls` 非空，且其中至少一个 URL 的 Provenance 能落到具体字段值。
- 失败态同样保留 `source_urls`（尝试过的地址），用于诊断，但不得声称它支撑了任何值。
- 校验器需要断言：每个非 null 字段都能在 Provenance 中找到对应的 source URL。
