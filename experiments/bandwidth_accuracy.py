"""Compare steady UDP sender payload rate with the first inter-switch TX port."""
import json
import re
import runpy
import shutil
import statistics
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def sender_mbps(tool, output):
    if tool == "iperf3":
        report = json.loads(output)
        if "error" in report:
            raise ValueError(report["error"])
        intervals = [(i["sum"]["start"], i["sum"]["end"], i["sum"]["bits_per_second"] / 1e6)
                     for i in report["intervals"]]
    else:
        if "Server Report:" not in output:
            raise ValueError("No iperf receiver report")
        intervals = [(float(a), float(b), float(rate)) for a, b, rate in re.findall(
            r"\]\s*([\d.]+)\s*-\s*([\d.]+)\s+sec\s+[\d.]+\s+\S+\s+([\d.]+)\s+Mbits/sec",
            output.split("Server Report:")[0])]
    selected = [(b - a, rate) for a, b, rate in intervals
                if a >= 4.9 and b <= 25.1 and 0 < b - a < 2]
    duration = sum(t for t, _ in selected)
    if duration < 18:
        raise ValueError("Incomplete sender interval report")
    return sum(t * rate for t, rate in selected) / duration


def stop(proc):
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def run(network):
    root = Path("/media/sf_sdn_transfer/experiments")
    helpers = runpy.run_path(str(root / "grid_demo.py"))
    api = helpers["api"]
    tool = "iperf3" if shutil.which("iperf3") else "iperf"
    if not shutil.which(tool):
        print("No local iperf executable found.")
        return
    src, dst = network["h1"], network["h16"]
    src.cmd("ping -n -c 1 -W 2 " + dst.IP())

    def current_path():
        topo = api("topology")
        hosts = {h["mac"]: h for h in api("sdn/hosts")["hosts"]}
        a, b = src.MAC().lower(), dst.MAC().lower()
        route = helpers["forwarding_path"](helpers["flow_tables"](topo["switches"]),
                                           topo["links"], a, b, hosts[a], hosts[b])
        if not route["complete"] or len(route["path"]) < 2:
            raise ValueError("No complete inter-switch route")
        return route["path"]

    report = dict(tool=tool, requested_bps=5000000, source="h1", target="h16", trials=[])
    output = root / "results" / datetime.now(timezone.utc).strftime("accuracy-%Y%m%dT%H%M%SZ.json")
    print(tool, "· H1 -> H16 · five 30-second UDP runs at 5 Mbps", flush=True)
    try:
        for index in range(5):
            route = current_path()
            port = str(5710 + index)
            trial = dict(path=route, samples=[])
            report["trials"].append(trial)
            server = client = None
            with tempfile.TemporaryFile(mode="w+t") as rx, tempfile.TemporaryFile(mode="w+t") as tx:
                try:
                    args = ["-1"] if tool == "iperf3" else ["-u"]
                    server = dst.popen([tool, "-s", "-p", port] + args,
                                       stdout=rx, stderr=subprocess.STDOUT)
                    time.sleep(0.6)
                    if server.poll() is not None:
                        raise RuntimeError("Receiver failed to start")
                    args = ["-J"] if tool == "iperf3" else ["-f", "m"]
                    cmd = [tool, "-c", dst.IP(), "-p", port, "-u", "-b", "5000000",
                           "-l", "1400", "-i", "1", "-t", "30"] + args
                    start = time.monotonic()
                    client = src.popen(cmd, stdout=tx, stderr=subprocess.STDOUT)
                    # Default controller polling period is 5s. Skip the startup
                    # and shutdown windows; snapshots lack controller timestamps.
                    for offset in (12, 17, 22):
                        time.sleep(max(0, start + offset - time.monotonic()))
                        if client.poll() is not None:
                            raise RuntimeError("Sender ended early")
                        records = api("sdn/bandwidth")["ports"]
                        reading = next(p for p in records if p["switch"] == route[0]
                                       and p.get("neighbor") == route[1])
                        elapsed = time.monotonic() - start
                        if elapsed > 25:
                            raise RuntimeError("Late controller reading")
                        trial["samples"].append(dict(elapsed=elapsed, **reading))
                    if client.wait(timeout=20) != 0:
                        raise RuntimeError("Sender failed")
                finally:
                    stop(client)
                    stop(server)
                    tx.seek(0)
                    rx.seek(0)
                    trial.update(sender_output=tx.read(), receiver_output=rx.read())
            if current_path() != route:
                raise RuntimeError("Route changed during run")
            measured = sender_mbps(tool, trial["sender_output"])
            monitored = statistics.mean(p["tx_mbps"] for p in trial["samples"])
            error = 100 * abs(monitored - measured) / measured
            trial.update(sender_mbps=measured, controller_tx_mbps=monitored, error_percent=error)
            print("Run %d/5: sender %.3f Mbps | controller %.3f Mbps | error %.2f%%" %
                  (index + 1, measured, monitored, error), flush=True)
        errors = [t["error_percent"] for t in report["trials"]]
        report.update(mean_error_percent=statistics.mean(errors), sd_error_percent=statistics.stdev(errors))
        print("Mean error %.2f%% | sample SD %.2f percentage points" %
              (report["mean_error_percent"], report["sd_error_percent"]))
    except (Exception, KeyboardInterrupt) as exc:
        report["error"] = repr(exc)
        print("Stopped:", repr(exc))
    finally:
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("Saved:", output, flush=True)


if "net" in globals():
    run(net)
