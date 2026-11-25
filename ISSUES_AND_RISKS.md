# Issues and limits

## Current triage | 2026-11-26

- Current rehearsal: Grid connectivity 30/30, managed reroute P1/20 to P3/21, long recovery 300/300, and Fat-tree connectivity 240/240. Raw rehearsal files are preserved under experiments/results/.
- Discovery remains an open limitation. The earlier recorded session removed all 32 Fat-tree links and rebuilt routes 64 times. The deployed change uses a maximum 10ms LLDP send guard on Fat-tree and yields between host pairs during bulk rebuilds. The newer supplied session has no link deletions, route rebuilds or tracebacks after startup. This is bounded evidence, not a proven root cause or universal stability guarantee.
- Resumed calibration221916Z contains four trials before that discovery change and one after it. Recomputed mean error3.135351% and sample SD0.263988 percentage points agree with the saved report. Keep this mixed-configuration rehearsal separate from the homogeneous five-trial batch193415Z (mean3.739527%, sample SD2.125110 percentage points).
- High-load loss is workload-dependent and not fully explained. Current baseline comparisons show gains, while current ten-flow and before/after experiments do not show an improvement in every metric. The isolated live hold-down test and historical unshaped LLDP instability remain unresolved.
- Pending delivery: update the report, figures, Arabic guide and run instructions with the current results and discovery setting; presentation, video, team/weekly records, reference review and any explicitly authorized remote publication remain pending. Historical entries below must not be read as current status.

## Historical troubleshooting snapshot (18 November; statuses below are as of that session)


| Item | Current evidence | State / next action |
| --- | --- | --- |
| High-load packet loss | Latest real trial: H1 receiver53.2Mbps,37% loss; H3 receiver22.1Mbps,26% loss. Raw file grid-demo-20261117T193620Z.json. | OPEN. Successful rerouting does not prove performance gains. Do not repeat stress blindly or change the assignment thresholds to force success. |
| S5-S6 recovery | P3 before failure, P1 while down and after restoration. 79/80 probes received. | One live trial. Largest reply gap 0.328979 s. Exact recovery time remains open. |
| iperf3 accuracy target | iperf is working; command -v iperf3 printed no path. No synchronized <10% accuracy study. | OPEN. Remain offline; no installs until Fouad changes the instruction. |
| Course bandwidth/delay | All seven Topo links show TCLink100Mbps/2ms; tc on s1-eth1 confirms100Mbit and2ms; pingall30/30. | IMPLEMENTED. Other interfaces were not individually tc-audited. Local topology synchronized at close from the verified edits, not a new VM export. |
| C4 and C5 | 20 port records,14 inter-switch directions; utilization, ingress host-pair rates; /topology,/links,/flows and old /sdn/ paths work. | IMPLEMENTED at defaultT5. T2-5 configuration exists but its experimental comparison and iperf3 calibration remain incomplete. |
| ARP changed valid paths | First trial changed P1 toP3 with priority20 and reset active counters. | FIXED in source and verified by the next trial keeping P1 until managed rerouting. Valid routes are reused; equal-hop initial Dijkstra order is deterministic. |
| Wrong elephant/cost choice | Trial2 moved H3 at priority21 while H1 stayedP1; ingress rates exceeded dropped port TX, hiding background demand in the old subtraction. | CORRECTED. Trial3 chose largest eligible H1 and moved it toP3/priority21. Estimated offered load may exceed100%; it is not measured C4 utilization. |
| MBB and hysteresis | Trial3 final OVS has21 on all four P3 switches and no old20 rules for H1->H6. Barrier ordering/error rollback,15pp and30s gates checked locally. | Live managed reroute observed once. Do not claim five-run validation, isolated hold-down behavior, zero loss, or exact detection/reroute latency. |
| Flow definition | Match is IPv4 source/destination MAC pair with ingress port; per-host-pair counters at source switch. | DISCLOSE. Not independent TCP/UDP5-tuples; choose distinct pairs in experiments or extend only when the experiment needs it. Switch-local rule totals are not unique network sessions. |
| Counter resets | Baseline/negative duration or byte changes reset the per-flow estimate. Real topology rebuilds and managed replacement can reset counters. | EXPECTED after real changes; avoid treating null rate or aggregate deltas as traffic history. Duplicate old C4 FLOW log messages remain harmless cleanup, not a blocker. |
| Cold start | Repeated30/30 observed; historical first runs sometimes lost probes. | LIMITATION. Report cold and warm results separately; no universal zero-loss claim. |
| Historical extreme LLDP instability | Unshaped TCP32-34Gbps caused link/host corruption and0/30, recovered after restart. | UNRESOLVED historical case. Not proof that a100Mbps link exceeded capacity, and restart is not a root-cause fix. |
| Eventlet warnings | Deprecation/RLock warnings appear; current app and REST start. os_ken.app.wsgi was absent. | KEEP working environment. Use eventlet.listen/wsgi; no opportunistic dependency upgrades or monkey-patching. OS-Ken is explicitly allowed by assignment pp.6-7. |
| Source drift | Original24-file archive is frozen. Windows controller has been supplied and run; local topology rebuilt at close from the instructed patch. Shared-folder writes do not automatically update Ubuntu copies. | Use vm-source as working files. Reconcile real VM edits when needed; no repeated copy/hash checks after every line. Never overwrite frozen checkpoints. |
| Fat-tree/dashboard/evaluation | Fat-tree source and topology-specific discovery are implemented. Live pingall 2 reached 240/240 on the fat-tree. Live dashboard path, flow rates and link utilization observed in Firefox. Performance evaluation pending. PDF reports are historical. | Follow PLAN after failure trial. No invented five-run averages, current screenshots, final report status, or deadline. |
| Git checkpoint | Local commit saved after filesystem approval, without a remote or network access. Earlier permission failure is historical. | SAVED OFFLINE. Do not add a remote or push until Fouad explicitly requests it. |

Original student screenshots are the only screenshot evidence allowed in reports. Actual experiment JSON and console text remain raw evidence with their own labels. The three real grid trials are preserved unchanged under experiments/results/; no generated screenshots or fabricated results.
