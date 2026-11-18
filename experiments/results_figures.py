"""Build the English figures and tables from the saved experiment JSON (ReportLab)."""
import json
import statistics as st
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen.canvas import Canvas


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "results"
OUTPUT = ROOT.parent / "output/pdf/sdn-experiment-results.pdf"
ACCURACY = "accuracy-20261118T162628Z.json"
GRID = "compare-grid-20261118T163914Z"
TEN = "ten-flows-20261118T170441Z"
RECOVERY = "recovery-20261118T173006Z"
DETECTION = "shared-detection-20261118T180711Z"
THRESHOLD = "threshold-20261118T182438Z"
PHASES = "route-phases-20261118T185932Z"
W, H = landscape(A4)


def read(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def records(name):
    return read(name + "/summary.json")


def by_mode(rows, mode):
    return sorted((r for r in rows if r["mode"] == mode), key=lambda r: r["pair"])


def stats(values, places=2):
    if not values:
        return "n/a"
    if len(values) == 1:
        return f"{values[0]:.{places}f} (n=1)"
    return f"{st.mean(values):.{places}f} ± {st.stdev(values):.{places}f}"


class Results:
    def __init__(self):
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        self.c = Canvas(str(OUTPUT), pagesize=(W, H), invariant=True)
        self.c.setTitle("SDN Track 1 | Experimental results")

    def text(self, x, y, value, size=11, bold=False, color="#18372f"):
        self.c.setFillColor(HexColor(color))
        self.c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        self.c.drawString(x, y, str(value))

    def page(self, title, subtitle, source):
        self.text(38, H-33, "SDN TRACK 1  /  EXPERIMENTAL RESULTS", 10, True)
        self.text(38, H-76, title, 28, True)
        self.text(38, H-99, subtitle)
        self.text(38, 20, "Source  experiments/results/  ·  " + source, 9)
        self.text(W-49, 20, self.c.getPageNumber(), 10, True)

    def chart(self, title, groups, maximum, unit):
        """Dot strip on a common zero-based axis. Vertical tick marks the group mean."""
        self.text(38, 462, title, 14, True)
        left, right, bottom, top = 190, W-65, 300, 432
        for i in range(6):
            x = left + (right-left)*i/5
            self.c.setStrokeColor(HexColor("#d8e3dc"))
            self.c.line(x, bottom, x, top)
            self.text(x-5, bottom-15, f"{maximum*i/5:g}", 9)
        for i, (name, values) in enumerate(groups):
            y = top-(i+0.5)*(top-bottom)/len(groups)
            self.text(38, y-4, name, 11, True)
            for index, value in enumerate(values):
                assert 0 <= value <= maximum
                x = left+(right-left)*value/maximum
                self.c.setFillColor(HexColor("#208366"))
                self.c.circle(x, y + (index-(len(values)-1)/2)*3.5, 3, fill=1, stroke=0)
            if values:
                x = left+(right-left)*st.mean(values)/maximum
                self.c.setStrokeColor(HexColor("#80350c"))
                self.c.setLineWidth(2)
                self.c.line(x, y-10, x, y+10)
                self.c.setLineWidth(1)
        self.text(38, 263, unit+"   ·   Dot = one observation; vertical mark = mean.", 10)

    def table(self, heads, rows, widths):
        y = 234
        for i, row in enumerate([heads, *rows]):
            x = 38
            if i == 0 or i % 2 == 0:
                self.c.setFillColor(HexColor("#e7efea" if i == 0 else "#f4f7f4"))
                self.c.rect(x, y-6, sum(widths), 20, fill=1, stroke=0)
            for cell, width in zip(row, widths):
                self.text(x+5, y, cell, 10, i == 0)
                x += width
            y -= 22

    def end(self, *notes):
        for i, line in enumerate(notes):
            self.text(38, 84-15*i, line, 10)
        self.c.showPage()


def main():
    doc = Results()
    a = read(ACCURACY)["trials"]
    doc.page("Bandwidth monitoring accuracy", "Fat-tree · H1 to H16 · 5 Mbps offered UDP · first inter-switch TX port", ACCURACY)
    doc.chart("Absolute relative error per run", [("iperf2 comparison",[r["error_percent"] for r in a])], 10, "Error (%)")
    doc.table(["Measured quantity","Runs","Mean ± sample SD"], [
        [label,len(a),stats([r[key] for r in a],3)] for label,key in
        [("Sender payload rate (Mbps)","sender_mbps"),("Controller port TX (Mbps)","controller_tx_mbps"),
         ("Absolute relative error (%)","error_percent")]], [330,100,335])
    doc.end("Sender payload and port TX were sampled during steady traffic. Port TX includes framing and background traffic.",
            "This preliminary comparison used iperf2. The coursework specifies a separate iperf3 calibration.")

    grid = records(GRID)
    modes = ["shortest","balanced"]
    doc.page("Receiver performance under shared load","Grid · H1 to H6 at 85 Mbps and H3 to H5 at 30 Mbps · 60 seconds per run",GRID)
    groups=[]; table=[]
    for host in ("H6","H5"):
        for mode in modes:
            v=[r["receivers"][host] for r in by_mode(grid,mode)]
            label=host+" / "+mode
            groups.append((label,[x["mbps"] for x in v]))
            table.append([label,len(v),*[stats([x[k] for x in v]) for k in ("mbps","loss_percent","jitter_ms")]])
    doc.chart("Received throughput",groups,60,"Receiver throughput (Mbps)")
    doc.table(["Receiver / policy","Runs","Mbps","Loss (%)","Jitter (ms)"],table,[180,75,170,170,170])
    doc.end("Table entries give mean ± sample SD across completed runs. H1 to H6 changed path in one of five balanced runs.",
            "One additional balanced attempt ended with an incomplete forwarding path; its raw file is retained separately.")

    ten=records(TEN)
    groups=[]; table=[]
    for mode in ["shortest","ecmp","balanced"]:
        v=by_mode(ten,mode); peaks=[r["peak_tx_percent"] for r in v]
        groups.append((mode.upper() if mode=="ecmp" else mode,peaks))
        packets=[r for t in v for r in read(TEN+"/"+t["file"])["receivers"].values()]
        table.append([mode,len(v),stats(peaks),stats([r["received_mbps"] for r in v]),
                      f"{sum(r['lost'] for r in packets):,} / {sum(r['total'] for r in packets):,}"])
    doc.page("Peak utilization with ten flows","Five matched rounds · ten directed host pairs per round · 144 Mbps total offered load",TEN)
    doc.chart("Highest sampled inter-switch TX utilization in each run",groups,100,"Peak utilization (%)")
    doc.table(["Policy","Runs","Peak TX (%)","Received (Mbps)","Lost / total datagrams"],table,[110,55,180,180,240])
    doc.end("Each peak spans 14 inter-switch directions and ten samples. Within a round all modes used the same traffic.",
            "A run peak includes samples taken before any reroute. Received rates use the precision reported by iperf.")

    rec=records(RECOVERY)
    v=[r["first_post_cut_reply_ms"] for r in rec]; lost=[r["lost"] for r in rec]
    doc.page("Connectivity after a link failure","Grid · H2 to H6 · S5-S6 temporarily down · ICMP probes every 50 ms",RECOVERY)
    doc.chart("Time from cut request to first qualifying reply",[("Recovery",v)],100,"Observed time (ms)")
    doc.table(["Measurement","Runs","Mean ± sample SD","Range"],[
        ["First qualifying reply (ms)",len(v),stats(v),f"{min(v):.2f} to {max(v):.2f}"],
        ["Lost probes per run",len(lost),stats(lost),f"{min(lost)} to {max(lost)}"]],[290,85,220,170])
    doc.end("Only replies from probes estimated to have been sent after completion of the link-down command qualify.",
            "All five trials used S4-S1-S2-S3-S6 during the cut. Six of 1,300 probes were lost across the full trials.")

    det=records(DETECTION); thresholds=records(THRESHOLD)
    groups=[]; table=[]
    for label,r in [("T=2 s / 60%",by_mode(thresholds,"theta60")),("T=2 s / 70%",by_mode(det,"T2")),
                    ("T=2 s / 80%",by_mode(thresholds,"theta80")),("T=5 s / 70%",by_mode(det,"T5"))]:
        times=[x["first_detection_seconds"] for x in r if x["status"]=="detected"]
        groups.append((label,times));table.append([label,f"{len(times)} / {len(r)}",stats(times)])
    doc.page("Congestion detection on S2 to S3","Four shared-link flows · 90 Mbps offered · two consecutive EWMA samples above threshold",DETECTION+"; "+THRESHOLD)
    doc.chart("Elapsed time from traffic launch to first declaration",groups,50,"Detection time (s), observed detections only")
    doc.table(["Poll interval / threshold","Detected within 60 s","Time (s), mean ± sample SD"],table,[245,210,310])
    doc.end("The 70% reference for the threshold comparison comes from the earlier matched-workload polling batch.",
            "At 80%, four trials had no declaration within 60 s. The single observed time cannot support a sample SD.",
            "On the original two-flow workload neither interval triggered at 70% (five runs each; detection-20261118T173741Z).")

    phase=[]
    for row in records(PHASES):
        data=read(PHASES+"/"+row["file"])
        phase.extend(x for x in data["phase_comparisons"] if set(x["phases"])=={"before","after"})
    for key,unit,title,axis in [("mbps","Mbps","Receiver throughput",35),("loss_percent","%","Receiver packet loss",30),
                              ("mean_ping_rtt_ms","ms","Ping round-trip time",200),
                              ("mean_interval_jitter_ms","ms","UDP receiver jitter",1)]:
        groups=[];table=[]
        for a,b in [("h1","h6"),("h3","h5"),("h3","h6"),("h4","h5")]:
            rows=[x["phases"] for x in phase if x["src"]==a and x["dst"]==b]
            values=[[r[t][key] for r in rows] for t in ("before","after")]
            label=a.upper()+" to "+b.upper()
            if a=="h1":
                groups=[("H1 to H6 / "+t,v) for t,v in zip(("before","after"),values)]
            table.append([label,len(rows),*[stats(v,3) for v in values]])
        doc.page(title+" around rerouting","Grid · five runs · receiver measurements around the first managed move for each directed pair",PHASES)
        doc.chart(title+" for the H1 to H6 flow",groups,axis,unit)
        doc.table(["Directed pair","Paired runs","Before, mean ± sample SD","After, mean ± sample SD"],table,[150,110,250,255])
        doc.end("Each side uses five consecutive one-second receiver intervals. A guard interval around the move excludes the transition.",
                "Only flows that moved and had two complete windows are included. Multiple flows can move during one run.",
                "Delay is measured as ping RTT. Jitter is the mean of interval-level UDP jitter readings.")
    doc.c.save()
    print(OUTPUT)


if __name__ == "__main__":
    main()
