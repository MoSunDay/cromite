#!/usr/bin/env bash
#
# collect_android.sh - on-device CPU data collection for Cromite A/B benchmarking.
#
# Subcommands:
#   trace <duration_seconds> <out_dir>      perfetto ftrace capture (sched/power), pulled to host
#   simpleperf <seconds> <out_dir>          simpleperf CPU profile of Cromite processes
#   wakeup <seconds> <out_dir>              dumpsys alarm/jobscheduler snapshots before/after sleep
#
# Device prerequisites:
#   - adb in PATH (override binary with ADB env var), one connected device.
#   - perfetto subcommand: userdebug/rooted build (ftrace access) with the
#     perfetto command-line tool on device (present on modern userdebug images).
#   - simpleperf subcommand: simpleperf on device (Android >= 7), app running.
#   - wakeup subcommand: any adb-accessible device; keep it idle for the window.
#
# Environment overrides (read-only config):
#   CROMITE_PACKAGE  browser package to profile (default: org.cromite.cromite)
#   ADB              adb binary (default: adb)

set -euo pipefail

readonly PACKAGE="${CROMITE_PACKAGE:-org.cromite.cromite}"
readonly ADB_BIN="${ADB:-adb}"
readonly DEVICE_TRACE_PATH=/data/misc/perfetto-traces/trace
readonly DEVICE_CFG_PATH=/data/local/tmp/cromite_perfetto.conf
readonly DEVICE_PERFDATA_PATH=/data/local/tmp/cromite_perf.data

die() {
    printf 'collect_android.sh: error: %s\n' "$1" >&2
    exit 1
}

usage() {
    sed -n '3,22p' "$0" | sed 's/^# \{0,1\}//'
}

check_adb() {
    command -v "$ADB_BIN" >/dev/null 2>&1 \
        || die "adb not found in PATH (set ADB=/path/to/adb)"
    "$ADB_BIN" get-state >/dev/null 2>&1 \
        || die "no adb device in the required state (check: $ADB_BIN devices)"
}

# ensure_positive_int <value> <label>
ensure_positive_int() {
    case "$2" in
        ''|*[!0-9]*) die "$1 must be a positive integer (got: '$2')" ;;
    esac
    [ "$2" -gt 0 ] || die "$1 must be > 0 (got: '$2')"
}

# ensure_out_dir <path>
ensure_out_dir() {
    mkdir -p -- "$1" || die "cannot create output dir: $1"
}

# print_collected <file>...
print_collected() {
    printf 'Collected files:\n'
    local f
    for f in "$@"; do
        printf '  %s\n' "$f"
    done
}

# write_trace_config <out_file> <duration_ms>
# Bundled perfetto config: ftrace sched + power (cpufreq), file output mode.
write_trace_config() {
    local out_file=$1 duration_ms=$2
    cat > "$out_file" <<EOF
buffers: {
    size_kb: 65536
    fill_policy: RING_BUFFER
}
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            ftrace_events: "sched/sched_switch"
            ftrace_events: "sched/sched_waking"
            ftrace_events: "power/cpu_frequency"
            ftrace_events: "power/cpu_idle"
            buffer_size_kb: 16384
        }
    }
}
duration_ms: ${duration_ms}
write_into_file: true
file_write_period_ms: 1000
EOF
}

# find_pids -> comma-separated pid list for the Cromite processes.
# Uses pidof for the main process and pgrep -f for sandboxed children
# (renderers share the package prefix in their process names).
find_pids() {
    local main_pids child_pids
    main_pids=$("$ADB_BIN" shell pidof "$PACKAGE" 2>/dev/null | tr -d '\r' || true)
    child_pids=$("$ADB_BIN" shell pgrep -f "$PACKAGE" 2>/dev/null | tr -d '\r' || true)
    printf '%s\n%s\n' "$main_pids" "$child_pids" \
        | tr -s ' \t' '\n' | sed '/^$/d' | sort -un | paste -sd, -
}

cmd_trace() {
    [ $# -eq 2 ] || die "usage: collect_android.sh trace <duration_seconds> <out_dir>"
    local duration=$1 out_dir=$2
    ensure_positive_int "duration" "$duration"
    ensure_out_dir "$out_dir"
    check_adb
    local cfg trace_file
    cfg="$out_dir/perfetto.conf"
    trace_file="$out_dir/trace.pftrace"
    printf 'Recording perfetto trace for %s s (package-independent ftrace)...\n' "$duration"
    write_trace_config "$cfg" "$((duration * 1000))"
    "$ADB_BIN" push "$cfg" "$DEVICE_CFG_PATH" >/dev/null
    "$ADB_BIN" shell perfetto -c "$DEVICE_CFG_PATH" --txt -o "$DEVICE_TRACE_PATH"
    "$ADB_BIN" pull "$DEVICE_TRACE_PATH" "$trace_file" >/dev/null
    print_collected "$trace_file" "$cfg"
    printf 'Next: convert to text, then analyze:\n'
    printf '  traceconv systrace %s > %s/trace.txt\n' "$trace_file" "$out_dir"
    printf '  python3 tools/perf/analyze_trace.py cpu %s/trace.txt --json %s/cpu.json\n' \
        "$out_dir" "$out_dir"
}

cmd_simpleperf() {
    [ $# -eq 2 ] || die "usage: collect_android.sh simpleperf <seconds> <out_dir>"
    local duration=$1 out_dir=$2
    ensure_positive_int "seconds" "$duration"
    ensure_out_dir "$out_dir"
    check_adb
    local pids perf_file
    pids=$(find_pids)
    [ -n "$pids" ] || die "no running process for $PACKAGE (start the browser first)"
    perf_file="$out_dir/perf.data"
    printf 'Recording simpleperf (-g, %s s) for pids %s...\n' "$duration" "$pids"
    "$ADB_BIN" shell simpleperf record -g --duration "$duration" \
        -p "$pids" -o "$DEVICE_PERFDATA_PATH"
    "$ADB_BIN" pull "$DEVICE_PERFDATA_PATH" "$perf_file" >/dev/null
    print_collected "$perf_file"
    printf 'Next: %s shell simpleperf report -i %s (or: report_html.py on host)\n' \
        "$ADB_BIN" "$DEVICE_PERFDATA_PATH"
}

# snapshot_dumps <label> <out_dir>
snapshot_dumps() {
    local label=$1 out_dir=$2
    "$ADB_BIN" shell dumpsys alarm > "$out_dir/alarm_${label}.txt"
    "$ADB_BIN" shell dumpsys jobscheduler > "$out_dir/jobscheduler_${label}.txt"
}

cmd_wakeup() {
    [ $# -eq 2 ] || die "usage: collect_android.sh wakeup <seconds> <out_dir>"
    local duration=$1 out_dir=$2
    ensure_positive_int "seconds" "$duration"
    ensure_out_dir "$out_dir"
    check_adb
    printf 'Snapshotting alarm/jobscheduler, sleeping %s s (keep device idle)...\n' "$duration"
    snapshot_dumps before "$out_dir"
    sleep "$duration"
    snapshot_dumps after "$out_dir"
    print_collected \
        "$out_dir/alarm_before.txt" "$out_dir/jobscheduler_before.txt" \
        "$out_dir/alarm_after.txt" "$out_dir/jobscheduler_after.txt"
    printf 'Next: diff %s/alarm_before.txt %s/alarm_after.txt to find new wakeups\n' \
        "$out_dir" "$out_dir"
}

main() {
    case "${1:-}" in
        trace) shift; cmd_trace "$@" ;;
        simpleperf) shift; cmd_simpleperf "$@" ;;
        wakeup) shift; cmd_wakeup "$@" ;;
        -h|--help|help|"") usage ;;
        *) die "unknown subcommand: '${1:-}' (try: collect_android.sh help)" ;;
    esac
}

main "$@"
