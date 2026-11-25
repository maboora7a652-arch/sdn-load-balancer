# تشغيل وديمو مشروع SDN على Ubuntu

آخر تحديث 2026-11-26. الأوامر التالية تُنفّذ داخل Ubuntu.

الكنترولر يستخدم monotonic لحساب مدد LLDP، ويحتفظ بمهلة الفشل الأصلية 10 ثوانٍ ومعالجة PortStatus للفصل الحقيقي. على Fat-tree يقل انتظار الإرسال بين البورتات إلى 0.01 ثانية كحد أقصى، ويتيح التنفيذ وقتًا للاكتشاف بين أزواج الأجهزة أثناء إعادة بناء المسارات. يظهر الإعداد في سطر بدء التشغيل. سجل التشغيل الأخير لم يتضمن حذف وصلات أو إعادة بناء بعد الاكتشاف الأول، لكن سبب التقطّع السابق لم يُحسم ولا نضمن الاستقرار في كل الظروف.

## مكان الملفات والتحديث

المشروع المحلي في ~/sdn-project. الكنترولر والتوبولوجي في vm-source، والتجارب ونتائجها في experiments، والداشبورد في dashboard. بيئة OS-Ken المستخدمة موجودة في ~/sdn-lab/.venv.

التعديل على نسخة Windows داخل /media/sf_sdn_transfer يحتاج نقله إلى نسخة Ubuntu. هذا الملف هو نسخة التشغيل التي تُنقل إلى ~/sdn-project/README.md. لتحديثه مع ملكية صحيحة:

```bash
sudo install -o "$(id -u)" -g "$(id -g)" -m 644 /media/sf_sdn_transfer/ubuntu/README.md "$HOME/sdn-project/README.md"
```

## 1. شغّل الـGrid

افتح ثلاثة ترمينالات. كل أمر في ترمينال منفصل، بالترتيب:

```bash
bash ~/sdn-project/run.sh controller grid 2>&1 | tee -a /tmp/sdn-controller-demo.log | grep --line-buffered -v 'C4 BANDWIDTH'
```

```bash
bash ~/sdn-project/run.sh network grid
```

```bash
bash ~/sdn-project/run.sh dashboard
```

أمر الكنترولر يحفظ كل الرسائل في ملف السجل التالي، ويخفي سطور C4 BANDWIDTH من الشاشة فقط. لا تحتاج اختيار أسطر يدويًا عند حدوث مشكلة:

```text
/tmp/sdn-controller-demo.log
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
bash ~/sdn-project/run.sh controller fattree 2>&1 | tee -a /tmp/sdn-controller-demo.log | grep --line-buffered -v 'C4 BANDWIDTH'
```

```bash
bash ~/sdn-project/run.sh network fattree
```

تأكد أن بدء الكنترولر يعرض LLDP timeout: 10.0s; send guard: 0.01s. انتظر 20 switches و32 links، ثم عند mininet>:

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

لو ظهر Stopped، احتفظ بملف JSON الذي يذكره Saved وبسجل الكنترولر قبل إعادة التشغيل. لا تعتبر الجولة المتوقفة قياسًا ناجحًا. يمكن الاستكمال ببارامتر resume داخل init_globals مع اسم الملف السابق؛ يحتفظ السكربت بالجولات التي حُسب لها error_percent. لو تغير الكود أو الإعداد بين الجولات، اذكر ذلك ولا تعرضها كدفعة متجانسة.

التجارب الدُفعية تبني شبكاتها بنفسها. اقفل Mininet والكنترولر الحاليين أولًا. في ترمينال Ubuntu عادي:

```bash
sudo python3 ~/sdn-project/experiments/compare_grid.py --help
```

اختار تجربة واحدة. --ten-flows للمقارنة مع shortest وECMP؛ --recovery لخمس تجارب تعافٍ قصيرة؛ --compare-shared-link لمقارنة فترات القياس؛ --compare-thresholds لتأثير العتبة؛ --route-phases للقياس قبل النقل وبعده.

دفعات التقييم المتكررة أُعيدت يوم 25 نوفمبر بإعداد 64k، وهي محفوظة بصورة مستقلة عن الدفعات القديمة. لا يلزم إعادة كل الدفعات أثناء العرض. التقرير وPDF الدليل ما زالا ينتظران تحديث الأرقام والإعدادات.

## نتيجة البروفة الأخيرة

- Grid: الاتصال 30/30، وتحويل H1 إلى H6 من P1 بأولوية 20 إلى P3 بأولوية 21. ملف النتيجة grid-demo-20261125T212305Z.json.
- التعافي الطويل: وصل 300/300، وتغيّر الطريق أثناء فصل S5–S6 ثم عادت الوصلة. ملف النتيجة link-failure-20261125T212611Z.json. هذه نتيجة الجولة، وليست ضمان فقد صفري في كل مرة.
- Fat-tree بعد تعديل LLDP: الاتصال 240/240. استُكملت الجولة الخامسة بخطأ 3.40%. ملف accuracy-20261125T221916Z.json يضم أربع جولات قبل التعديل وخامسة بعده، بمتوسط 3.14% وsample SD مقدارها 0.26 نقطة مئوية.
- مرجع المعايرة السابق بخمس جولات تحت إعداد واحد هو accuracy-20261125T193415Z.json، بمتوسط 3.74% وsample SD مقدارها 2.13 نقطة مئوية. لا تخلط الدفعتين.

## 6. اختبارات المنطق وWireshark

في ترمينال Ubuntu عادي:

```bash
python3 ~/sdn-project/experiments/check_logic.py
```

النسخة الحالية تتضمن14اختبارًا. اختبارات المنطق تحتاج استكمالها بالتجارب الحية. c1 يحتوي كود learning switch والتقاط Wireshark الأصلي. لإغلاق الديمو كله، exit في Mininet ثم Ctrl+C في الكنترولر والداشبورد.
