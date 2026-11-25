# تشغيل وديمو مشروع SDN على Ubuntu

آخر تحديث 2026-11-25. الأوامر التالية تُنفّذ داخل Ubuntu.

الكنترولر يضبط ساعة حساب مدد LLDP في وحدة الاكتشاف على monotonic عند بدء العملية، لحمايتها من تصحيح ساعة النظام داخل الـVM. مهلة LLDP الأصلية تظل10ثوانٍ، ومعالجة PortStatus للفصل الحقيقي كما في OS-Ken. يظهر سطر Discovery uses a monotonic clock عند تشغيل النسخة المحدثة. هذا إصلاح لحساب المدد؛ تأثيره على تقطّع الاكتشاف في التشغيل الحالي يحتاج تحققًا حيًا.

## مكان الملفات والتحديث

المشروع المحلي في ~/sdn-project. الكنترولر والتوبولوجي في vm-source، والتجارب ونتائجها في experiments، والداشبورد في dashboard. بيئة OS-Ken المستخدمة موجودة في ~/sdn-lab/.venv.

التعديل على نسخة Windows داخل /media/sf_sdn_transfer يحتاج نقله إلى نسخة Ubuntu. هذا الملف هو نسخة التشغيل التي تُنقل إلى ~/sdn-project/README.md. لتحديثه مع ملكية صحيحة:

```bash
sudo install -o "$(id -u)" -g "$(id -g)" -m 644 /media/sf_sdn_transfer/ubuntu/README.md "$HOME/sdn-project/README.md"
```

## 1. شغّل الـGrid

افتح ثلاثة ترمينالات. كل أمر في ترمينال منفصل، بالترتيب:

```bash
bash ~/sdn-project/run.sh controller grid
```

```bash
bash ~/sdn-project/run.sh network grid
```

```bash
bash ~/sdn-project/run.sh dashboard
```

انتظر 6 switches و7 links. افتح Firefox داخل Ubuntu على http://127.0.0.1:8081 واختار H1 → H6. عند تحديث ملفات الواجهة استخدم Ctrl+Shift+R.

عند mininet> افحص الاتصال:

```text
pingall
```

المتوقع 30/30. وصلات السويتشات تستخدم LabTCLink وLabTCIntf بسعة100Mbps وتأخير2ms وHTB burst/cburst64k. فحص التشغيل الجديد على s1-eth1 وs2-eth2 أظهر65512b. للتأكد بعد إعادة البناء:

```text
sh tc class show dev s1-eth1
sh tc class show dev s2-eth2
```

## 2. اعرض تحويل المسار تحت الزحمة

عند mininet> نفّذ السطر التالي مرة واحدة:

```text
py __import__('runpy').run_path('experiments/grid_demo.py', init_globals=dict(h1=h1,h3=h3,h5=h5,h6=h6)) and None
```

يبدأ H1 → H6 على P1: S1 → S2 → S3 → S6، وH3 → H5 على S2 → S3. الحمل المطلوب85 و30Mbps لمدة60ثانية. انتظر النتيجة النهائية. best هو المرشح، وcurrent المسار الحالي.

شرط الزحمة EWMA فوق70% لفترتين، والتدفق الكبير فوق10Mbps لفترتين. النقل يحتاج تحسن15نقطة مئوية ومرور30ثانية على آخر نقل لنفس الاتجاه. نجاح الديمو يعني Final H1->H6 كامل على [1,4,5,6] بأولوية21 أو أعلى. لو بقي[1,2,3,6] لم يثبت التحويل في هذه الجولة.

الداشبورد تقرأ كل ثانية تقريبًا بعد اكتمال الطلب، وإحصاءات الكنترولر لها فترة مستقلة افتراضيًا5ثواني.

## 3. اعرض التعافي الطويل بعد نجاح التحويل

لو H1 → H6 الآن على P3 بأولوية أعلى من20، نفّذ عند mininet>:

```text
py __import__('runpy').run_path('experiments/link_failure_demo.py', init_globals=dict(net=net)) and None
```

السكربت يرسل ping حوالي60ثانية. ينتظر8ثوانٍ ثم يفصل S5–S6 لمدة15ثانية على الأقل. يعرض مسارًا بديلًا أثناء الفصل، ثم يرجّع الوصلة ويعرض المسار بعد5ثوانٍ تقريبًا. هذا الوقت للمشاهدة؛ زمن التعافي يُستنتج من ردود ping.

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

## 4. الإيقاف وتشغيل الـFat-tree

اكتب exit في Mininet، واضغط Ctrl+C في ترمينال الكنترولر. شغّل الكنترولر والشبكة في ترمينالين باستخدام fattree:

```bash
bash ~/sdn-project/run.sh controller fattree
```

```bash
bash ~/sdn-project/run.sh network fattree
```

انتظر20switches و32links، ثم عند mininet>:

```text
pingall 2
```

المتوقع240/240. لو فشل الاتصال، اقرأ الحالة قبل إعادة كل المحاولات:

```text
sh curl -sS --max-time 3 http://127.0.0.1:8080/sdn/status
```

## 5. المعايرة والتجارب المتكررة

عند تقطّع مسارات Fat-tree، يمكن إجراء معايرة C4 على Grid المستقرة بين H1 وH6 بنفس المعدل ونوافذ القياس. أنشئ Grid جديدة واختبر الاتصال ثم شغّل:

```text
py __import__('runpy').run_path('experiments/bandwidth_accuracy.py', init_globals=dict(net=net, target='h6')) and None
```

تسجل المعايرة اسم الهدف في JSON. نتائج Grid وFat-tree دفعات منفصلة. هذا البديل يكمل قياس الدقة؛ مشكلة استقرار Fat-tree تظل مفتوحة.

على الـFat-tree بعد نجاح الاتصال، عند mininet>:

```text
py __import__('runpy').run_path('experiments/bandwidth_accuracy.py', init_globals=dict(net=net)) and None
```

خمس جولات UDP عند5Mbps، كل جولة30ثانية، باستخدام iperf3 المثبت. تحفظ النتائج في ~/sdn-project/experiments/results.

التجارب الدُفعية تبني شبكاتها بنفسها. اقفل Mininet والكنترولر الحاليين أولًا. في ترمينال Ubuntu عادي:

```bash
sudo python3 ~/sdn-project/experiments/compare_grid.py --help
```

اختار تجربة واحدة. --ten-flows للمقارنة مع shortest وECMP؛ --recovery لخمس تجارب تعافٍ قصيرة؛ --compare-shared-link لمقارنة فترات القياس؛ --compare-thresholds لتأثير العتبة؛ --route-phases للقياس قبل النقل وبعده.

نتائج التقرير القديمة استخدمت إعداد التشكيل السابق. عند إعادة التجارب بإعداد64k سجّل الإعداد واحتفظ بالنتائج الجديدة مستقلة.

## 6. اختبارات المنطق وWireshark

في ترمينال Ubuntu عادي:

```bash
python3 ~/sdn-project/experiments/check_logic.py
```

النسخة الحالية تتضمن14اختبارًا. اختبارات المنطق تحتاج استكمالها بالتجارب الحية. c1 يحتوي كود learning switch والتقاط Wireshark الأصلي. لإغلاق الديمو كله، exit في Mininet ثم Ctrl+C في الكنترولر والداشبورد.
