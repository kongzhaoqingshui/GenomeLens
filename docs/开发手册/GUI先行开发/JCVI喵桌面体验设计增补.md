# JCVI meow桌面体验设计增补

> 本增补定义 GUI 从 GenomeLens 通用桌面壳转向专门面向 JCVI 的「JCVI meow」桌面应用体验。底层仍通过 GenomeLens/Tauri command 对接已有 JCVI/GenomeLens 能力，前端品牌、启动体验、首页能力入口和工作台排版按本文件调整。

---

## 1. 产品定位

- 产品名：JCVI meow
- 定位：面向 JCVI 工作流的桌面分析工作台，优先服务 MCSCAN / pairwise synteny / multi-species / local synteny 等已由 GenomeLens 接入的能力。
- 后端关系：用户感知层称为 JCVI meow；运行层继续复用 GenomeLens CLI、AnalysisRequest、run_summary 和 run.log 契约。
- 设计关键词：冰蓝、轻快、桌面工作台、启动不卡顿、有生命感但不幼稚。

---

## 2. 图标资产规则

### 2.1 总原则

后续 GUI 图标不再由 Codex/开发者临时自绘。图标来源按以下优先级执行：

1. JCVI meow品牌 logo：只使用用户亲自提供、用户确认的 AI 生成图，或用户明确指定的最终资产。开发者不得自行重画品牌 logo。
2. 功能、工具、设置、状态类图标：统一使用 Nieobie/Game-Icon-Pack 的 SVG/PNG 资产。
3. 若 Game Icon Pack 中没有合适图标，先向 GUI lead 提出缺口，由 GUI lead 决定替代图标或等待用户指定；不得自行画新图标补位。

Nieobie/Game-Icon-Pack 采用 CC0 1.0 Universal，可修改和商用。项目内保留来源说明即可，不需要运行时联网加载。

### 2.2 品牌 logo 方向

图标是一个小猫头拿着透镜，透镜中显示 `JCVI`。当前方向改为更接近 Codex 图标的实色填充图标，而不是线描插画。

需借鉴用户给出的参考图的「极简小猫头记忆点」，但必须有明显变化：

- 猫头不使用原参考的红色方形脸，改为冰蓝实色或轻微同色渐变填充。
- 脸型保留柔和圆角几何感，必须画出耳朵，整体不能像普通圆点或无耳朵头像。
- 表情只保留眼睛，不画嘴、鼻子、胡须等多余细节；眼睛使用黑色长条眼，不使用眼白+瞳孔结构。
- 透镜为主要识别物：圆形镜片、短柄，镜片内写 `JCVI`；透镜位置要像被猫持着，避免单独漂浮的透镜感。
- 可使用尾巴托住或持住透镜，强化「猫拿着透镜」的结合感。
- 左右耳朵的浅色耳蜗块要尽量镜像对称，不允许出现随意切割感。
- 色彩：主色 `--ice-500`，浅底 `--ice-50`，描边 `#0F172A` 或深色模式下 `#E0F2FE`。
- 图标需能在 16/32/64/128 px 下辨认；小尺寸下可隐藏 `JCVI` 文字，只保留镜片高光。
- 上述方向仅作为用户或图像生成工具制作品牌 logo 的提示约束；开发者不得再自行绘制或“修一版”品牌 logo。

### 2.3 交付形态

品牌 logo 由 GUI lead 接收用户确认后的最终图片或 SVG，再统一导出 `.ico` / `.png` / `tauri.conf.json` 图标资产。前端不再手写 `JcviMeowIcon` 的图形细节；如需组件，只封装最终资产的加载和尺寸适配。

---

## 3. 启动加载体验

### 3.1 目标

解决进入软件后等待后端能力探测时的卡顿感。启动后立即展示中心动画，后端 `get_version()`、模板/schema 预热、环境检查等可并行进行。启动层必须是独立全屏场景，不能透出后面的工作台、导航、卡片或状态面板。

### 3.2 动画分镜

总时长建议 1600-2200 ms，可循环进入提示态。

1. 猫头从窗口上方轻微弹性落下，停在中心。
2. 猫头抬起或推出透镜，透镜从小到大展开。
3. 透镜中以打字机效果打印 `JCVI`。
4. 猫头 + 透镜组成最终应用图标，背景只保留淡色渐变和极轻的圆环，不增加复杂装饰。
5. 若后端仍未 ready，图标保持轻微呼吸动画，并轮播提示。

启动层中的图标、产品名和主提示位置必须固定，不被错误日志、诊断信息或慢启动提示挤动。错误详情只能进入下方预留区域，必要时内部滚动。

### 3.3 加载提示文案

提示文案不写技术噪音，语气轻松但专业：

- 正在唤醒 JCVI 引擎...
- 正在检查 GenomeLens 后端连接...
- 正在读取 MCSCAN 模板...
- 正在准备任务工作台...
- 如果第一次启动稍慢，通常是在编译或预热本地工具链。

### 3.4 可访问性

- 尊重 `prefers-reduced-motion`：禁用落下/弹性动画，改为静态图标 + 淡入提示。
- 加载超过 10 秒时显示「查看诊断」入口，跳转设置/环境诊断页。
- 加载失败时保留品牌图标，显示可读错误和重试按钮。

---

## 4. 首页能力入口

### 4.1 布局目标

加载完成后，不进入传统 landing hero，也不直接展示工作台。先进入简洁的「中心能力环」初始界面：中心是 JCVI meow图标，周围扩散出能力入口。能力入口围绕中心圆形/椭圆环绕，但位置有轻微不规则感，避免机械仪表盘。

### 4.2 首批能力入口

先只集成 GenomeLens 已有 JCVI 能力：

- 双物种共线性 / Pairwise Synteny
- 多物种共线性 / Multi-species Synteny
- 局部共线性 / Local Synteny
- Dotplot / 点图
- Karyotype / 核型总图
- Ortholog Catalog / 正交基因目录
- 环境诊断 / Environment Check

点击任一分析能力入口，直接进入工作台中的任务创建/运行视图，并预设对应 workflow 或至少定位到现有 MCSCAN wizard。环境诊断入口进入 settings/env panel。

### 4.3 交互

- 能力入口是图标按钮或短标签按钮，而不是大段文字卡片。
- 能力解释不直接铺在界面上，只在 hover/focus tooltip 中出现。
- hover/focus 时入口向外轻移 2-4px，连线变亮，中心图标轻微看向该入口。
- 点击后中心向工作台过渡，能力环淡出，工作台主区域展开。
- 已接入能力用冰蓝高亮；暂未完全接入但可预留的能力降低透明度并显示「即将接入」。

### 4.4 图标来源

除 JCVI meow品牌 logo 外，其他能力、工具、设置类图标统一使用 Nieobie/Game-Icon-Pack 的 SVG 资产。不得自行绘制临时图标、手写新图标 SVG、或用文字圆点冒充图标。

---

## 5. 工作台排版

### 5.1 总体结构

参考 Codex 的工作感：中间是主工作区，左侧是任务/能力导航，右侧是上下文面板。JCVI meow中间不是对话，而是当前选中 JCVI 任务的工作台。

```text
┌─────────────────────────────────────────────────────────────┐
│ 顶栏：JCVI meow / 当前任务名 / 运行状态 / 设置                  │
├───────────────┬─────────────────────────────┬───────────────┤
│ 左侧能力栏     │ 中心任务工作台                │ 右侧上下文栏    │
│ - 能力入口     │ - 参数表单 / Run 面板          │ - 后端状态      │
│ - 最近运行     │ - 日志 / 结果摘要              │ - 文件路径      │
│ - 环境诊断     │ - 图件预览                     │ - summary 快照  │
└───────────────┴─────────────────────────────┴───────────────┘
```

### 5.2 中心工作台

- 默认显示选中的 JCVI 任务，例如 MCSCAN wizard。
- Run 面板与日志不再像附属卡片堆叠在侧边，而是成为当前任务的下半区或右下区。
- 运行完成后，中心区从「参数输入」自然切换到「结果预览」，保留返回参数编辑入口。

### 5.3 右侧上下文栏

右侧栏承载密度较高但辅助的信息：

- GenomeLens / JCVI engine ready 状态。
- 当前 request path、outdir、runId、logPath、summaryPath。
- 最近 5 条状态事件。
- 打开输出目录、读取日志、读取 summary 等工具按钮。

### 5.4 视觉原则

- 避免大面积营销 hero、漂浮大卡片和重复卡片嵌套。
- 保持工作台密度，像生产工具而不是宣传页。
- 图标和动效承担品牌感，表单与日志区域保持克制。
- 继续使用冰蓝 token，但减少单色大面积铺开，加入白/深灰/状态色形成层次。

---

## 6. 与 Phase 2 / Phase 3 的衔接

### Phase 2 继续推进

- 保持当前 `run_analysis`、`analysis:*` 事件、`read_summary`、`read_run_log` 契约不变。
- 本轮 UI 重排不能破坏已打通的 Run flow。
- smoke 验收仍是：选择输入 -> Run -> 状态/日志 -> summary 展示。

### Phase 3 前置

- 工作台结果区要为图件网格、文件树、图片放大预览预留位置。
- `RunSummaryViewModel.figureAssets` 作为第一版图件入口。
- 后续若新增 `list_artifacts` / `read_artifact`，只扩展右侧上下文栏和结果区，不重写启动/首页架构。

---

## 7. A/B/C 实施拆分

### B：前端体验主任务

分支：`gui/feature/phase2-jcvi-meow-shell`

- 品牌 logo 不再由前端手绘；只封装用户确认的最终 logo 资产。能力、工具、状态图标统一接入 Game Icon Pack。
- 实现启动加载层：中心猫头落下、透镜展开、`JCVI` 打印、提示轮播、reduced motion 降级。
- 重做 Home：加载完成后显示中心能力环，入口点击进入现有 `/analysis/new` 或 settings。
- 重排 AppShell/NewAnalysisPage，使其向「左能力栏 + 中心工作台 + 右上下文栏」过渡；第一版可先在 new-analysis 页面落地，不要求一次全站完成。
- 更新文案：用户可见品牌改为 `JCVI meow`，底层说明中可保留 `Powered by GenomeLens`。

### C：数据流与状态适配

分支：`gui/feature/phase2-jcvi-meow-state`

- 梳理 Home/启动层需要的 ready 状态：`get_version`、`get_template`、`get_analysis_schema` 的加载阶段和错误模型。
- 提供轻量 view model：能力入口列表、已接入/预留状态、workflow 预设字段。
- 保持 `outdir`、`analysis:*`、`read_summary` 契约不变。
- 若 B 需要入口点击预设 workflow，负责在 draft mapper 或页面边界提供稳定 helper。

### A：后端与验证支援

分支：`gui/feature/phase2-jcvi-meow-smoke`

- 不改平台核心；验证品牌/启动 UI 改造后 `pnpm tauri dev` 仍能找到 GenomeLens/JCVI CLI。
- 协助确认启动预热调用不会阻塞窗口首屏。
- 做真实 smoke：pairwise、多物种、本地共线性至少各一轮或复用 A 已验证的 demo request。
- 记录首屏加载、Run flow、summary 展示问题。

---

## 8. 验收标准

- 应用首屏 300 ms 内出现 JCVI meow启动层，不再白屏等待后端探测。
- 动画完成后，如果后端未 ready，提示继续轮播且界面不冻结。
- 加载完成后出现中心能力环，点击已接入能力能进入工作台。
- 工作台中心区域能继续完成现有 Phase 2 Run flow。
- 真实运行结束后能看到日志、状态、summary 和主要图件入口。
- `corepack pnpm test`、`corepack pnpm run lint`、`corepack pnpm typecheck`、`corepack pnpm build:web` 通过。
- Rust/Tauri 改动如有，则 `cargo check`、`cargo clippy -- -D warnings` 通过。
