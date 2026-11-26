# -*- coding: utf-8 -*-
"""Front matter, Chapter 1, and Chapter 2 of the SDN Track 1 final report.

Exports:
    META, ABSTRACT_PARAGRAPHS, KEYWORDS, CHAPTERS_PART1 ([ch1, ch2])

Reference numbers [1]-[18] follow the canonical IEEE list shared with
content_part2.REFERENCES.
"""

META = {
    "university": "Helwan National University",
    "faculty": "Faculty of Engineering",
    "department": "Intelligent Systems Engineering",
    "course": "Computer Networks (ECE2606)",
    "title": "Intelligent Load Balancer with Fault Tolerance in Software-Defined Networks",
    "subtitle": "ECE2606: Computer Networks Course Project (Track 1)",
    "track": "Track 1: Intelligent Load Balancer with Fault Tolerance",
    "supervisor": "Prof. Ahmed M. Abdelhaleem",
    "semester": "Fall 2026/2027",
    "date": "November 2026",
    "logo_file": "hnu_logo.png",
    "team": [
        ("921230064", "عبدالحميد أحمد"),
        ("921230066", "عبدالرحمن أحمد محمد محمد"),
        ("921230065", "عبدالرحمن أحمد فؤاد"),
        ("921230069", "عبدالرحمن عمرو عبدالحليم"),
        ("921230061", "صهيب وائل محمد"),
        ("921230068", "عبدالرحمن صلاح الدين يحي"),
    ],
}

ABSTRACT_PARAGRAPHS = [
    (
        "Static shortest-path routing sends traffic between a host pair along one fixed sequence of switches, "
        "even when parallel paths of equal length carry little load. This report presents the design, "
        "implementation, and experimental evaluation of an OpenFlow 1.3 Software-Defined Networking (SDN) "
        "controller built on OS-Ken 3.1.1 for dynamic load balancing and automatic link-failure recovery. The "
        "controller discovers switches and links through LLDP, learns host locations with proxy ARP, polls "
        "OpenFlow 1.3 port and flow counters at a configurable period, smooths directional link utilization "
        "with an exponentially weighted moving average (EWMA), detects persistent elephant flows, and moves a "
        "selected directed host pair onto an alternate path using an egress-to-ingress make-before-break "
        "sequence confirmed by OpenFlow barrier messages. A lightweight Eventlet WSGI REST API and local web "
        "dashboard expose live topology, flow rules, and link utilization."
    ),
    (
        "The system was evaluated in Mininet with Open vSwitch on a six-switch, seven-link lab grid (100 Mbps, "
        "2 ms shaped links) and a 16-host k=4 fat-tree. Full reachability was verified at 30/30 host pairs on "
        "the grid and 240/240 pairs on the fat-tree, alongside 16/16 passing offline unit tests. Bandwidth "
        "calibration against steady 5 Mbps UDP iperf3 streams on the fat-tree produced a mean absolute relative "
        "error of 3.116 \u00b1 0.181% across five trials, well within the 10% target. Under competing 85 Mbps and "
        "30 Mbps grid flows (five runs per policy), balanced rerouting raised receiver throughput from 68.90 to "
        "79.60 Mbps for H1 to H6 and from 19.30 to 27.42 Mbps for H3 to H5, while cutting packet loss from "
        "18.74% to 6.22% and from 35.49% to 8.61%, respectively. Across five controlled S5-S6 link cuts on the "
        "grid, host-visible failover took 73.14 \u00b1 21.63 ms to the first qualifying reply, with 7 of 1,300 "
        "ICMP probes lost."
    ),
    (
        "The evaluation also documents where reactive centralized rerouting reaches its limits. On a ten-flow "
        "workload totaling 144 Mbps across the grid, static ECMP achieved a lower mean peak link utilization "
        "(47.96 \u00b1 4.74%) than either shortest-path routing (56.20 \u00b1 14.99%) or reactive balancing "
        "(56.50 \u00b1 15.13%), showing that hash-based spreading avoids transient peaks when traffic is already "
        "well distributed. The 30 s per-flow hold-down timer is verified by unit tests but has not been "
        "isolated in a live experiment, and extended fat-tree logs still record intermittent LLDP link "
        "deletions and rebuilds under software emulation."
    ),
]

KEYWORDS = [
    "Software-Defined Networking (SDN)",
    "OpenFlow 1.3",
    "OS-Ken",
    "Dynamic Load Balancing",
    "Elephant Flow Detection",
    "Make-Before-Break Rerouting",
    "Fault Tolerance",
]


def _h2(text):
    return {"type": "h2", "text": text}


def _h3(text):
    return {"type": "h3", "text": text}


def _p(text):
    return {"type": "p", "text": text}


# ---------------------------------------------------------------------------
# Chapter 1: Introduction (~2 pages)
# ---------------------------------------------------------------------------
CH1_BLOCKS = [
    _h2("1.1 Motivation"),
    _p(
        "Multi-path topologies exist to provide aggregate capacity and resilience, yet conventional hop-count "
        "routing leaves much of that capacity unused. Consider the six-switch, seven-link grid deployed in this "
        "project: host H1 attached to switch S1 can reach host H6 on switch S6 through the upper row "
        "(S1-S2-S3-S6) or through the lower row (S1-S4-S5-S6). Both routes cross three inter-switch links. "
        "Because hop count treats them as identical, a static shortest-path table pins H1-to-H6 traffic onto "
        "one fixed branch. When H3 simultaneously transmits to H5 over the shared S2-S3 link, both transfers "
        "contend for the same 100 Mbps bottleneck while the lower row sits idle. Queue buildup follows quickly, "
        "inflating jitter and dropping packets even though spare bandwidth exists one hop away."
    ),
    _p(
        "Steering traffic dynamically requires more than checking whether a single port looks busy. A port "
        "counter tells the controller that link S2-S3 is saturated, yet it cannot identify which active host "
        "pair is driving the load or whether moving that transfer will simply congest the replacement path. "
        "Reacting to every millisecond spike is equally counterproductive, because reprogramming switches on "
        "transient bursts wastes control-plane bandwidth and risks path oscillation. An effective load balancer "
        "must combine smoothed link-utilization measurements, per-flow rate estimates at network ingress, "
        "projected post-move path costs, and explicit update ordering so traffic shifts cleanly."
    ),
    _h2("1.2 Problem Statement"),
    _p(
        "Track 1 of the ECE2606 Computer Networks project addresses two operational problems within a single "
        "OpenFlow 1.3 controller: relieving persistent link congestion through dynamic rerouting and restoring "
        "host connectivity automatically after a physical link failure. Although both events change active "
        "forwarding paths, they impose distinct timing and safety requirements. During congestion, the existing "
        "route continues carrying packets while the controller evaluates up to three candidate paths, checks "
        "whether the projected gain justifies a move, and installs higher-priority rules on the replacement "
        "path before retiring the old entries. During a link failure, every path traversing the severed edge "
        "stops working immediately; the controller must prune the dead edge from its topology graph, recompute "
        "valid routes on the surviving links, and push updated forwarding rules as quickly as the control "
        "channel allows."
    ),
    _p(
        "The design operates under clear protocol and testbed boundaries. Each managed flow corresponds to a "
        "directed IPv4 host pair matched by Ethernet source and destination MAC addresses, without splitting "
        "traffic by TCP or UDP five-tuples, so concurrent sockets between the same endpoints aggregate into one "
        "rate estimate. Switch rules reside in OpenFlow 1.3 table 0 at priority 20 and above, avoiding rule "
        "conflicts with priority-0 table-miss entries and controller discovery traffic. All experiments execute "
        "in Mininet with Open vSwitch on a single Ubuntu virtual machine using Linux traffic-control shaping "
        "(100 Mbps rate and 2 ms delay per inter-switch link). Measurements therefore reflect software "
        "emulation under controlled capacities, and the evaluation explicitly distinguishes link-level counter "
        "peaks from end-host receiver throughput, loss, and delay."
    ),
    _h2("1.3 Project Objectives"),
    _p(
        "The project builds progressively from the five mandatory Common Core milestones (C1 to C5) to the "
        "Track 1 load-balancing and fault-tolerance requirements:"
    ),
    {
        "type": "numbered",
        "items": [
            "Verify an OpenFlow 1.3 control channel between OS-Ken and Open vSwitch (C1) by capturing and "
            "dissecting handshake, multipart, and flow-modification exchanges in Wireshark.",
            "Implement automatic LLDP topology discovery, host-to-port learning, proxy ARP, and shortest-path "
            "forwarding (C2, C3), verifying full host reachability on both the six-switch grid (30/30 pairs) "
            "and the 16-host k=4 fat-tree (240/240 pairs).",
            "Build periodic OpenFlow 1.3 port and flow counter polling (C4) using cumulative byte deltas "
            "(\u0394bytes \u00d7 8 / \u0394t) and validate measured port transmit rates against steady iperf3 "
            "streams within the 10% relative-error criterion.",
            "Expose live topology, host attachment tables, directional bandwidth, and installed flow entries "
            "through an embedded Eventlet WSGI REST API and a read-only web dashboard (C5).",
            "Implement Track 1 congestion control using EWMA utilization smoothing (\u03b1 = 0.5, threshold "
            "\u03b8 = 70% for two consecutive periods), elephant flow filtering (> 10% link capacity for two "
            "periods), Yen k = 3 candidate path ranking by projected post-move load, hysteresis guards "
            "(\u2265 15 percentage points improvement and 30 s per-flow hold-down), and barrier-confirmed "
            "egress-to-ingress make-before-break rule installation.",
            "Evaluate balanced routing against shortest-path and ECMP baselines across repeated five-run "
            "batches covering accuracy, congestion throughput and loss, ten-flow peak utilization, polling "
            "interval and threshold sensitivity, and before-versus-after route metrics.",
            "Implement automatic link-failure detection and path recomputation, quantifying host-visible "
            "recovery time and packet loss across repeated controlled link cuts.",
        ],
    },
    _h2("1.4 Report Organization"),
    _p(
        "The remainder of this report proceeds from theoretical background to verified experimental results. "
        "Chapter 2 reviews Software-Defined Networking concepts, OpenFlow 1.3 mechanics with our own Wireshark "
        "captures, controller platforms, data-plane technologies, related traffic-engineering literature, "
        "security and reliability trade-offs, and practical deployments. Chapter 3 details the controller "
        "architecture, grid and fat-tree topologies, mathematical monitoring formulation, path-selection "
        "pseudocode, and make-before-break update sequence. Chapter 4 documents the Python implementation, "
        "event handlers, REST endpoints, web dashboard, and unit-test suite. Chapter 5 presents the repeated "
        "experimental benchmarks, quantitative comparisons, and consolidated engineering limitations. Chapter 6 "
        "summarizes the findings and outlines concrete future work, followed by IEEE references and two "
        "appendices covering deployment commands and team contributions."
    ),
]


# ---------------------------------------------------------------------------
# Chapter 2: Software-Defined Networking Background (~10-11 pages)
# Covers all 8 mandatory subtopics 11.1-11.8 across 2.1-2.8 with 5 figures,
# 3 tables, and all 18 canonical IEEE citations [1]-[18].
# ---------------------------------------------------------------------------
CH2_BLOCKS = [
    # ---- 2.1 (~330 words + Fig 2.1) ----
    _h2("2.1 Traditional Networks versus SDN and Historical Evolution"),
    _p(
        "In a conventional IP router or Ethernet switch, packet forwarding and routing logic live inside the "
        "same chassis. Three planes are coupled in vendor firmware: the data plane parses headers and forwards "
        "frames at line rate, the control plane runs distributed routing protocols to populate local tables, "
        "and the management plane handles device configuration via vendor-specific CLIs or SNMP. Implementing "
        "a network-wide traffic policy means translating one operational goal into dozens of box-level "
        "configurations across different operating systems."
    ),
    _p(
        "Distributed protocols provide reachability and loop prevention, yet they underutilize parallel paths. "
        "Under Open Shortest Path First (OSPF), routers flood link-state updates and run Dijkstra's algorithm "
        "independently; static weights push traffic down one lowest-cost route regardless of live queue load, "
        "and link failures require flooding before tables reconverge. At Layer 2, the Spanning Tree Protocol "
        "(STP) avoids broadcast loops by blocking redundant links outright until a failure forces tree "
        "recalculation. Changing these algorithms in commercial switches is rarely feasible because control "
        "software is closed."
    ),
    _p(
        "Software-Defined Networking separates the control plane from the switching hardware and places "
        "routing logic in a logically centralized software controller. Switches retain fast match-action "
        "forwarding pipelines and expose a standard interface for rule programming. As shown in Figure 2.1, "
        "an operator can switch between shortest-path and congestion-aware policies in one Python module "
        "without reconfiguring individual devices. Once the controller installs rules, switches forward "
        "subsequent matching packets locally in the data plane."
    ),
    {
        "type": "figure",
        "id": "Figure 2.1",
        "file": "fig_2_1_trad_vs_sdn.png",
        "caption": (
            "Figure 2.1: Structural comparison between vertically integrated traditional network devices "
            "(distributed control per switch) and Software-Defined Networking (logically centralized control "
            "programming match-action data-plane switches)."
        ),
        "width_in": 6.1,
        "border": False,
    },
    _p(
        "This separation grew out of three research milestones before industry standardization. The 4D "
        "architecture [2] divided network control into Decision, Dissemination, Discovery, and Data planes, "
        "matching the exact pipeline in our controller where LLDP discovery feeds centralized path selection "
        "and rule dissemination. Ethane [1] then proved centralized flow-level access policy on a live "
        "enterprise network using simple flow switches. To bring programmable flow tables to commercial ASICs "
        "without exposing proprietary internals, Stanford researchers introduced OpenFlow [3], and the Open "
        "Networking Foundation (ONF) later standardized the protocol, producing the OpenFlow 1.3.5 "
        "specification [4] used in this project."
    ),

    # ---- 2.2 (~300 words + Fig 2.2) ----
    _h2("2.2 Three-Layer SDN Architecture and Control Interfaces"),
    _p(
        "SDN organizes network control into three horizontal layers joined by explicit interfaces [5], as "
        "depicted in Figure 2.2. The infrastructure (data) layer contains physical or virtual switches that "
        "hold flow entries, forward or rewrite packets, and increment byte and packet counters. The control "
        "layer acts as the network operating system: it maintains the live graph of switches, links, and "
        "hosts, gathers statistics, and translates routing decisions into switch rules. The application layer "
        "sits above the controller, hosting load balancers, firewalls, and monitoring dashboards that consume "
        "abstract network state."
    ),
    {
        "type": "figure",
        "id": "Figure 2.2",
        "file": "fig_2_2_sdn_3layer.png",
        "caption": (
            "Figure 2.2: Three-layer SDN architecture showing the Infrastructure, Control, and Application "
            "layers together with Southbound (OpenFlow 1.3), Northbound (REST/JSON), and East-West "
            "inter-controller interfaces."
        ),
        "width_in": 6.1,
        "border": False,
    },
    _p(
        "Southbound interfaces connect the control layer to switches. Our system uses OpenFlow 1.3 over TCP "
        "port 6653 to push flow modifications, issue barrier checks, poll counters, and receive asynchronous "
        "switch events; protocols such as OVSDB, NETCONF, and P4Runtime cover bridge configuration or custom "
        "pipelines. Northbound interfaces expose controller abstractions to applications and operators, most "
        "commonly through RESTful HTTP/JSON APIs. Our controller embeds an Eventlet WSGI server on "
        "`127.0.0.1:8080` serving `/topology`, `/links`, `/flows`, `/sdn/status`, `/sdn/hosts`, and "
        "`/sdn/bandwidth` for experiment scripts and the local web dashboard. East-west interfaces link peer "
        "controller nodes in multi-instance clusters to synchronize topology and switch ownership; our "
        "single-process lab controller has no east-west replication."
    ),
    _p(
        "Logical centralization differs from physical centralization [5]. Applications write against a single "
        "coherent network graph, yet production networks distribute the controller across a replicated server "
        "cluster so one machine failure does not stall flow setup. Even on one host, the controller's view "
        "trails live wire traffic by one polling period and TCP queue delay. Our load balancer accounts for "
        "that lag by checking sample freshness, smoothing utilization across ticks, and waiting for barrier "
        "replies before cutting traffic over."
    ),

    # ---- 2.3 (~680 words + Fig 2.3, Fig 2.4, Fig 2.5, Table 2.1) ----
    _h2("2.3 OpenFlow Protocol Architecture and Captured Lab Behavior"),
    _p(
        "OpenFlow defines a switch pipeline model and a binary wire protocol [3], [4]. OpenFlow 1.0 offered a "
        "single flow table with 12 fixed IPv4/Ethernet match fields, which simplified early prototypes but "
        "caused rule explosion when combining routing and ACLs. OpenFlow 1.3 [4] established the production "
        "baseline with multi-table pipelines, extensible OXM match fields (adding IPv6 and MPLS), group "
        "tables (Select, All, Fast-Failover), meter tables for rate limiting, auxiliary connections, and "
        "multipart statistics (`OFPMP_*`). OpenFlow 1.5 later added egress tables and scheduled bundles. "
        "Every Open vSwitch bridge in this project explicitly negotiates `OpenFlow13`."
    ),
    _h3("Switch Pipeline and Flow-Entry Anatomy"),
    _p(
        "An OpenFlow 1.3 switch maintains a TCP/TLS channel to the controller, numbered flow tables, and "
        "optional group and meter tables [4]. Figure 2.3 shows the pipeline and flow-entry fields. Each entry "
        "stores OXM match fields, a 16-bit priority, packet and byte counters, instructions, idle and hard "
        "timeouts, and a 64-bit controller cookie. Incoming packets enter Table 0, match the highest-priority "
        "qualifying entry, update counters, and execute instructions (`OFPIT_APPLY_ACTIONS`, "
        "`OFPIT_WRITE_ACTIONS`, `OFPIT_METER`, or `OFPIT_GOTO_TABLE`). Unlike OpenFlow 1.0, OpenFlow 1.3 "
        "drops unmatched packets by default unless the controller installs a priority-0 wildcard table-miss "
        "entry forwarding to `OFPP_CONTROLLER`. Our controller installs that table-miss rule at handshake and "
        "places managed IPv4 host-pair rules in Table 0 at priority 20 and above."
    ),
    {
        "type": "figure",
        "id": "Figure 2.3",
        "file": "fig_2_3_of13_pipeline.png",
        "caption": (
            "Figure 2.3: OpenFlow 1.3 multi-table match-action pipeline showing packet lookup from Table 0 "
            "through subsequent tables, table-miss handling, action-set execution, group/meter processing, "
            "and flow-entry fields."
        ),
        "width_in": 6.1,
        "border": False,
    },
    _h3("Message Classes and Reactive versus Proactive Forwarding"),
    _p(
        "OpenFlow 1.3 messages fall into three classes [4]. Symmetric messages (`OFPT_HELLO`, "
        "`OFPT_ECHO_REQUEST/REPLY`) originate from either side for version negotiation and keepalives. "
        "Controller-to-switch messages inspect or change state: `OFPT_FEATURES_REQUEST`, `OFPT_FLOW_MOD`, "
        "`OFPT_PACKET_OUT`, `OFPT_MULTIPART_REQUEST` (`OFPMP_PORT_DESC`, `OFPMP_PORT_STATS`, `OFPMP_FLOW`, "
        "replacing OpenFlow 1.0 `OFPST_*` names), and `OFPT_BARRIER_REQUEST`, which forces a switch to finish "
        "all earlier commands before returning `OFPT_BARRIER_REPLY`. Asynchronous messages (`OFPT_PACKET_IN`, "
        "`OFPT_PORT_STATUS`, `OFPT_FLOW_REMOVED`, `OFPT_ERROR`) report switch events upward."
    ),
    _p(
        "Reactive control installs rules only when an unmatched packet triggers `OFPT_PACKET_IN`, saving table "
        "space at the cost of first-packet latency and control-channel load. Proactive control pre-installs "
        "rules before packets arrive, avoiding setup delay while occupying more entries. Our controller uses "
        "reactive handling for ARP and host discovery, paired with proactive multi-hop rule installation for "
        "discovered IPv4 host pairs and congestion reroutes."
    ),
    _h3("Wireshark Verification of OpenFlow 1.3 Control Traffic (C1)"),
    _p(
        "For Common Core C1, we captured loopback traffic on TCP port 6653 (`c1-linear-rerun.pcapng`) over a "
        "two-switch linear topology (`S1-S2`, hosts `H1` and `H2`) controlled by OS-Ken. Figure 2.4 shows the "
        "filtered trace (`tcp.port == 6653 && tcp.len > 0`). Because both switches connect to `127.0.0.1:6653` "
        "from separate ephemeral ports, frames interleave: Frame 34 sends `OFPT_HELLO` (`OpenFlow 1.3`, 8-byte "
        "payload), frames 48 and 50 return `OFPT_FEATURES_REPLY` for datapaths 1 and 2, frames 51 to 56 "
        "exchange `OFPMP_PORT_DESC` port lists, frames 52 and 54 install the priority-0 table-miss "
        "`OFPT_FLOW_MOD` rules, and frames 79, 81, and 123 show initial `OFPT_PACKET_IN` and `OFPT_PACKET_OUT` "
        "exchanges."
    ),
    {
        "type": "figure",
        "id": "Figure 2.4",
        "file": "shot_c1_wireshark_overview.png",
        "caption": (
            "Figure 2.4: Authentic Wireshark capture (`c1-linear-rerun.pcapng`, filter `tcp.port == 6653 && "
            "tcp.len > 0` on `lo`) showing OpenFlow 1.3 handshake (`OFPT_HELLO`, `OFPT_FEATURES_REQUEST/REPLY`), "
            "`OFPMP_PORT_DESC` multipart queries, initial table-miss `OFPT_FLOW_MOD`, and `OFPT_PACKET_IN/OUT`."
        ),
        "width_in": 6.1,
        "border": True,
    },
    _p(
        "Table 2.1 lists the startup handshake and the reactive ICMP Echo Request sequence later in the same "
        "capture. On S1, frame 448 punts H1's first Echo Request via `OFPT_PACKET_IN`, frame 449 installs the "
        "matching `OFPT_FLOW_MOD`, and frame 450 releases the packet via `OFPT_PACKET_OUT`; S2 repeats those "
        "three steps in frames 452 to 454, after which all three pings succeed directly in the data plane."
    ),
    {
        "type": "table",
        "id": "Table 2.1",
        "caption": "Table 2.1: Observed OpenFlow 1.3 Control-Plane Sequence in C1 Capture (`c1-linear-rerun.pcapng`).",
        "headers": ["Frame(s)", "Switch", "OpenFlow 1.3 Message", "Observed Role in Capture"],
        "rows": [
            ["34, 39, 41, 44", "S1, S2", "`OFPT_HELLO`", "Negotiates OpenFlow 1.3 (`0x04`) over TCP port 6653 on `lo`."],
            ["43, 46, 48, 50", "S1, S2", "`OFPT_FEATURES_REQUEST/REPLY`", "Returns datapath IDs 1 and 2 and switch capabilities."],
            ["51, 53, 55, 56", "S1, S2", "`OFPMP_PORT_DESC` (Req/Rep)", "Enumerates active switch ports, MAC addresses, and speeds."],
            ["52, 54", "S1, S2", "`OFPT_FLOW_MOD` (`OFPFC_ADD`)", "Installs priority-0 wildcard table-miss entry sending misses to controller."],
            ["448", "S1", "`OFPT_PACKET_IN`", "Escalates unmatched H1-to-H2 ICMP Echo Request arriving on S1 port 1."],
            ["449", "S1", "`OFPT_FLOW_MOD` (`OFPFC_ADD`)", "Installs Table 0 rule matching ingress port 1 and H2 MAC to output port 2."],
            ["450", "S1", "`OFPT_PACKET_OUT`", "Forwards the triggering first ICMP packet out S1 port 2 toward S2."],
            ["452-454", "S2", "`PACKET_IN` / `FLOW_MOD` / `PACKET_OUT`", "Repeats reactive install on S2 (ingress port 2 to output port 1 for H2)."],
        ],
        "col_widths_mm": [24, 18, 48, 76],
    },
    _p(
        "Figure 2.5 dissects Frame 466 (`OFPT_FLOW_MOD`, 96-byte OpenFlow payload), confirming version "
        "`1.3 (0x04)`, type `14`, `Table ID: 0`, command `OFPFC_ADD (0)`, `Priority: 1`, `OFP_NO_BUFFER`, zero "
        "timeouts, and the OXM `Match` and `Instruction` fields on the wire."
    ),
    {
        "type": "figure",
        "id": "Figure 2.5",
        "file": "shot_c1_wireshark_flowmod.png",
        "caption": (
            "Figure 2.5: Wireshark protocol dissection of an OpenFlow 1.3 `OFPT_FLOW_MOD` (`OFPFC_ADD`) "
            "frame captured on `lo:6653`, showing version `0x04`, Table ID 0, priority, `OFP_NO_BUFFER`, "
            "cookie, match, and instruction sections."
        ),
        "width_in": 5.2,
        "border": True,
    },

    # ---- 2.4 (~240 words + Table 2.2) ----
    _h2("2.4 SDN Controllers and Platform Selection"),
    _p(
        "An SDN controller combines TCP/TLS session handling, binary protocol codecs, an event dispatcher "
        "(`EventOFPPacketIn`, `EventOFPPortStatsReply`, `EventOFPBarrierReply`), a topology store, and "
        "application APIs. Because handlers share an event loop, periodic polling runs in a separate greenlet, "
        "and datapath IDs paired with transaction IDs (`xid`) match incoming replies and barriers to their "
        "originating requests. Table 2.2 compares five open-source controllers against the Track 1 lab needs."
    ),
    {
        "type": "table",
        "id": "Table 2.2",
        "caption": "Table 2.2: Comparison of Open-Source SDN Controllers and Selection Rationale for Track 1.",
        "headers": ["Controller", "Language", "OpenFlow", "Architecture & Concurrency", "Suitability for Track 1 Lab"],
        "rows": [
            [
                "POX",
                "Python",
                "1.0 only",
                "Single-process event loop; teaching framework derived from NOX.",
                "Ruled out: lacks OpenFlow 1.3 multi-table, OXM, multipart (`OFPMP_*`), and barrier workflows.",
            ],
            [
                "Ryu / OS-Ken [6]",
                "Python",
                "1.0-1.5",
                "Event-driven with Eventlet green threads; clean Python `ofproto_v1_3` parser and REST support.",
                "Selected (OS-Ken 3.1.1): maintained OpenStack fork of Ryu with full Python 3.10+ and OF 1.3 support.",
            ],
            [
                "ONOS [7]",
                "Java",
                "1.0, 1.3",
                "Distributed OSGi cluster with Raft consensus, intent framework, and carrier-grade scale.",
                "Heavy JVM/cluster footprint exceeds single-VM scope; good reference for clustered failover.",
            ],
            [
                "OpenDaylight [8]",
                "Java",
                "1.0, 1.3",
                "Model-Driven SAL (MD-SAL) using YANG schemas, multi-protocol plugins (NETCONF, BGP, OVSDB).",
                "High memory overhead and steep YANG complexity for single-VM algorithm prototyping.",
            ],
            [
                "Floodlight",
                "Java",
                "1.0-1.4",
                "Modular Java framework using Netty I/O threads and Jackson REST endpoints.",
                "Solid OpenFlow 1.3 support, but slower iteration than Python + NetworkX for Track 1.",
            ],
        ],
        "col_widths_mm": [26, 18, 20, 48, 54],
    },
    _p(
        "Table 2.2 rules out POX immediately because it supports only OpenFlow 1.0 and cannot issue OpenFlow "
        "1.3 multipart queries or strict priority deletes. ONOS [7] and OpenDaylight [8] target carrier "
        "clusters and multi-protocol YANG orchestration, imposing JVM memory overhead that competes with "
        "Mininet inside a single VM. Upstream Ryu suffers from stale packaging on Python 3.10+, so we chose "
        "**OS-Ken 3.1.1** [6], the maintained OpenStack fork of Ryu permitted by the course specification. "
        "OS-Ken provides native `ofproto_v1_3` message objects, built-in LLDP discovery, and direct "
        "integration with `NetworkX` for Yen k = 3 path ranking. Because `os_ken.app.wsgi` is absent in "
        "OS-Ken, we run `eventlet.listen` and `eventlet.wsgi` directly inside the controller hub to serve "
        "read-only JSON endpoints without inter-process locking."
    ),

    # ---- 2.5 (~340 words) ----
    _h2("2.5 Data-Plane Platforms and Emulation Testbeds"),
    _p(
        "Our data plane runs on **Open vSwitch (OVS)** [9], a multilayer virtual switch split between "
        "`ovs-vswitchd` in user space (handling OpenFlow 1.3 tables and `ovsdb-server` state) and a Linux "
        "kernel megaflow cache that forwards established flows at high speed without user-space copies. OVS "
        "updates exact port and flow counters in kernel space, which our C4 poller reads. Because OVS port TX "
        "counters count full Layer 2 Ethernet frames (headers plus periodic LLDP traffic) while `iperf3` "
        "reports UDP payload rate, port counters naturally sit a few percent above the application sender "
        "rate, explaining the 3.116% calibration offset in Chapter 5."
    ),
    _p(
        "Hardware switches instead run OpenFlow pipelines on merchant silicon ASICs, pairing SRAM hash tables "
        "for exact matches with TCAM arrays for parallel single-cycle wildcard lookups. TCAM delivers "
        "sub-microsecond forwarding at multi-terabit scale, yet its cost, power draw, and finite rule "
        "capacity (often a few thousand wildcard entries) constrain per-flow rule count and update rates. "
        "Software OVS on one VM cannot replicate hardware TCAM limits, so our controller aggregates rules at "
        "the host-pair level and qualifies all benchmarks as emulated VM measurements."
    ),
    _p(
        "Where OpenFlow controls a fixed header set, **P4** [10] makes the switch parser and match-action "
        "tables programmable in software targeting PISA ASICs or BMv2, allowing operators to add custom "
        "telemetry headers without changing protocol specifications. Our project stays within standard OVS "
        "OpenFlow 1.3 tables for full compatibility with the course testbed."
    ),
    _p(
        "We assemble topologies in **Mininet** [11], which places each host in an isolated Linux network "
        "namespace wired to OVS bridges through `veth` links running real Linux TCP/IP stacks and `iperf3`. "
        "Unshaped `veth` links push software TCP bursts to 32-34 Gbps on a shared CPU, starving OS-Ken's "
        "LLDP keepalives and causing spurious link drops. Wrapping inter-switch links in Mininet `TCLink` "
        "(Linux `tc` HTB queues and `netem` delay) enforces 100 Mbps capacity and 2 ms delay per link with "
        "controlled `64k` HTB burst sizing, giving well-defined utilization denominators and repeatable queues."
    ),

    # ---- 2.6 (~610 words, citing [12]-[18]) ----
    _h2("2.6 Related Work on SDN Load Balancing and Fault Tolerance"),
    _p(
        "Seven seminal systems [12]-[18] define the design space for multi-path load balancing, consistent "
        "rule updates, and link-failure recovery, and directly frame our Track 1 choices."
    ),
    _h3("Data-Center Multi-Path Fabrics and Flow Scheduling"),
    _p(
        "Al-Fares, Loukissas, and Vahdat [12] demonstrated that commodity k-port switches wired into a "
        "three-tier fat-tree deliver full bisection bandwidth across (k/2)\u00b2 equal-cost core paths, matching "
        "our 20-switch, 16-host k = 4 test topology. Standard Equal-Cost Multi-Path (ECMP) hashes flows "
        "statically across parallel links with zero controller overhead, but hash collisions frequently place "
        "two large transfers on the same upstream link while parallel links sit underutilized."
    ),
    _p(
        "Hedera [13] resolved ECMP collisions centrally by targeting only *elephant flows* exceeding 10% of "
        "host NIC rate, leaving short *mice* flows on default ECMP paths while computing global placements "
        "(Global First Fit or Simulated Annealing) from periodic switch counter polls. Our controller adopts "
        "Hedera's elephant-only trigger directly (host pairs above 10% link capacity for two consecutive "
        "polls), while replacing global matrix optimization with deterministic Yen k = 3 candidate path "
        "ranking suited to our grid scale."
    ),
    _p(
        "MicroTE [14] showed from data-center traces that traffic matrices stay predictable only over short "
        "windows of a few seconds, meaning slow polling leads to stale reroutes. MicroTE applies fine-grained "
        "TE only to predictable pairs and uses weighted ECMP elsewhere. Our Chapter 5 sensitivity trials show "
        "this exact trade-off: reducing T from 5 s to 2 s cuts detection time from 18.93 s to 6.95 s, while "
        "EWMA smoothing (\u03b1 = 0.5) and two-period persistence reject transient bursts at the price of a "
        "bounded detection lag."
    ),
    _p(
        "CONGA [15] pushed congestion-aware load balancing into leaf-spine ASICs, steering TCP *flowlets* "
        "using VXLAN feedback within one RTT. Contrasting CONGA with centralized OpenFlow 1.3 explains our "
        "Chapter 5 benchmarks: multi-second host-pair rerouting relieves sustained asymmetric bottlenecks "
        "(85 + 30 Mbps grid trials) yet cannot beat proactive hash spreading on ten balanced flows."
    ),
    _h3("Consistent Updates, Wide-Area Engineering, and Failure Recovery"),
    _p(
        "Reitblatt et al. [16] formalized *per-packet consistency* via version-tagged two-phase commits so "
        "packets in flight never traverse mixed old/new rules. Our controller applies a single-flow "
        "make-before-break variant using OpenFlow 1.3 priorities and barriers: rules install from egress back "
        "to ingress at priority 21 with `OFPT_BARRIER_REQUEST/REPLY` confirmation per switch before ingress "
        "switches over and old priority-20 rules are deleted via `OFPFC_DELETE_STRICT`. This avoids blackhole "
        "windows on sequential moves without claiming full concurrent multi-flow two-phase versioning."
    ),
    _p(
        "Google B4 [17] proved centralized OpenFlow traffic engineering across inter-datacenter WANs, "
        "allocating link shares centrally to drive long-haul links near saturation while protecting priority "
        "traffic during outages. Though far larger in scale, B4 rests on the same premise as our controller: "
        "global link and flow visibility unlocks parallel bandwidth that static shortest-path routing wastes."
    ),
    _p(
        "Sharma et al. [18] contrasted reactive OpenFlow *restoration* (controller detects link loss via "
        "`OFPT_PORT_STATUS` or LLDP, recomputes paths, and pushes `FLOW_MOD` rules in tens to hundreds of "
        "milliseconds) with proactive *protection* using OpenFlow 1.3 `OFPGT_FF` fast-failover groups and "
        "local BFD for sub-50 ms switchover. Our controller implements reactive restoration via "
        "`EventLinkDelete` and `EventSwitchLeave`, achieving 73.14 \u00b1 21.63 ms host-visible recovery "
        "across five runs; fast-failover group tables remain future work in Chapter 6."
    ),

    # ---- 2.7 (~270 words + Table 2.3) ----
    _h2("2.7 Reliability, Scalability, and Security"),
    _p(
        "Centralizing control in software creates failure modes and attack surfaces absent in autonomous "
        "routers [5]. A single controller instance is a single point of failure (SPOF): if it disconnects, "
        "switches in `fail-secure` mode keep existing rules but drop unmatched traffic, whereas "
        "`fail-standalone` reverts to basic MAC learning. Production deployments run multi-node clusters "
        "(such as ONOS [7]) with Raft replication and OpenFlow 1.3 `OFPT_ROLE_REQUEST` master/slave roles "
        "[4], placing nodes close to switches to bound control latency [18]. Polling scalability adds "
        "O(N/T) multipart exchanges across N switches, which can compete with `PACKET_IN` and LLDP "
        "handling when T is too small."
    ),
    _p(
        "Three security threats specifically target SDN [5]: control-plane DoS (`PACKET_IN` floods exhausting "
        "controller CPU), flow-table or TCAM exhaustion from micro-flow storms, and topology poisoning via "
        "forged or relayed LLDP frames on host ports. Unencrypted OpenFlow TCP sessions and unauthenticated "
        "REST endpoints further risk rule tampering. Table 2.3 maps each threat to its production defense and "
        "states honestly what our lab controller enforces."
    ),
    {
        "type": "table",
        "id": "Table 2.3",
        "caption": "Table 2.3: SDN Reliability, Scalability, and Security Risks with Countermeasures and Lab Scope.",
        "headers": ["Threat / Risk", "Failure or Attack Mechanism", "Production Countermeasure", "Status in Lab Controller"],
        "rows": [
            [
                "Controller SPOF",
                "Controller crash halts new flow installs, rerouting, and failure recovery.",
                "Multi-node cluster with Raft state sync and OpenFlow 1.3 master/slave role election [4], [7].",
                "Single OS-Ken instance; existing switch rules continue forwarding during transient pauses.",
            ],
            [
                "Control-plane DoS (`PACKET_IN` flood)",
                "Spoofed unmatched traffic saturates controller CPU and OpenFlow TCP queue.",
                "Switch-side OpenFlow meter tables rate-limiting `OFPP_CONTROLLER` punts; proactive rules.",
                "Proactive multi-hop IPv4 installs and proxy ARP reduce steady-state `PACKET_IN` volume.",
            ],
            [
                "Flow-table / TCAM exhaustion",
                "Micro-flow storms fill hardware TCAM and block legitimate `FLOW_MOD` entries.",
                "Coarse flow aggregation, idle/hard timeouts, per-port quotas, and table-eviction flags.",
                "Coarse directed IPv4 MAC-pair rules keep table size O(H\u00b2) instead of per-socket 5-tuples.",
            ],
            [
                "Fake LLDP topology poisoning",
                "Compromised host injects or relays LLDP frames to forge false switch adjacencies.",
                "Cryptographic HMAC TLVs in LLDP packets; drop LLDP on host-facing access ports.",
                "Standard OS-Ken LLDP discovery on trusted Mininet links; port filtering is production work.",
            ],
            [
                "Southbound / Northbound tampering",
                "Eavesdropping or unauthorized writes on TCP 6653 or HTTP REST endpoints.",
                "Mutual TLS (mTLS) on OpenFlow channel; HTTPS with token/RBAC auth on northbound API.",
                "Loopback-only (`127.0.0.1`) OpenFlow and read-only HTTP REST; no external network exposure.",
            ],
            [
                "Polling & LLDP churn under load",
                "Excessive stats polling or unshaped host bursts starve LLDP keepalives on shared CPU.",
                "Dedicated control network, bounded polling cadence T, and hardware-assisted BFD/FF groups.",
                "Bounded `TCLink` shaping (100 Mbps) and configurable T = 2 s polling; fat-tree LLDP churn noted in Ch. 5.",
            ],
        ],
        "col_widths_mm": [28, 44, 50, 44],
    },

    # ---- 2.8 (~260 words) ----
    _h2("2.8 Practical SDN Applications"),
    _p(
        "Production networks deploy SDN across six major domains where centralized visibility solves "
        "concrete traffic-management problems. In cloud data centers, controllers pair virtual overlays "
        "(VXLAN or Geneve) with underlay congestion monitoring to steer elephant flows off saturated spines "
        "[13] or coordinate hardware load balancing [15] across isolated tenants. In Software-Defined WANs "
        "(SD-WAN), controllers continuously probe MPLS, fiber, and broadband circuits, assigning interactive "
        "traffic to low-jitter links while bulk transfers fill residual capacity, as shown globally by Google "
        "B4 [17]."
    ),
    _p(
        "SDN also anchors Network Functions Virtualization (NFV) and 5G transport slicing. When firewalls, "
        "NAT gateways, and intrusion sensors run as virtualized software instances, OpenFlow or P4 rules "
        "steer traffic through ordered service chains and bypass failed instances automatically. In 5G "
        "backhaul, transport slicing isolates high-throughput broadband (eMBB), ultra-reliable low-latency "
        "links (URLLC), and massive IoT (mMTC) with separate queues, meters, and disjoint paths coordinated "
        "with radio and core orchestrators."
    ),
    _p(
        "Two newer paradigms extend SDN automation further. Intent-Based Networking (IBN) compiles declarative "
        "policies (reachability, isolation, or utilization bounds) into verified switch states with closed-loop "
        "telemetry checks. Machine-learning-assisted traffic engineering applies flow classifiers and demand "
        "forecasters to anticipate congestion early, though closed-loop distribution shift makes opaque models "
        "harder to debug when routing changes alter future traffic. Our project uses deterministic EWMA "
        "thresholds, Yen path ranking, and barrier-ordered updates so every decision is auditable from counter "
        "logs. Chapter 3 details that design."
    ),
]


CHAPTERS_PART1 = [
    {"number": 1, "title": "Introduction", "blocks": CH1_BLOCKS},
    {"number": 2, "title": "Software-Defined Networking Background", "blocks": CH2_BLOCKS},
]
