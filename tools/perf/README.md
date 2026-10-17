# tools/perf - CPU A/B benchmarking for Cromite builds

Small, dependency-free tooling to measure whether a patched Cromite build
burns more CPU than its baseline, and to find *where* the extra cycles or
wakeups come from.

## Purpose

- Establish a CPU baseline (previous Cromite release or vanilla Chromium
  build of the same version) and compare a candidate patched build against
  it on the same hardware.
- Define the **"all-day mixed" metric**: CPU cost of a browser session that
  mixes the two regimes real users spend their day in:
  1. **foreground browsing** - page loads, scrolling, text input, video;
  2. **background idle** - browser backgrounded with tabs open, screen on
     or off, no user interaction.
  The metric is reported per scenario (cold start, background idle, mixed
  browsing) as per-process ON-CPU time plus wakeup counts, so regressions
  in one regime are not hidden by the other.

## Layout

| File | Role |
|------|------|
| `collect_android.sh` | on-device collection: perfetto trace, simpleperf profile, dumpsys wakeup snapshots |
| `analyze_trace.py` | parse sched traces, per-process CPU time, top wakeup sources, A/B compare |
| `fixtures/synthetic_trace.txt` | hand-computable fixture, used by `--self-test` |

## Prerequisites

- adb in PATH (or set `ADB=/path/to/adb`), exactly one connected device.
- `trace` subcommand: userdebug/rooted build (ftrace access) with the
  `perfetto` command-line tool on device.
- `simpleperf` subcommand: device with simpleperf (Android >= 7), browser
  running; override the package with `CROMITE_PACKAGE` (default
  `org.cromite.cromite`).
- Host: python3 (>= 3.6), bash. No third-party Python packages.

## Usage

```bash
# 30 min background-idle scenario, trace + wakeups side by side
bash tools/perf/collect_android.sh trace 1800 out/background/
bash tools/perf/collect_android.sh wakeup 1800 out/background/

# 60 s call-graph profile while reproducing a workload
bash tools/perf/collect_android.sh simpleperf 60 out/foreground/

# convert binary trace to text (either format works for the analyzer)
traceconv systrace out/background/trace.pftrace > out/background/trace.txt

# per-process CPU time (save as json for the A/B compare)
python3 tools/perf/analyze_trace.py cpu out/background/trace.txt \
    --json out/background/cpu.json

# top wakeup sources
python3 tools/perf/analyze_trace.py wakeups out/background/trace.txt -n 20

# analyzer sanity check (no device needed)
python3 tools/perf/analyze_trace.py --self-test
```

## A/B protocol

1. **Builds**: A (baseline) and B (candidate) from the *same* Chromium
   version, same GN args except the patch under test.
2. **Device**: same physical device, same Android build, airplane mode or
   identical network, fixed brightness (50%), battery > 50% or always
   plugged, no other apps running.
3. **Scenarios** (run A and B identically, in this order):
   - cold start x10: kill the app, `am start`, wait for first frame +
     10 s idle, per run;
   - 10-tab 30-min background idle: open 10 tabs, press Home, screen on,
     leave untouched for 30 min;
   - 30-min mixed browsing: scripted page loads + scroll + one video,
     repeated.
4. **Collect** per scenario and per build: `trace` for the full window
   (sched_switch/sched_waking/cpufreq), `simpleperf` for shorter call-graph
   windows, `wakeup` snapshots for the background window.
5. **Compare**: `analyze_trace.py cpu --json` for both builds, then
   `compare baseline.json candidate.json`.

## How the numbers feed the optimization plan

- `compare` output gives **per-process CPU deltas** (browser / renderer /
  GPU / utility): a delta concentrated in renderers points at rendering or
  scheduler-intensity patches; browser-process growth points at timers,
  network keepalives or background services.
- `wakeups` gives the **top wakeup sources** (waker -> target, counts):
  recurring entries such as `AlarmManager -> browser` or a native thread
  waking renderers identify timers/jobs to defer, batch or disable - each
  entry maps to a concrete patch action.
- `simpleperf` call graphs attribute the remaining on-CPU time to symbols,
  closing the loop from delta to code.

Accept a candidate only when the total delta is within noise (< 3% over
repeated runs) or justified by the feature; otherwise attach the compare
table and wakeup list to the patch review.

## Conventions

- Pure functional code: bash uses functions only with read-only config;
  the Python module defines no classes.
- ASCII only; no credentials or device-identifying data are collected.
