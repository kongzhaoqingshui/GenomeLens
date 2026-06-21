# GenomeLens CLI 入口壳设计

> 本文档定义 GenomeLens 命令行入口的**环境变量壳**（entry shell），属于平台级通用设计，不局限于智然体（HAIant）插件。

## 背景

GenomeLens 主 CLI 的子命令（如 `analyze`、`check`、`workbench`）语义较为通用。如果直接把这些子命令暴露到系统 PATH 中执行，例如：

```text
analyze run request.json
```

可能会与其他同名应用冲突，导致调用了非 GenomeLens 的程序。

为了提供**命名空间隔离**和**统一的环境变量配置**，我们在原始主入口之外再套一层壳，使用户和所有集成方都通过 `genomelens` 前缀调用：

```text
genomelens analyze run request.json
genomelens check --json
genomelens workbench
```

## 设计原则

1. **原始主入口不变**：原始 CLI 可执行文件（如 `GenomeLens.exe` 或 `GenomeLens-runtime.exe`）继续负责所有子命令解析和业务逻辑。
2. **壳只负责透传与环境配置**：壳不解析 `analyze`、`check`、`workbench` 等任何子命令，也不携带业务逻辑。
3. **命名避免冲突**：壳的文件名必须与原始主入口可区分，尤其在 Windows 大小写不敏感文件系统上。
4. **异常收集**：壳把原始主进程的 stdout/stderr 直接透传；仅在其无法启动或返回非 0 时输出错误并返回退出码。

## 组件

```text
GenomeLens/
├── GenomeLens.exe              # 原始主入口（PyInstaller 产物）
├── genomelens.cmd              # 环境变量壳（Windows 批处理）
└── resources/
    └── toolchain/
        ├── blast/
        ├── jcvi-genomelens/
        └── imagemagick/
```

### 原始主入口

- 由 `platform/packaging/pyinstaller/genomelens.spec` 构建。
- 当前产物名为 `GenomeLens-runtime.exe`，打包目录为 `GenomeLens/`。
- 它解析所有子命令、执行分析、输出结果。

### 环境变量壳 `genomelens`

壳可以是 `genomelens.cmd`、`genomelens.exe` 或 `genomelens`（无扩展名脚本），只要与原始主入口文件名可区分即可。

推荐命名（取决于原始主入口文件名）：

| 原始主入口文件名 | 推荐壳文件名 | 原因 |
|---|---|---|
| `GenomeLens-runtime.exe` | `genomelens.exe` | 名称完全不同，无冲突 |
| `GenomeLens.exe` | `genomelens.cmd` | Windows 大小写不敏感，`GenomeLens.exe` 与 `genomelens.exe` 会冲突，故用 `.cmd` |

壳的行为：

1. 根据自身路径推断 `GENOMELENS_HOME`（即壳所在目录）。
2. 设置 `GENOMELENS_TOOLCHAIN_DIR=%GENOMELENS_HOME%\resources\toolchain`。
3. 在同目录下找到原始主入口可执行文件。
4. 把所有命令行参数原样透传给原始主入口。
5. 等待子进程结束，返回其退出码。
6. 如果原始主入口不存在，输出错误：
   ```text
   未找到 GenomeLens 主入口。请确认安装包完整。
   ```

## 伪代码

```batch
@echo off
setlocal
set "GENOMELENS_HOME=%~dp0"
set "GENOMELENS_TOOLCHAIN_DIR=%GENOMELENS_HOME%resources\toolchain"
"%GENOMELENS_HOME%GenomeLens-runtime.exe" %*
exit /b %errorlevel%
```

若用 Python/PyInstaller 实现：

```python
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    home = Path(sys.executable).resolve().parent
    os.environ["GENOMELENS_HOME"] = str(home)
    os.environ["GENOMELENS_TOOLCHAIN_DIR"] = str(home / "resources" / "toolchain")
    runtime = home / "GenomeLens-runtime.exe"
    if not runtime.is_file():
        print("未找到 GenomeLens 主入口。", file=sys.stderr)
        return 1
    return subprocess.run([str(runtime), *sys.argv[1:]]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
```

## 与智然体插件的关系

当前 HAIant 插件采用**完全独立的轻量插件**模型：

- 每个 JCVI 小功能一个独立包（`gljcvi-dotplot`、`gljcvi-synteny` 等）。
- 插件不携带 GenomeLens 平台或工具链，也不在运行时搜索重型中心。
- 用户需要在 `params.json` 中提供 `genomelens_exe`（外部 GenomeLens 可执行文件路径），或预先设置 `GENOMELENS_EXE` 环境变量。
- 插件直接调用外部 GenomeLens：

  ```text
  <genomelens_exe> analyze run output\genomelens_request.json
  ```

如果用户把 GenomeLens 安装目录下的 `genomelens.cmd` 或 `genomelens.exe` 作为 `genomelens_exe`，那么实际上间接使用了本节描述的入口壳；但插件本身并不依赖壳的存在，任何能解析 `analyze run <request.json>` 的 GenomeLens 可执行文件都可以。

## 构建要求

- 平台打包脚本（`scripts/build_split_packages.ps1`）应在生成 `GenomeLens-runtime.exe` 后，额外生成 `genomelens.cmd`（或 `genomelens.exe`）。
- 壳必须和原始主入口放在同一输出目录（`platform/dist/GenomeLens/`）。
- 壳文件应进入最终安装包/zip。

## 兼容性

- 旧入口（直接调用 `GenomeLens-runtime.exe`）继续可用。
- 新文档、脚本、插件优先推荐 `genomelens` 入口。
- 第三方集成可以选择继续使用原始入口，但需自行设置环境变量。

---

*本文件随平台打包方式演进可修订。*
