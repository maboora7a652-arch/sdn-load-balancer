# مجلد تشغيل SDN المستقل على Ubuntu

انسخ **هذا المجلد ubuntu بالكامل** إلى جهاز Ubuntu، وسمِّ النسخة هناك sdn-project. كل ملفات تشغيل الشبكة والتجارب موجودة هنا؛ لا تحتاج جمع ملفات من باقي مجلدات المستودع.

## ابدأ هنا، أول مرة فقط

1. من GitHub اختار Code ثم Download ZIP، وفك الملف على Windows.
2. ادخل المجلد المستخرج وخد مجلد ubuntu كله. انقله إلى مجلد Home في Ubuntu باستخدام Shared Folder أو USB. سمِّ النسخة المنقولة sdn-project.
3. لو مجلد sdn-project كان موجودًا قبل النقل، لا تدمج فوقه يدويًا. استخدم قسم تحديث النسخة الموجودة أدناه.
4. افتح Terminal داخل Ubuntu ونفّذ بدون sudo:

```bash
bash "$HOME/sdn-project/setup.sh"
```

setup.sh يثبّت Mininet و Open vSwitch و iperf و iperf3 وباقي المتطلبات، ويجهّز OS-Ken. هيطلب باسورد Ubuntu عند تثبيت حزم النظام. لو بيئة OS-Ken القديمة موجودة، يستخدمها كما هي دون pip upgrade. الإنترنت مطلوب لأول تثبيت للحزم.

بيئة التشغيل التي استُخدمت في التجارب Ubuntu 22.04 و Python 3.10. التثبيت الجديد على جهاز آخر لم يُشغّل هنا؛ لا تعتبر فحوص الملفات بديلًا لتجربة الشبكة على جهازك.

بعد ظهور Ready، شغّل أوامر ترمينالات الكنترولر والشبكة والداشبورد في الخطوة 1 أدناه. **في المرات التالية تبدأ من الخطوة 1 مباشرة، ولا تعيد setup.sh.**

## الملفات التي يجب أن تكون عندك

```text
sdn-project/
    README.md
    setup.sh
    run.sh
    requirements.txt
    install_local.py
    update_local.py
    vm-source/
        rest_api_controller.py
        custom_topology.py
    dashboard/
    experiments/
        fixtures/
        results/
    c1/
```

| الملف أو المجلد | تستخدمه في إيه؟ |
| --- | --- |
| setup.sh | البداية على Ubuntu جديد، يجهّز البرامج والبيئة |
| run.sh | التشغيل اليومي: controller أو network أو dashboard |
| vm-source | كود الكنترولر والتوبولوجي الحالي |
| dashboard | صفحة الداشبورد وخادمها |
| experiments | الديموهات والاختبارات ونتائج التشغيل |
| c1 | كود learning switch والتقاط Wireshark الأصلي |
| requirements.txt | اعتماديات Python؛ يقرأها setup تلقائيًا |
| install_local.py | أداة نسخ داخلية يستدعيها setup لو شغّلته من Downloads أو الشير |
| update_local.py | تحديث نسخة تشغيل موجودة مع الحفاظ على نتائجها |

التقارير والفيديو ومصادر تأليفها موجودة في المستودع خارج هذا المجلد. لا تحتاجها لتشغيل الشبكة أو الديموهات أو اختبارات المنطق. ملفات Windows القديمة وبيئته الافتراضية لا تُنقل مع التشغيل.

<details>
<summary>لو هتنقل من الشير الحالي باستخدام أمر بدل File Manager</summary>

المثال يفترض أن مجلد ubuntu داخل الشير التالي. يُنشئ نسخة جديدة فقط؛ يتوقف لو مجلد الوجهة موجود أو symlink:

```bash
test ! -e "$HOME/sdn-project" && test ! -L "$HOME/sdn-project" &&
sudo cp -R -- "/media/sf_sdn_transfer/ubuntu" "$HOME/sdn-project" &&
sudo chown -R -- "$(id -u):$(id -g)" "$HOME/sdn-project"
```

بعدها شغّل setup.sh بالأمر الموجود أول الدليل. غيّر مسار المصدر لو اسم الشير عندك مختلف. لا تشغّل المشروع من مجلد الشير مباشرة.

</details>

## تحديث نسخة Ubuntu الموجودة، لفؤاد

نسخة التشغيل الموجودة تظل في ~/sdn-project، وبيئة OS-Ken في ~/sdn-lab/.venv. **لا تحتاج إعادة تثبيت المشروع بسبب ترتيب المجلدات الجديد.** بعد إيقاف Mininet والكنترولر والداشبورد، نفّذ من ترمينال Ubuntu عادي:

```bash
sudo python3 "/media/sf_sdn_transfer/ubuntu/update_local.py"
```

الأداة تنقل ملفات هذا المجلد مباشرة إلى نسخة التشغيل، وتحافظ على النتائج المحلية المختلفة والبيئة الموجودة، وتحفظ الكنترولر المختلف قبل استبداله. لو باقي المستودع موجود بجانب ubuntu، تنقل التقارير والوسائط وملفات تسليم AI أيضًا، بصورة اختيارية. المجلد المستقل يعمل بدونها.

للتأكد من وصول README بعد التحديث:

```bash
cmp -s "$HOME/sdn-project/README.md" "/media/sf_sdn_transfer/ubuntu/README.md" && echo "README is up to date"
```

تغيير Windows لا يصل إلى Ubuntu تلقائيًا. لا تستخدم setup لإعادة النسخ فوق مشروع موجود؛ استخدم المُحدّث السابق من الشير. لو توقف تثبيت جديد بعد نسخ المشروع، أكمل من setup.sh الموجود داخل ~/sdn-project؛ لا تعيد النسخ فوقه.

## 1. شغّل الـ Grid

افتح ثلاثة ترمينالات. كل أمر في ترمينال منفصل، بالترتيب:

```bash
bash ~/sdn-project/run.sh controller grid 2>&1 | tee "/tmp/sdn-controller-grid-$(date +%Y%m%d-%H%M%S).log" | grep --line-buffered -v 'C4 BANDWIDTH'
```

```bash
bash ~/sdn-project/run.sh network grid
```

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

المتوقع 30/30. وصلات السويتشات تستخدم LabTCLink و LabTCIntf بسعة 100Mbps وتأخير 2ms و HTB burst/cburst64k. فحص التشغيل الجديد على s1-eth1 و s2-eth2 أظهر 65512b. للتأكد بعد إعادة البناء:

```text
sh tc class show dev s1-eth1
sh tc class show dev s2-eth2
```

## 2. اعرض تحويل المسار تحت الزحمة

عند mininet> نفّذ السطر التالي مرة واحدة:

```text
py __import__('runpy').run_path('experiments/grid_demo.py', init_globals=dict(h1=h1,h3=h3,h5=h5,h6=h6)) and None
```

يبدأ H1 → H6 على P1: S1 → S2 → S3 → S6، و H3 → H5 على S2 → S3. الحمل المطلوب 85 و 30Mbps لمدة 60 ثانية. انتظر النتيجة النهائية. best هو المرشح، و current المسار الحالي.

شرط الزحمة EWMA فوق 70% لفترتين، والتدفق الكبير فوق 10Mbps لفترتين. النقل يحتاج تحسن 15 نقطة مئوية ومرور 30 ثانية على آخر نقل لنفس الاتجاه. نجاح الديمو يعني Final H1->H6 كامل على [1,4,5,6] بأولوية 21 أو أعلى. لو بقي[1,2,3,6] لم يثبت التحويل في هذه الجولة.

الداشبورد تقرأ كل ثانية تقريبًا بعد اكتمال الطلب، وإحصاءات الكنترولر لها فترة مستقلة افتراضيًا 5 ثواني.

## 3. اعرض التعافي الطويل بعد نجاح التحويل

لو H1 → H6 الآن على P3 بأولوية أعلى من 20، نفّذ عند mininet>:

```text
py __import__('runpy').run_path('experiments/link_failure_demo.py', init_globals=dict(net=net)) and None
```

السكربت يرسل ping حوالي 60 ثانية. ينتظر 8 ثوانٍ ثم يفصل S5–S6 لمدة 15 ثانية على الأقل. يعرض مسارًا بديلًا أثناء الفصل، ثم يرجّع الوصلة ويعرض المسار بعد 5 ثوانٍ تقريبًا. هذا الوقت للمشاهدة؛ زمن التعافي يُستنتج من ردود ping.

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

## 4. الإيقاف وتشغيل الـ Fat-tree

اكتب exit في Mininet، واضغط Ctrl+C في ترمينال الكنترولر. شغّل الكنترولر والشبكة في ترمينالين باستخدام fattree:

```bash
bash ~/sdn-project/run.sh controller fattree 2>&1 | tee "/tmp/sdn-controller-fattree-$(date +%Y%m%d-%H%M%S).log" | grep --line-buffered -v 'C4 BANDWIDTH'
```

```bash
bash ~/sdn-project/run.sh network fattree
```

تأكد أن بدء الكنترولر يعرض مهلة 10.0s و send guard: 0.01s وسطر الانتظار المحدود. انتظر 20 switches و 32 links، ثم عند mininet>:

```text
pingall 2
```

المتوقع 240/240. لو فشل الاتصال، اقرأ الحالة قبل إعادة كل المحاولات:

```text
sh curl -sS --max-time 3 http://127.0.0.1:8080/sdn/status
```

## 5. المعايرة والتجارب المتكررة

عند تقطّع مسارات Fat-tree، يمكن إجراء معايرة C4 على Grid المستقرة بين H1 و H6 بنفس المعدل ونوافذ القياس. أنشئ Grid جديدة واختبر الاتصال ثم شغّل:

```text
py __import__('runpy').run_path('experiments/bandwidth_accuracy.py', init_globals=dict(net=net, target='h6')) and None
```

تسجل المعايرة اسم الهدف في JSON. نتائج Grid و Fat-tree دفعات منفصلة. هذا البديل يكمل قياس الدقة؛ مشكلة استقرار Fat-tree تظل مفتوحة.

على الـ Fat-tree بعد نجاح الاتصال، عند mininet>:

```text
py __import__('runpy').run_path('experiments/bandwidth_accuracy.py', init_globals=dict(net=net)) and None
```

خمس جولات UDP عند 5Mbps، كل جولة 30 ثانية، باستخدام iperf3 المثبت. تحفظ النتائج في ~/sdn-project/experiments/results.

لو ظهر Stopped، احتفظ بملف JSON الذي يذكره Saved وبسجل الكنترولر قبل إعادة التشغيل. لا تعتبر الجولة المتوقفة قياسًا ناجحًا. يمكن الاستكمال ببارامتر resume داخل init_globals مع اسم الملف السابق؛ يحتفظ السكربت بالجولات التي حُسب لها error_percent. لو تغير الكود أو الإعداد بين الجولات، اذكر ذلك ولا تعرضها كدفعة متجانسة.

التجارب الدُفعية تبني شبكاتها بنفسها. اقفل Mininet والكنترولر الحاليين أولًا. في ترمينال Ubuntu عادي:

```bash
sudo python3 ~/sdn-project/experiments/compare_grid.py --help
```

اختار تجربة واحدة. --ten-flows للمقارنة مع shortest و ECMP؛ --recovery لخمس تجارب تعافٍ قصيرة؛ --compare-shared-link لمقارنة فترات القياس؛ --compare-thresholds لتأثير العتبة؛ --route-phases للقياس قبل النقل وبعده.

دفعات التقييم المتكررة أُعيدت يوم 25 نوفمبر بإعداد 64k، وهي محفوظة بصورة مستقلة عن الدفعات القديمة وقبل إصلاح انتظار LLDP الأخير. لا يلزم إعادة كل الدفعات أثناء العرض. التقرير المحدث والرسوم والدليل موجودون تحت output داخل النسخة المحدثة.

## نتيجة البروفة الأخيرة

- Grid: الاتصال 30/30، وتحويل H1 إلى H6 من P1/20 إلى P3/21. ملف grid-demo-20261126T120202Z.json يبين استقبال H6 بمعدل 80 Mbps وفقد 5.9%، و H5 بمعدل 27.2 Mbps وفقد 9.3%.
- التعافي الطويل: وصل 299/300 وتغيّر الطريق أثناء فصل S5–S6 ثم عادت الوصلة. الملف link-failure-20261126T120735Z.json. فقد باكتة واحدة في هذه الجولة، ولا نضمن فقدًا صفريًا دائمًا.
- Fat-tree: الاتصال 240/240. معايرة جديدة كاملة بخمس جولات بعد إصلاح الانتظار في accuracy-20261126T124854Z.json، بمتوسط خطأ 3.115742% و sample SD مقدارها 0.180965 نقطة مئوية. كل جولة فيها ثلاث عينات وبدون تحذير نهائي للمسار.
- دفعة 221916Z المستكملة بإعدادين، ودفعة 193415Z الأقدم، محفوظتان منفصلتين؛ لا تجمعهما مع المعايرة الجديدة. source الأرقام والرسوم الخاصة بالفيديو موجود في media/video-data.json.

## 6. اختبارات المنطق و Wireshark

في ترمينال Ubuntu عادي:

```bash
python3 ~/sdn-project/experiments/check_logic.py
```

النسخة الحالية تتضمن 16 اختبار منطق، ونجحوا على Ubuntu. لفحص حفظ الملفات أثناء التحديث:

```bash
python3 ~/sdn-project/experiments/check_sync.py
```

دي اختبارات نقل منفصلة عن اختبارات الشبكة. c1 يحتوي كود learning switch والتقاط Wireshark الأصلي. لفتحه:

لو Wireshark غير مثبت على الجهاز الجديد، ثبّته مرة واحدة من ترمينال Ubuntu عادي:

```bash
sudo apt install wireshark
```

ثم افتح الالتقاط:

```bash
wireshark ~/sdn-project/c1/c1-linear-rerun.pcapng
```

استخدم الفلتر tcp.port == 6653 && tcp.len > 0، وافتح حقول HELLO و FEATURES و FLOW_MOD و PACKET_IN و PACKET_OUT. لإغلاق الديمو، exit في Mininet ثم Ctrl+C في الكنترولر والداشبورد. فيديو media التعريفي المحدّث يعرض الأرقام الحالية مع فصل بعض الأمثلة التاريخية. مدته96ثانية وصامت، وليس تسجيل ديمو الشبكة. اعتمد فؤاد الفيديو كما هو، ولا توجد تعديلات فيديو مطلوبة.


## فريق المشروع

منسق المادة حسب التكليف الأصلي: Prof. Ahmed M. Abdelhaleem.

| الاسم | Student ID |
| --- | --- |
| عبدالحميد أحمد | 921230064 |
| عبدالرحمن أحمد محمد محمد | 921230066 |
| عبدالرحمن أحمد فؤاد | 921230065 |
| عبدالرحمن عمرو عبدالحليم | 921230069 |
| صهيب وائل محمد | 921230061 |
| عبدالرحمن صلاح الدين يحي | 921230068 |

توزيع المساهمات لكل فرد لم يُحدد بعد.
