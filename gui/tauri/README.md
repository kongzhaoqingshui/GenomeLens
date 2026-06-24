# GenomeLens GUI — JCVI meow

本目录是 GenomeLens 桌面 GUI 的 **先行版本**，代号 **JCVI meow**。GUI 只作为平台交互外壳，分析能力仍通过 `platform/` 暴露的 CLI / request / summary 协议完成。

## Root build helper

From the repository root, run the complete GUI verification flow with:

```powershell
.\scripts\build_gui.ps1
```

This installs dependencies, runs frontend lint/typecheck/tests/web build, and checks the Tauri Rust crate. To build the real desktop app and copy the runnable GUI entry into the root `app/JCVI-meow-gui/` folder:

```powershell
.\scripts\build_gui.ps1 -TauriBuild
```

The runnable app entry is `app/JCVI-meow-gui/JCVI-meow.exe`. Use `-DebugBundle` only for a debug-profile GUI build.

当前版本：`0.9.20-preview.1`（见 `package.json`、`src-tauri/Cargo.toml`、`src-tauri/tauri.conf.json`）。

## 环境要求

- Node.js >= 18
- pnpm（通过 `corepack enable` 启用）
- Rust / Cargo
- `genomelens` conda 环境，且 `platform/` 与 `engines/jcvi/` 已 editable install

Rust 工具链必须来自官方渠道：

- 推荐从 https://www.rust-lang.org/tools/install 安装 rustup。
- Windows 可用 `winget install --id Rustlang.Rustup -e`，安装前用 `winget show --id Rustlang.Rustup -e` 核验发布者、下载 URL 与 SHA256。
- 正式 rustup 下载域名应为 `static.rust-lang.org`，不要安装来源不明的同名包。

## 本地运行

```powershell
cd gui/tauri
corepack enable
pnpm install
pnpm tauri dev
```

开发服务器默认监听 `http://127.0.0.1:1420`，可在 `src-tauri/tauri.conf.json` 中修改 `devUrl`。

## 常用检查

```powershell
pnpm lint
pnpm typecheck
pnpm test
pnpm build:web
```

## Tauri 侧校验与构建

```powershell
cargo check --manifest-path src-tauri/Cargo.toml
pnpm tauri build
```

`tauri build` 需要在 Windows 环境中完成才能生成 `.msi` / `.exe` 安装包；若仅验证前端与 Rust 侧，可先执行 `pnpm build:web` 与 `cargo check`。

## 当前能力与迁移状态

- Tauri v2 + Vite + React 18 + TypeScript + Tailwind CSS 骨架。
- 最小权限 capability：core、fs、shell、dialog、notification、os。
- 分析向导首屏：支持选择输入目录、输出目录、参考物种与目标基因；当前源码仍有旧请求草案模型，下一阶段应迁移为 `WorkflowRequest v2`。
- 运行会话模型：展示任务运行状态与进度。
- Tauri command：已具备版本探测、模板/schema 读取、环境检查、运行、取消、summary/log/artifact 读取等基础能力。

## 已知限制

- 0.9.20 为先行预览版，主要完成桌面壳、向导首屏与请求草案模型；真实分析执行链路仍调用 `platform/` CLI。
- 平台当前协议已经升级为 `WorkflowRequest v2` 与 `RunSummary v3`，GUI 源码迁移计划见 `docs/开发手册/GUI先行开发/开发计划.md`。
- 安装包构建依赖 Windows + Rust，建议在具备完整工具链的机器或 CI 中执行 `pnpm tauri build`。
