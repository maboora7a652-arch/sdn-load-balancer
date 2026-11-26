# -*- coding: utf-8 -*-
"""Chapters 3 to 6, references and appendices of the SDN Track 1 report.

Exports CHAPTERS_PART2 (list of [ch3, ch4, ch5, ch6]), REFERENCES (18 IEEE strings, numbered
[1]-[18] in the canonical order shared with content_part1) and APPENDICES (list of [appA, appB]).
All measurements come from experiments/results/ and media/video-data.json.
"""


def h2(t):
    return {"type": "h2", "text": t}


def h3(t):
    return {"type": "h3", "text": t}


def p(t):
    return {"type": "p", "text": t}


def bullets(items):
    return {"type": "bullets", "items": items}


def numbered(items):
    return {"type": "numbered", "items": items}


def callout(title, text):
    return {"type": "callout", "title": title, "text": text}


def equation(formula, number, note):
    return {"type": "equation", "formula": formula, "number": number, "note": note}


def lines(text):
    return text.strip("\n").split("\n")


def code(title, text):
    return {"type": "code", "title": title, "lines": lines(text)}


def figure(fid, file, caption, width_in=6.1, border=False):
    return {"type": "figure", "id": fid, "file": file, "caption": caption,
            "width_in": width_in, "border": border}


def table(tid, caption, headers, rows, widths):
    assert sum(widths) == 166, (tid, sum(widths))
    return {"type": "table", "id": tid, "caption": caption, "headers": headers,
            "rows": rows, "col_widths_mm": widths}


# ---------------------------------------------------------------------------
# Chapter 3: System Design
# ---------------------------------------------------------------------------
CH3 = [
    h2("3.1 System Architecture and Controller Modules"),
    p(
        "The controller is a single OS-Ken application, `HostDiscoveryController`, started by `osken-manager` "
        "with `--observe-links` and limited to OpenFlow 1.3. Figure 3.1 shows its modules and the events that "
        "connect them. Events from `os_ken.topology.switches` (switch enter, link add, link delete, host add) "
        "keep a NetworkX graph whose edges record the port number at each end. Packet-in messages go to a "
        "proxy ARP module that answers requests from the controller itself, so no ARP broadcast crosses the "
        "grid, and the first resolved ARP exchange for a destination triggers the route installer. The "
        "installer walks the chosen path and writes one IPv4 rule per hop that matches the ingress port, the "
        "Ethernet source and the Ethernet destination."
    ),
    figure(
        "Figure 3.1", "fig_3_1_controller_modules.png",
        "Figure 3.1: OS-Ken controller modules and the events between them, from LLDP discovery and proxy ARP "
        "to the statistics poller, the path selector, the make-before-break engine, the REST API and the "
        "local dashboard.",
    ),
    p(
        "A monitoring green thread polls every switch each T seconds (5 s by default, configurable from 2 to "
        "5 s through `SDN_POLL_INTERVAL`). Port statistics feed the utilization and EWMA computation. Flow "
        "statistics feed the host-pair rate and elephant counters. Both end in dictionaries that the REST "
        "handler serves. In `balanced` mode the same thread then calls the path evaluator and, when its "
        "conditions hold, the make-before-break engine. The REST server runs in a second green thread on "
        "`127.0.0.1:8080`, and the dashboard is a separate Python process on port 8081 that reads the REST "
        "API. The controller keeps its state in memory only. The switches hold nothing but their flow "
        "tables."
    ),
    h2("3.2 Network Topologies and Link Model"),
    p(
        "Both topologies are Mininet `Topo` subclasses in `vm-source/custom_topology.py`. The lab grid "
        "(`MyNetwork`) has six OpenFlow switches S1 to S6 and six hosts H1 to H6 with MAC addresses "
        "`00:00:00:00:00:01` to `00:00:00:00:00:06` (Mininet's `--mac` option) and IP addresses `10.0.0.1` to "
        "`10.0.0.6`. Seven inter-switch links form the 2×3 grid of Figure 3.2(a): S1-S2, S2-S3, S3-S6, S6-S5, "
        "S2-S5, S4-S5 and S1-S4. The grid has no S4-S6 link and no S2-S4 link, and the controller treats the "
        "grid as complete only when discovery reports exactly six switches and seven links. Each "
        "inter-switch link is a `LabTCLink` with 100 Mbps capacity and 2 ms delay. Host links are unshaped."
    ),
    p(
        "Mininet numbers the ports of a switch in the order of the `addLink` calls, so the port map in Table "
        "3.1 follows from the topology file: inter-switch ports come first and the host port comes last. The "
        "controller does not assume these numbers. It reads them from LLDP, and they match the port numbers "
        "returned by the `/topology` endpoint. Three paths of equal length join H1 to H6: P1 = S1-S2-S3-S6, "
        "P2 = S1-S2-S5-S6 and P3 = S1-S4-S5-S6. A static shortest-path controller sends H1 to H6 over P1, "
        "and P1 crosses the S2-S3 link that also carries traffic from H3 to H5. That overlap is the "
        "contention scenario of the Track 1 demonstration."
    ),
    figure(
        "Figure 3.2", "fig_3_2_topologies.png",
        "Figure 3.2: (a) The 2×3 lab grid with port numbers, host attachments and the three equal-length "
        "paths from H1 to H6. (b) The k=4 fat-tree with 4 core, 8 aggregation and 8 edge switches, 16 hosts "
        "and 32 inter-switch links.",
    ),
    table(
        "Table 3.1",
        "Table 3.1: Grid port and host mapping. Each cell names the device reached through that port.",
        ["Switch", "Port 1", "Port 2", "Port 3", "Port 4"],
        [
            ["S1", "S2", "S4", "H1", "unused"],
            ["S2", "S1", "S3", "S5", "H3"],
            ["S3", "S2", "S6", "H5", "unused"],
            ["S4", "S5", "S1", "H2", "unused"],
            ["S5", "S6", "S2", "S4", "H4"],
            ["S6", "S3", "S5", "H6", "unused"],
        ],
        [26, 35, 35, 35, 35],
    ),
    p(
        "The second topology is the k=4 fat-tree (`FatTree4`). Four pods each hold two edge and two "
        "aggregation switches, which gives 8 edge switches (S1 to S8), 8 aggregation switches (S9 to S16) "
        "and 4 core switches (S17 to S20), 20 switches in all. Each edge switch serves two hosts, so the "
        "network has 16 hosts, H1 to H16, and 32 inter-switch links: 16 between edge and aggregation "
        "switches and 16 between aggregation and core switches. Every one of them is shaped like a grid "
        "link. Two hosts in different pods have four equal-cost paths, which makes the fat-tree the natural "
        "test for ECMP and for discovery at larger scale. The controller accepts ARP traffic only after it "
        "has found all 20 switches and 32 links."
    ),
    p(
        "The link model matters for the experiments. `LabTCLink` replaces the default HTB burst of 15 KB with "
        "a `burst` and `cburst` of 64 KB so that the shaper can catch up after scheduling delays in the virtual "
        "machine. After this change, `tc class show` on `s1-eth1` reports `65512b`. Section 5.8 shows what "
        "happens to LLDP discovery when no shaping is applied."
    ),
    h2("3.3 Traffic Monitoring, Elephant Filtering, and Congestion Detection"),
    p(
        "OpenFlow port and flow counters are cumulative, so every rate comes from two successive readings. "
        "For the directed link from switch u to switch v, the controller takes the transmit counter of the "
        "port on u that faces v and computes the utilization in Equation (3.1). Here Δt is the controller "
        "time between the two statistics replies and C is the link capacity, 100 Mbps. A negative delta, "
        "which means a counter reset, discards the sample."
    ),
    equation(
        "U(u, v) = (Δtx_{bytes} × 8) / (Δt × C)", "(3.1)",
        "Directional port TX utilization. Each direction of a link is measured at the sending port, so a "
        "byte is never counted at both ends.",
    ),
    p(
        "Raw utilization fluctuates from one sample to the next, so the congestion test uses the smoothed "
        "value of Equation (3.2). The first sample seeds the average. A link counts as congested after its "
        "smoothed utilization exceeds θ = 70% in 2 consecutive periods, and one period at or below θ resets "
        "the count."
    ),
    equation(
        "E_{t} = α · U_{t} + (1 − α) · E_{t−1},   α = 0.5,   congested if E_{t} > θ = 70% for 2 periods", "(3.2)",
        "EWMA smoothing of the directional utilization of Equation (3.1).",
    ),
    p(
        "Flow statistics provide the second signal. Only IPv4 rules at priority 20 or higher that match an "
        "Ethernet source address are counted, and only at the ingress switch of the directed host pair, so "
        "a packet that crosses four switches contributes to one rate. The rate comes from the byte count "
        "and the duration reported by the switch. A pair is an elephant when its ingress rate exceeds "
        "10 Mbps, which is 10% of the 100 Mbps capacity, in 2 consecutive periods."
    ),
    p(
        "When a link is congested and an elephant crosses it, the controller scores candidate paths. It "
        "takes up to k = 3 shortest simple paths between the ingress and egress switches of the pair and "
        "computes the bottleneck each path would have after the move, Equation (3.3). Candidates are "
        "ordered by that cost at 0.001 percentage-point resolution, then by hop count, then by the number "
        "of links shared with the current path."
    ),
    equation(
        "Cost(P) = max_{e ∈ P} [ U_{est}(e) + (r_{f} / C_{e}) · I(e ∉ P_{old}) ]", "(3.3)",
        "Projected bottleneck of candidate path P. U_{est}(e) = max(TX(e), D(e)) / C_{e}, where TX(e) is the "
        "measured port TX of Equation (3.1), D(e) is the summed ingress rate of all installed host-pair "
        "routes that cross e, r_{f} is the elephant's ingress rate, and I(·) is 1 for links that are not on "
        "the current path P_{old}.",
    ),
    callout(
        "Measured load and offered load",
        "The C4 values served by `/sdn/bandwidth` are measured port TX, which is what the link actually "
        "carried. A saturated link that drops packets reports at most its shaped rate, so measured TX alone "
        "would make a congested path look cheaper than it is. The path cost of Equation (3.3) therefore "
        "uses the larger of measured TX and the offered ingress demand. The two numbers answer different "
        "questions, and the report never mixes them.",
    ),
    p(
        "A move needs one more check. Equation (3.4) compares the bottleneck of the current path with the "
        "bottleneck of the best candidate and enforces the per-flow hold-down. The decision is skipped for "
        "a round when any switch's statistics are older than 2T."
    ),
    equation(
        "Cost(P_{old}) − Cost(P_{new}) ≥ 15 pp   and   t − t_{last}(f) ≥ 30 s", "(3.4)",
        "Hysteresis gate. t_{last}(f) is the commit time of the last move of the directed pair f. A topology "
        "rebuild does not clear it.",
    ),
    h2("3.4 Path Selection, Make-Before-Break Rerouting, and Fault Recovery"),
    p(
        "Listing 3.1 condenses the decision loop, and Figure 3.3 shows the same logic as a flowchart. The "
        "controller decides once per polling round, starting with the elephant that has the highest rate, "
        "and at most one directed pair is in transition at a time."
    ),
    code(
        "Listing 3.1: Decision loop of the balanced mode (pseudocode)",
        r"""
every T seconds:
    request FlowStats and PortStats from every switch
    for each inter-switch port (u, v):                     # Eq. 3.1 and 3.2
        U = delta_tx * 8 / (delta_t * C);  E = 0.5 * U + 0.5 * E_prev
        streak = streak + 1 if E > theta else 0
    for each host-pair rule, at its ingress switch only:
        r = delta_bytes * 8 / delta_t
        elephant = (r > 10 Mbps for 2 consecutive periods)

rebalance():                                               # once per round, balanced mode
    if a move is in progress or any statistics are older than 2T: return
    for f in elephants sorted by rate, highest first:
        if no link of P_old(f) has streak >= 2: continue
        candidates = first 3 shortest simple paths ingress -> egress
        cost(P) = max over e in P of (L(e) + r_f if e not in P_old else L(e)) / C   # Eq. 3.3
        P_new = candidate with the smallest (cost, hops, links shared with P_old)
        if P_new == P_old or cost(P_old) - cost(P_new) < 15 pp: continue
        if now - last_move(f) < 30 s: continue                                        # Eq. 3.4
        make_before_break(f, P_old, P_new)
        return                                             # one move per round

make_before_break(f, P_old, P_new):
    prio = priority(P_old) + 1
    for switch in reversed(P_new):                         # egress first, ingress last
        send FLOW_MOD(priority = prio, in_port, eth_src, eth_dst, output)
        send BARRIER_REQUEST; wait for BARRIER_REPLY with the same switch and xid
        on OFPT_ERROR, disconnect, topology change or 10 s timeout:
            delete the rules already sent at prio; abort
    for switch in P_old:
        send FLOW_MOD(OFPFC_DELETE_STRICT, priority = prio - 1, same match)
    last_move(f) = now
""",
    ),
    figure(
        "Figure 3.3", "fig_3_3_lb_flowchart.png",
        "Figure 3.3: Decision flowchart of the load balancer, from statistics polling through congestion "
        "and elephant tests, k=3 path scoring and the hysteresis gate to the make-before-break update.",
    ),
    p(
        "Figure 3.4 shows the OpenFlow exchange when H1 to H6 moves from P1 to P3. The controller writes the "
        "new rules at priority 21, one above the installed rules, starting at the egress switch S6 and "
        "walking back through S5 and S4 to the ingress switch S1. After each `FLOW_MOD` it sends a "
        "`BARRIER_REQUEST` and waits for the `BARRIER_REPLY` that carries the same switch and transaction "
        "identifier before it contacts the next switch. Until the rule on S1 exists, no packet enters the "
        "new path, so no packet reaches a switch that lacks a matching entry. The new S1 rule takes effect "
        "the moment it is installed, because it outranks the old rule with the same match. Only after S1 "
        "has acknowledged does the controller remove the old priority-20 rules on S1, S2, S3 and S6 with "
        "`OFPFC_DELETE_STRICT`."
    ),
    figure(
        "Figure 3.4", "fig_3_4_mbb_sequence.png",
        "Figure 3.4: Make-before-break sequence for H1 to H6 moving from P1 to P3: FLOW_MOD at priority 21 "
        "and BARRIER_REQUEST/REPLY on S6, S5, S4 and S1, then OFPFC_DELETE_STRICT at priority 20, with the "
        "rollback branch for an error or a barrier timeout.",
    ),
    p(
        "The update has a rollback path. An OpenFlow error that carries the transaction identifier of one of "
        "the requests, a switch disconnect, a topology change, or a barrier that has not arrived after 10 s "
        "all call the same abort routine. It deletes the priority-21 rules already sent and leaves the "
        "installed route untouched. The move applies to one directed host pair. The reverse direction keeps "
        "its priority-20 rules, which matches the per-direction rate measurement."
    ),
    p(
        "The controller starts in one of three routing modes, set by `SDN_ROUTING_MODE`. In `shortest` mode each "
        "pair stays on its initial Dijkstra path, computed on a canonically ordered graph so that ties "
        "between equal-length paths resolve identically on every run. In `ecmp` mode the initial path is "
        "picked among all shortest paths by a SHA-256 hash of the sorted MAC pair, the same in both "
        "directions, which spreads flows at installation time without any measurement. In `balanced` mode the "
        "initial path is the shortest one, and the logic above can move it later."
    ),
    p(
        "Fault recovery uses the same discovery events. When OS-Ken reports a link delete, the controller "
        "removes the edge from the graph and calls `rebuild_routes`. That routine aborts a pending move, "
        "clears the measurement state, deletes every IPv4 rule on every switch, and reinstalls "
        "priority-20 shortest-path rules for each known host pair on the surviving links. A link coming "
        "back triggers the same rebuild. The consequence is that managed placements are forgotten after a "
        "topology change: priorities return to 20 and traffic follows the shortest surviving path, while "
        "the 30 s hold-down timestamps stay in place."
    ),
]


# ---------------------------------------------------------------------------
# Chapter 4: Implementation
# ---------------------------------------------------------------------------
CH4 = [
    h2("4.1 Development Environment and Software Stack"),
    p(
        "Controller, switches, hosts and traffic generators all run on one Ubuntu virtual machine. Table "
        "4.1 lists the components and the settings that affect the results. The assignment allows OS-Ken as "
        "a replacement for Ryu, which does not install on Python 3.10 without changes, and POX is excluded "
        "because it speaks only OpenFlow 1.0. OS-Ken 3.1.1 has no os_ken.app.wsgi module, so the REST API "
        "uses eventlet directly: eventlet.listen opens the socket on 127.0.0.1:8080 and eventlet.wsgi "
        "serves the request handler inside a green thread of the controller."
    ),
    table(
        "Table 4.1",
        "Table 4.1: Software stack and settings of the test machine.",
        ["Component", "Version or setting", "Role"],
        [
            ["Guest OS", "Ubuntu 22.04 LTS, kernel 6.8.0-149, VirtualBox VM",
             "Runs controller, Mininet, Open vSwitch and all traffic on one machine"],
            ["Python", "3.10, virtual environment ~/sdn-lab/.venv", "Controller runtime"],
            ["OS-Ken", "3.1.1", "OpenFlow 1.3 framework (Ryu fork permitted by the assignment)"],
            ["OpenFlow", "1.3 (ofproto_v1_3; switches started with protocols=OpenFlow13)",
             "Southbound protocol"],
            ["Mininet", "2.3, mn --custom custom_topology.py --mac --link tc",
             "Emulated grid and fat-tree"],
            ["Open vSwitch", "Ubuntu package openvswitch-switch", "One software switch per node"],
            ["LabTCLink", "tc HTB 100 Mbps, netem delay 2 ms, burst 64k and cburst 64k",
             "Shaped inter-switch links"],
            ["NetworkX", "pip package", "Topology graph, Dijkstra and k shortest simple paths"],
            ["eventlet", "pip package, eventlet.wsgi on 127.0.0.1:8080", "REST server"],
            ["Dashboard", "Python http.server on 127.0.0.1:8081, static HTML, CSS and JavaScript",
             "Live view of /snapshot"],
            ["Traffic tools", "iperf 2 (UDP workloads), iperf3 3.9 (calibration), ping, Wireshark",
             "Load generation and measurement"],
        ],
        [30, 78, 58],
    ),
    h2("4.2 Controller Classes and Event Handlers"),
    p(
        "The controller code lives in vm-source/rest_api_controller.py and the topologies in "
        "vm-source/custom_topology.py. Table 4.2 maps each class and handler to the event that triggers it "
        "and the work it does. Figure 4.1 is a capture from the Ubuntu VM. It shows the Mininet grid "
        "starting in one terminal while the controller log in another reports each switch and each link "
        "with its two port numbers as LLDP discovery completes."
    ),
    table(
        "Table 4.2",
        "Table 4.2: Classes, event handlers and their responsibilities.",
        ["Class or handler", "Trigger", "Responsibility"],
        [
            ["HostDiscoveryController", "Application start",
             "Holds the graph, hosts, datapaths, snapshots and load state; spawns the monitor and REST threads"],
            ["switch_features", "EventOFPSwitchFeatures (config)",
             "Registers the datapath and installs the priority-0 table-miss rule to the controller"],
            ["switch_added, switch_removed", "EventSwitchEnter, EventSwitchLeave",
             "Adds or removes a graph node; on leave also drops its hosts and ARP entries and rebuilds routes"],
            ["link_added", "EventLinkAdd",
             "Adds an edge with both port numbers, removes false hosts learned on that port, rebuilds routes when a link returns"],
            ["link_removed", "EventLinkDelete", "Removes the edge and calls rebuild_routes"],
            ["host_added", "EventHostAdd", "Records MAC, switch and port, ignoring switch-to-switch ports"],
            ["handle_arp", "EventOFPPacketIn",
             "Learns IP to MAC, queues requests for unknown targets, probes host ports, answers as proxy ARP"],
            ["install_dynamic_route, install_flow", "First ARP resolution, rebuild",
             "Computes the shortest or ECMP path and writes one IPv4 FLOW_MOD per hop in both directions"],
            ["monitor_network", "Green thread, every T s",
             "Sends flow and port statistics requests, runs rebalance_network, aborts a move after 10 s"],
            ["port_stats_reply", "EventOFPPortStatsReply",
             "Computes RX and TX Mbps, directional utilization, EWMA, congestion streak"],
            ["flow_stats_reply, update_flow_details", "EventOFPFlowStatsReply",
             "Switch totals and ingress-only host-pair rates, elephant streak"],
            ["evaluate_paths, ingress_demands", "Called per elephant",
             "Read-only scoring of up to three candidate paths (Equation 3.3)"],
            ["maybe_reroute, send_reroute_hop, reroute_barrier_reply, reroute_error, abort_reroute",
             "Selector decision, EventOFPBarrierReply, EventOFPErrorMsg",
             "Barrier-gated egress-to-ingress update, strict deletion of old rules, rollback"],
            ["rebuild_routes", "Link or switch change",
             "Clears state, deletes IPv4 rules, reinstalls priority-20 routes"],
            ["start_rest_api, rest_application", "Green thread",
             "WSGI handler for the endpoints of Table 4.3"],
            ["LabTCIntf, LabTCLink, MyNetwork, FatTree4", "Mininet start",
             "Shaped links, 6-switch grid, k=4 fat-tree"],
            ["Dashboard (dashboard/serve.py)", "HTTP GET on port 8081",
             "Serves static files and the /snapshot proxy"],
        ],
        [50, 42, 74],
    ),
    figure(
        "Figure 4.1", "shot_grid_lldp_startup.png",
        "Figure 4.1: Mininet grid startup and live LLDP discovery on the Ubuntu VM. The controller log lists "
        "six switches and seven links with their port numbers.",
        6.1, True,
    ),
    h2("4.3 Core Implementation Fragments"),
    p(
        "Three fragments carry most of the design. They are shortened copies of the source, with elided "
        "lines marked by an ellipsis. Listing 4.1 holds the two measurement paths. In port_stats_reply the "
        "elapsed time is the controller's monotonic clock at the moment the reply arrives, and the "
        "capacity is the constant 100 Mbps of the shaped links. In update_flow_details the elapsed time is "
        "the duration the switch itself reports for the rule, which avoids reply-timing jitter, and the "
        "host and in_port check discards every copy of a rule except the one at the ingress switch."
    ),
    code(
        "Listing 4.1: Utilization with EWMA, and ingress-only host-pair accounting",
        r"""
# port_stats_reply: directional utilization on inter-switch ports
tx_mbps = (tx_change * 8) / (elapsed * 1000000)
if stat.port_no in link_ports:
    utilization = tx_mbps / 100.0
    old_ewma, old_streak = self.link_load.get(key, (utilization, 0))
    ewma = 0.5 * utilization + 0.5 * old_ewma
    streak = old_streak + 1 if ewma > self.congestion_threshold else 0
    self.link_load[key] = (ewma, streak)

# update_flow_details: count each directed host pair once, at its ingress switch
host = self.hosts.get(src)
if host is None or host["switch"] != dp.id or host["port"] != in_port:
    continue
...
elapsed = duration - old_duration
changed = stat.byte_count - old_bytes
if elapsed > 0 and changed >= 0:
    rate_mbps = changed * 8 / (elapsed * 1000000)
    if rate_mbps > 10.0:
        streak = old_streak + 1
...
"elephant": streak >= 2
""",
    ),
    p(
        "Listing 4.2 is the update engine. maybe_reroute builds the transition record, and the hop list is "
        "the new path reversed, so the first hop sent is the egress switch. send_reroute_hop installs one "
        "rule at the higher priority, sends a barrier request and records the switch and transaction "
        "identifier. Only a barrier reply that matches that pair advances the index. When all hops have "
        "been acknowledged the old rules are deleted. abort_reroute removes whatever was sent at the new "
        "priority."
    ),
    code(
        "Listing 4.2: Barrier-gated egress-to-ingress update and rollback",
        r"""
def maybe_reroute(self, src, dst, choice):
    ...
    if new_path == old_path or choice["improvement_pp"] < 15:
        return
    if time.monotonic() - self.last_reroute.get(key, float("-inf")) < 30:
        return
    ...
    self.reroute_state = {..., "priority": priority + 1,
        "old_hops": self.path_hops(old_path, src, dst),
        "new_hops": list(reversed(self.path_hops(new_path, src, dst))),
        "index": 0, "sent_hops": [], "requests": set(), "barrier": None}
    self.send_reroute_hop()

def send_reroute_hop(self):
    state = self.reroute_state
    if state["index"] == len(state["new_hops"]):
        for hop in state["old_hops"]:
            self.delete_path_rule(state, hop, state["old_priority"])   # DELETE_STRICT
        ...
        return
    switch, in_port, out_port = state["new_hops"][state["index"]]
    dp = self.datapaths.get(switch)
    state["sent_hops"].append((switch, in_port, out_port))
    xid = self.install_flow(dp, in_port, state["dst"], out_port, state["src"],
                            priority=state["priority"])
    barrier = dp.ofproto_parser.OFPBarrierRequest(dp)
    dp.set_xid(barrier)
    state["barrier"] = (switch, barrier.xid)
    dp.send_msg(barrier)

@set_ev_cls(ofp_event.EventOFPBarrierReply, MAIN_DISPATCHER)
def reroute_barrier_reply(self, ev):
    state = self.reroute_state
    if state is None or state["barrier"] != (ev.msg.datapath.id, ev.msg.xid):
        return
    state["index"] += 1
    self.send_reroute_hop()

def abort_reroute(self, reason):
    for hop in state["sent_hops"]:
        self.delete_path_rule(state, hop, state["priority"])
""",
    ),
    p(
        "Listing 4.3 shows the discovery changes. The installed OS-Ken LLDP loop can wait with no timeout "
        "when every port is due for a probe at the same moment, and discovery then stalls. The wrapper "
        "gives that wait a deadline of one per-port send period whenever ports exist and restores the "
        "original wait method when the loop returns, even after an exception. Discovery timestamps also "
        "use a monotonic clock, so a correction of the guest wall clock cannot expire links. The original "
        "10 s link timeout and the PortStatus handling are unchanged. link_removed then removes the edge "
        "and rebuilds the routes."
    ),
    code(
        "Listing 4.3: Bounded LLDP wait and route rebuild on EventLinkDelete",
        r"""
switches.time = SimpleNamespace(time=time.monotonic)
_discovery_lldp_loop = switches.Switches.lldp_loop

def _lldp_loop_with_deadline(discovery):
    lldp_event = discovery.lldp_event
    original_wait = lldp_event.wait

    def bounded_wait(timeout=None):
        if timeout is None and discovery.ports:
            timeout = discovery.LLDP_SEND_PERIOD_PER_PORT
        return original_wait(timeout=timeout)

    lldp_event.wait = bounded_wait
    try:
        return _discovery_lldp_loop(discovery)
    finally:
        lldp_event.wait = original_wait

switches.Switches.lldp_loop = _lldp_loop_with_deadline

@set_ev_cls(event.EventLinkDelete)
def link_removed(self, ev):
    src = ev.link.src.dpid
    dst = ev.link.dst.dpid
    if self.graph.has_edge(src, dst):
        self.graph.remove_edge(src, dst)
        self.logger.info("Link removed: S%s - S%s", src, dst)
        self.rebuild_routes()
""",
    ),
    p(
        "The offline test file experiments/check_logic.py runs 16 tests against the real method bodies and "
        "an exported copy of the OS-Ken discovery source. They cover the bounded wait, the monotonic "
        "clock, ingress-only counting, the hold-down and the 15-point gate, the projected-bottleneck "
        "ranking, barrier matching, and the rule that old rules are deleted only after every new barrier "
        "has returned. They do not start OS-Ken or Open vSwitch."
    ),
    h2("4.4 Northbound REST API and Live Web Dashboard"),
    p(
        "Table 4.3 lists the endpoints. The three original topology, link and flow paths under /sdn/ remain "
        "available next to the short /topology, /links and /flows forms that the assignment names. An "
        "unknown path returns 404 with a JSON error body. The dashboard process on port 8081 serves its "
        "static page and exposes /snapshot, which fetches topology, hosts, bandwidth and flows from the "
        "controller with a 2 s timeout and returns 502 if the controller does not answer. The browser asks "
        "for a new snapshot about one second after the previous request completes, while the controller's "
        "own measurements refresh every T seconds."
    ),
    table(
        "Table 4.3",
        "Table 4.3: REST endpoints of the controller (port 8080) and of the dashboard (port 8081).",
        ["Endpoint", "Content", "Main fields"],
        [
            ["GET /topology (alias /sdn/topology)", "Switches and links",
             "switches, links with source, source_port, destination, destination_port"],
            ["GET /links (alias /sdn/links)", "Link list", "count, links"],
            ["GET /flows (alias /sdn/flows)", "Switch totals and host-pair detail",
             "switches with flow_count and byte totals; flow_scope = directed_host_pair; elephant_threshold_mbps = 10; "
             "flows with rate_mbps, consecutive_periods, elephant, installed_path, installed_priority, path_selection"],
            ["GET /sdn/status", "Controller state",
             "status, topology, routing_mode, congestion_threshold_percent, switches, links, hosts"],
            ["GET /sdn/hosts", "Learned hosts", "count, hosts with ip, mac, switch, port"],
            ["GET /sdn/bandwidth", "Port rates",
             "unit = Mbps; per port rx_mbps, tx_mbps, neighbor, capacity_mbps, utilization_percent, "
             "ewma_utilization_percent, congested_periods, congested"],
            ["GET /snapshot (dashboard)", "Combined view",
             "topology, hosts, bandwidth and flows in one JSON document"],
        ],
        [44, 38, 84],
    ),
    p(
        "Figure 4.2 is an original capture from the C4 and C5 work. On the left, Mininet runs pingall and an "
        "iperf UDP transfer of 10 Mbps from H2 to H1, for which the iperf client reports 10.5 Mbits/sec. On "
        "the right, curl polls /sdn/bandwidth once per second. The JSON shows 9.674904 Mbps received on "
        "port 3 of S4, where H2 attaches, and 9.577393 Mbps transmitted on port 3 of S1, where H1 attaches. "
        "The capture checks direction and order of magnitude. The quantitative validation against iperf3 "
        "is the calibration in Section 5.2."
    ),
    figure(
        "Figure 4.2", "shot_c4_c5_bandwidth.png",
        "Figure 4.2: Mininet pingall and iperf UDP at 10 Mbps from H2 to H1 (left) next to the live "
        "/sdn/bandwidth JSON (right).",
        6.1, True,
    ),
    p(
        "Figure 4.3 shows the dashboard on the fat-tree with all 20 switches, 32 inter-switch links and 16 "
        "learned hosts. The pair H1 to H16 is selected and its installed path S1-S9-S17-S15-S8 is "
        "highlighted. Figure 4.4 shows the same view after the S9-S17 link was cut. The link count drops "
        "to 31 and the path for the pair now crosses core switch S18, S1-S9-S18-S15-S8, which is the "
        "recovery behavior of Section 3.4 on the larger topology."
    ),
    figure(
        "Figure 4.3", "shot_dashboard_fattree_normal.png",
        "Figure 4.3: Live dashboard on the k=4 fat-tree with 20 switches, 32 links and 16 hosts. The path "
        "from H1 to H16 is S1-S9-S17-S15-S8.",
        6.1, True,
    ),
    figure(
        "Figure 4.4", "shot_dashboard_fattree_failover.png",
        "Figure 4.4: The same dashboard after the S9-S17 link is cut. The count falls to 31 links and the "
        "path from H1 to H16 becomes S1-S9-S18-S15-S8.",
        6.1, True,
    ),
]


# ---------------------------------------------------------------------------
# Chapter 5: Experiments and Results
# ---------------------------------------------------------------------------
CH5 = [
    h2("5.1 Experimental Testbed and Batch Provenance"),
    p(
        "All experiments ran on the virtual machine of Table 4.1 with the controller and Mininet in separate "
        "processes. Each standalone batch in `experiments/compare_grid.py` builds a fresh grid and controller "
        "per trial, sets `SDN_ROUTING_MODE`, `SDN_POLL_INTERVAL`, and `SDN_CONGESTION_PERCENT`, and tears "
        "both down afterward. Every repeated setting ran n = 5 times; tables report mean and sample standard "
        "deviation (n - 1). Throughput is in decimal Mbps, loss and jitter are iperf UDP receiver metrics, "
        "delay is ping RTT, and each flow is a directed IPv4 MAC pair."
    ),
    p(
        "Table 5.1 documents the raw result sets and their exact controller provenance. The repeated 25 "
        "November batches ran with 64k HTB burst/cburst before the bounded LLDP wait patch (Listing 4.3, "
        "commit `70fcaa2`) was added. The homogeneous five-run calibration on 26 November "
        "(`accuracy-20261126T124854Z.json`) ran on Ubuntu after `70fcaa2` was deployed. By contrast, the two "
        "standalone 26 November live rehearsals (`grid-demo-20261126T120202Z.json` at 12:02 UTC and "
        "`link-failure-20261126T120735Z.json` at 12:07 UTC) do not record a controller commit hash in their "
        "JSON files, and their timestamps precede commit `70fcaa2` (14:27 local time, 12:27 UTC) during the "
        "earlier 0.01 s LLDP-guard rehearsal; they are therefore not attributed to the post-patch revision. "
        "Batches from different configurations are never pooled. Connectivity checks passed at 30/30 on the "
        "grid and 240/240 on the fat-tree, alongside 16/16 passing tests in `check_logic.py`."
    ),
    table(
        "Table 5.1",
        "Table 5.1: Raw result sets, workloads, and verified controller provenance (`experiments/results/`).",
        ["Result set", "Date (2026)", "Workload", "n", "Controller provenance"],
        [
            ["`accuracy-20261126T124854Z.json`", "26 Nov",
             "Fat-tree H1 to H16, 5 Mbps UDP iperf3, 30 s, 3 samples/trial", "5",
             "After bounded LLDP wait (`70fcaa2`)"],
            ["`compare-grid-20261125T194357Z`", "25 Nov",
             "Grid 85 Mbps H1-H6 + 30 Mbps H3-H5, 60 s, shortest vs balanced", "5 / mode",
             "64k HTB, before `70fcaa2`"],
            ["`ten-flows-20261125T200721Z`", "25 Nov",
             "Ten UDP pairs, 144 Mbps total, shortest vs ECMP vs balanced", "5 / mode",
             "64k HTB, before `70fcaa2`"],
            ["`shared-detection-20261125T203550Z`, `threshold-20261125T205244Z`", "25 Nov",
             "Four pairs on S2-S3, 90 Mbps; T = 2/5 s, θ = 60/70/80%",
             "5 / setting", "64k HTB, before `70fcaa2`"],
            ["`route-phases-20261125T210721Z`", "25 Nov",
             "Four pairs, T = 2 s, 5 s receiver windows before/after moves", "5 runs, 14 moves",
             "64k HTB, before `70fcaa2`"],
            ["`recovery-20261125T202848Z`", "25 Nov",
             "H2 to H6, S5-S6 cut, 260 pings at 50 ms", "5", "64k HTB, before `70fcaa2`"],
            ["`grid-demo-20261126T120202Z`, `link-failure-20261126T120735Z`", "26 Nov",
             "Live rehearsals: 85 + 30 Mbps move; S5-S6 cut (300 pings at 0.2 s)", "1 each",
             "Earlier 26 Nov rehearsal (before `70fcaa2`; revision unlogged in JSON)"],
        ],
        [44, 15, 53, 19, 35],
    ),
    h2("5.2 C4 Monitoring Accuracy Calibration"),
    p(
        "Each trial sends 5 Mbps UDP via `iperf3` (1,400-byte datagrams) from H1 to H16 on the fat-tree for "
        "30 s over `S1-S9-S17-S15-S8`. After 12 s settling, the script polls `/sdn/bandwidth` three times "
        "(5 s apart), averages the first inter-switch port TX rate, and computes absolute relative error "
        "against the `iperf3` sender rate (target < 10%). Table 5.2 and Figure 5.1 report a mean error of "
        "3.116 ± 0.181 percentage points (range 2.938% to 3.397%). The positive bias comes from layer "
        "framing: OVS port counters include 14-byte Ethernet, 20-byte IP, and 8-byte UDP headers "
        "(42 / 1,400 = 3.0%), leaving ~0.1 pp for control frames such as LLDP and ARP."
    ),
    table(
        "Table 5.2",
        "Table 5.2: Monitoring accuracy, 5 Mbps UDP, fat-tree, n = 5 trials (`accuracy-20261126T124854Z.json`).",
        ["Quantity", "Mean ± sample SD", "Observed range"],
        [
            ["Sender payload rate (Mbps)", "5.0004 ± 0.0004", "5.0002 to 5.0011"],
            ["Port TX rate (Mbps)", "5.156 ± 0.009", "5.148 to 5.170"],
            ["Absolute relative error (%)", "3.116 ± 0.181", "2.938 to 3.397"],
        ],
        [70, 48, 48],
    ),
    {
        "type": "figure",
        "id": "Figure 5.1",
        "file": "fig_5_1_c4_accuracy.png",
        "caption": (
            "Figure 5.1: Sender rate against controller port TX across five calibration trials, and relative "
            "error against the 10% limit (mean 3.116%, sample SD 0.181 pp)."
        ),
        "width_in": 5.3,
        "max_h_in": 1.88,
        "border": False,
    },
    h2("5.3 Congestion Rerouting: Shortest-Path vs Balanced Routing"),
    p(
        "The baseline grid scenario offers 85 Mbps from H1 to H6 and 30 Mbps from H3 to H5 for 60 s across "
        "shared 100 Mbps link S2-S3 (115 Mbps offered). Table 5.3 and Figure 5.2 report whole-run receiver "
        "metrics, which include the initial congested window before rerouting triggers. Balanced routing "
        "raised H6 throughput from 68.90 to 79.60 Mbps and H5 from 19.30 to 27.42 Mbps (combined 88.20 to "
        "107.02 Mbps), cutting packet loss from 18.74% to 6.22% at H6 and from 35.49% to 8.61% at H5. Every "
        "balanced run moved H1-H6 to `S1-S4-S5-S6` at priority 21, while shortest-path runs stayed on "
        "`S1-S2-S3-S6` at priority 20. H6 shortest-path jitter SD (1.51 ms) reflects one outlier run at "
        "3.612 ms alongside four runs between 0.206 and 0.295 ms."
    ),
    table(
        "Table 5.3",
        "Table 5.3: Receiver metrics under shortest-path and balanced routing, 60 s runs, mean ± sample SD, "
        "n = 5 per policy (`compare-grid-20261125T194357Z`).",
        ["Receiver and policy", "Throughput (Mbps)", "Loss (%)", "Jitter (ms)"],
        [
            ["H6, shortest", "68.90 ± 2.32", "18.74 ± 2.70", "0.92 ± 1.51"],
            ["H6, balanced", "79.60 ± 1.26", "6.22 ± 1.37", "0.24 ± 0.13"],
            ["H5, shortest", "19.30 ± 1.43", "35.49 ± 4.73", "1.18 ± 1.39"],
            ["H5, balanced", "27.42 ± 0.13", "8.61 ± 0.43", "0.19 ± 0.15"],
        ],
        [46, 40, 40, 40],
    ),
    {
        "type": "figure",
        "id": "Figure 5.2",
        "file": "fig_5_2_grid_comparison.png",
        "caption": (
            "Figure 5.2: Receiver throughput, packet loss, and jitter for H6 and H5 under shortest-path and "
            "balanced routing (bars show mean ± SD, dots show the five runs)."
        ),
        "width_in": 5.35,
        "max_h_in": 1.88,
        "border": False,
    },
    p(
        "Residual loss occurs while traffic shares S2-S3 prior to rerouting. In the standalone 26 November "
        "rehearsal `grid-demo-20261126T120202Z` (recorded prior to commit `70fcaa2`; exact controller commit "
        "not logged in JSON, and kept separate from Table 5.3), S2-S3 TX hit 86% at 5 s and 99.9% at 15 s; "
        "EWMA passed 70% before 15 s, reached streak 2 at 20 s, and shifted H1-H6 to `S1-S4-S5-S6` (priority "
        "21) between the 25 s and 30 s samples, dropping S2-S3 TX to 33.7% and then ~31%. Receivers measured "
        "80.0 Mbps (5.9% loss, 0.195 ms jitter) at H6 and 27.2 Mbps (9.3% loss, 0.178 ms jitter) at H5."
    ),
    h2("5.4 Ten-Flow Policy Comparison: Shortest, ECMP, and Balanced"),
    p(
        "Each of five seeded rounds draws ten directed UDP pairs totaling 144 Mbps (rates 8 to 28 Mbps) for "
        "60 s across all three policies, recording peak TX utilization over any inter-switch port across ten "
        "5 s samples (Table 5.4, Figure 5.3). All three policies delivered 144.00 Mbps. Static ECMP achieved "
        "the lowest mean peak (47.96 ± 4.74%) because hashing spreads pairs at install time before traffic "
        "starts, cutting the two heaviest shortest-path rounds (70.18% and 74.24%) down to 53.80% and 49.62%. "
        "Reactive balanced routing tracked shortest path closely (56.50% vs 56.20%, largest round gap 1.07 pp) "
        "because early samples capture peaks before EWMA crosses 70% for two periods, and occupied links "
        "rarely satisfy the 15 pp improvement gate. The 18 lost datagrams (0.0005%) occurred only under "
        "balanced runs; under uniform multi-flow demand, proactive ECMP is the stronger baseline."
    ),
    table(
        "Table 5.4",
        "Table 5.4: Ten-flow comparison, 144 Mbps offered, n = 5 rounds per policy "
        "(`ten-flows-20261125T200721Z`).",
        ["Routing policy", "Peak TX (%)", "Received (Mbps)", "Lost / total datagrams"],
        [
            ["Shortest", "56.20 ± 14.99", "144.00 ± 0.00", "0 / 3,673,623"],
            ["ECMP", "47.96 ± 4.74", "144.00 ± 0.00", "0 / 3,673,613"],
            ["Balanced", "56.50 ± 15.13", "144.00 ± 0.00", "18 / 3,673,617"],
        ],
        [44, 38, 42, 42],
    ),
    {
        "type": "figure",
        "id": "Figure 5.3",
        "file": "fig_5_3_ten_flows.png",
        "caption": (
            "Figure 5.3: Peak port TX utilization for shortest, ECMP, and balanced routing over five rounds "
            "(mean ± SD, round dots, dashed 70% threshold)."
        ),
        "width_in": 5.25,
        "max_h_in": 1.85,
        "border": False,
    },
    h2("5.5 Polling Interval (T) and Congestion Threshold (θ) Sensitivity"),
    p(
        "Four flows sharing S2-S3 (H3-H6 16 Mbps, H4-H5 18 Mbps, H1-H6 28 Mbps, H3-H5 28 Mbps; 90 Mbps total) "
        "tested detection latency from first sender launch until S2-S3 reached congestion streak 2 across 20 "
        "runs (Table 5.5, Figure 5.4). All 20 runs detected congestion. Cutting T from 5 s to 2 s at θ = 70% "
        "reduced declaration time from 18.932 s to 6.952 s (11.98 s faster, factor 2.72x, trading 2.5x higher "
        "stats-polling load). Raising θ from 70% to 80% added 1.975 s (roughly one 2 s tick), while lowering "
        "θ to 60% saved only 0.137 s (within run SD), supporting 70% as the default threshold."
    ),
    table(
        "Table 5.5",
        "Table 5.5: Time to declare congestion on S2-S3, n = 5 per setting "
        "(`shared-detection-20261125T203550Z`, `threshold-20261125T205244Z`).",
        ["Poll period T", "Threshold θ", "Detected", "First declaration (s)"],
        [
            ["2 s", "60%", "5 / 5", "6.815 ± 0.129"],
            ["2 s", "70%", "5 / 5", "6.952 ± 0.181"],
            ["2 s", "80%", "5 / 5", "8.927 ± 0.107"],
            ["5 s", "70%", "5 / 5", "18.932 ± 0.185"],
        ],
        [38, 38, 32, 58],
    ),
    {
        "type": "figure",
        "id": "Figure 5.4",
        "file": "fig_5_4_detection_threshold.png",
        "caption": (
            "Figure 5.4: Congestion declaration time for T = 2 s vs T = 5 s at θ = 70% (left) and θ = 60%, "
            "70%, and 80% at T = 2 s (right); all 20 runs detected."
        ),
        "width_in": 5.3,
        "max_h_in": 1.85,
        "border": False,
    },
    h2("5.6 Before-and-After Reroute Window Metrics"),
    p(
        "Across five T = 2 s runs, comparing five 1 s receiver intervals before and after each confirmed move "
        "(>= 1 s guard) yielded 14 paired comparisons with 0.00% loss in all 28 windows (Table 5.6, Figure 5.5). "
        "Throughput stayed near offered rates because total demand was 90 Mbps. Delay shifted by topology: "
        "H1-H6 kept three hops while leaving the congested queue, cutting RTT from 18.82 to 15.44 ms; H3-H5 "
        "detoured forward from 1-hop S2-S3 onto 3-hop S2-S5-S6-S3 (+4 ms propagation), raising RTT from 7.92 "
        "to 10.40 ms; H4-H5 swapped equal two-hop paths (9.59 vs 9.53 ms); and H3-H6 fell from 22.68 to "
        "10.12 ms (n = 1). Jitter rose slightly for H1-H6 and H3-H5 within one post-move SD, showing that "
        "rerouting benefits are pair- and metric-specific."
    ),
    table(
        "Table 5.6",
        "Table 5.6: Receiver windows before and after the first managed move, mean ± sample SD, entries are "
        "(before, after) (`route-phases-20261125T210721Z`).",
        ["Pair (n)", "Throughput (Mbps)", "Ping RTT (ms)", "UDP jitter (ms)"],
        [
            ["H1 to H6 (5)", "27.956 ± 0.098, 27.996 ± 0.009", "18.82 ± 9.16, 15.44 ± 1.08",
             "0.303 ± 0.030, 0.381 ± 0.149"],
            ["H3 to H5 (5)", "27.996 ± 0.009, 27.996 ± 0.009", "7.92 ± 3.13, 10.40 ± 0.82",
             "0.181 ± 0.061, 0.323 ± 0.169"],
            ["H4 to H5 (3)", "17.987 ± 0.023, 17.980 ± 0.035", "9.59 ± 0.25, 9.53 ± 0.15",
             "0.343 ± 0.043, 0.308 ± 0.078"],
            ["H3 to H6 (1)", "16.000, 16.000", "22.68, 10.12", "0.394, 0.290"],
        ],
        [30, 46, 45, 45],
    ),
    {
        "type": "figure",
        "id": "Figure 5.5",
        "file": "fig_5_5_route_phases.png",
        "caption": (
            "Figure 5.5: Ping RTT and UDP jitter before and after the first managed move across all four "
            "pairs (14 paired comparisons; 0.00% loss in every window)."
        ),
        "width_in": 5.3,
        "max_h_in": 1.88,
        "border": False,
    },
    h2("5.7 Automatic Link-Failure Recovery"),
    p(
        "Five recovery runs sent 260 pings at 50 ms spacing from H2 to H6 (`S4-S5-S6`) and cut S5-S6 mid-run, "
        "forcing failover onto `S4-S1-S2-S3-S6` via `EventLinkDelete` and `rebuild_routes` (Table 5.7, Figure "
        "5.6). The first qualifying post-cut reply arrived in 73.139 ± 21.631 ms (range 45.937 to 95.540 ms), "
        "with 7 of 1,300 probes lost (99.46% delivered; 50 ms probe spacing bounds resolution and measures "
        "host-visible outage rather than internal switch completion). In the separate 26 November live "
        "rehearsal `link-failure-20261126T120735Z` (recorded before commit `70fcaa2`; exact controller commit "
        "not logged in JSON), H1-H6 shifted from P3 (priority 21) onto `S1-S2-S3-S6` (priority 20) on the "
        "S5-S6 cut and remained there after restoration, receiving 299 of 300 pings at 0.2 s spacing (0.333% "
        "loss, coarse first reply 227.238 ms, largest inter-reply gap 0.724913 s, neither an exact convergence "
        "latency)."
    ),
    table(
        "Table 5.7",
        "Table 5.7: Recovery after an S5-S6 cut, H2 to H6, 260 probes per run, n = 5 "
        "(`recovery-20261125T202848Z`).",
        ["Metric", "Mean ± sample SD", "Observed range"],
        [
            ["First qualifying reply after the cut (ms)", "73.139 ± 21.631", "45.937 to 95.540"],
            ["Lost probes per run", "1.400 ± 0.894", "0 to 2"],
            ["Lost probes over all runs", "7 of 1,300 (0.54%)", "99.46% delivered"],
        ],
        [70, 48, 48],
    ),
    {
        "type": "figure",
        "id": "Figure 5.6",
        "file": "fig_5_6_failover_recovery.png",
        "caption": (
            "Figure 5.6: First post-cut reply time (mean 73.139 ± 21.631 ms) and lost probes per run "
            "(2, 2, 1, 0, 2; 7/1,300 total) across five recovery runs."
        ),
        "width_in": 5.3,
        "max_h_in": 1.85,
        "border": False,
    },
    h2("5.8 Engineering Limitations and Threats to Validity"),
    p(
        "All timings reflect single-VM emulation where controller, OVS, and generators share CPU cores. Five "
        "concrete limitations qualify the results above:"
    ),
    numbered([
        "**Batch and revision boundary:** Repeated 25 November batches used 64k HTB burst/cburst before the "
        "bounded LLDP wait patch (commit `70fcaa2`). Only the 26 November calibration (`124854Z`) is verified "
        "to have run after `70fcaa2` was deployed; the two 26 November live rehearsals (`120202Z` and "
        "`120735Z`) preceded `70fcaa2` and do not log a controller hash in JSON. Groups are never pooled.",
        "**Calibration scope:** `accuracy-20261126T124854Z.json` validates port TX at 5 Mbps on one fat-tree "
        "path (`n = 5`); earlier stopped or mixed-setting runs stay excluded, and saturation accuracy is not "
        "separately calibrated.",
        "**Residual LLDP churn:** Post-patch log `sdn-controller-fattree-20261126-144135.log` still records "
        "32 link deletions and 64 route rebuilds without tracebacks. Calibration succeeded despite them, yet "
        "their root cause remains open and universal discovery stability is not claimed.",
        "**Hold-down isolation and residual loss:** The 30 s per-flow hold-down passes offline unit tests "
        "(`check_logic.py`) but has not been isolated in a live Mininet run; high-load residual loss (6.22% "
        "H6, 8.61% H5 in Table 5.3) remains and zero loss is never claimed.",
        "**Flow and metric definitions:** Rules match directed IPv4 MAC pairs rather than 5-tuples; port TX "
        "includes framing and background traffic (~3% above UDP payload); receiver rate, ping RTT, and UDP "
        "jitter are distinct metrics; small samples (`n = 3` H4-H5, `n = 1` H3-H6) carry no statistical claim.",
    ]),
    p(
        "During C4 development, an unshaped TCP `iperf` (`qdisc noqueue`) reached 32.3 to 34.0 Gbit/s, "
        "starving LLDP keepalives and triggering `Link removed: S5 - S2`, `No path available`, and `0/30` "
        "pingall until restart (Figure 5.7). Every benchmark in this chapter therefore enforces 100 Mbps "
        "shaped links with 64k HTB burst."
    ),
    {
        "type": "figure",
        "id": "Figure 5.7",
        "file": "shot_unshaped_lldp_stress.png",
        "caption": (
            "Figure 5.7: Unshaped TCP iperf at 32.3 to 34.0 Gbit/s on `qdisc noqueue`, followed by "
            "`Link removed: S5 - S2` and `No path available` in the controller log."
        ),
        "width_in": 5.45,
        "max_h_in": 1.98,
        "border": True,
    },
]

# ---------------------------------------------------------------------------
# Chapter 6: Conclusion and Future Work
# ---------------------------------------------------------------------------
CH6 = [
    h2("6.1 Conclusion"),
    p(
        "The project delivers an OpenFlow 1.3 controller on OS-Ken that discovers a 6-switch grid and a "
        "20-switch fat-tree, learns hosts, answers ARP itself, measures port and host-pair load, and "
        "reroutes large flows with an egress-to-ingress update confirmed by barriers. The port TX "
        "measurement agrees with iperf3 to 3.116 ± 0.181% (n = 5), against a 10% limit, and the 3.0% "
        "that header overhead explains accounts for almost all of it. With 85 and 30 Mbps competing on "
        "S2-S3, balanced routing raised H6 from 68.90 to 79.60 Mbps and H5 from 19.30 to 27.42 Mbps, and "
        "cut loss from 18.74% to 6.22% and from 35.49% to 8.61%. Congestion was declared after 6.952 s "
        "at T = 2 s and after 18.932 s at T = 5 s. After an S5-S6 cut the first usable reply came "
        "73.139 ± 21.631 ms later, and 7 of 1,300 probes were lost."
    ),
    p(
        "The results also set the scope of the claim. Reactive rebalancing pays off when contention is "
        "persistent and an idle alternative exists, as in the demo scenario. With ten random flows, static "
        "ECMP gave a lower mean peak than both shortest path and balanced routing, 47.96% against 56.20% "
        "and 56.50%. Moving a flow can lengthen its path, which raised the RTT of H3 to H5 from 7.92 to "
        "10.40 ms. Connectivity checks passed at 30 of 30 on the grid and 240 of 240 on the fat-tree, and "
        "16 of 16 offline tests pass. Section 5.8 lists the open limitations: the batch boundary, the "
        "discovery churn in the fat-tree log, and the missing live isolation of the hold-down."
    ),
    h2("6.2 Future Work"),
    numbered([
        "Isolate the 30 s hold-down in a live run. The controller already logs a PATH_COMMIT line with a "
        "monotonic timestamp for each move, so repeated runs with the hold-down enabled and disabled can "
        "compare move counts and loss directly.",
        "Correlate the link-deletion episodes in the fat-tree log with LLDP send times and CPU load, "
        "to find out whether probe scheduling, the 10 s timeout or machine load causes them.",
        "Use OpenFlow 1.3 fast-failover group tables [4], [18] for link protection. The switch would fall back to a "
        "pre-installed bucket on port-down, which would remove the controller round trip from the 46 to "
        "96 ms recovery window.",
        "Match on the transport 5-tuple so that parallel connections between two hosts become separate "
        "flows with separate rates and separate paths.",
        "Predict elephants from the per-pair rate series the controller already stores, install the "
        "alternative path before the two-period trigger fires, and test the predictor against the ECMP "
        "baseline of Section 5.4.",
    ]),
]

CHAPTERS_PART2 = [
    {"number": 3, "title": "System Design", "blocks": CH3},
    {"number": 4, "title": "Implementation", "blocks": CH4},
    {"number": 5, "title": "Experiments and Results", "blocks": CH5},
    {"number": 6, "title": "Conclusion and Future Work", "blocks": CH6},
]

# ---------------------------------------------------------------------------
# References (IEEE), canonical numbering [1]-[18]
# ---------------------------------------------------------------------------
REFERENCES = [
    "[1] M. Casado, M. J. Freedman, J. Pettit, J. Luo, N. McKeown, and S. Shenker, \"Ethane: Taking control "
    "of the enterprise,\" in Proc. ACM SIGCOMM, Kyoto, Japan, Aug. 2007, pp. 1-12.",
    "[2] A. Greenberg, G. Hjalmtysson, D. A. Maltz, A. Myers, J. Rexford, G. Xie, H. Yan, J. Zhan, and "
    "H. Zhang, \"A clean slate 4D approach to network control and management,\" ACM SIGCOMM Comput. "
    "Commun. Rev., vol. 35, no. 5, pp. 41-54, Oct. 2005.",
    "[3] N. McKeown, T. Anderson, H. Balakrishnan, G. Parulkar, L. Peterson, J. Rexford, S. Shenker, and "
    "J. Turner, \"OpenFlow: Enabling innovation in campus networks,\" ACM SIGCOMM Comput. Commun. Rev., "
    "vol. 38, no. 2, pp. 69-74, Apr. 2008.",
    "[4] Open Networking Foundation, \"OpenFlow switch specification, version 1.3.5 (protocol version "
    "0x04),\" ONF TS-023, Mar. 2015.",
    "[5] D. Kreutz, F. M. V. Ramos, P. E. Verissimo, C. E. Rothenberg, S. Azodolmolky, and S. Uhlig, "
    "\"Software-defined networking: A comprehensive survey,\" Proc. IEEE, vol. 103, no. 1, pp. 14-76, "
    "Jan. 2015.",
    "[6] Ryu SDN Framework Community, \"Ryu SDN framework documentation,\" and OpenStack, \"OS-Ken "
    "documentation.\" [Online]. Available: https://ryu-sdn.org and https://docs.openstack.org/os-ken/latest/. "
    "Accessed: Nov. 2026.",
    "[7] P. Berde, M. Gerola, J. Hart, Y. Higuchi, M. Kobayashi, T. Koide, B. Lantz, B. O'Connor, "
    "P. Radoslavov, W. Snow, and G. Parulkar, \"ONOS: Towards an open, distributed SDN OS,\" in Proc. "
    "3rd Workshop Hot Topics Softw. Defined Netw. (HotSDN), Chicago, IL, USA, Aug. 2014, pp. 1-6.",
    "[8] J. Medved, R. Varga, A. Tkacik, and K. Gray, \"OpenDaylight: Towards a model-driven SDN "
    "controller architecture,\" in Proc. IEEE Int. Symp. World of Wireless, Mobile and Multimedia Netw. "
    "(WoWMoM), Sydney, Australia, Jun. 2014, pp. 1-6.",
    "[9] B. Pfaff, J. Pettit, T. Koponen, E. Jackson, A. Zhou, J. Rajahalme, J. Gross, A. Wang, "
    "J. Stringer, P. Shelar, K. Amidon, and M. Casado, \"The design and implementation of Open vSwitch,\" "
    "in Proc. 12th USENIX Symp. Networked Syst. Design Implement. (NSDI), Oakland, CA, USA, May 2015, "
    "pp. 117-130.",
    "[10] P. Bosshart, D. Daly, G. Gibb, M. Izzard, N. McKeown, J. Rexford, C. Schlesinger, D. Talayco, "
    "A. Vahdat, G. Varghese, and D. Walker, \"P4: Programming protocol-independent packet processors,\" "
    "ACM SIGCOMM Comput. Commun. Rev., vol. 44, no. 3, pp. 87-95, Jul. 2014.",
    "[11] B. Lantz, B. Heller, and N. McKeown, \"A network in a laptop: Rapid prototyping for "
    "software-defined networks,\" in Proc. 9th ACM SIGCOMM Workshop Hot Topics Netw. (HotNets), Monterey, "
    "CA, USA, Oct. 2010, pp. 19:1-19:6.",
    "[12] M. Al-Fares, A. Loukissas, and A. Vahdat, \"A scalable, commodity data center network "
    "architecture,\" in Proc. ACM SIGCOMM, Seattle, WA, USA, Aug. 2008, pp. 63-74.",
    "[13] M. Al-Fares, S. Radhakrishnan, B. Raghavan, N. Huang, and A. Vahdat, \"Hedera: Dynamic flow "
    "scheduling for data center networks,\" in Proc. 7th USENIX Symp. Networked Syst. Design Implement. "
    "(NSDI), San Jose, CA, USA, Apr. 2010, pp. 281-296.",
    "[14] T. Benson, A. Anand, A. Akella, and M. Zhang, \"MicroTE: Fine grained traffic engineering for "
    "data centers,\" in Proc. 7th Conf. Emerging Netw. Experiments Technol. (CoNEXT), Tokyo, Japan, "
    "Dec. 2011, pp. 8:1-8:12.",
    "[15] M. Alizadeh, T. Edsall, S. Dharmapurikar, R. Vaidyanathan, K. Chu, A. Fingerhut, V. T. Lam, "
    "F. Matus, R. Pan, N. Yadav, and G. Varghese, \"CONGA: Distributed congestion-aware load balancing "
    "for datacenters,\" in Proc. ACM SIGCOMM, Chicago, IL, USA, Aug. 2014, pp. 503-514.",
    "[16] M. Reitblatt, N. Foster, J. Rexford, C. Schlesinger, and D. Walker, \"Abstractions for network "
    "update,\" in Proc. ACM SIGCOMM, Helsinki, Finland, Aug. 2012, pp. 323-334.",
    "[17] S. Jain, A. Kumar, S. Mandal, J. Ong, L. Poutievski, A. Singh, S. Venkata, J. Wanderer, J. Zhou, "
    "M. Zhu, J. Zolla, U. Holzle, S. Stuart, and A. Vahdat, \"B4: Experience with a globally-deployed "
    "software defined WAN,\" in Proc. ACM SIGCOMM, Hong Kong, China, Aug. 2013, pp. 3-14.",
    "[18] S. Sharma, D. Staessens, D. Colle, M. Pickavet, and P. Demeester, \"OpenFlow: Meeting "
    "carrier-grade recovery requirements,\" Comput. Commun., vol. 36, no. 6, pp. 656-665, Mar. 2013.",
]

# ---------------------------------------------------------------------------
# Appendices
# ---------------------------------------------------------------------------
APP_A = [
    p(
        "All commands run in Ubuntu terminals from the independent project copy in ~/sdn-project. The "
        "controller environment is ~/sdn-lab/.venv. run.sh takes the role as its first argument and the "
        "topology (grid or fattree) as its second, and it exports SDN_TOPOLOGY for the controller."
    ),
    h2("A.1 Installation"),
    code(
        "Packages and virtual environment",
        r"""
sudo apt install mininet openvswitch-switch iperf iperf3 python3-venv wireshark
python3 -m venv "$HOME/sdn-lab/.venv"
"$HOME/sdn-lab/.venv/bin/python" -m pip install -r "$HOME/sdn-project/requirements.txt"
""",
    ),
    h2("A.2 Running the grid"),
    p(
        "Open three terminals and start them in this order. Wait for six switches and seven links in the "
        "controller log, then open http://127.0.0.1:8081 inside Ubuntu."
    ),
    code(
        "Terminals 1, 2 and 3",
        r"""
bash ~/sdn-project/run.sh controller grid      # terminal 1: OS-Ken, REST on 127.0.0.1:8080
bash ~/sdn-project/run.sh network grid         # terminal 2: Mininet, OVS with OpenFlow13, TCLinks
bash ~/sdn-project/run.sh dashboard            # terminal 3: dashboard on 127.0.0.1:8081
""",
    ),
    code(
        "Mininet prompt: connectivity, congestion demo and failure demo",
        r"""
mininet> pingall
mininet> py __import__('runpy').run_path('experiments/grid_demo.py', init_globals=dict(h1=h1,h3=h3,h5=h5,h6=h6)) and None
mininet> py __import__('runpy').run_path('experiments/link_failure_demo.py', init_globals=dict(net=net)) and None
mininet> sh tc class show dev s1-eth1
""",
    ),
    h2("A.3 Running the fat-tree"),
    code(
        "Fat-tree launch and calibration",
        r"""
bash ~/sdn-project/run.sh controller fattree   # wait for 20 switches and 32 links
bash ~/sdn-project/run.sh network fattree
mininet> pingall 2
mininet> py __import__('runpy').run_path('experiments/bandwidth_accuracy.py', init_globals=dict(net=net)) and None
""",
    ),
    p(
        "The controller reads its parameters from the environment when it starts. They can be prefixed to "
        "the controller command, for example SDN_ROUTING_MODE=ecmp bash ~/sdn-project/run.sh controller "
        "grid. Table A.1 lists them."
    ),
    table(
        "Table A.1",
        "Table A.1: Controller parameters read at start-up.",
        ["Variable", "Default", "Meaning"],
        [
            ["SDN_POLL_INTERVAL", "5", "Statistics period T in seconds, from 2 to 5"],
            ["SDN_CONGESTION_PERCENT", "70", "Congestion threshold θ, between 0 and 100 exclusive"],
            ["SDN_ROUTING_MODE", "balanced", "shortest, ecmp or balanced"],
            ["SDN_TOPOLOGY", "mynetwork", "mynetwork or fattree4, set by run.sh"],
            ["SDN_TRACE_DETECTION", "unset", "Set to 1 to log DETECTION_SAMPLE and PATH_COMMIT lines"],
        ],
        [50, 28, 88],
    ),
    h2("A.4 Experiment batches and tests"),
    p(
        "The standalone batches create and remove their own grid, so stop any running Mininet session and "
        "controller first. Each batch writes its raw JSON to experiments/results/."
    ),
    code(
        "Batches (sudo, no other controller running)",
        r"""
sudo python3 ~/sdn-project/experiments/compare_grid.py                       # shortest vs balanced
sudo python3 ~/sdn-project/experiments/compare_grid.py --ten-flows
sudo python3 ~/sdn-project/experiments/compare_grid.py --recovery
sudo python3 ~/sdn-project/experiments/compare_grid.py --compare-shared-link
sudo python3 ~/sdn-project/experiments/compare_grid.py --compare-thresholds
sudo python3 ~/sdn-project/experiments/compare_grid.py --route-phases
""",
    ),
    code(
        "Offline tests and a status check",
        r"""
python3 ~/sdn-project/experiments/check_logic.py     # 16 tests, all pass
python3 ~/sdn-project/experiments/check_sync.py
curl -s http://127.0.0.1:8080/sdn/status
""",
    ),
]

APP_B = [
    h2("B.1 Team Roster"),
    p(
        "Table B.1 lists the six team members as they appear on the cover page."
    ),
    table(
        "Table B.1",
        "Table B.1: Team roster.",
        ["Student ID", "Name"],
        [
            ["921230064", "عبدالحميد أحمد"],
            ["921230066", "عبدالرحمن أحمد محمد محمد"],
            ["921230065", "عبدالرحمن أحمد فؤاد"],
            ["921230069", "عبدالرحمن عمرو عبدالحليم"],
            ["921230061", "صهيب وائل محمد"],
            ["921230068", "عبدالرحمن صلاح الدين يحي"],
        ],
        [50, 116],
    ),
    h2("B.2 Repository History"),
    p(
        "Contribution allocation: INCOMPLETE; awaiting team confirmation. Individual roles, actual tasks "
        "and per-member commit attribution remain unverified. Local Git tracking begins with the lab "
        "source snapshot received on 17 November 2026 and records later integration, experiments and "
        "documentation. These dates do not establish the original start date or a complete 12-week "
        "project timeline. The commits use one author identity. Original weekly progress reports for "
        "Weeks 3 to 14 are not supplied. Table B.2 maps work packages to repository evidence, not to "
        "individual students."
    ),
    table(
        "Table B.2",
        "Table B.2: Work packages and repository evidence.",
        ["Work package", "Evidence in the repository"],
        [
            ["Controller: discovery, proxy ARP, routing", "`vm-source/rest_api_controller.py`"],
            ["Topologies and link shaping", "`vm-source/custom_topology.py` (`MyNetwork`, `FatTree4`, `LabTCLink`)"],
            ["REST API and dashboard", "`rest_application` in the controller, `dashboard/`"],
            ["OpenFlow capture (C1)", "`c1/` learning switch and `c1/c1-linear-rerun.pcapng`"],
            ["Experiments and raw results", "`experiments/*.py`, `experiments/results/*.json`"],
            ["Offline regression tests", "`experiments/check_logic.py` (16 tests), `check_sync.py`"],
            ["Run guides", "`README.md`, `ubuntu/README.md`, `ubuntu/run.sh`"],
        ],
        [70, 96],
    ),
    h2("B.3 Milestone Log"),
    p(
        "The course defines six checkpoints, CP1 to CP6, in Section 8 of the project handout. Table B.3 "
        "matches each one with the material in this report and in the repository."
    ),
    table(
        "Table B.3",
        "Table B.3: Course checkpoints and the corresponding evidence.",
        ["Checkpoint", "Handout deliverable", "Evidence"],
        [
            ["CP1", "SDN background draft, setup screenshots, approved proposal",
             "Chapter 2; Wireshark capture of the OpenFlow 1.3 handshake (Figures 2.4 and 2.5); separate Week 4 proposal file not stored in repository"],
            ["CP2", "Discovery, routing, live utilization",
             "LLDP graph, Dijkstra routing, proxy ARP, port statistics; pingall 30/30 (Figure 4.1)"],
            ["CP3", "Track topology and first feature",
             "k=4 fat-tree with 240/240 connectivity; elephant and congestion detection (Section 3.3)"],
            ["CP4", "Live mid-project demo",
             "experiments/grid_demo.py and grid-demo-20261126T120202Z.json (Section 5.3)"],
            ["CP5", "All required features",
             "Barrier-gated make-before-break, hysteresis, recovery, REST API and dashboard (Chapters 3 and 4)"],
            ["CP6", "Results tables and graphs",
             "Chapter 5 and the raw JSON batches in experiments/results/"],
        ],
        [24, 62, 80],
    ),
]

APPENDICES = [
    {"letter": "A", "title": "Deployment and Reproducibility Guide", "blocks": APP_A},
    {"letter": "B", "title": "Team Roster, Repository History, and Milestone Log", "blocks": APP_B},
]
