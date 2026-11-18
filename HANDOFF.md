# HANDOFF

## Now: 2026-11-18

- الشغل والحفظ offline حتى يقول غير كده. لا إنترنت أو تنزيل أو رفع أو push. Git المحلي مسموح. ممنوع Computer Use بدون طلب جديد.
- فؤاد ينفذ على Ubuntu. نجمع التعديل في جزء مفيد واختبار في آخره، من غير نسخ وhash وrestart بعد كل سطر.
- اقرأ README.md وPLAN.md وISSUES_AND_RISKS.md في الجذر. لا يوجد docs/ أو reference/. المطلوب Track 1، ولا proposal منفصل، وOS-Ken مسموح.
- ملفات Ubuntu النشطة داخل ~/sdn-lab؛ نسخ العمل على Windows داخل vm-source/. الأرشيف المستلم ومجلده المستخرج baseline قديم ومجمّد.
- ملفات vm-source اتحدثت لدعم fat-tree. التشغيل الجديد من المجلد المشترك مباشرة، ونسخ Ubuntu القديمة ما اتغيرتش.

## اللي اشتغل واتأكد

- Grid من 6 switches و7 links و6 hosts، وpingall نجح 30/30. وصلات switches السبع معرفة TCLink بسعة 100 Mbps وتأخير 2 ms؛ فحص tc الفعلي كان على s1-eth1. Cold-start مش مضمون دائمًا بلا فقد.
- /topology و/links و/flows تعمل، مع بقاء مسارات /sdn/. المراقبة تعرض 20 منفذًا، منها 14 اتجاهًا لوصلات switches.
- القياس التفصيلي عند ingress هو directed host pair بقواعد IPv4 MAC-pair، وليس TCP/UDP sessions منفصلة. معدلات ingress لا تجمع نفس المرور عبر عدة switches.
- Elephant: أكبر من 10 Mbps لفترتين. Congestion: EWMA بمعامل 0.5 فوق 70% لفترتين. T الافتراضي 5s وقابل للضبط 2-5 عبر SDN_POLL_INTERVAL؛ مقارنة فترات T لم تُجرَ بعد.
- الاختيار بين 3 paths، بكلفة الحمل المتوقع بعد النقل، ثم hops وshared links. نموذج الطلب يستخدم max(port TX, ingress demand)؛ ده مختلف عن C4 measured utilization.
- التحويل يثبت priority أعلى من egress إلى ingress مع barriers، ثم يحذف قواعد الأولوية القديمة فقط. شرط التحسن 15pp وhold-down لمدة 30s موجودان؛ hold-down لم يُعزل في اختبار حي عن شرط التحسن.
- آخر دليل: experiments/results/grid-demo-20261117T193620Z.json. انتقل H1->H6 من P1 إلى P3 [1,4,5,6] بقواعد priority 21 على الأربع switches، ولا قواعد priority 20 متبقية لنفس الزوج في OVS final.
- Congestion ظهر عند 30s؛ آخر عينة P1 كانت 35.032s وأول P3 كانت 40.034s. دي نافذة رصد، مش قياس دقيق لزمن التحويل.
- نفس التجربة: H1 sender 84.9 Mbps، receiver 53.2 Mbps، loss 160610/433673 (37%)، jitter 5.585 ms، و13477 out-of-order. H3 sender 30.0 Mbps، receiver 22.1 Mbps، loss 40025/153043 (26%)، jitter 0.498 ms، و1206 out-of-order. الأداء لم يتحل.
- ARP refresh يحتفظ بالمسار السليم؛ baseline Dijkstra ثابت. القرار مرة لكل polling round، بالأكبر أولًا، ويرفض القياسات الأقدم من 2T.

## تجربة العطل والخطوة الجاية

- أثناء فصل S5-S6 رجع H1 إلى H6 عبر P1 بأولوية 20 واستمر عليه بعد استعادة الوصلة. وصل 79 من 80 ping. أكبر فاصل بين ردين 0.328979 ثانية. النتيجة في experiments/results/link-failure-20261118T143438Z.json.
- تجربة hold-down-20261118T150135Z.json رصدت P3 من 31.641s حتى 87.331s. تحسن P1 المتوقع 31.21 نقطة عند 48.156s دون رصد زحمة على P3؛ عزل المؤقت حيًا ما زال مفتوحًا. الـfat-tree جاهزة في المصدر؛ شغّل فؤاد fat-tree على Ubuntu؛ أول pingall 1 وصل 0/240، حتى بين h1 وh2 على s1. السبب مفتوح. التالي قراءة /sdn/status وقواعد s1 أثناء الجلسة الحالية قبل إعادة التشغيل. فحص محلي أكد 20 سويتش و16 هوست و32 وصلة بين السويتشات ومسافات كل أزواج الهوستات. راجع فجوة الأداء في تجارب التقييم.

## حدود مهمة

- فقد الحمل العالي وسببه مفتوحان؛ ومشكلة LLDP التاريخية مع 32-34 Gbps غير محلولة. لا نكرر الضغط الأعمى أو نغيّر حدود الدكتور لإظهار نجاح.
- iperf3 غير ظاهر عبر PATH؛ لا تثبيت أثناء offline. الدقة <10%، التجارب الخمس وmean/std، وقياس recovery time والتقرير والعرض والفيديو لم يكتملوا.
- C1 القديمة كانت single,2؛ يلزم مراجعتها مقابل linear المطلوبة. لا تزود دعم sessions منفصلة أو bonus إلا عند حاجة فعلية في الخطة.
- ملفات PDF القديمة لم تتحدث اليوم. WORK_LOG فيه ملحق الجلسة؛ النتائج الخام الثلاثة محفوظة دون تعديل في experiments/results/.
- تم حفظ الشغل في Git محلي بعد السماح بكتابة .git، بدون remote أو رفع أو إنترنت. حدّثنا ملفات البداية وAGENTS عند الإغلاق. استخدم git log لمعرفة آخر commit؛ لا تعيد طلب GitHub لمجرد الحفظ المحلي.

## SHA-256 لنسخ العمل المحلية يوم 2026-11-17 قبل إضافة fat-tree

- Controller: `ae5339affe9925cb40e4dde39db406f2cbab3d7cce506a6142b7009bf7ccdafe`
- Topology: `6b25536c804fca1ff2f51c009bd58fc1c66afe63bbb9fad73401237384c6cc8d`
- الأرشيف الأصلي: `7f7577a1f2816667a2dfe151bec759592714ecaaa47d643c9c55f2c5fa9a8188`
