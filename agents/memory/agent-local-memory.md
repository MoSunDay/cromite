# 本地记忆 — Cromite 仓库

> 规则见 `agents/memory/agent-local-memory.mdc.rule`（头部不可修改）。
> 每次会话开工前必读本文件；仓库状态或工作上下文变化后立即更新。

## 背景 & 目标 (Background & Goals)

- Cromite 是基于 Bromite 的 Chromium 隐私增强浏览器（uazo/cromite 的 fork，远端 `MoSunDay/cromite`，分支 `master`）。
- 本仓库**不含 Chromium 源码**，维护的是：补丁集（`build/patches/`，327 个 patch）、
  GN 构建参数、补丁应用/导出脚本（`tools/`）、用户文档（`docs/`）与 CI（`.github/workflows/`）。
- 当前补丁集适配 Chromium **153.0.8010.37**（2026-09-14 批次合入）。
- 目标：持续跟随 Chromium 上游版本 rebase 补丁、通过 Gerrit 同步（`tools/gerrit/`）保持
  patch 数据可索引、CI 自动产出 Android/Windows/Linux 构建与 `docs/PATCHES.md`。

## 仓库地图 (Repository Map)

- `build/patches/` — 全部 Chromium 补丁（GPL-2.0/GPL-3.0，作者 csagan5/uazo 等）
- `build/cromite_patches_list.txt` — 补丁应用顺序清单
- `build/cromite.gn_args`、`build/chromium.gn_args` — GN 构建参数
- `build/userscripts/` — 用户脚本与附加 patch（如 Allow-playing-videos-in-background）
- `build/components/` — 字体等组件资源
- `tools/*.sh` — 补丁流水线（`apply-all-patch.sh`、`export-single-patch.sh`、`extract-patch-data.sh` 等）
- `tools/gerrit/` — Gerrit ↔ GitHub 同步（TS：`sync_gerrit.ts`、`patch_upload.ts`、`rebuild_change_versions.ts`、`diff_utils.ts`、`api/`）
- `tools/filters/`、`tools/cves/` — 过滤列表与 CVE 记录
- `docs/` — `FEATURES.md`、`PATCHES.md`、`HOW_TO_BUILD.md`、`PRIVACY_POLICY.md`、`FAQ.md` 等
- `.github/workflows/` — CI：`build_cromite.yaml`、`release.yaml`、`gerrit-sync.yaml`、
  `update-patches-doc.yaml`、`check-git-apply.yaml`、`check_nist.yaml` 等
- `.chglog/` — git-chglog 配置（`CHANGELOG.tpl.md`、`config.yml`）

## 近期变化 (Recent Changes)

- 2026-10-18：**Cromite Linux 构建成功并部署 192.168.31.196:/opt/cromite**（992M，Cromite 153.0.8010.37，BUILD_COMMIT=583b613b=origin/master；headless + JS 冒烟通过；旧版备份 /opt/cromite.bak-20261018-0026）。构建链：privoxy HTTP→SOCKS 桥(:8118) → clang24/PGO profdata/V8 builtins-pgo 全量补齐 → gn gen 32061 targets → siso 31877 steps 8h45m → systemd PathExists 自动触发 03-deploy.sh。
- 2026-10-17：M153 适配修复：移除失效补丁 Disable-periodic-background-sync（kPeriodicBackgroundSync 上游已删，65c46a48/583b613b，清单 328→327）；容器补丁栈 327 补丁 git am 全成功；vpython 9 spec 环境建立。
- 2026-10-17：**push 已完成**（SSH 走 SOCKS）：9866a195..7c78b47d → 后续 65c46a48/99d6e569/583b613b 均已合流推送；fork 无 Actions（CI 不触发），全量验证以本地容器构建为准（已通过）。
  `d975426d` DoH 未指定时默认 OpenDNS；`9e5b4a0d` 底部导航栏崩溃修复（#3046）并默认禁用上游底栏（#3044）；
  `f7eccec0` 退出清除数据 UI 计数修复；`af2d3b9a` 恢复 Simplified NTP 丢失 hunk；CI 自动再生 PATCHES.md（#3052）。

## 待办事项 (Pending Work)

- 部署自动化收尾：cromite-deploy.path 已 disable（PathExists 持久 flag 会重复触发）；下次部署前先 `rm out-lin64/.build-done` 再临时 `systemctl start cromite-deploy.path`，或手动跑 03-deploy.sh。
- `use_v8_context_snapshot=true` 的 #317 崩溃场景需真机回归；若复现直接改回 false（cromite.gn_args 注释已留指引）。
- CPU 优化 #5（Android 后台 tab 冻结）：被"无 Chromium 源码树/无外网"阻塞，需在可拉取 153 源码的环境按设计实施（battery-saver 门控、音频/下载豁免、core+exemption 两文件 ≤400 行）；#7 用 `tools/perf/` 真机采基线后再评估 #7/#8 收益。
- 观察下一轮 Gerrit 同步周期：验证"缺失补丁重下载"逻辑是否消除上传失败（关联 `2384a226` 日志）。
- 跟踪 Chromium 153 后续小版本 rebase 与用户反馈（底栏 / NTP 相关 issue）。

## Agent 备注 (Agent Notes)

- 补丁流水线：改 `build/patches/` 后保持 `build/cromite_patches_list.txt` 顺序一致；`docs/PATCHES.md` 由 CI 自动再生，勿手改。
- 提交信息约定：`[TOOLS]` 工具类 / `[AUTO][DOC]` CI 文档 / 补丁改动直接用英文补丁描述。
- 工程约束：新增文件 ≤400 行、迭代文件 ≤800 行；新增代码纯函数式（禁 class）；严禁敏感信息入码。
- 时间线与简报：任务完成/阻塞后在 `features/dev-memory-timeline.md` 追加条目；用户要汇总时按 `features/dev-memory-newsletter.mdc.rule` 生成简报。
