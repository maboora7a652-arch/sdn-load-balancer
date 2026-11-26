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
        "appendices covering deployment commands, the team roster, and repository records."
    ),
]


# ---------------------------------------------------------------------------
# Chapter 2: Software-Defined Networking Background (10-12 pages)
# Covers all 8 mandatory subtopics 11.1-11.8 across 2.1-2.8 with 5 figures,
# 4 tables, and all 18 canonical IEEE citations [1]-[18].
# ---------------------------------------------------------------------------
CH2_BLOCKS = [
    # ---- 2.1 Traditional Networks vs SDN & Historical Evolution ----
    _h2("2.1 Traditional Networks versus SDN and Historical Evolution"),
    _p(
        "In a conventional IP router or Ethernet switch, packet forwarding and routing intelligence reside "
        "inside the same physical chassis. Three functional planes are tightly coupled inside proprietary "
        "firmware: the data plane parses headers and forwards frames at line rate across switch silicon, the "
        "control plane executes distributed routing and spanning-tree protocols to compute local forwarding "
        "tables, and the management plane exposes vendor-specific command-line interfaces (CLIs) or SNMP MIBs "
        "for operator configuration. Translating a single network-wide traffic policy into production state "
        "requires pushing low-level, device-specific syntax to dozens of heterogeneous boxes, a manual workflow "
        "that makes configuration drift and human error routine."
    ),
    _p(
        "Distributed control protocols provide reliable reachability and loop avoidance, yet they systematically "
        "underuse redundant physical links. Under Open Shortest Path First (OSPF), every router floods link-state "
        "advertisements across an area and executes Dijkstra's shortest-path-first algorithm independently on a "
        "shared metric graph. Because administrative link weights are static unless an operator re-tunes them "
        "manually, OSPF pins all traffic for a destination onto one lowest-cost route regardless of instantaneous "
        "queue occupancy; when a link fails, neighbors must detect the timeout, flood new link-state advertisements, "
        "and recompute shortest-path trees independently before forwarding stabilizes. At Layer 2, the Spanning "
        "Tree Protocol (STP) eliminates broadcast storms by logically blocking redundant switch ports until a "
        "primary path fails. On our six-switch lab grid, STP would block links on the lower row (`S1-S4-S5-S6`) "
        "outright, cutting bisection capacity in half even when both paths are healthy. Modifying these embedded "
        "protocols inside commercial switches is rarely possible because control software is closed and tied to "
        "vendor release cycles, creating long-term vendor lock-in and slow innovation."
    ),
    _p(
        "Software-Defined Networking (SDN) breaks this vertical integration by decoupling the control plane from "
        "the switching hardware and migrating routing decisions into a logically centralized software controller "
        "[5]. Data-plane devices retain high-speed match-action forwarding pipelines and expose a standardized, "
        "open programming interface. As illustrated in Figure 2.1, an operator can switch an entire network from "
        "static shortest-path forwarding to congestion-aware elephant rerouting by updating one Python module "
        "rather than touching individual switch operating systems. Critically, decoupling does not force every "
        "packet through the controller: once rules are installed in switch flow tables, matching packets continue "
        "flowing directly through the data plane at switch forwarding speed."
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
        "Modern SDN emerged through a clear sequence of academic and standardization milestones. First, the 4D "
        "architecture [2] argued that legacy routing complexity stemmed from burying network-wide objectives inside "
        "distributed per-router protocols, and proposed refactoring network control into four clean planes: a "
        "Decision plane computing global paths, a Dissemination plane carrying rules to switches, a Discovery plane "
        "tracking physical topology, and a Data plane forwarding packets. That four-part split maps directly onto "
        "our Track 1 controller, where LLDP discovery feeds centralized path ranking and barrier-gated rule "
        "dissemination. Second, Ethane [1] validated centralized flow-level control on a live university enterprise "
        "network of several hundred hosts, proving that a central controller could enforce explicit per-flow access "
        "and routing policy over simple flow-table switches with modest setup overhead."
    ),
    _p(
        "Deploying programmable flow tables on commercial switches still required a common abstraction that switch "
        "vendors could implement without exposing proprietary ASIC internals. Stanford researchers addressed that "
        "gap with OpenFlow [3], recognizing that Ethernet switches, IP routers, and firewalls from different "
        "vendors already shared an internal TCAM-based flow table capable of matching packet headers and applying "
        "actions. OpenFlow exported a standard wire protocol to program those tables remotely while keeping packet "
        "forwarding in silicon. Industry adoption accelerated once the Open Networking Foundation (ONF) took over "
        "stewardship of the specification, evolving it from academic version 1.0 to the OpenFlow 1.3.5 baseline "
        "[4] deployed across our Mininet and Open vSwitch testbed."
    ),

    # ---- 2.2 Three-Layer SDN Architecture & Control Interfaces ----
    _h2("2.2 Three-Layer SDN Architecture and Control Interfaces"),
    _p(
        "SDN organizes network functionality into three horizontal planes separated by well-defined interfaces "
        "[5], as shown in Figure 2.2. At the bottom, the infrastructure (data) layer consists of physical ASIC "
        "switches or virtual switches such as Open vSwitch. Switches hold flow, group, and meter entries, match "
        "arriving headers, execute forwarding or rewrite actions, maintain exact byte and packet counters, and "
        "report link or packet exceptions upward. In the middle, the control layer functions as a network "
        "operating system (NOS): it maintains the authoritative graph of switches, directed links, and host "
        "attachments, collects periodic telemetry, resolves ARP or reachability queries, and translates abstract "
        "forwarding intent into low-level switch rules. At the top, the application layer hosts modular network "
        "services, including congestion-aware load balancers, access-control filters, traffic-engineering "
        "planners, and monitoring dashboards that read and manipulate network state without parsing raw wire "
        "protocols."
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
        "Three interface families govern communication across and within these layers [5]. Southbound interfaces "
        "(SBIs) bridge the control layer and infrastructure switches. Our controller uses OpenFlow 1.3 over TCP "
        "port 6653 to install and delete flow rules, synchronize rule installation with barrier messages, poll "
        "multipart port and flow statistics, and receive asynchronous packet and topology notifications. Alongside "
        "OpenFlow, production environments pair complementary management SBIs such as OVSDB for creating virtual "
        "bridges and shaping queues, NETCONF/YANG for device configuration, and P4Runtime for switches with "
        "custom programmable pipelines [10]."
    ),
    _p(
        "Northbound interfaces (NBIs) expose the controller's global view to applications and external tooling. "
        "Unlike the southbound layer, no single NBI standard dominates; controllers combine in-process Python or "
        "Java event APIs for low-latency control loops with HTTP/JSON REST APIs for external dashboards and "
        "orchestration scripts. In our system, the load-balancing engine runs in-process inside the OS-Ken "
        "controller to react directly to statistics replies and link-delete events, while an embedded Eventlet "
        "WSGI server on `127.0.0.1:8080` serves read-only JSON endpoints (`/topology`, `/links`, `/flows`, "
        "`/sdn/status`, `/sdn/hosts`, and `/sdn/bandwidth`) consumed by both our experiment scripts and the local "
        "web dashboard on port 8081. East-west interfaces connect peer controller instances in clustered "
        "deployments so separate servers share topology graphs, host tables, and switch ownership using either "
        "strong consensus protocols such as Raft [7] or eventual gossip synchronization. Because our coursework "
        "runs inside a single virtual machine, our implementation operates as a single OS-Ken process without "
        "east-west replication."
    ),
    _p(
        "A core SDN principle is that logical centralization is distinct from physical centralization [5]. "
        "Applications always reason over one consistent network graph rather than exchanging distributed routing "
        "messages, yet carrier networks deploy multiple controller servers physically to avoid single-node "
        "bottlenecks and machine failures. Three further principles follow from this separation: direct "
        "programmability of forwarding state, vendor-neutral hardware abstraction, and closed-loop automated "
        "control driven by switch telemetry. Even on one physical host, however, the controller's view trails "
        "wire reality by one polling interval plus OpenFlow TCP serialization and greenlet scheduling latency. "
        "Our controller explicitly accounts for this visibility lag through monotonic timestamps, sample-freshness "
        "checks, two-period persistence filters, and barrier-confirmed updates before cutting traffic over."
    ),

    # ---- 2.3 OpenFlow Protocol Deep-Dive & C1 Wireshark Verification ----
    _h2("2.3 OpenFlow Protocol Architecture and Captured Lab Behavior"),
    _p(
        "OpenFlow defines both an abstract switch forwarding model and a binary TCP/TLS control protocol [3], "
        "[4]. Its specification matured significantly across major releases. OpenFlow 1.0 (2009) exposed a single "
        "flat flow table with 12 fixed Ethernet, VLAN, IPv4, and TCP/UDP match fields; while straightforward for "
        "early campus prototypes, placing Layer 2 switching, Layer 3 routing, and security filters in one table "
        "triggered cross-product rule explosion. OpenFlow 1.3 [4] became the dominant production baseline by "
        "introducing multi-table pipelines, extensible OpenFlow Extensible Match (OXM) TLV fields supporting IPv6 "
        "and MPLS, group tables for multi-path and failover actions, per-flow meter tables for QoS rate limiting, "
        "auxiliary UDP/TCP control channels, and multipart statistics messages (`OFPMP_*`). OpenFlow 1.5 later "
        "extended the model with egress processing tables, packet-type-aware pipelines, and scheduled atomic "
        "bundles. Every Open vSwitch bridge in our Mininet topologies explicitly negotiates `OpenFlow13`."
    ),
    _h3("Switch Components, Pipeline Processing, and Flow-Entry Anatomy"),
    _p(
        "An OpenFlow 1.3 switch contains four architectural subsystems: an OpenFlow channel connecting over TCP "
        "or TLS to one or more controllers, one or more numbered flow tables (`Table 0` through `Table N`), a "
        "group table for shared action buckets, and a meter table for rate-based packet policing or DSCP "
        "remarking [4]. Figure 2.3 depicts the resulting multi-table match-action pipeline and the structure of a "
        "single flow entry. When a packet arrives on an ingress port, lookup always starts at Table 0. The switch "
        "compares extracted header fields and metadata against all flow entries in the table and selects the "
        "highest-priority matching rule. Upon a match, the switch increments the entry's packet and byte counters "
        "and executes its instructions, which may apply actions immediately (`OFPIT_APPLY_ACTIONS`), append "
        "deferred actions to the packet's action set (`OFPIT_WRITE_ACTIONS`), clear pending actions "
        "(`OFPIT_CLEAR_ACTIONS`), attach a rate meter (`OFPIT_METER`), or forward the packet to a higher-numbered "
        "table (`OFPIT_GOTO_TABLE`). Once pipeline traversal ends, the switch executes the accumulated action set "
        "in specification order (copy/set header fields, push/pop tags, apply QoS queue, and finally output to a "
        "physical port, logical port, or group)."
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
    _p(
        "Table 2.1 summarizes the exact OpenFlow 1.3 flow-entry fields, action categories, and group types "
        "defined in [4], together with how our Track 1 controller uses or omits each feature. A critical semantic "
        "change introduced in OpenFlow 1.3 concerns unmatched packets: whereas OpenFlow 1.0 automatically punted "
        "table misses to the controller, OpenFlow 1.3 drops unmatched packets by default unless the controller "
        "explicitly installs a priority-0 wildcard table-miss entry directing traffic to `OFPP_CONTROLLER`. Our "
        "controller installs that table-miss entry during `EventOFPSwitchFeatures` and reserves priorities 20 and "
        "above in Table 0 for managed IPv4 host-pair forwarding rules, allowing higher-priority reroute entries "
        "(priority 21, 22, ...) to shadow older entries cleanly during make-before-break transitions."
    ),
    {
        "type": "table",
        "id": "Table 2.1",
        "caption": "Table 2.1: OpenFlow 1.3 Switch Entry Components, Actions, and Usage in the Track 1 Controller [4].",
        "headers": ["Component", "Specification Role (OpenFlow 1.3.5)", "Usage in Track 1 Controller"],
        "rows": [
            [
                "Match fields (OXM)",
                "Extensible TLV tuples matching ingress port, Ethernet, VLAN, IPv4/IPv6, TCP/UDP, and metadata.",
                "Matches `in_port`, `eth_type=0x0800`, `eth_src`, and `eth_dst` for directed IPv4 host pairs.",
            ],
            [
                "Priority (16-bit)",
                "Resolves overlapping matches (0 to 65,535); highest numeric priority wins in a table.",
                "Priority 0 for table-miss; priority 20 for initial Dijkstra/ECMP paths; 21+ for managed reroutes.",
            ],
            [
                "Counters",
                "Per-table, per-flow, per-port, and per-group packet, byte, and duration counters.",
                "Polled via `OFPMP_PORT_STATS` (utilization) and `OFPMP_FLOW` (ingress elephant detection).",
            ],
            [
                "Instructions & Actions",
                "`APPLY_ACTIONS`, `WRITE_ACTIONS`, `GOTO_TABLE`, `METER`; actions include Output, Set-Field, Drop.",
                "Uses `OFPIT_APPLY_ACTIONS` with `OFPActionOutput` to a specific switch port or `OFPP_CONTROLLER`.",
            ],
            [
                "Timeouts & Cookie",
                "`idle_timeout`, `hard_timeout` for automatic eviction; 64-bit `cookie` for controller tagging.",
                "Managed host-pair rules stay persistent (`timeout=0`) until replaced by `OFPFC_DELETE_STRICT` or rebuild.",
            ],
            [
                "Group & Meter Tables",
                "`ALL`, `SELECT`, `INDIRECT`, `FAST_FAILOVER` (`OFPGT_FF`) groups; rate-limiting meters.",
                "Not used in current controller; `OFPGT_FF` switch-local protection is documented as future work.",
            ],
        ],
        "col_widths_mm": [32, 68, 66],
    },
    _h3("Message Classes and Reactive versus Proactive Rule Installation"),
    _p(
        "The OpenFlow 1.3 wire protocol partitions messages into three classes [4]. Symmetric messages can be "
        "initiated by either endpoint without solicitation: `OFPT_HELLO` negotiates the highest shared protocol "
        "version (`0x04` for 1.3), `OFPT_ECHO_REQUEST` and `OFPT_ECHO_REPLY` verify channel liveness and bound "
        "control round-trip delay, and `OFPT_EXPERIMENTER` supports vendor extensions. Controller-to-switch "
        "messages query or mutate switch state: `OFPT_FEATURES_REQUEST` discovers the datapath identifier (`dpid`) "
        "and buffer limits, `OFPT_FLOW_MOD` adds, modifies, or strictly deletes entries (`OFPFC_ADD`, "
        "`OFPFC_MODIFY`, `OFPFC_DELETE`, `OFPFC_DELETE_STRICT`), `OFPT_PACKET_OUT` injects controller-generated "
        "frames such as LLDP probes and proxy ARP replies, `OFPT_MULTIPART_REQUEST` retrieves large replies "
        "(`OFPMP_PORT_DESC`, `OFPMP_PORT_STATS`, `OFPMP_FLOW`), and `OFPT_BARRIER_REQUEST` enforces strict "
        "execution ordering by requiring the switch to complete all preceding commands before returning "
        "`OFPT_BARRIER_REPLY`. Asynchronous messages (`OFPT_PACKET_IN`, `OFPT_PORT_STATUS`, `OFPT_FLOW_REMOVED`, "
        "`OFPT_ERROR`) notify the controller of data-plane arrivals, physical port link changes, expired entries, "
        "or failed modifications."
    ),
    _p(
        "SDN controllers balance two rule-installation strategies. Under purely reactive installation, switches "
        "forward every unknown first packet to the controller via `OFPT_PACKET_IN`, and the controller installs "
        "rules on demand. Reactive control minimizes flow-table occupancy when only a small fraction of host pairs "
        "communicate, yet it adds first-packet setup latency and exposes the control channel to burst traffic. "
        "Under purely proactive installation, the controller pushes rules across all switches before packets "
        "arrive, eliminating first-packet punt delay at the cost of pre-populating entries for idle pairs. Our "
        "Track 1 controller adopts a hybrid pattern: ARP discovery and unknown host learning operate reactively "
        "through `OFPT_PACKET_IN`, whereas once a host pair is resolved, the controller installs bidirectional "
        "multi-hop IPv4 rules proactively across the entire path and executes congestion reroutes and link-failure "
        "rebuilds proactively across every affected switch."
    ),
    _h3("Wireshark Verification of OpenFlow 1.3 Control Traffic (C1)"),
    _p(
        "To verify Common Core C1 on real control traffic, we captured the loopback interface (`lo`) on TCP port "
        "6653 (`c1/c1-linear-rerun.pcapng`) using a two-switch linear Mininet topology (`S1-S2`, hosts `H1` and "
        "`H2`) controlled by an OS-Ken learning switch. Figure 2.4 presents the filtered Wireshark view "
        "(`tcp.port == 6653 && tcp.len > 0`). Because both switches open independent TCP connections from separate "
        "ephemeral ports to `127.0.0.1:6653`, startup messages interleave naturally: Frame 34 initiates "
        "`OFPT_HELLO` (`OpenFlow 1.3`, 8-byte payload), frames 48 and 50 return `OFPT_FEATURES_REPLY` carrying "
        "datapath IDs 1 and 2, frames 51 through 56 exchange `OFPMP_PORT_DESC` port inventories, frames 52 and 54 "
        "push the mandatory priority-0 table-miss `OFPT_FLOW_MOD` entries, and frames 79, 81, and 123 record the "
        "first `OFPT_PACKET_IN` and `OFPT_PACKET_OUT` exchanges."
    ),
    {
        "type": "figure",
        "id": "Figure 2.4",
        "file": "shot_c1_wireshark_overview.png",
        "caption": (
            "Figure 2.4: Authentic Wireshark capture (`c1/c1-linear-rerun.pcapng`, filter `tcp.port == 6653 && "
            "tcp.len > 0` on `lo`) showing OpenFlow 1.3 handshake (`OFPT_HELLO`, `OFPT_FEATURES_REQUEST/REPLY`), "
            "`OFPMP_PORT_DESC` multipart queries, initial table-miss `OFPT_FLOW_MOD`, and `OFPT_PACKET_IN/OUT`."
        ),
        "width_in": 6.1,
        "border": True,
    },
    _p(
        "Table 2.2 documents both the startup connection sequence and the reactive ICMP Echo Request flow setup "
        "observed later in the same capture. When H1 pings H2 for the first time, S1 punts the unmatched Echo "
        "Request in frame 448 (`OFPT_PACKET_IN`), the controller installs a Table 0 forwarding rule on S1 in "
        "frame 449 (`OFPT_FLOW_MOD`), and frame 450 releases the original buffered frame via `OFPT_PACKET_OUT`. "
        "Switch S2 repeats the identical three-message sequence in frames 452 to 454; once both directions are "
        "programmed, subsequent ICMP requests and replies traverse S1 and S2 purely in the data plane with 3/3 "
        "ping success and zero further `PACKET_IN` escalations."
    ),
    {
        "type": "table",
        "id": "Table 2.2",
        "caption": "Table 2.2: Observed OpenFlow 1.3 Control-Plane Sequence in C1 Capture (`c1/c1-linear-rerun.pcapng`).",
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
        "Figure 2.5 zooms into the protocol dissection pane for an individual `OFPT_FLOW_MOD` frame (96-byte "
        "OpenFlow payload), confirming wire-level conformance with OpenFlow 1.3.5: version byte `0x04`, message "
        "type `14` (`OFPT_FLOW_MOD`), `Table ID: 0`, command `OFPFC_ADD (0)`, explicit `Priority: 1`, "
        "`OFP_NO_BUFFER (0xffffffff)`, zero idle and hard timeouts, followed by the OXM `Match` TLVs and "
        "`OFPIT_APPLY_ACTIONS` instruction block."
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

    # ---- 2.4 SDN Controllers & Platform Selection ----
    _h2("2.4 SDN Controllers and Platform Selection"),
    _p(
        "Internally, every OpenFlow controller layers five core subsystems [5]: a southbound transport manager "
        "accepting switch TCP/TLS sockets, a binary OpenFlow encoder/decoder, an asynchronous event dispatcher "
        "routing incoming messages (`EventOFPPacketIn`, `EventOFPPortStatsReply`, `EventOFPFlowStatsReply`, "
        "`EventOFPBarrierReply`) to registered handlers, a network state store holding the switch-link graph and "
        "host table, and a northbound API layer. Concurrency design strongly affects both developer ergonomics "
        "and runtime behavior. Python controllers such as Ryu and OS-Ken [6] use cooperative Eventlet greenlets "
        "inside one process, eliminating explicit lock contention across shared graph structures while requiring "
        "handlers to yield during long loops so LLDP keepalives and OpenFlow heartbeats are not starved. "
        "Java-based platforms such as ONOS [7] and OpenDaylight [8] run multi-threaded JVM containers with OSGi "
        "module lifecycles and distributed data stores designed for carrier-scale clusters."
    ),
    _p(
        "Transaction correlation is equally central inside the controller core. Every request sent over OpenFlow "
        "carries a 32-bit transaction ID (`xid`). When our controller executes make-before-break rerouting, it "
        "records the `(datapath_id, xid)` pair of each outgoing `OFPT_BARRIER_REQUEST` and advances to the next "
        "upstream switch only after receiving the exact matching `OFPT_BARRIER_REPLY`. Table 2.3 compares five "
        "widely used open-source controllers against the functional and single-VM resource constraints of Track 1."
    ),
    {
        "type": "table",
        "id": "Table 2.3",
        "caption": "Table 2.3: Comparison of Open-Source SDN Controllers and Selection Rationale for Track 1.",
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
                "Heavy JVM/cluster footprint exceeds single-VM scope; strong reference for clustered failover.",
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
        "Table 2.3 narrows the choice rapidly. POX cannot execute OpenFlow 1.3 multipart statistics or strict "
        "priority deletions. ONOS [7] and OpenDaylight [8] excel in multi-server production deployments, yet their "
        "JVM heap requirements and build toolchains compete directly with Mininet and Open vSwitch inside a single "
        "Ubuntu VM. Floodlight offers clean Java OpenFlow 1.3 bindings, but lacks the direct Python scientific "
        "ecosystem (`NetworkX` for Yen k = 3 simple-path enumeration and rapid experiment integration). Upstream "
        "Ryu has aging packaging dependencies on Python 3.10+, so we selected **OS-Ken 3.1.1** [6], the actively "
        "maintained OpenStack fork of Ryu explicitly permitted by the project specification. OS-Ken preserves the "
        "exact Ryu `ofproto_v1_3` API and built-in LLDP topology module (`os_ken.topology.switches`) while running "
        "cleanly on Ubuntu Python 3.10. Because OS-Ken omits the legacy `os_ken.app.wsgi` wrapper, our controller "
        "spawns `eventlet.listen` and `eventlet.wsgi.server` directly inside its hub, serving `/topology`, "
        "`/links`, `/flows`, and `/sdn/*` JSON snapshots from in-memory dictionaries without inter-process IPC."
    ),

    # ---- 2.5 Data-Plane Platforms & Emulation Testbeds ----
    _h2("2.5 Data-Plane Platforms and Emulation Testbeds"),
    _p(
        "Our data plane is powered by **Open vSwitch (OVS)** [9], an open-source multilayer virtual switch widely "
        "deployed in cloud hypervisors and research testbeds. OVS splits packet processing into two cooperating "
        "layers: `ovs-vswitchd` runs in Linux user space, maintaining the full OpenFlow 1.3 flow tables and "
        "communicating with `ovsdb-server` for persistent bridge/port configuration, while an in-kernel datapath "
        "module caches flattened wildcard *megaflows* for fast-path forwarding. The first packet of a flow misses "
        "the kernel cache and triggers an upcall to `ovs-vswitchd`, which evaluates Table 0 rules and installs a "
        "matching kernel megaflow; subsequent packets forward entirely in kernel space without user-space copies. "
        "OVS updates exact per-port and per-flow packet and byte counters inside the kernel datapath. Because OVS "
        "port TX counters tally complete Layer 2 Ethernet frames (14-byte Ethernet, 20-byte IPv4, and 8-byte UDP "
        "headers plus periodic LLDP probes), whereas `iperf3` reports application UDP payload bits (1,400 bytes "
        "per datagram), port TX naturally reads roughly 3.0% above sender payload rate, closely matching our "
        "3.116% calibration measurement in Section 5.2."
    ),
    _p(
        "Hardware OpenFlow switches implement the same match-action abstraction on merchant-silicon ASICs rather "
        "than general-purpose CPUs. Exact-match lookups (such as Layer 2 MAC forwarding) map onto dense, "
        "low-power SRAM hash tables, whereas arbitrary wildcard matches (combining ingress port, IP prefixes, "
        "and transport fields) rely on Ternary Content-Addressable Memory (TCAM) capable of parallel single-cycle "
        "priority resolution. While hardware TCAM forwards at multi-terabit line rates with sub-microsecond "
        "latency, TCAM silicon is expensive, power-hungry, and capacity-bounded (often holding only a few "
        "thousand wildcard rules) with finite control-plane rule-insertion rates (hundreds to a few thousand "
        "`FLOW_MOD` updates per second). Software OVS on a single VM does not emulate TCAM table exhaustion or "
        "ASIC update latency directly; aggregating our managed rules at the directed IPv4 host-pair level keeps "
        "table size bounded at O(H\u00b2) regardless of concurrent socket count, and Chapter 5 qualifies every "
        "benchmark explicitly as software emulation."
    ),
    _p(
        "Even with OpenFlow 1.3's OXM extensions, the set of matchable packet headers remains tied to fixed "
        "specification versions. **P4** (Programming Protocol-Independent Packet Processors) [10] removes that "
        "constraint by defining a domain-specific language targeting Protocol-Independent Switch Architectures "
        "(PISA) and the software BMv2 switch. In P4, network operators program the packet parser state machine, "
        "custom match-action table layouts, and deparser directly, enabling capabilities such as In-Band Network "
        "Telemetry (INT) that stamp per-hop queue depths into live packets without waiting for a new OpenFlow "
        "standard. Our coursework stays within standard OpenFlow 1.3 on OVS to maintain full compatibility with "
        "the course rubric and Wireshark dissectors."
    ),
    _p(
        "We construct and automate both network topologies using **Mininet** [11]. Mininet isolates each virtual "
        "host inside its own Linux network namespace with a dedicated virtual Ethernet (`veth`) interface attached "
        "to an OVS switch port, allowing real unmodified Linux TCP/IP stacks, `ping`, `iperf`, and `iperf3` "
        "binaries to execute across arbitrary graphs on one virtual machine. However, because every host, OVS "
        "bridge, and OS-Ken greenlet shares the same VM CPU cores, emulation fidelity requires disciplined link "
        "shaping. Unshaped `veth` links (`qdisc noqueue`) allow software TCP transfers to burst to 32-34 Gbps "
        "in memory, monopolizing the CPU and starving OS-Ken's LLDP topology keepalives until links falsely time "
        "out (documented empirically in Section 5.8). Wrapping every inter-switch link in Mininet `TCLink` "
        "(Linux `tc` Hierarchical Token Bucket rate shaping paired with `netem` propagation delay) enforces "
        "100 Mbps bandwidth, 2 ms one-way delay, and a 64k HTB burst/cburst ceiling, giving repeatable queue "
        "dynamics and exact utilization denominators."
    ),

    # ---- 2.6 Related Work on SDN Load Balancing & Fault Tolerance ----
    _h2("2.6 Related Work on SDN Load Balancing and Fault Tolerance"),
    _p(
        "Seven foundational papers [12]-[18] anchor the traffic-engineering, consistent-update, and fault-recovery "
        "techniques in SDN and directly inform the architectural choices in Track 1."
    ),
    _h3("Multi-Path Data-Center Topologies and Dynamic Flow Scheduling"),
    _p(
        "Al-Fares, Loukissas, and Vahdat [12] showed that interconnecting commodity k-port switches into a "
        "three-tier Clos *fat-tree* provides full bisection bandwidth across (k/2)\u00b2 equal-cost paths between "
        "any two pods without requiring expensive core routers. Our scaled k = 4 evaluation topology implements "
        "this exact design: 4 core switches, 8 aggregation switches, 8 edge switches, 32 inter-switch links, and "
        "16 hosts. Conventional Equal-Cost Multi-Path (ECMP) routing distributes flows across those equal-hop "
        "paths by hashing packet headers statically at each switch. While ECMP adds zero controller latency and "
        "performs well under uniform traffic matrices, hash collisions inevitably map multiple long-lived large "
        "flows onto the same uplink while parallel uplinks carry little load."
    ),
    _p(
        "Hedera [13] attacked ECMP hash collisions with a centralized SDN flow scheduler built around a key "
        "empirical observation: most data-center flows are short *mice* that finish before a controller can "
        "measure them, while a small minority of long-lived *elephant flows* consume the bulk of total bytes. "
        "Hedera leaves mice on default ECMP paths, polls edge switch counters periodically to flag any flow "
        "exceeding 10% of host NIC capacity, estimates traffic demand across hosts, and computes non-colliding "
        "core placements using Global First Fit or Simulated Annealing. Our Track 1 controller adopts Hedera's "
        "elephant-only paradigm directly, flagging directed host pairs above 10% of link capacity (10 Mbps on "
        "100 Mbps links) for two consecutive polling intervals before considering a move, while replacing global "
        "demand-matrix optimization with deterministic Yen k = 3 simple-path scoring suited to our grid and "
        "single-controller scale."
    ),
    _p(
        "MicroTE [14] examined production data-center traffic traces and demonstrated that demand matrices remain "
        "predictable only over short windows of a few seconds, warning that overly slow statistics polling "
        "triggers stale reroutes after a burst has already subsided. MicroTE therefore applies fine-grained "
        "centralized traffic engineering only to predictable top-of-rack pairs while falling back to weighted "
        "ECMP for volatile traffic. Our polling-interval experiments in Section 5.5 confirm this exact control "
        "trade-off: shortening the OpenFlow polling period T from 5 s to 2 s cuts congestion declaration latency "
        "from 18.932 s down to 6.952 s at the cost of 2.5 times more multipart counter queries per switch, while "
        "EWMA smoothing (\u03b1 = 0.5) and two-period persistence filter transient spikes at the expense of "
        "bounded detection lag."
    ),
    _p(
        "CONGA [15] moved congestion-aware balancing down into leaf-spine switching silicon, splitting TCP flows "
        "into sub-RTT *flowlets* and piggybacking per-path congestion metrics inside VXLAN encapsulation headers "
        "so leaf switches react within a single round-trip time without involving a software controller. Comparing "
        "CONGA's sub-millisecond hardware reaction against centralized OpenFlow 1.3 polling directly clarifies our "
        "Chapter 5 evaluation: multi-second software rerouting delivers clear throughput and loss gains on "
        "sustained asymmetric bottlenecks (our 85 + 30 Mbps grid trials), yet on ten balanced 144 Mbps flows, "
        "proactive static ECMP achieves lower peak utilization than reactive balancing because peaks form during "
        "the multi-second detection window before any rule change fires."
    ),
    _h3("Consistent Network Updates, WAN Engineering, and Failure Recovery"),
    _p(
        "Changing forwarding rules across multiple switches asynchronously creates transient forwarding loops "
        "and blackholes if an ingress switch shifts traffic before downstream switches install the new path. "
        "Reitblatt et al. [16] formalized *per-packet consistency*, ensuring every packet traverses either the "
        "entire old configuration or the entire new configuration through a two-phase commit: the controller "
        "first installs version-tagged rules on interior switches, waits for acknowledgements, updates ingress "
        "switches to stamp the new version tag, and deletes old-version entries only after in-flight packets "
        "drain. Our Track 1 controller adapts this principle into a single-flow make-before-break update using "
        "OpenFlow 1.3 priorities and barriers: replacement rules install in strict egress-to-ingress order "
        "(for example `S6`, then `S5`, then `S4`, and finally `S1`) at incremented priority 21, each confirmed "
        "by a matching `OFPT_BARRIER_REPLY` before the next hop proceeds. Only after ingress switches over does "
        "the controller issue `OFPFC_DELETE_STRICT` for the old priority-20 entries; if any switch reports an "
        "`OFPT_ERROR` or misses its 10 s barrier deadline, already-installed priority-21 rules roll back while "
        "the old path stays intact. We state this scope precisely: it prevents blackholes during sequential "
        "single-flow moves without claiming generalized multi-flow two-phase packet tagging."
    ),
    _p(
        "At wide-area scale, Google B4 [17] deployed OpenFlow controllers across inter-datacenter WAN backbones, "
        "combining centralized multipath tunnel allocation with application-level bandwidth arbitration to drive "
        "expensive long-haul links close to full utilization while shifting bulk transfers gracefully during "
        "fiber cuts. Although B4 operates across continents with hierarchical controllers and Paxos replication, "
        "its core premise mirrors our lab system: global visibility of link utilization and active flows unlocks "
        "parallel path capacity that shortest-path routing leaves stranded."
    ),
    _p(
        "Finally, Sharma et al. [18] evaluated OpenFlow failure recovery against carrier-grade 50 ms benchmarks, "
        "contrasting reactive *restoration* against proactive *protection*. Under reactive restoration, the "
        "controller learns of a link cut via `OFPT_PORT_STATUS` or LLDP expiry, recomputes alternate paths, and "
        "pushes updated `OFPT_FLOW_MOD` rules across affected switches, yielding recovery latencies in the tens "
        "to hundreds of milliseconds depending on topology size and control-channel load. Under proactive "
        "protection, the controller pre-installs backup paths in OpenFlow 1.3 `OFPGT_FF` fast-failover group "
        "tables monitored locally by Bidirectional Forwarding Detection (BFD), allowing switches to fail over "
        "in under 50 ms without waiting for a controller round trip. Our controller implements reactive "
        "restoration triggered by `EventLinkDelete` and `EventSwitchLeave`, achieving 73.139 \u00b1 21.631 ms "
        "host-visible recovery across five controlled grid link cuts (Section 5.7), while switch-local fast-"
        "failover groups remain a natural future extension in Chapter 6."
    ),

    # ---- 2.7 Reliability, Scalability, and Security ----
    _h2("2.7 Reliability, Scalability, and Security"),
    _p(
        "Moving control logic out of distributed switches introduces operational failure modes and security "
        "exposures that do not exist in autonomous routers [5]. Foremost is the controller single point of "
        "failure (SPOF): if a standalone controller process crashes or loses network reachability, switches "
        "configured in `fail-secure` mode retain existing Table 0 entries yet silently drop all unmatched flows "
        "and cannot react to congestion or link cuts, whereas `fail-standalone` mode reverts to legacy L2 MAC "
        "learning and breaks SDN traffic engineering. Production deployments eliminate the SPOF through "
        "distributed controller clusters such as ONOS [7], synchronizing topology and flow state via Raft "
        "consensus and assigning switch ownership through OpenFlow 1.3 `OFPT_ROLE_REQUEST` (`OFPCR_ROLE_MASTER`, "
        "`OFPCR_ROLE_EQUAL`, and `OFPCR_ROLE_SLAVE`) messages [4]."
    ),
    _p(
        "Controller placement and control-plane scaling impose tight architectural bounds [5], [18]. Placing "
        "controllers too far from edge switches inflates both reactive flow-setup latency and link-failure "
        "restoration times; conversely, assigning too many switches to one instance creates CPU and socket "
        "contention. Periodic monitoring generates O(N/T) OpenFlow multipart requests and replies across N "
        "switches every T seconds. As N grows from our 6-switch grid to the 20-switch fat-tree (80 switch ports), "
        "multipart parsing, bulk route rebuilds, and LLDP probe sweeps share the same cooperative Eventlet loop, "
        "which is why our implementation enforces a bounded LLDP wait wrapper and cooperative `hub.sleep(0)` "
        "yields during large rebuilds (Section 4.3)."
    ),
    _p(
        "From a security perspective, centralization concentrates high-value targets on the control plane [5]. "
        "First, a compromised host can launch a control-plane denial-of-service (DoS) attack by transmitting "
        "spoofed packets with randomized headers that miss Table 0 and trigger a flood of `OFPT_PACKET_IN` "
        "messages, saturating the controller CPU and southbound TCP buffers. Second, the same micro-flow storm "
        "can exhaust finite hardware TCAM flow tables, preventing legitimate `OFPT_FLOW_MOD` installations. "
        "Third, because SDN controllers rely on LLDP frames to infer physical switch adjacencies, an attacker "
        "on a host access port can inject forged LLDP frames or relay genuine LLDP frames between two switches "
        "(topology poisoning), creating phantom links that attract or blackhole traffic. Fourth, cleartext "
        "OpenFlow TCP connections and unauthenticated northbound REST APIs expose switch rules to interception "
        "and unauthorized modification. Table 2.4 maps each risk to standard production countermeasures and "
        "documents honestly what our lab prototype implements."
    ),
    {
        "type": "table",
        "id": "Table 2.4",
        "caption": "Table 2.4: SDN Reliability, Scalability, and Security Risks with Countermeasures and Lab Scope.",
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
                "Bounded `TCLink` shaping (100 Mbps), bounded LLDP wait wrapper; fat-tree LLDP churn noted in Ch. 5.",
            ],
        ],
        "col_widths_mm": [28, 44, 50, 44],
    },

    # ---- 2.8 SDN Applications and Emerging Trends ----
    _h2("2.8 Practical SDN Applications and Emerging Trends"),
    _p(
        "Outside academic testbeds, SDN principles operate across six major production domains where centralized "
        "visibility resolves concrete operational limits [5]. In multi-tenant cloud data centers, virtualized "
        "overlay networks (VXLAN or Geneve) decouple tenant addressing from physical Clos fabrics [12], while "
        "centralized or leaf-level congestion telemetry steers large elephant transfers away from hot spine "
        "links [13], [15]. In enterprise and hyperscale Software-Defined WANs (SD-WAN), controllers continuously "
        "probe latency, loss, and utilization across parallel MPLS, private fiber, and broadband circuits, "
        "assigning interactive voice and control flows to low-jitter links while filling residual WAN capacity "
        "with background replication, following the traffic-engineering model pioneered by Google B4 [17]."
    ),
    _p(
        "SDN also pairs closely with Network Functions Virtualization (NFV) and 5G transport networks. Under "
        "NFV, dedicated hardware middleboxes (firewalls, load balancers, NAT gateways, intrusion-detection "
        "sensors) are replaced by virtualized software instances running on commodity servers; an SDN controller "
        "programs OpenFlow or P4 [10] rules to steer each traffic class through an ordered *service function "
        "chain* and dynamically bypass failed virtual appliances. In 5G mobile backhaul and core transport, "
        "network slicing partitions shared physical fiber into isolated logical slices matching distinct SLA "
        "profiles: high-bandwidth Enhanced Mobile Broadband (eMBB), latency-critical Ultra-Reliable Low-Latency "
        "Communications (URLLC), and high-density Massive Machine-Type Communications (mMTC), coordinating queues, "
        "meters, and disjoint backup paths from a central orchestrator."
    ),
    _p(
        "Two active research trends push network automation beyond explicit rule programming. Intent-Based "
        "Networking (IBN) elevates the northbound interface from low-level flow rules to declarative operational "
        "goals (for instance, keeping core utilization under 70% or isolating tenant subnets), automatically "
        "compiling policies into verified switch states and closing the loop with continuous telemetry checks. "
        "Machine-learning-assisted traffic engineering trains classifiers and demand forecasters on switch "
        "counter histories to identify elephants early or predict link saturation before queues build. While "
        "promising, learned policies face closed-loop distribution shift because every rerouting action alters "
        "the subsequent traffic matrix, making failures harder to diagnose. For this Track 1 implementation, we "
        "deliberately use deterministic EWMA thresholds, Yen k = 3 path ranking, explicit hysteresis gates, and "
        "barrier-confirmed updates so every routing transition can be audited directly from raw port and flow "
        "logs. Chapter 3 specifies that architecture in detail."
    ),
]


CHAPTERS_PART1 = [
    {"number": 1, "title": "Introduction", "blocks": CH1_BLOCKS},
    {"number": 2, "title": "Software-Defined Networking Background", "blocks": CH2_BLOCKS},
]
