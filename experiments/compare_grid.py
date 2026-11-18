"""Run paired shortest-path and load-balancer trials on fresh Mininet grids."""
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


def trial(mode, account, manager, output):
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
                   SDN_ROUTING_MODE=mode, SDN_POLL_INTERVAL="5", PYTHONDONTWRITEBYTECODE="1")
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
            for src, dst in (("h1", "h6"), ("h3", "h5")):
                if net.ping([net[src], net[dst]], timeout="2") and net.ping(
                        [net[src], net[dst]], timeout="2"):
                    raise RuntimeError("Host pair unreachable before traffic")
            demo["run_grid_demo"](net["h1"], net["h3"], net["h5"], net["h6"], output)
            data = json.loads(output.read_text())
            if data.get("interrupted"):
                raise KeyboardInterrupt
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


def main():
    import pwd
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
    folder = HERE / "results" / ("compare-grid-" + stamp)
    folder.mkdir(parents=True)
    trials = []
    for pair in range(1, 6):
        modes = ("shortest", "balanced") if pair % 2 else ("balanced", "shortest")
        for mode in modes:
            print("Pair %d/5: %s" % (pair, mode), flush=True)
            result = trial(mode, account, manager, folder / ("%02d-%s.json" % (pair, mode)))
            trials.append(dict(pair=pair, **result))
            (folder / "summary.json").write_text(json.dumps(trials, indent=2))
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
