"""Run paired shortest-path and load-balancer trials on fresh Mininet grids."""
import argparse
import json
import os
import re
import runpy
import shutil
import socket
import statistics
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from functools import partial
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "vm-source"
demo = runpy.run_path(str(HERE / "grid_demo.py"))


def receiver_report(text):
    match = re.search(r"(\d+(?:\.\d+)?)\s+([KMG]?)bits/sec\s+([\d.]+)\s+ms\s+(\d+)\s*/\s*(\d+)", text)
    if not match or int(match[5]) == 0:
        raise ValueError("Missing UDP receiver summary")
    scale = {"": 1e-6, "K": 0.001, "M": 1, "G": 1000}[match[2]]
    return {"mbps": float(match[1]) * scale, "jitter_ms": float(match[3]),
            "lost": int(match[4]), "total": int(match[5]),
            "loss_percent": 100 * int(match[4]) / int(match[5])}


def wait_status(controller, mode, grid=False):
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        if controller.poll() is not None:
            raise RuntimeError("Controller exited during startup")
        try:
            status = demo["api"]("sdn/status")
            if status.get("routing_mode") == mode and (not grid or
                    (status["switches"], status["links"]) == (6, 7)):
                return
        except OSError:
            pass
        time.sleep(0.5)
    raise RuntimeError("Timed out waiting for controller or grid discovery")


def detection_result(output, data, trace, interval):
    start = data["first_sender_launch_monotonic"]
    samples = []
    for line in trace.splitlines():
        if "DETECTION_SAMPLE " in line:
            stamp, use, ewma, streak = line.split("DETECTION_SAMPLE ")[1].split()
            elapsed = float(stamp) - start
            if 0 <= elapsed <= 60:
                samples.append(dict(seconds=elapsed, utilization_percent=float(use),
                                    ewma_percent=float(ewma), streak=int(streak)))
    events = [s["seconds"] for s in samples if s["streak"] == 2]
    times = [0] + [s["seconds"] for s in samples] + [60]
    largest_gap = max(b-a for a, b in zip(times, times[1:]))
    continuous = largest_gap < 1.8 * interval
    status = "detected" if events else "not detected"
    if not continuous:
        status = "incomplete telemetry"
    result = dict(file=output.name, mode="T%d" % interval, poll_seconds=interval,
                  status=status, first_detection_seconds=events[0] if events else None,
                  largest_sample_gap_seconds=largest_gap)
    data.update(detection=result, detection_samples=samples)
    output.write_text(json.dumps(data, indent=2))
    print(result, flush=True)
    return result


def wait_idle_link(interval):
    deadline = time.monotonic() + 4 * interval + 10
    while not any(p["switch"] == 2 and p.get("neighbor") == 3 and
                  p.get("ewma_utilization_percent", 100) < 5
                  for p in demo["api"]("sdn/bandwidth")["ports"]):
        if time.monotonic() > deadline:
            raise RuntimeError("No idle baseline on S2 -> S3")
        time.sleep(0.5)


def trial(mode, account, manager, output, workload=None, recovery=False, interval=None):
    from mininet.link import TCLink
    from mininet.net import Mininet
    from mininet.node import OVSSwitch, RemoteController

    topo = runpy.run_path(str(SOURCE / "custom_topology.py"))["MyNetwork"]()
    with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryFile(mode="w+t") as log:
        directory = Path(temp)
        app = directory / "rest_api_controller.py"
        shutil.copyfile(SOURCE / app.name, app)
        directory.chmod(0o755)
        app.chmod(0o644)
        env = dict(os.environ, HOME=account.pw_dir, SDN_TOPOLOGY="mynetwork",
                   SDN_ROUTING_MODE=mode, SDN_POLL_INTERVAL=str(interval or 5),
                   SDN_TRACE_DETECTION="1" if interval else "0", PYTHONDONTWRITEBYTECODE="1")
        controller = subprocess.Popen([str(manager), "--observe-links", "--ofp-tcp-listen-port",
            "6653", str(app)], cwd=temp, env=env, user=account.pw_uid, group=account.pw_gid,
            extra_groups=[], stdout=log, stderr=subprocess.STDOUT)
        net = None
        try:
            wait_status(controller, mode)
            net = Mininet(topo=topo, build=False, controller=None,
                          switch=partial(OVSSwitch, protocols="OpenFlow13"),
                          link=TCLink, autoSetMacs=True)
            net.addController("c0", controller=RemoteController, ip="127.0.0.1", port=6653)
            net.build()
            net.start()
            wait_status(controller, mode, grid=True)
            if recovery:
                from link_failure_demo import run_link_failure_demo
                pair = [net["h2"], net["h6"]]
                if net.ping(pair, timeout="2") and net.ping(pair, timeout="2"):
                    raise RuntimeError("Warm-up failed before link failure")
                run_link_failure_demo(net, source_name="h2", output_path=output)
                data = json.loads(output.read_text())
                if data.get("interrupted"):
                    raise KeyboardInterrupt
                alternate = data.get("while_down", {}).get("forwarding", {})
                path = alternate.get("path", [])
                def link_present(stage):
                    links = data.get(stage, {}).get("topology", {}).get("links", [])
                    return any({link["source"], link["destination"]} == {5, 6} for link in links)

                if (data.get("error") or not alternate.get("complete")
                        or link_present("while_down") or not link_present("after")
                        or any({a, b} == {5, 6} for a, b in zip(path, path[1:]))):
                    raise RuntimeError(data.get("error") or "Alternate route or restoration not confirmed")
                metrics = data["ping_measurements"]
                if metrics["first_post_cut_reply_ms"] is None or not metrics["summary"]:
                    raise RuntimeError("No valid timing window or ping summary")
                summary = metrics["summary"]
                return dict(file=output.name, mode=mode, path=path,
                            first_post_cut_reply_ms=metrics["first_post_cut_reply_ms"],
                            lost=summary["transmitted"] - summary["received"])
            if workload is not None:
                from ten_flows import measure
                if interval:
                    wait_idle_link(interval)
                result = measure(net, mode, output, workload, demo, receiver_report)
                if interval:
                    data = json.loads(output.read_text())
                    for flow in workload:
                        path = data["initial_paths"][str(flow["port"])]["path"]
                        if (2, 3) not in zip(path, path[1:]):
                            raise RuntimeError("Calibration flow did not start on S2 -> S3")
                    with open("/proc/self/fd/%d" % log.fileno(), errors="replace") as trace:
                        result = detection_result(output, data, trace.read(), interval)
                    for sample in data["detection_samples"]:
                        print("t=%.2fs  EWMA=%.3f%%  streak=%d" %
                              (sample["seconds"], sample["ewma_percent"], sample["streak"]))
                    return result
                return result
            for src, dst in (("h1", "h6"), ("h3", "h5")):
                if net.ping([net[src], net[dst]], timeout="2") and net.ping(
                        [net[src], net[dst]], timeout="2"):
                    raise RuntimeError("Host pair unreachable before traffic")
            if interval:
                wait_idle_link(interval)
            demo["run_grid_demo"](net["h1"], net["h3"], net["h5"], net["h6"], output)
            data = json.loads(output.read_text())
            if data.get("interrupted"):
                raise KeyboardInterrupt
            if interval and not data.get("error") and "final_path" in data:
                for host in ("H5", "H6"):
                    receiver_report(data["process_output"][host + " receiver"])
                # Read without disturbing the controller's shared write offset.
                with open("/proc/self/fd/%d" % log.fileno(), errors="replace") as trace:
                    return detection_result(output, data, trace.read(), interval)
            if data.get("error") or not data.get("final_path", {}).get("complete"):
                raise RuntimeError(data.get("error") or "Trial did not finish with a complete path")
            if mode == "shortest" and data["final_path"] != data["initial_path"]:
                raise RuntimeError("Baseline route changed")
            return {"file": output.name, "mode": mode, "path": data["final_path"],
                    "receivers": {host: receiver_report(data["process_output"][host + " receiver"])
                                  for host in ("H6", "H5")}}
        except Exception:
            log.seek(0)
            print(log.read()[-1800:])
            raise
        finally:
            try:
                if net is not None:
                    net.stop()
            finally:
                controller.terminate()
                try:
                    controller.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    controller.kill()
                    controller.wait()


def shared_link_workload():
    pairs = [("h3", "h6", 16), ("h4", "h5", 18),
             ("h1", "h6", 28), ("h3", "h5", 28)]
    return [dict(src=a, dst=b, mbps=rate, port=5821+i)
            for i, (a, b, rate) in enumerate(pairs)]


def main():
    import pwd
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", metavar="BATCH", help="existing compare-grid results directory name")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--ten-flows", action="store_true", help="compare three modes with ten UDP pairs")
    group.add_argument("--recovery", action="store_true", help="measure five S5-S6 link failures")
    group.add_argument("--detection", action="store_true", help="compare congestion detection at T=2s and T=5s")
    group.add_argument("--calibrate-detection", action="store_true", help="one direct H3-H5 UDP trial at T=5s")
    group.add_argument("--shared-link-detection", action="store_true", help="one trial with four UDP pairs sharing S2 -> S3")
    group.add_argument("--compare-shared-link", action="store_true", help="five matched T=2s and T=5s rounds on S2 -> S3")
    args = parser.parse_args()
    if os.getuid() != 0 or not os.environ.get("SUDO_USER"):
        raise SystemExit("Launch with sudo from your Ubuntu user terminal.")
    account = pwd.getpwnam(os.environ["SUDO_USER"])
    manager = Path(account.pw_dir) / "sdn-lab/.venv/bin/osken-manager"
    if not manager.is_file() or not shutil.which("iperf"):
        raise SystemExit("Missing local osken-manager or iperf.")
    bridges = subprocess.check_output(["ovs-vsctl", "list-br"], text=True).split()
    if any(re.fullmatch(r"s\d+", name) for name in bridges):
        raise SystemExit("Exit the existing Mininet session before launching.")
    for port in (6653, 8080):
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                raise SystemExit("Stop the existing controller before launching.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if args.calibrate_detection or args.shared_link_detection:
        if args.resume:
            parser.error("Calibration is a single independent trial.")
        if args.shared_link_detection:
            output = HERE / "results" / ("shared-link-" + stamp + ".json")
            workload = shared_link_workload()
        else:
            output = HERE / "results" / ("calibration-" + stamp + ".json")
            workload = [dict(src="h3", dst="h5", mbps=95, port=5811)]
        print("S2 -> S3 calibration, 60 seconds, T=5s:", workload, flush=True)
        trial("balanced", account, manager, output, workload=workload, interval=5)
        print("Saved:", output)
        return
    prefix = "ten-flows-" if args.ten_flows else "compare-grid-"
    if args.recovery:
        prefix = "recovery-"
    if args.detection:
        prefix = "detection-"
    if args.compare_shared_link:
        prefix = "shared-detection-"
    compare_intervals = args.detection or args.compare_shared_link
    if args.resume and not re.fullmatch(prefix + r"\d{8}T\d{6}Z", args.resume):
        parser.error("Expected a compare-grid timestamp directory name")
    folder = HERE / "results" / (args.resume or prefix + stamp)
    summary = folder / "summary.json"
    if args.resume:
        if not folder.is_dir():
            parser.error("Batch directory does not exist")
        trials = json.loads(summary.read_text()) if summary.exists() else []
        for row in trials:
            if not (folder / row["file"]).is_file():
                raise ValueError("Missing raw data for " + row["file"])
    else:
        folder.mkdir(parents=True)
        trials = []
    completed = {(r["pair"], r["mode"]) for r in trials}
    for pair in range(1, 6):
        modes = ("shortest", "balanced") if pair % 2 else ("balanced", "shortest")
        workload = None
        if args.recovery:
            modes = ("balanced",)
        if compare_intervals:
            modes = ("T2", "T5") if pair % 2 else ("T5", "T2")
            if args.compare_shared_link:
                workload = shared_link_workload()
        if args.ten_flows:
            from ten_flows import make_workload
            workload = make_workload(pair)
            modes = ("shortest", "ecmp", "balanced")
            offset = (pair - 1) % len(modes)
            modes = modes[offset:] + modes[:offset]
        for mode in modes:
            if (pair, mode) in completed:
                continue
            print("Pair %d/5: %s" % (pair, mode), flush=True)
            output = folder / ("%02d-%s.json" % (pair, mode))
            if output.exists():
                print("Preserving earlier attempt:", output.name, flush=True)
                output = folder / ("%02d-%s-retry-%s.json" % (pair, mode, stamp))
                if output.exists():
                    raise FileExistsError(output)
            if compare_intervals:
                result = trial("balanced", account, manager, output, workload=workload, interval=int(mode[1:]))
            else:
                result = trial(mode, account, manager, output, workload, args.recovery)
            trials.append(dict(pair=pair, **result))
            pending = summary.with_suffix(".tmp")
            pending.write_text(json.dumps(trials, indent=2))
            pending.replace(summary)
    if compare_intervals:
        for setting in ("T2", "T5"):
            rows = [r for r in trials if r["mode"] == setting]
            times = [r["first_detection_seconds"] for r in rows if r["status"] == "detected"]
            print(setting, "detected:", len(times), "not detected:",
                  sum(r["status"] == "not detected" for r in rows), "incomplete:",
                  sum(r["status"] == "incomplete telemetry" for r in rows))
            if times:
                print("Mean seconds among detections:", round(statistics.mean(times), 3))
            if len(times) > 1:
                print("Sample SD seconds:", round(statistics.stdev(times), 3))
        print("Saved:", folder)
        return
    if args.recovery:
        for metric in ("first_post_cut_reply_ms", "lost"):
            values = [r[metric] for r in trials]
            print("%s: mean %.3f, sample SD %.3f" %
                  (metric, statistics.mean(values), statistics.stdev(values)))
        print("Saved:", folder)
        return
    if args.ten_flows:
        for mode in ("shortest", "ecmp", "balanced"):
            for metric in ("peak_tx_percent", "received_mbps", "loss_percent"):
                values = [r[metric] for r in trials if r["mode"] == mode]
                print("%s %s: mean %.3f, sample SD %.3f" %
                      (mode, metric, statistics.mean(values), statistics.stdev(values)))
        print("Saved:", folder)
        return
    for mode in ("shortest", "balanced"):
        for host in ("H6", "H5"):
            rows = [r["receivers"][host] for r in trials if r["mode"] == mode]
            for metric in ("mbps", "loss_percent", "jitter_ms"):
                values = [r[metric] for r in rows]
                print("%s %s %s: mean %.3f, sample SD %.3f" % (
                    mode, host, metric, statistics.mean(values), statistics.stdev(values)))
    print("Saved:", folder)


if __name__ == "__main__":
    main()
