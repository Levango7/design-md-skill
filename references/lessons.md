# 血泪教训集（lessons）

> 来源：NexusChain Explorer 前端 2026-09-16 全面质量审查 + 生产修复实战。
> 每一条都是**真事故**——照着抄可以少走几个月的弯路。

## 1. Tailwind alpha 与双形式令牌（最高频事故）

**事故**：颜色只写成 `--surface: #111418`，组件用 `bg-surface/80`。Tailwind v3 对
`var(--surface)` 这类不可解析值**不做 alpha 合成**——`bg-surface/80`、`bg-success/15`、
`border-danger/30` 不生成任何 CSS 规则，**且不报错**。表现为：Badge 浅底退化成实色块、
页头失去半透明——排查半天查不出。

**修复**：每个颜色同时定义两种形式：

```css
--surface: #111418;        /* hex：原生 CSS 直接用 */
--surface-rgb: 17 20 24;   /* 空格分隔通道：供 Tailwind 合成 */
```

```js
// tailwind.config.js
colors: { surface: "rgb(var(--surface-rgb) / <alpha-value>)" }
```

新增颜色必须同步补 `-rgb`，并让构建脚本校验（scaffold.py 自动生成；verify 阶段检查数量对齐）。

## 2. 品牌色必须拆两档（accent / accent-solid）

同一色值不可能同时满足两个方向：
- 暗背景上的品牌**文字**要够亮（≥4.5:1）→ `--accent: #8B96FF`
- 白字下的品牌**实底按钮**要够深（≥4.5:1）→ `--accent-solid: #4B5AE0`

用一个值强行两用，必然一个方向不达标。同理 danger 系：文字 `--danger` 与实底 `--danger-solid` 分开。

## 3. 浅底不要用 alpha 稀释（实测失败）

**错误做法**：`bg-warn/10` 做警告浅底。
**实测**：浅色主题下，"文字色稀释后当底色"会让底色趋近文字色，对比度随不透明度升高**反而恶化**（实测 3.81:1，不达标）。
**修复**：语义浅底拆独立令牌 `--success-soft` / `--warn-soft` / `--danger-soft`，两主题各自定值。

## 4. 可交互边界 vs 装饰边界（WCAG 1.4.11）

输入框边框用 `--border`（装饰色）时，对背景对比度不足 3:1——用户看不清"这里能点"。
拆出 `--border-strong`（≥3:1）用于所有可交互控件的边界；`--border` 只留装饰性分隔。

## 5. 焦点可见性与键盘可达

- `focus-visible` 统一焦点环令牌：`--focus-ring`（2px accent 环 + 2px 底色隔离环）。键盘用户是真实用户。
- 弹窗 **ESC 必须始终可关**。`disableBackdropClose` 只能禁用遮罩点击，**不得连带禁用 ESC**——否则违反 WCAG 2.1.2（No Keyboard Trap）。这是修复过的真缺陷。
- 弹窗打开移焦入内、Tab 循环限制在内、关闭归还焦点；标题 id 用 `useId()` 防碰撞。

## 6. 触摸目标

- 默认按钮 ≥44×44px（WCAG 2.5.5 AAA）。
- 紧凑场景下限 24px（WCAG 2.2 SC 2.5.8 AA）——本项目取 `sm`=36px 作表格行内档。
- 图标按钮必须有 `aria-label`。

## 7. 字重别发明档位

写 `font-weight: 510 / 590` 这类非标准值：字体缺对应字重时浏览器回退，视觉效果不受控。
**裁定**：只用 400/500/600/700；三处文件（DESIGN.md / tokens.json / tokens.ts）必须一致。

## 8. 图标契约

- 全站一个图标库（如 lucide-react），**精确版本号钉死**（禁 `^` 浮动）。
- 尺寸三档：行内 16 / 按钮 20 / 独立 24。
- **禁 emoji 作功能图标**（跨平台渲染不可控）。
- 状态表达 = **图标 + 文字**，不能只靠颜色（WCAG 1.4.1 色觉无障碍）：success=CheckCircle2、warning=AlertTriangle、failed=XCircle。

## 9. 数据契约：TS 类型运行时不存在

`request<T>()` 是**无运行时校验的类型断言**——后端字段改名，前端静默拿 `undefined`。
**修复模式**：
1. `api/client.ts` 每个端点声明 `REQUIRED_FIELDS`，缺失即抛可诊断错误（好过白屏/空值）。
2. 可能缺失的字段一律 `orDash()` → `—`，**不得直接渲染**（React 把 undefined 渲染为空串，用户分不清"值为 0"与"字段缺失"）。
3. 测试 mock 必须取自真实后端形状的 fixtures——**自编 mock 正是 P0 逃逸的原因**：测试全绿但线上字段对不上。

## 10. 页面可达性 = 存在性

"后端有能力、用户不可达"是隐蔽缺陷：端点一直可用、README 一直宣称支持，但前端**没有任何页面消费**（合约页/跨链页曾缺失数月）。
**修复**：加**路由可达性测试**——每条路由必须至少有一个 `<Link to>` / `navigate()` 指向它；只有手敲 URL 能访问的页面 = 不存在。

## 11. 动效与强制降级

- `prefers-reduced-motion` 下关闭 pulse/spin 等持续动效。
- 过渡时长走令牌（150/200ms），别散写 `transition: all .3s`。

## 12. 对比度回归必须机器化

色值改动后"肉眼觉得还行"是不可接受的验收方式。
**做法**：验证脚本直接解析 **tokens.css 的实际值**（而不是断言里硬编码期望值），按真实用法逐组合计算，接进 `npm run check` 与 CI——色值一旦破线，构建直接红。覆盖：文本×底色、实底按钮、Badge 浅底、半透明 banner 合成底、可交互边界。

## 13. 深色系层级靠亮度与边框，不靠重阴影

暗色主题里阴影几乎不可见。用 surface 阶梯（bg → surface → surface-2）+ 细边框表达层级；
浅色主题再按需给 raised 阴影。z-index 也令牌化（sticky/dropdown/modal/toast）。

## 14. 写进契约的"品味规则"也是规则

如"禁紫粉渐变、禁装饰性毛玻璃、圆角上限 16px、禁散用 `indigo-*`/`gray-*` 工具类"——
这些看似主观的约束，一旦写进 DESIGN.md 的 Don'ts，就能在整个团队与所有 AI agent 间保持一致。
