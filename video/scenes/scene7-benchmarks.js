(function () {
  'use strict';

  var SVG_NS = 'http://www.w3.org/2000/svg';
  var FONT_SANS = '"Segoe UI", "Bahnschrift", "Arial", sans-serif';
  var FONT_MONO = '"Cascadia Mono", "Cascadia Code", "Consolas", monospace';

  function el(tag, styles, text) {
    var node = document.createElement(tag);
    if (styles) {
      var keys = Object.keys(styles);
      for (var i = 0; i < keys.length; i++) {
        node.style[keys[i]] = styles[keys[i]];
      }
    }
    if (text !== undefined && text !== null) {
      node.textContent = String(text);
    }
    return node;
  }

  function sEl(tag, attrs, text) {
    var node = document.createElementNS(SVG_NS, tag);
    if (attrs) {
      var keys = Object.keys(attrs);
      for (var i = 0; i < keys.length; i++) {
        node.setAttribute(keys[i], String(attrs[keys[i]]));
      }
    }
    if (text !== undefined && text !== null) {
      node.textContent = String(text);
    }
    return node;
  }

  function hexAlpha(hex, alpha) {
    var h = hex.replace('#', '');
    var r = parseInt(h.slice(0, 2), 16);
    var g = parseInt(h.slice(2, 4), 16);
    var b = parseInt(h.slice(4, 6), 16);
    return 'rgba(' + r + ',' + g + ',' + b + ',' + alpha.toFixed(3) + ')';
  }

  window.SDN_VIDEO.registerScene({
    id: 'scene7-benchmarks',
    index: 6,
    title: 'Measured Experimental Results (Mininet + OVS, n = 5)',
    chapter: '07 / MEASURED BENCHMARKS',
    start: 71,
    duration: 15,

    mount: function (rootEl, api) {
      var C = api.COLORS;

      var wrap = el('div', {
        position: 'absolute',
        inset: '0',
        width: '1920px',
        height: '1080px',
        fontFamily: FONT_SANS,
        color: C.text,
        boxSizing: 'border-box'
      });
      rootEl.appendChild(wrap);

      // ── Header (x: 96..1824, y: 90..172) ─────────────────────────────
      var header = el('div', {
        position: 'absolute',
        left: '96px',
        top: '90px',
        width: '1728px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '24px'
      });
      header.appendChild(el('div', {
        fontSize: '46px',
        fontWeight: '700',
        letterSpacing: '-0.025em',
        lineHeight: '1.1',
        color: C.text
      }, 'Measured Experimental Results (Mininet + OVS, n = 5)'));
      header.appendChild(el('div', {
        padding: '10px 18px',
        borderRadius: '999px',
        fontFamily: FONT_MONO,
        fontSize: '18px',
        fontWeight: '700',
        letterSpacing: '0.07em',
        textTransform: 'uppercase',
        border: '1.5px solid ' + hexAlpha(C.cyan, 0.7),
        backgroundColor: hexAlpha(C.cyan, 0.12),
        color: C.cyan,
        whiteSpace: 'nowrap'
      }, 'NOV 25 64k HTB · RAW JSON LOGS'));
      wrap.appendChild(header);

      // ── 2x2 Telemetry Grid (x: 96..1824, y: 176..996) ────────────────
      // Each card: 850 x 398 px, gap 28px horizontal / 24px vertical
      function makeCard(left, top, tagText, titleText, subText, rightBadge) {
        var card = el('div', {
          position: 'absolute',
          left: left + 'px',
          top: top + 'px',
          width: '850px',
          height: '398px',
          backgroundColor: C.surface,
          border: '1.5px solid ' + C.border,
          borderRadius: '18px',
          boxSizing: 'border-box',
          padding: '18px 24px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between'
        });
        var topBar = el('div', {
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '12px'
        });
        var tCol = el('div', { display: 'flex', flexDirection: 'column', gap: '2px', minWidth: '0' });
        tCol.appendChild(el('div', {
          fontFamily: FONT_MONO,
          fontSize: '18px',
          fontWeight: '700',
          letterSpacing: '0.04em',
          color: C.cyan,
          whiteSpace: 'nowrap'
        }, tagText));
        tCol.appendChild(el('div', {
          fontSize: '25px',
          fontWeight: '700',
          letterSpacing: '-0.015em',
          lineHeight: '1.15',
          color: C.text,
          whiteSpace: 'nowrap'
        }, titleText));
        tCol.appendChild(el('div', {
          fontFamily: FONT_MONO,
          fontSize: '18px',
          color: C.textMuted,
          whiteSpace: 'nowrap'
        }, subText));
        topBar.appendChild(tCol);
        if (rightBadge) {
          topBar.appendChild(rightBadge);
        }
        card.appendChild(topBar);
        wrap.appendChild(card);
        return card;
      }

      // ── CARD A (Top-Left): Grid Load Balancing — Shortest vs Balanced ─
      var cardABadge = el('div', {
        padding: '6px 12px',
        borderRadius: '10px',
        fontFamily: FONT_MONO,
        fontSize: '19px',
        fontWeight: '700',
        backgroundColor: hexAlpha(C.emerald, 0.18),
        border: '1.5px solid ' + C.emerald,
        color: C.emeraldBright,
        fontVariantNumeric: 'tabular-nums',
        whiteSpace: 'nowrap',
        flexShrink: '0'
      }, '-26.88 pp LOSS');
      var cardA = makeCard(
        96, 176,
        'CARD A · compare-grid-20261125T194357Z (n = 5)',
        'Grid Load Balancing: Shortest vs Balanced',
        '85+30 Mbps · 64k HTB burst · improved in all 5/5 runs',
        cardABadge
      );

      var cardABody = el('div', {
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      });

      // Helper for each flow block (H1->H6 and H3->H5) with 0..40% loss bar comparison
      var lossScaleMax = 40.0;
      var lossSvgW = 350;
      var lossBars = [];

      function makeFlowBlock(spec) {
        var blk = el('div', {
          backgroundColor: hexAlpha(C.bg, 0.74),
          border: '1px solid ' + C.border,
          borderRadius: '12px',
          padding: '8px 14px',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
          fontFamily: FONT_MONO,
          fontVariantNumeric: 'tabular-nums'
        });

        var topLine = el('div', {
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '10px'
        });

        topLine.appendChild(el('span', {
          padding: '2px 8px',
          borderRadius: '6px',
          backgroundColor: hexAlpha(C.cyan, 0.14),
          color: C.cyan,
          fontSize: '18px',
          fontWeight: '700',
          whiteSpace: 'nowrap'
        }, spec.flow));

        var rxSpan = el('div', { fontSize: '18px', fontWeight: '600', whiteSpace: 'nowrap' });
        rxSpan.appendChild(el('span', { color: C.textMuted }, 'Rx '));
        rxSpan.appendChild(el('span', { color: C.amber }, spec.rxBefore));
        rxSpan.appendChild(el('span', { color: C.textMuted }, '→'));
        rxSpan.appendChild(el('span', { color: C.emeraldBright, fontWeight: '700' }, spec.rxAfter));
        rxSpan.appendChild(el('span', { color: C.emeraldBright, fontWeight: '700' }, ' (' + spec.rxDelta + ')'));
        topLine.appendChild(rxSpan);

        var jitSpan = el('div', { fontSize: '18px', fontWeight: '600', whiteSpace: 'nowrap' });
        jitSpan.appendChild(el('span', { color: C.textMuted }, 'Jit '));
        jitSpan.appendChild(el('span', { color: C.amber }, spec.jitBefore));
        jitSpan.appendChild(el('span', { color: C.textMuted }, '→'));
        jitSpan.appendChild(el('span', { color: C.emeraldBright, fontWeight: '700' }, spec.jitAfter));
        topLine.appendChild(jitSpan);

        blk.appendChild(topLine);

        var botLine = el('div', {
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '14px'
        });

        var svg = sEl('svg', { viewBox: '0 0 ' + lossSvgW + ' 32', width: String(lossSvgW), height: '32' });
        svg.appendChild(sEl('rect', { x: '0', y: '2', width: String(lossSvgW), height: '12', rx: '3', fill: hexAlpha(C.linkIdle, 0.2) }));
        var bBefore = sEl('rect', { x: '0', y: '2', width: '0', height: '12', rx: '3', fill: C.amber });
        svg.appendChild(bBefore);
        svg.appendChild(sEl('rect', { x: '0', y: '18', width: String(lossSvgW), height: '12', rx: '3', fill: hexAlpha(C.linkIdle, 0.2) }));
        var bAfter = sEl('rect', { x: '0', y: '18', width: '0', height: '12', rx: '3', fill: C.emeraldBright });
        svg.appendChild(bAfter);
        botLine.appendChild(svg);

        var lossTxt = el('div', { fontSize: '18px', fontWeight: '700', whiteSpace: 'nowrap' });
        lossTxt.appendChild(el('span', { color: C.textMuted, fontWeight: '600' }, 'Loss '));
        lossTxt.appendChild(el('span', { color: C.amber }, spec.lossBefore));
        lossTxt.appendChild(el('span', { color: C.textMuted }, '→'));
        lossTxt.appendChild(el('span', { color: C.emeraldBright }, spec.lossAfter));
        lossTxt.appendChild(el('span', { color: C.emeraldBright }, ' (' + spec.lossDelta + ')'));
        botLine.appendChild(lossTxt);

        blk.appendChild(botLine);
        lossBars.push({
          beforeBar: bBefore,
          afterBar: bAfter,
          beforeW: (spec.lossBeforeNum / lossScaleMax) * lossSvgW,
          afterW: (spec.lossAfterNum / lossScaleMax) * lossSvgW
        });
        return blk;
      }

      var blockH1 = makeFlowBlock({
        flow: 'H1→H6 (H6 rx)',
        rxBefore: '68.90',
        rxAfter: '79.60 Mbps',
        rxDelta: '+10.70',
        jitBefore: '0.92',
        jitAfter: '0.24 ms',
        lossBefore: '18.74%',
        lossAfter: '6.22%',
        lossDelta: '-12.52 pp',
        lossBeforeNum: 18.74,
        lossAfterNum: 6.22
      });
      var blockH3 = makeFlowBlock({
        flow: 'H3→H5 (H5 rx)',
        rxBefore: '19.30',
        rxAfter: '27.42 Mbps',
        rxDelta: '+8.12',
        jitBefore: '1.18',
        jitAfter: '0.19 ms',
        lossBefore: '35.49%',
        lossAfter: '8.61%',
        lossDelta: '-26.88 pp',
        lossBeforeNum: 35.49,
        lossAfterNum: 8.61
      });
      cardABody.appendChild(blockH1);
      cardABody.appendChild(blockH3);

      // Compact bottom strip: route-phases-20261125T210721Z (14 paired comparisons)
      var phasesStrip = el('div', {
        padding: '7px 14px',
        borderRadius: '10px',
        backgroundColor: hexAlpha(C.emerald, 0.08),
        border: '1px solid ' + hexAlpha(C.emerald, 0.45),
        borderLeft: '4px solid ' + C.emeraldBright,
        display: 'flex',
        flexDirection: 'column',
        gap: '2px',
        fontFamily: FONT_MONO,
        fontSize: '18px',
        fontVariantNumeric: 'tabular-nums'
      });
      var phLine1 = el('div', {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '10px'
      });
      phLine1.appendChild(el('span', { color: C.cyan, fontWeight: '700' }, 'route-phases-20261125T210721Z (14 pairs)'));
      phLine1.appendChild(el('span', { color: C.emeraldBright, fontWeight: '700' }, '0.00% loss before/after'));
      var phLine2 = el('div', { color: C.text, fontWeight: '600' }, 'H1→H6 RTT 18.82 → 15.44 ms · Rate 27.96 → 28.00 Mbps');
      phasesStrip.appendChild(phLine1);
      phasesStrip.appendChild(phLine2);
      cardABody.appendChild(phasesStrip);

      cardA.appendChild(cardABody);

      // ── CARD B (Top-Right): Polling Interval T=2s vs T=5s ────────────
      var cardBBadge = el('div', {
        padding: '6px 12px',
        borderRadius: '10px',
        fontFamily: FONT_MONO,
        fontSize: '19px',
        fontWeight: '700',
        backgroundColor: C.emeraldFill,
        border: '1.5px solid ' + C.emeraldBright,
        color: C.text,
        fontVariantNumeric: 'tabular-nums',
        whiteSpace: 'nowrap',
        flexShrink: '0'
      }, '11.98 s (~2.72×)');
      var cardB = makeCard(
        974, 176,
        'CARD B · shared-detection-20261125T203550Z (n = 5)',
        'Polling Interval: T = 2 s vs T = 5 s',
        'Matched 4-flow 90 Mbps · 64k HTB burst · θ = 70% · 5/5 each',
        cardBBadge
      );

      // SVG Horizontal Bars with ±SD whiskers + dedicated right label column (802 x 194)
      var pollSvg = sEl('svg', { viewBox: '0 0 802 194', width: '802', height: '194' });
      var pBarX0 = 104;
      var pBarW = 440;
      var pMax = 22;
      var pTicks = [0, 5, 10, 15, 20];
      for (var ti = 0; ti < pTicks.length; ti++) {
        var tx = pBarX0 + (pTicks[ti] / pMax) * pBarW;
        pollSvg.appendChild(sEl('line', {
          x1: tx.toFixed(1), y1: '10', x2: tx.toFixed(1), y2: '156',
          stroke: C.border, 'stroke-width': '1', 'stroke-dasharray': ti === 0 ? '' : '4 4'
        }));
        pollSvg.appendChild(sEl('text', {
          x: tx.toFixed(1), y: '182', 'text-anchor': 'middle',
          fill: C.textMuted, 'font-family': FONT_MONO, 'font-size': '18'
        }, pTicks[ti] + ' s'));
      }

      // Row 1: T = 2 s (6.95 ± 0.18 s, 5/5)
      pollSvg.appendChild(sEl('text', {
        x: '0', y: '52', fill: C.emeraldBright,
        'font-family': FONT_MONO, 'font-size': '21', 'font-weight': '700'
      }, 'T = 2 s'));
      pollSvg.appendChild(sEl('rect', {
        x: pBarX0, y: '24', width: pBarW, height: '42', rx: '8',
        fill: hexAlpha(C.linkIdle, 0.16)
      }));
      var pollBar2 = sEl('rect', {
        x: pBarX0, y: '24', width: '0', height: '42', rx: '8',
        fill: C.emerald
      });
      pollSvg.appendChild(pollBar2);
      var w2X1 = pBarX0 + ((6.95 - 0.18) / pMax) * pBarW;
      var w2X2 = pBarX0 + ((6.95 + 0.18) / pMax) * pBarW;
      var pollWhisker2 = sEl('g', { opacity: '0' });
      pollWhisker2.appendChild(sEl('line', { x1: w2X1.toFixed(1), y1: '45', x2: w2X2.toFixed(1), y2: '45', stroke: C.text, 'stroke-width': '3' }));
      pollWhisker2.appendChild(sEl('line', { x1: w2X1.toFixed(1), y1: '36', x2: w2X1.toFixed(1), y2: '54', stroke: C.text, 'stroke-width': '2.5' }));
      pollWhisker2.appendChild(sEl('line', { x1: w2X2.toFixed(1), y1: '36', x2: w2X2.toFixed(1), y2: '54', stroke: C.text, 'stroke-width': '2.5' }));
      pollSvg.appendChild(pollWhisker2);
      var pollText2 = sEl('text', {
        x: '560', y: '52',
        fill: C.emeraldBright, 'font-family': FONT_MONO, 'font-size': '19', 'font-weight': '700', opacity: '0'
      }, '6.95 ± 0.18 s (5/5)');
      pollSvg.appendChild(pollText2);

      // Row 2: T = 5 s (18.93 ± 0.19 s, 5/5)
      pollSvg.appendChild(sEl('text', {
        x: '0', y: '124', fill: C.amber,
        'font-family': FONT_MONO, 'font-size': '21', 'font-weight': '700'
      }, 'T = 5 s'));
      pollSvg.appendChild(sEl('rect', {
        x: pBarX0, y: '96', width: pBarW, height: '42', rx: '8',
        fill: hexAlpha(C.linkIdle, 0.16)
      }));
      var pollBar5 = sEl('rect', {
        x: pBarX0, y: '96', width: '0', height: '42', rx: '8',
        fill: C.amber
      });
      pollSvg.appendChild(pollBar5);
      var w5X1 = pBarX0 + ((18.93 - 0.19) / pMax) * pBarW;
      var w5X2 = pBarX0 + ((18.93 + 0.19) / pMax) * pBarW;
      var pollWhisker5 = sEl('g', { opacity: '0' });
      pollWhisker5.appendChild(sEl('line', { x1: w5X1.toFixed(1), y1: '117', x2: w5X2.toFixed(1), y2: '117', stroke: C.text, 'stroke-width': '3' }));
      pollWhisker5.appendChild(sEl('line', { x1: w5X1.toFixed(1), y1: '108', x2: w5X1.toFixed(1), y2: '126', stroke: C.text, 'stroke-width': '2.5' }));
      pollWhisker5.appendChild(sEl('line', { x1: w5X2.toFixed(1), y1: '108', x2: w5X2.toFixed(1), y2: '126', stroke: C.text, 'stroke-width': '2.5' }));
      pollSvg.appendChild(pollWhisker5);
      var pollText5 = sEl('text', {
        x: '560', y: '124',
        fill: C.text, 'font-family': FONT_MONO, 'font-size': '19', 'font-weight': '700', opacity: '0'
      }, '18.93 ± 0.19 s (5/5)');
      pollSvg.appendChild(pollText5);

      cardB.appendChild(pollSvg);
      cardB.appendChild(el('div', {
        fontFamily: FONT_MONO,
        fontSize: '18px',
        color: C.textMuted
      }, 'T = 2 s detected congestion 11.98 s faster (~2.72×) across all 5/5 rounds.'));

      // ── CARD C (Bottom-Left): Congestion Threshold Sensitivity ───────
      var cardCBadge = el('div', {
        padding: '6px 12px',
        borderRadius: '10px',
        fontFamily: FONT_MONO,
        fontSize: '19px',
        fontWeight: '700',
        backgroundColor: hexAlpha(C.emerald, 0.18),
        border: '1.5px solid ' + C.emerald,
        color: C.emeraldBright,
        whiteSpace: 'nowrap',
        flexShrink: '0'
      }, 'θ = 70% DEFAULT ✓');
      var cardC = makeCard(
        96, 598,
        'CARD C · threshold-20261125T205244Z (n = 5)',
        'Congestion Threshold Sensitivity',
        'T = 2 s · EWMA α = 0.5 · 2 periods · all 3 detect 5/5',
        cardCBadge
      );

      var threshList = el('div', {
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
      });
      var threshData = [
        { label: 'θ = 60%', rate: '5 / 5', time: 6.81, timeTxt: '6.81 ± 0.13 s', note: 'Early trigger', col: C.cyan, hi: false },
        { label: 'θ = 70%', rate: '5 / 5', time: 6.95, timeTxt: '6.95 ± 0.18 s', note: 'Default ✓', col: C.emeraldBright, hi: true },
        { label: 'θ = 80%', rate: '5 / 5', time: 8.93, timeTxt: '8.93 ± 0.11 s', note: '+1.98 s slower', col: C.amber, hi: false }
      ];
      var threshBars = [];
      for (var tIdx = 0; tIdx < threshData.length; tIdx++) {
        var td = threshData[tIdx];
        var tRow = el('div', {
          height: '66px',
          borderRadius: '12px',
          backgroundColor: td.hi ? hexAlpha(C.emerald, 0.11) : hexAlpha(C.bg, 0.72),
          border: '1.5px solid ' + (td.hi ? C.emerald : C.border),
          padding: '0 14px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          boxSizing: 'border-box',
          fontFamily: FONT_MONO,
          fontVariantNumeric: 'tabular-nums'
        });

        tRow.appendChild(el('span', {
          width: '88px',
          fontSize: '20px',
          fontWeight: '700',
          color: td.col,
          flexShrink: '0'
        }, td.label));

        tRow.appendChild(el('span', {
          width: '68px',
          textAlign: 'center',
          padding: '4px 6px',
          borderRadius: '8px',
          fontSize: '18px',
          fontWeight: '700',
          backgroundColor: hexAlpha(td.col, 0.18),
          color: td.col,
          flexShrink: '0'
        }, td.rate));

        // GPU scaleX bar track (0..10.5 s)
        var bTrack = el('div', {
          flex: '1',
          height: '20px',
          borderRadius: '6px',
          backgroundColor: hexAlpha(C.linkIdle, 0.22),
          overflow: 'hidden'
        });
        var bFill = el('div', {
          width: '100%',
          height: '100%',
          borderRadius: '6px',
          backgroundColor: td.col,
          transformOrigin: 'left center',
          transform: 'scaleX(0)'
        });
        bTrack.appendChild(bFill);
        tRow.appendChild(bTrack);

        tRow.appendChild(el('span', {
          width: '164px',
          textAlign: 'right',
          fontSize: '19px',
          fontWeight: '700',
          color: C.text,
          flexShrink: '0',
          whiteSpace: 'nowrap'
        }, td.timeTxt));

        tRow.appendChild(el('span', {
          width: '154px',
          textAlign: 'right',
          fontSize: '18px',
          fontWeight: '700',
          color: td.hi ? C.emeraldBright : (tIdx === 2 ? C.amber : C.textMuted),
          flexShrink: '0',
          whiteSpace: 'nowrap'
        }, td.note));

        threshList.appendChild(tRow);
        threshBars.push({ fill: bFill, frac: td.time / 10.5, row: tRow });
      }
      cardC.appendChild(threshList);
      cardC.appendChild(el('div', {
        fontFamily: FONT_MONO,
        fontSize: '18px',
        color: C.textMuted
      }, 'Scale 0–10.5 s · all 3 detect 5/5 (θ = 80% is +1.98 s slower).'));

      // ── CARD D (Bottom-Right): 10-Flow Policy Benchmark ──────────────
      var cardDBadge = el('div', {
        padding: '6px 12px',
        borderRadius: '10px',
        fontFamily: FONT_MONO,
        fontSize: '19px',
        fontWeight: '700',
        backgroundColor: hexAlpha(C.emerald, 0.18),
        border: '1.5px solid ' + C.emerald,
        color: C.emeraldBright,
        whiteSpace: 'nowrap',
        flexShrink: '0'
      }, 'ECMP LOWEST');
      var cardD = makeCard(
        974, 598,
        'CARD D · ten-flows-20261125T200721Z (n = 5)',
        '10-Flow Policy Benchmark: Peak TX Util',
        '144.0 Mbps delivered · 64k HTB burst · mean ± SD & loss',
        cardDBadge
      );

      // SVG Horizontal Policy Comparison Bars with ±SD whiskers (802 x 172)
      var polSvg = sEl('svg', { viewBox: '0 0 802 172', width: '802', height: '172' });
      var dX0 = 114;
      var dW = 320;
      var dMax = 75; // percent scale
      var dPolicies = [
        { name: 'ECMP', val: 47.96, sdVal: 4.74, valTxt: '47.96 ± 4.74%', lossTxt: '0 lost/3.67M', col: C.emeraldBright, lossCol: C.emeraldBright },
        { name: 'Shortest', val: 56.20, sdVal: 14.99, valTxt: '56.20 ± 14.99%', lossTxt: '0 lost/3.67M', col: C.cyan, lossCol: C.textMuted },
        { name: 'Balanced', val: 56.50, sdVal: 15.13, valTxt: '56.50 ± 15.13%', lossTxt: '18 lost/3.67M', col: C.amber, lossCol: C.amber }
      ];
      var polBars = [];
      for (var dp = 0; dp < dPolicies.length; dp++) {
        var pol = dPolicies[dp];
        var py = 10 + dp * 54;
        polSvg.appendChild(sEl('text', {
          x: '0', y: (py + 25).toFixed(0),
          fill: pol.col, 'font-family': FONT_MONO, 'font-size': '20', 'font-weight': '700'
        }, pol.name));
        polSvg.appendChild(sEl('rect', {
          x: dX0, y: py, width: dW, height: '34', rx: '7',
          fill: hexAlpha(C.linkIdle, 0.18)
        }));
        var pb = sEl('rect', {
          x: dX0, y: py, width: '0', height: '34', rx: '7',
          fill: pol.col
        });
        polSvg.appendChild(pb);

        var dw1 = dX0 + ((pol.val - pol.sdVal) / dMax) * dW;
        var dw2 = dX0 + ((pol.val + pol.sdVal) / dMax) * dW;
        var pWhisk = sEl('g', { opacity: '0' });
        pWhisk.appendChild(sEl('line', { x1: dw1.toFixed(1), y1: String(py + 17), x2: dw2.toFixed(1), y2: String(py + 17), stroke: C.text, 'stroke-width': '2.5' }));
        pWhisk.appendChild(sEl('line', { x1: dw1.toFixed(1), y1: String(py + 10), x2: dw1.toFixed(1), y2: String(py + 24), stroke: C.text, 'stroke-width': '2' }));
        pWhisk.appendChild(sEl('line', { x1: dw2.toFixed(1), y1: String(py + 10), x2: dw2.toFixed(1), y2: String(py + 24), stroke: C.text, 'stroke-width': '2' }));
        polSvg.appendChild(pWhisk);

        var pt = sEl('text', {
          x: '448', y: (py + 25).toFixed(0),
          fill: C.text, 'font-family': FONT_MONO, 'font-size': '19', 'font-weight': '700', opacity: '0'
        }, pol.valTxt);
        polSvg.appendChild(pt);

        var pl = sEl('text', {
          x: '800', y: (py + 25).toFixed(0), 'text-anchor': 'end',
          fill: pol.lossCol, 'font-family': FONT_MONO, 'font-size': '18', 'font-weight': '600', opacity: '0'
        }, pol.lossTxt);
        polSvg.appendChild(pl);

        polBars.push({ bar: pb, whisk: pWhisk, txt: pt, loss: pl, targetW: (pol.val / dMax) * dW });
      }
      cardD.appendChild(polSvg);

      cardD.appendChild(el('div', {
        padding: '9px 14px',
        borderRadius: '10px',
        backgroundColor: hexAlpha(C.amber, 0.09),
        borderLeft: '4px solid ' + C.amber,
        fontSize: '18px',
        fontWeight: '500',
        color: C.text
      }, 'All 3 deliver 144.0 Mbps; reactive balancing lets brief peaks form before rerouting.'));

      return {
        header: header,
        cards: [cardA, cardB, cardC, cardD],
        lossBars: lossBars,
        cardABadge: cardABadge,
        blockH1: blockH1,
        blockH3: blockH3,
        phasesStrip: phasesStrip,
        pollBar2: pollBar2,
        pollBar5: pollBar5,
        pollWhisker2: pollWhisker2,
        pollWhisker5: pollWhisker5,
        pollText2: pollText2,
        pollText5: pollText5,
        cardBBadge: cardBBadge,
        threshBars: threshBars,
        polBars: polBars,
        cardDBadge: cardDBadge
      };
    },

    update: function (state, localT, globalT, api) {
      var E = api.EASE;
      var M = api.math;
      var D = api.dom;

      // Header + 2x2 grid entrance (stagger 60ms × 4 = 0.24s <= 0.50s)
      D.setFadeSlide(state.header, M.seg(localT, 0.0, 0.42, E.power3Out), 18, 0.98);
      for (var i = 0; i < state.cards.length; i++) {
        var cp = M.stagger(localT, 0.08, i, 0.06, 0.48, E.power3Out);
        D.setFadeSlide(state.cards[i], cp, 22, 0.95);
      }

      // ── Wave 1 (0.7..2.6s): Card A — Grid Load Balancing ─────────────
      for (var lb = 0; lb < state.lossBars.length; lb++) {
        var bInfo = state.lossBars[lb];
        var bPreP = M.seg(localT, 0.70 + lb * 0.22, 0.72, E.power4Out);
        var bPostP = M.seg(localT, 1.08 + lb * 0.22, 0.72, E.power4Out);
        bInfo.beforeBar.setAttribute('width', (bInfo.beforeW * bPreP).toFixed(1));
        bInfo.afterBar.setAttribute('width', (bInfo.afterW * bPostP).toFixed(1));
      }
      D.setFadeSlide(state.cardABadge, M.seg(localT, 1.55, 0.45, E.power3Out), 8, 0.94);
      D.setFadeSlide(state.phasesStrip, M.seg(localT, 1.75, 0.45, E.power3Out), 10, 0.96);

      // ── Wave 2 (2.4..4.4s): Card B — Polling T=2s vs T=5s ────────────
      var pBarW = 440;
      var pMax = 22;
      var p2P = M.seg(localT, 2.40, 0.85, E.power4Out);
      var p5P = M.seg(localT, 2.75, 0.95, E.power4Out);
      var w2 = (6.95 / pMax) * pBarW * p2P;
      var w5 = (18.93 / pMax) * pBarW * p5P;
      state.pollBar2.setAttribute('width', w2.toFixed(1));
      state.pollBar5.setAttribute('width', w5.toFixed(1));

      // ±SD Whiskers & right-column labels fade in cleanly once bars settle
      var w2Op = M.seg(localT, 3.15, 0.40, E.power3Out);
      state.pollWhisker2.setAttribute('opacity', w2Op.toFixed(3));
      state.pollText2.setAttribute('opacity', w2Op.toFixed(3));

      var w5Op = M.seg(localT, 3.45, 0.40, E.power3Out);
      state.pollWhisker5.setAttribute('opacity', w5Op.toFixed(3));
      state.pollText5.setAttribute('opacity', w5Op.toFixed(3));

      D.setFadeSlide(state.cardBBadge, M.seg(localT, 3.60, 0.45, E.power3Out), 8, 0.94);

      // ── Wave 3 (4.5..6.8s): Card C — Threshold Sensitivity ───────────
      for (var tIdx = 0; tIdx < state.threshBars.length; tIdx++) {
        var tb = state.threshBars[tIdx];
        var tp = M.stagger(localT, 4.50, tIdx, 0.14, 0.80, E.power4Out);
        tb.fill.style.transform = 'scaleX(' + (tb.frac * tp).toFixed(4) + ')';
      }

      // ── Wave 4 (6.6..9.0s): Card D — 10-Flow Policy Benchmark ────────
      for (var dp = 0; dp < state.polBars.length; dp++) {
        var pb = state.polBars[dp];
        var pp = M.stagger(localT, 6.60, dp, 0.14, 0.85, E.power4Out);
        var pop = M.stagger(localT, 7.10, dp, 0.12, 0.35, E.power3Out);
        pb.bar.setAttribute('width', (pb.targetW * pp).toFixed(1));
        pb.whisk.setAttribute('opacity', pop.toFixed(3));
        pb.txt.setAttribute('opacity', pop.toFixed(3));
        pb.loss.setAttribute('opacity', pop.toFixed(3));
      }
      D.setFadeSlide(state.cardDBadge, M.seg(localT, 7.60, 0.45, E.power3Out), 8, 0.94);
    }
  });
})();
