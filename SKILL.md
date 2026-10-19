---
name: design-md
metadata:
  version: "1.0.0"
  requires:
    bins: ["python3"]
    optional: ["gh", "curl", "node"]
  env:
    optional: ["DEEPSEEK_API_KEY"]
description: >-
  DESIGN.md 设计契约工作流——为任意项目生成 / 提炼 / 验收前端设计系统。
  按 Google Stitch 规范的 DESIGN.md（YAML 令牌 + 11 节正文）沉淀设计决策，
  产出机器可读 tokens、tokens.css（双形式令牌）、Tailwind 映射与可视化预览页，
  并用 WCAG 2.1 对比度门禁做回归验收（可在 CI 中阻断构建）。
  集成 awesome-design-md（84 个真实品牌 DESIGN.md 参考库）与 DeepSeek Search/Fetch
  实时网页研究（需 DEEPSEEK_API_KEY，缺失时优雅降级为内置抓取）。
  TRIGGER when: 用户要给项目立设计规范/统一样式（"设计系统"、"DESIGN.md"、"design tokens"、
  "配色规范"、"前端风格不一致"）；要从参考网站提炼配色/字体/圆角；要审计 UI 对比度 /
  可访问性（WCAG、contrast）；要引用 awesome-design-md 里的现成 DESIGN.md；
  为 UI 工作做 design research（竞品视觉分析、品牌参考）。
  DO NOT TRIGGER when: 纯后端 / CLI / 数据管道任务；只需要生成一张图片（用
  qianwen-image-generation）；只是普通代码功能开发且不涉及视觉一致性。
license: MIT
compatibility: "Python 3.9+（纯标准库，零依赖）；可选 gh / curl 用于参考站抓取（两者都缺失时 fetch_ref 报错退出）。OpenCode：放入 skills 目录热加载即用；Claude Code / Cursor 等 SKILL.md 兼容 agent：拷贝本目录即用。无 DEEPSEEK_API_KEY 时网页研究优雅降级为内置抓取。"
---

# design-md · DESIGN.md 设计契约工作流

把「设计决策」从散落的样式代码里抽出来，沉淀成 **DESIGN.md**——一份 AI agent 与人都能读的
设计契约。本 skill 覆盖完整闭环：

```
研究（可选联网） → 提炼（extract） → 生成（scaffold） → 应用到代码 → 验收（verify） → CI 门禁
```

> DESIGN.md 是 Google Stitch 提出的概念：纯文本设计系统文档，放在项目根目录，
> 任何 AI coding agent 读了之后产出的 UI 都能保持视觉一致。
> `AGENTS.md` 管"怎么构建"，`DESIGN.md` 管"长什么样"。

## 目录结构

| 位置 | 用途 |
|---|---|
| `scripts/wcag.py` | WCAG 2.1 对比度引擎：解析 tokens.css / design-tokens.json，自动按约定配对核算（文本 4.5:1、UI 3:1），exit code 可直接当 CI 门禁 |
| `scripts/extract.py` | 从任意 URL 提炼设计令牌草稿（配色排名 / 字体栈 / 圆角），产出 `tokens-draft.json` + DESIGN.draft.md 骨架 |
| `scripts/scaffold.py` | 从令牌 JSON 一键生成：`tokens.css`（双形式令牌）+ `tailwind.extend.js` + `preview.html` 可视化目录 + 对比度报告 |
| `scripts/fetch_ref.py` | 从 awesome-design-md 拉取参考 DESIGN.md（84 个品牌，raw → gh api 双通道回退） |
| `scripts/research.py` | DeepSeek Search/Fetch 联网研究（key 从本机文件 / 环境变量读取，**永不回显**；无 key 时优雅报错） |
| `references/spec.md` | DESIGN.md 文件规范：frontmatter + YAML 令牌 + 11 节正文 + 写法规则 |
| `references/lessons.md` | 血泪教训集：双形式令牌、alpha 稀释陷阱、accent 拆分、数据契约等（来自真实生产审计） |
| `references/research.md` | DeepSeek Search/Fetch API 用法 + awesome-design-md 参考库目录（84 slug 全量） |
| `references/verify.md` | 验收清单 + CI 接线模板（npm script / GitHub Actions） |
| `templates/design-tokens.example.json` | 可直接跑通的输入示例（双主题、全部通过 AA），照它改即可 |

## 快速开始

```bash
# 0) 环境：python3 ≥ 3.9，仅用标准库
python3 scripts/wcag.py --help

# 1) 研究（可选）：从参考站点提炼令牌草稿
python3 scripts/extract.py --url https://example.com --out-dir ./design-draft
#    → design-draft/tokens-draft.json + design-draft/DESIGN.draft.md

# 2) 拉一个知名品牌 DESIGN.md 当参考（当灵感，不当抄袭）
python3 scripts/fetch_ref.py --list                 # 看 84 个 slug
python3 scripts/fetch_ref.py --slug linear.app      # → ./DESIGN.reference-linear.app.md

# 2b) （可选）DeepSeek 联网研究——key 由本机文件提供，永不进对话/日志
python3 scripts/research.py check                   # 验证 key（默认读 %USERPROFILE%\.deepseek\api_key）
python3 scripts/research.py search --query "fintech dashboard design site:dribbble.com" --count 8

# 3) 生成完整令牌工程（以你对齐后的 tokens JSON 为输入）
python3 scripts/scaffold.py --tokens my-tokens.json --out ./design-out
#    → tokens.css / design-tokens.json / tailwind.extend.js / preview.html / contrast-report.txt

# 4) 验收（独立跑，也可接 CI）
python3 scripts/wcag.py --tokens ./design-out/tokens.css     # CSS 输入
python3 scripts/wcag.py --tokens ./design-out/design-tokens.json   # JSON 输入
python3 scripts/wcag.py --pair "#E6E9EF:#0A0C10:4.5"         # 单对 hex 速查
```

## 标准工作流（给 agent 的执行顺序）

1. **定需求**：读项目现状（有没有 DESIGN.md / tokens / 组件库），明确主题方向（暗色优先？品牌色？行业调性——金融/开发者工具/医疗…）。
2. **研究**（可选）：用 `references/research.md` 里的方法做设计研究——DeepSeek Search 找参考站点，DeepSeek Fetch / 内置抓取把页面转 Markdown 细读；从 awesome-design-md 拉 1-3 个同行业 DESIGN.md 参考。
3. **提炼/起草**：`extract.py` 出草稿 → 按 `references/spec.md` 的 11 节结构人工/agent 归并角色（把"出现 200 次的 #5e6ad2"变成"品牌主色，用于 CTA 与焦点环"）。
4. **生成**：整理成规范 tokens JSON → `scaffold.py` 产出全套工程文件（含预览页给用户看效果）。
5. **应用**：把 tokens.css / tailwind 映射接进项目；组件按 DESIGN.md §4 的组件规则实现。
6. **验收**：`wcag.py` 全绿 + `references/verify.md` 清单逐项过；把门禁接进 CI（见 verify.md 模板）。
7. **迭代**：改任何色值 → 必须重跑 `wcag.py`，不凭观感；设计决策变更写回 DESIGN.md（版本注记）。

## 硬规则（务必遵守）

1. **对比度不靠观感**：任何颜色改动都要跑 `wcag.py`。文本 ≥4.5:1，UI 控件/边框 ≥3:1。
2. **双形式令牌**：每个颜色同时输出 `--x`（hex）与 `--x-rgb`（通道），否则 Tailwind 透明度修饰符静默失效（详见 lessons.md #1）。
3. **不要用 `bg-{warn}/10` 之类的 alpha 稀释做浅底**——浅底必须是独立令牌（`--warn-soft`）。实测稀释法在浅色主题下对比度反而恶化。
4. **品牌色拆两档**：`--accent`（文字/链接）与 `--accent-solid`（实底按钮）。同一个值不可能同时满足「暗背景上的亮文字」和「白字下的暗底」两个 ≥4.5:1。
5. **可交互边界用 `--border-strong`**（3:1），`--border` 只做装饰性分隔。
6. **诚实标注 Known Gaps**：没提取到的（表单错误态、亮色版、私有字体替代）如实写进 DESIGN.md，不装完整。
7. **参考 ≠ 照抄**：awesome-design-md 的分析对象是各品牌的公开 CSS 特征；引用时读它们的"方法"（层级、节奏、取舍），不要冒充品牌身份；商业项目注意商标与字体授权。

## 安全

- **绝不回显任何 API Key**。key 解析顺序：`--key-file` → 环境变量 `DEEPSEEK_API_KEY` →
  环境变量 `DEEPSEEK_API_KEY_FILE` → 默认文件 `%USERPROFILE%\.deepseek\api_key`（推荐让用户
  自行在终端创建，key 不经过对话/日志）。`research.py` 全链路输出做 `sk-***` 掩码。
- 未配置 key 时不做 docstring 所谓的"必须联网"假设——`extract.py` 走本地 urllib 抓取，DeepSeek 只是增强项。
- 抓取遵守 robots 与访问频率；`extract.py` 默认最多抓 5 张样式表、单张 512KB 上限。

## 与其他能力的关系

- **awesome-design-md**（VoltAgent，MIT）：84 个真实站点的 DESIGN.md 分析集合。本 skill 提供 `fetch_ref.py` 一键取用；它是"参考素材库"，本 skill 是"工作流引擎"。
- **DeepSeek Search/Fetch**：`https://api.deepseek.com/v1/tools/search|fetch`。设计研究阶段的实时网页检索与正文抓取（含 site:/lang:/after: 语法）。按次计费（5 元/1000 次）。本 skill 提供 `scripts/research.py` 封装调用（key 永不回显）。
- **Google Stitch 官方 lint**（可选）：`npx @google/design.md lint DESIGN.md`。
