# SDN Track 1: Intelligent Load Balancer with Fault Tolerance

ابدأ من [HANDOFF.md](HANDOFF.md) للحالة والتسليم بين الحسابات، و[PLAN.md](PLAN.md) للخطة، و[WORK_LOG.md](WORK_LOG.md) لتاريخ التنفيذ، و[ISSUES_AND_RISKS.md](ISSUES_AND_RISKS.md) للمشاكل. المرجع هو [تكليف الدكتور](Computer_Networks_Project_2026_v3.pdf).

## التشغيل الحالي

اتبع [دليل نسخة Ubuntu المستقلة](ubuntu/README.md) و[الدليل العربي](output/pdf/sdn-arabic-lab-guide.pdf). ملفات العمل في vm-source/ وdashboard/ وexperiments/. التقرير المجمّع موجود [هنا](output/report/sdn-track-1-report.pdf). العمل محلي وفؤاد ينفّذ أوامر الـVM.

## طريقة التشغيل الأصلية من الشير وبيئة التطوير

التعليمات التالية مرجع للنسخة القديمة أو لتشغيل مقصود من المجلد المشترك. عند استخدام النسخة المستقلة اتبع دليل Ubuntu أعلاه.

Terminal Ubuntu الأولى:

```bash
cd "$HOME/sdn-lab"
source .venv/bin/activate
osken-manager --observe-links --ofp-tcp-listen-port 6653 rest_api_controller.py
```

فترة المراقبة الافتراضية 5s. لتغييرها إلى 2s للتجارب لاحقًا، ضع `SDN_POLL_INTERVAL=2` قبل `osken-manager`؛ القيم المقبولة 2-5. الافتراضي 5s اختُبر على Ubuntu؛ نتائج مقارنة T موثّقة في الفصل الخامس.

Terminal الثانية:

```bash
sudo mn --custom "$HOME/sdn-lab/custom_topology.py" --topo mynetwork --mac --switch ovs,protocols=OpenFlow13 --link tc --controller=remote,ip=127.0.0.1,port=6653
```

داخلMininet: `pingall`. syntax checks منفصلة عن imports/runtime. لا تشغل mn-c أو توقف VM لمجرد قراءة الحالة.

## التجارب الجاهزة، لا تشغّل تلقائيًا عند الاستكمال

سيناريو التحويل، مرور 85 و30 Mbps بقيم bit/s صريحة لمدة 60s:

```text
py exec(open("/media/sf_sdn_transfer/experiments/grid_demo.py").read(), dict(h1=h1,h3=h3,h5=h5,h6=h6))
```

أمر تجربة العطل التي نُفذت يوم 2026-11-18. يبدأ من P3 ويفصل S5-S6 مؤقتًا ثم يعيدها.

```text
py exec(open("/media/sf_sdn_transfer/experiments/link_failure_demo.py").read(), dict(net=net))
```

الاختبار الثاني يحتاج الحالة الحالية managed P3 بأولوية أعلى من 20، ويتوقف قبل فصل أي وصلة لو الحالة مختلفة. يحتفظ بالمسار أثناءالعطل وraw ping timestamps، ويحاول إعادة الوصلة في finally عند الانقطاع. النتائج فيexperiments/results/ دون إنترنت أو نقل يدوي.

اختبار واحد ليس خمس تجارب أو قياسًا دقيقًا للاستعادة. أكبر فجوة بين ردودPing ليست وحدها زمن convergence.

## Run the k=4 fat-tree on Ubuntu

Exit the current Mininet CLI with `exit`, then stop its controller with Ctrl+C.
In the controller terminal, stage the shared source in a fresh user-owned directory. Only reading the VirtualBox share requires sudo. Keep Mininet running if it is already on fattree4:

```bash
run_dir=$(mktemp -d "$HOME/sdn-lab/fattree-run.XXXXXX") &&
cd "$run_dir" &&
sudo cat /media/sf_sdn_transfer/vm-source/rest_api_controller.py > rest_api_controller.py &&
SDN_TOPOLOGY=fattree4 "$HOME/sdn-lab/.venv/bin/osken-manager" --observe-links --ofp-tcp-listen-port 6653 "$PWD/rest_api_controller.py"
```

In the Mininet terminal:

```bash
sudo mn --custom /media/sf_sdn_transfer/vm-source/custom_topology.py --topo fattree4 --mac --switch ovs,protocols=OpenFlow13 --link tc --controller=remote,ip=127.0.0.1,port=6653
```

Once the controller reports 20 switches and 32 links, run `pingall 2` at the Mininet prompt. Sixteen hosts give 240 directed probes. The original grid uses the default controller mode and topology name `mynetwork`.

## Local dashboard

Keep the Ubuntu controller and Mininet running. Open another Ubuntu terminal:

```bash
sudo -u "$(id -un)" -g vboxsf -- python3 /media/sf_sdn_transfer/dashboard/serve.py
```

Open http://127.0.0.1:8081 in Firefox inside Ubuntu. The process uses your user identity with the VirtualBox shared-folder group for read access. Ctrl+C in this terminal stops the dashboard. No install required.

Select a directed host pair to highlight its controller-reported installed path. Each refresh reads topology, learned hosts, port TX utilization and ingress flow details from the local controller. Changes are detected between samples while the tab is open; brief events between polls can be missed. The most recent view stays on screen with a disconnected status if the controller stops responding.

## Compare ten concurrent flows on the grid

With the previous Mininet and controller processes stopped, run in the Ubuntu terminal:

```bash
sudo python3 /media/sf_sdn_transfer/experiments/compare_grid.py --ten-flows
```

Five matched rounds run shortest-path, ECMP and balanced routing on fresh grids in rotating order. Each round draws ten distinct directed host pairs with a fixed seed and reuses their UDP rates across all three modes. Total requested rate is 144 Mbps across all ten pairs. ECMP hashes each host pair onto an equal-hop shortest path and installs the reverse path symmetrically.

Peak utilization is the largest sampled TX utilization over all 14 inter-switch directions and ten snapshots during the common traffic window. The script also sums receiver throughput and computes loss weighted by receiver datagram totals. Raw samples, flow paths, iperf output and the summary are saved under experiments/results/ten-flows-UTC. To continue a stopped batch, pass --ten-flows --resume followed by its directory name.
