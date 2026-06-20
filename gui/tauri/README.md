# GenomeLens GUI 本地开发

本目录是 GenomeLens 桌面 GUI 的 Phase 0 Tauri 骨架。GUI 只作为平台交互外壳，分析能力仍通过 `platform/` 暴露的 CLI / request / summary 协议完成。

## 环境要求

- Node.js >= 18
- pnpm
- Rust / Cargo
- `genomelens` conda 环境，且 `platform/` 与 `engines/jcvi/` 已 editable install

Rust 工具链必须来自官方渠道：

- 推荐从 https://www.rust-lang.org/tools/install 安装 rustup。
- Windows 可用 `winget install --id Rustlang.Rustup -e`，安装前用 `winget show --id Rustlang.Rustup -e` 核验发布者、下载 URL 与 SHA256。
- 正式 rustup 下载域名应为 `static.rust-lang.org`，不要安装来源不明的同名包。

## 本地运行

```powershell
cd gui/tauri
pnpm install
pnpm tauri dev
```

## 调试构建

```powershell
cd gui/tauri
pnpm tauri build --debug
```

## 常用检查

```powershell
pnpm lint
pnpm typecheck
pnpm test
```

## Phase 0 能力

- Tauri v2 + Vite + React 18 + TypeScript + Tailwind CSS 骨架
- 最小权限 capability：core、fs、shell、dialog、notification、os
- `get_version()` Tauri command，返回 platform 与 engine 版本探测结果
- 前端首页调用 `get_version()` 并展示版本状态
