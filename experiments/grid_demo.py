"""Run from Mininet CLI using exec(open(...).read()); no external dependencies."""
import json
import re
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def api(path):
    with urllib.request.urlopen("http://127.0.0.1:8080/" + path, timeout=3) as response:
        return json.load(response)


def port_number(value):
    value = value.strip('"')
    return int(value.rsplit("-eth", 1)[-1])


def matching_rule(table, src, dst, in_port):
    matches = []
    for line in table.splitlines():
        if "dl_src=" + src not in line or "dl_dst=" + dst not in line:
            continue
        priority = re.search(r"priority=(\d+)", line)
        incoming = re.search(r'in_port=("[^"]+"|[^,\s]+)', line)
        outgoing = re.search(r'actions=output:("[^"]+"|\d+)', line)
        if priority and incoming and outgoing and port_number(incoming.group(1)) == in_port:
            matches.append((int(priority.group(1)), port_number(outgoing.group(1))))
    return max(matches) if matches else None


def forwarding_path(tables, links, src, dst, start, end):
    neighbors = {}
    for link in links:
        a, b = link["source"], link["destination"]
        pa, pb = link["source_port"], link["destination_port"]
        neighbors[(a, pa)] = (b, pb)
        neighbors[(b, pb)] = (a, pa)
    switch, incoming = start["switch"], start["port"]
    path, priorities = [], []
    while switch not in path:
        path.append(switch)
        rule = matching_rule(tables[switch], src, dst, incoming)
        if rule is None:
            return {"path": path, "priorities": priorities, "complete": False}
        priority, outgoing = rule
        priorities.append(priority)
        if switch == end["switch"]:
            return {"path": path, "priorities": priorities,
                    "complete": outgoing == end["port"]}
        if (switch, outgoing) not in neighbors:
            break
        switch, incoming = neighbors[(switch, outgoing)]
    return {"path": path, "priorities": priorities, "complete": False}


def flow_tables(switches):
    return {n: subprocess.check_output(
        ["ovs-ofctl", "-O", "OpenFlow13", "dump-flows", "s" + str(n)],
        text=True, stderr=subprocess.STDOUT, timeout=3) for n in switches}


def run_grid_demo(host1, host3, host5, host6):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    result = {"started_utc": stamp, "duration_seconds": 60,
              "requested_rates": {"H1->H6": "85000000 bit/s", "H3->H5": "30000000 bit/s"},
              "samples": [], "process_output": {}}
    processes, streams = {}, {}
    output = Path("/media/sf_sdn_transfer/experiments/results") / ("grid-demo-" + stamp + ".json")
    try:
        topology = api("topology")
        hosts = {h["mac"].lower(): h for h in api("sdn/hosts")["hosts"]}
        src, dst = host1.MAC().lower(), host6.MAC().lower()
        bg_src, bg_dst = host3.MAC().lower(), host5.MAC().lower()
        before = flow_tables(topology["switches"])
        result["initial_flow_tables"] = before
        result["initial_path"] = forwarding_path(
            before, topology["links"], src, dst, hosts[src], hosts[dst])
        background = forwarding_path(
            before, topology["links"], bg_src, bg_dst, hosts[bg_src], hosts[bg_dst])
        result["background_path"] = background
        print("Initial H1->H6:", result["initial_path"], flush=True)
        print("Initial H3->H5:", background, flush=True)
        if (not result["initial_path"]["complete"] or not background["complete"]
                or result["initial_path"]["path"] != [1, 2, 3, 6]
                or background["path"] != [2, 3]):
            print("Stopped before traffic: initial paths do not match the required scenario.", flush=True)
            return

        def start(name, host, args):
            streams[name] = tempfile.TemporaryFile(mode="w+t")
            processes[name] = host.popen(["iperf"] + args,
                                          stdout=streams[name], stderr=subprocess.STDOUT)

        start("H6 receiver", host6, ["-s", "-u", "-p", "5506"])
        start("H5 receiver", host5, ["-s", "-u", "-p", "5505"])
        time.sleep(0.5)
        if any(p.poll() is not None for p in processes.values()):
            raise RuntimeError("An iperf receiver did not start; see saved output.")
        start("H3->H5 client", host3,
              ["-c", host5.IP(), "-u", "-b", "30000000", "-t", "60", "-p", "5505"])
        start("H1->H6 client", host1,
              ["-c", host6.IP(), "-u", "-b", "85000000", "-t", "60", "-p", "5506"])
        begin, failures = time.monotonic(), 0
        print("Two UDP flows started; samples every ~5 seconds. Ctrl+C stops this trial.", flush=True)
        while time.monotonic() - begin < 60:
            started = time.monotonic()
            sample = {"elapsed_seconds": round(started - begin, 3)}
            try:
                bandwidth, flows = api("sdn/bandwidth"), api("flows")
                sample["bandwidth"], sample["flows"] = bandwidth, flows
                link = next((p for p in bandwidth["ports"]
                             if p["switch"] == 2 and p.get("neighbor") == 3), {})
                flow = next((f for f in flows["flows"]
                             if f["src_mac"] == src and f["dst_mac"] == dst), {})
                choice = flow.get("path_selection", {})
                print("t=%.0fs EWMA=%s%% congested=%s elephant=%s current=%s priority=%s best=%s" % (
                    sample["elapsed_seconds"], link.get("ewma_utilization_percent"),
                    link.get("congested"), flow.get("elephant"),
                    flow.get("installed_path", choice.get("current_path")),
                    flow.get("installed_priority"), choice.get("best_path")), flush=True)
                failures = 0
            except Exception as error:
                sample["error"] = str(error)
                failures += 1
                print("API sample failed:", error, flush=True)
            result["samples"].append(sample)
            if failures >= 3:
                raise RuntimeError("Three consecutive API failures; stopping traffic.")
            time.sleep(max(0, 5 - (time.monotonic() - started)))
        for name, process in processes.items():
            if name.endswith("client"):
                process.wait(timeout=12)
        after = flow_tables(topology["switches"])
        result["final_flow_tables"] = after
        result["final_path"] = forwarding_path(
            after, topology["links"], src, dst, hosts[src], hosts[dst])
        print("Final H1->H6:", result["final_path"], flush=True)
    except KeyboardInterrupt:
        result["interrupted"] = True
        print("Trial interrupted; stopping only processes created by this script.", flush=True)
    except Exception as error:
        result["error"] = str(error)
        print("Trial stopped:", error, flush=True)
    finally:
        for name, process in processes.items():
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            streams[name].seek(0)
            text = streams[name].read()
            result["process_output"][name] = text
            result.setdefault("return_codes", {})[name] = process.returncode
            streams[name].close()
            if name.endswith("client"):
                print("\n" + name + ":\n" + text, flush=True)
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print("Saved raw trial results:", output, flush=True)
        except OSError as error:
            print("Could not save results:", error, flush=True)


if all(name in globals() for name in ("h1", "h3", "h5", "h6")):
    run_grid_demo(h1, h3, h5, h6)
