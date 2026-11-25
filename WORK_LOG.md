# SDN work log — reconstructed from actual conversation, files and captures

**Date range:** approximately 22 Oct – 17 Nov 2026. Dates inside periods are only assigned where independently recorded. This is a **detailed reconstruction**, not a line-by-line verbatim export of ChatGPT dialogue. Source screenshots, older PDFs and pasted code/logs are in the bundle.

## Phase 0: assignment and environment

- Read course handout `Computer_Networks_Project_2026_v3.pdf` for Computer Networks ECE2606, fall 2026/2027. Spec common core C1–C5, then specialized track. Topology described as six switches, six hosts, seven inter-switch edges. Official requirement is `bw=100 Mbps, delay='2ms'` on every switch-to-switch TCLink, OpenFlow 1.3, Ryu controller; user actually ran OS-Ken 3.1.1 on Ubuntu guest.
- Configured Ubuntu VM, Python virtual environment, OS-Ken, Open vSwitch, Mininet, NetworkX, Wireshark. Terminal prompts show `~/sdn-lab` and `(.venv)`.
- User wants to learn command by command and be shown code edit location **exactly**; preserve the successful state at every milestone with a separately named backup.

## C1: OpenFlow base switch (early work)

- Built a learning switch with `simple_switch_13` style behavior under OpenFlow 1.3.
- Observed switch-controller exchange including PacketIn and FlowMod; visual screenshots were saved in earlier progress reports; do not assert every prescribed handshake message has separate screenshot evidence without checking originals.
- Investigated Wireshark OpenFlow display/connection messages; worked toward course's `HELLO`, `FEATURES`, table miss, `PACKET_IN`, `FLOW_MOD`, `PACKET_OUT` explanation.
- Established general launch pattern: activate `.venv`; run `osken-manager` in terminal 1; start remote-controller Mininet in terminal 2; test `pingall` and OVS flow entries.

## C2: topology + host discovery (around 30 Oct)

- Created a custom topology with S1–S6 and H1–H6; seven inter-switch edges: S1-S2, S2-S3, S3-S6, S6-S5, S2-S5, S4-S5, S1-S4.
- Enabled link discovery with `app_manager.require_app('os_ken.topology.switches')` and manager `--observe-links`. Used OS-Ken switch/link add/remove events and NetworkX graph (`graph.nodes`, `graph.edges`, `ports` edge attribute).
- Verified graph has 6 switch nodes and 7 switch-switch edges; hosts located by MAC and switch/port.
- Stored earlier code/terminal evidence in original PDFs and historical pasted text. The current VM file names still need an actual tree listing.

## C3: generalized Dijkstra routing, ARP learning, failover (31 Oct – 16 Nov)

- Earlier narrow demonstration installed explicit H1↔H6 priority-10 routes. Generalized `dynamic_routing_controller.py` to route arbitrary host pairs using `nx.dijkstra_path` and install bidirectional priority-20 IPv4 FlowMod entries by deriving per-hop ports.
- Created dynamic ARP/IP/MAC learning and Proxy ARP. Initial cold-start handling failed because an ARP request to an as-yet-unknown target could not be answered. Original first `pingall` baseline recorded `13/30 received, 56% dropped` (Mininet's displayed percent).
- Added `self.pending_arp` queue, targeted ARP probes to host-facing ports (avoid flooding cycles), learned replies and delivered pending Proxy ARP responses. New cold-start sample improved to 28/30 (6% dropped), later `pingall` 30/30. Initial cold-start still not always 0%; do not call it fully solved.
- Investigated same-host pair tests, including H2→H5 and H5→H2; earlier sample logs show 3/3 both directions after learning, with equal-cost shortest paths sometimes selected differently.
- Implemented `rebuild_routes()` triggered on topology changes. The controller removes old IPv4 routes and installs routes for discovered host pairs. Test `link s4 s5 down`: H2→H6 5/5 pings successful, general `pingall` 30/30 with link down; link was restored. Additional running ping `h2 ping -c 40 -i 0.5 10.0.0.6` while toggling S4–S5 link produced 40/40, 0% loss, RTT min/avg/max/mdev 0.056/0.130/1.078/0.159 ms.
- Intermediate controller progression includes `dynamic_routing_controller.py`, `cold_start_controller.py`, `failover_controller.py`. Earlier code `Pasted text.txt` and `Pasted text(2).txt` are historical; not guaranteed to match VM current version.

## C4: monitoring + bandwidth (17 Nov, before C5)

- Copied working failover logic into `monitoring_controller.py`, added `from os_ken.lib import hub`, periodic `monitor_network()` polling flow and port multipart counters every 5 seconds. Observed `C4 FLOW S4: +46 packets, +4508 bytes` and `C4 PORT S4 P3 RX ... TX ...` log lines. OVS `dump-flows` for S4 had expected matches/packets after 20 H2→H1 pings.
- Copied to `bandwidth_controller.py`, imported `time`, saved monotonic timestamps, computed actual Mbps from successive `rx_bytes`,`tx_bytes` differences rather than cumulative counters. Typical ping observation: `C4 BANDWIDTH S4 P3 RX 0.003448 Mbps, TX 0.003832 Mbps` (an observed illustrative log; precise values in previous conversation).
- Performed **very high, unshaped TCP** `iperf h2 h1`, reported ~32.3–34 Gbit/s. Controller log showed S4 P3 RX about 31,135.603766 Mbps and S1 P3 RX about 31,168 Mbps at a sample point. This was not physically plausible for course-limited 100-Mbps edges because the actual VM links did not have `bw=100` and `qdisc` reported `noqueue`.
- **Failure:** under the extreme test the LLDP topology became unstable, reported disappearing links and no path, false host events on switch-link ports; Mininet `links` still showed links OK, but a subsequent `pingall` was **0/30**. Not fully debugged or fixed. Reboot/stop/start and Mininet cleanup restored graph and stable connectivity. This must be explicitly preserved in report, not described as a solved congestion problem.
- A bounded `iperfudp 10M h2 h1` test produced `10.5 Mbits/sec` TX and RX and a subsequent `pingall` 30/30. It validates recovery and moderate-load behavior only; doesn't prove that extreme-load topology instability was repaired.

## C5: REST API — first endpoint and troubleshooting (17 Nov)

- `rest_api_controller.py` copied from working `bandwidth_controller.py` (i.e., C1–C4 features retained). Initial attempt used `from os_ken.app.wsgi import ControllerBase, WSGIApplication, route`; crashed with `ModuleNotFoundError: No module named 'os_ken.app.wsgi'`. `python -m py_compile` succeeded before runtime import; lesson: syntax check is not import check.
- Working alternative: `from eventlet import listen, wsgi`; start a green thread `hub.spawn(self.start_rest_api)`; listen only on `('127.0.0.1', 8080)` and serve WSGI `self.rest_application`. HTTP endpoint `GET /sdn/status` returns JSON from live `self.datapaths`, `self.graph`, ARP-learned `self.hosts`.
- First `curl` attempt failed because `curl` was not installed; resolved using `sudo apt update && sudo apt install -y curl`. Initial successful HTTP response `200 OK`, but JSON switch/link/host counts were zero before Mininet boot. After Mininet start/pingall, API read `switches:6`, `links:7`, `hosts:6` (screenshot 17 Nov ~15:57 VM clock, original file `image(20261117-135715).png`). One startup `pingall` gave 28/30, next 30/30.

## C5: topology endpoint

- First test `curl -s http://127.0.0.1:8080/sdn/topology | python3 -m json.tool` returned `{ "error":"Not Found" }`, despite status being healthy. Diagnostic `grep -n -C 8 'sdn/topology' rest_api_controller.py` returned **no matching line**. The endpoint code was missing from actual file, not a network/runtime routing bug.
- Precisely inserted `/sdn/topology` branch **after** prior `/sdn/status` `return [body]` and **before** default `# Unknown API endpoint` 404 branch, at same 8-space indentation as existing route branches. Verification `grep` showed line ~1082. Restarted controller + Mininet.
- Test succeeded, returned `switches:[1,2,3,4,5,6]` plus all seven links with correct per-endpoint `source_port`, `destination_port` matching the actual graph. See `API_CONTRACT_AND_TESTS.md`.

## C5: hosts endpoint

- Before editing, user asked which file to open after `cp rest_api_controller.py rest_api_controller_topology_success.py`. Clarified SOURCE is live file, DEST is frozen backup. Always open `nano rest_api_controller.py`, not `*_success.py`. Restoring reverses `cp` and overwrites the live file.
- Added `/sdn/hosts` after `/sdn/topology` and before 404. Uses `self.arp_table.items()`, lookup `self.hosts.get(mac)`, returns sorted six records with `ip`,`mac`,`switch`,`port`, and `count`.
- `grep -n 'sdn/hosts'` found line ~1128, and live curl JSON returned all six expected attachments.

## C5: bandwidth endpoint

- Backed up `rest_api_controller.py` as `rest_api_controller_hosts_success.py`. Added `self.bandwidth_data = {}` in `__init__` after existing snapshot dictionaries.
- Updated `port_stats_reply` immediately after computing `rx_mbps` and `tx_mbps` to store `self.bandwidth_data[(dpid,port)] = {'switch':..,'port':..,'rx_mbps':round(..,6),'tx_mbps':round(..,6)}`.
- Added `/sdn/bandwidth` branch before the 404 fallback and after `/sdn/hosts` return, `python -m py_compile` passed; grep found condition near line 1178. `grep -n self.bandwidth_data` confirmed three references: initialization, periodic storage, endpoint.
- Live `curl` returned six entries with host-facing ports and near-idle values (e.g. TX ~0.00048 Mbps). Subsequently used `watch -n 1 'curl -s http://127.0.0.1:8080/sdn/bandwidth | python3 -m json.tool'` while running `iperfudp 10M h2 h1` repeatedly. Screenshot `image(20261117-144759).png` captured S4 P3 RX=9.674904 Mbps, S1 P3 TX=9.577393 Mbps and 10.5 Mbits/sec in iperf. Important direction: RX into S4 from sender H2; TX out of S1 to receiver H1.

## C5: flows endpoint and live confirmation (17 Nov ~17:13)

- Backed up `rest_api_controller.py` as `rest_api_controller_bandwidth_success.py`. Existing `flow_stats_reply` code at lines ~880–923 filters priority 20, totals packet_count and byte_count per switch, caches previous values, and logs positive deltas.
- Added `self.flow_data = {}` after `self.flow_snapshot = {}` in `__init__`; inserted storage of `flow_count`, `total_packets`, `total_bytes`, and zero-initialized `new_packets`,`new_bytes` after snapshot update. Then updated latest delta fields after negative-counter guard.
- Added `/sdn/flows` route after bandwidth block and before 404. Curl returned `count=6`, `total_flows=84`, individual flow counts S1=10,S2=13,S3=12,S4=14,S5=20,S6=15, totals 311 packets and 30,478 bytes **aggregated across datapaths**.
- `watch -n 1 .../sdn/flows` while `h2 ping -c 100 -i 0.1 10.0.0.1` captured 100/100 packets and 0% loss; API showed `new_packets:84`,`new_bytes:8232` for S1 and S4, with their `total_packets` 190 and 206 in that screenshot; S2/S3/S5 showed zero new_packets. Original `image(20261117-151334).png`.
- User was told to preserve checkpoint `rest_api_controller_flows_success.py`; existence on VM not independently audited.

## Historical pause point (17 November)

- Next intended `/sdn/routes` read-only introspection endpoint. Before coding, assistant asked user to run `grep -nE 'def .*route|def .*path|shortest_path|def rest_application' rest_api_controller.py`. **No result for that command is present yet.**
- User instead requested full PDFs, work log, comprehensive handoff and transfer to Work/Codex; this bundle is that documentation handoff. **No route endpoint has been added or tested.**

## Never erase these caveats

1. Cold-start first-run packet loss intermittently remains; 30/30 after warm-up ≠ 30/30 cold guaranteed.
2. High-rate TCP traffic broke LLDP/controller graph and pingall, not repaired; moderate UDP did not prove repair.
3. Current source missing course-mandated 100-Mbps/2ms TC links at last known inspection; re-inspect latest VM source.
4. Current C4 monitors only host ports; official C4 is per-link utilization and <10% iperf3 validation.
5. Current API uses `/sdn/` prefix and lacks required exact `/links` endpoint. Don't call official C5 compliance complete.
6. OS-Ken vs course Ryu naming deserves approval.
7. History exists as screenshots, raw pasted terminal excerpts, and older PDFs; **not** as full verbatim chat data.


## جلسة Codex المحلية: 17 نوفمبر 2026

- راجعنا التكليف كاملًا وحددنا Track 1. صححنا أن OS-Ken مسموح، وأجلنا /sdn/routes والـbonus. فؤاد طلب العمل offline وعدم Computer Use، وتجميع التغييرات بدل فحوص ونسخ بعد كل سطر.
- استلمنا 24 ملف Python في الأرشيف الأصلي، وحافظنا عليه وعلى checkpoints. ضبط فؤاد وصلات switches على100Mbps/2ms؛ Topo والمنافذ وtc علىs1-eth1 والـpingall30/30 أكدوا الحالة المسجلة.
- أضفنا مراقبة inter-switch utilization وingress host-pair rates، وC5 بالعناوين المطلوبة، وelephant وEWMA، واختيار3paths والتحويل معbarriers والأولويات وشروط15pp/30s.
- أول trial غيّر المسار بأولوية20، فلم نعتبره نجاحLB. أصلحنا ARP refresh وترتيبDijkstra. ثاني trial أثبت نقلH3 الأصغر بأولوية21؛ أصلحنا تكلفة offered demand وترتيب القرار بالأكبر أولًا.
- ثالث trial هو النجاح الوظيفي المؤكد: grid-demo-20261117T193620Z.json؛ H1->H6 انتقلP1 إلىP3 بأولوية21 علىالأربعswitches، وقواعد20 القديمة لنفسالزوج غابت منOVS final. لا استنتاج بزمنتحويلدقيق منالفاصل بينعينات5s.
- نتيجة الأداء فينفسالتجربة لم تتحسن بمايكفي: H1receiver53.2Mbps وخسارة160610/433673(37%)، وH3receiver22.1Mbps وخسارة40025/153043(26%). البيانات الخام الثلاثة محفوظة دونتعديل؛ لا توجد معايرةiperf3 أوخمسruns أوتقريرنهائي جديد.
- جهزنا link_failure_demo.py لاختبارPing خفيف وفصلS5-S6 وإعادتها، وفحصنا syntax/parser محليًا فقط. فؤاد طلب التوقف قبل تشغيله؛ هو أولخطوةللاستكمال. لم نوقف أو نغيّر حالةVM عند إنهاءالجلسة.
- حدثنا ملفات البداية وAGENTS والخطة والـhandoff والمشاكل، وزامنا topology المحلية معالتعديلالمؤكد دونتصديرVM جديد. لارفع أوإنترنت أوتعديلPDF. Gitمحلي بلاremote؛ حالةcommit النهائية موضحةفيHANDOFF.

- حفظ الجلسة: تم إنشاء commit محلي بعد السماح بالكتابة داخل .git؛ لا remote أو إنترنت أو رفع. أضيفت .gitattributes للحفاظ على bytes المصدر والنتائج عند Git checkout.


## متابعة من سجل Git والتجارب حتى 2026-11-23

- طلب فؤاد تحديث الداشبورد أسرع؛ تم تقليل انتظار المتصفح من 5s إلى 1s بعد اكتمال الطلب. إحصائيات الكنترولر لها فترة مستقلة. سكربت العطل ينتظر 5s ثم يأخذ snapshot قبل طلب up، ويعرض نتيجة after بعد انتهاء ping. لم نغيّر أزمنة العطل أو شروط التجربة.

- مراجعة 23 نوفمبر: قراءة مسارات الكنترولر والتوبولوجي والواجهة والتجارب والمثبت. إصلاح switch_removed لتنظيف datapaths وإجماليات الإحصاء وARP والطلبات وإعادة بناء المسارات. المعايرة تحتفظ بنتيجة نافذة مكتملة لو قراءة المسار الختامية فشلت، مع تحذير محفوظ. إضافة topology للحالة لتشخيص اختلاف المود.
- أضيف experiments/check_logic.py، ونجحت 9 حالات منطق مع اعتماديات بديلة لاختبار الدوال الفعلية. شملت hold-down و15pp وتقدير المسارات والـbarriers وترتيب حذف القديم والـingress وتنظيف السويتش وتركيب الشبكتين ومعايرة محفوظة وفشل قراءة المسار النهائي. فُحص syntax لجميع مصادر التشغيل وJavaScript وقراءة 89 JSON. لم تُختبر imports الخاصة بـOS-Ken وMininet أو الشبكة فعليًا على Windows. ما زال 0/240 والفقد العالي يحتاجان Ubuntu.

- 18 نوفمبر: تشغيل Fat-tree والداشبورد. اختبارات المقارنة والتعافي والكشف والعتبة وقبل/بعد النقل محفوظة في experiments/results/. أمثلة للاسترجاع: recovery-20261118T173006Z وroute-phases-20261118T185932Z. تجربة عزل hold-down لم تحسم السبب.
- 19 نوفمبر: التقاط C1 ومعايرة iperf3. الجولتان المتوقفتان محفوظتان، والخامسة حُسبت من نافذة الإرسال والعينات الثلاث. تفاصيل القياس في الفصل الخامس. تجميع تقرير 32 صفحة وملحقاته في commit 53388ed.
- 21 نوفمبر: تجهيز نسخة Ubuntu المستقلة b2c2884 ثم الدليل العربي a4c8652. آخر إخراج من فؤاد 0/240 في Fat-tree. طُلبت حالة الكنترولر والمود؛ لا توجد مخرجات تحسم التشخيص حتى التسليم.
- 23 نوفمبر: توحيد ملفات بداية الجلسة والتسليم. فُحص تتبّع الملفات والأدلة في Git؛ لم تُشغّل VM أو تجارب جديدة. سجل Git يحفظ تغييرات الملفات، وهذا السجل يلخص البنود والقرارات والنتائج التي وصلت للمشروع.
