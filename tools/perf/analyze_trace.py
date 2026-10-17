#!/usr/bin/env python3
"""Parse sched traces and compare per-process CPU time between Cromite builds.

Pure-functional analyzer for the tools/perf A/B benchmarking workflow.
No classes are defined here; data flows through plain functions, tuples and
dicts that are treated as immutable once built.

Input formats (auto-detected per line, unparseable lines are skipped+counted):
  1. perfetto systrace text:
       <task>_<pid>_S:<tid> [000] d..1  123.456789: sched_switch: prev_comm=... next_comm=...
       <task>_<pid>_S:<tid> [000] d..2  123.456789: sched_waking: comm=... pid=... target_cpu=...
  2. traceconv text:
       sched_switch(cpu=0, ts=123.45, prev.pid=..., prev.comm='...', next.comm='...')
       sched_waking(cpu=1, ts=123.46, comm='...', pid=..., waker_comm='...')

Usage: cpu <trace.txt> [--json out.json] | wakeups <trace.txt> [-n N] [--json out]
      | compare <baseline.json> <candidate.json> | --self-test
"""

import argparse
import json
import os
import re
import sys

# --- module-level constants (immutable by convention) ----------------------

FIXTURE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'synthetic_trace.txt')

SYSTRACE_RE = re.compile(
    r'(?P<header>.*?)\s*(?P<ts>\d+(?:\.\d+)?):\s+'
    r'(?P<name>sched_switch|sched_waking):\s*(?P<payload>.*)$')

TRACECONV_RE = re.compile(
    r'^\s*(?P<name>sched_switch|sched_waking)\s*\((?P<payload>.*)\)\s*$')

FIELD_RE = re.compile(
    r'(?P<key>[\w.]+)=(?P<val>"[^"]*"|\'[^\']*\'|[^\s,()]+)')

CPU_RE = re.compile(r'\[\s*(?P<cpu>\d+)\s*\]')

HEADER_TID_RE = re.compile(
    r'^(?P<comm>[\w./+-]+)_(?P<pid>\d+)_S:(?P<tid>\d+)\s')

HEADER_COMM_RE = re.compile(r'^(?P<comm>[\w./+-]+?)-(?P<pid>\d+)\b')

SAMPLE_TRACECONV = (
    "sched_switch(cpu=0, ts=100.0, prev.pid=100, prev.comm='browser', "
    "next.pid=200, next.comm='renderer_A')\n"
    "sched_switch(cpu=0, ts=101.5, prev.pid=200, prev.comm='renderer_A', "
    "next.pid=0, next.comm='swapper/0')\n"
    "sched_waking(cpu=1, ts=99.0, comm='renderer_A', pid=200, waker_comm='browser')\n")

# --- line parsing -----------------------------------------------------------

def coerce_value(raw):
    """Strip optional quotes, then coerce to int / float / original string."""
    stripped = raw.strip('"\'')
    for cast in (int, float):
        try:
            return cast(stripped)
        except ValueError:
            pass
    return stripped

def parse_fields(payload):
    """Key -> coerced-value dict from a `k=v k=v` or `k=v, k=v` payload."""
    return {m.group('key'): coerce_value(m.group('val'))
            for m in FIELD_RE.finditer(payload)}

def parse_header(header):
    """(comm, pid, tid) from a systrace header; values may be None."""
    m = HEADER_TID_RE.match(header)
    if m:
        return m.group('comm'), m.group('pid'), m.group('tid')
    m = HEADER_COMM_RE.match(header)
    if m:
        return m.group('comm'), m.group('pid'), m.group('pid')
    return None, None, None

def parse_ts(fields):
    """Timestamp in seconds from traceconv fields (ts / ts_ns / ts_us)."""
    if 'ts' in fields:
        return float(fields['ts'])
    if 'ts_ns' in fields:
        return float(fields['ts_ns']) / 1e9
    if 'ts_us' in fields:
        return float(fields['ts_us']) / 1e6
    return None

def make_event(kind, ts, cpu, comm, pid, tid, fields):
    """Build one event record; the returned dict is treated as immutable."""
    return {'kind': kind, 'ts': ts, 'cpu': cpu, 'comm': comm,
            'pid': pid, 'tid': tid, 'fields': fields}

def parse_line(line):
    """Parse a single trace line; return an event dict or None."""
    conv = TRACECONV_RE.match(line)
    if conv:
        fields = parse_fields(conv.group('payload'))
        cpu = fields.get('cpu')
        return make_event(conv.group('name'), parse_ts(fields),
                          int(cpu) if cpu is not None else None,
                          None, None, None, fields)
    m = SYSTRACE_RE.search(line)
    if m:
        fields = parse_fields(m.group('payload'))
        header = m.group('header')
        comm, pid, tid = parse_header(header)
        cpu_m = CPU_RE.search(header)
        cpu = int(cpu_m.group('cpu')) if cpu_m else None
        return make_event(m.group('name'), float(m.group('ts')), cpu,
                          comm, pid, tid, fields)
    return None

def parse_sched_events(lines):
    """Parse sched events -> (events, skipped_count).

    events: tuple of immutable-view event dicts in file order. Comment and
    blank lines are ignored silently; unparseable lines are counted.
    """
    events = []
    skipped = 0
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        event = parse_line(line)
        if event is None:
            skipped += 1
        else:
            events.append(event)
    return tuple(events), skipped

def field_of(event, *keys, **kwargs):
    """First matching payload field, else default (systrace + traceconv keys)."""
    for key in keys:
        if key in event['fields']:
            return event['fields'][key]
    return kwargs.get('default')

# --- metrics ----------------------------------------------------------------

def cpu_time_per_process(events):
    """Per-process ON-CPU microseconds, assigned by the `next` comm.

    Per CPU, consecutive sched_switch pairs (e1, e2) mean the `next_comm`
    thread of e1 ran from e1.ts to e2.ts.
    """
    switches = sorted(
        (e for e in events
         if e['kind'] == 'sched_switch' and e['ts'] is not None
         and e['cpu'] is not None),
        key=lambda e: (e['cpu'], e['ts']))
    totals = {}
    for e1, e2 in zip(switches, switches[1:]):
        if e1['cpu'] != e2['cpu']:
            continue
        comm = str(field_of(e1, 'next.comm', 'next_comm', default='?'))
        totals[comm] = totals.get(comm, 0) + round((e2['ts'] - e1['ts']) * 1e6)
    return dict(sorted(totals.items(), key=lambda kv: kv[1], reverse=True))

def waker_name(event):
    """Waker identity: explicit field wins, else the emitting (header) task."""
    fields = event['fields']
    if 'waker_comm' in fields:
        return str(fields['waker_comm'])
    if 'common_pid' in fields:
        return 'pid:%s' % fields['common_pid']
    return str(event['comm']) if event['comm'] else 'unknown'

def target_name(event):
    """Wakeup target identity: payload comm/pid, else 'unknown'."""
    fields = event['fields']
    if 'comm' in fields:
        return str(fields['comm'])
    if 'pid' in fields:
        return 'pid:%s' % fields['pid']
    return 'unknown'

def top_wakeup_sources(events, limit=20):
    """Top-N (waker, target, count) tuples from sched_waking, sorted desc."""
    counts = {}
    for event in events:
        if event['kind'] != 'sched_waking':
            continue
        key = (waker_name(event), target_name(event))
        counts[key] = counts.get(key, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1]))
    return [(waker, target, count) for (waker, target), count in ranked[:limit]]

def delta_pct(baseline, candidate):
    """Percent change, or None when the baseline is zero."""
    if baseline == 0:
        return None
    return round((candidate - baseline) * 100.0 / baseline, 2)

def make_row(name, baseline_us, candidate_us):
    return {'process': name, 'baseline_us': baseline_us,
            'candidate_us': candidate_us,
            'delta_us': candidate_us - baseline_us,
            'delta_pct': delta_pct(baseline_us, candidate_us)}

def compare(baseline, candidate):
    """Compare two {process: cpu_us} dicts -> report dict for render_report."""
    names = sorted(set(baseline) | set(candidate))
    rows = tuple(make_row(n, baseline.get(n, 0), candidate.get(n, 0))
                 for n in names)
    b_total = sum(baseline.values())
    c_total = sum(candidate.values())
    return {'rows': rows, 'baseline_total_us': b_total,
            'candidate_total_us': c_total,
            'total_delta_us': c_total - b_total,
            'total_delta_pct': delta_pct(b_total, c_total)}

def fmt_ms(us):
    return '%.3f' % (us / 1000.0)

def signed(text, positive):
    return ('+' if positive else '') + text

def fmt_pct(pct):
    return 'n/a' if pct is None else signed('%.2f%%' % pct, pct >= 0)

def render_report(report):
    """Render a compare() report dict as a plain-text table."""
    bar = '-' * 82
    lines = ['%-24s %14s %14s %14s %10s' % (
        'process', 'baseline_ms', 'candidate_ms', 'delta_ms', 'delta_pct'), bar]
    for row in report['rows']:
        lines.append('%-24s %14s %14s %14s %10s' % (
            row['process'][:24], fmt_ms(row['baseline_us']),
            fmt_ms(row['candidate_us']),
            signed(fmt_ms(row['delta_us']), row['delta_us'] >= 0),
            fmt_pct(row['delta_pct'])))
    lines.append(bar)
    lines.append('%-24s %14s %14s %14s %10s' % (
        'TOTAL', fmt_ms(report['baseline_total_us']),
        fmt_ms(report['candidate_total_us']),
        signed(fmt_ms(report['total_delta_us']),
               report['total_delta_us'] >= 0),
        fmt_pct(report['total_delta_pct'])))
    return '\n'.join(lines)

# --- I/O helpers ------------------------------------------------------------

def read_lines(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as handle:
        return tuple(handle.read().splitlines())

def dump_json(obj, path):
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(obj, handle, indent=2, sort_keys=True)
        handle.write('\n')

def load_json(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)

def extract_cpu_us(doc):
    """Accept both {'cpu_time_us': {...}} (our dumps) and a plain mapping."""
    if isinstance(doc, dict) and 'cpu_time_us' in doc:
        return dict(doc['cpu_time_us'])
    if isinstance(doc, dict):
        return {str(k): int(v) for k, v in doc.items()}
    raise SystemExit('error: %r is not a per-process CPU-time mapping' % (doc,))

# --- subcommands ------------------------------------------------------------

def cmd_cpu(args):
    events, skipped = parse_sched_events(read_lines(args.trace))
    totals = cpu_time_per_process(events)
    print('trace: %s (%d sched events, %d skipped lines)'
          % (args.trace, len(events), skipped))
    print('%-24s %14s %14s' % ('process', 'cpu_us', 'cpu_ms'))
    for name, us in totals.items():
        print('%-24s %14d %14s' % (name, us, fmt_ms(us)))
    if args.json:
        dump_json({'cpu_time_us': totals}, args.json)
        print('json: %s' % args.json)
    return 0

def cmd_wakeups(args):
    events, skipped = parse_sched_events(read_lines(args.trace))
    ranked = top_wakeup_sources(events, args.limit)
    print('trace: %s (%d sched events, %d skipped lines)'
          % (args.trace, len(events), skipped))
    print('%6s  %-24s -> %s' % ('count', 'waker', 'target'))
    for waker, target, count in ranked:
        print('%6d  %-24s -> %s' % (count, waker, target))
    print('total wakeups (top %d): %d'
          % (args.limit, sum(c for _, _, c in ranked)))
    if args.json:
        dump_json({'wakeups': [[w, t, c] for w, t, c in ranked]}, args.json)
        print('json: %s' % args.json)
    return 0

def cmd_compare(args):
    baseline = extract_cpu_us(load_json(args.baseline))
    candidate = extract_cpu_us(load_json(args.candidate))
    print(render_report(compare(baseline, candidate)))
    return 0

# --- self-test --------------------------------------------------------------

def run_self_test():
    """Assert the analyzer against the bundled fixture; return failure count."""
    failures = []

    def check(label, actual, expected):
        ok = actual == expected
        print('%s %s' % ('PASS' if ok else 'FAIL', label))
        if not ok:
            failures.append(label)
            print('  expected: %r' % (expected,))
            print('  actual:   %r' % (actual,))

    events, skipped = parse_sched_events(read_lines(FIXTURE_PATH))
    check('fixture: 9 events parsed', len(events), 9)
    check('fixture: 2 garbage lines skipped', skipped, 2)
    check('fixture: 6 sched_switch',
          sum(1 for e in events if e['kind'] == 'sched_switch'), 6)
    check('fixture: 3 sched_waking',
          sum(1 for e in events if e['kind'] == 'sched_waking'), 3)
    cpu = cpu_time_per_process(events)
    check('fixture: renderer_A == 3000000 us', cpu.get('renderer_A'), 3000000)
    check('fixture: browser == 1000000 us', cpu.get('browser'), 1000000)
    check('fixture: swapper counted 0 us', cpu.get('swapper/0', 0), 0)
    check('fixture: wakeup ranking',
          top_wakeup_sources(events, 10),
          [('browser', 'renderer_A', 2), ('AlarmManager', 'browser', 1)])

    conv_events, conv_skipped = parse_sched_events(SAMPLE_TRACECONV.splitlines())
    check('traceconv: 3 events parsed', len(conv_events), 3)
    check('traceconv: 0 skipped', conv_skipped, 0)
    check('traceconv: quoted comm unquoted',
          field_of(conv_events[0], 'next.comm'), 'renderer_A')
    check('traceconv: cpu time renderer_A == 1500000 us',
          cpu_time_per_process(conv_events), {'renderer_A': 1500000})
    check('traceconv: waking waker/target',
          top_wakeup_sources(conv_events, 5), [('browser', 'renderer_A', 1)])

    report = compare({'renderer_A': 3000000, 'browser': 1000000},
                     {'renderer_A': 3300000, 'browser': 900000})
    row = {r['process']: r for r in report['rows']}
    rendered = render_report(report)
    check('compare: renderer_A delta +300000 us',
          row['renderer_A']['delta_us'], 300000)
    check('compare: renderer_A delta +10%', row['renderer_A']['delta_pct'], 10.0)
    check('compare: browser delta -10%', row['browser']['delta_pct'], -10.0)
    check('compare: total delta +200000 us', report['total_delta_us'], 200000)
    check('compare: total delta +5%', report['total_delta_pct'], 5.0)
    check('compare: report renders table',
          'TOTAL' in rendered and 'renderer_A' in rendered, True)
    check('json: round-trip',
          extract_cpu_us(json.loads(json.dumps({'cpu_time_us': cpu}))), cpu)
    return len(failures)

# --- CLI --------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog='analyze_trace.py',
        description='Per-process CPU time / wakeup analysis of sched traces.')
    parser.add_argument('--self-test', action='store_true',
                        help='run assertions against the bundled fixture')
    sub = parser.add_subparsers(dest='cmd')
    p_cpu = sub.add_parser('cpu', help='per-process ON-CPU time from a trace')
    p_cpu.add_argument('trace', help='trace text file (systrace or traceconv)')
    p_cpu.add_argument('--json', metavar='OUT', help='dump cpu-time json')
    p_wake = sub.add_parser('wakeups', help='top sched_wakeup sources')
    p_wake.add_argument('trace', help='trace text file (systrace or traceconv)')
    p_wake.add_argument('-n', '--limit', type=int, default=20,
                        help='show top N waker/target pairs (default 20)')
    p_wake.add_argument('--json', metavar='OUT', help='dump wakeup json')
    p_cmp = sub.add_parser('compare', help='diff two cpu-time json files')
    p_cmp.add_argument('baseline', help='baseline json (see cpu --json)')
    p_cmp.add_argument('candidate', help='candidate json (see cpu --json)')
    return parser

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.self_test:
        failures = run_self_test()
        print('self-test: %d failure(s)' % failures)
        return 1 if failures else 0
    handlers = {'cpu': cmd_cpu, 'wakeups': cmd_wakeups, 'compare': cmd_compare}
    handler = handlers.get(args.cmd)
    if handler is None:
        parser.print_help()
        return 2
    return handler(args)

if __name__ == '__main__':
    sys.exit(main())
