# GenomeLens 课堂汇报 PPT 大纲

> 汇报时长：10 分钟  
> 总页数：22 P（一 P 一页）  
> 约束来源：`docs/汇报/GenomeLens_课堂汇报技术报告.md` + `docs/开发手册/架构研究报告.md` + `docs/开发手册/新增/大纲.md`

---

## 时间分配速览

| 章节 | 页数 | 建议时长 |
|---|---|---|
| 一、开场与背景 | P1–P3 | 1 分钟 |
| 二、技术路线及分工 | P4–P5 | 1 分钟 |
| 三、开发实践过程 | P6–P11 | 2.5 分钟 |
| 四、MVP 核心功能与结果 | P12–P16 | 3 分钟（重点）|
| 五、架构与实现细节 | P17–P20 | 2 分钟 |
| 六、总结与展望 / 致谢 | P21–P22 | 0.5 分钟 |
| **合计** | **22 P** | **10 分钟** |

---

## 一、开场与背景

### P1 封面

**标题**：GenomeLens — 面向 Windows 的本地比较基因组学分析平台  
**副标题**：JCVI 共线性分析平台的 MVP 设计与实现

**页面信息**：
- 汇报人：杨宏达（组长）
- 团队成员：贺宇洲、魏士林、饶国靖
- GitHub：`https://github.com/nhAirsy/GenomeLens`
- 日期：2026.6.26

**配图**：【图：项目 Logo 或一张典型 synteny 结果图作为底图】

---

### P2 研究背景

**标题**：为什么要做 GenomeLens？

**要点**：
- 比较基因组学中，共线性分析是揭示染色体保守性、识别直系同源基因的核心方法。
- JCVI 库功能强大，但面向类 Unix 环境，Windows 用户门槛高。
- 痛点：环境配置复杂、路径/命令不兼容、结果整理困难、缺乏本地一站式工具。

**配图**：【图：JCVI 官方示例图 + Windows 下环境配置/报错流程对比示意】

---

### P3 项目目标（MVP）

**标题**：MVP 目标：让 Windows 用户也能一键跑通共线性分析

**要点**：
- **本地**：无需上传数据，保护隐私。
- **轻量**：PyInstaller 单文件包 + 按需下载工具链。
- **快捷**：一条命令完成从输入发现、预处理、比对到出图。
- **双模式交付**：一站式工作流 + 可编排子模块。
- **可扩展**：统一协议，为未来多引擎、AI Agent 预留结构。

**配图**：【图：左侧“一站式”一次性跑完全链路，右侧“子模块”像积木一样组合】

---

## 二、技术路线及分工

### P4 技术路线

**标题**：技术路线：从 conda 试错到可插拔架构

**要点**：
1. 初期：直接基于 conda JCVI 在 Windows 上跑通最小样例。
2. 转型：将 JCVI 随包源码内置（vendored），打 Windows 兼容补丁。
3. 分离：把 JCVI 引擎独立为 `engines/jcvi/`，与平台核心解耦。
4. 优化：对 `synteny` 一站式工作流进行流程与算法层优化。
5. 外延：开发 HAIant 插件与 Tauri GUI（JCVI meow）。

**配图**：【图：一条从左到右的五阶段技术路线箭头图】

---

### P5 分工

**标题**：团队分工

**要点**：

| 成员 | 主要职责 |
|---|---|
| 杨宏达 | 组长，项目决策、系统架构、全栈开发 |
| 贺宇洲 | HAIant 智然体插件开发、数据准备、基因注释 |
| 魏士林 | 测试开发、同类平台分析、CI 维护 |
| 饶国靖 | 子模块开发、报告撰写、文档整理 |

**配图**：【图：四格分工图，或团队照片】

---

## 三、开发实践过程

### P6 初期探索：conda JCVI 在 Windows 上的尝试

**标题**：第一阶段：验证 JCVI 能在 Windows 上跑起来

**要点**：
- 尝试用 conda 安装 JCVI，配置 BLAST+、Python 环境。
- 跑通最小 BED+CDS 样例，理解 anchors / simple / blocks / layout 等中间文件。
- **结论**：JCVI 能力可行，但 CLI、Windows 兼容、工具链、结果整理耦合在一起，难以扩展。

**配图**：【图：早期 conda 环境截图 + 第一次成功出图的结果】

---

### P7 架构转型：vendored JCVI 与 Windows 兼容补丁

**标题**：第二阶段：把 JCVI 内置进来，掌握主动权

**要点**：
- 将 JCVI 1.6.6 作为 vendored 代码放入 `engines/jcvi/src/jcvi/`。
- 针对 Windows 打补丁：
  - `SIGPIPE` 仅在 Unix 生效；
  - `which()` 自动补全 `.exe`；
  - 避免硬编码 `/bin/bash`；
  - 统一使用 `pathlib` 处理路径。
- 形成可在 Windows 上独立运行的 `jcvi-genomelens` 引擎。

**配图**：【图：vendored JCVI 目录结构 + 补丁前后对比示意】

---

### P8 再次迭代：引擎与平台核心分离

**标题**：第三阶段：可插拔的引擎架构

**要点**：
- 将 `jcvi-genomelens` 引擎与 GenomeLens 平台核心拆分为两个独立包。
- 平台通过 `jcvi_engine_manifest.json` 调用引擎。
- 引擎只暴露 `probe` 和 `run` 两个入口。
- 未来可在 `engines/` 下并列接入 `mcscanx`、`syri`、`pangenome` 等新引擎。

**配图**：【图：平台与引擎通过 JSON 文件协议交互的示意图】

---

### P9 迭代优化（上）：synteny 一站式工作流优化

**标题**：第四阶段（上）：synteny 一站式工作流深度优化

**要点**：
- 将旧 `analyze mcscan` 收束为单一 `analyze workflow synteny`。
- 根据物种数自动路由：
  - 2 物种 → pairwise；
  - 3+ 物种 → all-vs-all pairwise + global karyotype + multi local synteny；
  - 带 `target_gene_ids` → reference-vs-targets 局部共线性。
- 计算与渲染解耦：先跑 pairwise，再注入产物进行渲染。

**配图**：【图：synteny 自动路由决策树】

---

### P10 迭代优化（下）：算法与工程优化

**标题**：第四阶段（下）：从算法到工程的细节打磨

**要点**：
- **窗口并集优化**：多目标局部共线性由包络合并改为窗口并集，block 行数从 965 降至 78。
- **进度条修复**：FINALIZING 态不再回退。
- **子模块重整**：`mcscan_pairwise` + `catalog_ortholog` 合并为 `jcvi.pairwise`；渲染模块缺产物时报错，不再静默重算。
- **Cython 加速**：`cblast`、`chic` 纳入打包，缺失时自动回退到纯 Python。

**配图**：【图：窗口并集优化前后对比图 + 子模块分层图】

---

### P11 HAIant 插件侧 / 独立 GUI 开发探索

**标题**：第五阶段：向外延伸——插件与 GUI

**要点**：
- **HAIant 插件**：独立轻量插件，通过标准 JSON 请求调用平台，不重复打包引擎。
- **JCVI meow GUI**：基于 Tauri v2 + React 18 的桌面外壳，定位为“平台调用器”。
- 两者都复用同一套 `WorkflowRequest` / `SubmoduleRequest` 协议。

**配图**：【图：左侧插件流程图，右侧 GUI 界面截图】

---

## 四、MVP 版本核心功能与结果

### P12 核心功能①：一站式 synteny 工作流（概念）

**标题**：核心功能 1：一站式 synteny 共线性分析

**要点**：
- 面向“我把物种目录扔进去，直接拿到结果”的场景。
- 一个命令跑完全链路：

```powershell
GenomeLens.exe analyze workflow synteny input output --force
```

- 自动识别物种数、自动选择执行路径、自动预处理 GFF+FASTA。

**配图**：【图：命令行截图 + 输入目录结构示意】

---

### P13 核心功能②：一站式 synteny 工作流（结果）

**标题**：synteny 工作流输出什么？

**要点**：
- 输出目录结构：
  - `run.log`：结构化日志；
  - `run_summary.json` / `engine_run_summary.json`：运行摘要；
  - `artifacts/`：图件与中间产物。
- 典型输出：
  - dotplot（点图）
  - synteny figure（共线性对齐图）
  - karyotype（核型图）
  - local synteny（局部共线性图）
  - 多物种 global karyotype / multi local synteny

**配图**：【图：输出目录截图 + 2~3 张典型结果图拼接】

---

### P14 核心功能③：可编排子模块（9 个子模块）

**标题**：核心功能 2：可编排子模块，按需调用

**要点**：

| 类型 | 数量 | 示例 |
|---|---|---|
| Lightweight | 7 | `jcvi.pairwise`、`jcvi.graphics_dotplot`、`jcvi.local_synteny`、`jcvi.graphics_histogram` 等 |
| Aggregate | 2 | `jcvi.graphics_karyotype_global`、`jcvi.local_synteny_multi` |

- 每个子模块声明输入/输出端口和参数。
- 适合“我已经有中间产物，只想画某张图”的场景。

```powershell
GenomeLens.exe analyze submodule jcvi.graphics_dotplot `
  --input-ports '{"species_pair":"input","anchors":"input/query__subject.anchors"}' `
  --output-dir output --force
```

**配图**：【图：9 个子模块的能力矩阵图或端口示意图】

---

### P15 核心功能④：HAIant 插件

**标题**：HAIant 智然体插件：让 GenomeLens 成为可插拔能力

**要点**：
- 插件不重复打包平台，只携带入口与配置。
- 通过 `GenomeLens_Path` 或 `GENOMELENS_EXE` 定位外部 GenomeLens。
- 生成 `WorkflowRequest` / `SubmoduleRequest`，调用 `analyze run`。
- 产物：
  - `app/onestop/gljcvi-synteny.zip`
  - `app/submodules/lightweight/gljcvi-*.zip`
  - `app/submodules/aggregate/gljcvi-*.zip`

**配图**：【图：插件运行流程图 + 插件产物目录截图】

---

### P16 核心功能⑤：JCVI meow GUI 探索版

**标题**：JCVI meow：Tauri + React 桌面 GUI 先行版

**要点**：
- 定位：平台外壳，不承载业务规则。
- 已实现：
  - 多任务工作台；
  - 实时日志流；
  - 运行状态机：PENDING → RUNNING → FINALIZING → COMPLETED/FAILED；
  - 结果摘要与产物列表；
  - 请求 JSON 导入/导出。
- 技术栈：Tauri v2 + React 18 + Vite + Tailwind CSS + Zustand。

**配图**：【图：JCVI meow 界面截图 2~3 张】

---

## 五、架构与实现细节

### P17 总体架构

**标题**：系统总体架构

**要点**：

```text
┌─────────────────────────────────────────┐
│  CLI │ Tauri GUI │ HAIant Plugin │ Agent │
├─────────────────────────────────────────┤
│      Platform Core（platform/）          │
│  WorkflowRequest/SubmoduleRequest →     │
│  WorkflowPlanner → PlanOptimizer →      │
│  PlanExecutor → RunSummary              │
├─────────────────────────────────────────┤
│      Engine Layer（engines/jcvi/）       │
│  probe / run --manifest                 │
├─────────────────────────────────────────┤
│  BLAST+ │ LAST │ Diamond │ ImageMagick  │
└─────────────────────────────────────────┘
```

- 跨层协议：`jcvi_engine_manifest.json` → `engine_run_summary.json` → `run_summary.json`

**配图**：【图：架构研究报告中的全局架构 Mermaid 图】

---

### P18 Platform 核心子系统

**标题**：平台核心：从用户意图到执行计划

**要点**：
- **CLI 入口**：`cli/main.py` 命令树，支持 `analyze workflow`、`analyze submodule`、`workflow list/describe/validate`。
- **请求模型**：`WorkflowRequest` / `SubmoduleRequest`（V3 协议）。
- **规划与执行**：
  - `WorkflowPlanner`：把 synteny 展开为 pairwise / all-vs-all / reference-vs-targets；
  - `PlanOptimizer`：去重预处理、共享 runtime、产物复用；
  - `PlanExecutor`：执行 DAG、归档产物、写出 RunSummary。
- **引擎适配**：`engines/jcvi/manifest_builder.py` 生成 engine manifest。

**配图**：【图：请求流转图：Request → ExecutionPlan → Manifest → Summary】

---

### P19 JCVI 引擎子系统

**标题**：JCVI 引擎：只暴露 probe 和 run

**要点**：
- 独立 Python 包 `jcvi-genomelens`。
- `probe --json`：输出能力声明。
- `run --manifest --outdir`：加载 manifest、dispatch workflow、写出摘要。
- 内部结构：
  - `manifest/`：manifest 解析；
  - `runtime/`：命令执行、日志、摘要；
  - `workflows/`：pairwise / graphics / local_synteny / aggregate；
  - `graphics/`：扩展图形渲染；
  - `src/jcvi/`：vendored JCVI 1.6.6。

**配图**：【图：引擎内部 workflow 分发图】

---

### P20 HAIant 插件 与 JCVI meow GUI

**标题**：插件与 GUI：统一协议的外壳

**要点**：
- **HAIant 插件**：参数翻译 → 生成 `genomelens_request.json` → 子进程调用 `GenomeLens-runtime.exe analyze run`。
- **JCVI meow GUI**：Tauri 后端通过子进程调用 `genomelens.exe`，通过事件向前端推送日志和状态。
- 共同点：都只提交标准请求，不直接拼 engine manifest。

**配图**：【图：插件/GUI 与平台调用关系序列图】

---

## 六、总结与展望

### P21 MVP 版本的不足与展望

**标题**：MVP 的不足与未来方向

**要点**：

**当前不足**：
- 尚未完全吃透 JCVI 所有能力；
- 未接入其他分析引擎；
- HAIant 插件与 GUI 支持尚未完全成熟；
- 算法工程、性能优化、可视化优化仍有空间。

**未来展望**：
- **短期**：补齐 JCVI 图形与 QC，打磨协议。
- **中期**：引入 Ks 分析、QUOTA-ALIGN、SynFind、系统发育树。
- **长期**：多引擎接入、机器学习评分、AI Agent 工作流、可追溯 Artifact 体系。

**配图**：【图：路线图时间轴】

---

### P22 致谢

**标题**：致谢

**要点**：
- 感谢指导老师、实验室、同学的支持。
- 感谢 JCVI、Tauri、React、Python 等开源社区。
- 项目仍在持续开发中，欢迎交流与合作。
- GitHub：`https://github.com/nhAirsy/GenomeLens`

**配图**：【图：GitHub 仓库二维码 + 谢谢页面底图】

---

## 附录：可直接复用的图片素材

以下图片可直接从我写的《架构研究报告》中截取或重新绘制：

1. **全局架构 Mermaid 图** → P17
2. **请求流转图** → P18
3. **引擎内部 workflow 分发图** → P19
4. **CLI/GUI/Plugin 调用平台序列图** → P20
5. **9 个子模块能力矩阵** → P14
6. **目录树状图** → 可作为技术细节备用页
