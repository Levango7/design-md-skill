# design-md

> **DESIGN.md 设计契约工作流 — 为 AI coding agent 与团队统一前端设计系统。**
> Design-contract workflow for AI coding agents: research → extract → scaffold → verify → CI gate.

**纯 Python 标准库，零依赖** · 适配任何支持 `SKILL.md` 的 agent（OpenCode / Claude Code / Cursor / Codex…）

---

## 这是什么

把「设计决策」从散落的样式代码里抽出来，沉淀成 **DESIGN.md**——一份 AI agent 与人都能读的设计契约（Google Stitch 规范：YAML 令牌 + 11 节正文）。之后任何 agent 读了它产出的 UI 都会保持视觉一致：`AGENTS.md` 管「怎么构建」，`DESIGN.md` 管「长什么样」。

```
研究（可选联网） → 提炼（extract） → 生成（scaffold） → 应用到代码 → 验收（wcag） → CI 门禁
```

| 能力 | 脚本 | 产出 |
|---|---|---|
| 从任意 URL 提炼设计令牌草稿 | `scripts/extract.py` | `tokens-draft.json` + `DESIGN.draft.md` |
| 一键生成令牌工程 | `scripts/scaffold.py` | `tokens.css`（双形式令牌）+ `tailwind.extend.js` + `preview.html` + 对比度报告 |
| WCAG 2.1 对比度门禁（可断 CI） | `scripts/wcag.py` | 通过/失败清单；exit code ≠ 0 即失败 |
| 取用 84 个真实品牌 DESIGN.md 参考 | `scripts/fetch_ref.py` | `DESIGN.reference-<slug>.md` |
| DeepSeek 联网研究（可选） | `scripts/research.py` | 实时搜索 / 整页抓取为 Markdown（key 只从本机文件读，**永不回显**） |

## 安装

本 skill 是标准 `SKILL.md` 结构，适配任何支持该约定的 agent：

| Agent | 安装方式 |
|---|---|
| **OpenCode** | 拷贝 `design-md/` 目录到其 skills 加载目录（本仓库开发机上为 `agents-skills/`），热加载生效 |
| **Claude Code** | 拷贝到 `~/.claude/skills/design-md/` |
| **Cursor / 其他** | 把本目录（或至少 `SKILL.md`）接入其 rules / skills 机制，见各自文档 |

**运行要求**：Python ≥ 3.9（仅标准库，无需 `pip install`）。可选：`gh` 或 `curl`（抓取参考站）、`DEEPSEEK_API_KEY`（联网研究，非必需，缺失时自动降级）。

## 快速开始

```bash
# 1) 从参考站点提炼令牌草稿
python3 scripts/extract.py --url https://example.com --out-dir ./design-draft

# 2) 拉一个知名品牌 DESIGN.md 当参考（84 个：--list 看全量）
python3 scripts/fetch_ref.py --slug linear.app

# 3) 生成完整令牌工程（输入：按 references/spec.md 对齐后的 tokens JSON）
python3 scripts/scaffold.py --tokens my-tokens.json --out ./design-out

# 4) 验收：WCAG 2.1 对比度门禁（--strict 同时核算半透明横幅合成色）
python3 scripts/wcag.py --tokens ./design-out/tokens.css --strict

# 5)（可选）DeepSeek 联网研究
python3 scripts/research.py check    # 验证 key（读本机文件，不回显）
python3 scripts/research.py search --query "fintech dashboard design" --count 8
```

起手模板见 `templates/design-tokens.example.json`（双主题、全部通过 AA，照它改即可）。

## CI 接线（一行门禁）

```yaml
- run: python3 scripts/wcag.py --tokens ./design-out/tokens.css --strict
```

exit code ≠ 0 即阻断构建；更多模板（npm script / GitHub Actions）见 `references/verify.md`。

## 仓库结构

```
design-md-skill/
├── SKILL.md          # agent 入口：触发条件 / 工作流 / 硬规则 / 安全边界
├── scripts/          # 5 个可独立运行的脚本（纯标准库）
│   ├── extract.py    #   参考站 → 令牌草稿
│   ├── scaffold.py   #   令牌 JSON → tokens.css / tailwind / preview
│   ├── wcag.py       #   WCAG 2.1 对比度引擎（CI 门禁）
│   ├── fetch_ref.py  #   awesome-design-md 参考库拉取
│   └── research.py   #   DeepSeek Search/Fetch 封装（key 永不回显）
├── references/       # spec（文件规范）/ lessons（真实生产审计教训）/
│                     # verify（验收清单+CI 模板）/ research（研究方法）
└── templates/        # 可直接跑通的输入示例
```

## 硬规则（节选，全文见 SKILL.md）

- **对比度不靠观感**：任何色值改动必须跑 `wcag.py`（文本 ≥ 4.5:1，UI 控件 ≥ 3:1）。
- **双形式令牌**：每个颜色同时输出 `--x`（hex）与 `--x-rgb`（通道），否则 Tailwind 透明度修饰符静默失效。
- **品牌色拆两档**：`--accent`（文字/链接）与 `--accent-solid`（实底按钮）——同一个值不可能同时满足两个 ≥ 4.5:1 场景。
- **浅底必须独立令牌**（`--warn-soft`），不用 `bg-{warn}/10` 稀释。
- **诚实标注 Known Gaps**：没提取到的如实写进 DESIGN.md，不装完整。

## 安全与边界

- **API key 永不回显**：`research.py` 解析链 `--key-file` → `DEEPSEEK_API_KEY` → `DEEPSEEK_API_KEY_FILE` → `~/.deepseek/api_key`；全链路输出 `sk-***` 掩码。
- 抓取遵守 robots 与频率限制（最多 5 张样式表、单张 512KB 上限）。
- **参考 ≠ 照抄**：参考库仅用于方法学习（层级、节奏、取舍）；商业项目注意商标与字体授权。

## 致谢与许可

- 本 skill 以 **MIT** 许可开源（见 `LICENSE`）。
- 参考库引用自 [awesome-design-md](https://github.com/VoltAgent/awesome-design-md)（MIT，VoltAgent）：`fetch_ref.py` 按需下载，本仓库不打包其内容。
- DESIGN.md 概念来自 Google Stitch。
