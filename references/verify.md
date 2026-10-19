# 验收清单与 CI 接线（verify）

## 一、验收四关

### 关 1：对比度（机器化，必须过）

```bash
python3 scripts/wcag.py --tokens tokens.css          # 或 design-tokens.json
python3 scripts/wcag.py --tokens tokens.css --strict  # 半透明合成底也逐对核算
```

自动配对约定（覆盖组件真实用法）：

| 类别 | 组合 | 阈值 |
|---|---|---|
| 正文/次级/辅助文本 | `fg / fg-2 / muted / accent / success / warn / danger` × `bg / surface / surface-2` | 4.5:1 |
| 实底按钮 | `accent-on` on `accent-solid(-hover/-active)`；`danger-on` on `danger-solid` | 4.5:1 |
| Badge 浅底 | `{tone}` on `{tone}-soft` | 4.5:1 |
| 半透明 banner | `bg-{tone}/NN` 叠加 `bg` 后的合成底（strict 模式） | 4.5:1 |
| 可交互边界 | `border-strong` on `bg / surface` | 3:1 |

### 关 2：令牌完整性（人工+脚本抽查）

- [ ] 每个颜色都有 `--x`（hex）与 `--x-rgb`（通道）**成对**出现，数量一致
- [ ] 品牌色拆了 `accent`（文字）与 `accent-solid`（实底）+ hover/active/on
- [ ] 语义浅底是独立令牌（`*-soft`），全站 grep 无 `bg-{语义色}/\d+` 稀释用法
- [ ] 可交互边界全部用 `border-strong`，`border` 只出现在装饰性分隔
- [ ] 字重仅 400/500/600/700；字号/圆角/间距全部来自令牌
- [ ] tokens.css / design-tokens.json / tailwind 映射三处一致（scaffold 产物天然一致）

### 关 3：交互与无障碍（人工过一遍）

- [ ] `focus-visible` 焦点环清晰可见（键盘 Tab 走查）
- [ ] 弹窗：ESC 可关、焦点圈定在内、关闭归还焦点
- [ ] 触摸目标 ≥44px（紧凑档 ≥24px）；图标按钮有 `aria-label`
- [ ] 状态不只靠颜色：图标+文字（Badge/告警/表格状态列）
- [ ] `prefers-reduced-motion` 下持续动效停用
- [ ] 可能缺失的字段渲染为 `—`（不是 undefined/空白）
- [ ] 每条路由有导航入口（可达性测试在跑）

### 关 4：文档一致性

- [ ] DESIGN.md 11 节齐全（允许裁剪但需注明）
- [ ] 值与 tokens 源文件一致；有修订注记
- [ ] Known Gaps 诚实：未提取到的、未实测的，都写明
- [ ] （可选）`npx @google/design.md lint DESIGN.md` 无告警

## 二、CI 接线模板

### npm scripts（前端项目）

```json
{
  "scripts": {
    "verify:contrast": "python3 ../scripts/wcag.py --tokens src/styles/tokens.css --strict",
    "verify:tokens": "node scripts/check-token-pairs.mjs",
    "check": "npm run format:check && npm run lint && npm run test && npm run build && npm run verify:contrast"
  }
}
```

> 若项目里没有 python，可把 `wcag.py` 的算法移植成 60 行 node 脚本（参考 NexusChain Explorer 的 `verify-contrast.mjs` 模式：**解析 tokens.css 实际值**，不硬编码期望值）。

### GitHub Actions 片段

```yaml
  ui-design-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - name: 设计令牌对比度门禁
        run: python3 <skill>/scripts/wcag.py --tokens frontend/src/styles/tokens.css --strict
      - name: 令牌配对完整性
        run: |
          grep -c -- '--[a-z0-9-]*-rgb:' frontend/src/styles/tokens.css
          # 期望值与颜色数一致（在脚本里断言更稳）
```

### 设计契约 lint（可选）

```yaml
      - name: DESIGN.md lint（可选，需 node）
        run: npx @google/design.md lint DESIGN.md
```

## 三、门禁哲学（重要）

1. **校验真实值，不校验期望值**：脚本必须解析 tokens 源文件的实际色值——色值一改就能暴露；硬编码期望值的断言会在改色时忘记更新，形同虚设。
2. **失败必须阻断**：exit code 接入 `npm run check` 与 CI，不达标直接红。
3. **阈值不谈判**：4.5:1 / 3:1 是 WCAG 2.1 AA 的底线；"差一点点"就是不过。
4. **改动即重跑**：改任何色值/新增任何组合都要重跑，禁止「肉眼看过」。

## 四、验收输出物

| 产物 | 出处 | 消费者 |
|---|---|---|
| `tokens.css` | scaffold.py | 浏览器（原生 CSS 变量） |
| `design-tokens.json` | scaffold.py | 设计工具 / 下游脚本 |
| `tailwind.extend.js` | scaffold.py | 构建配置 |
| `preview.html` | scaffold.py | 人（视觉走查目录） |
| `contrast-report.txt` | wcag.py / scaffold.py | 审计留痕 / CI artifact |
| DESIGN.md | agent + 人 | 所有后续 UI 工作的契约 |
