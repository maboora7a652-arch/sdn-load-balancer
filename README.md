# SDN Track 1: Intelligent Load Balancer with Fault Tolerance

آخر حفظ: 2026-11-17. فؤاد طلب نوقف النهارده ونكمل لاحقًا. كل العمل والحفظ offline؛ لا GitHub أو إنترنت حتى يطلب غير ذلك.

- ابدأ بـ[HANDOFF.md](HANDOFF.md)، ثم [PLAN.md](PLAN.md) و[ISSUES_AND_RISKS.md](ISSUES_AND_RISKS.md).
- التكليف: [Computer_Networks_Project_2026_v3.pdf](Computer_Networks_Project_2026_v3.pdf). لا proposal منفصل، وOS-Ken مسموح صراحة.
- [WORK_START_PROMPT_AR.md](WORK_START_PROMPT_AR.md) برومبت استكمال محدث؛ [ARABIC_START_HERE.md](ARABIC_START_HERE.md) مدخل مختصر.
- التقارير PDF وملفات C1 وسجل WORK_LOG أرشيف تقدم، وليست تقرير التسليم النهائي. لا يوجد docs/ أو reference/ هنا.

## آخر نتيجة مؤكدة

Grid فيها 6 switches و7 links و6 hosts، وصلات TCLink بسعة 100 Mbps وتأخير 2 ms، وpingall نجح 30/30. C5 يدعم /topology و/links و/flows مع الاحتفاظ بمسارات /sdn/ القديمة. المراقبة تعرض20 منفذًا، وتفاصيل التدفقات عند الدخول.

آخر تجربة فعلية محفوظة في [grid-demo-20261117T193620Z.json](experiments/results/grid-demo-20261117T193620Z.json): انتقل H1->H6 من P1 إلى P3 [1,4,5,6] بأولوية 21 على الأربع switches، واختفت قواعد 20 القديمة لنفس التدفق. تحسن الأداء لم يثبت؛ H1 receiver = 53.2 Mbps وفقد 37%، وH3 receiver = 22.1 Mbps وفقد 26% في نفس التجربة.

المتبقي يشمل معالجة أو تفسير فقد الحمل العالي، معايرة iperf3 و5 runs، وdashboard وbaselines والتسليم النهائي. التفاصيل في الخطة.

## أين الكود؟

- Windows: `vm-source/rest_api_controller.py` و`vm-source/custom_topology.py` هما نسختا العمل المحدثتان.
- Ubuntu: `~/sdn-lab/rest_api_controller.py` و`~/sdn-lab/custom_topology.py` هما الملفان النشطان اللذان يشغلهما فؤاد.
- المجلد المشترك: `/media/sf_sdn_transfer` يشير إلى مجلد المشروع علىWindows.
- الأرشيف `sdn-python-source-20261117-190113.tar.gz` والمجلد المستخرج بنفس الاسم baseline تاريخي، ليس آخر Controller.
- تم تحديث topology المحلية عند الإغلاق بنفس التعديل الذي نفذه فؤاد وأكد مخرجاته؛ لم نطلب تصديرًا جديدًا لإثبات تطابقها بالبايت معUbuntu. لا تخلط المصدر المستلم القديم بالنسخة المحدثة.
- لا نعيد نقل/حفظ/فحص بعد كل سطر. فؤاد ينفذ، ولا Computer Use بدون طلب جديد.

## تشغيل عادي بعد إيقاف أي تشغيل قديم

Terminal Ubuntu الأولى:

```bash
cd "$HOME/sdn-lab"
source .venv/bin/activate
osken-manager --observe-links --ofp-tcp-listen-port 6653 rest_api_controller.py
```

فترة المراقبة الافتراضية 5s. لتغييرها إلى 2s للتجارب لاحقًا، ضع `SDN_POLL_INTERVAL=2` قبل `osken-manager`؛ القيم المقبولة 2-5. الافتراضي 5s اختُبر على Ubuntu؛ تغيير T لم يُقيّم تجريبيًا بعد.

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