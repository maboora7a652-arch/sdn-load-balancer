"""One bounded two-stage UDP trial on the running Mininet grid."""
import json
import runpy
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def run_hold_down(network):
    folder = Path("/media/sf_sdn_transfer/experiments")
    helpers = runpy.run_path(str(folder / "grid_demo.py"))
    api = helpers["api"]
    h1, h2, h3, h4, h5, h6 = (network["h%d" % n] for n in range(1, 7))
    topo = api("topology")

    def path(tables, source, target):
        a, b = source.MAC().lower(), target.MAC().lower()
        return helpers["forwarding_path"](tables, topo["links"], a, b, hosts[a], hosts[b])

    pairs = ((h1, h6, [1, 2, 3, 6]), (h3, h5, [2, 3]), (h2, h4, [4, 5]))
    for source, target, _ in pairs:
        source.cmd("ping -n -c 1 -W 1 " + target.IP())
    hosts = {h["mac"].lower(): h for h in api("sdn/hosts")["hosts"]}
    tables = helpers["flow_tables"](topo["switches"])
    for source, target, expected in pairs:
        if source.MAC().lower() not in hosts or target.MAC().lower() not in hosts:
            print("Stopped before load: host discovery incomplete")
            return
        actual = path(tables, source, target)
        if not actual["complete"] or actual["path"] != expected or set(actual["priorities"]) != {20}:
            print("Stopped before load:", source.name, target.name, actual)
            return

    processes = {}
    result = {"samples": [], "logs": {}, "requested_bps": {"h1": 85000000, "h3": 30000000, "h2": 30000000}}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    def launch(name, host, args):
        stream = tempfile.TemporaryFile(mode="w+t")
        try:
            proc = host.popen(["iperf"] + args, stdout=stream, stderr=subprocess.STDOUT)
        except BaseException:
            stream.close()
            raise
        processes[name] = proc, stream
        return proc

    def stop(proc):
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)

    def client(host, target, port, seconds):
        return launch(host.name, host, ["-u", "-c", target.IP(), "-p", port,
                      "-b", str(result["requested_bps"][host.name]), "-t", str(seconds)])

    start = time.monotonic()
    switched = None
    try:
        for host, port in ((h6, "5606"), (h5, "5605"), (h4, "5604")):
            launch(host.name, host, ["-s", "-u", "-p", port])
        time.sleep(0.5)
        if any(proc.poll() is not None for proc, _ in processes.values()):
            raise RuntimeError("Receiver failed to start")
        background = client(h3, h5, "5605", 65)
        client(h1, h6, "5606", 125)
        print("Stage 1: H1->H6 plus H3->H5", flush=True)
        while True:
            flows = api("flows")["flows"]
            flow = next((f for f in flows if f["src_mac"] == h1.MAC().lower()
                         and f["dst_mac"] == h6.MAC().lower()), {})
            choice = flow.get("path_selection", {})
            ports = api("sdn/bandwidth")["ports"]
            congested = [[p["switch"], p["neighbor"]] for p in ports if p.get("congested")]
            actual = path(helpers["flow_tables"](topo["switches"]), h1, h6)
            elapsed = round(time.monotonic() - start, 3)
            result["samples"].append(dict(t=elapsed, forwarding=actual, flow=flow, congested=congested))
            print("t=%ss path=%s priority=%s congested=%s improvement_pp=%s" %
                  (elapsed, actual["path"], actual["priorities"], congested,
                   choice.get("improvement_pp")), flush=True)
            if switched is None:
                if actual["complete"] and actual["path"] == [1, 4, 5, 6] and set(actual["priorities"]) == {21}:
                    switched = elapsed
                    stop(background)
                    client(h2, h4, "5604", 60)
                    print("Stage 2: background moved to S4->S5", flush=True)
                elif elapsed >= 60:
                    print("No first reroute within 60 seconds.", flush=True)
                    break
            elif (actual["complete"] and min(actual["priorities"]) > 21) or elapsed - switched >= 55:
                break
            time.sleep(2)
    except (Exception, KeyboardInterrupt) as error:
        result["error"] = repr(error)
        print("Stopped:", repr(error), flush=True)
    finally:
        for name, (proc, stream) in reversed(list(processes.items())):
            stop(proc)
            stream.seek(0)
            result["logs"][name] = stream.read()
            stream.close()
        output = folder / "results" / ("hold-down-" + stamp + ".json")
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print("Saved:", output, flush=True)


if "net" in globals():
    run_hold_down(net)
