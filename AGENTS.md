# AGENTS.md — Cromite 仓库协作入口

> 本文件是所有 agent 在本仓库工作的第一入口。开始任何任务前，请先阅读
> `agents/memory/agent-local-memory.md`（本地记忆），并遵守本文件的约定。

## 1. 仓库是什么

Cromite 是基于 Bromite 的 Chromium 隐私增强浏览器分支（uazo/cromite 的 fork，远端 MoSunDay/cromite）。
本仓库**不包含 Chromium 源码**，只包含：

- 针对 Chromium 的补丁集（约 327 个 patch，`build/patches/`）
- GN 构建参数与补丁清单（`build/*.gn_args`、`build/cromite_patches_list.txt`）
- 构建/导出/应用补丁的脚本（`tools/`，bash + TypeScript Gerrit 同步）
- 用户文档（`docs/`）与 CI 工作流（`.github/workflows/`）

当前补丁集适配的 Chromium 版本：**153.0.8010.37**（2026-09-14 批次合入）。

## 2. 目录速查

| 路径 | 说明 |
|------|------|
| `build/patches/` | 全部 Chromium 补丁（GPL-2.0/GPL-3.0，作者 csagan5/uazo 等） |
| `build/cromite_patches_list.txt` | 补丁应用顺序清单 |
| `build/cromite.gn_args` / `chromium.gn_args` | GN 构建参数 |
| `build/userscripts/` | 用户脚本与附加 patch（后台播放视频等） |
| `build/components/` | 字体等组件资源 |
| `tools/*.sh` | 应用/导出补丁脚本（`apply-all-patch.sh`、`export-single-patch.sh` 等） |
| `tools/gerrit/` | Gerrit ↔ GitHub 同步（TypeScript：`sync_gerrit.ts`、`patch_upload.ts`、`api/`） |
| `tools/filters/`、`tools/cves/` | 过滤列表与 CVE 记录 |
| `docs/` | `FEATURES.md`、`PATCHES.md`、`HOW_TO_BUILD.md`、`PRIVACY_POLICY.md` 等 |
| `.github/workflows/` | CI：`build_cromite.yaml`、`release.yaml`、`gerrit-sync.yaml`、`update-patches-doc.yaml` 等 |
| `.chglog/` | git-chglog 配置 |

## 3. 本地记忆系统（强制）

每次会话必须：

1. **开工前**读取 `agents/memory/agent-local-memory.md`，了解背景、仓库地图、待办。
2. **任务完成/阻塞后**立即更新：
   - `features/dev-memory-timeline.md`：按固定格式追加时间线条目；
   - `agents/memory/agent-local-memory.md`：必要时更新 Recent Changes / Pending Work；
   - 用户要求汇总时，按规则生成 `features/dev-memory-newsletter.md`。
3. 各记忆文件的规则（.mdc.rule）见对应目录，规则头部不可修改。

## 4. 工程约束（必须遵守）

- **行数限制**：新增文件 ≤400 行；迭代中的文件 ≤800 行；超限必须按职责拆分子模块。
- **纯函数式**：新增代码禁止使用 class；用纯函数、组合与高阶函数；优先不可变数据。
- **安全**：代码与文档中不得包含任何 API Key/Token/密码/连接串等敏感信息。
- **提交信息约定**：工具类改动以 `[TOOLS]` 开头；CI 自动文档以 `[AUTO][DOC]` 开头；
  补丁类改动直接使用补丁英文描述。
- **文档同步**：修改 `build/patches/` 后，`docs/PATCHES.md` 由 CI（update-patches-doc）自动再生，勿手改格式。

## 5. 常见任务入口

- 适配新 Chromium 版本：参照 `docs/HOW_TO_BUILD.md` + `tools/apply-all-patch.sh`。
- 修改某个补丁：编辑 `build/patches/<Name>.patch`，保持 `cromite_patches_list.txt` 顺序一致。
- Gerrit 同步问题：看 `tools/gerrit/sync_gerrit.ts` 与 `.github/workflows/gerrit-sync.yaml`。
