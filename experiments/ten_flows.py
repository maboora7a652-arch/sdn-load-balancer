"""Ten-flow workload for compare_grid.py. Rates are decimal Mbps."""
import json
import random
import subprocess
import tempfile
import time


def make_workload(round_number):
    rng = random.Random(20261118 + round_number)
    pairs = [(a, b) for a in range(1, 7) for b in range(1, 7) if a != b]
    rates = [8, 8, 8, 8, 12, 12, 16, 20, 24, 28]
    return [dict(src="h%d" % a, dst="h%d" % b, mbps=rate, port=5801 + i)
            for i, ((a, b), rate) in enumerate(zip(rng.sample(pairs, 10), rates))]


def measure(net, mode, output, workload, demo, receiver_report, phases=False):
    raw = dict(mode=mode, duration_seconds=60, workload=workload, samples=[], logs={})
    processes = {}

    def launch(key, host, args, program="iperf"):
        stream = tempfile.TemporaryFile(mode="w+t")
        try:
            proc = net[host].popen([program] + args, stdout=stream, stderr=subprocess.STDOUT)
        except BaseException:
            stream.close()
            raise
        processes[key] = proc, stream

    def paths():
        topo = demo["api"]("topology")
        hosts = {h["mac"]: h for h in demo["api"]("sdn/hosts")["hosts"]}
        tables = demo["flow_tables"](topo["switches"])
        result = {}
        for flow in workload:
            a, b = (net[flow[k]].MAC().lower() for k in ("src", "dst"))
            result[str(flow["port"])] = demo["forwarding_path"](
                tables, topo["links"], a, b, hosts[a], hosts[b])
        return result

    try:
        for flow in workload:
            pair = [net[flow["src"]], net[flow["dst"]]]
            if net.ping(pair, timeout="2") and net.ping(pair, timeout="2"):
                raise RuntimeError("Unreachable pair before traffic: " + str(flow))
        raw["initial_paths"] = paths()
        if not all(p["complete"] for p in raw["initial_paths"].values()):
            raise RuntimeError("Incomplete initial forwarding path")
        links = demo["api"]("topology")["links"]
        directions = {(l["source"], l["destination"]) for l in links}
        directions |= {(b, a) for a, b in directions}
        if len(directions) != 14:
            raise RuntimeError("Grid topology incomplete")
        try:
            for flow in workload:
                port = str(flow["port"])
                options = ["-i", "1", "-f", "m"] if phases else []
                launch("rx"+port, flow["dst"], ["-s", "-u", "-p", port] + options)
                if phases:
                    launch("ping"+port, flow["src"], ["-D", "-n", "-i", "0.25",
                           net[flow["dst"]].IP()], program="ping")
            time.sleep(0.5)
            if any(proc.poll() is not None for proc, _ in processes.values()):
                raise RuntimeError("Receiver failed to start")
            raw["first_sender_launch_monotonic"] = time.monotonic()
            raw["epoch_minus_monotonic"] = time.time() - time.monotonic()
            raw["sender_launches"] = {}
            for flow in workload:
                port = str(flow["port"])
                raw["sender_launches"][port] = time.monotonic()
                launch("tx"+port, flow["src"], ["-u", "-c", net[flow["dst"]].IP(), "-p", port,
                       "-b", str(flow["mbps"] * 1000000), "-t", "60"])
            start = time.monotonic()
            for offset in range(10, 60, 5):
                time.sleep(max(0, start + offset - time.monotonic()))
                ports = [p for p in demo["api"]("sdn/bandwidth")["ports"] if p.get("neighbor")]
                elapsed = time.monotonic() - start
                raw["samples"].append(dict(elapsed=elapsed, ports=ports))
                if {(p["switch"], p["neighbor"]) for p in ports} != directions:
                    raise RuntimeError("Incomplete inter-switch bandwidth sample")
                if elapsed >= 60 or any(proc.poll() is not None for proc, _ in processes.values()):
                    raise RuntimeError("Sample outside common traffic window")
            for key, (proc, _) in processes.items():
                if key.startswith("tx") and proc.wait(timeout=20) != 0:
                    raise RuntimeError("Sender failed: " + key)
        finally:
            for key, (proc, stream) in reversed(list(processes.items())):
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                stream.seek(0)
                raw["logs"][key] = stream.read()
                stream.close()
        raw["final_paths"] = paths()
        if not all(p["complete"] for p in raw["final_paths"].values()):
            raise RuntimeError("Incomplete final forwarding path")
        if mode != "balanced" and raw["initial_paths"] != raw["final_paths"]:
            raise RuntimeError("Baseline path changed")
        def full_report(log):
            if phases:
                import re
                log = "\n".join(line for line in log.splitlines()
                                if re.search(r"\]\s*0(?:\.0+)?\s*-\s*(?:[5-9]\d|\d{3,})(?:\.\d+)?\s+sec", line))
            return receiver_report(log)
        reports = {k: full_report(log) for k, log in raw["logs"].items() if k.startswith("rx")}
        raw["receivers"] = reports
        peak = max((p for s in raw["samples"] for p in s["ports"]),
                   key=lambda p: p["utilization_percent"])
        total = sum(r["total"] for r in reports.values())
        result = dict(file=output.name, mode=mode, peak_tx_percent=peak["utilization_percent"],
                      peak_link=[peak["switch"], peak["neighbor"]],
                      received_mbps=sum(r["mbps"] for r in reports.values()),
                      loss_percent=100 * sum(r["lost"] for r in reports.values()) / total)
        raw["result"] = result
        print(result, flush=True)
        return result
    except (Exception, KeyboardInterrupt) as exc:
        raw["error"] = repr(exc)
        raise
    finally:
        output.write_text(json.dumps(raw, indent=2))
