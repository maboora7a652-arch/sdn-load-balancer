"""Update the existing report and export current video numbers from real results.

Authoring dependencies: python-docx, ReportLab, pypdfium2, Pillow.
The Ubuntu network runtime does not need these packages.
"""
import copy
import io
import json
import math
import statistics as st
import subprocess
import tempfile
from pathlib import Path

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import pypdfium2 as pdfium

import results_figures as figures


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "output/report"
DATA = ROOT / "ubuntu/experiments/results"
TEAM = [
    ("عبدالحميد أحمد", "921230064"),
    ("عبدالرحمن أحمد محمد محمد", "921230066"),
    ("عبدالرحمن أحمد فؤاد", "921230065"),
    ("عبدالرحمن عمرو عبدالحليم", "921230069"),
    ("صهيب وائل محمد", "921230061"),
    ("عبدالرحمن صلاح الدين يحي", "921230068"),
]


def update_cover(doc):
    """Build an editable cover; abstract and contents each start on their own page."""
    abstract_index = next(i for i, p in enumerate(doc.paragraphs) if p.text == 'Abstract')
    abstract = doc.paragraphs[abstract_index + 1].text
    contents = next(p for p in doc.paragraphs if p.text == 'Contents')._p
    body = doc._element.body
    while body[0] != contents:
        body.remove(body[0])

    navy, muted = '173B61', '566575'

    def paragraph(text='', size=12, bold=False, color='000000', before=0, after=0):
        p = doc.add_paragraph()
        contents.addprevious(p._p)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(after)
        p.paragraph_format.line_spacing = 1.1
        run = p.add_run(text)
        run.font.name = 'Arial'
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = RGBColor.from_string(color)
        return p

    paragraph('Helwan National University', 21, True, navy, after=4)
    paragraph('Faculty of Engineering', 12, after=3)
    paragraph('Intelligent Systems Engineering', 11, color=muted, after=10)
    logo = paragraph(after=9)
    logo.add_run().add_picture(str(ROOT / 'media/hnu-logo.png'), width=Inches(1.25))
    paragraph('Computer Networks', 15, True, navy, after=3)
    paragraph('ECE2606  /  Course Project  /  Track 1', 10, color=muted, after=12)
    title = paragraph('Intelligent Load Balancer\nwith Fault Tolerance', 23, True, navy, before=8, after=12)
    borders = OxmlElement('w:pBdr')
    for side in ('top', 'bottom'):
        border = OxmlElement('w:' + side)
        for key, value in (('val', 'single'), ('sz', '6'), ('space', '10'), ('color', 'B7C9DB')):
            border.set(qn('w:' + key), value)
        borders.append(border)
    title._p.get_or_add_pPr().append(borders)
    paragraph('Submitted by', 10, color=muted, before=4, after=6)

    table = doc.add_table(rows=1, cols=2)
    contents.addprevious(table._tbl)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Inches(1.7)
    table.columns[1].width = Inches(3.6)
    table.rows[0].cells[0].text = 'Student ID'
    table.rows[0].cells[1].text = 'الاسم'
    for name, student_id in TEAM:
        row = table.add_row()
        row.cells[0].text = student_id
        row.cells[1].text = name
    for i, row in enumerate(table.rows):
        for j, cell in enumerate(row.cells):
            cell.width = Inches(1.7 if j == 0 else 3.6)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pr = cell._tc.get_or_add_tcPr()
            margins = OxmlElement('w:tcMar')
            for side, value in (('top', '65'), ('bottom', '65'), ('left', '120'), ('right', '120')):
                edge = OxmlElement('w:' + side)
                edge.set(qn('w:w'), value)
                edge.set(qn('w:type'), 'dxa')
                margins.append(edge)
            pr.append(margins)
            edges = OxmlElement('w:tcBorders')
            for side in ('top', 'left', 'bottom', 'right'):
                edge = OxmlElement('w:' + side)
                for key, value in (('val', 'single'), ('sz', '4'), ('color', 'D9D9D9')):
                    edge.set(qn('w:' + key), value)
                edges.append(edge)
            pr.append(edges)
            if i == 0:
                shade = OxmlElement('w:shd')
                shade.set(qn('w:fill'), 'EDF2F7')
                pr.append(shade)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if j == 0 else WD_ALIGN_PARAGRAPH.RIGHT
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.1
            if j == 1:
                bidi = OxmlElement('w:bidi')
                bidi.set(qn('w:val'), '1')
                p._p.get_or_add_pPr().append(bidi)
            for run in p.runs:
                run.font.name = 'Arial'
                run.font.size = Pt(12 if j == 1 and i > 0 else 11)
                run.font.bold = i == 0
                run.font.color.rgb = RGBColor(0, 0, 0)
                run.font.rtl = j == 1
                run._r.get_or_add_rPr().rFonts.set(qn('w:cs'), 'Arial')
                complex_size = OxmlElement('w:szCs')
                complex_size.set(qn('w:val'), '24' if j == 1 and i > 0 else '22')
                run._r.rPr.append(complex_size)
                language = OxmlElement('w:lang')
                language.set(qn('w:val'), 'ar-EG' if j == 1 else 'en-US')
                language.set(qn('w:bidi'), 'ar-EG')
                run._r.rPr.append(language)
    paragraph('Submitted to', 10, color=muted, before=12, after=3)
    paragraph('Prof. Ahmed M. Abdelhaleem', 13, True, navy, after=3)
    paragraph('Course Coordinator', 9, color=muted, after=11)
    paragraph('November 2026  /  Fall 2026–2027', 10, color=muted)
    paragraph().add_run().add_break(WD_BREAK.PAGE)
    p = paragraph('Abstract', 17, True, before=0, after=12)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p = paragraph(abstract, 12)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.runs[0].font.name = 'Times New Roman'
    paragraph().add_run().add_break(WD_BREAK.PAGE)
    toc = next(t for t in doc.tables if t.cell(0, 0).text == 'Section')
    for row, page in zip(toc.rows[1:], (4, 6, 16, 20, 24, 30, 31, 32, 33)):
        row.cells[1].text = str(page)


def compact_layout(doc):
    """Remove optional breaks while retaining the assignment's chapter minima."""
    paragraphs = list(doc.paragraphs)
    join_before = ('Contents', '5.4  Congestion detection', '5.5  Receiver measurements',
                   '5.6  Recovery after', 'Appendix B')
    for i, p in enumerate(paragraphs):
        breaks = p._p.xpath('.//w:br[@w:type="page"]')
        if not breaks:
            continue
        following = next((x.text for x in paragraphs[i + 1:] if x.text.strip()), '')
        if following.startswith(join_before):
            for br in breaks:
                br.getparent().remove(br)
            if not p.text.strip() and not p._p.xpath('.//w:drawing'):
                p._p.getparent().remove(p._p)
    in_body = False
    for p in doc.paragraphs:
        if p.text == 'Abstract':
            in_body = True
        if not in_body:
            continue
        if p._p.xpath('.//w:drawing'):
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.keep_together = True
        elif p.text.strip() and p.style.name == 'Normal':
            p.paragraph_format.space_after = Pt(3)
    # Give narrative columns the space they need instead of wasting half a table on dates.
    width = doc.sections[0].page_width - doc.sections[0].left_margin - doc.sections[0].right_margin
    for table in doc.tables:
        header = table.cell(0, 0).text
        ratios = {'Record': (0.23, 0.59, 0.18), 'Date (2026)': (0.20, 0.80)}.get(header)
        if ratios:
            table.autofit = False
            for i, ratio in enumerate(ratios):
                table.columns[i].width = int(width * ratio)
                for row in table.rows:
                    row.cells[i].width = int(width * ratio)
    toc = next(t for t in doc.tables if t.cell(0, 0).text == 'Section')
    for row, page in zip(toc.rows[1:], (3, 5, 15, 19, 23, 28, 29, 30, 30)):
        row.cells[1].text = str(page)


def metric(values):
    return {"n": len(values), "mean": st.mean(values),
            "sample_sd": st.stdev(values) if len(values) > 1 else None,
            "values": values}


def formatted(values, places=2):
    result = metric(values)
    if result["sample_sd"] is None:
        return f"{result['mean']:.{places}f} (n=1)"
    return f"{result['mean']:.{places}f} ± {result['sample_sd']:.{places}f}"


def collect():
    a = figures.read(figures.ACCURACY)
    if a.get("error") or a.get("resumed_from") or len(a["trials"]) != 5:
        raise ValueError("Use a complete homogeneous accuracy batch")
    errors = []
    from bandwidth_accuracy import sender_mbps
    for trial in a["trials"]:
        if len(trial["samples"]) != 3:
            raise ValueError("Accuracy trial is missing samples")
        measured = sender_mbps(a["tool"], trial["sender_output"])
        monitored = st.mean(p["tx_mbps"] for p in trial["samples"])
        error = 100 * abs(monitored - measured) / measured
        if not math.isclose(error, trial["error_percent"], abs_tol=1e-8):
            raise ValueError("Saved accuracy does not reproduce")
        errors.append(error)
    result = {"updated": "2026-11-26", "units": {
        "throughput": "decimal Mbps", "time": "milliseconds or seconds as named",
        "spread": "sample standard deviation", "flow": "directed IPv4 MAC pair"},
        "sources": {k: v for k, v in vars(figures).items()
                    if k in ("ACCURACY", "GRID", "TEN", "RECOVERY", "DETECTION", "THRESHOLD", "PHASES")},
        "accuracy_error_percent": metric(errors),
        "accuracy_sender_mbps": metric([t["sender_mbps"] for t in a["trials"]]),
        "accuracy_controller_tx_mbps": metric([t["controller_tx_mbps"] for t in a["trials"]]),
        "grid": {}, "ten_flows": {}, "detection": {}, "phases": {}}
    for mode in ("shortest", "balanced"):
        rows = figures.by_mode(figures.records(figures.GRID), mode)
        result["grid"][mode] = {
            host: {key: metric([r["receivers"][host][key] for r in rows])
                   for key in ("mbps", "loss_percent", "jitter_ms")}
            for host in ("H6", "H5")}
    for mode in ("shortest", "ecmp", "balanced"):
        rows = figures.by_mode(figures.records(figures.TEN), mode)
        packets = [receiver for row in rows
                   for receiver in figures.read(figures.TEN + "/" + row["file"])["receivers"].values()]
        result["ten_flows"][mode] = {
            "peak_tx_percent": metric([r["peak_tx_percent"] for r in rows]),
            "received_mbps": metric([r["received_mbps"] for r in rows]),
            "lost": sum(r["lost"] for r in packets), "total": sum(r["total"] for r in packets)}
    for label, batch, mode in (("T2_theta60", figures.THRESHOLD, "theta60"),
                               ("T2_theta70", figures.DETECTION, "T2"),
                               ("T2_theta80", figures.THRESHOLD, "theta80"),
                               ("T5_theta70", figures.DETECTION, "T5")):
        rows = figures.by_mode(figures.records(batch), mode)
        result["detection"][label] = {
            "detected": sum(r["status"] == "detected" for r in rows), "runs": len(rows),
            "seconds": metric([r["first_detection_seconds"] for r in rows if r["status"] == "detected"])}
    comparisons = []
    for row in figures.records(figures.PHASES):
        comparisons.extend(item for item in figures.read(figures.PHASES + "/" + row["file"])["phase_comparisons"]
                           if set(item["phases"]) == {"before", "after"})
    result["paired_comparisons"] = len(comparisons)
    for source, target in (("h1", "h6"), ("h3", "h5"), ("h4", "h5"), ("h3", "h6")):
        rows = [r for r in comparisons if (r["src"], r["dst"]) == (source, target)]
        result["phases"][source + "_" + target] = {
            phase: {key: metric([r["phases"][phase][key] for r in rows])
                    for key in ("mbps", "loss_percent", "mean_ping_rtt_ms", "mean_interval_jitter_ms")}
            for phase in ("before", "after")}
    recovery = figures.records(figures.RECOVERY)
    result["recovery"] = {
        "first_post_cut_reply_ms": metric([r["first_post_cut_reply_ms"] for r in recovery]),
        "lost_per_run": metric([r["lost"] for r in recovery]), "lost_total": sum(r["lost"] for r in recovery),
        "transmitted_total": 1300}
    result["logic_tests"] = {"passed": 16, "platform": "Ubuntu", "kind": "offline method and fixture regressions"}
    result["connectivity"] = {"grid": {"received": 30, "sent": 30},
                              "fattree4": {"received": 240, "sent": 240},
                              "source": "Fouad's recorded terminal output"}
    result["limitations"] = [
        "The repeated performance comparisons are November 25 batches using 64k HTB burst/cburst, before the November 26 LLDP wait change.",
        "The latest homogeneous calibration is a separate November 26 batch. Do not pool it with resumed or earlier runs.",
        "Controller logs still contain link-deletion/relearning episodes. A completed calibration is not a general stability guarantee.",
        "The 30-second hold-down is implemented and unit-tested; it has not been isolated in a successful live experiment.",
        "Port TX includes framing and background traffic; receiver throughput, ping RTT and UDP jitter are distinct metrics."]
    return result


def set_table(table, values):
    if len(table.rows) != len(values):
        raise ValueError("Unexpected report table shape")
    for i, row in enumerate(values):
        for cell, value in zip(table.rows[i].cells, row):
            cell.text = str(value)
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(10)
                    run.bold = i == 0


def update_chart_images(doc, plots):
    paragraphs = doc.paragraphs
    for i, paragraph in enumerate(paragraphs):
        if not paragraph.text.startswith("Figure 5."):
            continue
        number = int(paragraph.text.split(".")[1])
        for previous in reversed(paragraphs[max(0, i-2):i]):
            blips = previous._p.xpath(".//a:blip")
            if blips:
                rid = blips[0].get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                image_part = doc.part.related_parts[rid]
                if image_part.content_type != "image/png":
                    raise ValueError("Expected an existing PNG chart")
                image_part._blob = plots[number].read_bytes()
                break


def replace_chapter(combined, chapter, start, end):
    """Keep the combined document in sync with the canonical chapter and its images."""
    body = combined._element.body
    nodes = list(body)

    def text(node):
        return ''.join(node.xpath('.//w:t/text()'))

    first = next(i for i, node in enumerate(nodes) if text(node).startswith(start))
    last = next(i for i in range(first + 1, len(nodes)) if text(nodes[i]).startswith(end))
    inserted = []
    for original in chapter._element.body:
        if original.tag.endswith('}sectPr'):
            continue
        element = copy.deepcopy(original)
        for blip in element.xpath('.//a:blip'):
            attribute = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed'
            image = chapter.part.related_parts[blip.get(attribute)]
            rid, _ = combined.part.get_or_add_image(io.BytesIO(image.blob))
            blip.set(attribute, rid)
        inserted.append(element)
    for node in nodes[first:last]:
        body.remove(node)
    for i, node in enumerate(inserted):
        body.insert(first + i, node)
    separator = combined.add_page_break()._p
    body.insert(first + len(inserted), separator)


def update_reports(data, plots):
    replacements = {}
    accuracy = data["accuracy_error_percent"]
    grid = data["grid"]
    phases = data["phases"]
    recovery = data["recovery"]
    paragraphs = {
        "chapter-3-system-design.docx": {
            9: "Each inter-switch link has 100 Mbps capacity and 2 ms configured delay. LabTCLink uses HTB burst and cburst values of 64k. The seven grid links give H1 three equal-hop routes to H6. Traffic between H3 and H5 competes with H1 traffic on S2 to S3.",
            25: "In the November 26 grid rehearsal, H1 to H6 initially used the upper route at priority 20. Congestion was visible in the 20-second sample. The 30-second sample showed S1 to S4 to S5 to S6 at priority 21. These observations bound the change at the five-second sampling resolution; they are not an exact reroute latency.",
            29: "A failed link triggers a topology event. The controller removes the edge and rebuilds routes using the surviving links. In the November 26 S5-S6 rehearsal, H1 traffic moved from the lower route to the upper route during the cut. The host received 299 of 300 probes. This restores reachability independently of the congestion threshold."},
        "chapter-4-implementation.docx": {
            4: "In vm-source/custom_topology.py, MyNetwork creates the six-switch grid in an explicit link order that fixes port numbers. FatTree4 builds four pods, eight edge and eight aggregation switches, and four core switches. LabTCLink and LabTCIntf apply 100 Mbps, 2 ms delay and 64k HTB burst/cburst to inter-switch links. SDN_TOPOLOGY selects the controller's discovery expectations.",
            6: "HostDiscoveryController receives OS-Ken events, registers datapaths, installs table-miss rules and records switch, link and host locations. A local compatibility wrapper bounds LLDP event waits by the send period when ports exist: the installed loop could otherwise wait indefinitely when all ports were due. The project also uses a monotonic discovery clock, a 10 ms maximum send guard on the fat-tree, and cooperative yields during bulk route rebuilding. The original 10-second link timeout and PortStatus handling remain in force.",
            33: "The browser refreshes approximately one second after the preceding request completes. Controller measurements have an independent default period of five seconds. Selecting H1 to H16 highlights its installed path. The original student captures below show a change from 32 to 31 links and from core S17 to S18."},
        "chapter-5-experiments-and-results.docx": {
            2: "We evaluated an OpenFlow 1.3 load balancer using Mininet, Open vSwitch and OS-Ken. Under 115 Mbps shared demand, balanced routing improved receiver throughput over shortest path. With ten flows, ECMP gave the lowest mean sampled peak utilization. The separate 90 Mbps before/after experiment showed that a route change does not improve every receiver metric.",
            3: "The grid contains six switches, seven inter-switch links and six hosts; the k = 4 fat-tree contains 20 switches, 16 hosts and 32 inter-switch links. Links use 100 Mbps, 2 ms delay and 64k HTB burst/cburst. The November 25 repeated comparisons precede the November 26 bounded LLDP-wait change. The latest five-run calibration is kept separate. A flow is one directed IPv4 MAC pair.",
            7: f"All five November 26 iperf3 trials completed automatically with three steady-traffic samples each and no final-route warnings. Mean error was {accuracy['mean']:.3f}% (sample SD {accuracy['sample_sd']:.3f} percentage points), below the 10% limit in every run. Earlier stopped and resumed calibrations remain available separately. The successful windows do not establish general discovery stability; the supplied controller logs still contain topology-churn episodes.",
            8: "Data in experiments/results/ · " + figures.ACCURACY,
            14: "H6 mean received rate increased from 68.90 to 79.60 Mbps and mean loss fell from 18.74% to 6.22%. H5 increased from 19.30 to 27.42 Mbps, with loss falling from 35.49% to 8.61%. These are whole-run measurements, including the time spent waiting for the trigger. The five matched runs support a benefit for this offered workload, not a zero-loss guarantee.",
            15: "All five balanced runs ended on S1-S4-S5-S6 at priority 21, while all five shortest runs retained S1-S2-S3-S6 at priority 20. Historical attempts and earlier shaping settings are retained separately; their values are not pooled with this batch.",
            16: "Data in experiments/results/ · " + figures.GRID,
            23: "Mean sampled peak utilization was 47.96% for ECMP, 56.20% for shortest path and 56.50% for balanced routing. Total received rate was 144 Mbps at iperf precision under all three policies. Shortest and ECMP lost no datagrams in these runs; balanced lost 18 of 3,673,617. The result depends on the traffic matrix and does not show a universal advantage for adaptive routing.",
            24: "Data in experiments/results/ · " + figures.TEN,
            30: "The timing workload used four directed pairs sharing S2 to S3, with 90 Mbps total offered demand. All five runs declared congestion at each tested period. At the default 70% threshold, the mean first declaration was 6.952 s with T = 2 s and 18.932 s with T = 5 s, a difference of 11.980 s. These times include traffic ramp-up and EWMA smoothing.",
            31: "At T = 2 s, all five trials declared congestion at both 60% and 80%. The means were 6.815 s and 8.927 s, respectively. The 70% reference comes from the separate matched-workload polling batch. The default remains 70%; thresholds were not lowered to force the main demo to pass.",
            32: "Data in experiments/results/ · " + figures.DETECTION + " · " + figures.THRESHOLD,
            35: "Five four-flow runs used T = 2 s and a 70% threshold. For each pair that moved, we compared five consecutive one-second receiver intervals on each side of its first confirmed change, with a guard of at least one second. Fourteen paired comparisons were available: H1-H6 and H3-H5 each n = 5, H4-H5 n = 3, and H3-H6 n = 1. Sender launch approximates receiver stream alignment.",
            38: "H1 to H6 throughput was already close to the requested 28 Mbps: the means were 27.956 before and 27.996 Mbps after the move. Both windows had zero observed loss. Mean RTT fell from 18.82 to 15.44 ms, while mean interval jitter rose from 0.303 to 0.381 ms. This workload does not reproduce the large throughput gains of the older batch.",
            39: "For H3 to H5, mean throughput stayed at 27.996 Mbps and loss was zero in both windows. Mean RTT increased from 7.92 to 10.40 ms, and jitter from 0.181 to 0.323 ms. Reported improvements must therefore name the pair and metric. RTT is round-trip delay; one-way delay was not measured. A single H3-H6 pair cannot support a sample standard deviation.",
            40: "Data in experiments/results/ · " + figures.PHASES,
            46: "We measured from the cut request to the first reply whose probe was estimated to have been sent after completion of the link-down command. The estimate uses the reply timestamp and RTT. Mean first qualifying reply was 73.139 ms (sample SD 21.631 ms). Seven of 1,300 probes were missing over the complete five trials. This observable differs from the largest inter-reply gap and from switch-by-switch convergence.",
            47: "The measurements support workload-specific benefits, correct ingress accounting and observed alternate-path recovery. Port TX, receiver delivery and host timing are different quantities. The latest complete calibration followed a bounded LLDP-wait correction, but topology churn remains visible in supplied logs and must not be called universally resolved. High-load loss and isolated live validation of the 30-second hold-down remain limitations.",
            48: "Data in experiments/results/ · " + figures.RECOVERY},
        "chapter-6-conclusion.docx": {
            3: "Benefits depended on the workload. With 85 and 30 Mbps competing on the grid, balanced routing raised H6 receiver throughput from 68.90 to 79.60 Mbps and H5 from 19.30 to 27.42 Mbps. With ten flows, ECMP had the lowest mean sampled peak utilization, 47.96%, versus 56.50% for balanced routing. In the separate 90 Mbps before/after batch, throughput was already near demand and some RTT and jitter measurements increased after a move.",
            4: f"The November 26 five-run iperf3 calibration gave mean absolute relative error {accuracy['mean']:.3f}% (sample SD {accuracy['sample_sd']:.3f} percentage points), with every run below 10%. Five light-load failures gave a mean first qualifying reply of 73.139 ms and seven missing probes among 1,300. These host observations do not timestamp completion on every switch.",
            6: "The source review found an indefinitely blocking LLDP wait when every port was due. A local wrapper bounds that wait without changing the 10-second failure timeout. Sixteen logic tests passed on Ubuntu and a complete calibration followed, but supplied logs still show discovery churn. Its full cause and the remaining high-load losses require further investigation; the results do not prove universal stability."}}

    a = figures.read(figures.ACCURACY)["trials"]
    tables = [[['Quantity', 'Mean ± sample SD, n = 5'],
               ['Sender payload (Mbps)', formatted([t['sender_mbps'] for t in a], 3)],
               ['Port TX (Mbps)', formatted([t['controller_tx_mbps'] for t in a], 3)],
               ['Absolute relative error (%)', formatted([t['error_percent'] for t in a], 3)]]]
    rows = [['Receiver / policy', 'Rate (Mbps)', 'Loss (%)', 'Jitter (ms)']]
    for host in ('H6', 'H5'):
        for mode in ('shortest', 'balanced'):
            rows.append([host + ' / ' + mode] + [formatted(grid[mode][host][k]['values'])
                        for k in ('mbps', 'loss_percent', 'jitter_ms')])
    tables.append(rows)
    rows = [['Routing policy', 'Peak TX (%)', 'Received (Mbps)', 'Lost / total']]
    for mode in ('shortest', 'ecmp', 'balanced'):
        row = data['ten_flows'][mode]
        rows.append([mode, formatted(row['peak_tx_percent']['values']),
                     formatted(row['received_mbps']['values']), f"{row['lost']:,} / {row['total']:,}"])
    tables.append(rows)
    rows = [['Poll period', 'Threshold', 'Declared in 60 s', 'Time (s)']]
    for key, period, threshold in [('T2_theta60', '2 s', '60%'), ('T2_theta70', '2 s', '70%'),
                                    ('T2_theta80', '2 s', '80%'), ('T5_theta70', '5 s', '70%')]:
        row = data['detection'][key]
        rows.append([period, threshold, f"{row['detected']} / {row['runs']}", formatted(row['seconds']['values'], 3)])
    tables.append(rows)
    rows = [['H1 to H6, n = 5', 'Before first move', 'After first move']]
    for label, key, places in [('Throughput (Mbps)', 'mbps', 3), ('UDP loss (%)', 'loss_percent', 2),
                               ('Ping RTT (ms)', 'mean_ping_rtt_ms', 3), ('UDP jitter (ms)', 'mean_interval_jitter_ms', 3)]:
        rows.append([label] + [formatted(phases['h1_h6'][p][key]['values'], places) for p in ('before', 'after')])
    tables.append(rows)
    rows = [['Metric', 'Mean ± sample SD', 'Observed range']]
    for label, key in [('First qualifying reply (ms)', 'first_post_cut_reply_ms'), ('Lost probes per run', 'lost_per_run')]:
        values = recovery[key]['values']
        rows.append([label, formatted(values, 3), f'{min(values):.3f} to {max(values):.3f}'])
    tables.append(rows)
    for name, updates in paragraphs.items():
        doc = Document(REPORT / name)
        for index, text in updates.items():
            previous = doc.paragraphs[index].text
            replacements[previous] = text
            p = doc.paragraphs[index]
            if not p.runs:
                p.add_run(text)
            else:
                p.runs[0].text = text
                for run in p.runs[1:]:
                    run.text = ''
        if name.startswith('chapter-5'):
            for table, values in zip(doc.tables, tables):
                set_table(table, values)
            update_chart_images(doc, plots)
            for p in doc.paragraphs:
                previous = p._p.getprevious()
                if previous is not None and previous.tag.endswith('}tbl'):
                    p.paragraph_format.space_before = Pt(8)
        doc.save(REPORT / name)

    combined = Document(REPORT / 'sdn-track-1-report.docx')
    for p in combined.paragraphs:
        if p.text in replacements:
            text = replacements[p.text]
            p.runs[0].text = text
            for run in p.runs[1:]:
                run.text = ''
    abstract_index = next(i for i, p in enumerate(combined.paragraphs) if p.text == 'Abstract')
    combined.paragraphs[abstract_index + 1].text = (
        f'This project implements an OpenFlow 1.3 controller that monitors directional links, detects sustained large flows and changes paths under congestion or failure. '
        f'A six-switch grid supports repeated comparisons and a 20-switch, 16-host fat-tree tests larger-scale connectivity. '
        f'Five complete iperf3 trials gave mean monitoring error {accuracy["mean"]:.3f}%. Balanced routing improved receiver throughput in the 115 Mbps competing workload, while ECMP had the lowest mean sampled peak with ten flows. '
        'The results distinguish receiver delivery from switch counters and retain limitations in discovery stability and isolated hold-down validation.')
    for number, end in ((3, 'Chapter 4'), (4, 'Chapter 5'), (5, 'Chapter 6'), (6, 'References')):
        name = next(name for name in paragraphs if name.startswith(f'chapter-{number}-'))
        replace_chapter(combined, Document(REPORT / name), f'Chapter {number}', end)
    for i, p in enumerate(combined.paragraphs):
        text = p.text
        if text.startswith('The project directory is mounted at /media'):
            p.text = 'Use the independent Ubuntu project at ~/sdn-project with the existing OS-Ken environment in ~/sdn-lab/.venv. Start the controller first in a free lab session. The detailed Arabic run guide is ubuntu/README.md.'
        elif text.startswith('share=/media/sf_sdn_transfer'):
            p.text = 'bash ~/sdn-project/run.sh controller grid'
        elif text.startswith('sudo mn --custom /media/sf_sdn_transfer'):
            p.text = 'bash ~/sdn-project/run.sh network grid'
        elif text.startswith('sudo -u "$(id -un)" -g vboxsf'):
            p.text = 'bash ~/sdn-project/run.sh dashboard'
        elif text.startswith('For the fat-tree, use fattree4 for both'):
            p.text = 'For the fat-tree, use fattree instead of grid in the controller and network launchers. Expect 20 switches, 32 inter-switch links and 240/240 directed ping replies in a successful test. The five-run iperf3 command and complete demo sequence are in ubuntu/README.md. Results stay under experiments/results/. Stop Mininet with exit, then stop the controller and dashboard with Ctrl+C.'
        elif text.startswith('The repository count is a snapshot before assembly'):
            p.text = 'The six-member team and student IDs are listed on the cover as supplied by the team. The local Git count is a dated snapshot of version history. A shared commit identity cannot establish the division of work among students. Per-member contribution allocation remains to be supplied before submission.'
        elif text.startswith('The six-member team and student IDs'):
            p.text = 'The six-member team and student IDs are listed on the cover as supplied by the team. The local Git count is a dated snapshot of version history. A shared commit identity cannot establish the division of work among students. Per-member contribution allocation remains to be supplied before submission.'
    count = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], cwd=ROOT,
                           capture_output=True, text=True, check=False).stdout.strip()
    contributions = next(t for t in combined.tables if t.cell(0, 0).text == 'Record')
    progress = next(t for t in combined.tables if t.cell(0, 0).text == 'Date (2026)')
    contributions.cell(2, 1).text = 'Controller, topology, dashboard, experiments and updated report sources. Snapshot on 26 November 2026; not individual attribution.'
    contributions.cell(2, 2).text = (count + ' local commits at this snapshot') if count else 'See Git history'
    progress.cell(2, 0).text = '18-19 November'
    progress.cell(2, 1).text = 'Fat-tree, dashboard, original C1 capture and earlier evaluation batches. Raw outputs remain distinct from later repetitions.'
    progress.cell(3, 0).text = '25-26 November'
    progress.cell(3, 1).text = '64k shaping comparisons, current recovery/detection/threshold/window measurements, LLDP source review, 16 logic regressions and a complete new iperf3 calibration.'
    update_cover(combined)
    compact_layout(combined)
    combined.save(REPORT / 'sdn-track-1-report.docx')


def main():
    data = collect()
    (ROOT / 'media').mkdir(exist_ok=True)
    (ROOT / 'media/video-data.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    figures.main()
    with tempfile.TemporaryDirectory(prefix='sdn-report-plots-') as temporary:
        folder = Path(temporary)
        pdf = pdfium.PdfDocument(str(figures.OUTPUT))
        plots = {}
        for number, page_index in {1: 0, 2: 1, 3: 2, 4: 4, 5: 5, 6: 3}.items():
            page = pdf[page_index]
            scale = 2
            image = page.render(scale=scale).to_pil()
            w, h = page.get_size()
            image = image.crop((30*scale, (h-475)*scale, (w-30)*scale, (h-250)*scale))
            path = folder / f'figure-5-{number}.png'
            image.save(path)
            plots[number] = path
            if number == 2:
                image.save(ROOT / 'media/baseline-throughput.png')
        update_reports(data, plots)
        pdf.close()
    print('Updated report sources and media/video-data.json')


if __name__ == '__main__':
    main()
