# خطة تسليم SDN Track 1

آخر تحديث 2026-11-18. الحالة الحالية في HANDOFF.md والعمل offline.
المرجع: تكليف الدكتور الأصلي، خصوصًا صفحات 2-4 و6-11. لا proposal منفصل. نكمل بندًا واحدًا كل مرة، ومن غير features خارج المطلوب.

## اللي بقى شغال على Grid

- [x] استلام المصدر القديم: 24 ملف Python، وحفظ الأرشيف والـcheckpoints كما وصلوا. نسخ العمل المحدثة داخل vm-source/.
- [x] اكتشاف 6 switches و7 links و6 hosts، وDijkstra وProxy ARP، وpingall بنتيجة 30/30 في التجارب المسجلة. لا ضمان عام لأول cold start.
- [x] TCLink بسعة 100 Mbps وتأخير 2 ms للوصولات السبع حسب Topo؛ فحص tc الفعلي على s1-eth1. نسخة topology المحلية اتزامنت مع التعديل عند الإغلاق، من غير VM export جديد.
- [x] مراقبة 20 منفذًا، منها 14 اتجاه inter-switch، وحساب utilization من فروق TX bytes والزمن والسعة. T قابل للضبط 2-5s، والافتراضي 5s هو المستخدم في التجارب الحالية.
- [x] /topology و/links و/flows تعمل مع الاحتفاظ بمسارات /sdn/ القديمة.
- [x] تفاصيل ingress لكل directed host pair، من غير عد نفس المرور عبر كل switches. القواعد MAC-pair IPv4، مش sessions منفصلة.
- [x] Elephant فوق 10% من السعة لفترتين؛ ظهر H2->H1 بمعدل 16.922316 Mbps وعدّاد 3 وelephant=true.
- [x] Congestion: EWMA بمعامل 0.5 فوق 70% لفترتين؛ ظهر true على S2->S3 في التجربة.
- [x] اختيار أول 3 simple paths حسب bottleneck المتوقع بعد النقل، ثم hops ثم shared links. نموذج offered demand مختلف عن utilization المقاس، وموضح في الكود والبيانات.
- [x] التحويل الفعلي H1->H6 من P1 إلى P3 بأولوية 21 على الأربع switches، وحذف قواعد 20 القديمة لنفس الزوج. المصدر يثبت من egress إلى ingress وينتظر barriers. الدليل: grid-demo-20261117T193620Z.json.
- [x] إصلاح تجديد ARP ليحافظ على المسار السليم والعدادات، وترتيب Dijkstra ثابت، والقرار مرة لكل round وبالأكبر أولًا.
- [x] Git محلي بلا remote وحفظ الشغل في commit بعد السماح بصلاحية .git. لا رفع للإنترنت.

## أول جزء هنكمله

- [x] تجربة S5-S6 نقلت H1 إلى H6 عبر P1 وقت الفصل، ووصل 79 من 80 ping.
- [ ] تأكيد hold-down لمدة 30s في اختبار حي يعزله عن شرط التحسن 15pp؛ منطق الشرطين اتفحص محليًا، والتحسن المستخدم في التحويل تجاوز 30pp.
- [x] اكتمل الديمو الوظيفي على Grid بنقل التدفق إلى P3 تحت الحمل ثم استعادة المرور على P1 عند فصل S5-S6.

## فجوات Common Core والأداء

- [ ] معايرة القياس باستخدام iperf3 بخطأ أقل من 10% ونوافذ مقارنة مناسبة. القياس المبدئي بـiperf2 اكتمل لخمس تجارب عند 5 Mbps بمتوسط خطأ 2.96%. معايرة iperf3 باقية؛ لا تثبيت أثناء offline.
- [ ] تفسير ومعالجة فقد الحمل العالي قبل ادعاء تحسن الأداء. أحدث تجربة: H1 receiver 53.2 Mbps وفقد 37%، وH3 receiver 22.1 Mbps وفقد 26%. لا نخفي النتائج ولا نخفض شروط الدكتور.
- [x] C1 على linear,2: نجح ping 3/3. ملف c1-linear-rerun.pcapng يوثق اتصال OpenFlow وقواعد التوجيه على السويتشين. تفاصيل الحزم في HANDOFF.md.

## التوسعة والتسليم المطلوبان

- [x] تشغيل Fat-tree k=4 على Ubuntu. فيها 20 سويتش و32 وصلة بين السويتشات، ونجح pingall 2 بين الـ16 هوست في كل الاتجاهات (240/240).
- [x] Dashboard المحلية اتنفذت. تعرض الشبكة واستخدام الوصلات والتدفقات وتغير المسار أو الوصلة بين العينات. أكدت لقطتا Firefox تغيّر معدل H1 إلى H16 وعرض استخدام وصلات المسار على fat-tree.
- [x] مقارنة Grid بحملي 85 و30 Mbps: خمس تشغيلات مكتملة لكل وضع shortest وbalanced، مع تسجيل الاستقبال والفقد والـjitter. نتائج الدفعة في HANDOFF.
- [x] مقارنة 10 تدفقات على Grid بخمس جولات متطابقة بين الأوضاع. متوسط أقصى TX utilization: ECMP 48.16% وshortest 56.16% وbalanced 56.20%. النتائج الخام ten-flows-20261118T170441Z.
- [x] تعافي Grid بعد فصل S5–S6 وإعادتها في خمس جولات. متوسط زمن أول رد 82.599 ms وفقد 6/1300 خلال الجولات.
- [x] مقارنة T=2 وT=5 على الحمل الأصلي عند 70%: لم تبلغ أي جولة شرط الاكتشاف. زمن الإعلان عند هذه العتبة ما زال مفتوحًا.
- [x] تأكيد العبور بجولة مستقلة بأربعة تدفقات: أول إعلان عند 18.905s لفترة قياس 5s. اكتملت المقارنة المتكررة بنفس الحمل والعتبة: اكتشاف 5/5 لكل إعداد؛ متوسط T2 بلغ 13.214s ومتوسط T5 بلغ 32.081s.
- [x] تأثير عتبة الزحمة عند T=2s: اكتشاف 5/5 عند 60% و1/5 عند 80%، مع مرجع 70% من الدفعة السابقة.
- [x] قياسات الاستقبال والفقد وjitter وping RTT في نوافذ قبل/بعد أول تحويل. دفعة 185932Z فيها خمس جولات و15 مقارنة مكتملة.
- [x] رسوم وجداول التجارب الأساسية، مع n والمتوسط والانحراف المعياري ومراجع الدفعات، في output/pdf/sdn-experiment-results.pdf.
- [ ] استكمال تجارب التقييم: دقة المراقبة، زمن الاكتشاف، throughput/delay/jitter/loss قبل وبعد النقل، max utilization، recovery time/lost packets، وتأثير T وtheta. كل تجربة 5 مرات على الأقل، مع mean/std وscripts وraw results ورسوم من البيانات الفعلية.
- [x] فصل 5 بالإنجليزية من ست صفحات بالرسوم والجداول وتفسير النتائج، في output/report/ بصيغتي Word وPDF.
- [ ] تقرير إنجليزي 25-35 صفحة A4 بحجم 12pt وIEEE references، وفصل SDN من 10-12 صفحة يغطي موضوعات التكليف، مع 15 مرجعًا على الأقل منها 5 papers تخص Track 1.
- [ ] توثيق design وimplementation والنتائج، user guide والمساهمات وتقارير التقدم المتاحة؛ من غير اختلاق تاريخ أو قياسات أو مساهمات.
- [ ] عرض 25-35 slides، و20 دقيقة عرض و10 demo و10 أسئلة، وفيديو 5-8 دقائق وREADME وتعليمات التشغيل والكود والنتائج.
- [ ] GitHub بعد إذن جديد من فؤاد. تاريخ التسليم في التكليف placeholder، فلا نفترض موعدًا.

## Later

- ML prediction وfast-failover groups هما bonus، و/sdn/routes اختياري فقط لو احتاجه dashboard.
- فصل TCP/UDP sessions لنفس الزوج لو احتاجته التجارب؛ إلى ذلك الحين نصرح أن تعريف التدفق host pair.
- تحديث dependencies أو التحقيق في عشرات Gbps غير المحدودة ليسا بندًا حاليًا، إلا لو عطل مثبت منع المطلوب.

## مصادر تقنية راجعناها قبل طلب offline

- Mininet TCIntf: https://mininet.org/api/classmininet_1_1link_1_1TCIntf.html
- Ryu traffic monitor: https://osrg.github.io/ryu-book/en/html/traffic_monitor.html
- NetworkX paths: https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.simple_paths.shortest_simple_paths.html
- Hedera: https://www.usenix.org/conference/nsdi10-0/hedera-dynamic-flow-scheduling-data-center-networks
