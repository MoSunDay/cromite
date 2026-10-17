# 开发时间线（Dev Memory Timeline）

> 规则见 `dev-memory-timeline.mdc.rule`（头部不可修改）。
> 每个已执行的 skill/任务按下列格式登记，状态变化或新目标产生时立即更新。

## [2026-10-17] 全量补丁本地验证 + Docker 构建 153.0.8010.37（执行会话）
**Status**: In Progress（编译中，72,350 步）
**Objective**: push 全部提交后以官方镜像本地构建 Cromite Linux 153.0.8010.37，全量验证 328 补丁可应用性，产出可部署 chrome-lin64
**Changes**:
- push：SSH key 免 PAT 直接 `git push git@github.com:MoSunDay/cromite.git`，6+1 commit 已上远端（3724efc6..7c71dd9e）；fork Actions 未启用（runs total=0），CI 验证由本地构建替代
- 镜像：Docker Hub 无 153 版 cromite-build（止步 147）→ 用 `uazo/chromium:153.0.8010.37`（21.3GB 源码镜像）；dockerd 配 systemd socks5 代理后 `docker pull` 由 daemon 承担（会话杀不掉）
- **git am 疑难**：`Disable-update-scheduler.patch` hunk old 侧缺尾随上下文行 → git 2.34.1 对"无尾上下文且非文件尾"的 hunk 一律拒配（GNU patch 可打）；修复=补一行 `case TaskIds.NOTIFICATION_TRIGGER_JOB_ID:` 且计数 8→9（commit `7c71dd9e` 已推送）
- 补丁全量验证：容器内按清单 git am 328/328 全通过（287 新应用 + 41 复检跳过；跳过检测须用 `git rev-list --count --grep=`，`git log --grep` 无匹配也退 0）
- 工具链补齐：clang 24（tarball 手动装 + cr_build_revision stamp）、chrome-linux PGO profdata 327MB 与 v8 builtins x64.profile（GCS 直链 curl，绕过 vpython/gsutil）
- 编译：`buildtools/linux64/gn`（depot_tools gn wrapper 缺 bootstrap 不可用）+ `siso.py ninja -C out/lin64 chrome chrome_sandbox --offline`
**Next**:
- 编译完成后按 release.yaml 清单打包 chrome-lin64.tar.gz → scp amos（root@192.168.31.196）原子换 /opt/cromite（备份 .bak）→ `--version` 冒烟 + chrome://gpu、#freezing-without-battery-saver 验证

## [2026-10-17] 远程切换 SSH 并启动本地构建发布流水线
**Status**: In Progress
**Objective**: 按用户指示将 git 远程改为 SSH（github.com HTTPS 被墙、SSH 经 127.0.0.1:1080 SOCKS 可达），完成提交 push；并执行"构建应用发布到 192.168.31.196"
**Changes**:
- `git remote set-url origin git@github.com:MoSunDay/cromite.git`；提交 `7c78b47d`（agent 记忆系统 7 文件）并 push 成功——此前"超时"的 HTTPS push 实际已服务端完成（6 commit 在远端）
- **关键发现**：fork 的 GitHub Actions 从未启用（API total_count=0），push 不会触发任何 CI；check-git-apply 兜底假设失效，全量 328 补丁验证只能靠本地容器构建
- 网络拓扑：直连可达 raw.githubusercontent/objects.githubusercontent/codeload/storage.googleapis/ghcr.io/docker.m.daocloud.io；被墙需走 SOCKS(1080)：github.com/hub.docker.com/auth.docker.io/chromium.googlesource；dockerd 已加 systemd 代理（socks5://127.0.0.1:1080）可拉 Docker Hub
- 构建路径：192.168.31.196(amos) `/opt/cromite` 现部署 Cromite 153.0.8010.37 Linux 版（9/15 构建）；局域网无自建 runner、无 Chromium 源码树 → 采用 uazo 公开镜像 `uazo/chromium:153.0.8010.37`（21.3GB，经代理 ~3-5MB/s 拉取中）
- 本地编排脚本 `/root/cromite-build/`（04-run.sh 全自动）：容器内 squash 5 个嵌套仓库（v8/skia/perfetto/devtools-frontend/boringssl）→ git am 应用本 fork 全部补丁 → gn gen（含 use_v8_context_snapshot=true）→ siso ninja out/lin64 chrome chrome_sandbox → 03-deploy.sh rsync 至 amos 原子换目录（备份 /opt/cromite.bak-*，附 BUILD_COMMIT/RELEASE）
- 本机构建资源：16 核 / 62G RAM / 388G 空闲
**Next**:
- 盯 `/root/cromite-build/pipeline.log`：镜像拉完自动 apply+build；apply 若有 FAILED 补丁需回仓库修复再 push；build 完跑 03-deploy.sh 并在 amos 验证 `--version`
## [2026-10-17] CPU 优化批次（#4/#6/#7）执行核验与交付收尾
**Status**: Completed (push 阻塞-无外网)
**Objective**: 对 4 笔已落盘 commit（`1ba6f466`/`b3ca8fc3`/`88b39e87`/`9866a195`）做交付前全量本地核验，并尝试 push 触发 CI 硬闸门
**Changes**:
- 本地核验全绿：`analyze_trace.py --self-test` 20 断言 0 失败（exit 0）；`bash -n collect_android.sh` 通过；`git apply --stat` 确认两个补丁均为合法 unified diff（update-scheduler 4+/4-、periodic-sync 2 files 9+）；补丁清单无重复登记（L42/L63）；行数上限达标（analyze_trace.py 397 ≤ 400）；`grep "class "` 零命中（纯函数式约束）；diff 全文敏感信息扫描零命中
- `git push origin master` 30s 超时（exit 124，NO_NET 环境实测确认），领先 6 commit 待推送；328 补丁全量 apply 验证依计划转交 CI `check-git-apply`
**Next**:
- 网络恢复后 `git push origin master`，盯 CI `check-git-apply`（重点：update-scheduler 扩展 hunk、periodic-sync 新补丁）与 `build_cromite`（use_v8_context_snapshot=true 可编译性）；后续真机项见 agent-local-memory Pending Work

## [2026-10-17] 新增 tools/perf CPU A/B 基准测量模块
**Status**: Completed
**Objective**: 为 Cromite 构建（基线 vs 补丁版）建立可复现的 CPU A/B 测量工具链，定义 "all-day mixed" 指标（前台浏览 + 后台空闲），把 per-process CPU 增量与 top wakeup 源接入优化决策
**Changes**:
- 新增 `tools/perf/README.md`（104 行）：目的、指标定义、用法、A/B 协议（同版本同设备；冷启动×10、10 标签 30min 后台空闲、30min 混合浏览；perfetto+simpleperf 采集）、数字如何反哺优化计划
- 新增 `tools/perf/collect_android.sh`（179 行）：纯函数式 bash（仅函数 + readonly 配置，`set -euo pipefail`），`main` case 分发 `trace`（heredoc 生成 perfetto ftrace 配置 sched_switch/sched_waking/power/cpufreq，落 /data/misc/perfetto-traces/trace 后 pull）/ `simpleperf`（pidof+pgrep 找 pid，`CROMITE_PACKAGE` 可覆盖，默认 org.cromite.cromite）/ `wakeup`（dumpsys alarm+jobscheduler 前后快照）；参数校验 die、创建 out_dir、打印产物路径
- 新增 `tools/perf/analyze_trace.py`（397 行）：零 class 纯函数管线——`parse_sched_events`（同时解析 perfetto systrace `<task>_<pid>_S:<tid>` 与 traceconv 文本两种格式，坏行计数跳过）、`cpu_time_per_process`（按 CPU 相邻 sched_switch 对算 ON-CPU us）、`top_wakeup_sources`、`compare`+`render_report`（per-process 绝对/百分比增量表）；CLI `cpu`/`wakeups`/`compare`/`--self-test`，JSON 往返
- 新增 `tools/perf/fixtures/synthetic_trace.txt`（31 行）：合成轨迹（renderer_A=3000000us、browser=1000000us、browser→renderer_A×2 / AlarmManager→browser×1、2 条垃圾行），`#` 注释记载期望值
- 验证：`--self-test` 20 项断言全 PASS（exit 0）；`bash -n` 通过；cpu/wakeups/compare 端到端输出正确；全 ASCII、无 class 关键字、无敏感信息；未 commit
**Next**:
- 在真实 userdebug 设备上实测三场景采集（本环境无 adb/设备）
- 按 README 协议产出一次基线 vs 候选的 compare 报告，验证 <3% 噪声阈值是否合理

## [2026-10-17] 禁用 Android 后台调度任务与 Periodic Background Sync
**Status**: Completed
**Objective**: 消除浏览器后台周期性唤醒源（隐私 + 省电），用户可经 chrome://flags 恢复
**Changes**:
- `build/patches/Disable-update-scheduler.patch`：hunk 由 1 处 return null 扩为 4 处（WEBAPK update / component update / background sync one-shot / notification scheduler 四类后台任务全部返回 null）；diffstat 改为 `1 file changed, 4 insertions(+), 4 deletions(-)`；`NotificationSchedulerTask` 类名经 `Remove-binary-blob-integrations.patch` L362 的 import hunk-header（80 列截断于 `...NotificationScheduler`，恰为 80 字符）确证
- 新增 `build/patches/Disable-periodic-background-sync.patch`：仅两个新文件——`cromite_flags/third_party/blink/common/features_cc/Disable-periodic-background-sync.inc`（`SET_CROMITE_FEATURE_DISABLED(kPeriodicBackgroundSync);`）+ `cromite_flags/chrome/browser/about_flags_cc/` 同名 .inc（`periodic-background-sync` flag，`kOsAll`，`FEATURE_VALUE_TYPE(blink::features::kPeriodicBackgroundSync)`，含 `#ifdef FLAG_SECTION` 守卫）；header 带 `Need: Add-cromite-flags-support.patch`（镜像 `Disable-support-for-pointer-device-id.patch` 约定）；diffstat 与 git 实测输出逐字一致（`2 files changed, 9 insertions(+)`）
- `build/cromite_patches_list.txt`：第 63 行插入一行（`Disable-fetching-of-all-field-trials` 与 `Disable-plugins-enumeration` 之间，即字母序正确相邻对；且晚于 L3 的 `Add-cromite-flags-support.patch` 满足依赖）
**Next**:
- 等 CI check-git-apply / update-patches-doc（PATCHES.md 自动再生）确认

## [2026-10-17] 重新启用 V8 context snapshot
**Status**: Completed
**Objective**: 降低 renderer 启动 CPU 开销（冷启动/新标签页无需重跑 JS 重建 context）
**Changes**:
- `build/cromite.gn_args`：`use_v8_context_snapshot = false` → `true`（原禁用源于 uazo/cromite#317 崩溃场景，注释保留原 issue 链接与回退提示；全仓 grep 确认仅此一处；已提交 `88b39e87`，待 CI 构建与 #317 场景真机回归）
**Next**:
- 观察启用后是否复现 #317 类崩溃；若复现按注释提示改回 false

## [2026-10-17] 默认安全修复：VAAPI 驱动检查与后台冻结策略
**Status**: Completed
**Objective**: 根治「默认危险」配置导致的 XFCE/X11 UI 卡死与后台标签假死（默认安全 + 可选开启）
**Changes**:
- `dce7dd1c` `Enable-platform-aac-audio-and-h264-video.patch`：删除 `SET_CROMITE_FEATURE_ENABLED(kVaapiIgnoreDriverChecks)`，恢复 Chromium 驱动黑名单检查（坏驱动→自动软解回退而非挂起 GPU 进程）；硬解/硬编默认值不变；用户仍可 `--enable-features=VaapiIgnoreDriverChecks` 强制开启
- `65ceef93` `Enable-HighEfficiencyMode-by-default.patch`：`kFreezingWithoutBatterySaver` 改回 `FEATURE_DISABLED_BY_DEFAULT`（省电模式才冻结，上游行为）；Memory Saver 保持开启；`chrome://flags/#freezing-without-battery-saver` 开关仍可用（`FEATURE_VALUE_TYPE` 注册未动）
- 补丁 diffstat/hunk 计数已同步修正（7→6 行、70→69 insertions）；用合成目标 `git apply` 实测两个 hunk 均干净应用
- DoH 硬编码 OpenDNS（`d975426d`）经评估为刻意隐私设计，未改动
**Next**:
- 重建后验证 `chrome://gpu` VaapiVideoDecoder 行为与 XFCE 复现路径；若仍卡死按 gdb 三进程抓栈（看栈顶 futex 还是 DRM ioctl）
- 等 CI check-git-apply 与 update-patches-doc（PATCHES.md 自动再生）

## [2026-10-17] 初始化本地记忆系统
**Status**: Completed
**Objective**: 为 Cromite 仓库建立 agent 本地记忆（AGENTS.md + agents/memory + features）
**Changes**:
- 新建 `AGENTS.md`（仓库协作入口）、`agents/memory/agent-local-memory.md`（+.mdc.rule）
- 新建 `features/dev-memory-timeline.md`、`features/dev-memory-newsletter.md`（+各自 .mdc.rule）
**Next**:
- 后续任务按规则持续追加时间线与更新本地记忆

## [2026-09-19] Gerrit 同步工具改进
**Status**: Completed
**Objective**: 提升 Gerrit ↔ GitHub 补丁同步的可靠性
**Changes**:
- `3724efc6` 为 diff 索引重下载缺失补丁
- `2384a226` 上传失败增加日志
**Next**:
- 观察下一同步周期是否仍出现上传失败

## [2026-09-15] 构建脚本 vpython3 → python3 迁移
**Status**: Completed
**Objective**: 移除构建链对 vpython3 的依赖并修复缓存目录
**Changes**:
- `bf50983d` 构建脚本以 python3 替换 vpython3
- `c0af5b6c`、`49c23e54` 创建 `/github/home/.cache` 目录；`a711448b` 常规 Gerrit 同步
**Next**:
- 无

## [2026-09-14] Chromium 153.0.8010.37 补丁适配批次
**Status**: Completed
**Objective**: 将 327 个补丁适配并合入 Chromium 153
**Changes**:
- `6c77ae37` 153.0.8010.37 补丁批次
- `9a6fc36d` 完成 Global Privacy Control 上游实现补全
- `d975426d` DoH 默认 OpenDNS（用户未指定时）
- `9e5b4a0d` 底部导航栏崩溃修复（#3046）、默认禁用上游底栏（#3044）
- `f7eccec0` 退出清除数据设置 UI 计数修复
- `af2d3b9a` 恢复 Simplified NTP 意外丢失的 hunk
- `11507ac1`/`e3e366be` CI 自动再生 docs/PATCHES.md
**Next**:
- 跟进 153 后续小版本 rebase 与用户反馈

## 2026-10-17 14:58 — Cromite 构建工具链修复 & build6 启动 & 自动部署武装
**类型**: build/pipeline | **状态**: In Progress
- 根因: chr-source 镜像 `gclient sync --nohooks` 跳过全部 hook → clang/PGO/V8-builtins-pgo 全缺; Python urllib 不支持 socks5 → 装 privoxy(HTTP)→SOCKS 桥 `0.0.0.0:8118`(宿主 systemd 常驻, 修掉 Debian 配置自带 listen-address 双绑死锁)。
- 修复动作: tools/clang/scripts/update.py(167M clang24)、chrome/build/pgo_profiles(327M profdata via update_pgo_profiles.py)、v8/tools/builtins-pgo/download_profiles.py(19M)、devtools sync_rollup_libs.py(exit 0)。
- gn gen 成功: 32061 targets; build6 = siso ninja chrome chrome_sandbox --offline, 75k steps, ~2-3h, log=/tmp/build6.log(容器)。
- 自动化: 容器 watchdog 触发 out/lin64/.build-done → 宿主 systemd cromite-deploy.path → 03-deploy.sh(rsync→amos 备份换目录→验证), deploy.log 落 /root/cromite-build/。
- vpython 9 spec 重装(PATH 缺失导致首轮全 FAIL, 已带 proxy 重跑)。

## 2026-10-17 15:35 — M153 补丁失效修复: Disable-periodic-background-sync 移除
**类型**: patch-fix | **状态**: Done
- build6 在 23384/61240 处失败: cromite_flags/.../Disable-periodic-background-sync.inc 引用的 blink::features::kPeriodicBackgroundSync 在 M153 已被上游删除(仅剩 use_counter/mojom 枚举)。
- 处置: 容器树内 git rm 两个 .inc(318bcdb30b) + 仓库删除 build/patches/Disable-periodic-background-sync.patch 与清单行, commit 65c46a48 已推送; 补丁数 328→327。
- build7 = siso 断点续跑(23k 步缓存有效), 完成后自动 touch .build-done → cromite-deploy.path 自动发布到 192.168.31.196。

## 2026-10-18 00:35 — Cromite Linux 构建成功并部署到 192.168.31.196
**类型**: build/deploy | **状态**: Done
- build8 siso 全量成功: 31877 steps, 8h45m, chrome 862MB + chrome_sandbox(SUID) + v8_context_snapshot.bin。
- 自动部署链生效: .build-done → cromite-deploy.path → 03-deploy.sh → amos /opt/cromite(992M), 版本 Cromite 153.0.8010.37, BUILD_COMMIT=583b613b(=origin/master)。
- 验证: --version OK; headless dump-dom + JS 引擎 OK(JS-OK); 旧版备份 /opt/cromite.bak-20261018-0026(991M)。
- 坑: systemd PathExists 对持久 flag 会重复触发(path 单元连发 5 次部署, 备份目录堆积), 已 disable + rm flag; 首次 mv 到已存在 bak 目录会内嵌成子目录。
- 会话容器与宿主 /root/cromite 为不同 overlay 视图, 宿主 auto-commit(99d6e569/583b613b)与我的 65c46a48 合流后被自动同步推送, 历史无冲突。
