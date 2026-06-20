# 未来 JCVI 能力依赖安装记录

> 记录为集成 JCVI 扩展功能而尝试安装额外依赖的结果，以及 Windows 平台下的阻塞项。

## 环境

- 环境名：`genomelens`
- Python：`3.12.13`
- 操作系统：Windows 11 Home China (win-64)

## 已成功安装

| 包 | 版本 | 用途 | 验证 |
|---|---|---|---|
| `deap` | 1.4.4 | `jcvi.assembly.hic`、`jcvi.algorithms.ec` | `import deap` OK |
| `pyliftover` | 0.4.1 | `jcvi.formats.vcf`、`jcvi.variation.impute` | `import pyliftover` OK |
| `boto3` | 1.43.34 | `jcvi.variation.delly`、`jcvi.utils.aws` | `import boto3` OK |
| `pyefd` | 1.7.0 | `jcvi.graphics.grabseeds` | `import pyefd` OK |

安装命令：

```bash
pip install deap pyliftover boto3 pyefd
```

单元测试回归结果：

```text
110 passed, 1 warning in 2.22s
```

## 安装失败/不可用

| 包 | 预期用途 | 失败原因 | 后续方案 |
|---|---|---|---|
| `pysam` | `jcvi.variation.phase`、`jcvi.formats.sam`、`CrossMap` | Windows 无官方 wheel/conda 包；源码构建需要 Unix `make` 与 HTSlib | 使用 WSL、Docker，或将相关功能标记为 Linux-only |
| `CrossMap`（即 `cmmodule`） | `jcvi.assembly.allmaps` | 依赖 `pysam`，随 CrossMap 安装时触发 pysam 构建失败 | 同上；或尝试单独源码编译 `cmmodule`（无独立 PyPI 包） |
| `pybedtools` | `jcvi.variation.cnv` | 构建时同样触发 pysam/Unix 工具链缺失 | 同 pysam；或改写在 Windows 下使用 `pyranges` 替代 |
| `bx-python` | `jcvi.formats.maf` | 源码编译到 `bgzf` 扩展时缺少 `zlib.h`（即使 conda `zlib` 已安装） | Linux/macOS 可直接 `pip install bx-python`；Windows 需补全编译头文件路径或改用 Linux 环境 |
| `pyfasta` | `jcvi.variation.str` | 0.5.2 为 Python 2 包，`import pyfasta` 在 Python 3.12 下报 `ModuleNotFoundError: No module named 'fasta'` | 使用 `pyfastx` 或 `pyfaidx` 替换，并给 JCVI 打补丁 |
| `Bio.Align.Applications` | `jcvi.compara.ks` | Biopython >=1.82 已移除该模块 | 降级 Biopython 或重写 `compara.ks` 的调用逻辑 |

## 配置文件更新

已更新以下文件，把可安装依赖写入可选依赖组，并把阻塞项以注释形式保留：

- `engines/jcvi/pyproject.toml`：新增 `[project.optional-dependencies]` 下的 `future` 组。
- `platform/environment.yml`：在 `pip:` 段新增 `deap`、`pyliftover`、`boto3`、`pyefd`，并注释说明阻塞项。

## 结论

- **短期可启用**：依赖 `deap`、`pyliftover`、`boto3`、`pyefd` 的功能（Hi-C、liftover、DELLY/SV、grabseeds）。
- **Windows 阻塞**：所有依赖 `pysam` 的模块（variation 大部分、ALLMAPS、CrossMap/cmmodule、pybedtools、bx-python 的 bgzf 部分）。
- **需要补丁**：`compara.ks`（Bio.Align.Applications 已移除）、`variation.str`（pyfasta Python 2 不兼容）。

建议策略：

1. 把 **Windows 可直接运行** 的能力先集成进 GenomeLens。
2. 对 **pysam 依赖链** 的功能，提供 WSL/Docker 执行后端，或标注为“Windows 暂不支持”。
3. 对 **pyfasta / Bio.Align.Applications** 这类 JCVI 内部兼容性问题，通过 fork 或 monkey-patch 解决，而非在环境中硬塞旧包。

---

*记录时间：2026-06-20*
