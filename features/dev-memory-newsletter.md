# Cromite 开发简报（Dev Memory Newsletter）

> 规则见 `dev-memory-newsletter.mdc.rule`（头部不可修改）。条目来源：`dev-memory-timeline.md`。

## 本期更新 (2026-09-14 ~ 2026-10-17)

- Gerrit 同步工具链改进：缺失补丁重下载用于 diff 索引（`3724efc6`）、上传失败日志（`2384a226`）。
- 构建链迁移：vpython3 → python3（`bf50983d`），并修复 CI 缓存目录（`c0af5b6c`/`49c23e54`）。
- Chromium **153.0.8010.37** 补丁批次合入（`6c77ae37`），`docs/PATCHES.md` 随之自动再生。
- 初始化 agent 本地记忆系统（AGENTS.md / agents/memory / features）。

## 关键变化

- **Global Privacy Control**：补全上游实现（`9a6fc36d`）。
- **DoH**：用户未指定时默认使用 OpenDNS（`d975426d`）。
- **底部导航栏**：修复 MessageContainerCoordinator 崩溃（#3046），默认禁用上游底栏（#3044）（`9e5b4a0d`）。
- **退出时清除数据**：修正 UI 计数显示（`f7eccec0`）。
- **Simplified NTP**：找回意外丢失的 hunk（`af2d3b9a`）。

## 问题与风险

- Gerrit 上传仍存在失败场景，已加日志待下一同步周期观察验证。
- 153 rebase 后需关注底栏 / NTP 相关用户反馈（issue #3044、#3046）。

## 下期计划

- 验证 Gerrit 同步"缺失补丁重下载"逻辑的实际效果。
- 跟踪 Chromium 153 后续小版本，准备下一次 rebase。
- 按记忆规则持续维护时间线与本地记忆。
