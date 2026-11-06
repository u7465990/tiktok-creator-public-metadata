# Tt 达人公开元信息采集笔试题（允许使用 AI）

## 背景

我们提供 100 个达人 handle。请设计并实现一个可重复运行的数据采集程序，仅利用公网可访问的信息，补全这些达人的公开元信息。

这是一道允许借助 AI 工具完成的笔试题，重点考察数据采集、数据质量、异常处理、工程化能力，以及对 AI 工具的合理使用。建议限时 6 小时；未完成全部功能时，请优先保证数据真实、过程可复现，并说明取舍。

输入数据见文末「输入 Handle（100 个）」章节。

## 任务目标

对输入中的每个 handle 生成且仅生成一条结果。至少采集以下字段：

|字段|类型|要求|
|---|---|---|
|`handle`|string|原始输入，不得丢失或静默修改|
|`normalized_handle`|string|规范化后的 handle|
|`profile_url`|string/null|最终确认的公开主页 URL|
|`display_name`|string/null|达人展示名|
|`avatar_url`|string/null|头像原始 URL|
|`avatar_file`|string/null|下载后的本地相对路径；无法下载时说明原因|
|`bio`|string/null|公开个人简介；空简介与采集失败需要区分|
|`follower_count`|integer/null|粉丝数，统一转成非负整数|
|`language`|string|ISO 639\-1 代码；无法判断时填 `und`|
|`language_confidence`|number|0 到 1|
|`language_evidence`|object/null|语言判断使用的公开证据和方法|
|`source_urls`|string\[\]|支撑结果的公开来源 URL|
|`collected_at`|string|UTC ISO 8601 时间|
|`status`|string|`ok`、`not_found`、`private`、`blocked` 或 `error`|
|`error`|string/null|失败原因，不能包含 Cookie、Token 等敏感信息|

可选加分字段包括 `following_count`、`likes_count`、`video_count`、公开地区、最近发帖时间，以及字段级来源信息。

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

- 不得直接复用本公司的内部达人数据作为答案。

- 不得把 Cookie、代理凭证、API Key 或个人密钥提交到代码仓库。

- 一个来源被阻断时，应返回明确状态并保留可诊断信息，不能伪造成功数据。

## AI 工具使用说明（允许使用）

允许并鼓励使用 ChatGPT、Claude、Gemini、Cursor、Codex 等 AI 工具辅助完成代码生成、页面结构理解、字段清洗、语言识别和调试。候选人仍需对最终实现和数据真实性负责。请提交 `AI_USAGE.md`，至少说明：

- 使用了哪些模型或工具；

- AI 参与了哪些环节；

- 如何校验 AI 输出、避免幻觉；

- 哪些关键逻辑由人工确认。

评分关注使用方式是否可靠、可审计，而不是是否使用 AI。

## 交付物

1. 可运行的源代码及依赖锁文件；

2. `README.md`：安装、运行、架构、来源选择、限速和失败策略；

3. `results.jsonl`：100 行结果，每个输入 handle 一行；

4. `avatars/`：成功下载的头像；

5. `report.json`：总体成功数、各状态数量、字段覆盖率、耗时和来源分布；

6. `AI_USAGE.md`；

7. 至少 3 个自动化测试，覆盖数量解析、语言结果规范化和异常状态映射。

建议提供一条命令完成采集，例如：

```bash
./run.sh creator-public-handles-100.csv
```

程序重复执行时应复用缓存或支持断点续跑，避免无意义地重复请求公网来源。

## 验收要求

- 输入的 100 个 handle 在结果中全部出现且无重复；

- `status=ok` 的记录必须具有可访问的来源，不允许伪造或用内部数据补齐；

- 所有粉丝数均为整数或 `null`，能够正确解析 `1.2K`、`3.4M` 等格式；

- 明确区分空 bio、主页不存在、账号私密、访问受限和程序错误；

- 抽样复核 20 个账号时，来源、头像、bio 和粉丝数应与采集时公开页面一致；

- 日志和结果中不得出现密钥、Cookie 或完整代理凭证。

公网状态可能变化，因此不会仅以绝对成功率判定结果。对不可访问账号给出真实、可复现的失败状态，优于返回未经验证的数据。

## 评分标准（100 分）

|维度|分值|关注点|
|---|---|---|
|数据真实性与正确性|30|字段准确、无幻觉、数值规范化正确|
|覆盖率与异常处理|20|多来源回退、状态分类、重试和断点续跑|
|工程质量|20|结构、可运行性、测试、日志、配置管理|
|来源与可审计性|15|时间戳、来源 URL、证据和错误可诊断性|
|AI 使用质量|10|使用合理、结果校验、成本与缓存意识|
|合规与安全|5|公开信息边界、限速、敏感信息保护|

## 面试追问

- 如果输入从 100 个扩大到 500 万个，你会如何设计调度、去重、刷新和成本控制？

- handle 发生变更时，如何识别同一达人并避免产生重复实体？

- 如何定义字段新鲜度，并证明粉丝数不是历史缓存？

- 当不同公开来源的粉丝数不一致时，如何选择或融合？

- 如何监控采集成功率下降，并区分页面改版、账号失效和访问限制？

## 输入 Handle（100 个）

```text
sr.smits03
israelarguetaa
carlit0s_toys
heathermomof4kiddos
stephjacobe
user6719638728
franyerlisri
syl_hoops
mateomarteell11
skizzlow222
glrefurbishing
shell_hips
bassurgence
cupcakelady77
naldo_videos_gt2
whoisgabs13
kikikiara
plushies_youchoose
daddiestoyboy
nanoflx
boo.licious
quonn1yx
kharis_gardner
film.judge6
alexaaaclark
krystalkalina
jose.diaz7468
ou_dog
hnieves77
jordang_tattoo
nibras_n13
seandarko
music.therapy22
mdlanc1716
fddj24
kuttem12kkk
cute.pet.life58
dedcurryhabibi
cassidyy.nelsonnn
huyfanta999
rudyroque939
tyy.myles
creepyfacts890
ghanakrom
khhxhc
zaecheebv
hifi5710
kammy114114
wildandfree_21
howtossculpt
disaintrk
shannon.scott4
flashygman
mazmynjakenna
vtjndknr
chelseaamadison
thetrumpshow
landonaxel
thezoealiaha
peyton.diane0
amyf4277
fatuma543
ale_mejia40
veritolashista2079
hkteamsold
livingwithamanda
liora10098
taylor.music04
roselynn_life
karatekieth
drunk_n_beauty21
shoppingessentials67
kirklin.makenna
cgurnee
pedronavajas1972
dippi.girlsbb
huahuqnppx6
monicadeviaje
rocklovejewelry
keegan0731
kyleejburleigh
ychuan.pet
foodflo_usa
miroslavarosales1
taylorquon
brycedelange
jesuslovesyou10160
ashkardashbabe
albertoalvarado948
richard.buehling
gwendolynbponyo
nenedetroit
ohdatscayden
scribbles.k
spencer_official_2.0
ocfarmboy
alienquizofc
linadomiinguez
thegirlwiththenotebook
believeinmaybe
```

\[creator\-public\-data\-written\-test\-candidate\.zip\]

