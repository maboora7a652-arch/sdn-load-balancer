(function () {
  "use strict";

  var api = window.SDN_VIDEO;
  if (!api) {
    throw new Error("grid-svg.js must be loaded after engine.js");
  }

  var COLORS = api.COLORS;
  var svgEl = api.dom.svgEl;
  var clamp = api.math.clamp;

  var diagramCounter = 0;

  // Exact 6-switch / 7-link / 6-host Lab Grid coordinates (ViewBox 0 0 960 620)
  var SWITCH_POS = {
    S1: [190, 240],
    S2: [480, 240],
    S3: [770, 240],
    S4: [190, 425],
    S5: [480, 425],
    S6: [770, 425]
  };

  var HOST_INFO = {
    H1: { sw: "S1", swPort: "p3", ip: "10.0.0.1", x: 190, y: 132, top: true },
    H3: { sw: "S2", swPort: "p4", ip: "10.0.0.3", x: 480, y: 132, top: true },
    H5: { sw: "S3", swPort: "p3", ip: "10.0.0.5", x: 770, y: 132, top: true },
    H2: { sw: "S4", swPort: "p3", ip: "10.0.0.2", x: 190, y: 534, top: false },
    H4: { sw: "S5", swPort: "p4", ip: "10.0.0.4", x: 480, y: 534, top: false },
    H6: { sw: "S6", swPort: "p3", ip: "10.0.0.6", x: 770, y: 534, top: false }
  };

  var LINK_DEFS = [
    { id: "S1-S2", a: "S1", b: "S2", pa: "p1", pb: "p1" },
    { id: "S2-S3", a: "S2", b: "S3", pa: "p2", pb: "p1" },
    { id: "S3-S6", a: "S3", b: "S6", pa: "p2", pb: "p1" },
    { id: "S5-S6", a: "S5", b: "S6", pa: "p1", pb: "p2" },
    { id: "S2-S5", a: "S2", b: "S5", pa: "p3", pb: "p2" },
    { id: "S4-S5", a: "S4", b: "S5", pa: "p1", pb: "p3" },
    { id: "S1-S4", a: "S1", b: "S4", pa: "p2", pb: "p2" }
  ];

  function normalizeLinkId(id) {
    if (!id) return "";
    var parts = String(id).trim().toUpperCase().split("-");
    if (parts.length !== 2) return String(id).trim().toUpperCase();
    var a = parts[0], b = parts[1];
    return a < b ? (a + "-" + b) : (b + "-" + a);
  }

  function getNodeCoords(nodeId) {
    var k = String(nodeId).toUpperCase();
    if (SWITCH_POS[k]) return SWITCH_POS[k];
    if (HOST_INFO[k]) return [HOST_INFO[k].x, HOST_INFO[k].y];
    return null;
  }

  function createGridDiagram(opts) {
    var cfg = opts || {};
    var showController = Boolean(cfg.showController);
    var showPorts = cfg.showPorts !== false;
    var showIPs = cfg.showIPs !== false;
    var uid = "gd" + (++diagramCounter);

    var svg = svgEl("svg", {
      viewBox: "0 0 960 620",
      preserveAspectRatio: "xMidYMid meet",
      width: "100%",
      height: "100%",
      style: { display: "block", overflow: "visible" }
    });

    // Unique per-diagram SVG glow filters
    var defs = svgEl("defs");
    var glowColors = {
      emerald: COLORS.emerald,
      amber: COLORS.amber,
      crimson: COLORS.crimson,
      cyan: COLORS.cyan
    };

    Object.keys(glowColors).forEach(function (name) {
      var flt = svgEl("filter", {
        id: uid + "-glow-" + name,
        x: "-45%",
        y: "-45%",
        width: "190%",
        height: "190%"
      });
      flt.appendChild(svgEl("feGaussianBlur", { stdDeviation: "4.5", result: "blur" }));
      var merge = svgEl("feMerge");
      merge.appendChild(svgEl("feMergeNode", { in: "blur" }));
      merge.appendChild(svgEl("feMergeNode", { in: "SourceGraphic" }));
      flt.appendChild(merge);
      defs.appendChild(flt);
    });
    svg.appendChild(defs);

    // Subtle backing container grid frame inside SVG
    var layerControl = svgEl("g", { class: "layer-control" });
    var layerHostLinks = svgEl("g", { class: "layer-host-links" });
    var layerLinks = svgEl("g", { class: "layer-links" });
    var layerPackets = svgEl("g", { class: "layer-packets" });
    var layerCuts = svgEl("g", { class: "layer-cuts" });
    var layerSwitches = svgEl("g", { class: "layer-switches" });
    var layerHosts = svgEl("g", { class: "layer-hosts" });
    var layerBadges = svgEl("g", { class: "layer-badges" });

    svg.appendChild(layerControl);
    svg.appendChild(layerHostLinks);
    svg.appendChild(layerLinks);
    svg.appendChild(layerPackets);
    svg.appendChild(layerCuts);
    svg.appendChild(layerSwitches);
    svg.appendChild(layerHosts);
    svg.appendChild(layerBadges);

    // Optional Controller banner at top (y = 4..50, clear of top host pills)
    var ctrlRefs = null;
    if (showController) {
      var ctrlLines = [];
      ["S1", "S2", "S3"].forEach(function (sid) {
        var sp = SWITCH_POS[sid];
        var l = svgEl("path", {
          d: "M 480 50 C 480 86, " + sp[0] + " 78, " + sp[0] + " " + (sp[1] - 28),
          fill: "none",
          stroke: COLORS.cyan,
          "stroke-width": "1.6",
          "stroke-dasharray": "6 6",
          opacity: "0.34"
        });
        layerControl.appendChild(l);
        ctrlLines.push(l);
      });

      var ctrlG = svgEl("g", { class: "controller-node" });
      var ctrlRect = svgEl("rect", {
        x: 292,
        y: 4,
        width: 376,
        height: 46,
        rx: 12,
        fill: "#0B2427",
        stroke: COLORS.cyan,
        "stroke-width": "2"
      });
      var ctrlText = svgEl("text", {
        x: 480,
        y: 33,
        "text-anchor": "middle",
        fill: COLORS.text,
        "font-family": "var(--font-mono)",
        "font-size": "18",
        "font-weight": "700",
        "letter-spacing": "0.06em"
      }, "OS-KEN 3.1.1 · OPENFLOW 1.3");
      ctrlG.appendChild(ctrlRect);
      ctrlG.appendChild(ctrlText);
      layerControl.appendChild(ctrlG);
      ctrlRefs = { group: ctrlG, rect: ctrlRect, text: ctrlText, lines: ctrlLines };
    }

    // Build 7 inter-switch links
    var linkMap = {};
    LINK_DEFS.forEach(function (def) {
      var pA = SWITCH_POS[def.a];
      var pB = SWITCH_POS[def.b];
      var dx = pB[0] - pA[0];
      var dy = pB[1] - pA[1];
      var len = Math.hypot(dx, dy);
      var mx = (pA[0] + pB[0]) / 2;
      var my = (pA[1] + pB[1]) / 2;
      var isHoriz = Math.abs(dy) < 1;

      var g = svgEl("g", { class: "link-group", "data-link": def.id });

      var glowLine = svgEl("line", {
        x1: pA[0], y1: pA[1], x2: pB[0], y2: pB[1],
        stroke: COLORS.emerald,
        "stroke-width": "10",
        "stroke-linecap": "round",
        opacity: "0"
      });

      var mainLine = svgEl("line", {
        x1: pA[0], y1: pA[1], x2: pB[0], y2: pB[1],
        stroke: COLORS.linkIdle,
        "stroke-width": "3.5",
        "stroke-linecap": "round",
        opacity: "1"
      });

      g.appendChild(glowLine);
      g.appendChild(mainLine);

      // Port micro-labels near each switch endpoint
      if (showPorts) {
        var ux = dx / len;
        var uy = dy / len;
        var off = isHoriz ? 58 : 42;
        var nx = isHoriz ? 0 : -18;
        var ny = isHoriz ? -12 : 4;
        g.appendChild(svgEl("text", {
          x: pA[0] + ux * off + nx,
          y: pA[1] + uy * off + ny,
          "text-anchor": "middle",
          fill: COLORS.textMuted,
          opacity: "0.75",
          "font-family": "var(--font-mono)",
          "font-size": "14",
          "font-weight": "600"
        }, def.pa));
        g.appendChild(svgEl("text", {
          x: pB[0] - ux * off + nx,
          y: pB[1] - uy * off + ny,
          "text-anchor": "middle",
          fill: COLORS.textMuted,
          opacity: "0.75",
          "font-family": "var(--font-mono)",
          "font-size": "14",
          "font-weight": "600"
        }, def.pb));
      }

      // Dynamic link telemetry label pill (hidden unless label text provided)
      var labelG = svgEl("g", { opacity: "0" });
      var labelY = isHoriz ? my - 22 : my;
      var labelX = isHoriz ? mx : mx + (def.a === "S1" ? -48 : (def.a === "S3" ? 48 : 50));
      var labelRect = svgEl("rect", {
        x: labelX - 58,
        y: labelY - 14,
        width: 116,
        height: 28,
        rx: 7,
        fill: "#091513",
        stroke: COLORS.border,
        "stroke-width": "1.5"
      });
      var labelText = svgEl("text", {
        x: labelX,
        y: labelY + 5,
        "text-anchor": "middle",
        fill: COLORS.text,
        "font-family": "var(--font-mono)",
        "font-size": "15",
        "font-weight": "700"
      }, "");
      labelG.appendChild(labelRect);
      labelG.appendChild(labelText);
      g.appendChild(labelG);

      layerLinks.appendChild(g);

      // Cut indicator (crimson gap + X slash + clean below-circle status badge)
      var cutG = svgEl("g", { opacity: "0" });
      var cutBg = svgEl("circle", {
        cx: mx, cy: my, r: 21,
        fill: "#1B090B",
        stroke: COLORS.crimson,
        "stroke-width": "2.5"
      });
      var cutSlash1 = svgEl("line", {
        x1: mx - 12, y1: my - 12, x2: mx + 12, y2: my + 12,
        stroke: COLORS.crimson,
        "stroke-width": "4.5",
        "stroke-linecap": "round"
      });
      var cutSlash2 = svgEl("line", {
        x1: mx + 12, y1: my - 12, x2: mx - 12, y2: my + 12,
        stroke: COLORS.crimson,
        "stroke-width": "4.5",
        "stroke-linecap": "round"
      });
      var cutLabelY = my + 39;
      var cutLabelRect = svgEl("rect", {
        x: mx - 56,
        y: cutLabelY - 12,
        width: 112,
        height: 24,
        rx: 7,
        fill: "#1B090B",
        stroke: COLORS.crimson,
        "stroke-width": "1.6"
      });
      var cutLabelText = svgEl("text", {
        x: mx,
        y: cutLabelY + 5,
        "text-anchor": "middle",
        fill: "#FCA5A5",
        "font-family": "var(--font-mono)",
        "font-size": "14",
        "font-weight": "700"
      }, def.id.replace("-", "–") + " CUT");
      cutG.appendChild(cutBg);
      cutG.appendChild(cutSlash1);
      cutG.appendChild(cutSlash2);
      cutG.appendChild(cutLabelRect);
      cutG.appendChild(cutLabelText);
      layerCuts.appendChild(cutG);

      linkMap[def.id] = {
        def: def,
        len: len,
        mx: mx,
        my: my,
        labelX: labelX,
        labelY: labelY,
        glowLine: glowLine,
        mainLine: mainLine,
        labelG: labelG,
        labelRect: labelRect,
        labelText: labelText,
        cutG: cutG,
        cutBg: cutBg,
        cutSlash1: cutSlash1,
        cutSlash2: cutSlash2,
        cutLabelRect: cutLabelRect,
        cutLabelText: cutLabelText,
        cutProgress: 0,
        lastLabel: ""
      };
    });

    // Build 6 host-to-switch access links & host nodes
    var hostMap = {};
    Object.keys(HOST_INFO).forEach(function (hid) {
      var info = HOST_INFO[hid];
      var sp = SWITCH_POS[info.sw];
      var accessLine = svgEl("line", {
        x1: sp[0], y1: sp[1], x2: info.x, y2: info.y,
        stroke: COLORS.linkIdle,
        "stroke-width": "2.5",
        opacity: "0.78"
      });
      layerHostLinks.appendChild(accessLine);

      var g = svgEl("g", { class: "host-node", "data-host": hid });
      var ring = svgEl("circle", {
        cx: info.x, cy: info.y, r: 28,
        fill: "none",
        stroke: COLORS.emerald,
        "stroke-width": "2.5",
        opacity: "0"
      });
      var circle = svgEl("circle", {
        cx: info.x, cy: info.y, r: 22,
        fill: "#0D1E1A",
        stroke: COLORS.switchStroke,
        "stroke-width": "2.5"
      });
      var text = svgEl("text", {
        x: info.x, y: info.y + 7,
        "text-anchor": "middle",
        fill: COLORS.text,
        "font-family": "var(--font-mono)",
        "font-size": "19",
        "font-weight": "700"
      }, hid);

      g.appendChild(ring);
      g.appendChild(circle);
      g.appendChild(text);

      if (showIPs) {
        g.appendChild(svgEl("text", {
          x: info.x,
          y: info.top ? info.y - 30 : info.y + 40,
          "text-anchor": "middle",
          fill: COLORS.textMuted,
          "font-family": "var(--font-mono)",
          "font-size": "14",
          "font-weight": "600"
        }, info.ip + " (" + info.swPort + ")"));
      }

      // Optional traffic rate pill beside host (12px clear gap from IP label when showIPs=true)
      var rateG = svgEl("g", { opacity: "0" });
      var rateY = info.top
        ? (showIPs ? info.y - 66 : info.y - 46)
        : (showIPs ? info.y + 66 : info.y + 46);
      var rateRect = svgEl("rect", {
        x: info.x - 54,
        y: rateY - 13,
        width: 108,
        height: 26,
        rx: 7,
        fill: "#0A1A16",
        stroke: COLORS.emerald,
        "stroke-width": "1.5"
      });
      var rateText = svgEl("text", {
        x: info.x,
        y: rateY + 5,
        "text-anchor": "middle",
        fill: COLORS.emeraldBright,
        "font-family": "var(--font-mono)",
        "font-size": "15",
        "font-weight": "700"
      }, "");
      rateG.appendChild(rateRect);
      rateG.appendChild(rateText);
      g.appendChild(rateG);

      layerHosts.appendChild(g);
      hostMap[hid] = {
        info: info,
        accessLine: accessLine,
        ring: ring,
        circle: circle,
        text: text,
        rateG: rateG,
        rateRect: rateRect,
        rateText: rateText
      };
    });

    // Build 6 switches (S1..S6)
    var switchMap = {};
    Object.keys(SWITCH_POS).forEach(function (sid) {
      var pos = SWITCH_POS[sid];
      var x = pos[0], y = pos[1];
      var g = svgEl("g", { class: "switch-node", "data-switch": sid });

      var rect = svgEl("rect", {
        x: x - 46,
        y: y - 26,
        width: 92,
        height: 52,
        rx: 11,
        fill: "#0F221E",
        stroke: COLORS.switchStroke,
        "stroke-width": "2.8"
      });

      var innerDotL = svgEl("circle", { cx: x - 31, cy: y, r: 3.2, fill: COLORS.linkIdle });
      var innerDotR = svgEl("circle", { cx: x + 31, cy: y, r: 3.2, fill: COLORS.linkIdle });

      var label = svgEl("text", {
        x: x,
        y: y + 8,
        "text-anchor": "middle",
        fill: COLORS.text,
        "font-family": "var(--font-mono)",
        "font-size": "22",
        "font-weight": "700"
      }, sid);

      // Floating priority / status badge centered outward (above top row S1..S3, below bottom row S4..S6)
      // Guarantees zero overlap with port labels (p1/p2/p3) and horizontal link labels
      var isTopRow = y < 330;
      var badgeCy = isTopRow ? (y - 45) : (y + 45);
      var badgeG = svgEl("g", { opacity: "0" });
      var badgeRect = svgEl("rect", {
        x: x - 34,
        y: badgeCy - 12,
        width: 68,
        height: 24,
        rx: 7,
        fill: COLORS.emeraldFill,
        stroke: COLORS.emeraldBright,
        "stroke-width": "1.6"
      });
      var badgeText = svgEl("text", {
        x: x,
        y: badgeCy + 5,
        "text-anchor": "middle",
        fill: COLORS.text,
        "font-family": "var(--font-mono)",
        "font-size": "14",
        "font-weight": "700"
      }, "");
      badgeG.appendChild(badgeRect);
      badgeG.appendChild(badgeText);

      g.appendChild(rect);
      g.appendChild(innerDotL);
      g.appendChild(innerDotR);
      g.appendChild(label);
      g.appendChild(badgeG);
      layerSwitches.appendChild(g);

      switchMap[sid] = {
        x: x,
        y: y,
        badgeCy: badgeCy,
        group: g,
        rect: rect,
        dotL: innerDotL,
        dotR: innerDotR,
        label: label,
        badgeG: badgeG,
        badgeRect: badgeRect,
        badgeText: badgeText
      };
    });

    // Packet stream pools (up to 12 deterministic dots per streamKey)
    var packetPools = {};
    var MAX_PACKETS = 12;

    function getPacketPool(streamKey) {
      if (packetPools[streamKey]) return packetPools[streamKey];
      var g = svgEl("g", { class: "packet-stream", "data-stream": streamKey });
      var dots = [];
      for (var i = 0; i < MAX_PACKETS; i++) {
        var c = svgEl("circle", {
          cx: -100, cy: -100, r: 6,
          fill: COLORS.emeraldBright,
          opacity: "0"
        });
        g.appendChild(c);
        dots.push(c);
      }
      layerPackets.appendChild(g);
      packetPools[streamKey] = { group: g, dots: dots };
      return packetPools[streamKey];
    }

    // Flexible floating badges (keyed by id)
    var badgePool = {};

    function glowFilterFor(colorOrName) {
      if (!colorOrName) return "";
      var s = String(colorOrName).toLowerCase();
      if (s === "emerald" || s === COLORS.emerald.toLowerCase() || s === COLORS.emeraldBright.toLowerCase()) {
        return "url(#" + uid + "-glow-emerald)";
      }
      if (s === "amber" || s === COLORS.amber.toLowerCase() || s === COLORS.amberFill.toLowerCase()) {
        return "url(#" + uid + "-glow-amber)";
      }
      if (s === "crimson" || s === COLORS.crimson.toLowerCase()) {
        return "url(#" + uid + "-glow-crimson)";
      }
      if (s === "cyan" || s === COLORS.cyan.toLowerCase()) {
        return "url(#" + uid + "-glow-cyan)";
      }
      return "url(#" + uid + "-glow-emerald)";
    }

    function updateLink(id, o) {
      var key = normalizeLinkId(id);
      var item = linkMap[key];
      if (!item) return;
      var optsObj = o || {};
      var color = optsObj.color || COLORS.linkIdle;
      var width = optsObj.width !== undefined ? optsObj.width : 3.5;
      var opacity = optsObj.opacity !== undefined ? clamp(optsObj.opacity, 0, 1) : 1;

      item.mainLine.setAttribute("stroke", color);
      item.mainLine.setAttribute("stroke-width", String(width));
      item.mainLine.setAttribute("opacity", opacity.toFixed(4));

      if (optsObj.dashed) {
        item.mainLine.setAttribute("stroke-dasharray", typeof optsObj.dashed === "string" ? optsObj.dashed : "12 8");
        item.mainLine.setAttribute("stroke-dashoffset", String(optsObj.dashOffset || 0));
      } else if (optsObj.drawProgress !== undefined) {
        var dp = clamp(optsObj.drawProgress, 0, 1);
        item.mainLine.setAttribute("stroke-dasharray", item.len.toFixed(2));
        item.mainLine.setAttribute("stroke-dashoffset", (item.len * (1 - dp)).toFixed(2));
      } else {
        item.mainLine.removeAttribute("stroke-dasharray");
        item.mainLine.removeAttribute("stroke-dashoffset");
      }

      if (optsObj.glow) {
        var gColor = typeof optsObj.glow === "string" ? (
          optsObj.glow === "emerald" ? COLORS.emerald :
          optsObj.glow === "amber" ? COLORS.amber :
          optsObj.glow === "crimson" ? COLORS.crimson :
          optsObj.glow === "cyan" ? COLORS.cyan : optsObj.glow
        ) : color;
        item.glowLine.setAttribute("stroke", gColor);
        item.glowLine.setAttribute("stroke-width", String(width + 7));
        item.glowLine.setAttribute("opacity", (opacity * 0.34).toFixed(4));
        item.glowLine.setAttribute("filter", glowFilterFor(optsObj.glow === true ? color : optsObj.glow));
        if (optsObj.drawProgress !== undefined) {
          var dpG = clamp(optsObj.drawProgress, 0, 1);
          item.glowLine.setAttribute("stroke-dasharray", item.len.toFixed(2));
          item.glowLine.setAttribute("stroke-dashoffset", (item.len * (1 - dpG)).toFixed(2));
        } else {
          item.glowLine.removeAttribute("stroke-dasharray");
          item.glowLine.removeAttribute("stroke-dashoffset");
        }
      } else {
        item.glowLine.setAttribute("opacity", "0");
        item.glowLine.removeAttribute("filter");
      }

      item.lastLabel = optsObj.label ? String(optsObj.label) : "";
      if (item.lastLabel && item.cutProgress <= 0.01) {
        var txt = item.lastLabel;
        var w = Math.max(82, txt.length * 10 + 24);
        item.labelRect.setAttribute("x", (item.labelX - w / 2).toFixed(1));
        item.labelRect.setAttribute("width", w.toFixed(1));
        item.labelRect.setAttribute("stroke", optsObj.labelColor || color);
        item.labelText.textContent = txt;
        item.labelText.setAttribute("fill", optsObj.labelColor || COLORS.text);
        item.labelG.setAttribute("opacity", opacity.toFixed(4));
      } else {
        item.labelG.setAttribute("opacity", "0");
      }
      if (item.cutProgress > 0.01) {
        refreshCutBadge(item);
      }
    }

    function refreshCutBadge(item) {
      var raw = item.lastLabel ? item.lastLabel.trim() : "";
      var prefix = item.def.id.replace("-", "–");
      var text = !raw ? (prefix + " CUT") : (raw.length <= 5 ? (prefix + " " + raw) : raw);
      var w = Math.max(96, text.length * 9.5 + 22);
      item.cutLabelRect.setAttribute("x", (item.mx - w / 2).toFixed(1));
      item.cutLabelRect.setAttribute("width", w.toFixed(1));
      item.cutLabelText.textContent = text;
    }

    function updateSwitch(id, o) {
      var item = switchMap[String(id).toUpperCase()];
      if (!item) return;
      var optsObj = o || {};
      var stroke = optsObj.stroke || COLORS.switchStroke;
      var fill = optsObj.fill || "#0F221E";
      var scale = optsObj.scale !== undefined ? optsObj.scale : 1;

      item.rect.setAttribute("stroke", stroke);
      item.rect.setAttribute("fill", fill);
      item.dotL.setAttribute("fill", stroke);
      item.dotR.setAttribute("fill", stroke);

      if (optsObj.glow) {
        item.rect.setAttribute("filter", glowFilterFor(optsObj.glow === true ? stroke : optsObj.glow));
      } else {
        item.rect.removeAttribute("filter");
      }

      if (Math.abs(scale - 1) > 0.0005) {
        item.group.setAttribute(
          "transform",
          "translate(" + item.x + " " + item.y + ") scale(" + scale.toFixed(4) + ") translate(" + (-item.x) + " " + (-item.y) + ")"
        );
      } else {
        item.group.removeAttribute("transform");
      }

      var bOp = optsObj.badgeOpacity !== undefined ? clamp(optsObj.badgeOpacity, 0, 1) : (optsObj.badgeText ? 1 : 0);
      if (optsObj.badgeText && bOp > 0.001) {
        var bt = String(optsObj.badgeText);
        var bw = Math.max(52, bt.length * 9.5 + 18);
        var bc = optsObj.badgeColor || COLORS.emerald;
        item.badgeRect.setAttribute("x", (item.x - bw / 2).toFixed(1));
        item.badgeRect.setAttribute("width", bw.toFixed(1));
        item.badgeRect.setAttribute("fill", "#081714");
        item.badgeRect.setAttribute("stroke", bc);
        item.badgeText.setAttribute("x", item.x.toFixed(1));
        item.badgeText.setAttribute("fill", bc);
        item.badgeText.textContent = bt;
        item.badgeG.setAttribute("opacity", bOp.toFixed(4));
      } else {
        item.badgeG.setAttribute("opacity", "0");
      }
    }

    function updateHost(id, o) {
      var item = hostMap[String(id).toUpperCase()];
      if (!item) return;
      var optsObj = o || {};
      var active = Boolean(optsObj.active);
      var color = optsObj.color || COLORS.emerald;

      item.circle.setAttribute("stroke", active ? color : COLORS.switchStroke);
      item.circle.setAttribute("fill", active ? "#102A23" : "#0D1E1A");
      item.accessLine.setAttribute("stroke", active ? color : COLORS.linkIdle);
      item.accessLine.setAttribute("stroke-width", active ? "3.2" : "2.5");
      item.ring.setAttribute("stroke", color);
      item.ring.setAttribute("opacity", active ? "0.45" : "0");
      if (active) {
        item.ring.setAttribute("filter", glowFilterFor(color));
      } else {
        item.ring.removeAttribute("filter");
      }

      if (optsObj.rateText) {
        var rt = String(optsObj.rateText);
        var rw = Math.max(88, rt.length * 10 + 22);
        item.rateRect.setAttribute("x", (item.info.x - rw / 2).toFixed(1));
        item.rateRect.setAttribute("width", rw.toFixed(1));
        item.rateRect.setAttribute("stroke", color);
        item.rateText.setAttribute("fill", color);
        item.rateText.textContent = rt;
        item.rateG.setAttribute("opacity", "1");
      } else {
        item.rateG.setAttribute("opacity", "0");
      }
    }

    function setPackets(streamKey, waypoints, o) {
      var pool = getPacketPool(streamKey || "default");
      var optsObj = o || {};
      var opacity = optsObj.opacity !== undefined ? clamp(optsObj.opacity, 0, 1) : 1;
      var count = Math.min(MAX_PACKETS, Math.max(0, Math.floor(optsObj.count !== undefined ? optsObj.count : 6)));

      if (!waypoints || waypoints.length < 2 || opacity <= 0.001 || count === 0) {
        for (var k = 0; k < MAX_PACKETS; k++) pool.dots[k].setAttribute("opacity", "0");
        return;
      }

      // Build polyline segments
      var pts = [];
      for (var p = 0; p < waypoints.length; p++) {
        var c = Array.isArray(waypoints[p]) ? waypoints[p] : getNodeCoords(waypoints[p]);
        if (c) pts.push(c);
      }
      if (pts.length < 2) {
        for (var z = 0; z < MAX_PACKETS; z++) pool.dots[z].setAttribute("opacity", "0");
        return;
      }

      var segLens = [];
      var totalLen = 0;
      for (var s = 0; s < pts.length - 1; s++) {
        var sl = Math.hypot(pts[s + 1][0] - pts[s][0], pts[s + 1][1] - pts[s][1]);
        segLens.push(sl);
        totalLen += sl;
      }
      if (totalLen <= 0.001) return;

      var t = Number(optsObj.t) || 0;
      var speed = optsObj.speed !== undefined ? Number(optsObj.speed) : 0.42;
      var color = optsObj.color || COLORS.emeraldBright;
      var radius = optsObj.radius !== undefined ? Number(optsObj.radius) : 6;
      var filterVal = glowFilterFor(color);

      for (var i = 0; i < MAX_PACKETS; i++) {
        var dot = pool.dots[i];
        if (i >= count) {
          dot.setAttribute("opacity", "0");
          continue;
        }
        var raw = (t * speed + i / count) % 1;
        var frac = raw < 0 ? raw + 1 : raw;
        var dist = frac * totalLen;

        var acc = 0;
        var px = pts[0][0], py = pts[0][1];
        for (var j = 0; j < segLens.length; j++) {
          if (dist <= acc + segLens[j] || j === segLens.length - 1) {
            var localFrac = segLens[j] > 0 ? clamp((dist - acc) / segLens[j], 0, 1) : 0;
            px = pts[j][0] + (pts[j + 1][0] - pts[j][0]) * localFrac;
            py = pts[j][1] + (pts[j + 1][1] - pts[j][1]) * localFrac;
            break;
          }
          acc += segLens[j];
        }

        // Smooth edge fade near host endpoints so packets never pop abruptly
        var edgeFade = Math.min(1, frac / 0.07, (1 - frac) / 0.07);
        dot.setAttribute("cx", px.toFixed(2));
        dot.setAttribute("cy", py.toFixed(2));
        dot.setAttribute("r", String(radius));
        dot.setAttribute("fill", color);
        dot.setAttribute("filter", filterVal);
        dot.setAttribute("opacity", (opacity * clamp(edgeFade, 0, 1)).toFixed(4));
      }
    }

    function setCut(linkId, progress) {
      var key = normalizeLinkId(linkId);
      var item = linkMap[key];
      if (!item) return;
      var p = clamp(Number(progress) || 0, 0, 1);
      item.cutProgress = p;
      if (p <= 0.001) {
        item.cutG.setAttribute("opacity", "0");
        return;
      }
      // Hide underlying link mid-label so the crimson X never overlaps text
      item.labelG.setAttribute("opacity", "0");
      refreshCutBadge(item);
      var slashLen = Math.hypot(24, 24);
      var p1 = clamp(p * 1.6, 0, 1);
      var p2 = clamp((p - 0.25) * 1.6, 0, 1);
      item.cutG.setAttribute("opacity", clamp(p * 1.4, 0, 1).toFixed(4));
      item.cutBg.setAttribute("filter", glowFilterFor("crimson"));
      item.cutSlash1.setAttribute("stroke-dasharray", slashLen.toFixed(1));
      item.cutSlash1.setAttribute("stroke-dashoffset", (slashLen * (1 - p1)).toFixed(1));
      item.cutSlash2.setAttribute("stroke-dasharray", slashLen.toFixed(1));
      item.cutSlash2.setAttribute("stroke-dashoffset", (slashLen * (1 - p2)).toFixed(1));
    }

    function setBadge(id, o) {
      var optsObj = o || {};
      var bKey = String(id || "badge");
      var entry = badgePool[bKey];
      if (!entry) {
        var g = svgEl("g", { opacity: "0" });
        var r = svgEl("rect", { rx: 8, height: 30, fill: "#091715", stroke: COLORS.cyan, "stroke-width": "1.6" });
        var tx = svgEl("text", {
          "text-anchor": "middle",
          fill: COLORS.text,
          "font-family": "var(--font-mono)",
          "font-size": "15",
          "font-weight": "700"
        }, "");
        g.appendChild(r);
        g.appendChild(tx);
        layerBadges.appendChild(g);
        entry = { g: g, rect: r, text: tx };
        badgePool[bKey] = entry;
      }

      var op = optsObj.opacity !== undefined ? clamp(optsObj.opacity, 0, 1) : (optsObj.text ? 1 : 0);
      if (!optsObj.text || op <= 0.001) {
        entry.g.setAttribute("opacity", "0");
        return;
      }

      var cx = optsObj.x;
      var cy = optsObj.y;
      if (cx === undefined || cy === undefined) {
        var norm = normalizeLinkId(bKey);
        if (linkMap[norm]) {
          cx = linkMap[norm].mx;
          cy = linkMap[norm].my - 34;
        } else if (switchMap[bKey.toUpperCase()]) {
          cx = switchMap[bKey.toUpperCase()].x;
          cy = switchMap[bKey.toUpperCase()].y - 46;
        } else {
          cx = 480;
          cy = 330;
        }
      }

      var txt = String(optsObj.text);
      var w = Math.max(88, txt.length * 10 + 26);
      var col = optsObj.color || COLORS.cyan;
      entry.rect.setAttribute("x", (cx - w / 2).toFixed(1));
      entry.rect.setAttribute("y", (cy - 15).toFixed(1));
      entry.rect.setAttribute("width", w.toFixed(1));
      entry.rect.setAttribute("fill", optsObj.bg || "#091715");
      entry.rect.setAttribute("stroke", col);
      entry.text.setAttribute("x", cx.toFixed(1));
      entry.text.setAttribute("y", (cy + 5).toFixed(1));
      entry.text.setAttribute("fill", col);
      entry.text.textContent = txt;
      entry.g.setAttribute("opacity", op.toFixed(4));
    }

    function updateController(o) {
      if (!ctrlRefs) return;
      var optsObj = o || {};
      var pulse = optsObj.pulse !== undefined ? clamp(optsObj.pulse, 0, 1) : 0.35;
      var dashOffset = optsObj.dashOffset !== undefined ? optsObj.dashOffset : 0;
      if (optsObj.label) ctrlRefs.text.textContent = String(optsObj.label);
      ctrlRefs.rect.setAttribute("stroke", optsObj.color || COLORS.cyan);
      ctrlRefs.lines.forEach(function (l) {
        l.setAttribute("opacity", (0.22 + pulse * 0.45).toFixed(3));
        l.setAttribute("stroke-dashoffset", String(dashOffset));
      });
    }

    function reset() {
      LINK_DEFS.forEach(function (def) {
        updateLink(def.id, {
          color: COLORS.linkIdle,
          width: 3.5,
          opacity: 1,
          dashed: false,
          glow: false,
          label: ""
        });
        setCut(def.id, 0);
      });
      Object.keys(SWITCH_POS).forEach(function (sid) {
        updateSwitch(sid, {
          stroke: COLORS.switchStroke,
          fill: "#0F221E",
          glow: false,
          badgeText: "",
          badgeOpacity: 0,
          scale: 1
        });
      });
      Object.keys(HOST_INFO).forEach(function (hid) {
        updateHost(hid, { active: false, color: COLORS.emerald, rateText: "" });
      });
      Object.keys(packetPools).forEach(function (sk) {
        var dots = packetPools[sk].dots;
        for (var i = 0; i < dots.length; i++) dots[i].setAttribute("opacity", "0");
      });
      Object.keys(badgePool).forEach(function (bk) {
        badgePool[bk].g.setAttribute("opacity", "0");
      });
    }

    reset();

    return {
      svg: svg,
      updateLink: updateLink,
      updateSwitch: updateSwitch,
      updateHost: updateHost,
      setPackets: setPackets,
      setCut: setCut,
      setBadge: setBadge,
      updateController: updateController,
      reset: reset,
      SWITCH_POS: SWITCH_POS,
      HOST_INFO: HOST_INFO
    };
  }

  api.createGridDiagram = createGridDiagram;
})();
