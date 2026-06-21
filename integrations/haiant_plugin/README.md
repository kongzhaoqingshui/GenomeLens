# GenomeLens HAIant plugin(智然体插件)

这一 integration layer(集成层) 会把 HAIant `params.json` 转换为 GenomeLens runtime command(运行时命令)。它不实现分析算法，也不直接调用 JCVI。

## 当前范围

当前插件参数面向 2 到 n 个物种的 GenomeLens 一站式 JCVI 出图流程：

- BED+CDS 输入。
- GFF+FASTA 输入。
- `species[]` 物种列表（至少两个物种）。
- 固定通过 `graphics_synteny` workflow(工作流) 输出 dotplot(点图) 与 synteny figure(共线性图)。
- `allow_simplified_fallback` 字段保留，但正式流程不启用简化算法。

完整目标中的插件表单美化、参数自动推荐、单独子任务入口、全局总图调参与机器学习评分尚未接入。

## 入口

```powershell
GenomeLens.exe
GenomeLens.exe params.json
```

带 `params.json` 运行时，插件会先写出稳定的 `genomelens_request.json`，再调用：

```powershell
GenomeLens-runtime.exe analyze run output/genomelens_request.json
```

打包插件期望运行时位于：

```text
runtime/GenomeLens/GenomeLens-runtime.exe
```
