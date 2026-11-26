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

  var ALL_LINKS = ['S1-S2', 'S2-S3', 'S3-S6', 'S5-S6', 'S2-S5', 'S4-S5', 'S1-S4'];
  var ALL_SWITCHES = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6'];
  var P1_WAYPOINTS = ['H1', 'S1', 'S2', 'S3', 'S6', 'H6'];
  var P3_WAYPOINTS = ['H1', 'S1', 'S4', 'S5', 'S6', 'H6'];
  var H3_WAYPOINTS = ['H3', 'S2', 'S3', 'H5'];

  // Approximate switch centers in grid-svg viewBox (0 0 960 620) for overlay barrier pulse rings
  var RING_POS = {
    S6: { cx: 740, cy: 430 },
    S5: { cx: 480, cy: 430 },
    S4: { cx: 220, cy: 430 },
    S1: { cx: 220, cy: 230 }
  };

  window.SDN_VIDEO.registerScene({
    id: 'scene5-mbb',
    index: 4,
    title: 'Make-Before-Break Rerouting (Egress → Ingress)',
    chapter: '05 / MAKE-BEFORE-BREAK',
    start: 46,
    duration: 13,

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

      // ── Header (x: 96..1824, y: 92..192) ─────────────────────────────
      var header = el('div', {
        position: 'absolute',
        left: '96px',
        top: '90px',
        width: '1728px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      });
      var headRow = el('div', {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '24px'
      });
      var titleEl = el('div', {
        fontSize: '46px',
        fontWeight: '700',
        letterSpacing: '-0.025em',
        lineHeight: '1.1',
        color: C.text
      }, 'Make-Before-Break Rerouting (Egress → Ingress)');

      var phasePill = el('div', {
        padding: '10px 20px',
        borderRadius: '999px',
        fontFamily: FONT_MONO,
        fontSize: '18px',
        fontWeight: '700',
        letterSpacing: '0.07em',
        textTransform: 'uppercase',
        border: '1.5px solid ' + C.cyan,
        backgroundColor: hexAlpha(C.cyan, 0.12),
        color: C.cyan,
        whiteSpace: 'nowrap'
      }, 'PHASE 1 · REVERSE INSTALL + BARRIER ACK');

      headRow.appendChild(titleEl);
      headRow.appendChild(phasePill);

      var subEl = el('div', {
        fontSize: '22px',
        fontWeight: '500',
        color: C.textMuted,
        lineHeight: '1.25'
      }, 'Install P3 [S1-S4-S5-S6] at priority 21 from egress S6 back to ingress S1 before cutting over and deleting P1 prio 20.');

      header.appendChild(headRow);
      header.appendChild(subEl);
      wrap.appendChild(header);

      // ── Left Column (x: 96..980, w: 884, y: 204..996) ────────────────
      var leftCol = el('div', {
        position: 'absolute',
        left: '96px',
        top: '204px',
        width: '884px',
        height: '792px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px'
      });
      wrap.appendChild(leftCol);

      // Grid Card (h: 612)
      var gridCard = el('div', {
        position: 'relative',
        width: '884px',
        height: '612px',
        backgroundColor: C.surface,
        border: '1.5px solid ' + C.border,
        borderRadius: '18px',
        overflow: 'hidden',
        boxSizing: 'border-box',
        padding: '62px 16px 46px 16px'
      });
      leftCol.appendChild(gridCard);

      var grid = api.createGridDiagram({
        showController: true,
        showPorts: true,
        showIPs: false
      });
      if (grid && grid.svg) {
        grid.svg.style.width = '100%';
        grid.svg.style.height = '100%';
        grid.svg.style.display = 'block';
        gridCard.appendChild(grid.svg);
      }

      // Dedicated top banner inside grid card (zero overlap with SVG)
      var gridCallout = el('div', {
        position: 'absolute',
        left: '18px',
        right: '18px',
        top: '14px',
        height: '40px',
        padding: '0 16px',
        borderRadius: '10px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontFamily: FONT_MONO,
        fontSize: '18px',
        fontWeight: '700',
        letterSpacing: '0.04em',
        backgroundColor: hexAlpha(C.bg, 0.90),
        border: '1.5px solid ' + C.cyan,
        color: C.cyan,
        fontVariantNumeric: 'tabular-nums',
        boxSizing: 'border-box'
      }, 'INSTALLING P3: S6 → S5 → S4 → S1');
      gridCard.appendChild(gridCallout);

      // Overlay legend bar at bottom of grid card
      var legendBar = el('div', {
        position: 'absolute',
        left: '16px',
        right: '16px',
        bottom: '12px',
        height: '32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontFamily: FONT_MONO,
        fontSize: '18px',
        color: C.textMuted,
        padding: '0 8px'
      });
      var legendItems = [
        { color: C.amber, label: 'P1 Old (P20)' },
        { color: C.emerald, label: 'P3 New (P21)' },
        { color: C.cyan, label: 'Barrier ACK ✓' },
        { color: C.textMuted, label: 'H3→H5 Steady' }
      ];
      for (var li = 0; li < legendItems.length; li++) {
        var lWrap = el('div', { display: 'flex', alignItems: 'center', gap: '8px' });
        lWrap.appendChild(el('span', {
          display: 'inline-block',
          width: '12px',
          height: '12px',
          borderRadius: '50%',
          backgroundColor: legendItems[li].color
        }));
        lWrap.appendChild(el('span', { color: C.text }, legendItems[li].label));
        legendBar.appendChild(lWrap);
      }
      gridCard.appendChild(legendBar);

      // 3-Phase Protocol Timeline Strip (h: 164)
      var timelineCard = el('div', {
        position: 'relative',
        width: '884px',
        height: '164px',
        backgroundColor: C.surface,
        border: '1.5px solid ' + C.border,
        borderRadius: '18px',
        boxSizing: 'border-box',
        padding: '16px 22px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between'
      });
      leftCol.appendChild(timelineCard);

      var tlHeader = el('div', {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontFamily: FONT_MONO,
        fontSize: '18px',
        letterSpacing: '0.06em',
        textTransform: 'uppercase'
      });
      tlHeader.appendChild(el('span', { color: C.cyan, fontWeight: '700' }, 'MBB PROTOCOL PHASES (ILLUSTRATIVE SEQUENCE)'));
      var tlClock = el('span', {
        color: C.text,
        fontWeight: '700',
        fontVariantNumeric: 'tabular-nums'
      }, 'PHASE 1 / 3');
      tlHeader.appendChild(tlClock);
      timelineCard.appendChild(tlHeader);

      var phaseRow = el('div', {
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '12px',
        width: '100%'
      });
      var phaseDefs = [
        { title: 'Step 1 · Reverse Install', sub: 'S6→S5→S4→S1 + Barrier' },
        { title: 'Step 2 · Ingress Cutover', sub: 'S1 Atomic Switch to P3' },
        { title: 'Step 3 · Strict Delete', sub: 'OFPFC_DELETE_STRICT P20' }
      ];
      var phaseBoxes = [];
      for (var pi = 0; pi < phaseDefs.length; pi++) {
        var pBox = el('div', {
          padding: '10px 14px',
          borderRadius: '12px',
          backgroundColor: hexAlpha(C.bg, 0.7),
          border: '1.5px solid ' + C.border,
          boxSizing: 'border-box',
          minWidth: '0'
        });
        var pTitle = el('div', {
          fontSize: '19px',
          fontWeight: '700',
          color: C.text,
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis'
        }, phaseDefs[pi].title);
        var pSub = el('div', {
          fontFamily: FONT_MONO,
          fontSize: '18px',
          color: C.textMuted,
          marginTop: '4px',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis'
        }, phaseDefs[pi].sub);
        pBox.appendChild(pTitle);
        pBox.appendChild(pSub);
        phaseRow.appendChild(pBox);
        phaseBoxes.push({ box: pBox, title: pTitle, sub: pSub });
      }
      timelineCard.appendChild(phaseRow);

      // Deterministic progress bar track (GPU scaleX)
      var trackBg = el('div', {
        width: '100%',
        height: '8px',
        borderRadius: '999px',
        backgroundColor: hexAlpha(C.linkIdle, 0.35),
        overflow: 'hidden'
      });
      var trackFill = el('div', {
        width: '100%',
        height: '100%',
        borderRadius: '999px',
        backgroundColor: C.cyan,
        transformOrigin: 'left center',
        transform: 'scaleX(0)'
      });
      trackBg.appendChild(trackFill);
      timelineCard.appendChild(trackBg);

      // ── Right Column (x: 1020..1824, w: 804, y: 204..996) ────────────
      var rightCol = el('div', {
        position: 'absolute',
        left: '1020px',
        top: '204px',
        width: '804px',
        height: '792px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px'
      });
      wrap.appendChild(rightCol);

      // Card 1: 4-Step Protocol Checklist (h: 372)
      var checkCard = el('div', {
        width: '804px',
        height: '372px',
        backgroundColor: C.surface,
        border: '1.5px solid ' + C.border,
        borderRadius: '18px',
        boxSizing: 'border-box',
        padding: '20px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      });
      rightCol.appendChild(checkCard);

      var checkHead = el('div', {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      });
      checkHead.appendChild(el('span', {
        fontFamily: FONT_MONO,
        fontSize: '19px',
        fontWeight: '700',
        letterSpacing: '0.07em',
        color: C.cyan,
        textTransform: 'uppercase'
      }, 'OPENFLOW 1.3 MBB SEQUENCE'));
      checkHead.appendChild(el('span', {
        fontFamily: FONT_MONO,
        fontSize: '18px',
        color: C.textMuted
      }, 'prio 20 → 21'));
      checkCard.appendChild(checkHead);

      var stepSpecs = [
        { label: '1. S6 FLOW_MOD P21 + Barrier ✓', hop: 'EGRESS', start: 1.0, done: 1.55 },
        { label: '2. S5 FLOW_MOD P21 + Barrier ✓', hop: 'HOP 2', start: 2.2, done: 2.75 },
        { label: '3. S4 FLOW_MOD P21 + Barrier ✓', hop: 'HOP 3', start: 3.4, done: 3.95 },
        { label: '4. S1 Ingress Cutover + Strict Delete P20', hop: 'INGRESS', start: 4.6, done: 9.4 }
      ];
      var stepRows = [];
      for (var si = 0; si < stepSpecs.length; si++) {
        var row = el('div', {
          height: '66px',
          borderRadius: '12px',
          backgroundColor: hexAlpha(C.bg, 0.72),
          border: '1.5px solid ' + C.border,
          padding: '0 18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          boxSizing: 'border-box'
        });
        var leftGrp = el('div', { display: 'flex', alignItems: 'center', gap: '14px' });
        var dot = el('div', {
          width: '14px',
          height: '14px',
          borderRadius: '50%',
          backgroundColor: C.linkIdle,
          flexShrink: '0'
        });
        var lbl = el('span', {
          fontFamily: FONT_MONO,
          fontSize: '20px',
          fontWeight: '600',
          color: C.textMuted
        }, stepSpecs[si].label);
        leftGrp.appendChild(dot);
        leftGrp.appendChild(lbl);

        var badge = el('div', {
          padding: '5px 12px',
          borderRadius: '8px',
          fontFamily: FONT_MONO,
          fontSize: '18px',
          fontWeight: '700',
          letterSpacing: '0.04em',
          backgroundColor: hexAlpha(C.linkIdle, 0.2),
          color: C.textMuted,
          whiteSpace: 'nowrap'
        }, 'QUEUED');

        row.appendChild(leftGrp);
        row.appendChild(badge);
        checkCard.appendChild(row);
        stepRows.push({ row: row, dot: dot, lbl: lbl, badge: badge, spec: stepSpecs[si] });
      }

      // Middle Rollback Safety Pill (h: 72)
      var rollbackPill = el('div', {
        width: '804px',
        height: '72px',
        backgroundColor: hexAlpha(C.amber, 0.10),
        border: '1.5px solid ' + hexAlpha(C.amber, 0.55),
        borderLeft: '6px solid ' + C.amber,
        borderRadius: '14px',
        boxSizing: 'border-box',
        padding: '0 22px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px'
      });
      rollbackPill.appendChild(el('span', {
        fontFamily: FONT_MONO,
        fontSize: '18px',
        fontWeight: '700',
        letterSpacing: '0.07em',
        color: C.amber,
        textTransform: 'uppercase',
        whiteSpace: 'nowrap'
      }, 'ROLLBACK GUARD'));
      rollbackPill.appendChild(el('span', {
        fontSize: '21px',
        fontWeight: '600',
        color: C.text
      }, 'Auto-rollback on error / >10s timeout'));
      rightCol.appendChild(rollbackPill);

      // Bottom Card: Real Observed Telemetry (h: 316)
      var telemCard = el('div', {
        width: '804px',
        height: '316px',
        backgroundColor: C.surface,
        border: '1.5px solid ' + C.border,
        borderRadius: '18px',
        boxSizing: 'border-box',
        padding: '20px 24px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between'
      });
      rightCol.appendChild(telemCard);

      var telTop = el('div', {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      });
      telTop.appendChild(el('span', {
        fontFamily: FONT_MONO,
        fontSize: '18px',
        fontWeight: '700',
        letterSpacing: '0.06em',
        color: C.textMuted,
        textTransform: 'uppercase'
      }, 'OBSERVED TELEMETRY · grid-demo-20261117T193620Z'));
      var deltaBadge = el('span', {
        padding: '4px 12px',
        borderRadius: '999px',
        fontFamily: FONT_MONO,
        fontSize: '18px',
        fontWeight: '700',
        backgroundColor: hexAlpha(C.emerald, 0.18),
        color: C.emeraldBright,
        fontVariantNumeric: 'tabular-nums'
      }, '-42.57 pp');
      telTop.appendChild(deltaBadge);
      telemCard.appendChild(telTop);

      // Gauge + Readout row
      var gaugeRow = el('div', {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '24px'
      });
      var metricCol = el('div', { display: 'flex', flexDirection: 'column', gap: '4px', minWidth: '250px' });
      metricCol.appendChild(el('div', {
        fontFamily: FONT_MONO,
        fontSize: '19px',
        color: C.textMuted
      }, 'S2 → S3 TX UTILIZATION'));
      var utilReadout = el('div', {
        fontFamily: FONT_MONO,
        fontSize: '58px',
        fontWeight: '700',
        lineHeight: '1.02',
        color: C.amber,
        fontVariantNumeric: 'tabular-nums'
      }, '72.03%');
      var utilSub = el('div', {
        fontFamily: FONT_MONO,
        fontSize: '18px',
        color: C.textMuted,
        fontVariantNumeric: 'tabular-nums'
      }, '72.03% → 29.46% post-move');
      metricCol.appendChild(utilReadout);
      metricCol.appendChild(utilSub);
      gaugeRow.appendChild(metricCol);

      // SVG Horizontal Precision Gauge (470 x 106)
      var gaugeSvg = sEl('svg', { viewBox: '0 0 470 106', width: '470', height: '106' });
      // Background track
      gaugeSvg.appendChild(sEl('rect', {
        x: '10', y: '34', width: '450', height: '30', rx: '8',
        fill: hexAlpha(C.linkIdle, 0.22), stroke: C.border, 'stroke-width': '1.5'
      }));
      // Congested zone highlight (>70% => x: 10 + 450*0.7 = 325)
      gaugeSvg.appendChild(sEl('rect', {
        x: '325', y: '34', width: '135', height: '30', rx: '4',
        fill: hexAlpha(C.amber, 0.14)
      }));
      // Animated fill bar (scaleX via transform or rect width in SVG)
      var gaugeFill = sEl('rect', {
        x: '10', y: '34', width: '324', height: '30', rx: '8',
        fill: C.amber
      });
      gaugeSvg.appendChild(gaugeFill);
      // 70% threshold dashed line
      gaugeSvg.appendChild(sEl('line', {
        x1: '325', y1: '20', x2: '325', y2: '78',
        stroke: C.amber, 'stroke-width': '2.5', 'stroke-dasharray': '5 4'
      }));
      gaugeSvg.appendChild(sEl('text', {
        x: '325', y: '14', 'text-anchor': 'middle',
        fill: C.amber, 'font-family': FONT_MONO, 'font-size': '18', 'font-weight': '700'
      }, 'θ = 70%'));
      // Tick labels 0%, 50%, 100%
      gaugeSvg.appendChild(sEl('text', {
        x: '10', y: '96', 'text-anchor': 'start',
        fill: C.textMuted, 'font-family': FONT_MONO, 'font-size': '18'
      }, '0%'));
      gaugeSvg.appendChild(sEl('text', {
        x: '235', y: '96', 'text-anchor': 'middle',
        fill: C.textMuted, 'font-family': FONT_MONO, 'font-size': '18'
      }, '50%'));
      gaugeSvg.appendChild(sEl('text', {
        x: '460', y: '96', 'text-anchor': 'end',
        fill: C.textMuted, 'font-family': FONT_MONO, 'font-size': '18'
      }, '100%'));
      gaugeRow.appendChild(gaugeSvg);
      telemCard.appendChild(gaugeRow);

      // Verification footer pill inside telemetry card
      var verifyBar = el('div', {
        padding: '12px 16px',
        borderRadius: '12px',
        backgroundColor: hexAlpha(C.emerald, 0.14),
        border: '1.5px solid ' + hexAlpha(C.emerald, 0.55),
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontFamily: FONT_MONO,
        fontSize: '18px',
        color: C.text
      });
      verifyBar.appendChild(el('span', { color: C.emeraldBright, fontWeight: '700' }, 'VERIFIED OVS DUMP'));
      verifyBar.appendChild(el('span', { color: C.text }, 'H1→H6 prio 21 on all 4 switches · old prio 20 absent'));
      telemCard.appendChild(verifyBar);

      return {
        header: header,
        gridCard: gridCard,
        timelineCard: timelineCard,
        checkCard: checkCard,
        rollbackPill: rollbackPill,
        telemCard: telemCard,
        grid: grid,
        phasePill: phasePill,
        gridCallout: gridCallout,
        tlClock: tlClock,
        phaseBoxes: phaseBoxes,
        trackFill: trackFill,
        stepRows: stepRows,
        utilReadout: utilReadout,
        gaugeFill: gaugeFill,
        deltaBadge: deltaBadge,
        verifyBar: verifyBar
      };
    },

    update: function (state, localT, globalT, api) {
      var C = api.COLORS;
      var E = api.EASE;
      var M = api.math;
      var D = api.dom;

      // Smooth entrances (hero visible <= 0.5s, total group stagger <= 0.35s)
      D.setFadeSlide(state.header, M.seg(localT, 0.0, 0.45, E.power3Out), 18, 0.98);
      D.setFadeSlide(state.gridCard, M.seg(localT, 0.08, 0.50, E.power3Out), 22, 0.95);
      D.setFadeSlide(state.timelineCard, M.seg(localT, 0.16, 0.50, E.power3Out), 20, 0.96);
      D.setFadeSlide(state.checkCard, M.seg(localT, 0.12, 0.50, E.power3Out), 22, 0.95);
      D.setFadeSlide(state.rollbackPill, M.seg(localT, 0.22, 0.48, E.power3Out), 16, 0.96);
      D.setFadeSlide(state.telemCard, M.seg(localT, 0.28, 0.50, E.power3Out), 20, 0.95);

      // Phase classification
      var phaseIdx = localT < 6.0 ? 0 : (localT < 8.5 ? 1 : 2);
      var phaseLabels = [
        { text: 'PHASE 1 · REVERSE INSTALL + BARRIER ACK', color: C.cyan },
        { text: 'PHASE 2 · ATOMIC INGRESS CUTOVER (S1)', color: C.emeraldBright },
        { text: 'PHASE 3 · STRICT DELETE OLD PRIO 20', color: C.emerald }
      ];
      var activePhase = phaseLabels[phaseIdx];
      state.phasePill.textContent = activePhase.text;
      state.phasePill.style.color = activePhase.color;
      state.phasePill.style.borderColor = activePhase.color;
      state.phasePill.style.backgroundColor = hexAlpha(activePhase.color, 0.13);

      // Callout pill inside grid card (locked in sync with right checklist & switch ACK ✓)
      if (localT < 2.2) {
        state.gridCallout.textContent = localT >= 1.55
          ? 'STEP 1/4 · S6 FLOW_MOD P21 + BARRIER ✓'
          : 'STEP 1/4 · S6 FLOW_MOD P21...';
        state.gridCallout.style.color = localT >= 1.55 ? C.emeraldBright : C.cyan;
        state.gridCallout.style.borderColor = localT >= 1.55 ? C.emerald : C.cyan;
      } else if (localT < 3.4) {
        state.gridCallout.textContent = localT >= 2.75
          ? 'STEP 2/4 · S5 FLOW_MOD P21 + BARRIER ✓'
          : 'STEP 2/4 · S5 FLOW_MOD P21...';
        state.gridCallout.style.color = localT >= 2.75 ? C.emeraldBright : C.cyan;
        state.gridCallout.style.borderColor = localT >= 2.75 ? C.emerald : C.cyan;
      } else if (localT < 4.6) {
        state.gridCallout.textContent = localT >= 3.95
          ? 'STEP 3/4 · S4 FLOW_MOD P21 + BARRIER ✓'
          : 'STEP 3/4 · S4 FLOW_MOD P21...';
        state.gridCallout.style.color = localT >= 3.95 ? C.emeraldBright : C.cyan;
        state.gridCallout.style.borderColor = localT >= 3.95 ? C.emerald : C.cyan;
      } else if (localT < 6.0) {
        state.gridCallout.textContent = localT >= 5.20
          ? 'STEP 4/4 · S1 INGRESS P21 + BARRIER ✓'
          : 'STEP 4/4 · S1 INGRESS P21...';
        state.gridCallout.style.color = localT >= 5.20 ? C.emeraldBright : C.cyan;
        state.gridCallout.style.borderColor = localT >= 5.20 ? C.emerald : C.cyan;
      } else if (localT < 8.5) {
        state.gridCallout.textContent = 'ATOMIC CUTOVER · H1→H6 LIVE ON P3 (P21)';
        state.gridCallout.style.color = C.emeraldBright;
        state.gridCallout.style.borderColor = C.emerald;
      } else {
        state.gridCallout.textContent = 'OFPFC_DELETE_STRICT (PRIO 20) · P1 CLEARED';
        state.gridCallout.style.color = C.emeraldBright;
        state.gridCallout.style.borderColor = C.emerald;
      }

      // Phase indicator & illustrative progress rail (no animation-seconds shown as latency)
      state.tlClock.textContent = 'PHASE ' + (phaseIdx + 1) + ' / 3';
      var progress = M.clamp(localT / 13.0, 0, 1);
      state.trackFill.style.transform = 'scaleX(' + progress.toFixed(4) + ')';
      state.trackFill.style.backgroundColor = phaseIdx === 0 ? C.cyan : C.emerald;

      for (var pi = 0; pi < state.phaseBoxes.length; pi++) {
        var pb = state.phaseBoxes[pi];
        var isCur = pi === phaseIdx;
        var isDone = pi < phaseIdx;
        var accent = pi === 0 ? C.cyan : C.emerald;
        pb.box.style.borderColor = isCur ? accent : (isDone ? hexAlpha(C.emerald, 0.55) : C.border);
        pb.box.style.backgroundColor = isCur ? hexAlpha(accent, 0.14) : hexAlpha(C.bg, 0.7);
        pb.title.style.color = isCur ? C.text : (isDone ? C.emeraldBright : C.textMuted);
      }

      // 4-step checklist updates
      for (var si = 0; si < state.stepRows.length; si++) {
        var sr = state.stepRows[si];
        var sp = sr.spec;
        var isStep4 = si === 3;
        if (localT < sp.start) {
          sr.row.style.borderColor = C.border;
          sr.row.style.backgroundColor = hexAlpha(C.bg, 0.72);
          sr.dot.style.backgroundColor = C.linkIdle;
          sr.lbl.style.color = C.textMuted;
          sr.badge.textContent = 'QUEUED';
          sr.badge.style.backgroundColor = hexAlpha(C.linkIdle, 0.22);
          sr.badge.style.color = C.textMuted;
        } else if (localT < sp.done) {
          var isCutoverWaitingDel = isStep4 && localT >= 6.0;
          var col = isCutoverWaitingDel ? C.emeraldBright : C.cyan;
          sr.row.style.borderColor = col;
          sr.row.style.backgroundColor = hexAlpha(col, 0.12);
          sr.dot.style.backgroundColor = col;
          sr.lbl.style.color = C.text;
          sr.badge.textContent = isCutoverWaitingDel ? (localT >= 8.5 ? 'DEL P20...' : 'CUTOVER ✓') : 'FLOW_MOD...';
          sr.badge.style.backgroundColor = hexAlpha(col, 0.22);
          sr.badge.style.color = col;
        } else {
          sr.row.style.borderColor = hexAlpha(C.emerald, 0.65);
          sr.row.style.backgroundColor = hexAlpha(C.emerald, 0.11);
          sr.dot.style.backgroundColor = C.emeraldBright;
          sr.lbl.style.color = C.text;
          sr.badge.textContent = isStep4 ? 'CLEAN ✓' : 'BARRIER ✓';
          sr.badge.style.backgroundColor = hexAlpha(C.emerald, 0.22);
          sr.badge.style.color = C.emeraldBright;
        }
      }

      // Observed Telemetry Gauge (S2->S3: 72.03% -> 29.46% smoothly across 6.0..8.6s)
      var dropP = M.seg(localT, 6.0, 2.6, E.expoInOut);
      var utilVal = M.lerp(72.03, 29.46, dropP);
      state.utilReadout.textContent = D.fmt(utilVal, 2) + '%';
      var isHealthy = utilVal < 50;
      var gaugeCol = utilVal >= 70 ? C.amber : (isHealthy ? C.emerald : C.cyan);
      state.utilReadout.style.color = gaugeCol;
      state.gaugeFill.setAttribute('width', (450 * (utilVal / 100)).toFixed(1));
      state.gaugeFill.setAttribute('fill', gaugeCol);

      var deltaP = M.seg(localT, 7.6, 0.5, E.power3Out);
      D.setFadeSlide(state.deltaBadge, deltaP, 8, 0.94);

      var verP = M.seg(localT, 9.2, 0.55, E.power3Out);
      state.verifyBar.style.opacity = String(M.lerp(0.35, 1.0, verP));
      state.verifyBar.style.borderColor = verP > 0.5 ? C.emerald : C.border;

      // ── Grid SVG Update (100% pure function of localT) ───────────────
      var g = state.grid;
      if (!g) return;
      g.reset();

      if (typeof g.updateController === 'function') {
        var ctrlPulse = 0.5 + 0.5 * Math.sin(localT * 3.5);
        g.updateController({
          label: phaseIdx === 0 ? 'OS-KEN · FLOW_MOD + BARRIER' : (phaseIdx === 1 ? 'OS-KEN · INGRESS CUTOVER' : 'OS-KEN · DELETE_STRICT P20'),
          color: phaseIdx === 0 ? C.cyan : C.emeraldBright,
          pulse: phaseIdx === 0 ? (0.45 + ctrlPulse * 0.45) : 0.4,
          dashOffset: -localT * 26
        });
      }

      var cutover = localT >= 6.0;
      var deleteP = M.seg(localT, 8.5, 1.5, E.power3Out); // 0 -> 1 as P1 prio-20 deleted

      // Reverse-install hop progress
      var s6Inst = M.seg(localT, 1.0, 0.75, E.power3Out);
      var s5Inst = M.seg(localT, 2.2, 0.75, E.power3Out);
      var s4Inst = M.seg(localT, 3.4, 0.75, E.power3Out);
      var s1Inst = M.seg(localT, 4.6, 0.85, E.power3Out);

      // Base idle links
      for (var i = 0; i < ALL_LINKS.length; i++) {
        g.updateLink(ALL_LINKS[i], {
          color: C.linkIdle,
          width: 3,
          opacity: 0.45,
          dashed: false,
          glow: null,
          label: ''
        });
      }

      // Old P1 links (S1-S2, S2-S3, S3-S6)
      var p1Opacity = cutover ? M.lerp(0.68, 0.35, deleteP) : 0.92;
      var p1Col = cutover ? (deleteP > 0.65 ? C.linkIdle : C.amber) : C.amber;
      var p1Width = cutover ? M.lerp(4.5, 3, deleteP) : 5.5;
      var p1Dashed = cutover && deleteP < 0.85;

      g.updateLink('S1-S2', {
        color: p1Col,
        width: p1Width,
        opacity: p1Opacity,
        dashed: p1Dashed,
        dashOffset: -localT * 28,
        glow: cutover ? null : 'amber',
        label: cutover ? (deleteP < 0.85 ? 'DEL P20' : '') : 'P1 · P20',
        labelColor: C.amber
      });
      g.updateLink('S3-S6', {
        color: p1Col,
        width: p1Width,
        opacity: p1Opacity,
        dashed: p1Dashed,
        dashOffset: -localT * 28,
        glow: cutover ? null : 'amber',
        label: ''
      });

      // S2-S3 stays active for H3->H5! Transitions from congested 72.0% -> healthy 29.5%
      var s2s3Col = utilVal >= 65 ? C.amber : C.emerald;
      g.updateLink('S2-S3', {
        color: s2s3Col,
        width: utilVal >= 65 ? 6.5 : 5,
        opacity: 1,
        dashed: utilVal >= 65,
        dashOffset: -localT * 42,
        glow: utilVal >= 65 ? 'amber' : 'emerald',
        label: D.fmt(utilVal, 1) + '%',
        labelColor: s2s3Col
      });

      // New P3 links light up egress -> ingress: S5-S6, then S4-S5, then S1-S4
      var l56 = M.seg(localT, 1.5, 0.7, E.power3Out);
      var l45 = M.seg(localT, 2.7, 0.7, E.power3Out);
      var l14 = M.seg(localT, 3.9, 0.7, E.power3Out);
      var p3Pairs = [
        { id: 'S5-S6', p: l56, lbl: cutover ? 'P3 · P21' : '' },
        { id: 'S4-S5', p: l45, lbl: '' },
        { id: 'S1-S4', p: l14, lbl: cutover ? 'ACTIVE' : '' }
      ];
      for (var j = 0; j < p3Pairs.length; j++) {
        var pair = p3Pairs[j];
        if (pair.p > 0.01) {
          g.updateLink(pair.id, {
            color: cutover ? C.emeraldBright : C.cyan,
            width: cutover ? 6.5 : M.lerp(3, 5, pair.p),
            opacity: M.lerp(0.45, 1.0, pair.p),
            dashed: !cutover,
            dashOffset: localT * 24,
            glow: cutover ? 'emerald' : 'cyan',
            label: pair.lbl,
            labelColor: C.emeraldBright
          });
        }
      }

      // Switch states & reverse-order P21 / BARRIER ✓ badges
      var swMap = {
        S6: { inst: s6Inst, barAt: 1.55 },
        S5: { inst: s5Inst, barAt: 2.75 },
        S4: { inst: s4Inst, barAt: 3.95 },
        S1: { inst: s1Inst, barAt: 5.20 }
      };
      for (var k = 0; k < ALL_SWITCHES.length; k++) {
        var sid = ALL_SWITCHES[k];
        var info = swMap[sid];
        if (info) {
          var inBarFlash = localT >= info.barAt && localT < info.barAt + 0.75;
          var installed = info.inst > 0.05;
          var bText = '';
          var bCol = C.emerald;
          if (inBarFlash) {
            bText = 'ACK ✓';
            bCol = C.cyan;
          } else if (installed) {
            bText = 'P21';
            bCol = C.emerald;
          }
          g.updateSwitch(sid, {
            stroke: inBarFlash ? C.cyan : (installed ? C.emeraldBright : C.switchStroke),
            fill: installed ? hexAlpha(C.emerald, 0.18) : C.surface,
            glow: inBarFlash ? 'cyan' : (installed ? 'emerald' : null),
            badgeText: bText,
            badgeColor: bCol,
            badgeOpacity: info.inst,
            scale: inBarFlash ? 1.06 : 1.0
          });
        } else {
          // S2, S3 (on old P1 & H3->H5)
          var delFlash = localT >= 8.5 && localT < 9.6;
          g.updateSwitch(sid, {
            stroke: delFlash ? C.amber : (cutover ? C.switchStroke : C.amber),
            fill: C.surface,
            glow: delFlash ? 'amber' : null,
            badgeText: delFlash ? 'DEL P20' : (cutover ? '' : 'P20'),
            badgeColor: C.amber,
            badgeOpacity: delFlash ? 1 : (cutover ? 0 : 0.85),
            scale: 1.0
          });
        }
      }

      // Hosts
      g.updateHost('H1', { active: true, color: cutover ? C.emeraldBright : C.amber, rateText: '85M' });
      g.updateHost('H6', { active: true, color: cutover ? C.emeraldBright : C.amber, rateText: 'RX' });
      g.updateHost('H3', { active: true, color: s2s3Col, rateText: '30M' });
      g.updateHost('H5', { active: true, color: s2s3Col, rateText: 'RX' });

      // Packet streams (linear speed, deterministic)
      if (!cutover) {
        g.setPackets('h1_h6_p1', P1_WAYPOINTS, {
          t: localT, speed: 0.42, count: 8, color: C.amber, radius: 6, opacity: 0.95
        });
        g.setPackets('h1_h6_p3', P3_WAYPOINTS, {
          t: localT, speed: 0.48, count: 8, color: C.emeraldBright, radius: 6.5, opacity: 0
        });
      } else {
        g.setPackets('h1_h6_p1', P1_WAYPOINTS, {
          t: localT, speed: 0.42, count: 8, color: C.amber, radius: 6, opacity: 0
        });
        g.setPackets('h1_h6_p3', P3_WAYPOINTS, {
          t: localT, speed: 0.50, count: 9, color: C.emeraldBright, radius: 6.5, opacity: 1.0
        });
      }
      // H3->H5 continuous uninterrupted stream
      g.setPackets('h3_h5', H3_WAYPOINTS, {
        t: localT, speed: 0.55, count: 5, color: s2s3Col, radius: 5.5, opacity: 0.92
      });
    }
  });
})();
