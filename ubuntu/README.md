# دليل Ubuntu: التشغيل والديمو والتثبيت

نسخة الدليل: guide-layout-20261126. هذا هو **دليل أوامر تشغيل الشبكة**. الأوامر التالية داخل Ubuntu.

## اختار بدايتك

| حالتك | ابدأ من هنا |
| --- | --- |
| المشروع موجود وعايز تشغّله أو تعرضه للدكتور | [التشغيل والعرض خطوة بخطوة](#demo) |
| أول مرة تثبّت المشروع على جهاز جديد | [التثبيت لأول مرة](#install) ثم ارجع للتشغيل |
| عندك نسخة قديمة وعايز تنقل تحديثات الشير | [تحديث النسخة الموجودة](#update) |
| عايز تجربة مقارنة أو Wireshark أو اختبارات منطق | [التجارب الإضافية](#experiments) |
| أمر توقف أو الاتصال فشل | [المشاكل الشائعة](#problems) |

**لفؤاد دلوقتي: ابدأ بالتشغيل والعرض.** التثبيت والتحديث يتعملوا عند الحاجة، مش قبل كل تشغيل.

نسخة تشغيل فؤاد في المسار الأول. علامة ~ في المسارين التاليين تعني مجلد حساب Ubuntu الحالي:

```text
/home/fouad/sdn-project/
~/sdn-project/
~/sdn-lab/.venv/
```

في GitHub اسم هذا الملف ubuntu/README.md. المُحدّث ينسخه إلى README.md داخل نسخة التشغيل المستقلة، فيبقى نفس دليل الأوامر قدامك في المكانين.

**اختار الترمينال الصحيح:** بلوكات bash في ترمينال Ubuntu العادي. البلوكات المكتوب قبلها mininet> داخل ترمينال الشبكة فقط. لا تكتب mininet> نفسها مع الأمر.

<a id="demo"></a>

## التشغيل والعرض خطوة بخطوة

المسار المعتاد للعرض: تشغيل Grid، فحص اتصال، نقل المسار تحت الضغط، ثم التعافي. Fat-tree والمعايرة تكملة لو عايز تعرضهم. التجارب الدُفعية مش مطلوبة كل مرة تشغّل فيها الديمو.

### 1. افتح المشروع في ثلاثة ترمينالات

ابدأ الكنترولر أولًا، ثم الشبكة، ثم الداشبورد. كل أمر في ترمينال Ubuntu منفصل. اترك الترمينالات مفتوحة.

**ترمينال 1: الكنترولر، مع حفظ السجل وإخفاء سطور الإحصاءات المتكررة من الشاشة.**

```bash
bash ~/sdn-project/run.sh controller grid 2>&1 | tee "/tmp/sdn-controller-grid-$(date +%Y%m%d-%H%M%S).log" | grep --line-buffered -v 'C4 BANDWIDTH'
```

**ترمينال 2: شبكة Mininet.**

```bash
bash ~/sdn-project/run.sh network grid
```

**ترمينال 3: الداشبورد.**

```bash
bash ~/sdn-project/run.sh dashboard
```

أمر الكنترولر يحفظ كل الرسائل في ملف السجل التالي، ويخفي سطور C4 BANDWIDTH من الشاشة فقط. لا تحتاج اختيار أسطر يدويًا عند حدوث مشكلة:

```text
/tmp/sdn-controller-grid-YYYYMMDD-HHMMSS.log
```

انتظر 6 switches و 7 links. افتح Firefox داخل Ubuntu على http://127.0.0.1:8081 واختار H1 → H6. عند تحديث ملفات الواجهة استخدم Ctrl+Shift+R.

عند mininet> افحص الاتصال:

```text
pingall
```

المتوقع 30/30. لو الاتصال فشل، اقرأ [المشاكل الشائعة](#problems) قبل تشغيل الحمل.

### 2. اعرض Load Balancing تحت الضغط

عند mininet> نفّذ السطر التالي مرة واحدة:

```text
py __import__('runpy').run_path('experiments/grid_demo.py', init_globals=dict(h1=h1,h3=h3,h5=h5,h6=h6)) and None
```

يبدأ H1 → H6 على P1: S1 → S2 → S3 → S6، و H3 → H5 على S2 → S3. الحمل المطلوب 85 و 30Mbps لمدة 60 ثانية. انتظر النتيجة النهائية. best هو المرشح، و current المسار الحالي.

شرط الزحمة EWMA فوق 70% لفترتين، والتدفق الكبير فوق 10Mbps لفترتين. النقل يحتاج تحسن 15 نقطة مئوية ومرور 30 ثانية على آخر نقل لنفس الاتجاه. نجاح الديمو يعني Final H1->H6 كامل على [1,4,5,6] بأولوية 21 أو أعلى. لو بقي[1,2,3,6] لم يثبت التحويل في هذه الجولة.

الداشبورد تقرأ كل ثانية تقريبًا بعد اكتمال الطلب، وإحصاءات الكنترولر لها فترة مستقلة افتراضيًا 5 ثواني.

### 3. اعرض التعافي بعد قطع وصلة

لو H1 → H6 الآن على P3 بأولوية أعلى من 20، نفّذ عند mininet>:

```text
py __import__('runpy').run_path('experiments/link_failure_demo.py', init_globals=dict(net=net)) and None
```

السكربت يرسل ping حوالي 60 ثانية. ينتظر 8 ثوانٍ ثم يفصل S5–S6 لمدة 15 ثانية على الأقل. يعرض مسارًا بديلًا أثناء الفصل، ثم يرجّع الوصلة ويعرض المسار بعد 5 ثوانٍ تقريبًا. هذا الوقت للمشاهدة؛ زمن التعافي يُستنتج من ردود ping.

### 4. اقفل العرض أو انتقل إلى Fat-tree

عند mininet> اكتب:

```text
exit
```

اضغط Ctrl+C في ترمينال الكنترولر. لو خلصت العرض كله، اضغط Ctrl+C في ترمينال الداشبورد أيضًا. لو هتكمل Fat-tree، ممكن تسيب الداشبورد مفتوحة وتعيد تشغيل الكنترولر والشبكة فقط.

### 5. شغّل Fat-tree لو هتعرض الشبكة الأكبر

بعد إيقاف Grid بالخطوة السابقة، شغّل الكنترولر والشبكة في ترمينالين باستخدام fattree:

```bash
bash ~/sdn-project/run.sh controller fattree 2>&1 | tee "/tmp/sdn-controller-fattree-$(date +%Y%m%d-%H%M%S).log" | grep --line-buffered -v 'C4 BANDWIDTH'
```

```bash
bash ~/sdn-project/run.sh network fattree
```

تأكد أن بدء الكنترولر يعرض مهلة 10.0s و send guard: 0.01s وسطر الانتظار المحدود. انتظر 20 switches و 32 links، واختار H1 → H16 في الداشبورد. ثم عند mininet>:

```text
pingall 2
```

المتوقع 240/240. لو فشل الاتصال، اقرأ الحالة قبل إعادة كل المحاولات:

```text
sh curl -sS --max-time 3 http://127.0.0.1:8080/sdn/status
```

### 6. معايرة الدقة على Fat-tree

بعد نجاح الاتصال، عند mininet>:

```text
py __import__('runpy').run_path('experiments/bandwidth_accuracy.py', init_globals=dict(net=net)) and None
```

خمس جولات UDP عند 5Mbps، كل جولة 30 ثانية، باستخدام iperf3 المثبت. تحفظ النتائج في ~/sdn-project/experiments/results. عند إنهاء العرض اكتب exit في Mininet واضغط Ctrl+C في الكنترولر والداشبورد.

لو ظهر Stopped، احتفظ بملف JSON الذي يذكره Saved وبسجل الكنترولر قبل إعادة التشغيل. لا تعتبر الجولة المتوقفة قياسًا ناجحًا. يمكن الاستكمال ببارامتر resume داخل init_globals مع اسم الملف السابق؛ يحتفظ السكربت بالجولات التي حُسب لها error_percent. لو تغير الكود أو الإعداد بين الجولات، اذكر ذلك ولا تعرضها كدفعة متجانسة.

<a id="install"></a>

## التثبيت لأول مرة على Ubuntu

هذا الجزء لجهاز Ubuntu جديد فقط. لو المشروع يعمل عندك بالفعل، ابدأ من [التشغيل والعرض](#demo). الأوامر هنا في ترمينال Ubuntu عادي.

بيئة التجارب المسجلة Ubuntu 22.04 و Python 3.10. يمكن استخدام Ubuntu داخل VirtualBox أو على جهاز Linux مستقل. الشبكة تحتاج Mininet و Open vSwitch داخل Ubuntu. التثبيت من الصفر على جهاز آخر لم يُجرّب هنا، وملف الاعتماديات ليس نسخة مقفولة من كل إصدارات البيئة الحالية.

### أ. تثبيت الأدوات على Ubuntu الجديد

```bash
sudo apt update
sudo apt install git mininet openvswitch-switch iperf iperf3 python3-venv curl
sudo systemctl start openvswitch-switch
```

Mininet يبني الشبكة، و Open vSwitch يشغّل السويتشات. نحتاج iperf لديمو Grid، و iperf3 للمعايرة. الإنترنت مطلوب لتنزيل الملفات والحزم أثناء الإعداد. لفتح التقاط C1 يمكنك تثبيت Wireshark أيضًا:

```bash
sudo apt install wireshark
```

### ب. اختار طريقة واحدة لجلب الملفات

الأسهل: نزّل المستودع مباشرة داخل Ubuntu، فلا تحتاج نقل ملفات من Windows:

```bash
git clone https://github.com/maboora7a652-arch/sdn-load-balancer.git "$HOME/sdn-project"
```

البديل: من GitHub على Windows اختار Code ثم Download ZIP، وفك الملف. شارك المجلد المستخرج مع VirtualBox. المثال التالي يفترض أن vm-source و ubuntu وباقي المجلدات موجودة مباشرة داخل /media/sf_sdn_transfer. لو فيه مجلد إضافي باسم sdn-load-balancer-master، استخدمه كمجلد المصدر بدلًا من جذر الشير.

| المجلد أو الملف | دوره |
| --- | --- |
| vm-source | الكنترولر الحالي والتوبولوجي |
| experiments بالكامل مع fixtures | الديموهات والتجارب واختبارات المنطق؛ results فيه النتائج المسجلة ونتائج التشغيل الجديد |
| dashboard | صفحة الداشبورد والخادم المحلي وملفات الواجهة |
| ubuntu | ملف التشغيل والدليل وأدوات النقل |
| requirements.txt | اعتماديات Python الخاصة بالكنترولر |
| c1 | learning switch والتقاط OpenFlow لجزء Wireshark |
| README.md | تعليمات المستودع |
| output و media و report_builder و video | اختيارية للتشغيل، وتحتاجها لو عايز التقارير والفيديو ومصادر التأليف |
| AGENTS.md و HANDOFF.md و PLAN.md و ISSUES_AND_RISKS.md و WORK_LOG.md | سياق المشروع وتاريخه عند تسليمه لشخص أو AI آخر |

لا تنقل بيئة Python الخاصة بـWindows. لا تستخدم الأرشيف القديم أو ملفات success أو before بدل vm-source الحالية.

لإنشاء نسخة تشغيل جديدة من الشير، نفّذ المجموعة التالية كما هي. تتوقف لو مجلد الوجهة موجود بالفعل، وتحافظ على ملكية النسخة الجديدة لحساب Ubuntu:

```bash
mkdir -- "$HOME/sdn-project" &&
sudo cp -R -- \
    "/media/sf_sdn_transfer/vm-source" \
    "/media/sf_sdn_transfer/experiments" \
    "/media/sf_sdn_transfer/dashboard" \
    "/media/sf_sdn_transfer/ubuntu" \
    "/media/sf_sdn_transfer/c1" \
    "/media/sf_sdn_transfer/requirements.txt" \
    "/media/sf_sdn_transfer/README.md" \
    "$HOME/sdn-project/" &&
sudo chown -R -- "$(id -u):$(id -g)" "$HOME/sdn-project"
```

غيّر مسار الشير لو اسمه عندك مختلف أو تستخدم USB. نشغّل من مجلد Ubuntu المحلي، فيستمر العمل حتى لو الشير غير متاح.

### ج. تجهيز بيئة الكنترولر وملف التشغيل

على الجهاز الجديد فقط، أنشئ البيئة بالأوامر التالية بدون sudo. المسار مقصود لأن ملف التشغيل والتجارب الدُفعية يستخدمانه:

```bash
mkdir -p -- "$HOME/sdn-lab"
python3 -m venv "$HOME/sdn-lab/.venv"
"$HOME/sdn-lab/.venv/bin/python" -m pip install -r "$HOME/sdn-project/requirements.txt"
```

ملف الاعتماديات يختار OS-Ken من سلسلة 3.x لأن المشروع يحتاج osken-manager. قيد التوافق لا يغيّر بيئتك الحالية، ولا يعني أننا قسنا النتائج على كل إصدارات الاعتماديات الجديدة. مراجع التثبيت: [Mininet](https://mininet.org/download/)، وملفات إعداد OS-Ken الرسمية [3.1.1](https://github.com/openstack/os-ken/blob/3.1.1/setup.cfg) و [4.0.0](https://github.com/openstack/os-ken/blob/4.0.0/setup.cfg).

بعد أي طريقة تنزيل، انسخ ملف التشغيل إلى جذر المشروع. لا تشغّل ubuntu/run.sh مباشرة لأنه سيبحث عن ملفات الشبكة داخل مجلد ubuntu:

```bash
cp -- "$HOME/sdn-project/ubuntu/run.sh" "$HOME/sdn-project/run.sh"
```

المسارات الأساسية بعد الإعداد:

```text
~/sdn-project/run.sh
~/sdn-project/vm-source/rest_api_controller.py
~/sdn-project/vm-source/custom_topology.py
~/sdn-project/experiments/
~/sdn-project/dashboard/
~/sdn-project/ubuntu/README.md
~/sdn-lab/.venv/bin/osken-manager
```

بعد الإعداد انتقل إلى [التشغيل والعرض](#demo). لا تحتاج تثبيت الأدوات من جديد كل مرة.

<a id="update"></a>

## تحديث نسخة Ubuntu الموجودة من الشير

المشروع المحلي في ~/sdn-project. الكنترولر والتوبولوجي في vm-source، والتجارب ونتائجها في experiments، والداشبورد في dashboard. بيئة OS-Ken المستخدمة موجودة في ~/sdn-lab/.venv.

التعديل على نسخة Windows داخل /media/sf_sdn_transfer يحتاج نقله إلى نسخة Ubuntu. بعد إيقاف الديمو، حدّث النسخة المستقلة كلها من ترمينال Ubuntu عادي:

```bash
sudo python3 /media/sf_sdn_transfer/ubuntu/update_local.py
```

المُحدّث ينقل الكود و README والاختبارات والتقارير والوسائط، ويحافظ على البيئة الموجودة والنتائج المحلية. لو الكنترولر الحالي مختلف، يحفظه في sdn-backups قبل استبداله. أي نتيجة محلية بنفس الاسم ومحتوى مختلف تظل كما هي ويذكرها في الخرج. لا يشغّل أو يوقف عمليات الشبكة تلقائيًا.

المُحدّث ينسخ هذا الدليل إلى README في جذر نسخة Ubuntu. للتأكد من تطابقه مع النسخة الحالية في الشير، نفّذ مرة واحدة بعد التحديث:

```bash
cmp -s "$HOME/sdn-project/README.md" "/media/sf_sdn_transfer/ubuntu/README.md" && echo "README is up to date"
```

ظهور الرسالة يؤكد تطابق محتوى README. تغيير الملفات على Windows وحده لا يؤكد وصولها إلى Ubuntu. أمر التحديث السابق يحتاج نسخة المستودع الكاملة في الشير، ويُنفّذ من الشير، وليس من داخل نسخة الوجهة.

<a id="experiments"></a>

## التجارب الإضافية

تُستخدم لإعادة التقييم أو لطلب محدد من الدكتور. اختار التجربة المطلوبة؛ لا تحتاج تشغيل القائمة كلها في العرض.

### المقارنات الدُفعية

التجارب الدُفعية تبني شبكاتها بنفسها. اقفل Mininet والكنترولر الحاليين أولًا. في ترمينال Ubuntu عادي:

```bash
sudo python3 ~/sdn-project/experiments/compare_grid.py --help
```

استخدم أمر المساعدة السابق لاختيار تشغيل واحد:

| الاختيار | التجربة |
| --- | --- |
| بدون flag للتجربة | مقارنة shortest و balanced بحمل 85+30Mbps |
| --ten-flows | مقارنة shortest و ECMP و balanced بعشرة تدفقات |
| --recovery | خمس جولات تعافٍ قصيرة، وفيها قطع S5–S6 وإرجاعها |
| --compare-shared-link | مقارنة فترتي القياس 2 و 5 ثوانٍ |
| --compare-thresholds | مقارنة عتبتي 60% و 80% |
| --route-phases | قياس نوافذ قبل نقل المسار وبعده |

مثال لإعادة تجربة العشرة تدفقات، بعد إيقاف الشبكة والكنترولر التفاعليين:

```bash
sudo python3 ~/sdn-project/experiments/compare_grid.py --ten-flows
```

دفعات التقييم المتكررة أُعيدت يوم 25 نوفمبر بإعداد 64k، وهي محفوظة بصورة مستقلة عن الدفعات القديمة وقبل إصلاح انتظار LLDP الأخير. لا يلزم إعادة كل الدفعات أثناء العرض. التقرير المحدث والرسوم والدليل موجودون تحت output داخل النسخة المحدثة.

### اختبارات المنطق و Wireshark

في ترمينال Ubuntu عادي:

```bash
python3 ~/sdn-project/experiments/check_logic.py
```

النسخة الحالية تتضمن 16 اختبار منطق، ونجحوا على Ubuntu. لفحص حفظ الملفات أثناء التحديث:

```bash
python3 ~/sdn-project/experiments/check_sync.py
```

دي اختبارات نقل منفصلة عن اختبارات الشبكة. c1 يحتوي كود learning switch والتقاط Wireshark الأصلي. لفتحه:

```bash
wireshark ~/sdn-project/c1/c1-linear-rerun.pcapng
```

استخدم الفلتر التالي داخل Wireshark:

```text
tcp.port == 6653 && tcp.len > 0
```

افتح حقول HELLO و FEATURES و FLOW_MOD و PACKET_IN و PACKET_OUT. الفيديو التعريفي مدته 96 ثانية وصامت، وهو منفصل عن تسجيل ديمو الشبكة.


<a id="problems"></a>

## المشاكل الشائعة والتفاصيل عند الحاجة

### الاتصال فشل أو عدد الوصلات ناقص

راجع أن الكنترولر والشبكة يعملان بنفس الاختيار، grid أو fattree. داخل Mininet اقرأ الحالة:

```text
sh curl -sS --max-time 3 http://127.0.0.1:8080/sdn/status
```

Grid يتوقع 6 switches و 7 links. Fat-tree يتوقع 20 switches و 32 links. استرجع أي وصلة فصلتها يدويًا. لا تعتبر نتيجة ping قديمة إثباتًا لحالة الشبكة الحالية.

### تجربة التعافي توقفت قبل القطع

لو ظهر Stopped: unexpected initial forwarding path، اقرأ Before failure. التجربة تتوقف قبل القطع حين يكون H1 على طريق مختلف. لاختبار التعافي وحده باستخدام H2 → H6، اختار الزوج ده في الداشبورد وشغّل:

```text
py __import__('runpy').run_path('experiments/link_failure_demo.py')['run_link_failure_demo'](net, source_name='h2', presentation=True)
```

الطريق المعتاد[4,5,6]، وأثناء القطع ظهر[4,1,2,3,6]. الجولة الطويلة لا تُخلط بإحصاءات جولات التعافي القصيرة القديمة.

للفصل اليدوي ثم الإرجاع:

```text
link s5 s6 down
link s5 s6 up
```

اكتب down كما هي. اختار وصلة موجودة على مسار التدفق قبل فصلها. أرجع أي وصلة فصلتها قبل التجربة التالية.

### المعايرة توقفت أو قراءة المسار ناقصة

احتفظ بملف Saved وبسجل الكنترولر. فشل القراءة مش نتيجة دقة ناجحة. المعايرة على Grid بديل منفصل عند الحاجة:

عند تقطّع مسارات Fat-tree، يمكن إجراء معايرة C4 على Grid المستقرة بين H1 و H6 بنفس المعدل ونوافذ القياس. أنشئ Grid جديدة واختبر الاتصال ثم شغّل:

```text
py __import__('runpy').run_path('experiments/bandwidth_accuracy.py', init_globals=dict(net=net, target='h6')) and None
```

تسجل المعايرة اسم الهدف في JSON. نتائج Grid و Fat-tree دفعات منفصلة. هذا البديل يكمل قياس الدقة؛ مشكلة استقرار Fat-tree تظل مفتوحة.

### فحص تشكيل الوصلة عند الحاجة

المتوقع 30/30. وصلات السويتشات تستخدم LabTCLink و LabTCIntf بسعة 100Mbps وتأخير 2ms و HTB burst/cburst64k. فحص التشغيل الجديد على s1-eth1 و s2-eth2 أظهر 65512b. للتأكد بعد إعادة البناء:

```text
sh tc class show dev s1-eth1
sh tc class show dev s2-eth2
```

### حدود الاكتشاف المسجلة

الكنترولر يستخدم monotonic لحساب مدد LLDP، ويحتفظ بمهلة الفشل الأصلية 10 ثوانٍ ومعالجة PortStatus للفصل الحقيقي. الإصلاح المحلي يمنع انتظار LLDP المفتوح عند وجود بورتات، ويظهر سطر LLDP wait is bounded while ports are present عند التشغيل. على Fat-tree انتظار الإرسال بين البورتات أقصاه 0.01 ثانية، مع إتاحة وقت للاكتشاف أثناء إعادة بناء المسارات. المعايرة الجديدة اكتملت خمس جولات، لكن السجلات الكاملة ما زالت تحتوي على دورات حذف وإعادة اكتشاف؛ لا نعتبر كل أسباب التقطّع محلولة.

<a id="recorded-results"></a>

<details>
<summary>النتائج المسجلة سابقًا ومصادرها، للرجوع فقط</summary>

## نتيجة البروفة الأخيرة

- Grid: الاتصال 30/30، وتحويل H1 إلى H6 من P1/20 إلى P3/21. ملف grid-demo-20261126T120202Z.json يبين استقبال H6 بمعدل 80 Mbps وفقد 5.9%، و H5 بمعدل 27.2 Mbps وفقد 9.3%.
- التعافي الطويل: وصل 299/300 وتغيّر الطريق أثناء فصل S5–S6 ثم عادت الوصلة. الملف link-failure-20261126T120735Z.json. فقد باكتة واحدة في هذه الجولة، ولا نضمن فقدًا صفريًا دائمًا.
- Fat-tree: الاتصال 240/240. معايرة جديدة كاملة بخمس جولات بعد إصلاح الانتظار في accuracy-20261126T124854Z.json، بمتوسط خطأ 3.115742% و sample SD مقدارها 0.180965 نقطة مئوية. كل جولة فيها ثلاث عينات وبدون تحذير نهائي للمسار.
- دفعة 221916Z المستكملة بإعدادين، ودفعة 193415Z الأقدم، محفوظتان منفصلتين؛ لا تجمعهما مع المعايرة الجديدة. source الأرقام والرسوم الخاصة بالفيديو موجود في media/video-data.json.

</details>
