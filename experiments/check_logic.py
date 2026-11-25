"""Offline regressions using actual method bodies; no OS-Ken/OVS emulation."""
import ast
import copy
from contextlib import redirect_stdout
import io
import json
from itertools import islice
import runpy
import statistics
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "vm-source/rest_api_controller.py"


def methods(*names):
    tree = ast.parse(SOURCE.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    nodes = [copy.deepcopy(node) for node in cls.body
             if isinstance(node, ast.FunctionDef) and node.name in names]
    for node in nodes:
        node.decorator_list = []
    scope = {"time": time}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), scope)
    return scope


class LogicChecks(unittest.TestCase):
    def test_missing_bandwidth_is_bounded_and_never_fabricated(self):
        script = runpy.run_path(str(ROOT / "experiments/bandwidth_accuracy.py"))
        read = script["port_reading"]
        clock = SimpleNamespace(now=0)

        def sleep(seconds):
            clock.now += seconds

        row = dict(switch=1, neighbor=2, tx_mbps=5.1)
        with patch.dict(read.__globals__, time=SimpleNamespace(
                monotonic=lambda: clock.now, sleep=sleep)):
            api = Mock(side_effect=[dict(ports=[]), dict(ports=[row])])
            self.assertEqual(read(api, [1, 2], 3), row)
            self.assertEqual(clock.now, 1)
            api = Mock(return_value=dict(ports=[dict(switch=2, neighbor=3)]))
            with self.assertRaisesRegex(RuntimeError, "Missing bandwidth for S1 -> S2"):
                read(api, [1, 2], 3)
            self.assertEqual(clock.now, 3)

    def test_topologies_and_grid_port_order(self):
        class Topology:
            def __init__(self):
                self.switches, self.hosts, self.links, self.ports = [], [], [], {}
                self.build()

            def addSwitch(self, name):
                self.switches.append(name)
                return name

            def addHost(self, name):
                self.hosts.append(name)
                return name

            def addLink(self, a, b, **options):
                for node in (a, b):
                    self.ports[node] = self.ports.get(node, 0) + 1
                self.links.append((a, b, dict(options), self.ports[a], self.ports[b]))

        tree = ast.parse((ROOT / "vm-source/custom_topology.py").read_text())
        tree.body = [node for node in tree.body if not isinstance(node, ast.ImportFrom)]
        scope = {"Topo": Topology, "TCLink": object, "TCIntf": object}
        exec(compile(tree, "custom_topology.py", "exec"), scope)
        for name, switches, hosts, trunks in [("MyNetwork", 6, 6, 7), ("FatTree4", 20, 16, 32)]:
            topo = scope[name]()
            self.assertEqual(len(topo.switches), switches)
            self.assertEqual(len(topo.hosts), hosts)
            links = [row for row in topo.links if row[0].startswith("s") and row[1].startswith("s")]
            self.assertEqual(len(links), trunks)
            self.assertTrue(all(row[2]["bw"] == 100 and row[2]["delay"] == "2ms" for row in links))
            self.assertTrue(all(row[2]["cls"] is scope["LabTCLink"] for row in links))
        grid = scope["MyNetwork"]()
        self.assertEqual([(a, b, pa, pb) for a, b, _, pa, pb in grid.links[:3]],
                         [("s1", "s2", 1, 1), ("s2", "s3", 2, 1), ("s3", "s6", 2, 1)])

    def test_htb_burst_preserves_rate_parent_and_other_shapers(self):
        class Interface:
            def bwCmds(self, *args, **kwargs):
                return kwargs["commands"], " parent 5:1 "

        class Link:
            def __init__(self, **kwargs):
                self.interfaces = (kwargs.get("cls1", Interface),
                                   kwargs.get("cls2", Interface))

        tree = ast.parse((ROOT / "vm-source/custom_topology.py").read_text())
        tree.body = [node for node in tree.body if isinstance(node, ast.ClassDef)
                     and node.name in ("LabTCIntf", "LabTCLink")]
        scope = {"TCIntf": Interface, "TCLink": Link}
        exec(compile(tree, "custom_topology.py", "exec"), scope)
        intf = scope["LabTCIntf"]()
        commands = ["%s class add dev %s parent 5:0 classid 5:1 htb rate 100.000000Mbit burst 15k",
                    "%s qdisc add dev %s root handle 5: tbf rate 100Mbit burst 15000 latency 1ms"]
        updated, parent = intf.bwCmds(commands=commands)
        self.assertEqual(updated[0], commands[0].replace("burst 15k", "burst 64k cburst 64k"))
        self.assertEqual(updated[1], commands[1])
        self.assertEqual(parent, " parent 5:1 ")
        self.assertEqual(scope["LabTCLink"]().interfaces,
                         (scope["LabTCIntf"], scope["LabTCIntf"]))

    def test_host_pair_rate_counts_only_ingress(self):
        update = methods("update_flow_details")["update_flow_details"]
        controller = SimpleNamespace(
            hosts={"a": {"switch": 1, "port": 3}}, flow_detail_snapshot={},
            flow_details={}, flow_sample_time={}, installed_paths={},
            route_priorities={}, logger=Mock(), evaluate_paths=Mock(return_value={}))
        flow = SimpleNamespace(match={"eth_src": "a", "eth_dst": "b", "in_port": 3},
                               duration_sec=0, duration_nsec=0, byte_count=0)
        for duration, count in [(0, 0), (5, 7_500_000), (10, 15_000_000)]:
            flow.duration_sec, flow.byte_count = duration, count
            update(controller, SimpleNamespace(id=1), [flow])
        self.assertTrue(controller.flow_details[1][0]["elephant"])
        self.assertEqual(controller.flow_details[1][0]["rate_mbps"], 12)
        update(controller, SimpleNamespace(id=2), [flow])
        self.assertEqual(controller.flow_details[2], [])
        flow.byte_count = 0
        flow.duration_sec = 1
        update(controller, SimpleNamespace(id=1), [flow])
        self.assertIsNone(controller.flow_details[1][0]["rate_mbps"])
        self.assertFalse(controller.flow_details[1][0]["elephant"])

    def test_switch_leave_removes_state_and_rebuilds(self):
        remove = methods("switch_removed")["switch_removed"]
        c = SimpleNamespace(
            datapaths={1: "gone", 2: "live"}, switch_ports={1: {1}},
            flow_data={1: {}}, flow_snapshot={1: (0, 0)},
            graph=Mock(has_node=Mock(return_value=True)),
            hosts={"a": {"switch": 1}, "b": {"switch": 2}},
            arp_table={"10.0.0.1": "a", "10.0.0.2": "b"},
            pending_arp={"x": [{"switch": 1}, {"switch": 2}]},
            rebuild_routes=Mock(), logger=Mock())
        remove(c, SimpleNamespace(switch=SimpleNamespace(dp=SimpleNamespace(id=1))))
        self.assertEqual(c.datapaths, {2: "live"})
        self.assertEqual(c.arp_table, {"10.0.0.2": "b"})
        self.assertEqual(c.pending_arp["x"], [{"switch": 2}])
        c.rebuild_routes.assert_called_once()

    def test_hold_down_and_improvement_gate(self):
        move = methods("maybe_reroute")["maybe_reroute"]
        c = SimpleNamespace(
            reroute_state=None, last_reroute={("a", "b"): time.monotonic()},
            graph={1: {2: {"ports": {1: 1}}}}, link_load={(1, 1): (.8, 2)},
            hosts={"a": {}, "b": {}}, datapaths={1: None, 2: None, 3: None},
            route_priorities={}, path_hops=Mock(return_value=[(1, 3, 1), (2, 1, 3)]),
            send_reroute_hop=Mock())
        choice = dict(ready=True, current_path=[1, 2], best_path=[1, 3, 2],
                      improvement_pp=20)
        move(c, "a", "b", choice)
        c.send_reroute_hop.assert_not_called()
        c.last_reroute.clear()
        move(c, "a", "b", dict(choice, improvement_pp=14.99))
        c.send_reroute_hop.assert_not_called()
        move(c, "a", "b", choice)
        self.assertEqual(c.reroute_state["priority"], 21)
        self.assertEqual(c.reroute_state["new_hops"], [(2, 1, 3), (1, 3, 1)])
        c.send_reroute_hop.assert_called_once()

    def test_projected_bottleneck_prefers_unshared_path_and_rejects_stale_data(self):
        funcs = methods("evaluate_paths", "ingress_demands")
        evaluate = funcs["evaluate_paths"]
        paths = [[1, 2, 3, 6], [1, 2, 5, 6], [1, 4, 5, 6]]

        class Graph(dict):
            def has_edge(self, a, b):
                return b in self.get(a, {})

        c = SimpleNamespace(graph=Graph(), installed_paths={("a", "b"): paths[0],
                            ("x", "y"): [2, 3]}, bandwidth_data={}, port_sample_time={},
                            poll_interval=5, flow_details={2: [
                                dict(src_mac="x", dst_mac="y", rate_mbps=30)]},
                            flow_sample_time={2: time.monotonic()})
        for path in paths:
            for a, b in zip(path, path[1:]):
                c.graph.setdefault(a, {})[b] = {"ports": {a: b}}
                c.bandwidth_data[(a, b)] = dict(neighbor=b, tx_mbps=0, capacity_mbps=100)
                c.port_sample_time[(a, b)] = time.monotonic()
        c.ingress_demands = lambda *args: funcs["ingress_demands"](c, *args)
        with patch.dict(evaluate.__globals__, nx=SimpleNamespace(
                shortest_simple_paths=lambda *args: iter(paths)), islice=islice):
            choice = evaluate(c, "a", "b", 85)
            self.assertEqual(choice["best_path"], paths[2])
            self.assertAlmostEqual(choice["improvement_pp"], 30)
            c.port_sample_time[(1, 4)] = time.monotonic() - 11
            self.assertFalse(evaluate(c, "a", "b", 85)["ready"])

    def test_barrier_must_match_switch_and_transaction(self):
        reply = methods("reroute_barrier_reply")["reroute_barrier_reply"]
        c = SimpleNamespace(reroute_state={"barrier": (6, 10), "index": 0},
                            send_reroute_hop=Mock())
        for switch, xid in [(5, 10), (6, 11), (6, 10)]:
            reply(c, SimpleNamespace(msg=SimpleNamespace(
                datapath=SimpleNamespace(id=switch), xid=xid)))
        self.assertEqual(c.reroute_state["index"], 1)
        c.send_reroute_hop.assert_called_once()

    def test_old_rules_deleted_only_after_all_new_barriers(self):
        functions = methods("send_reroute_hop", "reroute_barrier_reply")
        calls = []
        datapaths = {}
        for switch in (1, 6):
            dp = SimpleNamespace(
                ofproto_parser=SimpleNamespace(
                    OFPBarrierRequest=lambda dp: SimpleNamespace(xid=100)),
                set_xid=lambda barrier: None,
                send_msg=lambda msg, switch=switch: calls.append(("barrier", switch)))
            datapaths[switch] = dp
        c = SimpleNamespace(
            reroute_state=dict(src="a", dst="b", new_path=[1, 6],
                               new_hops=[(6, 1, 3), (1, 3, 1)],
                               old_hops=[(1, 3, 2), (6, 2, 3)], old_priority=20,
                               priority=21, index=0, sent_hops=[], requests=set(),
                               improvement_pp=20, old_path=[1, 2, 6]),
            datapaths=datapaths, installed_paths={}, route_priorities={}, last_reroute={},
            trace_detection=False, logger=Mock())
        c.install_flow = lambda dp, *args, **kwargs: calls.append(("install", args)) or 99
        c.delete_path_rule = lambda *args: calls.append(("delete", args[1]))
        c.send_reroute_hop = lambda: functions["send_reroute_hop"](c)
        c.send_reroute_hop()
        for switch in (6, 1):
            self.assertFalse(any(kind == "delete" for kind, _ in calls))
            functions["reroute_barrier_reply"](c, SimpleNamespace(
                msg=SimpleNamespace(datapath=SimpleNamespace(id=switch), xid=100)))
        self.assertEqual(sum(kind == "delete" for kind, _ in calls), 2)
        self.assertEqual(c.installed_paths[("a", "b")], [1, 6])
        self.assertIsNone(c.reroute_state)

    def test_saved_accuracy_is_reproducible(self):
        data = json.loads((ROOT / "experiments/results/accuracy-20261119T201236Z.json").read_text())
        rate = runpy.run_path(str(ROOT / "experiments/bandwidth_accuracy.py"))["sender_mbps"]
        errors = []
        for trial in data["trials"]:
            sender = rate("iperf3", trial["sender_output"])
            monitor = statistics.mean(row["tx_mbps"] for row in trial["samples"])
            errors.append(abs(monitor - sender) / sender * 100)
        self.assertEqual(len(errors), 5)
        self.assertAlmostEqual(statistics.mean(errors), 3.024752187391, places=8)
        self.assertLess(max(errors), 10)

    def test_accuracy_scores_completed_window_when_final_lookup_fails(self):
        script = runpy.run_path(str(ROOT / "experiments/bandwidth_accuracy.py"))
        run = script["run"]
        previous = json.loads((ROOT / "experiments/results/accuracy-20261119T201236Z.json").read_text())
        final = previous["trials"][-1]
        previous["trials"] = previous["trials"][:4]
        previous["target"] = "h6"

        def process(args, stdout, **kwargs):
            if "-c" in args:
                stdout.write(final["sender_output"])
                stdout.flush()
            return Mock(poll=Mock(return_value=None), wait=Mock(return_value=0))

        source = Mock(MAC=Mock(return_value="a"), popen=process)
        target = Mock(MAC=Mock(return_value="b"), IP=Mock(return_value="10.0.0.16"), popen=process)
        route = dict(complete=True, path=[1, 9, 17, 15, 8])
        trace = Mock(side_effect=[route, route, route, route, ValueError("No route")])

        def api(path):
            if path == "topology":
                return dict(switches=[1, 9], links=[])
            if path == "sdn/hosts":
                return dict(hosts=[dict(mac="a"), dict(mac="b")])
            return dict(ports=[dict(switch=1, neighbor=9, tx_mbps=5.15)])

        helpers = dict(api=api, forwarding_path=trace, flow_tables=Mock(return_value={}))
        clock = SimpleNamespace(now=0)

        def sleep(seconds):
            clock.now += seconds

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "results").mkdir()
            (root / "results/previous.json").write_text(json.dumps(previous))
            with patch.dict(run.__globals__, EXPERIMENTS=root,
                            time=SimpleNamespace(monotonic=lambda: clock.now, sleep=sleep)):
                with patch.object(run.__globals__["runpy"], "run_path", return_value=helpers):
                    with patch.object(run.__globals__["shutil"], "which", return_value="iperf3"):
                        with redirect_stdout(io.StringIO()):
                            run(dict(h1=source, h6=target), "previous.json", target_name="h6")
            output = next(p for p in (root / "results").glob("accuracy-*.json"))
            report = json.loads(output.read_text())
            self.assertEqual(len(report["trials"]), 5)
            self.assertNotIn("error", report)
            self.assertIn("final_path_warning", report["trials"][-1])
            self.assertIn("error_percent", report["trials"][-1])
            self.assertEqual(report["target"], "h6")

    def test_presentation_failure_timing_and_cleanup(self):
        run = runpy.run_path(str(ROOT / "experiments/link_failure_demo.py"))["run_link_failure_demo"]
        host = Mock(MAC=Mock(return_value="a"), IP=Mock(return_value="10.0.0.6"))
        network = Mock()
        network.__getitem__ = Mock(return_value=host)
        helpers = dict(api=Mock(side_effect=lambda path: (
            {"hosts": [dict(mac="a", switch=1, port=3)]} if path == "sdn/hosts"
            else dict(switches=[1, 6], links=[dict(source=5, destination=6)]))),
            flow_tables=Mock(return_value={}), forwarding_path=Mock(return_value=dict(
                complete=True, path=[1, 4, 5, 6], priorities=[21]*4)))
        for presentation, count, delays in [(False, 80, [2, 5]),
                                             (True, 300, [8, 5, 10, 5])]:
            host.reset_mock()
            network.reset_mock()
            clock = Mock(time=Mock(return_value=100))
            with tempfile.TemporaryDirectory() as temp:
                output = Path(temp) / "result.json"
                with patch.dict(run.__globals__, time=clock), redirect_stdout(io.StringIO()):
                    with patch.object(run.__globals__["runpy"], "run_path", return_value=helpers):
                        run(network, output_path=output, presentation=presentation)
                report = json.loads(output.read_text())
                self.assertEqual(report["requested_ping_count"], count)
                self.assertEqual([c.args[0] for c in clock.sleep.call_args_list], delays)
                self.assertEqual(network.configLinkStatus.call_args_list[0].args, ("s5", "s6", "down"))
                self.assertEqual(network.configLinkStatus.call_args_list[1].args, ("s5", "s6", "up"))


if __name__ == "__main__":
    unittest.main()
