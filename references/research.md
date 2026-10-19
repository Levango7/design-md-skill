# 设计研究：DeepSeek Search/Fetch + awesome-design-md

## 一、DeepSeek Search & Fetch API

> 官方文档：https://api-docs.deepseek.com/zh-cn/guides/search/
> 用途：设计研究阶段的**实时网页检索**与**正文抓取**（把网页转成 Markdown 细读）。

### 基本信息

| API | Endpoint | 说明 |
|---|---|---|
| Search | `POST https://api.deepseek.com/v1/tools/search` | DeepSeek 自研搜索引擎 |
| Fetch | `POST https://api.deepseek.com/v1/tools/fetch` | URL → Markdown 正文 |

- 鉴权：`Authorization: Bearer $DEEPSEEK_API_KEY` + `Content-Type: application/json`
- 计费：各 5 元/1000 次成功请求（返回 200 且产生结果才计费；失败/空结果不计费）
- 限速：Search 100 QPS / Fetch 25 QPS（账号级）

> 本 skill 提供 `scripts/research.py` 封装以上两个端点：key 解析链
> `--key-file` → `DEEPSEEK_API_KEY` → `DEEPSEEK_API_KEY_FILE` → `~/.deepseek/api_key`，
> **永不回显**（输出做 `sk-***` 掩码）；4xx 不重试、408/429/5xx 退避重试 3 次。
> 密钥建议由用户在自己终端落盘：`notepad "%USERPROFILE%\.deepseek\api_key"`（仅一行 key）。

### Search 请求

```json
{
  "query": "crypto exchange dashboard design system",
  "count": 5,
  "need_content": false,
  "ori_question": "帮我的区块链浏览器选一套设计风格"
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `query` | 是 | 1~128 字符。支持搜索语法（下表） |
| `count` | 否 | 1~50，默认 10 |
| `ori_question` | 否 | 触发搜索的原始问题，帮助理解意图 |
| `localization` | 否 | 优先本地化结果的 IP 地址 |
| `need_content` | 否 | true 时 `content` 返回网页正文 |

搜索语法（可组合）：`site:github.com`、`-site:`、`-广告`、`-"release notes"`、`"精确短语"`、`lang:zh,en`、`after:2025-01-01`、`before:2026-06-01`。

### Search 响应字段

`results[]`: `rerank_score`（0~3，≥1.5 优质）、`title`、`url`、`snippet`（百来字，适合展示）、`summary`（600~800 字，适合给模型）、`content`（need_content=true 时的正文）、`site_name`、`site_icon`、`date`、`authority`（0~4，≥3 极权威）。

### Fetch

```json
{ "url": "https://example.com/article" }
```

响应：`{"title": "...", "content": "# Markdown 正文..."}`。受目标站可用性影响；404=拿不到正文，403=安全策略拒绝。

### 错误与重试

400/401/402/403/404 不重试（先修问题）；408/429/5xx 等待后重试；402=余额不足。

### 调用示例

```bash
curl https://api.deepseek.com/v1/tools/search \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "block explorer UI design site:dribbble.com OR site:behance.net", "count": 10}'
```

```python
import os, requests
r = requests.post("https://api.deepseek.com/v1/tools/search",
    headers={"Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}"},
    json={"query": "fintech dark dashboard design", "count": 10, "need_content": False})
for item in r.json()["results"]:
    print(item["title"], item["url"], item.get("rerank_score"))
```

### 设计研究用法建议

| 目标 | 查询模式 |
|---|---|
| 找同行业参考 | `"<行业> dashboard design" site:dribbble.com OR site:behance.net` |
| 找真实站点的设计说明 | `"<站点名> design system" -site:<站点>` 或 `"<站点>" "design tokens"` |
| 竞品视觉分析 | Fetch 竞品首页 → 读 Markdown 里的结构/文案/层级描述 |
| 找公开令牌 | `"<品牌>" css variables colors site:github.com` |
| 时效 | `after:2025 lang:zh,en` 控制新近度与语言 |

> **没有 key 时的降级**：直接用本 harness 的 webfetch/内置抓取；`extract.py` 完全离线可用（urllib）。

---

## 二、awesome-design-md 参考库

> GitHub: https://github.com/VoltAgent/awesome-design-md（MIT）
> 网站: https://getdesign.md/
> 定位：84 个真实网站的设计系统分析（DESIGN.md + README），"Drop one into your project and let coding agents generate a matching UI"。
> 伦理与授权：分析对象为各站**公开可见 CSS 特征**；用于学习其方法与审美取舍，**不要冒充品牌身份**；商标与私有字体注意授权（Upstream 自己也用开源替代字体）。

### 取用方式（三通道）

1. **本 skill 脚本**（推荐）：
   ```bash
   python3 scripts/fetch_ref.py --list
   python3 scripts/fetch_ref.py --slug linear.app          # → ./DESIGN.reference-linear.app.md
   ```
2. **raw URL**（网络通畅时）：
   `https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/<slug>/DESIGN.md`
3. **gh api 回退**（raw 被墙/证书故障时）：
   ```bash
   gh api repos/VoltAgent/awesome-design-md/contents/design-md/<slug>/DESIGN.md --jq .content \
     | base64 -d > DESIGN.reference-<slug>.md
   ```

### 参考文件内部结构（以 linear.app 为例）

frontmatter：`version / name / description` + YAML 令牌区（`colors:`、`typography:`、`components:`…）
正文节：`Overview / Colors / Typography / Layout / Elevation & Depth / Shapes / Components / Do's and Don'ts / Responsive Behavior / Iteration Guide / Known Gaps`
正文引用令牌用 `{typography.display-xl}` 语法。已知用法：`npx @google/design.md lint DESIGN.md`。

### 目录（84 slug，按行业分）

**金融科技/加密（做钱包/浏览器/交易所优先看）**：
`binance`、`coinbase`、`kraken`、`mercury`（初创银行）、`stripe`、`revolut`、`wise`、`nerdwallet`、`mastercard`

**开发者工具/基础设施（做技术产品优先看）**：
`vercel`、`linear.app`、`cursor`、`raycast`、`warp`、`supabase`、`sentry`、`posthog`、`clickhouse`、`mongodb`、`hashicorp`、`composio`、`sanity`、`resend`、`mintlify`、`expo`、`lovable`、`superhuman`

**AI 平台**：
`claude`、`cohere`、`elevenlabs`、`minimax`、`mistral.ai`、`ollama`、`opencode.ai`、`replicate`、`runwayml`、`together.ai`、`voltagent`、`x.ai`、`jobright`

**生产力/SaaS**：
`notion`、`cal`、`intercom`、`sap`、`zapier`、`airtable`、`figma`、`framer`、`miro`、`webflow`、`clay`

**消费/媒体/零售**：
`apple`、`meta`、`airbnb`、`shopify`、`nike`、`starbucks`、`spotify`、`pinterest`、`uber`、`playstation`、`oura`、`dji`、`hp`、`ibm`、`nvidia`、`spacex`、`tesla`、`theverge`、`wired`、`vodafone`、`aljazeera`、`1win`、`mydealz`

**汽车**：`bmw`、`bmw-m`、`bugatti`、`ferrari`、`lamborghini`、`renault`

**怀旧（复古风彩蛋）**：`dell-1996`、`nintendo-2001`

### 使用心法

- 拉 2-3 个**同行业**参考 → 对比它们的"底色策略 / 主色稀缺度 / 字重节奏 / 圆角语言"差异 → 提炼出你项目的取舍，而不是混合成缝合怪。
- 优先读 `Do's and Don'ts` 与 `Known Gaps` 两节——前者是护栏，后者是"作者诚实度"。
- 把参考文件放到项目外（如 `./design-refs/`），只把**消化后的决策**写进你自己的 DESIGN.md，避免两份契约打架。
