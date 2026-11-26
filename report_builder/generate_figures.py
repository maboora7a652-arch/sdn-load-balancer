"""Generate all curated authentic screenshots, 300 DPI technical diagrams,
and publication-grade Nov 25-26 experiment figures into report_builder/assets/.

Run with Python 3.11 (matplotlib 3.11.2, numpy, Pillow):
    C:\\Users\\Fouad\\AppData\\Local\\Programs\\Python\\Python311\\python.exe report_builder/generate_figures.py
"""
from __future__ import annotations

import json
import shutil
import statistics as st
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon, Rectangle, Circle
import numpy as np
from PIL import Image

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(__file__).resolve().parent / "assets"
DATA = ROOT / "experiments" / "results"
AUDIT_IMGS = Path(
    r"C:\Users\Fouad\.gemini\antigravity\brain"
    r"\96b7c01b-bdf4-47a3-9f39-d8af196634d9\scratch\audit_imgs"
)

# ── Executive Engineering Palette ────────────────────────────────────────────
NAVY = "#173B61"
NAVY_DARK = "#0F2942"
NAVY_LIGHT = "#EBF2F9"
TEAL = "#0F6E6E"
TEAL_LIGHT = "#E6F4F3"
AMBER = "#C05621"
AMBER_LIGHT = "#FEF3EB"
CRIMSON = "#B91C1C"
CRIMSON_LIGHT = "#FEECEC"
EMERALD = "#15803D"
EMERALD_LIGHT = "#EAF7EE"
SLATE = "#475569"
SLATE_DARK = "#1E293B"
SLATE_MUTED = "#64748B"
BG_SOFT = "#F8FAFC"
GRID = "#E2E8F0"
BORDER = "#CBD5E1"
WHITE = "#FFFFFF"

# Global matplotlib styling
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
    "axes.edgecolor": BORDER,
    "axes.linewidth": 0.9,
    "axes.labelcolor": SLATE_DARK,
    "axes.titlecolor": NAVY_DARK,
    "xtick.color": SLATE,
    "ytick.color": SLATE,
    "text.color": SLATE_DARK,
    "figure.facecolor": WHITE,
    "axes.facecolor": WHITE,
    "savefig.facecolor": WHITE,
    "savefig.dpi": 300,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linestyle": "-",
    "grid.linewidth": 0.7,
    "axes.axisbelow": True,
})


def save_fig(fig: plt.Figure, filename: str, pad: float = 0.14) -> Path:
    out = ASSETS / filename
    fig.savefig(out, dpi=300, bbox_inches="tight", pad_inches=pad, facecolor=WHITE)
    plt.close(fig)
    return out


# ── Helpers for Clean Diagrams ───────────────────────────────────────────────
def draw_box(
    ax, x, y, w, h, title="", subtitle="", fc=WHITE, ec=NAVY, lw=1.4,
    title_color=NAVY_DARK, sub_color=SLATE, title_size=9.5, sub_size=7.8,
    radius=0.08, title_bold=True, align="center", zorder=3,
):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.02,rounding_size={radius}",
        facecolor=fc, edgecolor=ec, linewidth=lw, zorder=zorder,
    )
    ax.add_patch(patch)
    cx = x + w / 2.0 if align == "center" else x + 0.14
    ha = "center" if align == "center" else "left"
    if title and subtitle:
        ax.text(
            cx, y + h * 0.64, title, ha=ha, va="center",
            fontsize=title_size, fontweight="bold" if title_bold else "normal",
            color=title_color, zorder=zorder + 1,
        )
        ax.text(
            cx, y + h * 0.30, subtitle, ha=ha, va="center",
            fontsize=sub_size, color=sub_color, zorder=zorder + 1,
            linespacing=1.22,
        )
    elif title:
        ax.text(
            cx, y + h / 2.0, title, ha=ha, va="center",
            fontsize=title_size, fontweight="bold" if title_bold else "normal",
            color=title_color, zorder=zorder + 1, linespacing=1.22,
        )
    return patch


def draw_arrow(
    ax, x1, y1, x2, y2, color=NAVY, lw=1.5, style="-|>", rad=0.0,
    ls="-", ms=12, zorder=4,
):
    arr = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style,
        connectionstyle=f"arc3,rad={rad}",
        color=color, linewidth=lw, linestyle=ls,
        mutation_scale=ms, zorder=zorder,
    )
    ax.add_patch(arr)
    return arr


def draw_diamond(ax, cx, cy, w, h, text, fc=AMBER_LIGHT, ec=AMBER, lw=1.5, fontsize=8.0):
    pts = [(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)]
    poly = Polygon(pts, closed=True, facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3)
    ax.add_patch(poly)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fontsize,
            fontweight="bold", color=SLATE_DARK, zorder=4, linespacing=1.18)


def style_axes(ax, ygrid=True, xgrid=False):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BORDER)
    ax.spines["bottom"].set_color(BORDER)
    if ygrid:
        ax.yaxis.grid(True, color=GRID, linewidth=0.75)
    else:
        ax.yaxis.grid(False)
    if xgrid:
        ax.xaxis.grid(True, color=GRID, linewidth=0.75)
    else:
        ax.xaxis.grid(False)
    ax.tick_params(axis="both", labelsize=8.8, length=3.5, color=BORDER)


# ═════════════════════════════════════════════════════════════════════════════
# PART A — CURATED AUTHENTIC STUDENT SCREENSHOTS (8 FILES)
# ═════════════════════════════════════════════════════════════════════════════
def prepare_screenshots():
    print("[Part A] Preparing authentic student screenshots...")
    # 1. HNU Logo
    shutil.copy2(ROOT / "media" / "hnu-logo.png", ASSETS / "hnu_logo.png")

    # Helper: copy from audit_imgs/docx or fallback directly to DOCX archive
    def copy_docx_img(audit_name: str, docx_rel: str, media_member: str, dst_name: str):
        src = AUDIT_IMGS / "docx" / audit_name
        if src.exists():
            shutil.copy2(src, ASSETS / dst_name)
        else:
            with zipfile.ZipFile(ROOT / docx_rel, "r") as z:
                (ASSETS / dst_name).write_bytes(z.read(media_member))

    # 2. Wireshark OF1.3 Overview
    copy_docx_img(
        "4ca33291079d_image4.png",
        "output/report/chapter-2-sdn-background.docx",
        "word/media/image4.png",
        "shot_c1_wireshark_overview.png",
    )

    # 3. Wireshark OFPT_FLOW_MOD Deep Dissection (already crisp, no chrome)
    shutil.copy2(
        AUDIT_IMGS / "pdf" / "EN_C5_p11_obj118_951x773_94b6f5d3ce8c.png",
        ASSETS / "shot_c1_wireshark_flowmod.png",
    )

    # 4. Split Ubuntu Terminal Mininet Grid Startup + Live LLDP (crop VirtualBox title/menu/status chrome)
    im4 = Image.open(AUDIT_IMGS / "pdf" / "EN_C5_p11_obj116_1917x1026_4df7ae94c859.png")
    w4, h4 = im4.size
    # Top 62px = VirtualBox window title + menu bar; bottom 26px = VirtualBox status bar
    im4.crop((0, 62, w4, h4 - 26)).save(ASSETS / "shot_grid_lldp_startup.png", "PNG")

    # 5. Side-by-side pingall 30/30 + iperfudp 10M + watch curl /sdn/bandwidth (crop bottom 22px VB bar)
    im5 = Image.open(AUDIT_IMGS / "pdf" / "EN_C5_p1_obj13_1722x892_d975d95ed932.png")
    w5, h5 = im5.size
    im5.crop((0, 0, w5, h5 - 22)).save(ASSETS / "shot_c4_c5_bandwidth.png", "PNG")

    # 6 & 7. Live Web Dashboard Fat-Tree Normal & Failover (already clean browser crops)
    copy_docx_img(
        "8dc75ae389f6_image1.png",
        "output/report/chapter-4-implementation.docx",
        "word/media/image1.png",
        "shot_dashboard_fattree_normal.png",
    )
    copy_docx_img(
        "a4c738176772_image2.png",
        "output/report/chapter-4-implementation.docx",
        "word/media/image2.png",
        "shot_dashboard_fattree_failover.png",
    )

    # 8. Unshaped 32.3-34.0 Gbps TCP Stress causing LLDP link removal (crop bottom 26px VB bar)
    im8 = Image.open(AUDIT_IMGS / "pdf" / "EN_C5_p1_obj5_1892x928_00fb27e1f1b8.png")
    w8, h8 = im8.size
    im8.crop((0, 0, w8, h8 - 26)).save(ASSETS / "shot_unshaped_lldp_stress.png", "PNG")


# ═════════════════════════════════════════════════════════════════════════════
# PART B — REDRAWN 300 DPI TECHNICAL DIAGRAMS (7 FILES)
# ═════════════════════════════════════════════════════════════════════════════
def make_fig_2_1_trad_vs_sdn():
    fig, ax = plt.subplots(figsize=(10.2, 4.7))
    ax.set_xlim(0, 12.2)
    ax.set_ylim(0, 5.7)
    ax.axis("off")

    # Panel banners
    draw_box(ax, 0.25, 0.25, 5.45, 5.15, fc=BG_SOFT, ec=BORDER, lw=1.2, radius=0.14, zorder=1)
    draw_box(ax, 6.45, 0.25, 5.50, 5.15, fc=BG_SOFT, ec=TEAL, lw=1.3, radius=0.14, zorder=1)

    ax.text(2.97, 5.05, "(a) Traditional Vertically Integrated Switches",
            ha="center", va="center", fontsize=10.5, fontweight="bold", color=NAVY_DARK)
    ax.text(2.97, 4.72, "Distributed control + data planes coupled inside each device",
            ha="center", va="center", fontsize=8.0, color=SLATE_MUTED)

    ax.text(9.20, 5.05, "(b) Software-Defined Networking (SDN)",
            ha="center", va="center", fontsize=10.5, fontweight="bold", color=TEAL)
    ax.text(9.20, 4.72, "Logically centralized controller programs open forwarding tables",
            ha="center", va="center", fontsize=8.0, color=SLATE_MUTED)

    # Left: 3 traditional switches
    for idx, sx in enumerate([0.55, 2.25, 3.95], 1):
        draw_box(ax, sx, 1.35, 1.45, 2.95, fc=WHITE, ec=SLATE, lw=1.2, radius=0.10, zorder=2)
        ax.text(sx + 0.725, 4.08, f"Switch {idx}", ha="center", va="center",
                fontsize=8.6, fontweight="bold", color=NAVY_DARK, zorder=4)
        draw_box(ax, sx + 0.12, 3.18, 1.21, 0.65, "Mgmt / CLI", "Per-box config",
                 fc=AMBER_LIGHT, ec=AMBER, lw=1.0, title_size=7.6, sub_size=6.5, radius=0.06, zorder=3)
        draw_box(ax, sx + 0.12, 2.34, 1.21, 0.70, "Control Plane", "OSPF / STP / BGP",
                 fc=NAVY_LIGHT, ec=NAVY, lw=1.0, title_size=7.6, sub_size=6.5, radius=0.06, zorder=3)
        draw_box(ax, sx + 0.12, 1.48, 1.21, 0.70, "Data Plane", "ASIC / TCAM",
                 fc="#E2E8F0", ec=SLATE, lw=1.0, title_size=7.6, sub_size=6.5, radius=0.06, zorder=3)
    # Peer links between traditional switches
    for x1, x2 in [(2.00, 2.25), (3.70, 3.95)]:
        draw_arrow(ax, x1, 2.68, x2, 2.68, color=NAVY, lw=1.2, style="<->", ms=8)
        draw_arrow(ax, x1, 1.83, x2, 1.83, color=SLATE, lw=1.4, style="<->", ms=8)

    ax.text(2.97, 0.78, "Proprietary firmware · Local hop-by-hop view\nManual per-device tuning · Slow global convergence",
            ha="center", va="center", fontsize=8.0, color=AMBER, fontweight="bold", linespacing=1.35)

    # Right: SDN decoupled planes
    draw_box(ax, 6.72, 3.72, 4.96, 0.70, "Network Applications (Load Balancer · Failover · Dashboard)",
             "Policy via Northbound REST API (HTTP/JSON)",
             fc=NAVY_LIGHT, ec=NAVY, lw=1.3, title_size=7.7, sub_size=7.1, radius=0.08, zorder=3)
    draw_box(ax, 6.72, 2.52, 4.96, 0.78, "Logically Centralized SDN Controller (OS-Ken)",
             "Global topology graph · C4 telemetry · Yen k=3 path & MBB engine",
             fc=TEAL_LIGHT, ec=TEAL, lw=1.6, title_size=8.5, sub_size=7.1,
             title_color=TEAL, radius=0.08, zorder=3)

    draw_arrow(ax, 9.20, 3.70, 9.20, 3.33, color=NAVY, lw=1.5, style="<->", ms=10)
    ax.text(10.55, 3.51, "Northbound API", ha="center", va="center",
            fontsize=7.3, fontweight="bold", color=NAVY)

    # OpenFlow southbound arrows to 3 decoupled switches
    sw_xs = [6.78, 8.51, 10.24]
    for idx, sx in enumerate(sw_xs, 1):
        draw_box(ax, sx, 1.18, 1.38, 0.76, f"OVS Switch {idx}", "Data Plane Only",
                 fc=WHITE, ec=SLATE_DARK, lw=1.2, title_size=8.0, sub_size=6.8, radius=0.08, zorder=3)
        draw_arrow(ax, sx + 0.69, 2.50, sx + 0.69, 1.97, color=TEAL, lw=1.4, style="<->", ms=9)
    # Data plane links
    for x1, x2 in [(8.18, 8.50), (9.91, 10.23)]:
        draw_arrow(ax, x1, 1.56, x2, 1.56, color=SLATE, lw=1.6, style="<->", ms=8)

    ax.text(9.20, 2.24, "OpenFlow 1.3 Southbound (TCP :6653) — FlowMod / Stats / Barrier",
            ha="center", va="center", fontsize=7.3, fontweight="bold", color=TEAL,
            bbox=dict(boxstyle="round,pad=0.2", fc=WHITE, ec=TEAL, lw=0.8), zorder=5)

    ax.text(9.20, 0.66, "Vendor-neutral forwarding · Global real-time visibility\nProgrammatic traffic engineering · Atomic Make-Before-Break updates",
            ha="center", va="center", fontsize=7.4, color=TEAL, fontweight="bold", linespacing=1.35)

    save_fig(fig, "fig_2_1_trad_vs_sdn.png")


def make_fig_2_2_sdn_3layer():
    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    ax.set_xlim(0, 12.6)
    ax.set_ylim(0, 6.4)
    ax.axis("off")

    ax.text(6.3, 6.12, "Three-Layer Software-Defined Networking Architecture",
            ha="center", va="center", fontsize=11.5, fontweight="bold", color=NAVY_DARK)

    # Layer 3: Application Plane
    draw_box(ax, 0.35, 4.60, 8.95, 1.22, fc=NAVY_LIGHT, ec=NAVY, lw=1.4, radius=0.12, zorder=1)
    ax.text(0.58, 5.56, "APPLICATION PLANE", ha="left", va="center",
            fontsize=8.3, fontweight="bold", color=NAVY)
    apps = [
        ("Load Balancing", "Congestion-aware\nrerouting (Track 1)"),
        ("Fault Tolerance", "Link failure\nrecovery"),
        ("Telemetry & UI", "Live topology &\nlink utilization"),
        ("Policy / Security", "QoS, slicing,\naccess control"),
    ]
    for i, (t, s) in enumerate(apps):
        draw_box(ax, 0.55 + i * 2.18, 4.74, 2.02, 0.68, t, s,
                 fc=WHITE, ec=NAVY, lw=1.0, title_size=8.1, sub_size=6.8, radius=0.07)

    # Northbound interface band
    draw_arrow(ax, 4.82, 4.58, 4.82, 3.92, color=NAVY, lw=1.9, style="<->", ms=12)
    ax.text(5.05, 4.25, "Northbound Interface (NBI)  ·  REST / HTTP JSON (:8080)",
            ha="left", va="center", fontsize=8.3, fontweight="bold", color=NAVY,
            bbox=dict(boxstyle="round,pad=0.25", fc=WHITE, ec=NAVY, lw=0.9))

    # Layer 2: Control Plane
    draw_box(ax, 0.35, 2.40, 8.95, 1.48, fc=TEAL_LIGHT, ec=TEAL, lw=1.6, radius=0.12, zorder=1)
    ax.text(0.58, 3.63, "CONTROL PLANE  (Logically Centralized SDN Controller — OS-Ken / OpenFlow 1.3)",
            ha="left", va="center", fontsize=8.3, fontweight="bold", color=TEAL)
    ctrls = [
        ("Topology Manager", "LLDP discovery &\ngraph state"),
        ("Path Engine", "Yen k=3 & bottleneck\ncost selection"),
        ("Stats & Detection", "EWMA α=0.5 &\nelephant tracking"),
        ("Rule Orchestrator", "Priority-tiered MBB\n+ Barrier ACK"),
    ]
    for i, (t, s) in enumerate(ctrls):
        draw_box(ax, 0.55 + i * 2.18, 2.55, 2.02, 0.90, t, s,
                 fc=WHITE, ec=TEAL, lw=1.1, title_size=8.1, sub_size=6.9,
                 title_color=TEAL, radius=0.07)

    # East-West peer box on right (generous gap for label)
    draw_box(ax, 10.45, 2.55, 1.85, 1.18, "Peer Controller\nCluster",
             "Distributed state\nsync (ONOS/ODL)",
             fc=AMBER_LIGHT, ec=AMBER, lw=1.3, title_size=8.1, sub_size=6.9,
             title_color=AMBER, radius=0.09)
    draw_arrow(ax, 9.34, 3.04, 10.41, 3.04, color=AMBER, lw=1.7, style="<->", ms=11)
    ax.text(9.88, 3.48, "East–West\nAPI", ha="center", va="center",
            fontsize=7.6, fontweight="bold", color=AMBER)

    # Southbound interface band
    draw_arrow(ax, 4.82, 2.38, 4.82, 1.72, color=TEAL, lw=1.9, style="<->", ms=12)
    ax.text(5.05, 2.05, "Southbound Interface (SBI)  ·  OpenFlow 1.3 (TCP :6653) / OVSDB",
            ha="left", va="center", fontsize=8.3, fontweight="bold", color=TEAL,
            bbox=dict(boxstyle="round,pad=0.25", fc=WHITE, ec=TEAL, lw=0.9))

    # Layer 1: Infrastructure / Data Plane
    draw_box(ax, 0.35, 0.30, 8.95, 1.38, fc=BG_SOFT, ec=SLATE, lw=1.4, radius=0.12, zorder=1)
    ax.text(0.58, 1.44, "INFRASTRUCTURE (DATA) PLANE  —  Mininet + Open vSwitch (OVS) & Virtual Hosts",
            ha="left", va="center", fontsize=8.3, fontweight="bold", color=SLATE_DARK)
    sws = ["OVS S1", "OVS S2", "OVS S3", "OVS S4 .. S20"]
    for i, label in enumerate(sws):
        sx = 0.65 + i * 2.15
        draw_box(ax, sx, 0.48, 1.75, 0.72, label, "Flow Tables · Meters",
                 fc=WHITE, ec=SLATE_DARK, lw=1.1, title_size=8.2, sub_size=6.8, radius=0.07)
        if i < len(sws) - 1:
            draw_arrow(ax, sx + 1.77, 0.84, sx + 2.13, 0.84, color=SLATE, lw=1.5, style="<->", ms=8)

    # Side vertical annotation
    draw_box(ax, 10.45, 0.45, 1.85, 1.10, "Project Scope",
             "Single OS-Ken node\n6-switch Grid &\n20-switch Fat-Tree",
             fc=BG_SOFT, ec=BORDER, lw=1.1, title_size=8.0, sub_size=6.8, radius=0.09)

    save_fig(fig, "fig_2_2_sdn_3layer.png")


def make_fig_2_3_of13_pipeline():
    fig, ax = plt.subplots(figsize=(10.4, 5.4))
    ax.set_xlim(0, 12.4)
    ax.set_ylim(0, 6.3)
    ax.axis("off")

    ax.text(6.2, 6.02, "OpenFlow 1.3 Multi-Table Match-Action Pipeline & Flow Entry Anatomy",
            ha="center", va="center", fontsize=11.0, fontweight="bold", color=NAVY_DARK)

    # Top half: Packet Pipeline
    draw_box(ax, 0.25, 2.75, 11.90, 2.98, fc=BG_SOFT, ec=BORDER, lw=1.1, radius=0.12, zorder=1)
    ax.text(0.48, 5.48, "(a) Packet Processing Pipeline", ha="left", va="center",
            fontsize=9.0, fontweight="bold", color=NAVY)

    draw_box(ax, 0.48, 3.68, 1.45, 0.95, "Ingress\nPort", "Packet arrives\nwith metadata",
             fc=NAVY_LIGHT, ec=NAVY, lw=1.2, title_size=8.3, sub_size=6.8, radius=0.08)
    draw_box(ax, 2.38, 3.60, 2.05, 1.12, "Table 0", "Highest-priority match\n(Track 1: P20 / P21+)",
             fc=TEAL_LIGHT, ec=TEAL, lw=1.5, title_size=8.8, sub_size=7.0, title_color=TEAL, radius=0.08)
    draw_box(ax, 4.92, 3.60, 1.95, 1.12, "Table 1 .. N", "Optional Goto-Table\nchaining (OF 1.3)",
             fc=WHITE, ec=NAVY, lw=1.2, title_size=8.5, sub_size=6.9, radius=0.08)
    draw_box(ax, 7.38, 3.60, 2.05, 1.12, "Action Set &\nGroup Table", "Apply / Write Actions\nOutput / Select / FF",
             fc=NAVY_LIGHT, ec=NAVY, lw=1.2, title_size=8.3, sub_size=6.9, radius=0.08)
    draw_box(ax, 9.95, 3.68, 1.92, 0.95, "Egress Port", "Transmit packet\n(HTB 100 Mbps)",
             fc=EMERALD_LIGHT, ec=EMERALD, lw=1.3, title_size=8.5, sub_size=6.9, title_color=EMERALD, radius=0.08)

    draw_arrow(ax, 1.95, 4.16, 2.36, 4.16, color=NAVY, lw=1.5)
    draw_arrow(ax, 4.45, 4.16, 4.90, 4.16, color=NAVY, lw=1.4, ls="--")
    ax.text(4.67, 4.38, "Goto", ha="center", va="center", fontsize=6.9, color=SLATE)
    draw_arrow(ax, 6.89, 4.16, 7.36, 4.16, color=NAVY, lw=1.4, ls="--")
    draw_arrow(ax, 9.45, 4.16, 9.93, 4.16, color=EMERALD, lw=1.6)

    # Direct shortcut from Table 0 to Action Set (cleanly arched below label)
    draw_arrow(ax, 3.40, 4.74, 8.40, 4.74, color=TEAL, lw=1.5, rad=-0.12)
    ax.text(5.90, 5.34, "Track 1 Fast Path: Table 0 Apply-Actions(OUTPUT:port)",
            ha="center", va="center", fontsize=7.8, fontweight="bold", color=TEAL,
            bbox=dict(boxstyle="round,pad=0.18", fc=WHITE, ec=TEAL, lw=0.7), zorder=5)

    # Table-miss branch below Table 0 (widened so text fits with ample margins)
    draw_box(ax, 1.15, 2.90, 5.25, 0.44, "Table-Miss (Priority 0)  →  OFPT_PACKET_IN  →  Controller",
             fc=AMBER_LIGHT, ec=AMBER, lw=1.1, title_size=7.6, title_color=AMBER, radius=0.06)
    draw_arrow(ax, 3.40, 3.58, 3.40, 3.36, color=AMBER, lw=1.4)
    ax.text(3.60, 3.47, "No match", ha="left", va="center", fontsize=7.0, color=AMBER, fontweight="bold")

    # Bottom half: Flow Entry Anatomy
    draw_box(ax, 0.25, 0.22, 11.90, 2.30, fc=WHITE, ec=NAVY, lw=1.2, radius=0.12, zorder=1)
    ax.text(0.48, 2.26, "(b) OpenFlow 1.3 Flow Entry Structure (Installed via OFPT_FLOW_MOD)",
            ha="left", va="center", fontsize=9.0, fontweight="bold", color=NAVY)

    fields = [
        ("Match Fields", "eth_type=0x0800\neth_src, eth_dst\n(in_port optional)", NAVY_LIGHT, NAVY),
        ("Priority", "0: Table-miss\n20: Initial path\n21+: MBB reroute", TEAL_LIGHT, TEAL),
        ("Counters", "packet_count\nbyte_count\nduration_sec", BG_SOFT, SLATE),
        ("Instructions", "Apply-Actions:\nOUTPUT(port)\n(or CONTROLLER)", EMERALD_LIGHT, EMERALD),
        ("Timeouts", "idle_timeout\nhard_timeout\n(0 = permanent)", AMBER_LIGHT, AMBER),
        ("Cookie & Flags", "64-bit cookie\nSEND_FLOW_REM\n(OFPFC_ADD/DEL)", BG_SOFT, NAVY),
    ]
    fw = 1.82
    gap = 0.12
    for i, (t, s, fc, ec) in enumerate(fields):
        fx = 0.45 + i * (fw + gap)
        draw_box(ax, fx, 0.45, fw, 1.54, t, s, fc=fc, ec=ec, lw=1.2,
                 title_size=8.3, sub_size=7.0, title_color=ec if ec != SLATE else SLATE_DARK, radius=0.07)

    save_fig(fig, "fig_2_3_of13_pipeline.png")


def make_fig_3_1_controller_modules():
    fig, ax = plt.subplots(figsize=(10.8, 5.9))
    ax.set_xlim(0, 13.0)
    ax.set_ylim(0, 6.8)
    ax.axis("off")

    ax.text(6.5, 6.52, "OS-Ken Controller Modular Architecture & Event Interaction",
            ha="center", va="center", fontsize=11.2, fontweight="bold", color=NAVY_DARK)

    # Main controller enclosure (slightly wider right margin for clean failure channel)
    draw_box(ax, 0.30, 1.75, 9.25, 4.45, fc=BG_SOFT, ec=NAVY, lw=1.5, radius=0.14, zorder=1)
    ax.text(0.55, 5.95, "HostDiscoveryController  (vm-source/rest_api_controller.py · OS-Ken 3.1.1)",
            ha="left", va="center", fontsize=8.8, fontweight="bold", color=NAVY)

    # Row 1 inside controller: Discovery & ARP & Failure
    draw_box(ax, 0.55, 4.55, 2.65, 1.12, "LLDP Topology &\nHost Discovery",
             "Bounded LLDP wait · 10 s timeout\nNetworkX graph · PortStatus events",
             fc=NAVY_LIGHT, ec=NAVY, lw=1.2, title_size=8.2, sub_size=6.8, radius=0.08)
    draw_box(ax, 3.45, 4.55, 2.65, 1.12, "Proxy ARP &\nTable-Miss Handler",
             "Learns IP↔MAC↔(dpid,port)\nSuppresses broadcast ARP storms",
             fc=NAVY_LIGHT, ec=NAVY, lw=1.2, title_size=8.2, sub_size=6.8, radius=0.08)
    draw_box(ax, 6.35, 4.55, 2.65, 1.12, "Failure Recovery\nEngine",
             "Removes failed edges on EventLinkDelete\nRebuilds surviving paths automatically",
             fc=CRIMSON_LIGHT, ec=CRIMSON, lw=1.2, title_size=8.2, sub_size=6.7,
             title_color=CRIMSON, radius=0.08)

    # Row 2 inside controller: Telemetry & Detection & Path Selection
    draw_box(ax, 0.55, 3.18, 2.65, 1.08, "C4 Stats Poller",
             "OFPMP_PORT_STATS & FLOW_STATS\nPeriod T (5 s default / 2 s test)\nIngress MAC-pair accounting",
             fc=TEAL_LIGHT, ec=TEAL, lw=1.3, title_size=8.2, sub_size=6.7,
             title_color=TEAL, radius=0.08)
    draw_box(ax, 3.45, 3.18, 2.65, 1.08, "EWMA & Elephant\nDetector",
             "EWMA α=0.5 > θ (70%) ×2 periods\nElephant > 10% cap ×2 periods",
             fc=AMBER_LIGHT, ec=AMBER, lw=1.3, title_size=8.2, sub_size=6.7,
             title_color=AMBER, radius=0.08)
    draw_box(ax, 6.35, 3.18, 2.65, 1.08, "Yen k=3 Path\nSelector",
             "Simulated post-move bottleneck\nHop & shared-link tie-breakers\n≥15 pp gain + 30 s hold-down",
             fc=TEAL_LIGHT, ec=TEAL, lw=1.3, title_size=8.2, sub_size=6.6,
             title_color=TEAL, radius=0.08)

    # Row 3 inside controller: MBB Rule Engine (2-line subtitle fits comfortably)
    draw_box(ax, 0.55, 1.94, 8.45, 0.98, "Barrier-Gated Make-Before-Break (MBB) Rule Engine",
             "Installs priority P+1 rules egress → ingress and waits for OFPT_BARRIER_REPLY per switch;\ncommits with OFPFC_DELETE_STRICT (priority P) or safely rolls back on timeout",
             fc=EMERALD_LIGHT, ec=EMERALD, lw=1.5, title_size=8.5, sub_size=6.9,
             title_color=EMERALD, radius=0.08)

    # Internal arrows (orthogonal channel for Failure Recovery so zero text crossing!)
    draw_arrow(ax, 3.22, 5.10, 3.43, 5.10, color=NAVY, lw=1.3, ms=9)
    draw_arrow(ax, 3.22, 3.72, 3.43, 3.72, color=TEAL, lw=1.4, ms=10)
    draw_arrow(ax, 6.12, 3.72, 6.33, 3.72, color=AMBER, lw=1.4, ms=10)
    draw_arrow(ax, 7.68, 3.16, 7.68, 2.94, color=EMERALD, lw=1.5, ms=10)
    # Orthogonal right channel: Failure Recovery -> MBB
    ax.plot([9.02, 9.32, 9.32], [5.10, 5.10, 2.43], color=CRIMSON, lw=1.4, ls="--", zorder=4)
    draw_arrow(ax, 9.32, 2.43, 9.02, 2.43, color=CRIMSON, lw=1.4, ls="--", ms=9)
    draw_arrow(ax, 1.88, 4.53, 1.88, 4.28, color=NAVY, lw=1.2, ms=9)

    # Right column: REST API + Web Dashboard + Experiment Harness
    draw_box(ax, 10.05, 4.25, 2.45, 1.65, "Eventlet WSGI\nREST API",
             "127.0.0.1:8080\n/sdn/status · /topology\n/hosts · /bandwidth · /flows",
             fc=NAVY_LIGHT, ec=NAVY, lw=1.4, title_size=8.4, sub_size=6.8, radius=0.09)
    draw_box(ax, 10.05, 2.50, 2.45, 1.32, "Local Web Dashboard",
             "dashboard/serve.py (:8081)\n1 s live poll · SVG topology\nPath highlight & link bars",
             fc=WHITE, ec=TEAL, lw=1.3, title_size=8.2, sub_size=6.7,
             title_color=TEAL, radius=0.09)
    draw_box(ax, 10.05, 0.35, 2.45, 1.55, "Experiment Harness",
             "experiments/*.py\nRepeatable JSON captures\n(Nov 25–26 datasets)",
             fc=BG_SOFT, ec=SLATE, lw=1.2, title_size=8.2, sub_size=6.8, radius=0.09)

    draw_arrow(ax, 9.57, 5.05, 10.03, 5.05, color=NAVY, lw=1.5, style="<->", ms=10)
    draw_arrow(ax, 11.27, 4.23, 11.27, 3.84, color=TEAL, lw=1.4, style="<->", ms=10)
    # Clean outer right channel from REST API -> Experiment Harness (zero box crossing!)
    ax.plot([12.52, 12.78, 12.78], [5.05, 5.05, 1.12], color=SLATE, lw=1.3, ls="--", zorder=4)
    draw_arrow(ax, 12.78, 1.12, 12.52, 1.12, color=SLATE, lw=1.3, ls="--", ms=9)

    # Bottom: Mininet + OVS Data Plane
    draw_box(ax, 0.30, 0.35, 9.25, 0.92, "Mininet 2.3 + Open vSwitch (OpenFlow 1.3 · TCP 127.0.0.1:6653)",
             "6-Switch Grid (7 × 100 Mbps / 2 ms / 64k HTB)  &  k=4 Fat-Tree (20 Switches · 32 Links · 16 Hosts)",
             fc=WHITE, ec=SLATE_DARK, lw=1.4, title_size=8.6, sub_size=7.2, radius=0.09)

    draw_arrow(ax, 1.65, 1.29, 1.65, 1.73, color=TEAL, lw=1.6, ms=10)
    ax.text(1.80, 1.51, "PACKET_IN / LLDP / Stats Replies", ha="left", va="center",
            fontsize=7.3, fontweight="bold", color=TEAL)
    draw_arrow(ax, 5.75, 1.73, 5.75, 1.29, color=EMERALD, lw=1.6, ms=10)
    ax.text(5.90, 1.51, "FLOW_MOD / BARRIER / PACKET_OUT", ha="left", va="center",
            fontsize=7.3, fontweight="bold", color=EMERALD)

    save_fig(fig, "fig_3_1_controller_modules.png")


def make_fig_3_2_topologies():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 5.2), gridspec_kw={"width_ratios": [1.0, 1.22]})

    # ── Panel (a): 2×3 Lab Grid with exact port labels & P1 vs P3 ────────────
    ax1.set_xlim(-0.3, 6.3)
    ax1.set_ylim(-0.6, 5.4)
    ax1.axis("off")
    ax1.set_title("(a) 2×3 Lab Grid  (6 Switches · 7 Links · 6 Hosts)",
                  fontsize=10.0, fontweight="bold", color=NAVY_DARK, pad=6)

    sw_pos = {
        "S1": (1.0, 3.3), "S2": (3.0, 3.3), "S3": (5.0, 3.3),
        "S4": (1.0, 1.5), "S5": (3.0, 1.5), "S6": (5.0, 1.5),
    }
    host_pos = {
        "H1\n10.0.0.1": (1.0, 4.65, "S1", "p3"),
        "H3\n10.0.0.3": (3.0, 4.65, "S2", "p4"),
        "H5\n10.0.0.5": (5.0, 4.65, "S3", "p3"),
        "H2\n10.0.0.2": (1.0, 0.15, "S4", "p3"),
        "H4\n10.0.0.4": (3.0, 0.15, "S5", "p4"),
        "H6\n10.0.0.6": (5.0, 0.15, "S6", "p3"),
    }

    # Exact links from vm-source/custom_topology.py:
    # (u, v, port_u, port_v, color, ls, lw)
    grid_links = [
        ("S1", "S2", "p1", "p1", AMBER, "--", 2.6),   # P1 upper
        ("S2", "S3", "p2", "p1", AMBER, "--", 2.6),   # P1 upper (shared bottleneck)
        ("S3", "S6", "p2", "p1", AMBER, "--", 2.6),   # P1 upper
        ("S1", "S4", "p2", "p2", TEAL, "-", 2.8),     # P3 lower (balanced reroute)
        ("S4", "S5", "p1", "p3", TEAL, "-", 2.8),     # P3 lower
        ("S5", "S6", "p1", "p2", TEAL, "-", 2.8),     # P3 lower
        ("S2", "S5", "p3", "p2", SLATE_MUTED, "-", 1.8),  # Center vertical (P2)
    ]

    for u, v, pu, pv, col, ls, lw in grid_links:
        x1, y1 = sw_pos[u]
        x2, y2 = sw_pos[v]
        ax1.plot([x1, x2], [y1, y2], color=col, linestyle=ls, linewidth=lw, zorder=2)
        # Port labels offset cleanly near switch boundary
        dx, dy = x2 - x1, y2 - y1
        dist = np.hypot(dx, dy)
        ux, uy = dx / dist, dy / dist
        # Perpendicular tiny offset so labels never collide with link lines
        px, py = -uy * 0.19, ux * 0.19
        if y1 == y2:  # horizontal link -> put labels slightly above/below
            off_y = 0.20 if y1 > 2.5 else -0.22
            ax1.text(x1 + ux * 0.56, y1 + off_y, pu, ha="center", va="center",
                     fontsize=7.3, fontweight="bold", color=SLATE_DARK, zorder=5)
            ax1.text(x2 - ux * 0.56, y2 + off_y, pv, ha="center", va="center",
                     fontsize=7.3, fontweight="bold", color=SLATE_DARK, zorder=5)
        else:  # vertical link -> put labels slightly to the right
            ax1.text(x1 + 0.25, y1 + uy * 0.48, pu, ha="center", va="center",
                     fontsize=7.3, fontweight="bold", color=SLATE_DARK, zorder=5)
            ax1.text(x2 + 0.25, y2 - uy * 0.48, pv, ha="center", va="center",
                     fontsize=7.3, fontweight="bold", color=SLATE_DARK, zorder=5)

    # Host links
    for hlbl, (hx, hy, sw, hp) in host_pos.items():
        sx, sy = sw_pos[sw]
        ax1.plot([hx, sx], [hy, sy], color=SLATE_MUTED, linewidth=1.3, zorder=1)
        off_y = 0.48 if hy > sy else -0.48
        ax1.text(sx - 0.24, sy + off_y, hp, ha="center", va="center",
                 fontsize=7.1, fontweight="bold", color=SLATE, zorder=5)
        draw_box(ax1, hx - 0.55, hy - 0.28, 1.10, 0.56, hlbl,
                 fc=NAVY_LIGHT, ec=NAVY, lw=1.1, title_size=7.4, radius=0.09, zorder=4)

    # Switches
    for name, (sx, sy) in sw_pos.items():
        draw_box(ax1, sx - 0.42, sy - 0.28, 0.84, 0.56, name,
                 fc=WHITE, ec=NAVY_DARK, lw=1.6, title_size=9.2, radius=0.09, zorder=4)

    # Legend & link spec banner
    ax1.plot([0.1, 0.65], [-0.42, -0.42], color=AMBER, ls="--", lw=2.5)
    ax1.text(0.75, -0.42, "P1 (Default P20)", va="center", fontsize=7.6, fontweight="bold", color=AMBER)
    ax1.plot([2.55, 3.10], [-0.42, -0.42], color=TEAL, ls="-", lw=2.7)
    ax1.text(3.20, -0.42, "P3 (Rerouted P21)", va="center", fontsize=7.6, fontweight="bold", color=TEAL)
    ax1.text(3.0, 2.40, "All 7 trunks:\n100 Mbps · 2 ms\n64k HTB burst",
             ha="center", va="center", fontsize=7.0, color=SLATE,
             bbox=dict(boxstyle="round,pad=0.22", fc=BG_SOFT, ec=BORDER, lw=0.8), zorder=5)

    # ── Panel (b): k=4 Fat-Tree ──────────────────────────────────────────────
    ax2.set_xlim(-0.5, 16.5)
    ax2.set_ylim(-0.6, 5.4)
    ax2.axis("off")
    ax2.set_title("(b) k = 4 Fat-Tree  (20 Switches · 32 Links · 16 Hosts)",
                  fontsize=10.0, fontweight="bold", color=NAVY_DARK, pad=6)

    core_xs = [2.6, 6.2, 9.8, 13.4]
    agg_xs = [1.0, 2.8, 5.2, 7.0, 9.4, 11.2, 13.6, 15.4]
    edge_xs = list(agg_xs)
    host_xs = [x + dx for x in edge_xs for dx in (-0.42, 0.42)]

    y_core, y_agg, y_edge, y_host = 4.55, 3.15, 1.70, 0.48

    # Pod backdrop rectangles
    for pod in range(4):
        px = agg_xs[2 * pod] - 0.85
        pw = (agg_xs[2 * pod + 1] - agg_xs[2 * pod]) + 1.70
        draw_box(ax2, px, 0.08, pw, 3.55, fc=BG_SOFT, ec=GRID, lw=0.9, radius=0.14, zorder=0)
        ax2.text(px + pw / 2, -0.14, f"Pod {pod}", ha="center", va="center",
                 fontsize=7.6, fontweight="bold", color=SLATE_MUTED)

    # Active H1->H16 path edges & failover path
    normal_edges = {(0, 0), (0, 8), (6, 8), (6, 7)}  # handled explicitly below

    # Draw Agg <-> Core links (16 links)
    for pod in range(4):
        for local_idx in (0, 1):
            a_i = 2 * pod + local_idx
            for c_i in (2 * local_idx, 2 * local_idx + 1):
                is_norm = (a_i == 0 and c_i == 0) or (a_i == 6 and c_i == 0)
                is_fail = (a_i == 0 and c_i == 1) or (a_i == 6 and c_i == 1)
                col = TEAL if is_norm else (AMBER if is_fail else "#CBD5E1")
                lw = 2.4 if is_norm else (2.0 if is_fail else 0.95)
                ls = "-" if not is_fail else "--"
                z = 3 if (is_norm or is_fail) else 1
                ax2.plot([agg_xs[a_i], core_xs[c_i]], [y_agg, y_core],
                         color=col, lw=lw, ls=ls, zorder=z)

    # Draw Edge <-> Agg links (16 links)
    for pod in range(4):
        for e_off in (0, 1):
            e_i = 2 * pod + e_off
            for a_off in (0, 1):
                a_i = 2 * pod + a_off
                is_norm = (e_i == 0 and a_i == 0) or (e_i == 7 and a_i == 6)
                col = TEAL if is_norm else "#CBD5E1"
                lw = 2.4 if is_norm else 0.95
                z = 3 if is_norm else 1
                ax2.plot([edge_xs[e_i], agg_xs[a_i]], [y_edge, y_agg],
                         color=col, lw=lw, zorder=z)

    # Draw Host <-> Edge links (16 links)
    for i, hx in enumerate(host_xs):
        e_i = i // 2
        is_hl = i in (0, 15)
        ax2.plot([hx, edge_xs[e_i]], [y_host, y_edge],
                 color=TEAL if is_hl else "#CBD5E1", lw=1.8 if is_hl else 0.85, zorder=2)
        ax2.scatter([hx], [y_host], s=26 if is_hl else 16,
                    color=TEAL if is_hl else SLATE_MUTED, zorder=5)
        if i in (0, 1, 7, 8, 14, 15):
            ax2.text(hx, y_host - 0.25, f"H{i+1}", ha="center", va="center",
                     fontsize=6.4, fontweight="bold" if is_hl else "normal",
                     color=TEAL if is_hl else SLATE)

    # Core switches S17-S20
    for i, cx in enumerate(core_xs):
        lbl = f"S{17+i}"
        ec = TEAL if i == 0 else (AMBER if i == 1 else NAVY)
        fc = TEAL_LIGHT if i == 0 else (AMBER_LIGHT if i == 1 else WHITE)
        draw_box(ax2, cx - 0.62, y_core - 0.25, 1.24, 0.50, lbl,
                 fc=fc, ec=ec, lw=1.4 if i < 2 else 1.1, title_size=7.8, radius=0.08, zorder=5)

    # Agg switches S9-S16
    for i, axx in enumerate(agg_xs):
        hl = i in (0, 6)
        draw_box(ax2, axx - 0.55, y_agg - 0.22, 1.10, 0.44, f"S{9+i}",
                 fc=TEAL_LIGHT if hl else WHITE, ec=TEAL if hl else NAVY,
                 lw=1.35 if hl else 0.95, title_size=7.0, radius=0.07, zorder=5)

    # Edge switches S1-S8
    for i, ex in enumerate(edge_xs):
        hl = i in (0, 7)
        draw_box(ax2, ex - 0.55, y_edge - 0.22, 1.10, 0.44, f"S{1+i}",
                 fc=TEAL_LIGHT if hl else WHITE, ec=TEAL if hl else SLATE_DARK,
                 lw=1.35 if hl else 0.95, title_size=7.0, radius=0.07, zorder=5)

    # Layer labels on far left
    ax2.text(-0.42, y_core, "Core\n(4)", ha="center", va="center", fontsize=7.0, fontweight="bold", color=NAVY)
    ax2.text(-0.42, y_agg, "Agg\n(8)", ha="center", va="center", fontsize=7.0, fontweight="bold", color=NAVY)
    ax2.text(-0.42, y_edge, "Edge\n(8)", ha="center", va="center", fontsize=7.0, fontweight="bold", color=NAVY)

    # Fat-tree legend
    ax2.plot([0.2, 1.2], [-0.45, -0.45], color=TEAL, lw=2.4)
    ax2.text(1.4, -0.45, "Primary H1→H16 (via S17)", va="center", fontsize=7.5, fontweight="bold", color=TEAL)
    ax2.plot([8.2, 9.2], [-0.45, -0.45], color=AMBER, ls="--", lw=2.0)
    ax2.text(9.4, -0.45, "Failover path after S9–S17 cut (via S18)", va="center", fontsize=7.5, fontweight="bold", color=AMBER)

    fig.tight_layout(w_pad=1.6)
    save_fig(fig, "fig_3_2_topologies.png")


def make_fig_3_3_lb_flowchart():
    fig, ax = plt.subplots(figsize=(10.4, 6.2))
    ax.set_xlim(0, 12.6)
    ax.set_ylim(0, 7.6)
    ax.axis("off")

    ax.text(6.3, 7.34, "Congestion-Aware Load Balancer Decision & Rerouting Flowchart",
            ha="center", va="center", fontsize=11.0, fontweight="bold", color=NAVY_DARK)

    # Top row (left -> right): Poll -> EWMA -> Elephant
    draw_box(ax, 0.35, 5.75, 2.75, 1.05, "1. C4 Periodic Poll (T)",
             "OFPMP_PORT_STATS & FLOW_STATS\nCompute directional TX Mbps\n& ingress MAC-pair rates",
             fc=NAVY_LIGHT, ec=NAVY, lw=1.3, title_size=8.4, sub_size=6.8, radius=0.09)

    draw_diamond(ax, 5.35, 6.27, 2.85, 1.38, "2. EWMA (α=0.5)\n> θ (70%) for\n2 consecutive polls?")

    draw_diamond(ax, 9.80, 6.27, 2.95, 1.38, "3. Elephant Flow\n> 10% cap (10 Mbps)\nfor 2 polls on link?")

    draw_arrow(ax, 3.12, 6.27, 3.90, 6.27, color=NAVY, lw=1.5)
    draw_arrow(ax, 6.80, 6.27, 8.30, 6.27, color=TEAL, lw=1.5)
    ax.text(7.55, 6.48, "Yes", ha="center", va="center", fontsize=8.0, fontweight="bold", color=TEAL)

    # "No" return box from EWMA / Elephant
    draw_box(ax, 5.45, 4.45, 3.15, 0.65, "Keep Current Paths",
             "Update EWMA state · Wait next poll T",
             fc=BG_SOFT, ec=SLATE, lw=1.1, title_size=8.0, sub_size=6.8, radius=0.08)
    draw_arrow(ax, 5.35, 5.56, 6.40, 5.12, color=SLATE, lw=1.3, ls="--")
    ax.text(5.45, 5.30, "No", ha="center", va="center", fontsize=7.6, fontweight="bold", color=SLATE)
    draw_arrow(ax, 9.80, 5.56, 7.65, 5.12, color=SLATE, lw=1.3, ls="--")
    ax.text(9.05, 5.18, "No", ha="center", va="center", fontsize=7.6, fontweight="bold", color=SLATE)

    # Step 4: Yen k=3 Path Selection (right middle)
    draw_box(ax, 9.15, 3.30, 3.10, 1.28, "4. Yen k = 3 Candidate\nPath Selection",
             "Simulate moving flow off old path\nMin post-move bottleneck util.\nTie-break: hops → shared links",
             fc=TEAL_LIGHT, ec=TEAL, lw=1.4, title_size=8.3, sub_size=6.8,
             title_color=TEAL, radius=0.09)
    draw_arrow(ax, 10.70, 5.56, 10.70, 4.60, color=TEAL, lw=1.5)
    ax.text(11.02, 5.12, "Yes", ha="center", va="center", fontsize=8.0, fontweight="bold", color=TEAL)

    # Step 5: Hysteresis & Hold-Down gate (center bottom-mid)
    draw_diamond(ax, 6.05, 3.00, 3.35, 1.48, "5. Gain ≥ 15 pp\nAND Hold-Down\n(30 s) expired?")
    draw_arrow(ax, 9.13, 3.72, 7.70, 3.22, color=TEAL, lw=1.5)

    # No -> Suppress oscillation
    draw_box(ax, 5.00, 1.05, 2.55, 0.72, "Suppress Reroute",
             "Prevent route flapping;\nkeep active priority rules",
             fc=BG_SOFT, ec=SLATE, lw=1.1, title_size=8.0, sub_size=6.8, radius=0.08)
    draw_arrow(ax, 6.05, 2.24, 6.05, 1.80, color=SLATE, lw=1.3, ls="--")
    ax.text(6.32, 2.04, "No", ha="center", va="center", fontsize=7.8, fontweight="bold", color=SLATE)

    # Step 6: Egress-to-Ingress MBB + Barrier ACK (left middle)
    draw_box(ax, 0.72, 2.40, 3.05, 1.25, "6. Egress → Ingress MBB",
             "Install new path at priority P+1\nSend OFPT_BARRIER_REQUEST\nWait BARRIER_REPLY per switch",
             fc=EMERALD_LIGHT, ec=EMERALD, lw=1.5, title_size=8.4, sub_size=6.8,
             title_color=EMERALD, radius=0.09)
    draw_arrow(ax, 4.35, 3.00, 3.79, 3.00, color=EMERALD, lw=1.6)
    ax.text(4.07, 3.22, "Yes", ha="center", va="center", fontsize=8.0, fontweight="bold", color=EMERALD)

    # Step 7: All Barriers OK?
    draw_diamond(ax, 2.24, 1.15, 2.50, 1.12, "7. All Barrier\nACKs received?")
    draw_arrow(ax, 2.24, 2.38, 2.24, 1.73, color=EMERALD, lw=1.5)

    # Yes -> Commit & Strict Delete (clean orthogonal entry into bottom center of 8a)
    draw_box(ax, 8.20, 0.60, 4.05, 1.12, "8a. Commit Cutover & Cleanup",
             "Send OFPFC_DELETE_STRICT for old priority P\nRecord active path & start 30 s hold-down timer",
             fc=EMERALD_LIGHT, ec=EMERALD, lw=1.4, title_size=8.3, sub_size=6.8,
             title_color=EMERALD, radius=0.09)
    ax.plot([2.24, 2.24, 10.22], [0.57, 0.20, 0.20], color=EMERALD, lw=1.6, zorder=4)
    draw_arrow(ax, 10.22, 0.20, 10.22, 0.58, color=EMERALD, lw=1.6)
    ax.text(5.80, 0.35, "Yes (All switches acknowledged)", ha="center", va="center",
            fontsize=7.7, fontweight="bold", color=EMERALD)

    # No -> Rollback (with crisp white label badge)
    draw_box(ax, 0.72, 4.18, 3.05, 0.92, "8b. Safe Rollback",
             "Delete partial priority P+1 rules\nOriginal priority P path stays intact",
             fc=CRIMSON_LIGHT, ec=CRIMSON, lw=1.3, title_size=8.2, sub_size=6.8,
             title_color=CRIMSON, radius=0.08)
    ax.plot([0.97, 0.30, 0.30], [1.15, 1.15, 4.64], color=CRIMSON, lw=1.4, ls="--", zorder=4)
    draw_arrow(ax, 0.30, 4.64, 0.70, 4.64, color=CRIMSON, lw=1.4, ls="--")
    ax.text(0.30, 3.05, "No\n(Timeout)", ha="center", va="center",
            fontsize=7.1, fontweight="bold", color=CRIMSON,
            bbox=dict(boxstyle="round,pad=0.18", fc=WHITE, ec=CRIMSON, lw=0.7), zorder=5)

    save_fig(fig, "fig_3_3_lb_flowchart.png")


def make_fig_3_4_mbb_sequence():
    fig, ax = plt.subplots(figsize=(10.4, 6.4))
    ax.set_xlim(0, 12.2)
    ax.set_ylim(0, 7.9)
    ax.axis("off")

    ax.text(6.1, 7.64, "OpenFlow 1.3 Barrier-Gated Make-Before-Break (MBB) Sequence  (H1→H6: P1 → P3)",
            ha="center", va="center", fontsize=10.6, fontweight="bold", color=NAVY_DARK)

    actors = [
        ("OS-Ken\nController", 1.35, NAVY_LIGHT, NAVY),
        ("S6\n(Egress)", 4.05, TEAL_LIGHT, TEAL),
        ("S5\n(Core/Mid)", 6.45, TEAL_LIGHT, TEAL),
        ("S4\n(Core/Mid)", 8.85, TEAL_LIGHT, TEAL),
        ("S1\n(Ingress)", 11.10, AMBER_LIGHT, AMBER),
    ]
    for label, x, fc, ec in actors:
        draw_box(ax, x - 0.82, 6.72, 1.64, 0.64, label, fc=fc, ec=ec, lw=1.4, title_size=8.3, radius=0.08)
        ax.plot([x, x], [0.28, 6.70], color=BORDER, ls="--", lw=1.2, zorder=1)

    # Phase 1 shading: generous bottom margin below final BARRIER_REPLY
    draw_box(ax, 0.25, 3.12, 11.75, 3.30, fc="#F2FBF9", ec=TEAL, lw=0.9, radius=0.10, zorder=0)
    ax.text(0.42, 6.22, "Phase 1 — Egress-to-Ingress Priority-21 Installation (Old Priority-20 Path S1→S2→S3→S6 Remains Active)",
            ha="left", va="center", fontsize=7.9, fontweight="bold", color=TEAL)

    steps_p1 = [
        (5.76, 4.05, "1. FLOW_MOD (ADD, prio=21, out=p3→H6) + BARRIER_REQ", "BARRIER_REPLY (S6 ready)"),
        (5.06, 6.45, "2. FLOW_MOD (ADD, prio=21, out=p1→S6) + BARRIER_REQ", "BARRIER_REPLY (S5 ready)"),
        (4.36, 8.85, "3. FLOW_MOD (ADD, prio=21, out=p1→S5) + BARRIER_REQ", "BARRIER_REPLY (S4 ready)"),
        (3.66, 11.10, "4. FLOW_MOD (ADD, prio=21, out=p2→S4) + BARRIER_REQ  [Atomic Cutover!]", "BARRIER_REPLY (S1 cutover ACK)"),
    ]
    x0 = actors[0][1]
    for y, xt, req, rep in steps_p1:
        col = AMBER if xt > 10 else TEAL
        draw_arrow(ax, x0 + 0.05, y, xt - 0.05, y, color=col, lw=1.6, ms=10)
        ax.text((x0 + xt) / 2, y + 0.14, req, ha="center", va="center",
                fontsize=7.2, fontweight="bold", color=col)
        draw_arrow(ax, xt - 0.05, y - 0.24, x0 + 0.05, y - 0.24, color=SLATE, lw=1.2, ls="--", ms=9)
        ax.text((x0 + xt) / 2, y - 0.39, rep, ha="center", va="center",
                fontsize=6.9, color=SLATE)

    # Phase 2a: Success cleanup
    draw_box(ax, 0.25, 1.62, 11.75, 1.32, fc=EMERALD_LIGHT, ec=EMERALD, lw=1.0, radius=0.10, zorder=0)
    ax.text(0.42, 2.75, "Phase 2a — Normal Completion (All 4 Barrier Replies Received Within Timeout)",
            ha="left", va="center", fontsize=7.9, fontweight="bold", color=EMERALD)
    draw_arrow(ax, x0 + 0.05, 2.30, 11.05, 2.30, color=EMERALD, lw=1.6, ms=10)
    ax.text(6.2, 2.46, "5. OFPFC_DELETE_STRICT (prio=20) sent to old path switches {S1, S2, S3, S6}",
            ha="center", va="center", fontsize=7.5, fontweight="bold", color=EMERALD)
    ax.text(6.2, 1.88, "Traffic shifts cleanly to P3 (S1→S4→S5→S6) at priority 21 · 30 s per-flow hold-down timer armed",
            ha="center", va="center", fontsize=7.4, color=SLATE_DARK, style="italic")

    # Phase 2b: Rollback branch
    draw_box(ax, 0.25, 0.26, 11.75, 1.18, fc=CRIMSON_LIGHT, ec=CRIMSON, lw=1.0, radius=0.10, zorder=0)
    ax.text(0.42, 1.25, "Phase 2b — Rollback Branch (If Any Switch Fails or Misses Barrier Reply Timeout)",
            ha="left", va="center", fontsize=7.9, fontweight="bold", color=CRIMSON)
    draw_arrow(ax, x0 + 0.05, 0.79, 8.80, 0.79, color=CRIMSON, lw=1.5, ls="--", ms=10)
    ax.text(5.1, 0.94, "OFPFC_DELETE_STRICT (prio=21) removes partial installs on already-updated switches",
            ha="center", va="center", fontsize=7.4, fontweight="bold", color=CRIMSON)
    ax.text(6.2, 0.47, "Original priority-20 rules on P1 are never deleted → zero black-hole forwarding state",
            ha="center", va="center", fontsize=7.3, color=SLATE_DARK, style="italic")

    save_fig(fig, "fig_3_4_mbb_sequence.png")


# ═════════════════════════════════════════════════════════════════════════════
# PART C — PUBLICATION-GRADE 300 DPI CH. 5 EXPERIMENT PLOTS (6 FILES)
# ═════════════════════════════════════════════════════════════════════════════
def load_json(rel: str):
    return json.loads((DATA / rel).read_text(encoding="utf-8"))


def make_fig_5_1_c4_accuracy():
    raw = load_json("accuracy-20261126T124854Z.json")
    trials = raw["trials"]
    idx = np.arange(1, len(trials) + 1)
    sender = [t["sender_mbps"] for t in trials]
    tx = [t["controller_tx_mbps"] for t in trials]
    err = [t["error_percent"] for t in trials]
    mean_err = st.mean(err)
    sd_err = st.stdev(err)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.2, 4.1), gridspec_kw={"width_ratios": [1.15, 1.0]})

    # Panel (a): Grouped bar per trial
    w = 0.36
    b1 = ax1.bar(idx - w / 2, sender, width=w, color=NAVY, label="iperf3 Sender Payload", zorder=3)
    b2 = ax1.bar(idx + w / 2, tx, width=w, color=TEAL, label="Controller Port TX", zorder=3)
    for bar, val in zip(b1, sender):
        ax1.text(bar.get_x() + bar.get_width() / 2, val + 0.08, f"{val:.2f}",
                 ha="center", va="bottom", fontsize=7.3, color=NAVY_DARK)
    for bar, val in zip(b2, tx):
        ax1.text(bar.get_x() + bar.get_width() / 2, val + 0.08, f"{val:.2f}",
                 ha="center", va="bottom", fontsize=7.3, fontweight="bold", color=TEAL)
    ax1.set_xticks(idx)
    ax1.set_xticklabels([f"Trial {i}" for i in idx])
    ax1.set_ylabel("Throughput (Mbps)", fontweight="bold")
    ax1.set_ylim(0, 6.4)
    ax1.set_title("(a) Sender Payload vs. Controller Port TX", fontsize=9.8, fontweight="bold", pad=8)
    ax1.legend(loc="lower right", frameon=True, facecolor=WHITE, edgecolor=BORDER, fontsize=8.0)
    style_axes(ax1)

    # Panel (b): Absolute Relative Error + 10% limit
    ax2.axhspan(mean_err - sd_err, mean_err + sd_err, color=TEAL_LIGHT, alpha=0.85, zorder=1,
                label=f"Mean ± SD ({mean_err:.3f} ± {sd_err:.3f}%)")
    ax2.axhline(mean_err, color=TEAL, lw=1.6, ls="-", zorder=2)
    ax2.axhline(10.0, color=CRIMSON, lw=1.6, ls="--", zorder=2, label="Assignment Limit (10.0%)")
    ax2.scatter(idx, err, s=62, color=NAVY, edgecolor=WHITE, linewidth=1.2, zorder=4)
    for x, y in zip(idx, err):
        ax2.text(x, y + 0.42, f"{y:.2f}%", ha="center", va="bottom",
                 fontsize=7.8, fontweight="bold", color=NAVY_DARK)
    ax2.text(3.0, 9.25, "10.0% Max Error Requirement (All 5/5 Pass)",
             ha="center", va="center", fontsize=7.7, fontweight="bold", color=CRIMSON)
    ax2.set_xticks(idx)
    ax2.set_xticklabels([f"T{i}" for i in idx])
    ax2.set_ylabel("Absolute Relative Error (%)", fontweight="bold")
    ax2.set_ylim(0, 11.4)
    ax2.set_title("(b) Relative Monitoring Error (n = 5)", fontsize=9.8, fontweight="bold", pad=8)
    ax2.legend(loc="center right", frameon=True, facecolor=WHITE, edgecolor=BORDER, fontsize=7.8)
    style_axes(ax2)

    fig.suptitle("C4 Bandwidth Monitoring Accuracy — k = 4 Fat-Tree (H1→H16, 5 Mbps UDP, Nov 26)",
                 fontsize=10.8, fontweight="bold", color=NAVY_DARK, y=1.01)
    fig.tight_layout(w_pad=2.0)
    save_fig(fig, "fig_5_1_c4_accuracy.png")


def make_fig_5_2_grid_comparison():
    rows = load_json("compare-grid-20261125T194357Z/summary.json")

    def get_vals(host, mode, key):
        sub = sorted([r for r in rows if r["mode"] == mode], key=lambda r: r["pair"])
        return [r["receivers"][host][key] for r in sub]

    fig, axes = plt.subplots(1, 3, figsize=(11.2, 4.2))
    specs = [
        ("mbps", "(a) Receiver Throughput", "Throughput (Mbps)", 96, "{:.2f}"),
        ("loss_percent", "(b) Packet Loss", "Packet Loss (%)", 47, "{:.2f}%"),
        ("jitter_ms", "(c) UDP Jitter", "Jitter (ms)", 4.2, "{:.2f}"),
    ]
    x = np.array([0, 1])
    w = 0.34
    rng = np.random.default_rng(42)

    for ax, (key, title, ylabel, ymax, fmt) in zip(axes, specs):
        sh_vals = [get_vals("H6", "shortest", key), get_vals("H5", "shortest", key)]
        ba_vals = [get_vals("H6", "balanced", key), get_vals("H5", "balanced", key)]
        sh_m = [st.mean(v) for v in sh_vals]
        sh_s = [st.stdev(v) for v in sh_vals]
        ba_m = [st.mean(v) for v in ba_vals]
        ba_s = [st.stdev(v) for v in ba_vals]

        ax.bar(x - w / 2, sh_m, width=w, color=AMBER, alpha=0.88, label="Shortest Path (P1, P20)", zorder=2)
        ax.bar(x + w / 2, ba_m, width=w, color=TEAL, alpha=0.92, label="Balanced MBB (P3, P21)", zorder=2)
        ax.errorbar(x - w / 2, sh_m, yerr=sh_s, fmt="none", ecolor=SLATE_DARK, capsize=4, lw=1.2, zorder=4)
        ax.errorbar(x + w / 2, ba_m, yerr=ba_s, fmt="none", ecolor=SLATE_DARK, capsize=4, lw=1.2, zorder=4)

        # Overlay individual trial dots
        for i in range(2):
            jx = rng.uniform(-0.06, 0.06, size=len(sh_vals[i]))
            ax.scatter(np.full(len(sh_vals[i]), x[i] - w / 2) + jx, sh_vals[i],
                       s=22, color=NAVY_DARK, edgecolor=WHITE, linewidth=0.6, zorder=5)
            ax.scatter(np.full(len(ba_vals[i]), x[i] + w / 2) + jx, ba_vals[i],
                       s=22, color=NAVY_DARK, edgecolor=WHITE, linewidth=0.6, zorder=5)

            # Clean non-overlapping mean annotations placed above bar+SD (or above max dot)
            top_sh = max(sh_m[i] + sh_s[i], max(sh_vals[i]))
            top_ba = max(ba_m[i] + ba_s[i], max(ba_vals[i]))
            pad_y = ymax * 0.032
            ax.text(x[i] - w / 2, top_sh + pad_y, fmt.format(sh_m[i]),
                    ha="center", va="bottom", fontsize=7.9, fontweight="bold", color=AMBER)
            ax.text(x[i] + w / 2, top_ba + pad_y, fmt.format(ba_m[i]),
                    ha="center", va="bottom", fontsize=7.9, fontweight="bold", color=TEAL)

        ax.set_xticks(x)
        ax.set_xticklabels(["H6 (85 Mbps flow)", "H5 (30 Mbps flow)"], fontsize=8.4)
        ax.set_ylabel(ylabel, fontweight="bold")
        ax.set_ylim(0, ymax)
        ax.set_title(title, fontsize=9.6, fontweight="bold", pad=8)
        style_axes(ax)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.99),
               ncol=2, frameon=True, facecolor=WHITE, edgecolor=BORDER, fontsize=8.6)
    fig.suptitle("Shared-Link Competing Workload Comparison — 2×3 Grid (n = 5 Matched Pairs, 64k HTB Burst)",
                 fontsize=10.6, fontweight="bold", color=NAVY_DARK, y=1.06)
    fig.tight_layout(rect=[0, 0, 1, 0.91], w_pad=1.6)
    save_fig(fig, "fig_5_2_grid_comparison.png")


def make_fig_5_3_ten_flows():
    rows = load_json("ten-flows-20261125T200721Z/summary.json")
    modes = [("ecmp", "ECMP\n(Static Hash)", TEAL),
             ("shortest", "Shortest Path\n(Static OSPF-like)", NAVY),
             ("balanced", "Balanced\n(Adaptive MBB)", AMBER)]

    means, sds, all_vals = [], [], []
    for m, _, _ in modes:
        sub = sorted([r for r in rows if r["mode"] == m], key=lambda r: r["pair"])
        v = [r["peak_tx_percent"] for r in sub]
        means.append(st.mean(v))
        sds.append(st.stdev(v))
        all_vals.append(v)

    fig, ax = plt.subplots(figsize=(8.8, 4.3))
    x = np.arange(len(modes))
    cols = [c for _, _, c in modes]
    ax.bar(x, means, width=0.46, color=cols, alpha=0.86, zorder=2)
    ax.errorbar(x, means, yerr=sds, fmt="none", ecolor=SLATE_DARK, capsize=5, lw=1.4, zorder=4)

    # Plot 5 paired dots with round offsets & faint connecting lines to reveal paired structure
    offsets = np.linspace(-0.12, 0.12, 5)
    round_colors = ["#0F2942", "#0F6E6E", "#C05621", "#6D28D9", "#15803D"]
    for r_i in range(5):
        xs_r = [x[m_i] + offsets[r_i] for m_i in range(3)]
        ys_r = [all_vals[m_i][r_i] for m_i in range(3)]
        ax.plot(xs_r, ys_r, color=BORDER, lw=0.8, ls=":", zorder=3)
        ax.scatter(xs_r, ys_r, s=36, color=round_colors[r_i], edgecolor=WHITE, lw=0.8, zorder=5,
                   label=f"Round {r_i+1}" if r_i < 5 else None)

    # 70% EWMA congestion threshold line (label placed on wide-open left above ECMP)
    ax.axhline(70.0, color=CRIMSON, lw=1.5, ls="--", zorder=3)
    ax.text(-0.48, 71.8, "70% Congestion Threshold (θ)", ha="left", va="bottom",
            fontsize=8.2, fontweight="bold", color=CRIMSON)

    # Value labels cleanly placed above max(mean+sd, max_dot)
    for i in range(3):
        top = max(means[i] + sds[i], max(all_vals[i]))
        ax.text(x[i], top + 2.2, f"{means[i]:.2f} ± {sds[i]:.2f}%",
                ha="center", va="bottom", fontsize=8.8, fontweight="bold", color=cols[i])

    ax.set_xticks(x)
    ax.set_xticklabels([lbl for _, lbl, _ in modes], fontsize=9.0, fontweight="bold")
    ax.set_ylabel("Peak Directional Link TX Utilization (%)", fontweight="bold")
    ax.set_ylim(0, 92)
    ax.set_xlim(-0.55, 2.55)
    ax.set_title("Ten-Flow Peak Inter-Switch Utilization Across Policies (144 Mbps Offered · n = 5 Matched Rounds)",
                 fontsize=10.0, fontweight="bold", pad=10)
    ax.legend(loc="upper left", ncol=5, frameon=True, facecolor=WHITE, edgecolor=BORDER,
              fontsize=7.4, columnspacing=0.9, handletextpad=0.3)

    ax.text(0.01, 0.03,
            "All policies delivered 144 Mbps aggregate rate; lost datagrams: Shortest 0/3.67M · ECMP 0/3.67M · Balanced 18/3.67M",
            transform=ax.transAxes, fontsize=7.6, color=SLATE,
            bbox=dict(boxstyle="round,pad=0.25", fc=BG_SOFT, ec=BORDER, lw=0.8))
    style_axes(ax)
    fig.tight_layout()
    save_fig(fig, "fig_5_3_ten_flows.png")


def make_fig_5_4_detection_threshold():
    det = load_json("shared-detection-20261125T203550Z/summary.json")
    thr = load_json("threshold-20261125T205244Z/summary.json")

    def vals(rows, mode):
        return [r["first_detection_seconds"]
                for r in sorted([x for x in rows if x["mode"] == mode], key=lambda x: x["pair"])
                if r["status"] == "detected"]

    v_t2 = vals(det, "T2")
    v_t5 = vals(det, "T5")
    v_60 = vals(thr, "theta60")
    v_80 = vals(thr, "theta80")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.2, 4.2))
    rng = np.random.default_rng(7)

    # Panel (a): Polling period T=2s vs T=5s at theta=70%
    p_vals = [v_t2, v_t5]
    p_lbls = ["T = 2 s\n(Fast Poll)", "T = 5 s\n(Default Poll)"]
    p_cols = [TEAL, NAVY]
    x1 = np.arange(2)
    m1 = [st.mean(v) for v in p_vals]
    s1 = [st.stdev(v) for v in p_vals]
    ax1.bar(x1, m1, width=0.45, color=p_cols, alpha=0.88, zorder=2)
    ax1.errorbar(x1, m1, yerr=s1, fmt="none", ecolor=SLATE_DARK, capsize=5, lw=1.3, zorder=4)
    for i, v in enumerate(p_vals):
        ax1.scatter(np.full(len(v), x1[i]) + rng.uniform(-0.07, 0.07, len(v)), v,
                    s=28, color=NAVY_DARK, edgecolor=WHITE, lw=0.7, zorder=5)
        ax1.text(x1[i], m1[i] + s1[i] + 0.65, f"{m1[i]:.2f} ± {s1[i]:.2f} s\n(5/5 detected)",
                 ha="center", va="bottom", fontsize=8.1, fontweight="bold", color=p_cols[i])
    # Delta callout
    ax1.annotate("Δ = +11.98 s\n(2.72× slower)", xy=(0.5, 13.0), ha="center", va="center",
                 fontsize=8.2, fontweight="bold", color=AMBER,
                 bbox=dict(boxstyle="round,pad=0.28", fc=AMBER_LIGHT, ec=AMBER, lw=1.0))
    ax1.set_xticks(x1)
    ax1.set_xticklabels(p_lbls, fontsize=8.8, fontweight="bold")
    ax1.set_ylabel("Time to First Congestion Declaration (s)", fontweight="bold")
    ax1.set_ylim(0, 23.5)
    ax1.set_title("(a) Effect of Polling Period T  (θ = 70%)", fontsize=9.6, fontweight="bold", pad=8)
    style_axes(ax1)

    # Panel (b): Threshold sensitivity at T=2s
    t_vals = [v_60, v_t2, v_80]
    t_lbls = ["θ = 60%", "θ = 70%\n(Default)", "θ = 80%"]
    t_cols = [EMERALD, TEAL, AMBER]
    x2 = np.arange(3)
    m2 = [st.mean(v) for v in t_vals]
    s2 = [st.stdev(v) for v in t_vals]
    ax2.bar(x2, m2, width=0.48, color=t_cols, alpha=0.88, zorder=2)
    ax2.errorbar(x2, m2, yerr=s2, fmt="none", ecolor=SLATE_DARK, capsize=5, lw=1.3, zorder=4)
    for i, v in enumerate(t_vals):
        ax2.scatter(np.full(len(v), x2[i]) + rng.uniform(-0.07, 0.07, len(v)), v,
                    s=28, color=NAVY_DARK, edgecolor=WHITE, lw=0.7, zorder=5)
        ax2.text(x2[i], m2[i] + s2[i] + 0.35, f"{m2[i]:.2f} ± {s2[i]:.2f} s\n(5/5)",
                 ha="center", va="bottom", fontsize=8.0, fontweight="bold", color=t_cols[i])
    ax2.set_xticks(x2)
    ax2.set_xticklabels(t_lbls, fontsize=8.8, fontweight="bold")
    ax2.set_ylabel("Time to First Congestion Declaration (s)", fontweight="bold")
    ax2.set_ylim(0, 11.8)
    ax2.set_title("(b) Effect of EWMA Threshold θ  (T = 2 s)", fontsize=9.6, fontweight="bold", pad=8)
    style_axes(ax2)

    fig.suptitle("Congestion Detection Latency on Shared Link S2–S3 (90 Mbps Offered · Two Consecutive EWMA Samples)",
                 fontsize=10.4, fontweight="bold", color=NAVY_DARK, y=1.01)
    fig.tight_layout(w_pad=2.0)
    save_fig(fig, "fig_5_4_detection_threshold.png")


def make_fig_5_5_route_phases():
    summary = load_json("route-phases-20261125T210721Z/summary.json")
    comps = []
    for row in summary:
        d = load_json("route-phases-20261125T210721Z/" + row["file"])
        comps.extend(c for c in d["phase_comparisons"] if set(c["phases"]) == {"before", "after"})

    pairs = [("h1", "h6", "H1→H6\n(n=5)"), ("h3", "h5", "H3→H5\n(n=5)"),
             ("h4", "h5", "H4→H5\n(n=3)"), ("h3", "h6", "H3→H6\n(n=1)")]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.8, 4.4))
    x = np.arange(len(pairs))
    w = 0.35
    rng = np.random.default_rng(11)

    for ax, key, title, ylabel, ymax, fmt in [
        (ax1, "mean_ping_rtt_ms", "(a) Ping Round-Trip Time (Before vs. After Move)", "Mean Ping RTT (ms)", 41.0, "{:.2f}"),
        (ax2, "mean_interval_jitter_ms", "(b) UDP Interval Jitter (Before vs. After Move)", "Mean Interval Jitter (ms)", 0.74, "{:.2f}"),
    ]:
        b_all, a_all = [], []
        for s, d, _ in pairs:
            sub = [c["phases"] for c in comps if c["src"] == s and c["dst"] == d]
            b_all.append([r["before"][key] for r in sub])
            a_all.append([r["after"][key] for r in sub])

        bm = [st.mean(v) for v in b_all]
        bs = [st.stdev(v) if len(v) > 1 else 0.0 for v in b_all]
        am = [st.mean(v) for v in a_all]
        as_ = [st.stdev(v) if len(v) > 1 else 0.0 for v in a_all]

        ax.bar(x - w / 2, bm, width=w, color=NAVY, alpha=0.88, label="Before First Move", zorder=2)
        ax.bar(x + w / 2, am, width=w, color=TEAL, alpha=0.90, label="After First Move", zorder=2)
        for i in range(len(pairs)):
            if len(b_all[i]) > 1:
                ax.errorbar(x[i] - w / 2, bm[i], yerr=bs[i], fmt="none", ecolor=SLATE_DARK, capsize=3.5, lw=1.1, zorder=4)
                ax.errorbar(x[i] + w / 2, am[i], yerr=as_[i], fmt="none", ecolor=SLATE_DARK, capsize=3.5, lw=1.1, zorder=4)
            ax.scatter(np.full(len(b_all[i]), x[i] - w / 2) + rng.uniform(-0.05, 0.05, len(b_all[i])),
                       b_all[i], s=20, color=AMBER, edgecolor=WHITE, lw=0.5, zorder=5)
            ax.scatter(np.full(len(a_all[i]), x[i] + w / 2) + rng.uniform(-0.05, 0.05, len(a_all[i])),
                       a_all[i], s=20, color=AMBER, edgecolor=WHITE, lw=0.5, zorder=5)

            top_b = max(bm[i] + bs[i], max(b_all[i]))
            top_a = max(am[i] + as_[i], max(a_all[i]))
            pad = ymax * 0.025
            ax.text(x[i] - w / 2, top_b + pad, fmt.format(bm[i]),
                    ha="center", va="bottom", fontsize=7.6, fontweight="bold", color=NAVY_DARK)
            ax.text(x[i] + w / 2, top_a + pad, fmt.format(am[i]),
                    ha="center", va="bottom", fontsize=7.6, fontweight="bold", color=TEAL)

        ax.set_xticks(x)
        ax.set_xticklabels([lbl for _, _, lbl in pairs], fontsize=8.4, fontweight="bold")
        ax.set_ylabel(ylabel, fontweight="bold")
        ax.set_ylim(0, ymax)
        ax.set_title(title, fontsize=9.4, fontweight="bold", pad=8)
        style_axes(ax)

    handles, labels = ax1.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.985),
               ncol=2, frameon=True, facecolor=WHITE, edgecolor=BORDER, fontsize=8.5)
    fig.text(0.5, 0.01,
             "All 14 paired 5-second windows observed 0.00% UDP packet loss and steady near-offered throughput (H1→H6: 27.96→28.00, H3→H5: 28.00→28.00, H4→H5: 17.99→17.98, H3→H6: 16.00→16.00 Mbps).",
             ha="center", va="bottom", fontsize=7.6, color=SLATE,
             bbox=dict(boxstyle="round,pad=0.25", fc=BG_SOFT, ec=BORDER, lw=0.8))
    fig.suptitle("Before-vs.-After Rerouting Metrics Across 14 Paired Flow Moves (90 Mbps Four-Flow Workload)",
                 fontsize=10.5, fontweight="bold", color=NAVY_DARK, y=1.05)
    fig.tight_layout(rect=[0, 0.06, 1, 0.91], w_pad=1.8)
    save_fig(fig, "fig_5_5_route_phases.png")


def make_fig_5_6_failover_recovery():
    rec = load_json("recovery-20261125T202848Z/summary.json")
    runs = np.arange(1, len(rec) + 1)
    times = [r["first_post_cut_reply_ms"] for r in rec]
    lost = [r["lost"] for r in rec]
    mean_t = st.mean(times)
    sd_t = st.stdev(times)
    total_lost = sum(lost)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.2, 4.1), gridspec_kw={"width_ratios": [1.2, 1.0]})

    # Panel (a): Recovery time per run + Mean ± SD band
    ax1.axhspan(mean_t - sd_t, mean_t + sd_t, color=TEAL_LIGHT, alpha=0.85, zorder=1,
                label=f"±1 SD Band ({sd_t:.2f} ms)")
    ax1.axhline(mean_t, color=TEAL, lw=1.7, ls="--", zorder=2, label=f"Mean ({mean_t:.2f} ms)")
    bars = ax1.bar(runs, times, width=0.48, color=NAVY, alpha=0.88, zorder=3)
    for b, val in zip(bars, times):
        ax1.text(b.get_x() + b.get_width() / 2, val + 2.2, f"{val:.2f} ms",
                 ha="center", va="bottom", fontsize=8.0, fontweight="bold", color=NAVY_DARK)
    ax1.set_xticks(runs)
    ax1.set_xticklabels([f"Run {i}" for i in runs])
    ax1.set_ylabel("First Post-Cut Qualifying Reply (ms)", fontweight="bold")
    ax1.set_ylim(0, 118)
    ax1.set_title("(a) Host-Observed Recovery Time (S5–S6 Cut)", fontsize=9.6, fontweight="bold", pad=8)
    ax1.legend(loc="upper right", frameon=True, facecolor=WHITE, edgecolor=BORDER, fontsize=7.8)
    style_axes(ax1)

    # Panel (b): Probes lost per run
    cols2 = [AMBER if l > 0 else EMERALD for l in lost]
    bars2 = ax2.bar(runs, lost, width=0.48, color=cols2, alpha=0.90, zorder=3)
    for b, val in zip(bars2, lost):
        ax2.text(b.get_x() + b.get_width() / 2, val + 0.12, f"{val} lost",
                 ha="center", va="bottom", fontsize=8.2, fontweight="bold",
                 color=AMBER if val > 0 else EMERALD)
    ax2.set_xticks(runs)
    ax2.set_xticklabels([f"Run {i}" for i in runs])
    ax2.set_ylabel("Lost ICMP Probes (out of 260 / run)", fontweight="bold")
    ax2.set_ylim(0, 3.3)
    ax2.set_yticks([0, 1, 2, 3])
    ax2.set_title("(b) ICMP Probe Loss per Trial (50 ms Interval)", fontsize=9.6, fontweight="bold", pad=8)
    ax2.text(0.5, 0.87, f"Total: {total_lost} / 1,300 probes lost (99.46% delivered)\nAll 5 runs rerouted via S4–S1–S2–S3–S6",
             transform=ax2.transAxes, ha="center", va="center", fontsize=7.8, fontweight="bold",
             color=TEAL, bbox=dict(boxstyle="round,pad=0.28", fc=TEAL_LIGHT, ec=TEAL, lw=0.9))
    style_axes(ax2)

    fig.suptitle("Automatic Link-Failure Recovery — 2×3 Grid (H2→H6 · S5–S6 Down · n = 5 Trials)",
                 fontsize=10.6, fontweight="bold", color=NAVY_DARK, y=1.01)
    fig.tight_layout(w_pad=2.0)
    save_fig(fig, "fig_5_6_failover_recovery.png")


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    prepare_screenshots()

    print("[Part B] Generating 300 DPI technical diagrams...")
    make_fig_2_1_trad_vs_sdn()
    make_fig_2_2_sdn_3layer()
    make_fig_2_3_of13_pipeline()
    make_fig_3_1_controller_modules()
    make_fig_3_2_topologies()
    make_fig_3_3_lb_flowchart()
    make_fig_3_4_mbb_sequence()

    print("[Part C] Generating 300 DPI Nov 25-26 experiment figures...")
    make_fig_5_1_c4_accuracy()
    make_fig_5_2_grid_comparison()
    make_fig_5_3_ten_flows()
    make_fig_5_4_detection_threshold()
    make_fig_5_5_route_phases()
    make_fig_5_6_failover_recovery()

    files = sorted(ASSETS.glob("*.png"))
    print(f"\nGenerated {len(files)} assets in {ASSETS}:")
    for p in files:
        im = Image.open(p)
        print(f"  {p.name:40s} {im.width:4d}x{im.height:<4d} ({p.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
