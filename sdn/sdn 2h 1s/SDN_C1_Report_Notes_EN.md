# SDN Common Core — C1 Technical Report Notes

**Course:** Computer Networks (ECE2606)  
**Program:** Intelligent Systems Engineering — Helwan National University  
**Term:** Fall 2026/2027  
**Work package:** C1 — Setup and OpenFlow 1.3 familiarization  
**Status:** **Verified single-switch learning exercise; not the complete Common Core**  
**Prepared as:** Reusable documentation and evidence inventory for the final report (not a claim that the final report is complete)

> **Editorial note:** Replace the bracketed screenshot placeholders with actual project evidence. This document separates **observed results** from **planned work**. The screenshots shared in the chat confirm the observations below, but the existence of a saved `.pcapng` capture and final evidence folder has **not** yet been confirmed.

---

## 1. Purpose and scope

The course project follows a **common SDN core** and then one of six application tracks. The common core requires environment setup, topology discovery, Dijkstra-based routing, monitoring of link/flow statistics, and a REST API. The initial C1 requirement focuses on running an OpenFlow 1.3 learning-switch application and analyzing the controller–switch message exchange in Wireshark.

This exercise implemented and tested a **minimal proof-of-concept** topology of two virtual hosts connected to one Open vSwitch. The OpenFlow controller was implemented using **OS-Ken**, the Ryu fork permitted by the course brief. A custom Python learning-switch application (`first_controller.py`) was used because the example `os_ken.app.simple_switch_13` was not available in the installed OS-Ken package. The goal was to demonstrate the functional separation of the control plane and data plane and inspect their communication.

**Scope boundary:** The run demonstrates a one-switch learning scenario, **not** the course's six-switch lab grid, LLDP topology discovery, shortest-path routing, utilization monitoring, or REST API. The course brief specifies a linear-topology `simple_switch_13` run for C1; our implementation uses an equivalent **locally written learning-switch exercise** on the `single,2` topology. The precise acceptability of this substitution for formal grading should be checked against the instructor's requirements.

## 2. Learning objectives

1. Instantiate an emulated topology with Mininet and Open vSwitch.
2. Run a Python controller in an isolated environment using OpenFlow 1.3.
3. Establish controller–switch connectivity over TCP port 6653.
4. Confirm inter-host reachability with ICMP Echo tests.
5. Inspect OpenFlow Flow Entries and their counters on the switch.
6. Capture and explain key OpenFlow messages: HELLO, FEATURES, FLOW_MOD, PACKET_IN, PACKET_OUT, and ECHO.

## 3. Experimental environment

| Component | Observed or used configuration | Evidence / qualification |
|---|---|---|
| Host platform | Windows running Oracle VirtualBox | Ubuntu VM was operated interactively. |
| Guest OS | Ubuntu 22.04 (`jammy`) | Supported by terminal package output from the setup session. |
| Guest kernel | `6.8.0-138-generic` | Observed with `uname -r`. |
| VirtualBox Guest Additions | Installer for version `7.2.22` successfully ran | Kernel, shared-folder, and graphics modules built; bidirectional clipboard was subsequently tested. |
| Python | Python 3.10 environment | Visible in `/home/fouad/sdn-lab/.venv/lib/python3.10/...`; exact patch version was not recorded. |
| Controller framework | OS-Ken, version 3.1.1 targeted | Older installed framework used after the 4.2.2 package did not expose the expected `osken-manager` entry point. Working entry point at `.venv/bin/osken-manager` was confirmed. |
| Network emulator | Mininet | Operational test passed; exact installed version still needs `mn --version` capture. |
| Virtual switch | Open vSwitch | Functional in standalone and externally controlled configurations; exact installed version not recorded. |
| Controller communication | OpenFlow 1.3 over TCP | Loopback address `127.0.0.1`, port `6653`. |
| Analyzer | Wireshark 3.6.2 | Version appeared on Wireshark welcome screen. |

**Virtual environment path:** `/home/fouad/sdn-lab/.venv`  
**Controller source:** `/home/fouad/sdn-lab/first_controller.py`

## 4. Architecture and topology

```text
                  Control Plane
             OS-Ken LearningSwitch
             127.0.0.1 : TCP 6653
                       |
                 OpenFlow 1.3
                       |
                    OVS S1
                 /            \
             s1-eth1        s1-eth2
               /                \
       H1: 10.0.0.1        H2: 10.0.0.2
       MAC ...:01          MAC ...:02
                    Data Plane
```

Mininet created two Linux-emulated hosts (`h1` and `h2`) attached to one software switch (`s1`). The controller and OVS ran in the same Ubuntu virtual machine; hence the control channel appeared as loopback traffic in Wireshark. The use of a remote-controller setting means the **controller is a separate process** from Mininet, not that it is on a different physical computer.

### Responsibilities of the components

- **Mininet:** constructs the topology, virtual host networking, and interfaces.
- **OVS:** matches packets against OpenFlow entries and forwards frames according to actions.
- **OS-Ken application:** installs a table-miss rule, learns source MAC-to-port associations, performs flooding for unknown destinations, and installs higher-priority forwarding rules for learned destinations.
- **OpenFlow 1.3:** carries the control messages between OS-Ken and OVS.
- **Wireshark:** records the control-channel packet exchange for examination and evidence.

## 5. Implementation and reproduction

### 5.1 Environment activation and controller startup

```bash
cd ~/sdn-lab
source .venv/bin/activate
osken-manager --ofp-tcp-listen-port 6653 first_controller.py
```

The shell changed to the existing project folder, activated the virtual Python environment, and started OS-Ken listening for OpenFlow connections on TCP port 6653. Successful application loading displayed messages including:

```text
loading app first_controller.py
loading app os_ken.controller.ofp_handler
instantiating app first_controller.py of LearningSwitch
instantiating app os_ken.controller.ofp_handler of OFPHandler
```

After Mininet connected, the controller logged:

```text
Switch 1 connected
```

**Interpretation:** the switch identification event reached the application; this confirms controller–switch interaction rather than only installation of the Python package.

### 5.2 Topology startup in a second terminal

```bash
sudo mn --topo single,2 --mac --switch ovs,protocols=OpenFlow13 --controller remote,ip=127.0.0.1,port=6653
```

Arguments:

- `single,2`: one switch and two hosts.
- `--mac`: deterministic host MAC addressing for easier analysis.
- `ovs,protocols=OpenFlow13`: OVS configured to speak OpenFlow 1.3.
- `remote,ip=127.0.0.1,port=6653`: controller running independently on Ubuntu loopback.

Mininet returned the interactive `mininet>` prompt; the displayed creation output included `h1 h2` and `s1`.

### 5.3 Relevant parts of the Python controller

**Table-miss rule upon switch feature negotiation:**

```python
@set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
def switch_connected(self, ev):
    dp = ev.msg.datapath
    p = dp.ofproto_parser
    o = dp.ofproto
    match = p.OFPMatch()
    actions = [p.OFPActionOutput(o.OFPP_CONTROLLER, o.OFPCML_NO_BUFFER)]
    inst = [p.OFPInstructionActions(o.OFPIT_APPLY_ACTIONS, actions)]
    dp.send_msg(p.OFPFlowMod(
        datapath=dp, priority=0,
        match=match, instructions=inst
    ))
    self.logger.info("Switch %s connected", dp.id)
```

An empty match with priority 0 provides a fallback rule for packets that do not match a more specific entry; its action sends them to the controller.

**Learning and forwarding logic in the PACKET_IN handler:**

```python
src = eth.src
dst = eth.dst
self.mac_to_port.setdefault(dp.id, {})[src] = in_port
out_port = self.mac_to_port[dp.id].get(dst, o.OFPP_FLOOD)
actions = [p.OFPActionOutput(out_port)]

if out_port != o.OFPP_FLOOD:
    match = p.OFPMatch(in_port=in_port, eth_dst=dst)
    inst = [p.OFPInstructionActions(o.OFPIT_APPLY_ACTIONS, actions)]
    dp.send_msg(p.OFPFlowMod(
        datapath=dp, priority=1,
        match=match, instructions=inst
    ))

dp.send_msg(p.OFPPacketOut(
    datapath=dp,
    buffer_id=o.OFP_NO_BUFFER,
    in_port=in_port,
    actions=actions,
    data=msg.data
))
```

For unknown destination MAC addresses, the application floods the current frame. For learned destinations, it creates a priority-1 Flow Entry, then instructs the switch to forward the current frame. This simple approach is suitable for the small lab, but **does not provide loop-free topology-wide forwarding**.

**Full code location:** `first_controller.py`. The Arabic practice guide also contains a complete restorable copy.

## 6. Tests and observed results

### 6.1 Basic Mininet / OVS check (without an external controller)

**Command:**

```bash
sudo mn --switch ovsbr --test pingall
```

**Observed output:**

```text
*** Results: 0% dropped (2/2 received)
completed in 0.425 seconds
```

**What this demonstrates:** basic OVS/Mininet switching and connectivity. It **does not** establish SDN control by OS-Ken.

### 6.2 Controller-based Mininet test

**Command inside Mininet:**

```text
pingall
```

**Observed:**

```text
*** Results: 0% dropped (2/2 received)
```

### 6.3 H1 to H2 ICMP test

**Command:**

```text
h1 ping -c 5 h2
```

**Observed:** `5 packets transmitted, 5 received, 0% packet loss`. One recorded run reported:

```text
rtt min/avg/max/mdev = 0.099/1.514/3.134/1.323 ms
```

An additional `h1 ping -c 1 h2` returned one successful reply, with an example recorded RTT of approximately `2.766 ms`. These are **individual observations**, not statistically repeated measurements or performance comparisons.

### 6.4 Flow-table verification

**Command inside Mininet:**

```text
sh ovs-ofctl -O OpenFlow13 dump-flows s1
```

**Representative recorded rules (abbreviated):**

```text
priority=1,in_port="s1-eth2",dl_dst=00:00:00:00:00:01 actions=output:"s1-eth1"
priority=1,in_port="s1-eth1",dl_dst=00:00:00:00:00:02 actions=output:"s1-eth2"
priority=0 actions=CONTROLLER:65535
```

| Entry | Match | Action | Interpretation |
|---|---|---|---|
| Priority 1 | in_port 2; destination MAC `...:01` | output 1 | Forward H2 → H1. |
| Priority 1 | in_port 1; destination MAC `...:02` | output 2 | Forward H1 → H2. |
| Priority 0 | fallback / table-miss | send to controller | Delegate unmatched packets. |

**Flow counter readings as recorded:**

| Entry | First snapshot | Second snapshot | Third snapshot |
|---|---:|---:|---:|
| H2 → H1 | 3 | 10 | 13 |
| H1 → H2 | 2 | 9 | 12 |
| Table-miss | 29 | 33 | 33 |

The specific flow counters rose across the observations, whereas the table-miss counter remained at 33 between the latter two readings. This is consistent with installed matching rules handling subsequent packets. **Caution:** the snapshots were separated in time; other background frames could have contributed to the counter increases, so the differences must not be presented as exact per-ping counts.

## 7. Wireshark: OpenFlow 1.3 message analysis

**Capture interface:** `Loopback: lo`  
**Control-channel display filter:** `tcp.port == 6653`  
**Selective display filters:** `openflow_v4.type == 14` (FLOW_MOD); `openflow_v4.type == 10 || openflow_v4.type == 13` (PACKET_IN/OUT).

A new Mininet connection was established while Wireshark was recording. The capture displayed an OpenFlow handshake and subsequent packet-processing messages.

### 7.1 Initial handshake

The recorded exchange included:

1. `OFPT_HELLO` messages in both directions to negotiate protocol support.
2. `OFPT_FEATURES_REQUEST` from the controller.
3. `OFPT_FEATURES_REPLY` from OVS.
4. `OFPT_MULTIPART_REQUEST` for port descriptions (`OFPMP_PORT_DESC`).
5. `OFPT_FLOW_MOD` entries issued by the controller as rules were installed.

The controller and switch used IPv4 loopback `127.0.0.1`. The controller listened on port `6653`, while the switch used a temporary client-side TCP port, e.g. `43518` in the examined handshake and `38504` in another recorded connection.

### 7.2 HELLO example

**Recorded message:** packet 1467 in a capture segment.

| Field | Value |
|---|---|
| OpenFlow version | 1.3 (`0x04`) |
| Type | `OFPT_HELLO (0)` |
| OpenFlow message length | 16 bytes |
| Additional information | Hello element present (8 bytes beyond the 8-byte header) |

The HELLO confirms OpenFlow negotiation. Its frame direction, as inspected via TCP source/destination ports, was switch to controller.

### 7.3 FEATURES_REPLY example

**Recorded message:** packet 1472.

| Field | Value |
|---|---|
| Version | 1.3 (`0x04`) |
| Type | `OFPT_FEATURES_REPLY (6)` |
| OpenFlow message length | 32 bytes |
| Datapath ID | `0x0000000000000001` |
| Number of buffers | `0` |
| Number of tables | `254` (advertised) |
| Auxiliary ID | `0` |
| Capabilities | `0x0000004f` |

Wireshark decoded the following supported capabilities as true: `FLOW_STATS`, `TABLE_STATS`, `PORT_STATS`, `GROUP_STATS`, and `QUEUE_STATS`. The `IP_REASM` and `PORT_BLOCKED` capability flags were false. Advertised capability bits do not, by themselves, validate the behavior of every supported feature.

### 7.4 FLOW_MOD example

**Recorded message:** packet 466, emitted controller → switch.

| Field | Value |
|---|---|
| Type | `OFPT_FLOW_MOD (14)` |
| OpenFlow message length | 96 bytes |
| Command | `OFPFC_ADD (0)` |
| Table ID | `0` |
| Priority | `1` |
| Idle timeout / hard timeout | `0 / 0` |
| Buffer ID | `OFP_NO_BUFFER` |
| Match type | `OFPMT_OXM` |
| Match fields | `IN_PORT = 2`, `ETH_DST = 00:00:00:00:00:01` |
| Instruction | `OFPIT_APPLY_ACTIONS` |
| Action | `OFPAT_OUTPUT`, port `1` |

**Interpretation:** if a frame arrives on port 2 with destination MAC `...:01`, output it through port 1. This corresponds to the learned H2 → H1 rule. The output port is identified by the Action; the top-level Flow-Mod `out_port` field is not that forwarding action.

### 7.5 PACKET_IN example

**Recorded message:** packet 432.

| Field | Value |
|---|---|
| Type | `OFPT_PACKET_IN (10)` |
| OpenFlow message length | 152 bytes |
| Total original frame length | 110 bytes |
| Reason | `OFPR_NO_MATCH (0)` |
| Table ID | `0` |
| Buffer ID | `OFP_NO_BUFFER` |
| Original source MAC | `00:00:00:00:00:02` |
| Destination MAC | `33:33:00:00:00:16` |
| Protocol content | IPv6 multicast / ICMPv6, destination `ff02::16` |

**Important:** this particular PACKET_IN carried **IPv6 multicast traffic**, not the IPv4 Ping request. It shows how the learning application can encounter background control traffic as well as intentional test traffic.

### 7.6 PACKET_OUT example

**Recorded message:** packet 434, close in time and content to packet 432.

| Field | Value |
|---|---|
| Type | `OFPT_PACKET_OUT (13)` |
| OpenFlow message length | 150 bytes |
| Buffer ID | `OFP_NO_BUFFER` |
| In port | `2` |
| Action | `OFPAT_OUTPUT` |
| Output port | `OFPP_FLOOD` |
| Embedded data | IPv6 multicast / ICMPv6 frame sourced from H2 |

**Interpretation:** when the destination MAC was not learned, the controller requested flooding over eligible switch ports rather than adding a unicast forwarding rule for that destination. The matching frame information and nearby timestamps are consistent with PACKET_IN → PACKET_OUT handling.

### 7.7 ECHO exchange

`OFPT_ECHO_REQUEST` and `OFPT_ECHO_REPLY` were also seen. These are OpenFlow control-channel liveness messages; they must not be confused with the end-host ICMP Echo Request/Reply generated by `ping`.

## 8. Issues encountered and resolutions

| Issue | Observation | Resolution/workaround |
|---|---|---|
| Graphical terminal initially failed to open | GUI Terminal did not launch on first setup | Ubuntu language/region formats were adjusted, after which GNOME Terminal opened. |
| Kernel-header package not initially located | `linux-headers-6.8.0-138-generic` could not initially be found | Installed `linux-generic-hwe-22.04` with build tools and rebooted; subsequent `/lib/modules/$(uname -r)/build` resolved to the matching headers. |
| Guest Additions autorun did not start | Clicking GUI “Run Software” produced no useful result | Installed from the mounted ISO using `sudo sh /media/fouad/VBox_GAs_7.2.22/VBoxLinuxAdditions.run`, then rebooted. Bidirectional clipboard was tested. |
| Missing `osken-manager` with OS-Ken 4.2.2 | Shell reported command not found | Selected OS-Ken 3.1.1 in the Python virtual environment, where the manager command was found. |
| Missing `os_ken.app.simple_switch_13` | Python raised `ModuleNotFoundError` for the packaged example | Created a local learning-switch app (`first_controller.py`), which was successfully loaded. |
| Eventlet warning | Deprecation and RLock-related messages displayed | Warning was non-fatal in the observed run; no claim of long-term compatibility is made. |
| Wireshark not installed | `wireshark: command not found` | Installed `wireshark-qt` and configured the capture-permission group. |

## 9. Findings and limitations

The exercise confirms that OS-Ken can program OVS Flow Entries through OpenFlow 1.3 in the tested Ubuntu virtual environment. The installed unicast rules and the table-miss entry were observable both in switch flow-table output and in the captured OpenFlow messages. ICMP communication between the two hosts succeeded with zero packet loss in the recorded tests.

**Limitations:**

- The topology contains only one switch and two hosts and does not exercise alternative routes or topology loops.
- The sample learning-switch logic uses flooding for unknown MAC addresses and therefore is **not a complete solution for the loop-containing six-switch grid**.
- No LLDP graph discovery, Dijkstra routing, live utilization computation, or REST API is implemented yet.
- No controlled baseline comparison, five-run experiment set, or mean and standard-deviation analysis has been produced yet.
- The exact Mininet, OVS, and Python patch versions should be recorded from the installed system before final submission.
- A retained `.pcapng` file and final screenshot paths should be confirmed and archived; Wireshark screenshots alone do not establish that the capture was saved.

## 10. Evidence inventory for the report

These entries are **suggested filenames**, not assertions that the files already exist. Save or recreate the evidence during a repeat run.

| Suggested artifact | What to capture | Current evidence status |
|---|---|---|
| `fig_c1_controller_connected.png` | Controller terminal: `Switch 1 connected` | Demonstrated in chat screenshots. |
| `fig_c1_mininet_topology.png` | Mininet startup with h1, h2, s1 and `mininet>` | Demonstrated in chat screenshots. |
| `fig_c1_pingall.png` | `0% dropped (2/2 received)` | Exact terminal output shared in chat. |
| `fig_c1_ping_h1_h2.png` | 5/5 successful Ping replies and RTT summary | Exact terminal output shared in chat. |
| `fig_c1_flow_table.png` | Priority-1 forwarding entries and priority-0 table-miss | Exact terminal output shared in chat. |
| `fig_c1_openflow_hello.png` | HELLO, version and header fields | Wireshark screenshot reviewed. |
| `fig_c1_features_reply.png` | Datapath ID, n_tables, capabilities | Wireshark screenshot reviewed. |
| `fig_c1_flow_mod.png` | Match (in_port=2; eth_dst=:01), Action output=1 | Wireshark screenshot reviewed. |
| `fig_c1_packet_in_out.png` | PACKET_IN with no-match + PACKET_OUT flood | Wireshark screenshot reviewed. |
| `c1_openflow_capture.pcapng` | Entire replayable capture | **Not yet confirmed saved.** |
| `first_controller.py` | Complete application source | User-created in `~/sdn-lab`; verify its continued presence. |

### Suggested captions

- **Figure C1-1.** Single-switch Mininet topology controlled by OS-Ken via OpenFlow 1.3.
- **Figure C1-2.** Successful bidirectional connectivity test between the two Mininet hosts.
- **Figure C1-3.** OpenFlow entries installed by the learning-switch controller in OVS.
- **Figure C1-4.** OpenFlow 1.3 feature negotiation and switch capabilities.
- **Figure C1-5.** A FLOW_MOD message with OXM match fields and an output action.
- **Figure C1-6.** Packet-in and packet-out exchanges during unknown-destination handling.

## 11. Next stage: C2 topology discovery

The next technical phase is the course-defined six-switch grid with six hosts and seven inter-switch links:

```text
S1 -- S2 -- S3
|     |     |
S4 -- S5 -- S6
```

A separate host is attached to each switch. Inter-switch links are specified in the brief as **100 Mbps** with **2 ms** delay. The controller must discover switch and link additions/removals via LLDP, maintain a NetworkX graph, and learn host locations. The topology contains cycles; unrestricted L2 flooding can cause loops, so ARP and broadcast handling require care. Subsequent core modules add Dijkstra shortest paths (C3), port/flow statistics monitoring (C4), and a REST API (C5).

**Course checkpoint CP2:** automatically discovered topology, `pingall` with 0% loss on the **six-switch lab topology**, and a live link-utilization table. **This checkpoint is not yet achieved by the current exercise.**

## 12. References / sources for the final report

1. Course handout: *Computer Networks (ECE2606) – Course Project: Software-Defined Networking Project: One Common Core, Six Tracks*, Helwan National University, Fall 2026/2027 (especially Sections 1–7, 10–13 and 15).
2. Open Networking Foundation, *OpenFlow Switch Specification*, Version 1.3.5 (2015), as cited in the course handout.
3. Mininet and Open vSwitch documentation (versions corresponding to the installed setup should be verified and cited formally).
4. OS-Ken source/documentation and the team's own application source code (link to the final team's Git repository once created).

> For inclusion in the **final 25–35 page English report**, integrate the relevant material into the *SDN Background*, *System Design*, *Implementation*, and *Experiments and Results* chapters; add original diagrams, numbered figures, reproducible experimental setup, repeat runs, and properly formatted IEEE references. Do not submit this note as if it were the final report.
