"""Compare complete receiver intervals around the first managed move per pair."""
import json
import re
import statistics


def summarize(output, trace, receiver_report):
    data = json.loads(output.read_text())
    events = re.findall(r"PATH_COMMIT ([\d.]+) (\S+) (\S+) (\[[^\]]+\]) (\[[^\]]+\])", trace)
    data["path_commits"] = events
    measurements = []
    for flow in data["workload"]:
        port = str(flow["port"])
        macs = ["00:00:00:00:00:%02x" % int(flow[key][1:]) for key in ("src", "dst")]
        moves = [float(t) for t, a, b, _, _ in events if [a, b] == macs]
        if not moves:
            continue
        start = data["sender_launches"][port]
        cut = moves[0] - start
        end = min(60, moves[1] - start - 1 if len(moves) > 1 else 60)
        bins = []
        for line in data["logs"]["rx"+port].splitlines():
            span = re.search(r"\]\s*([\d.]+)\s*-\s*([\d.]+)\s+sec", line)
            if span and re.search(r"\d\s+ms\s+\d+\s*/", line):
                a, b = map(float, span.groups())
                if 0.95 <= b - a <= 1.05:
                    bins.append((a, b, receiver_report(line)))
        before = [row for row in bins if row[0] >= 1 and row[1] <= cut-1][-5:]
        after = [row for row in bins if row[0] >= cut+1 and row[1] <= end][:5]
        item = dict(src=flow["src"], dst=flow["dst"], commit_seconds=cut, phases={})
        measurements.append(item)
        for name, rows in (("before", before), ("after", after)):
            if len(rows) != 5 or any(abs(r[0]-l[1]) > 0.05 for l,r in zip(rows,rows[1:])):
                continue
            lo, hi = rows[0][0], rows[-1][1]
            rtts = []
            for t, delay in re.findall(r"^\[([\d.]+)\].*bytes from .*time=([\d.]+) ms",
                                       data["logs"]["ping"+port], re.MULTILINE):
                stamp = float(t)-data["epoch_minus_monotonic"]-start
                if lo <= stamp-float(delay)/1000 and stamp <= hi:
                    rtts.append(float(delay))
            total = sum(r["total"] for _, _, r in rows)
            item["phases"][name] = dict(window_seconds=[lo, hi], mbps=sum(
                (b-a)*r["mbps"] for a,b,r in rows)/(hi-lo),
                loss_percent=100*sum(r["lost"] for _,_,r in rows)/total,
                mean_interval_jitter_ms=statistics.mean(r["jitter_ms"] for _,_,r in rows),
                mean_ping_rtt_ms=statistics.mean(rtts) if rtts else None, ping_replies=len(rtts))
    data["phase_comparisons"] = measurements
    output.write_text(json.dumps(data, indent=2))
    paired = sum(len(item["phases"]) == 2 for item in measurements)
    print("Moved workload pairs:", len(measurements), "| paired receiver windows:", paired, flush=True)
    return dict(file=output.name, mode="balanced", moved_pairs=len(measurements), paired_windows=paired)
