(function () {
  'use strict';

  var NS = 'http://www.w3.org/2000/svg';
  var FONT_SANS = '"Segoe UI", "Bahnschrift", Arial, sans-serif';
  var FONT_MONO = '"Cascadia Mono", "Cascadia Code", Consolas, monospace';

  function el(tag, style, text) {
    var node = document.createElement(tag);
    if (style) node.style.cssText = style;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function svgEl(tag, attrs, text) {
    var node = document.createElementNS(NS, tag);
    if (attrs) {
      var keys = Object.keys(attrs);
      for (var i = 0; i < keys.length; i++) {
        node.setAttribute(keys[i], String(attrs[keys[i]]));
      }
    }
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function applyFadeSlide(node, p, dy, scaleFrom) {
    var c = p < 0 ? 0 : p > 1 ? 1 : p;
    var y = (1 - c) * (dy === undefined ? 18 : dy);
    var sf = scaleFrom === undefined ? 0.95 : scaleFrom;
    var sc = sf + (1 - sf) * c;
    node.style.opacity = c.toFixed(4);
    node.style.transform = 'translate3d(0,' + y.toFixed(2) + 'px,0) scale(' + sc.toFixed(4) + ')';
  }

  // Real measured S2 -> S3 series from experiments/results/grid-demo-20261117T193620Z.json
  var SAMPLES = [
    { t: 0,  raw: 0.002,  ewma: 0.002,  cp: 0, cong: false },
    { t: 5,  raw: 64.768, ewma: 32.385, cp: 0, cong: false },
    { t: 10, raw: 74.708, ewma: 53.546, cp: 0, cong: false },
    { t: 15, raw: 70.350, ewma: 61.948, cp: 0, cong: false },
    { t: 20, raw: 75.116, ewma: 68.532, cp: 0, cong: false },
    { t: 25, raw: 74.647, ewma: 71.589, cp: 1, cong: false },
    { t: 30, raw: 72.705, ewma: 72.147, cp: 2, cong: true  },
    { t: 35, raw: 72.033, ewma: 72.090, cp: 3, cong: true  }
  ];

  // Chart coordinate geometry inside viewBox 0 0 820 450
  var CH = { x0: 76, x1: 786, y0: 42, y1: 382 };
  function mapX(sec) {
    return CH.x0 + (sec / 35) * (CH.x1 - CH.x0);
  }
  function mapY(pct) {
    return CH.y1 - (pct / 100) * (CH.y1 - CH.y0);
  }

  function polylinePath(points) {
    var d = '';
    for (var i = 0; i < points.length; i++) {
      d += (i === 0 ? 'M' : ' L') + points[i][0].toFixed(2) + ' ' + points[i][1].toFixed(2);
    }
    return d;
  }

  function polylineLength(points) {
    var total = 0;
    for (var i = 1; i < points.length; i++) {
      var dx = points[i][0] - points[i - 1][0];
      var dy = points[i][1] - points[i - 1][1];
      total += Math.sqrt(dx * dx + dy * dy);
    }
    return total;
  }

  function sampleEwmaAt(sec) {
    if (sec <= 0) return SAMPLES[0].ewma;
    if (sec >= 35) return SAMPLES[SAMPLES.length - 1].ewma;
    var idx = Math.floor(sec / 5);
    if (idx >= SAMPLES.length - 1) return SAMPLES[SAMPLES.length - 1].ewma;
    var frac = (sec - idx * 5) / 5;
    return SAMPLES[idx].ewma + (SAMPLES[idx + 1].ewma - SAMPLES[idx].ewma) * frac;
  }

  window.SDN_VIDEO.registerScene({
    id: 'scene3-telemetry',
    index: 2,
    title: 'Real-Time Telemetry & Dual-Stage Detection',
    chapter: '03 / C4 TELEMETRY & DETECTION',
    start: 21,
    duration: 13,

    mount: function (rootEl, api) {
      var C = api.COLORS;
      rootEl.innerHTML = '';

      var wrap = el(
        'div',
        'position:absolute;inset:0;width:1920px;height:1080px;overflow:hidden;' +
        'font-family:' + FONT_SANS + ';color:' + C.text + ';'
      );

      // SCENE HEADER (y: 94..160)
      var header = el(
        'div',
        'position:absolute;left:96px;top:94px;width:1728px;display:flex;' +
        'align-items:center;justify-content:space-between;will-change:transform,opacity;'
      );
      var title = el(
        'h2',
        'margin:0;font-size:48px;font-weight:700;letter-spacing:-0.025em;color:' + C.text + ';',
        'Real-Time Telemetry & Dual-Stage Detection'
      );
      var headPill = el(
        'div',
        'padding:9px 20px;border-radius:999px;background:' + C.surface + ';' +
        'border:1px solid ' + C.border + ';font-family:' + FONT_MONO + ';font-size:19px;' +
        'font-weight:600;color:' + C.cyan + ';',
        'OPENFLOW 1.3 · C4 STATS POLLING'
      );
      header.appendChild(title);
      header.appendChild(headPill);
      wrap.appendChild(header);

      // LEFT COLUMN (x: 96..900, width 804px, y: 184..986)
      var leftCol = el(
        'div',
        'position:absolute;left:96px;top:184px;width:804px;height:802px;' +
        'display:flex;flex-direction:column;gap:22px;'
      );

      // --- TOP-LEFT CARD: C4 Port & Flow Polling ---
      var c4Card = el(
        'div',
        'flex:1;background:' + C.surface + ';border:1px solid ' + C.border + ';' +
        'border-top:4px solid ' + C.cyan + ';border-radius:18px;padding:20px 26px;' +
        'display:flex;flex-direction:column;justify-content:space-between;will-change:transform,opacity;'
      );

      var c4Head = el('div', 'display:flex;align-items:center;justify-content:space-between;');
      var c4Title = el('div', 'font-size:28px;font-weight:700;color:' + C.text + ';', 'C4 Port & Flow Polling');
      var c4Badge = el(
        'span',
        'padding:5px 14px;border-radius:8px;background:rgba(34,211,238,0.14);' +
        'border:1px solid rgba(34,211,238,0.45);font-family:' + FONT_MONO + ';font-size:18px;' +
        'font-weight:700;color:' + C.cyan + ';',
        'T = 2–5 s'
      );
      c4Head.appendChild(c4Title);
      c4Head.appendChild(c4Badge);
      c4Card.appendChild(c4Head);

      var c4Chips = el('div', 'display:flex;flex-wrap:wrap;gap:10px;');
      var c4Items = ['OFPPortStatsRequest', 'OFPFlowStatsRequest', '20 ports · 14 inter-switch directions'];
      for (var ci = 0; ci < c4Items.length; ci++) {
        c4Chips.appendChild(
          el(
            'span',
            'font-family:' + FONT_MONO + ';font-size:18px;font-weight:600;color:' + C.textMuted + ';' +
            'background:rgba(7,14,13,0.65);border:1px solid ' + C.border + ';border-radius:8px;padding:6px 12px;',
            c4Items[ci]
          )
        );
      }
      c4Card.appendChild(c4Chips);

      // Equation box
      var eqBox = el(
        'div',
        'padding:12px 18px;border-radius:12px;background:rgba(7,14,13,0.82);' +
        'border:1px solid ' + C.border + ';display:flex;align-items:center;justify-content:space-between;'
      );
      eqBox.appendChild(
        el(
          'span',
          'font-family:' + FONT_MONO + ';font-size:26px;font-weight:700;color:' + C.text + ';',
          'U = (Δtx_bytes × 8) / (Δt × C)'
        )
      );
      eqBox.appendChild(
        el(
          'span',
          'font-family:' + FONT_MONO + ';font-size:18px;color:' + C.cyan + ';',
          'C = 100 Mbps'
        )
      );
      c4Card.appendChild(eqBox);

      // Verified calibration callout badge (Nov 26 homogeneous batch: accuracy-20261126T124854Z.json)
      var calBadge = el(
        'div',
        'padding:12px 18px;border-radius:14px;background:rgba(20,117,85,0.22);' +
        'border:1px solid rgba(16,185,129,0.55);display:flex;flex-direction:column;' +
        'gap:7px;will-change:transform,opacity;'
      );
      var calTop = el('div', 'display:flex;align-items:center;justify-content:space-between;gap:14px;');
      var calLeft = el('div', 'display:flex;flex-direction:column;gap:2px;min-width:0;');
      calLeft.appendChild(
        el(
          'div',
          'font-family:' + FONT_MONO + ';font-size:18px;font-weight:700;letter-spacing:0.03em;color:' + C.emeraldBright + ';white-space:nowrap;',
          'VERIFIED iperf3 CALIBRATION (n = 5)'
        )
      );
      calLeft.appendChild(
        el(
          'div',
          'font-size:19px;font-weight:500;color:' + C.text + ';white-space:nowrap;',
          'Mean abs. error vs iperf3 · < 10% ✓'
        )
      );
      var calValue = el(
        'div',
        'font-family:' + FONT_MONO + ';font-size:32px;font-weight:700;font-variant-numeric:tabular-nums;' +
        'color:' + C.emeraldBright + ';white-space:nowrap;flex-shrink:0;',
        '3.116 ± 0.181%'
      );
      calTop.appendChild(calLeft);
      calTop.appendChild(calValue);

      var calMeta = el(
        'div',
        'display:flex;align-items:center;justify-content:space-between;gap:12px;padding-top:6px;' +
        'border-top:1px solid rgba(16,185,129,0.28);font-family:' + FONT_MONO + ';font-size:18px;' +
        'font-variant-numeric:tabular-nums;color:' + C.textMuted + ';'
      );
      calMeta.appendChild(el('span', 'white-space:nowrap;', 'accuracy-20261126T124854Z'));
      calMeta.appendChild(el('span', 'color:' + C.text + ';white-space:nowrap;', '5.000 vs 5.156 Mbps · Nov 26'));

      calBadge.appendChild(calTop);
      calBadge.appendChild(calMeta);
      c4Card.appendChild(calBadge);

      leftCol.appendChild(c4Card);

      // --- BOTTOM-LEFT CARD: Elephant Flow Filter ---
      var eleCard = el(
        'div',
        'flex:1;background:' + C.surface + ';border:1px solid ' + C.border + ';' +
        'border-top:4px solid ' + C.amber + ';border-radius:18px;padding:24px 28px;' +
        'display:flex;flex-direction:column;justify-content:space-between;will-change:transform,opacity;'
      );

      var eleHead = el('div', 'display:flex;align-items:center;justify-content:space-between;');
      eleHead.appendChild(el('div', 'font-size:28px;font-weight:700;color:' + C.text + ';', 'Elephant Flow Filter'));
      eleHead.appendChild(
        el(
          'span',
          'padding:5px 14px;border-radius:8px;background:rgba(249,115,22,0.16);' +
          'border:1px solid rgba(249,115,22,0.55);font-family:' + FONT_MONO + ';font-size:18px;' +
          'font-weight:700;color:' + C.amber + ';',
          '> 10% (10 Mbps) · 2 PERIODS'
        )
      );
      eleCard.appendChild(eleHead);

      var eleNote = el(
        'div',
        'font-size:20px;line-height:1.35;color:' + C.textMuted + ';',
        'Measured once at ingress IPv4 MAC-pair rules — zero multi-switch double-counting.'
      );
      eleCard.appendChild(eleNote);

      // Animated Elephant Flow Meter (H1 -> H6)
      var meterBlock = el(
        'div',
        'padding:16px 20px;border-radius:14px;background:rgba(7,14,13,0.78);' +
        'border:1px solid ' + C.border + ';display:flex;flex-direction:column;gap:12px;'
      );
      var meterRow = el('div', 'display:flex;align-items:baseline;justify-content:space-between;');
      meterRow.appendChild(
        el('span', 'font-family:' + FONT_MONO + ';font-size:21px;font-weight:700;color:' + C.text + ';', 'H1 → H6 (S1 Ingress)')
      );
      var eleRateVal = el(
        'span',
        'font-family:' + FONT_MONO + ';font-size:30px;font-weight:700;font-variant-numeric:tabular-nums;color:' + C.amber + ';',
        '0.0 Mbps'
      );
      meterRow.appendChild(eleRateVal);
      meterBlock.appendChild(meterRow);

      var eleTrack = el(
        'div',
        'position:relative;height:22px;border-radius:10px;background:rgba(31,59,52,0.45);' +
        'border:1px solid ' + C.border + ';overflow:hidden;'
      );
      var eleFill = el(
        'div',
        'width:100%;height:100%;transform-origin:left center;background:linear-gradient(90deg,' + C.emerald + ',' + C.amber + ');' +
        'will-change:transform;'
      );
      var eleThreshLine = el(
        'div',
        'position:absolute;left:10%;top:0;bottom:0;width:3px;background:' + C.text + ';'
      );
      eleTrack.appendChild(eleFill);
      eleTrack.appendChild(eleThreshLine);
      meterBlock.appendChild(eleTrack);

      var eleScaleRow = el(
        'div',
        'display:flex;justify-content:space-between;font-family:' + FONT_MONO + ';font-size:18px;color:' + C.textMuted + ';'
      );
      eleScaleRow.appendChild(el('span', '', '0 Mbps'));
      eleScaleRow.appendChild(el('span', 'color:' + C.text + ';font-weight:600;', '▲ 10 Mbps threshold'));
      eleScaleRow.appendChild(el('span', '', '100 Mbps'));
      meterBlock.appendChild(eleScaleRow);

      eleCard.appendChild(meterBlock);

      // Period 1 -> Period 2 -> ELEPHANT = TRUE strip
      var eleStateRow = el('div', 'display:flex;align-items:center;gap:12px;');
      var eleP1 = el(
        'div',
        'flex:1;text-align:center;padding:10px 10px;border-radius:10px;background:rgba(7,14,13,0.7);' +
        'border:1px solid ' + C.border + ';font-family:' + FONT_MONO + ';font-size:18px;font-weight:700;color:' + C.textMuted + ';',
        'PERIOD 1 ✓'
      );
      var eleP2 = el(
        'div',
        'flex:1;text-align:center;padding:10px 10px;border-radius:10px;background:rgba(7,14,13,0.7);' +
        'border:1px solid ' + C.border + ';font-family:' + FONT_MONO + ';font-size:18px;font-weight:700;color:' + C.textMuted + ';',
        'PERIOD 2 ✓'
      );
      var eleFlag = el(
        'div',
        'flex:1.45;text-align:center;padding:10px 12px;border-radius:10px;background:rgba(7,14,13,0.7);' +
        'border:1px solid ' + C.border + ';font-family:' + FONT_MONO + ';font-size:18px;font-weight:700;color:' + C.textMuted + ';',
        'ELEPHANT = TRUE'
      );
      eleStateRow.appendChild(eleP1);
      eleStateRow.appendChild(eleP2);
      eleStateRow.appendChild(eleFlag);
      eleCard.appendChild(eleStateRow);

      leftCol.appendChild(eleCard);
      wrap.appendChild(leftCol);

      // RIGHT LARGE CHART CARD: EWMA Congestion Detector (x: 940..1824, width 884px, y: 184..986)
      var rightCard = el(
        'div',
        'position:absolute;left:940px;top:184px;width:884px;height:802px;' +
        'background:' + C.surface + ';border:1px solid ' + C.border + ';' +
        'border-top:4px solid ' + C.amber + ';border-radius:18px;padding:24px 28px;' +
        'display:flex;flex-direction:column;justify-content:space-between;will-change:transform,opacity;'
      );

      var chartHead = el('div', 'display:flex;align-items:flex-start;justify-content:space-between;gap:16px;');
      var chartTitles = el('div', 'display:flex;flex-direction:column;gap:6px;');
      chartTitles.appendChild(
        el('div', 'font-size:30px;font-weight:700;color:' + C.text + ';', 'EWMA Congestion Detector (S2 → S3)')
      );
      chartTitles.appendChild(
        el(
          'div',
          'font-family:' + FONT_MONO + ';font-size:18px;color:' + C.textMuted + ';white-space:nowrap;',
          'α = 0.5 · θ = 70% (2 periods) · grid-demo-20261117T193620Z'
        )
      );
      var eqPill = el(
        'div',
        'padding:8px 14px;border-radius:10px;background:rgba(7,14,13,0.8);border:1px solid ' + C.border + ';' +
        'font-family:' + FONT_MONO + ';font-size:18px;font-weight:700;color:' + C.cyan + ';white-space:nowrap;',
        '0.5·U + 0.5·EWMA'
      );
      chartHead.appendChild(chartTitles);
      chartHead.appendChild(eqPill);
      rightCard.appendChild(chartHead);

      // Legend Row
      var legendRow = el(
        'div',
        'display:flex;align-items:center;gap:26px;font-family:' + FONT_MONO + ';font-size:18px;color:' + C.textMuted + ';'
      );
      legendRow.appendChild(el('span', 'color:' + C.emeraldBright + ';font-weight:700;', '━━ EWMA Utilization'));
      legendRow.appendChild(el('span', 'color:' + C.cyan + ';', '┈┈ Raw Port TX'));
      legendRow.appendChild(el('span', 'color:' + C.amber + ';font-weight:700;', '--- θ = 70% Threshold'));
      rightCard.appendChild(legendRow);

      // SVG Line Chart
      var chartSvg = svgEl('svg', {
        viewBox: '0 0 820 450',
        style: 'width:100%;height:460px;display:block;overflow:visible;'
      });

      var defs = svgEl('defs');
      var gradArea = svgEl('linearGradient', { id: 's3EwmaGrad', x1: '0', y1: '0', x2: '0', y2: '1' });
      gradArea.appendChild(svgEl('stop', { offset: '0%', 'stop-color': C.amber, 'stop-opacity': '0.32' }));
      gradArea.appendChild(svgEl('stop', { offset: '55%', 'stop-color': C.emerald, 'stop-opacity': '0.14' }));
      gradArea.appendChild(svgEl('stop', { offset: '100%', 'stop-color': C.emerald, 'stop-opacity': '0.0' }));
      defs.appendChild(gradArea);

      var clipRect = svgEl('rect', { x: String(CH.x0), y: '0', width: '0', height: '450' });
      var clipPath = svgEl('clipPath', { id: 's3ChartClip' });
      clipPath.appendChild(clipRect);
      defs.appendChild(clipPath);
      chartSvg.appendChild(defs);

      // Shaded congestion zone above 70%
      var y70 = mapY(70);
      chartSvg.appendChild(
        svgEl('rect', {
          x: CH.x0,
          y: CH.y0,
          width: CH.x1 - CH.x0,
          height: y70 - CH.y0,
          fill: 'rgba(249,115,22,0.08)'
        })
      );

      // Horizontal gridlines & Y labels (0, 20, 40, 60, 80, 100)
      var yTicks = [0, 20, 40, 60, 80, 100];
      for (var yi = 0; yi < yTicks.length; yi++) {
        var val = yTicks[yi];
        var yy = mapY(val);
        chartSvg.appendChild(
          svgEl('line', {
            x1: CH.x0,
            y1: yy,
            x2: CH.x1,
            y2: yy,
            stroke: val === 0 ? C.switchStroke : C.border,
            'stroke-width': val === 0 ? '1.8' : '1',
            opacity: val === 0 ? '0.9' : '0.65'
          })
        );
        chartSvg.appendChild(
          svgEl(
            'text',
            {
              x: CH.x0 - 12,
              y: yy + 6,
              fill: C.textMuted,
              'font-family': FONT_MONO,
              'font-size': '18',
              'text-anchor': 'end'
            },
            val + '%'
          )
        );
      }

      // Vertical gridlines & X labels (0s .. 35s)
      for (var xi = 0; xi < SAMPLES.length; xi++) {
        var sec = SAMPLES[xi].t;
        var xx = mapX(sec);
        chartSvg.appendChild(
          svgEl('line', {
            x1: xx,
            y1: CH.y0,
            x2: xx,
            y2: CH.y1,
            stroke: C.border,
            'stroke-width': '1',
            opacity: '0.4'
          })
        );
        chartSvg.appendChild(
          svgEl(
            'text',
            {
              x: xx,
              y: CH.y1 + 30,
              fill: C.textMuted,
              'font-family': FONT_MONO,
              'font-size': '18',
              'text-anchor': 'middle'
            },
            sec + 's'
          )
        );
      }

      // Dashed amber 70% threshold line
      chartSvg.appendChild(
        svgEl('line', {
          x1: CH.x0,
          y1: y70,
          x2: CH.x1,
          y2: y70,
          stroke: C.amber,
          'stroke-width': '2.6',
          'stroke-dasharray': '10 7'
        })
      );
      // Solid pill backdrop placed cleanly above Raw Port TX (max 75.1% => y=126.6)
      var threshGroup = svgEl('g');
      threshGroup.appendChild(
        svgEl('line', {
          x1: CH.x0 + 36,
          y1: y70 - 30,
          x2: CH.x0 + 36,
          y2: y70,
          stroke: C.amber,
          'stroke-width': '1.8',
          'stroke-dasharray': '3 3'
        })
      );
      threshGroup.appendChild(
        svgEl('rect', {
          x: CH.x0 + 10,
          y: y70 - 62,
          width: 328,
          height: 32,
          rx: 8,
          fill: C.surface,
          stroke: C.amber,
          'stroke-width': '1.6'
        })
      );
      threshGroup.appendChild(
        svgEl(
          'text',
          {
            x: CH.x0 + 24,
            y: y70 - 40,
            fill: C.amber,
            'font-family': FONT_MONO,
            'font-size': '18',
            'font-weight': '700'
          },
          'θ = 70% CONGESTION THRESHOLD'
        )
      );
      chartSvg.appendChild(threshGroup);

      // Compute points for Raw TX and EWMA
      var rawPts = [];
      var ewmaPts = [];
      for (var pi = 0; pi < SAMPLES.length; pi++) {
        rawPts.push([mapX(SAMPLES[pi].t), mapY(SAMPLES[pi].raw)]);
        ewmaPts.push([mapX(SAMPLES[pi].t), mapY(SAMPLES[pi].ewma)]);
      }

      // Area under EWMA curve (clipped smoothly with chart reveal)
      var areaD = polylinePath(ewmaPts) + ' L' + mapX(35).toFixed(2) + ' ' + CH.y1 + ' L' + mapX(0).toFixed(2) + ' ' + CH.y1 + ' Z';
      var ewmaArea = svgEl('path', {
        d: areaD,
        fill: 'url(#s3EwmaGrad)',
        'clip-path': 'url(#s3ChartClip)'
      });
      chartSvg.appendChild(ewmaArea);

      // Raw TX dashed line (clipped)
      var rawPath = svgEl('path', {
        d: polylinePath(rawPts),
        fill: 'none',
        stroke: C.cyan,
        'stroke-width': '2.4',
        'stroke-dasharray': '6 6',
        opacity: '0.68',
        'clip-path': 'url(#s3ChartClip)'
      });
      chartSvg.appendChild(rawPath);

      // EWMA bold solid line (stroke-dashoffset)
      var ewmaLen = polylineLength(ewmaPts);
      var ewmaPath = svgEl('path', {
        d: polylinePath(ewmaPts),
        fill: 'none',
        stroke: C.emeraldBright,
        'stroke-width': '4.8',
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-dasharray': ewmaLen.toFixed(2),
        'stroke-dashoffset': ewmaLen.toFixed(2)
      });
      chartSvg.appendChild(ewmaPath);

      // Alert segment overlay from t=25s..35s in burnt amber
      var hotPts = [ewmaPts[5], ewmaPts[6], ewmaPts[7]];
      var hotLen = polylineLength(hotPts);
      var hotPath = svgEl('path', {
        d: polylinePath(hotPts),
        fill: 'none',
        stroke: C.amber,
        'stroke-width': '5.4',
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
        'stroke-dasharray': hotLen.toFixed(2),
        'stroke-dashoffset': hotLen.toFixed(2)
      });
      chartSvg.appendChild(hotPath);

      // Interactive point dots
      var dotEls = [];
      for (var di = 0; di < SAMPLES.length; di++) {
        var isAlertPt = SAMPLES[di].t >= 25;
        var dot = svgEl('circle', {
          cx: ewmaPts[di][0].toFixed(2),
          cy: ewmaPts[di][1].toFixed(2),
          r: isAlertPt ? '7.5' : '5.5',
          fill: isAlertPt ? C.amber : C.emeraldBright,
          stroke: C.bg,
          'stroke-width': '2.5',
          opacity: '0'
        });
        chartSvg.appendChild(dot);
        dotEls.push(dot);
      }

      // Callout annotations for t=25s, t=30s, t=35s
      function makeCallout(x, y, boxX, boxY, boxW, line1, line2, borderCol, fillCol) {
        var g = svgEl('g', { opacity: '0' });
        g.appendChild(
          svgEl('line', {
            x1: x,
            y1: y,
            x2: boxX + boxW / 2,
            y2: boxY + (boxY < y ? 56 : 0),
            stroke: borderCol,
            'stroke-width': '2',
            'stroke-dasharray': '4 3'
          })
        );
        g.appendChild(
          svgEl('rect', {
            x: boxX,
            y: boxY,
            width: boxW,
            height: 58,
            rx: 10,
            fill: fillCol,
            stroke: borderCol,
            'stroke-width': '2'
          })
        );
        g.appendChild(
          svgEl(
            'text',
            {
              x: boxX + boxW / 2,
              y: boxY + 24,
              fill: borderCol,
              'font-family': FONT_MONO,
              'font-size': '18',
              'font-weight': '700',
              'text-anchor': 'middle'
            },
            line1
          )
        );
        g.appendChild(
          svgEl(
            'text',
            {
              x: boxX + boxW / 2,
              y: boxY + 47,
              fill: C.text,
              'font-family': FONT_MONO,
              'font-size': '18',
              'font-weight': '700',
              'text-anchor': 'middle'
            },
            line2
          )
        );
        chartSvg.appendChild(g);
        return g;
      }

      var callP1 = makeCallout(ewmaPts[5][0], ewmaPts[5][1], 396, 236, 184, 'P1 (t=25s)', '71.59%', C.amber, 'rgba(15,30,27,0.95)');
      var callP2 = makeCallout(ewmaPts[6][0], ewmaPts[6][1], 524, 18, 258, 'P2 (t=30s): 72.15%', 'CONGESTED = TRUE', C.amber, 'rgba(191,84,26,0.34)');
      var callP3 = makeCallout(ewmaPts[7][0], ewmaPts[7][1], 600, 236, 208, 't=35s: 72.09%', 'TRIGGER REROUTE', C.emeraldBright, 'rgba(20,117,85,0.34)');

      rightCard.appendChild(chartSvg);

      // Bottom Live Telemetry Summary Strip (3 tabular-nums readouts)
      var kpiStrip = el('div', 'display:grid;grid-template-columns:1fr 1fr 1.35fr;gap:14px;');

      function makeMiniKpi(label, initVal, accent) {
        var box = el(
          'div',
          'padding:14px 18px;border-radius:12px;background:rgba(7,14,13,0.78);' +
          'border:1px solid ' + C.border + ';display:flex;flex-direction:column;gap:4px;'
        );
        box.appendChild(
          el('div', 'font-family:' + FONT_MONO + ';font-size:18px;color:' + C.textMuted + ';', label)
        );
        var val = el(
          'div',
          'font-family:' + FONT_MONO + ';font-size:28px;font-weight:700;font-variant-numeric:tabular-nums;color:' + accent + ';',
          initVal
        );
        box.appendChild(val);
        return { box: box, val: val };
      }

      var kpiEwma = makeMiniKpi('S2→S3 EWMA', '0.00%', C.emeraldBright);
      var kpiPeriods = makeMiniKpi('PERIODS > 70%', '0 / 2', C.text);
      var kpiState = makeMiniKpi('DETECTOR STATUS', 'MONITORING', C.cyan);
      kpiStrip.appendChild(kpiEwma.box);
      kpiStrip.appendChild(kpiPeriods.box);
      kpiStrip.appendChild(kpiState.box);
      rightCard.appendChild(kpiStrip);

      wrap.appendChild(rightCard);
      rootEl.appendChild(wrap);

      return {
        header: header,
        c4Card: c4Card,
        calBadge: calBadge,
        eleCard: eleCard,
        eleRateVal: eleRateVal,
        eleFill: eleFill,
        eleP1: eleP1,
        eleP2: eleP2,
        eleFlag: eleFlag,
        rightCard: rightCard,
        clipRect: clipRect,
        ewmaPath: ewmaPath,
        ewmaLen: ewmaLen,
        hotPath: hotPath,
        hotLen: hotLen,
        dotEls: dotEls,
        callP1: callP1,
        callP2: callP2,
        callP3: callP3,
        kpiEwma: kpiEwma,
        kpiPeriods: kpiPeriods,
        kpiState: kpiState
      };
    },

    update: function (state, localT, globalT, api) {
      var C = api.COLORS;
      var E = api.EASE;
      var M = api.math;

      // Staggered card entrances (hero visible <= 0.5s)
      applyFadeSlide(state.header, M.seg(localT, 0.0, 0.40, E.power4Out), 16, 0.96);
      applyFadeSlide(state.c4Card, M.seg(localT, 0.05, 0.45, E.power4Out), 18, 0.96);
      applyFadeSlide(state.calBadge, M.seg(localT, 0.45, 0.45, E.power3Out), 12, 0.96);
      applyFadeSlide(state.eleCard, M.seg(localT, 0.16, 0.46, E.power4Out), 18, 0.96);
      applyFadeSlide(state.rightCard, M.seg(localT, 0.10, 0.46, E.power4Out), 18, 0.96);

      // Elephant Flow Meter animation (H1 -> H6 reaches 75.33 -> 87.64 Mbps)
      var pEleRamp1 = M.seg(localT, 1.4, 1.3, E.power3Out);
      var pEleRamp2 = M.seg(localT, 3.0, 1.0, E.power3Out);
      var eleMbps = 75.33 * pEleRamp1 + 12.31 * pEleRamp2; // 0 -> 75.33 -> 87.64 Mbps
      state.eleRateVal.textContent = eleMbps.toFixed(1) + ' Mbps';
      state.eleFill.style.transform = 'scaleX(' + M.clamp(eleMbps / 100, 0, 1).toFixed(4) + ')';

      var eleP1On = localT >= 2.6;
      var eleP2On = localT >= 3.9;
      var eleTrue = localT >= 4.2;

      state.eleP1.style.color = eleP1On ? C.amber : C.textMuted;
      state.eleP1.style.borderColor = eleP1On ? C.amber : C.border;
      state.eleP1.style.background = eleP1On ? 'rgba(249,115,22,0.16)' : 'rgba(7,14,13,0.7)';

      state.eleP2.style.color = eleP2On ? C.amber : C.textMuted;
      state.eleP2.style.borderColor = eleP2On ? C.amber : C.border;
      state.eleP2.style.background = eleP2On ? 'rgba(249,115,22,0.16)' : 'rgba(7,14,13,0.7)';

      state.eleFlag.style.color = eleTrue ? C.text : C.textMuted;
      state.eleFlag.style.borderColor = eleTrue ? C.amber : C.border;
      state.eleFlag.style.background = eleTrue ? C.amberFill : 'rgba(7,14,13,0.7)';

      // EWMA Chart Scrub: maps localT 1.6s..9.4s -> sample time 0s..35s
      var pChart = M.seg(localT, 1.6, 7.8, E.linear);
      var simSec = pChart * 35;

      // Reveal clip width for area + raw dashed line
      var clipW = (CH.x1 - CH.x0) * pChart;
      state.clipRect.setAttribute('width', clipW.toFixed(2));

      // Draw EWMA curve proportionally
      state.ewmaPath.setAttribute('stroke-dashoffset', (state.ewmaLen * (1 - pChart)).toFixed(2));

      // Draw amber hot overlay (t=25..35s => pChart 25/35..1.0)
      var pHot = M.clamp((simSec - 25) / 10, 0, 1);
      state.hotPath.setAttribute('stroke-dashoffset', (state.hotLen * (1 - pHot)).toFixed(2));

      // Dots appear cleanly as simSec passes each sample timestamp
      for (var d = 0; d < SAMPLES.length; d++) {
        var dotOp = M.clamp((simSec - SAMPLES[d].t + 1.0) / 1.5, 0, 1);
        state.dotEls[d].setAttribute('opacity', dotOp.toFixed(3));
      }

      // Callout badges appear at exact sample crossings
      var opC1 = M.seg(simSec, 24.8, 1.6, E.power3Out);
      var opC2 = M.seg(simSec, 29.8, 1.6, E.power3Out);
      var opC3 = M.seg(simSec, 34.0, 1.4, E.power3Out);
      state.callP1.setAttribute('opacity', opC1.toFixed(3));
      state.callP2.setAttribute('opacity', opC2.toFixed(3));
      state.callP3.setAttribute('opacity', opC3.toFixed(3));

      // Bottom KPI strip steps cleanly at each 5s poll tick so EWMA and PERIODS > 70% are always 100% synced
      var pollIdx = Math.min(SAMPLES.length - 1, Math.max(0, Math.floor(simSec / 5)));
      var curSample = SAMPLES[pollIdx];
      state.kpiEwma.val.textContent = curSample.ewma.toFixed(2) + '%';
      state.kpiEwma.val.style.color = curSample.ewma > 70 ? C.amber : C.emeraldBright;

      if (curSample.cp === 0) {
        state.kpiPeriods.val.textContent = '0 / 2';
        state.kpiPeriods.val.style.color = C.text;
        state.kpiState.val.textContent = 'MONITORING';
        state.kpiState.val.style.color = C.cyan;
      } else if (curSample.cp === 1) {
        state.kpiPeriods.val.textContent = '1 / 2';
        state.kpiPeriods.val.style.color = C.amber;
        state.kpiState.val.textContent = 'PERIOD 1 > 70%';
        state.kpiState.val.style.color = C.amber;
      } else if (curSample.cp === 2) {
        state.kpiPeriods.val.textContent = '2 / 2';
        state.kpiPeriods.val.style.color = C.amber;
        state.kpiState.val.textContent = 'CONGESTED = TRUE';
        state.kpiState.val.style.color = C.amber;
      } else {
        state.kpiPeriods.val.textContent = '3 / 2';
        state.kpiPeriods.val.style.color = C.amber;
        state.kpiState.val.textContent = 'REROUTE TRIGGER';
        state.kpiState.val.style.color = C.emeraldBright;
      }
    }
  });
})();
