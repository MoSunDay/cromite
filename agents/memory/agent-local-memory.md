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

- 2026-10-17（第二批）：CPU 优化 #4/#6/#7 交付并通过本地全量核验——`1ba6f466` update-scheduler 4 job 置 null、`b3ca8fc3` 新补丁 Disable-periodic-background-sync（清单 L63）、`88b39e87` use_v8_context_snapshot=true、`9866a195` tools/perf 4 文件；self-test 20/20、bash -n、git apply --stat、行数/纯函数式/无敏感信息检查全绿；push 因 NO_NET 超时（exit 124），领先 6 commit 待推送。
- 2026-10-17：CPU 优化决策「默认安全」：#1 BRP/#2 partition cookie/#3 GWP-ASan 降级项全部放弃（安全默认优先），目标由 30% 下调至 15–20%；#5 Android 后台冻结因本地无 Chromium 源/无外网无法带证据编写，降级为设计+度量先行；#8 顺延。`tools/perf/` 已提交 `9866a195`（注：此行由原首条改写，模块明细见下）。
- 2026-10-17：新增 `tools/perf/` CPU A/B 基准测量模块（README + collect_android.sh + analyze_trace.py + 合成 fixture，纯函数式、无 class、全 ASCII），self-test 20 断言全过、`bash -n` 通过；待真机实测采集（本环境无 adb）。
- 2026-10-17：禁用后台周期唤醒——`Disable-update-scheduler.patch` 扩为 4 任务 return null（WebAPK/组件更新/一次性后台同步/通知调度，NotificationSchedulerTask 类名已确证）；新增 `Disable-periodic-background-sync.patch`（默认关 Periodic Background Sync，chrome://flags 可开，Need: Add-cromite-flags-support），登记于补丁清单 L63（fetching-of-all-field-trials 与 plugins-enumeration 之间）；合成 pre-image `git apply --check` 全部通过；已提交 `1ba6f466`（扩展）+ `b3ca8fc3`（新补丁）。
- 2026-10-17：`build/cromite.gn_args` 重新启用 `use_v8_context_snapshot = true`（降 renderer 启动 CPU；#317 崩溃若复现需改回 false）；已提交 `88b39e87`。
- 2026-10-17：`dce7dd1c` 恢复 VAAPI 驱动检查（去除默认 kVaapiIgnoreDriverChecks）；`65ceef93` kFreezingWithoutBatterySaver 默认关闭（省电模式才冻结，flag 可开）——根治 XFCE 卡死/后台标签假死两处「默认危险」。
- 2026-09-19：`3724efc6` Gerrit 同步为 diff 索引重下载缺失补丁；`2384a226` 上传失败增加日志。
- 2026-09-15：`bf50983d` 构建脚本以 python3 替换 vpython3；`c0af5b6c`/`49c23e54` 创建 `/github/home/.cache` 目录；`a711448b` 常规 Gerrit 同步。
- 2026-09-14：`6c77ae37` 合入 Chromium 153.0.8010.37 补丁批次；`9a6fc36d` 完成 Global Privacy Control 实现；
  `d975426d` DoH 未指定时默认 OpenDNS；`9e5b4a0d` 底部导航栏崩溃修复（#3046）并默认禁用上游底栏（#3044）；
  `f7eccec0` 退出清除数据 UI 计数修复；`af2d3b9a` 恢复 Simplified NTP 丢失 hunk；CI 自动再生 PATCHES.md（#3052）。

## 待办事项 (Pending Work)

- **push 待执行**（本地 NO_NET，git push 30s 超时）：网络恢复后 `git push origin master`。push 后盯 CI：`check-git-apply`（重点验证 `Disable-update-scheduler.patch` 扩展 hunk 与新补丁 `Disable-periodic-background-sync.patch`）与 `build_cromite`（验证 `use_v8_context_snapshot=true` 可编译）。
- `use_v8_context_snapshot=true` 的 #317 崩溃场景需真机回归；若复现直接改回 false（cromite.gn_args 注释已留指引）。
- CPU 优化 #5（Android 后台 tab 冻结）：被"无 Chromium 源码树/无外网"阻塞，需在可拉取 153 源码的环境按设计实施（battery-saver 门控、音频/下载豁免、core+exemption 两文件 ≤400 行）；#7 用 `tools/perf/` 真机采基线后再评估 #7/#8 收益。
- 观察下一轮 Gerrit 同步周期：验证"缺失补丁重下载"逻辑是否消除上传失败（关联 `2384a226` 日志）。
- 跟踪 Chromium 153 后续小版本 rebase 与用户反馈（底栏 / NTP 相关 issue）。

## Agent 备注 (Agent Notes)

- 补丁流水线：改 `build/patches/` 后保持 `build/cromite_patches_list.txt` 顺序一致；`docs/PATCHES.md` 由 CI 自动再生，勿手改。
- 提交信息约定：`[TOOLS]` 工具类 / `[AUTO][DOC]` CI 文档 / 补丁改动直接用英文补丁描述。
- 工程约束：新增文件 ≤400 行、迭代文件 ≤800 行；新增代码纯函数式（禁 class）；严禁敏感信息入码。
- 时间线与简报：任务完成/阻塞后在 `features/dev-memory-timeline.md` 追加条目；用户要汇总时按 `features/dev-memory-newsletter.mdc.rule` 生成简报。
