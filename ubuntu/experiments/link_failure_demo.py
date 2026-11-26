"""Lightweight link-failure trial, launched explicitly from Mininet CLI."""
import json
import re
import runpy
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# Legacy Mininet exec(open(...)) calls have no __file__; runpy supplies it.
EXPERIMENTS = Path(globals().get("__file__", "/media/sf_sdn_transfer/experiments/link_failure_demo.py")).resolve().parent


def ping_summary(text):
    match = re.search(r"(\d+) packets transmitted, (\d+) received, ([\d.]+)% packet loss", text)
    summary = None if match is None else {
        "transmitted": int(match.group(1)), "received": int(match.group(2)),
        "packet_loss_percent": float(match.group(3))}
    replies = [float(m.group(1)) for m in re.finditer(
        r"^\[(\d+(?:\.\d+)?)\].*bytes from", text, re.MULTILINE)]
    gaps = [b - a for a, b in zip(replies, replies[1:])]
    return {"summary": summary,
            "largest_reply_gap_seconds": round(max(gaps), 6) if gaps else None}


def first_post_cut_reply_ms(text, requested, confirmed, restored):
    # ping -D timestamps replies. Subtract the reported RTT to exclude
    # requests already in flight at the end of configLinkStatus().
    pattern = r"^\[([\d.]+)\].*bytes from .*icmp_seq=\d+.*time=([\d.]+) ms"
    replies = [(float(t), float(rtt)) for t, rtt in re.findall(pattern, text, re.MULTILINE)]
    if not any(t < requested for t, _ in replies):
        return None
    for received, rtt in replies:
        if received - rtt / 1000 > confirmed and received < restored:
            return round(1000 * (received - requested), 3)
    return None


def run_link_failure_demo(network, source_name="h1", output_path=None, presentation=False):
    helpers = runpy.run_path(str(EXPERIMENTS / "grid_demo.py"))
    api = helpers["api"]
    tables = helpers["flow_tables"]
    trace = helpers["forwarding_path"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = output_path or (EXPERIMENTS / "results") / ("link-failure-" + stamp + ".json")
    managed = source_name == "h1"
    expected = [1, 4, 5, 6] if managed else [4, 5, 6]
    interval, count = (0.2, 80) if managed else (0.05, 260)
    if presentation:
        interval, count = 0.2, 300
    result = {"started_utc": stamp, "failed_link": [5, 6],
              "source": source_name, "destination": "h6",
              "ping_interval_seconds": interval, "requested_ping_count": count}
    result["presentation_mode"] = presentation
    link_down, process = False, None
    stream = tempfile.TemporaryFile(mode="w+t")
    try:
        source, target = network[source_name], network["h6"]
        src, dst = source.MAC().lower(), target.MAC().lower()
        hosts = {h["mac"].lower(): h for h in api("sdn/hosts")["hosts"]}

        def snapshot():
            topology = api("topology")
            flows = tables(topology["switches"])
            return {"topology": topology, "flow_tables": flows,
                    "forwarding": trace(flows, topology["links"], src, dst,
                                        hosts[src], hosts[dst])}

        result["before"] = snapshot()
        before = result["before"]["forwarding"]
        print("Before failure:", before, flush=True)
        if (not before["complete"] or before["path"] != expected
                or (managed and not all(priority > 20 for priority in before["priorities"]))):
            print("Stopped: unexpected initial forwarding path.", flush=True)
            return
        if not any({link["source"], link["destination"]} == {5, 6}
                   for link in result["before"]["topology"]["links"]):
            print("Stopped: S5-S6 is not in the current topology.", flush=True)
            return
        process = source.popen(["ping", "-n", "-D", "-c", str(count), "-i", str(interval), target.IP()],
                               stdout=stream, stderr=subprocess.STDOUT)
        if presentation:
            print("Presentation mode: about 60s of ping; link down for at least 15s.", flush=True)
        time.sleep(8 if presentation else 2)
        print("Taking S5-S6 down; ping continues.", flush=True)
        result["link_down_requested_unix"] = time.time()
        link_down = True
        network.configLinkStatus("s5", "s6", "down")
        result["link_down_command_returned_unix"] = time.time()
        time.sleep(5)
        result["while_down"] = snapshot()
        print("While S5-S6 is down:", result["while_down"]["forwarding"], flush=True)
        if presentation:
            time.sleep(10)
        print("Restoring S5-S6.", flush=True)
        result["link_up_requested_unix"] = time.time()
        network.configLinkStatus("s5", "s6", "up")
        link_down = False
        result["link_up_command_returned_unix"] = time.time()
        if presentation:
            time.sleep(5)
        else:
            process.wait(timeout=20)
        result["after"] = snapshot()
        print("After restoration:", result["after"]["forwarding"], flush=True)
        if presentation:
            process.wait(timeout=70)
    except KeyboardInterrupt:
        result["interrupted"] = True
        print("Interrupted; restoring the link.", flush=True)
    except Exception as error:
        result["error"] = str(error)
        print("Trial stopped:", error, flush=True)
    finally:
        if link_down:
            try:
                network.configLinkStatus("s5", "s6", "up")
                result["restored_in_cleanup"] = True
            except Exception as error:
                result["restoration_error"] = str(error)
                print("Restore failed. Run: link s5 s6 up", flush=True)
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            stream.seek(0)
            text = stream.read()
            result["ping_output"] = text
            result["ping_measurements"] = ping_summary(text)
            if "link_up_requested_unix" in result:
                result["ping_measurements"]["first_post_cut_reply_ms"] = first_post_cut_reply_ms(
                    text, result["link_down_requested_unix"],
                    result["link_down_command_returned_unix"], result["link_up_requested_unix"])
            print("\n" + "\n".join(text.splitlines()[-5:]), flush=True)
            print("Largest observed reply gap (not exact recovery time):",
                  result["ping_measurements"]["largest_reply_gap_seconds"], flush=True)
        stream.close()
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print("Saved raw trial results:", output, flush=True)
        except OSError as error:
            print("Could not save results:", error, flush=True)


if "net" in globals():
    run_link_failure_demo(net, presentation=True)
