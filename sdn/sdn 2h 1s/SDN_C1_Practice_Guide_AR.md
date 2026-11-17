# دليل التدريب العملي: تشغيل أول شبكة SDN من الصفر

**المادة:** Computer Networks (ECE2606) — Common Core / C1  
**التجربة:** جهازان H1 وH2 + سويتش S1 + Controller باستخدام OS-Ken / OpenFlow 1.3  
**الجهاز:** Ubuntu 22.04 داخل VirtualBox  
**مكان مشروعنا:** `/home/fouad/sdn-lab`  
**نوع الملف:** دليل تدريب ومراجعة عملي — مش تقرير التسليم النهائي

> **الهدف:** تقدر تقفل كل البرامج وتفتحها تاني، وتشغّل الـ Controller، وتربط Mininet بيه، وتختبر الاتصال، وتعرض الـ Flow Tables، وتسجّل رسائل OpenFlow في Wireshark، *من غير ما تحتاج ترجع للشات*. كل أمر متشرح والغرض منه واضح.

---

## 0) الخريطة الذهنية — مين بيعمل إيه؟

```text
                 OS-Ken Controller
                 first_controller.py
                  127.0.0.1:6653
                         |
                OpenFlow 1.3 (TCP)
                         |
   H1 (10.0.0.1) --- S1 (Open vSwitch) --- H2 (10.0.0.2)
          منفذ 1                  منفذ 2

                 Mininet ينشئ البيئة دي كلها داخل Ubuntu
```

| الأداة | دورها في التجربة |
|---|---|
| **VirtualBox** | يشغّل Ubuntu كجهاز افتراضي على Windows. |
| **Mininet** | ينشئ الـ Hosts والـ Switch والروابط الافتراضية، ويديك `mininet>` علشان تختبر الشبكة. |
| **Open vSwitch (OVS)** | هو السويتش الفعلي برمجيًا، عنده Flow Tables وبيمرر الـ Frames. |
| **OS-Ken** | Controller بلغة Python، مشابه لـ Ryu ومسموح به في ملف المشروع. |
| **OpenFlow 1.3** | بروتوكول التحكم بين الـ Controller والـ Switch. |
| **Wireshark** | بيسجّل وبيحلل رسائل OpenFlow اللي ماشية على الشبكة. |

**قاعدة ذهبية:** الـ Controller **بيقرر/بيثبت قواعد**، والـ Switch **بينقل البيانات طبقًا للقواعد**. مش كل Packet لازم تروح للـ Controller.

---

## 1) كل مرة قبل ما تبدأ — فحص سريع

افتح Ubuntu، واضغط `Ctrl + Alt + T` علشان تفتح Terminal. نفّذ الأوامر التالية **واحد واحد**:

```bash
python3 --version
```
- `python3`: تشغيل Python 3.
- `--version`: عرض الإصدار. استخدمنا بيئة Python 3.10 في تجربتنا السابقة.

```bash
mn --version
```
- `mn`: برنامج Mininet.
- `--version`: التأكد إنه موجود وعرض إصداره (نسخة التثبيت الفعلية سجّلها عندك).

```bash
sudo systemctl is-active openvswitch-switch
```
- `sudo`: صلاحيات إدارية.
- `systemctl`: أداة إدارة خدمات Linux.
- `is-active`: اسأل هل الخدمة شغالة.
- `openvswitch-switch`: اسم خدمة Open vSwitch.
- **المتوقع:** `active`. لو مش نشطة، استخدم: `sudo systemctl start openvswitch-switch`، وبعدها أعد الفحص.

```bash
cd ~/sdn-lab
ls -la
```
- `cd`: غيّر المجلد الحالي. الرمز `~` معناه مجلد المستخدم (`/home/fouad`).
- `ls`: عرض الملفات؛ `-l` تفاصيل و`-a` إظهار الملفات المخفية زي `.venv`.
- **لازم تلاقي:** مجلد `.venv` وملف `first_controller.py` إن كانوا محفوظين من تجربتنا.

> إذا الملف أو الـ virtual environment غير موجودين، راجع قسم **استرجاع الملفات** بالأسفل. ما تعملش تثبيت جديد عشوائيًا قبل ما تتأكد.

---

## 2) Terminal رقم 1 — تشغيل الـ Controller

### 2.1 ادخل مجلد المشروع وفعّل بيئة Python

```bash
cd ~/sdn-lab
source .venv/bin/activate
```

- `source`: يقرأ ويشغّل سكربت داخل الـ Shell الحالي.
- `.venv/bin/activate`: سكربت تفعيل Python Virtual Environment اللي ثبتنا جواها OS-Ken.
- **المتوقع:** بداية سطر الـ Terminal تبقى `(.venv)`.

اتأكد إن أمر التشغيل موجود:

```bash
which osken-manager
```

- `which`: يبيّن مكان البرنامج اللي هيتشغّل عند كتابة اسمه.
- **اللي ظهر عندنا فعلًا:** `/home/fouad/sdn-lab/.venv/bin/osken-manager`.

لو عايز تراجع الحزمة والإصدار:

```bash
python -m pip show os-ken
```

- `python -m pip`: شغّل مدير مكتبات Python الخاص بالبيئة المفعّلة.
- `show os-ken`: اعرض معلومات المكتبة المثبتة.
- استخدمنا إصدار **3.1.1** بعد ما الإصدار الأحدث عندنا مكنش موفّر نفس أمر التشغيل القديم.

### 2.2 تأكد إن الكود موجود وصحيح نحويًا

```bash
ls -l first_controller.py
python -m py_compile first_controller.py
```

- `ls -l`: يثبت إن الملف موجود.
- `python -m py_compile`: يفحص صياغة Python ويعمل Compilation، **مش** بيشغّل الـ Controller فعليًا؛ لو مفيش Error ده اختبار Syntax ناجح.

لو الملف **مش موجود**، انشئه باستخدام:

```bash
nano first_controller.py
```

ثم انسخ الكود الكامل من **الملحق A** في آخر الدليل؛ للحفظ داخل Nano اضغط `Ctrl+O` ثم `Enter`، وللخروج `Ctrl+X`.

### 2.3 شغّل الـ Controller

```bash
osken-manager --ofp-tcp-listen-port 6653 first_controller.py
```

| جزء الأمر | تفسيره |
|---|---|
| `osken-manager` | برنامج تشغيل تطبيقات OS-Ken Controller. |
| `--ofp-tcp-listen-port` | خيار تحديد منفذ TCP لاستقبال اتصالات OpenFlow. |
| `6653` | المنفذ اللي Mininet هيوصل عليه. |
| `first_controller.py` | برنامج Python اللي فيه منطق الـ Learning Switch. |

**المتوقع:** تظهر رسائل تحميل التطبيق مثل `loading app first_controller.py` و`instantiating app ... LearningSwitch`، والبرنامج يفضل شغال بدون رجوع لسطر `$`. بعد اتصال Mininet تظهر `Switch 1 connected`.

**مهم جدًا:** سيب Terminal رقم 1 **مفتوحة**. التحذير `EventletDeprecationWarning` ظهر عندنا، لكنه لم يمنع التشغيل. أما لو ظهر `Traceback` وتوقف البرنامج، يبقى محتاجين نعالج الخطأ.

---

## 3) Terminal رقم 2 — أنشئ الشبكة واربطها بالـ Controller

افتح Terminal **جديدة** بـ `Ctrl + Alt + T`. متقفّلش الأولى.

نفّذ هذا الأمر **كسطر واحد**:

```bash
sudo mn --topo single,2 --mac --switch ovs,protocols=OpenFlow13 --controller remote,ip=127.0.0.1,port=6653
```

| جزء الأمر | شرحه |
|---|---|
| `sudo` | Mininet يحتاج صلاحيات لإنشاء الـ namespaces والـ virtual interfaces. |
| `mn` | شغّل Mininet. |
| `--topo single,2` | أنشئ **Switch واحد** و**Hostين** متصلين به. |
| `--mac` | أعطِ الأجهزة MAC addresses مرتبة وسهلة التمييز. |
| `--switch ovs,protocols=OpenFlow13` | استخدم Open vSwitch وقيّده ببروتوكول OpenFlow 1.3. |
| `--controller remote` | اربط Mininet بـ Controller شغال في Process مستقل. |
| `ip=127.0.0.1` | عنوان Localhost لأن OS-Ken وMininet داخل نفس Ubuntu. |
| `port=6653` | نفس منفذ الاستماع اللي شغّلنا عليه الـ Controller. |

**المتوقع:** رسائل `Adding hosts: h1 h2` و`Adding switches: s1` و`Starting 1 switches` ثم يظهر:

```text
mininet>
```

بص على Terminal رقم 1؛ المفروض تلاقي:

```text
Switch 1 connected
```

لو ظهرت الرسالة دي، فدي علامة قوية على نجاح اتصال OpenFlow والحدث البرمجي `switch_connected()`.

> **فرق لازم تفتكره:** الأمر السابق اللي اختبرنا به Mininet أول مرة كان `sudo mn --switch ovsbr --test pingall`. ده Switch مستقل، **مش** نفس اختبار Controller خارجي. التدريب الحالي يستخدم `remote` وOpenFlow 1.3.

---

## 4) أوامر Mininet اللي هتتدرب عليها

**الأوامر التالية تكتبها عند** `mininet>` **مش عند** `fouad@MSD3:~$`.

### 4.1 اعرض الأجهزة

```text
nodes
```

- يعرض أسماء العناصر الافتراضية في الشبكة، مثل `h1` و`h2` و`s1` وربما `c0`.

### 4.2 اعرض التوصيلات

```text
net
```

- يبيّن كل عنصر متصل بمين، ويعرض أسماء الـ Interfaces.

### 4.3 اختبر الاتصال بين كل الـ Hosts

```text
pingall
```

- Mininet يطلب اختبارات Ping بين الـ Hosts.
- **اللي حصل عندنا:** `*** Results: 0% dropped (2/2 received)`.

### 4.4 اختبر من H1 إلى H2 خمس مرات

```text
h1 ping -c 5 h2
```

| الجزء | وظيفته |
|---|---|
| `h1` | نفّذ الأمر داخل الـ Host الافتراضي H1. |
| `ping` | أرسل ICMP Echo Requests لاختبار الاتصال. |
| `-c 5` | أرسل **5** طلبات فقط، بدل إرسالها باستمرار. |
| `h2` | اسم الـ Host المستهدف؛ Mininet يحلّه لعنوانه. |

- **اللي حصل عندنا:** `5 packets transmitted, 5 received, 0% packet loss`.
- في تشغيل مسجل واحد كانت قيم RTT: `min/avg/max/mdev = 0.099/1.514/3.134/1.323 ms`؛ **مش متوسط تجارب**.

### 4.5 اعرض قواعد OpenFlow المثبتة داخل S1

```text
sh ovs-ofctl -O OpenFlow13 dump-flows s1
```

| الجزء | معناه |
|---|---|
| `sh` | نفّذ أمر Linux من داخل Mininet CLI. |
| `ovs-ofctl` | أداة فحص وإدارة OpenFlow في OVS. |
| `-O OpenFlow13` | استخدم إصدار OpenFlow 1.3 في الأمر. |
| `dump-flows` | اعرض الـ Flow Entries الحالية. |
| `s1` | اسم الـ OVS Bridge / Switch المراد فحصه. |

**القواعد اللي ظهرت عندنا سابقًا:**

```text
priority=1,in_port="s1-eth2",dl_dst=00:00:00:00:00:01 actions=output:"s1-eth1"
priority=1,in_port="s1-eth1",dl_dst=00:00:00:00:00:02 actions=output:"s1-eth2"
priority=0 actions=CONTROLLER:65535
```

- أول قاعدة: Frames من H2 إلى H1، تخرج من Port 1.
- ثاني قاعدة: Frames من H1 إلى H2، تخرج من Port 2.
- ثالث قاعدة: **Table-miss** — لو مفيش قاعدة أعلى مناسبة، ابعت للـ Controller.
- `n_packets` و`n_bytes` عدادات **تراكمية** للـ Packets والـ Bytes المطابقة للقاعدة.

### 4.6 تدريب على العدادات

1. نفّذ `dump-flows` وسجّل `n_packets` للقواعد الثلاث.
2. نفّذ `h1 ping -c 5 h2`.
3. نفّذ `dump-flows` تاني، وقارن الأرقام.
4. لاحظ إن العدادات ممكن تزيد بسبب Traffic إضافي غير الـ Ping؛ ما ننسبش كل زيادة للـ Ping من غير Capture/عزل للترافيك.

---

## 5) Wireshark — سجل المحادثة بين الـ Controller والـ Switch

### الفكرة

- بيانات المستخدم H1 ↔ H2 تمر في منافذ S1.
- رسائل التحكم **OpenFlow** بين S1 وOS-Ken تمر على `127.0.0.1:6653` عبر واجهة **Loopback: lo**.
- علشان تلتقط **HELLO** من البداية: شغّل الـ Controller أولًا، وابدأ Wireshark Capture **قبل** تشغيل Mininet.

### الترتيب الصح للتجربة من الصفر

1. **Terminal 1:** شغّل `osken-manager ... first_controller.py` وسيبها مفتوحة.
2. **Terminal 3:** افتح Wireshark من قائمة البرامج أو اكتب في Terminal جديدة `wireshark`.
3. في Wireshark دبل كليك على **Loopback: lo** علشان يبدأ التسجيل.
4. في خانة **Display Filter** (بعد بدء التسجيل) اكتب:

   ```text
   tcp.port == 6653
   ```

   ده بيعرض TCP Traffic اللي مصدره أو وجهته المنفذ 6653.
5. **Terminal 2:** شغّل أمر `sudo mn ...` من القسم 3، ثم داخل `mininet>` نفّذ `h1 ping -c 2 h2`.
6. ارجع Wireshark واضغط **Stop** الأحمر **بعد** ما تخلص تسجيل.
7. استخدم **File → Save As**، واحفظ الملف مثلًا:

   ```text
   /home/fouad/sdn-lab/c1_openflow_capture.pcapng
   ```

   **تحذير:** احنا شوفنا Capture في الجلسة السابقة، لكن مش متأكدين إن ملف `.pcapng` اتحفظ على جهازك. لو مش موجود، اعمل Capture جديدة واحفظها.

### أهم Display Filters

| الفلتر | بيعرض إيه؟ |
|---|---|
| `tcp.port == 6653` | اتصال OpenFlow بالكامل، بما فيه TCP. |
| `openflow_v4.type == 0` | HELLO. |
| `openflow_v4.type == 6` | FEATURES_REPLY. |
| `openflow_v4.type == 14` | FLOW_MOD. |
| `openflow_v4.type == 10` | PACKET_IN. |
| `openflow_v4.type == 13` | PACKET_OUT. |
| `openflow_v4.type == 10 || openflow_v4.type == 13` | PACKET_IN **أو** PACKET_OUT. |

**متخلطش بين:**
- **Capture Filter:** بيتطبق أثناء التسجيل ويحدد إيه اللي هيتجمع.
- **Display Filter:** بيخفي ويظهر أجزاء من البيانات **بعد جمعها**؛ لا يحذفها من ملف الالتقاط.

### الرسائل اللي ظهرت معانا فعلًا

| الرسالة | معناها في تجربتنا |
|---|---|
| `HELLO` | الطرفان بدأوا اتصال OpenFlow 1.3. |
| `FEATURES_REQUEST / REPLY` | الـ Controller سأل، وS1 أعلن هويته وقدراته. |
| `MULTIPART_REQUEST (PORT_DESC)` | طلب وصف منافذ الـ Switch. |
| `FLOW_MOD` | الـ Controller ثبّت قاعدة في جدول السويتش. |
| `PACKET_IN` | S1 بعت Frame لمطابقة Table-miss. |
| `PACKET_OUT` | OS-Ken طلب التعامل مع Frame محددة (منها حالة Flooding). |
| `ECHO_REQUEST / REPLY` | تبادل رسائل متابعة اتصال التحكم. |

**ملاحظة من الـ Capture بتاعتنا:** الـ `PACKET_IN` رقم 432 والـ `PACKET_OUT` رقم 434 كانوا خاصين بـ **ICMPv6 multicast** من H2، مش Ping IPv4؛ مهم ما نخلطش بينهم.

---

## 6) اقفل التجربة بطريقة صحيحة

**الترتيب المقترح:**

1. في Wireshark: اضغط **Stop** واحفظ ملف `.pcapng`.
2. في **Terminal 2** عند `mininet>` اكتب:

   ```text
   exit
   ```

   ده بيوقف الـ Topology وينضف Mininet الموارد اللي أنشأها.
3. في **Terminal 1** اللي فيها OS-Ken اضغط `Ctrl + C` لإيقاف الـ Controller.
4. اقفل النوافذ عادي.

لو Mininet وقف بشكل غير طبيعي وساب Virtual Interfaces قديمة، وبعد ما تتأكد إنه **مش شغال**، استخدم من Terminal عادية:

```bash
sudo mn -c
```

- `-c`: أمر تنظيف حالة Mininet القديمة. **متستخدموش أثناء تشغيل شبكة عايز تحافظ عليها.**

---

## 7) أخطاء واجهتنا فعلًا وحلّها

| المشكلة | السبب / التصرف |
|---|---|
| `osken-manager: command not found` | الإصدار 4.2.2 اللي اتثبت في البداية لم يوفر أداة التشغيل القديمة في تجربتنا؛ انتقلنا لإصدار 3.1.1 داخل `.venv`. أولًا اتأكد إنك فعلت البيئة وأن `which osken-manager` بيرجع مسار. |
| `No module named os_ken.app.simple_switch_13` | المثال الجاهز غير متاح في الحزمة اللي استخدمناها؛ كتبنا تطبيق **محلي** اسمه `first_controller.py` وشغّلناه بالاسم ده بدل المثال. |
| تحذير Eventlet | ظهر عند تشغيل Controller، لكن البرنامج كمل وظهر `Switch 1 connected`. لو ظهر **Traceback** جديد، احتفظ بالنص وراجعه. |
| `mininet>` لا يظهر | شوف آخر Error في Terminal 2، واتأكد إن مفيش Mininet قديم شغال؛ التنظيف `sudo mn -c` فقط بعد إيقافه. |
| `Switch 1 connected` لا تظهر | راجع أن Controller شغال على 6653، وأن عنوان Mininet هو `127.0.0.1` وأن OpenFlow13 مضبوط. |
| `pingall` يفشل | افحص الاتصال بالـ Controller ونتيجة `dump-flows`، وجرب Ping ثانية بعد تعلم MAC؛ ما تعتبرش الفقد دائمًا طبيعيًا. |
| Wireshark لا يرى رسائل HELLO | لازم تبدأ Capture **قبل** تأسيس الاتصال؛ اخرج من Mininet وشغّله بعد بدء Capture. |
| Wireshark لا يسمح بالتقاط Packets | تأكد إن الحساب في مجموعة `wireshark` (أمر `groups`)، واعمل Log Out/Log In أو استخدم `newgrp wireshark` داخل Shell المناسبة. |

---

## 8) تمرين تعمله لوحدك (Self-check)

علّم على كل بند لما تنجح فيه:

- [ ] فتحت Ubuntu وراجعت خدمة Open vSwitch.
- [ ] فعلت `.venv` وتأكدت إن `first_controller.py` موجود.
- [ ] شغّلت Controller في Terminal مستقلة.
- [ ] فتحت Wireshark وسجلت على Loopback قبل Mininet.
- [ ] شغّلت Mininet بالشبكة `single,2` وOpenFlow 1.3.
- [ ] شفت `Switch 1 connected`.
- [ ] شغّلت `nodes` و`net` وفهمت التوصيلات.
- [ ] شغّلت `pingall` و`h1 ping -c 5 h2`.
- [ ] استخدمت `dump-flows` وحددت Rule اتجاه H1→H2 واتجاه H2→H1 والـ Table-miss.
- [ ] شفت HELLO وFEATURES وFLOW_MOD وPACKET_IN وPACKET_OUT في Wireshark.
- [ ] حفظت الـ Capture بصيغة `.pcapng`.
- [ ] قفلت Mininet بـ `exit` والـ Controller بـ `Ctrl+C`.

### ملفات مهمة للاحتفاظ بيها

```text
~/sdn-lab/
├── .venv/                           # بيئة Python (موجودة عندك)
├── first_controller.py              # Controller اللي كتبناه
├── c1_openflow_capture.pcapng       # احفظه بنفسك إن لم يكن موجودًا
└── docs/                            # مكان مقترح لملفات الـ Markdown
    ├── SDN_C1_Practice_Guide_AR.md
    └── SDN_C1_Report_Notes_EN.md
```

مجلد `docs` وأسماء الصور والـ Capture **اقتراحات للتنظيم**، مش معنى ظهورها هنا إن الملفات دي اتعملت على Ubuntu تلقائيًا.

---

## ملحق A — الكود الكامل لـ `first_controller.py`

> استخدم الكود التالي **لو محتاج تعيد إنشاء الملف**. ده Learning Switch بسيط صالح لتجربة Switch واحد، لكنه **مش** Controller آمن للتوبولوجي الكبيرة اللي فيها Loops.

```python
from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib.packet import packet, ethernet


class LearningSwitch(app_manager.OSKenApp):
    # اجبر البرنامج على التعامل ببروتوكول OpenFlow 1.3
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # لكل Switch: اربط عنوان الـ MAC بالمنفذ اللي اتعلمناه منه
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_connected(self, ev):
        dp = ev.msg.datapath             # الاتصال/الـ Switch
        p = dp.ofproto_parser            # منشئ رسائل OpenFlow
        o = dp.ofproto                   # ثوابت OpenFlow 1.3

        match = p.OFPMatch()              # Match فاضي = Table-miss لكل ما لا يطابق قاعدة أعلى
        actions = [p.OFPActionOutput(o.OFPP_CONTROLLER, o.OFPCML_NO_BUFFER)]
        inst = [p.OFPInstructionActions(o.OFPIT_APPLY_ACTIONS, actions)]

        dp.send_msg(p.OFPFlowMod(
            datapath=dp, priority=0,
            match=match, instructions=inst
        ))
        self.logger.info("Switch %s connected", dp.id)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in(self, ev):
        msg = ev.msg
        dp = msg.datapath
        p = dp.ofproto_parser
        o = dp.ofproto

        in_port = msg.match["in_port"]
        eth = packet.Packet(msg.data).get_protocol(ethernet.ethernet)
        if eth is None:
            return

        src = eth.src
        dst = eth.dst
        self.mac_to_port.setdefault(dp.id, {})[src] = in_port

        # الوجهة لو متعلّمة: المنفذ الصحيح، وإلا Flood
        out_port = self.mac_to_port[dp.id].get(dst, o.OFPP_FLOOD)
        actions = [p.OFPActionOutput(out_port)]

        # لو الوجهة معروفة، ثبّت قاعدة علشان الـ Switch يشتغل مباشرة بعد كده
        if out_port != o.OFPP_FLOOD:
            match = p.OFPMatch(in_port=in_port, eth_dst=dst)
            inst = [p.OFPInstructionActions(o.OFPIT_APPLY_ACTIONS, actions)]
            dp.send_msg(p.OFPFlowMod(
                datapath=dp, priority=1,
                match=match, instructions=inst
            ))

        # تعامل مع الـ Frame الحالية حتى قبل أي Packets تالية
        dp.send_msg(p.OFPPacketOut(
            datapath=dp,
            buffer_id=o.OFP_NO_BUFFER,
            in_port=in_port,
            actions=actions,
            data=msg.data
        ))
```

### نفهم أقسام الكود سريعًا

| القسم | دوره |
|---|---|
| `OSKenApp` | فئة التطبيق اللي OS-Ken بيديرها. |
| `OFP_VERSIONS` | الإصدار اللي التطبيق هيتكلم بيه. |
| `mac_to_port` | جدول تعلم عنوان MAC مع رقم المنفذ **لكل Switch**. |
| `EventOFPSwitchFeatures` | حدث وصول معلومات الـ Switch؛ عنده بنثبت قاعدة Table-miss بأولوية صفر. |
| `EventOFPPacketIn` | حدث وصول Packet للـ Controller؛ نتعلم مصدرها ونقرر الاتجاه. |
| `OFPMatch(in_port=..., eth_dst=...)` | الشروط: منفذ الدخول + Destination MAC. |
| `OFPFlowMod` | أمر إضافة Flow Rule للسويتش. |
| `OFPPacketOut` | أمر للتعامل مع Frame واحدة. |
| `OFPP_FLOOD` | توجيهها للمنافذ المؤهلة عند عدم معرفة الوجهة. |

---

## بعد ما تتقن التجربة دي

**C1** هيفضل محتاج ترتيب الأدلة والكود بما يوافق تسليم المادة؛ أما المرحلة اللي هنشتغل عليها بعد التدريب فهي **C2 – Topology Discovery**: إنشاء شبكة 6 Switches و6 Hosts، واستخدام LLDP وNetworkX لاكتشاف الرسم البياني للوصولات تلقائيًا. لازم وقتها نستبدل سلوك الـ Flooding الساذج بأسلوب مناسب لشبكة فيها Loops.
