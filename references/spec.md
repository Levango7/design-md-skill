# DESIGN.md 文件规范（spec）

> 依据：Google Stitch DESIGN.md 规范 + awesome-design-md 84 个实例 + NexusChain Explorer 生产实践。
> 一份合格的 DESIGN.md = **YAML frontmatter（机器可读令牌）** + **11 节正文（人/agent 可读规则）**。

---

## 1. 文件两段式结构

```markdown
---
version: alpha                 # 规范版本，沿用 alpha
name: <Project>-design-analysis
description: "一段话说清：底色、主色、字体、气质。要具体到 hex 与形容词。"
colors:                        # 机器可读令牌区（YAML）
  primary: "#5e6ad2"
  canvas: "#010102"
typography:
  display-xl:
    fontFamily: Inter
    fontSize: 80px
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: -3.0px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    ...
---
```

正文随后展开成节。**令牌区是权威值**，正文用 `{colors.primary}` 这种引用语法指回令牌，避免两处硬编码漂移。

## 2. 正文 11 节（推荐全量、可按项目裁剪）

| # | 节 | 写什么 | 判断合格的标准 |
|---|----|--------|----------------|
| 1 | **Overview** | 视觉主题与气质：3-6 个关键词 + 一句哲学 | 读到的人能画出一张"气质板" |
| 2 | **Colors** | 每个令牌：hex + 角色 + 使用场景 + 禁用场景 | 任意组件选色不再需要临场发挥 |
| 3 | **Typography** | 字体栈 + 层级表（字号/字重/行高/字距）+ 字重裁定 | 层级完整到覆盖所有页面元素 |
| 4 | **Layout** | 栅格、容器宽度、节区节奏、间距刻度 | 新页面直接套用，无需发明 |
| 5 | **Elevation & Depth** | 阴影体系 / 亮度层级、层级语义（flat/ring/raised） | 明确定义"什么浮在什么上" |
| 6 | **Shapes** | 圆角体系、禁止超过的上限 | 一处定义，全站一致 |
| 7 | **Components** | 按钮/卡片/输入框/标签/弹窗等：状态全覆盖（default/hover/focus/active/disabled/loading） | 组件不需要设计师也能实现出正确的态 |
| 8 | **Do's and Don'ts** | 护栏清单：✅ 与 ❌ 一一对应 | ❌ 每一条都指向一个真实事故或陷阱 |
| 9 | **Responsive Behavior** | 断点、触摸目标、折叠策略、图像行为 | 移动端行为已裁定，不留给实现者 |
| 10 | **Iteration Guide** | 给 agent 的迭代提示：一次改一个组件、引用令牌名、改完跑 lint/验证 | agent 能按图施工 |
| 11 | **Known Gaps** | 未覆盖的：表单错误态、亮色版缺失、私有字体替代、未实测项 | 诚实清单，防止"看起来什么都有"的假完整 |

> Stitch 官方 9 节对应关系：1-9 即上表前 9 节；awesome-design-md 额外补 10-11（Iteration Guide / Known Gaps）为最佳实践。

## 3. 项目专属扩展节（可选，按需加）

NexusChain Explorer 的两个扩展很值得借鉴，适合工程型项目：

- **图标契约（Icon Contract）**：锁定唯一图标库 + 精确版本（禁 `^` 浮动）+ 尺寸档（16/20/24）+ 「语义→图标」映射表（搜索→Search、成功→CheckCircle2…）。防"每个页面一套图标语言"。
- **数据契约（DTO Contract）**：字段名与后端逐字一致；请求层声明 `REQUIRED_FIELDS` 运行时校验；可能缺失的字段统一 `orDash()` 渲染为 `—`（React 把 undefined 渲染成空串，用户分不清"0"和"缺失"）；测试 mock 必须取自真实 fixtures。

## 4. 写作规则

1. **具体到值**：不写"用稍微深一点的背景"，写 `--surface: #111418`。
2. **每个值给理由**：`border-strong 用于可交互控件边界（WCAG 1.4.11 的 3:1）`。理由让后来者不敢乱改。
3. **反向用例进文档**：把"为什么不用某某做法"（alpha 稀释、双 accent 合一）写进 Don'ts —— 事故记忆是最贵的资产。
4. **修订注记**：文件头保留修订记录（日期 + 一句话 + 修了什么缺陷），让契约有历史。
5. **单一事实源**：tokens.css（或 tokens.json）是权威来源；DESIGN.md 的表格与它手工同步并在 CI 校验（见 verify.md）。
6. **语言**：团队什么语言就什么语言；令牌名与节标题保持英文（agent 解析最稳）。

## 5. 校验工具

```bash
# 官方 lint（可选，需 node）
npx @google/design.md lint DESIGN.md

# 本 skill 的对比度门禁（无需 node）
python3 scripts/wcag.py --tokens tokens.css --strict
```

## 6. 最小合格样例（骨架）

```markdown
---
version: alpha
name: acme-design-analysis
description: "暗色金融风：canvas #0A0C10，主色靛蓝 #8B96FF 只用于链接与激活态，语义色仅作状态。"
colors:
  bg: "#0A0C10"
  surface: "#111418"
  fg: "#E6E9EF"
  accent: "#8B96FF"
---

## Overview
关键词：专业、可信、克制。暗色优先，亮度递进 + 细边框构建层级，不靠重阴影。

## Colors
| Token | 值 | 角色 | 禁用 |
|---|---|---|---|
| `--bg` | `#0A0C10` | 页面背景 | 卡片 |
| `--accent` | `#8B96FF` | 链接/激活 | 大面积实底 |

...（其余 9 节）
```
