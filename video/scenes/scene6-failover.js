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
  var P3_WAYPOINTS = ['H1', 'S1', 'S4', 'S5', 'S6', 'H6'];
  var P1_WAYPOINTS = ['H1', 'S1', 'S2', 'S3', 'S6', 'H6'];

  var PROBE_COUNT = 48;
  var LOST_PROBE_INDEX = 11; // Aligns cleanly with localT ~ 2.6s (S5-S6 cut)

  window.SDN_VIDEO.registerScene({
    id: 'scene6-failover',
    index: 5,
    title: 'Automatic Link-Failure Recovery (S5–S6 Cut)',
    chapter: '06 / FAULT TOLERANCE',
    start: 59,
    duration: 12,

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

      // ── Header (x: 96..1824, y: 90..186) ─────────────────────────────
      var header = el('div', {
        position: 'absolute',
        left: '96px',
        top: '90px',
        width: '1728px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px'
      });
      var headRow = el('div', {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '24px'
      });
      headRow.appendChild(el('div', {
        fontSize: '46px',
        fontWeight: '700',
        letterSpacing: '-0.025em',
        lineHeight: '1.1',
        color: C.text
      }, 'Automatic Link-Failure Recovery (S5–S6 Cut)'));

      var statusPill = el('div', {
        padding: '10px 20px',
        borderRadius: '999px',
        fontFamily: FONT_MONO,
        fontSize: '18px',
        fontWeight: '700',
        letterSpacing: '0.07em',
        textTransform: 'uppercase',
        border: '1.5px solid ' + C.emerald,
        backgroundColor: hexAlpha(C.emerald, 0.14),
        color: C.emeraldBright,
        whiteSpace: 'nowrap'
      }, 'ACTIVE · P3 [S1-S4-S5-S6]');
      headRow.appendChild(statusPill);
      header.appendChild(headRow);

      header.appendChild(el('div', {
        fontSize: '20px',
        fontWeight: '500',
        color: C.textMuted,
        lineHeight: '1.25'
      }, 'S5–S6 cut triggers EventLinkDelete → rebuild_routes(): H1→H6 shifts P3→P1 (79/80 demo); H2→H6 5-run benchmark recovers in 73.14 ms & restores on EventLinkAdd.'));
      wrap.appendChild(header);

      // ── Left Column: Grid Diagram Card (x: 96..980, y: 196..810) ─────
      var gridCard = el('div', {
        position: 'absolute',
        left: '96px',
        top: '196px',
        width: '884px',
        height: '614px',
        backgroundColor: C.surface,
        border: '1.5px solid ' + C.border,
        borderRadius: '18px',
        overflow: 'hidden',
        boxSizing: 'border-box',
        padding: '64px 16px 14px 16px'
      });
      wrap.appendChild(gridCard);

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

      // Dynamic Event Banner at top of Grid Card
      var eventBanner = el('div', {
        position: 'absolute',
        left: '20px',
        right: '20px',
        top: '14px',
        height: '42px',
        borderRadius: '10px',
        backgroundColor: hexAlpha(C.bg, 0.9),
        border: '1.5px solid ' + C.border,
        padding: '0 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontFamily: FONT_MONO,
        fontSize: '19px',
        fontWeight: '700',
        letterSpacing: '0.04em'
      });
      var bannerText = el('span', { color: C.emeraldBright }, 'NOMINAL · TRAFFIC ON P3 [S1-S4-S5-S6]');
      var bannerTag = el('span', {
        color: C.textMuted,
        fontSize: '18px',
        fontVariantNumeric: 'tabular-nums'
      }, 'S5–S6 UP');
      eventBanner.appendChild(bannerText);
      eventBanner.appendChild(bannerTag);
      gridCard.appendChild(eventBanner);

      // ── Right Column: 3 High-Impact KPI Cards (x: 1020..1824, y: 196..810)
      var rightCol = el('div', {
        position: 'absolute',
        left: '1020px',
        top: '196px',
        width: '804px',
        height: '614px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px'
      });
      wrap.appendChild(rightCol);

      var benchHeader = el('div', {
        height: '34px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontFamily: FONT_MONO,
        fontSize: '18px',
        letterSpacing: '0.06em',
        textTransform: 'uppercase'
      });
      benchHeader.appendChild(el('span', { color: C.cyan, fontWeight: '700' }, 'MEASURED RECOVERY · H2→H6 · n = 5 RUNS'));
      benchHeader.appendChild(el('span', { color: C.textMuted }, 'recovery-20261125T202848Z'));
      rightCol.appendChild(benchHeader);

      function makeKpiCard(accentColor, bigText, labelText, subText) {
        var card = el('div', {
          flex: '1',
          backgroundColor: C.surface,
          border: '1.5px solid ' + C.border,
          borderLeft: '6px solid ' + accentColor,
          borderRadius: '16px',
          padding: '18px 24px',
          boxSizing: 'border-box',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          gap: '6px'
        });
        var val = el('div', {
          fontFamily: FONT_MONO,
          fontSize: '48px',
          fontWeight: '700',
          lineHeight: '1.08',
          color: accentColor,
          fontVariantNumeric: 'tabular-nums',
          letterSpacing: '-0.02em'
        }, bigText);
        var lbl = el('div', {
          fontSize: '23px',
          fontWeight: '600',
          color: C.text
        }, labelText);
        var sub = el('div', {
          fontFamily: FONT_MONO,
          fontSize: '18px',
          color: C.textMuted,
          fontVariantNumeric: 'tabular-nums'
        }, subText);
        card.appendChild(val);
        card.appendChild(lbl);
        card.appendChild(sub);
        return { card: card, val: val };
      }

      var kpi1 = makeKpiCard(
        C.cyan,
        '73.14 ± 21.63 ms',
        'Mean time to first post-cut reply',
        'Observed range: 45.94–95.54 ms · H2→H6 recovery (n = 5)'
      );
      var kpi2 = makeKpiCard(
        C.emeraldBright,
        '99.46%',
        'ICMP probe delivery across 5 runs',
        '1,293 / 1,300 received · 7 lost total (1.4 ± 0.89 / run)'
      );
      var kpi3 = makeKpiCard(
        C.text,
        '5 / 5 Runs',
        'Verified reroute & link restoration',
        'H2→H6: [4-5-6]→[4-1-2-3-6]→[4-5-6] · H1→H6 single demo: 79/80'
      );
      rightCol.appendChild(kpi1.card);
      rightCol.appendChild(kpi2.card);
      rightCol.appendChild(kpi3.card);

      // ── Bottom Mini Ping-Timeline Strip (x: 96..1824, y: 828..994) ───
      var pingStrip = el('div', {
        position: 'absolute',
        left: '96px',
        top: '828px',
        width: '1728px',
        height: '166px',
        backgroundColor: C.surface,
        border: '1.5px solid ' + C.border,
        borderRadius: '18px',
        boxSizing: 'border-box',
        padding: '16px 26px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between'
      });
      wrap.appendChild(pingStrip);

      var stripTop = el('div', {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontFamily: FONT_MONO,
        fontSize: '18px'
      });
      stripTop.appendChild(el('span', {
        color: C.cyan,
        fontWeight: '700',
        letterSpacing: '0.06em',
        textTransform: 'uppercase'
      }, 'ICMP PROBE STREAM · H2→H6 5-RUN RECOVERY PATTERN (50 ms INTERVAL)'));

      var stripLegend = el('div', { display: 'flex', gap: '24px', color: C.textMuted });
      var sLeg = [
        { col: C.emeraldBright, txt: '● Reply OK' },
        { col: C.crimson, txt: '× Lost at Cut (1.4 avg)' },
        { col: C.cyan, txt: '◆ Controller Event' }
      ];
      for (var li = 0; li < sLeg.length; li++) {
        stripLegend.appendChild(el('span', { color: sLeg[li].col, fontWeight: '600' }, sLeg[li].txt));
      }
      stripTop.appendChild(stripLegend);
      pingStrip.appendChild(stripTop);

      // SVG Probe Strip (1676 x 96)
      var probeSvg = sEl('svg', { viewBox: '0 0 1676 96', width: '1676', height: '96' });
      // Base rail
      probeSvg.appendChild(sEl('line', {
        x1: '24', y1: '46', x2: '1652', y2: '46',
        stroke: C.border, 'stroke-width': '2'
      }));

      // Event vertical markers: Cut (t=2.5s), Rebuild (t=3.6s), Restore (t=8.2s)
      function timeToX(tSec) {
        return 24 + (tSec / 11.4) * (1652 - 24);
      }

      var cutX = timeToX(2.5);
      var rebX = timeToX(3.6);
      var resX = timeToX(8.2);

      var cutMark = sEl('g', { opacity: '0' });
      cutMark.appendChild(sEl('line', { x1: cutX, y1: '14', x2: cutX, y2: '72', stroke: C.crimson, 'stroke-width': '2', 'stroke-dasharray': '4 3' }));
      cutMark.appendChild(sEl('text', {
        x: cutX, y: '92', 'text-anchor': 'middle', fill: C.crimson,
        'font-family': FONT_MONO, 'font-size': '18', 'font-weight': '700'
      }, 'S5–S6 CUT'));
      probeSvg.appendChild(cutMark);

      var rebMark = sEl('g', { opacity: '0' });
      rebMark.appendChild(sEl('line', { x1: rebX, y1: '14', x2: rebX, y2: '72', stroke: C.cyan, 'stroke-width': '2', 'stroke-dasharray': '4 3' }));
      rebMark.appendChild(sEl('text', {
        x: rebX + 18, y: '18', 'text-anchor': 'start', fill: C.cyan,
        'font-family': FONT_MONO, 'font-size': '18', 'font-weight': '700'
      }, '◆ EventLinkDelete → Alt Path (73.14 ms avg, H2→H6 n=5)'));
      probeSvg.appendChild(rebMark);

      var resMark = sEl('g', { opacity: '0' });
      resMark.appendChild(sEl('line', { x1: resX, y1: '14', x2: resX, y2: '72', stroke: C.cyan, 'stroke-width': '2', 'stroke-dasharray': '4 3' }));
      resMark.appendChild(sEl('text', {
        x: resX, y: '92', 'text-anchor': 'middle', fill: C.cyan,
        'font-family': FONT_MONO, 'font-size': '18', 'font-weight': '700'
      }, '◆ EventLinkAdd (Restored)'));
      probeSvg.appendChild(resMark);

      // 48 probe dots
      var probeNodes = [];
      for (var pIdx = 0; pIdx < PROBE_COUNT; pIdx++) {
        var px = 24 + (pIdx / (PROBE_COUNT - 1)) * (1652 - 24);
        var pTime = (pIdx / (PROBE_COUNT - 1)) * 11.4;
        if (pIdx === LOST_PROBE_INDEX) {
          var xGrp = sEl('g', { opacity: '0.2' });
          xGrp.appendChild(sEl('circle', {
            cx: px.toFixed(1), cy: '46', r: '12',
            fill: hexAlpha(C.crimson, 0.2), stroke: C.crimson, 'stroke-width': '2'
          }));
          xGrp.appendChild(sEl('line', { x1: (px - 5).toFixed(1), y1: '41', x2: (px + 5).toFixed(1), y2: '51', stroke: C.crimson, 'stroke-width': '2.5' }));
          xGrp.appendChild(sEl('line', { x1: (px + 5).toFixed(1), y1: '41', x2: (px - 5).toFixed(1), y2: '51', stroke: C.crimson, 'stroke-width': '2.5' }));
          probeSvg.appendChild(xGrp);
          probeNodes.push({ el: xGrp, t: pTime, lost: true });
        } else {
          var dot = sEl('circle', {
            cx: px.toFixed(1), cy: '46', r: '8',
            fill: C.emeraldBright, opacity: '0.16'
          });
          probeSvg.appendChild(dot);
          probeNodes.push({ el: dot, t: pTime, lost: false });
        }
      }

      // Sweep playhead cursor
      var playhead = sEl('line', {
        x1: '24', y1: '26', x2: '24', y2: '66',
        stroke: C.text, 'stroke-width': '2.5', opacity: '0.85'
      });
      probeSvg.appendChild(playhead);
      pingStrip.appendChild(probeSvg);

      return {
        header: header,
        gridCard: gridCard,
        benchHeader: benchHeader,
        kpi1: kpi1,
        kpi2: kpi2,
        kpi3: kpi3,
        pingStrip: pingStrip,
        grid: grid,
        statusPill: statusPill,
        eventBanner: eventBanner,
        bannerText: bannerText,
        bannerTag: bannerTag,
        cutMark: cutMark,
        rebMark: rebMark,
        resMark: resMark,
        probeNodes: probeNodes,
        playhead: playhead
      };
    },

    update: function (state, localT, globalT, api) {
      var C = api.COLORS;
      var E = api.EASE;
      var M = api.math;
      var D = api.dom;

      // Entrances (hero visible <= 0.5s, capped stagger <= 0.35s)
      D.setFadeSlide(state.header, M.seg(localT, 0.0, 0.42, E.power3Out), 18, 0.98);
      D.setFadeSlide(state.gridCard, M.seg(localT, 0.06, 0.48, E.power3Out), 22, 0.95);
      D.setFadeSlide(state.benchHeader, M.seg(localT, 0.12, 0.42, E.power3Out), 14, 0.97);
      D.setFadeSlide(state.kpi1.card, M.seg(localT, 0.16, 0.48, E.power3Out), 20, 0.95);
      D.setFadeSlide(state.kpi2.card, M.seg(localT, 0.22, 0.48, E.power3Out), 20, 0.95);
      D.setFadeSlide(state.kpi3.card, M.seg(localT, 0.28, 0.48, E.power3Out), 20, 0.95);
      D.setFadeSlide(state.pingStrip, M.seg(localT, 0.24, 0.50, E.power3Out), 20, 0.96);

      // KPI 1 & 2 smooth numeric roll-up after failover triggers (3.8..4.8s)
      var kpiP = M.seg(localT, 3.8, 0.95, E.power4Out);
      if (localT < 3.8) {
        state.kpi1.val.textContent = '73.14 ± 21.63 ms';
        state.kpi2.val.textContent = '99.46%';
      } else {
        var msVal = M.lerp(0, 73.14, kpiP);
        var sdVal = M.lerp(0, 21.63, kpiP);
        var pctVal = M.lerp(90.00, 99.46, kpiP);
        state.kpi1.val.textContent = D.fmt(msVal, 2) + ' ± ' + D.fmt(sdVal, 2) + ' ms';
        state.kpi2.val.textContent = D.fmt(pctVal, 2) + '%';
      }

      // Status pill + Grid Event Banner choreography
      var isCut = localT >= 2.5 && localT < 8.2;
      var isFailover = localT >= 3.6;
      var isRestored = localT >= 8.2;

      if (localT < 2.5) {
        state.statusPill.textContent = 'ACTIVE · P3 [S1-S4-S5-S6]';
        state.statusPill.style.color = C.emeraldBright;
        state.statusPill.style.borderColor = C.emerald;
        state.statusPill.style.backgroundColor = hexAlpha(C.emerald, 0.14);

        state.eventBanner.style.borderColor = hexAlpha(C.emerald, 0.55);
        state.bannerText.textContent = 'NOMINAL · TRAFFIC FLOWING ON P3 [S1-S4-S5-S6]';
        state.bannerText.style.color = C.emeraldBright;
        state.bannerTag.textContent = 'S5–S6 UP';
        state.bannerTag.style.color = C.emeraldBright;
      } else if (localT < 3.6) {
        state.statusPill.textContent = 'LINK CUT · S5–S6 DOWN';
        state.statusPill.style.color = C.crimson;
        state.statusPill.style.borderColor = C.crimson;
        state.statusPill.style.backgroundColor = hexAlpha(C.crimson, 0.16);

        state.eventBanner.style.borderColor = C.crimson;
        state.bannerText.textContent = 'LINK FAILURE · S5–S6 CUT DETECTED';
        state.bannerText.style.color = C.crimson;
        state.bannerTag.textContent = 'S5–S6 DOWN';
        state.bannerTag.style.color = C.crimson;
      } else if (localT < 8.2) {
        var rebFlash = localT < 5.6;
        state.statusPill.textContent = 'REROUTED · P1 [S1-S2-S3-S6]';
        state.statusPill.style.color = rebFlash ? C.cyan : C.emeraldBright;
        state.statusPill.style.borderColor = rebFlash ? C.cyan : C.emerald;
        state.statusPill.style.backgroundColor = hexAlpha(rebFlash ? C.cyan : C.emerald, 0.15);

        state.eventBanner.style.borderColor = C.cyan;
        state.bannerText.textContent = 'EventLinkDelete → rebuild_routes() → P1 [S1-S2-S3-S6]';
        state.bannerText.style.color = C.cyan;
        state.bannerTag.textContent = 'FAILOVER ACTIVE';
        state.bannerTag.style.color = C.emeraldBright;
      } else {
        state.statusPill.textContent = 'RESTORED · EventLinkAdd';
        state.statusPill.style.color = C.emeraldBright;
        state.statusPill.style.borderColor = C.emerald;
        state.statusPill.style.backgroundColor = hexAlpha(C.emerald, 0.14);

        state.eventBanner.style.borderColor = C.emerald;
        state.bannerText.textContent = 'EventLinkAdd → S5–S6 RESTORED CLEANLY';
        state.bannerText.style.color = C.emeraldBright;
        state.bannerTag.textContent = 'S5–S6 UP';
        state.bannerTag.style.color = C.cyan;
      }

      // ── Grid SVG Choreography ────────────────────────────────────────
      var g = state.grid;
      if (g) {
        g.reset();
        if (typeof g.updateController === 'function') {
          var isReacting = (localT >= 3.6 && localT < 5.8) || (localT >= 8.2 && localT < 9.8);
          g.updateController({
            label: localT < 2.5 ? 'OS-KEN · MONITORING TOPOLOGY'
              : (localT < 3.6 ? 'OS-KEN · LINK DOWN DETECTED'
              : (localT < 8.2 ? 'OS-KEN · rebuild_routes() → P1' : 'OS-KEN · EventLinkAdd RESTORED')),
            color: (localT >= 2.5 && localT < 3.6) ? C.crimson : (isReacting ? C.cyan : C.emeraldBright),
            pulse: isReacting ? 0.9 : 0.35,
            dashOffset: -localT * (isReacting ? 42 : 18)
          });
        }
        for (var i = 0; i < ALL_LINKS.length; i++) {
          g.updateLink(ALL_LINKS[i], {
            color: C.linkIdle, width: 3, opacity: 0.45, dashed: false, glow: null, label: ''
          });
        }

        var cutAnim = M.seg(localT, 2.5, 0.42, E.power4Out);
        var restoreAnim = M.seg(localT, 8.2, 0.65, E.power3Out);
        var failoverAnim = M.seg(localT, 3.6, 0.60, E.power4Out);

        if (!isFailover) {
          // Active on P3 until cut
          var p3Opacity = localT < 2.5 ? 1.0 : M.lerp(1.0, 0.42, cutAnim);
          var p3Col = localT < 2.5 ? C.emeraldBright : C.amber;
          g.updateLink('S1-S4', { color: p3Col, width: 6, opacity: p3Opacity, glow: localT < 2.5 ? 'emerald' : null, label: localT < 2.5 ? 'P3' : '', labelColor: C.emeraldBright });
          g.updateLink('S4-S5', { color: p3Col, width: 6, opacity: p3Opacity, glow: localT < 2.5 ? 'emerald' : null });
          g.updateLink('S5-S6', {
            color: localT < 2.5 ? C.emeraldBright : C.crimson,
            width: localT < 2.5 ? 6 : 4,
            opacity: localT < 2.5 ? 1.0 : 0.75,
            dashed: localT >= 2.5,
            glow: localT < 2.5 ? 'emerald' : 'crimson',
            label: localT >= 2.5 ? 'CUT' : '',
            labelColor: C.crimson
          });
        } else {
          // Failover active on P1 [S1-S2-S3-S6]
          var p1W = M.lerp(3, 6.5, failoverAnim);
          g.updateLink('S1-S2', { color: C.emeraldBright, width: p1W, opacity: M.lerp(0.45, 1, failoverAnim), glow: 'emerald', label: 'FAILOVER P1', labelColor: C.emeraldBright });
          g.updateLink('S2-S3', { color: C.emeraldBright, width: p1W, opacity: M.lerp(0.45, 1, failoverAnim), glow: 'emerald' });
          g.updateLink('S3-S6', { color: C.emeraldBright, width: p1W, opacity: M.lerp(0.45, 1, failoverAnim), glow: 'emerald' });

          // S5-S6 cut until 8.2s, then restores cleanly with cyan pulse
          if (!isRestored) {
            g.updateLink('S5-S6', {
              color: C.crimson, width: 3.5, opacity: 0.65, dashed: true, glow: 'crimson', label: 'DOWN', labelColor: C.crimson
            });
          } else {
            var pulseGlow = localT < 9.8 ? 'cyan' : null;
            g.updateLink('S5-S6', {
              color: localT < 9.8 ? C.cyan : C.emerald,
              width: M.lerp(3.5, 4.5, restoreAnim),
              opacity: M.lerp(0.55, 0.9, restoreAnim),
              dashed: false,
              glow: pulseGlow,
              label: 'RESTORED ✓',
              labelColor: C.cyan
            });
          }
        }

        // Animated crimson X slash on S5-S6
        var cutProgress = 0;
        if (localT >= 2.5 && localT < 8.2) {
          cutProgress = cutAnim;
        } else if (localT >= 8.2) {
          cutProgress = 1 - restoreAnim;
        }
        g.setCut('S5-S6', M.clamp(cutProgress, 0, 1));

        // Switches
        for (var k = 0; k < ALL_SWITCHES.length; k++) {
          var sid = ALL_SWITCHES[k];
          var stroke = C.switchStroke;
          var fill = C.surface;
          var glow = null;
          var bText = '';
          var bCol = C.emerald;
          var bOp = 0;

          if (!isFailover) {
            if (sid === 'S1' || sid === 'S4' || sid === 'S5' || sid === 'S6') {
              var alertPair = localT >= 2.5 && (sid === 'S5' || sid === 'S6');
              stroke = alertPair ? C.crimson : C.emeraldBright;
              fill = hexAlpha(alertPair ? C.crimson : C.emerald, 0.16);
              glow = alertPair ? 'crimson' : 'emerald';
              bText = alertPair ? 'LINK DOWN' : 'P21';
              bCol = alertPair ? C.crimson : C.emerald;
              bOp = 1;
            }
          } else {
            if (sid === 'S1' || sid === 'S2' || sid === 'S3' || sid === 'S6') {
              stroke = C.emeraldBright;
              fill = hexAlpha(C.emerald, 0.16);
              glow = 'emerald';
              bText = 'P20';
              bCol = C.emerald;
              bOp = failoverAnim;
            }
            if (!isRestored && sid === 'S5') {
              stroke = C.crimson;
              glow = 'crimson';
            } else if (isRestored && localT < 9.8 && (sid === 'S5' || sid === 'S6')) {
              stroke = C.cyan;
              glow = 'cyan';
            }
          }

          g.updateSwitch(sid, {
            stroke: stroke, fill: fill, glow: glow,
            badgeText: bText, badgeColor: bCol, badgeOpacity: bOp, scale: 1.0
          });
        }

        // Hosts
        var hCol = (localT >= 2.5 && localT < 3.6) ? C.crimson : C.emeraldBright;
        g.updateHost('H1', { active: true, color: hCol, rateText: 'SRC' });
        g.updateHost('H6', { active: true, color: hCol, rateText: 'DST' });

        // Packet streams
        if (localT < 2.5) {
          g.setPackets('p3_stream', P3_WAYPOINTS, { t: localT, speed: 0.48, count: 8, color: C.emeraldBright, radius: 6, opacity: 1 });
          g.setPackets('p1_stream', P1_WAYPOINTS, { t: localT, speed: 0.48, count: 8, color: C.emeraldBright, radius: 6, opacity: 0 });
        } else if (localT < 3.6) {
          var dropOp = 1 - M.seg(localT, 2.5, 0.25, E.power3Out);
          g.setPackets('p3_stream', P3_WAYPOINTS, { t: localT, speed: 0.48, count: 8, color: C.crimson, radius: 6, opacity: dropOp });
          g.setPackets('p1_stream', P1_WAYPOINTS, { t: localT, speed: 0.48, count: 8, color: C.emeraldBright, radius: 6, opacity: 0 });
        } else {
          g.setPackets('p3_stream', P3_WAYPOINTS, { t: localT, speed: 0.48, count: 8, color: C.emeraldBright, radius: 6, opacity: 0 });
          g.setPackets('p1_stream', P1_WAYPOINTS, { t: localT, speed: 0.50, count: 8, color: C.emeraldBright, radius: 6, opacity: failoverAnim });
        }
      }

      // ── Bottom Ping-Timeline Strip Update ────────────────────────────
      var sweepT = M.clamp(localT, 0, 11.4);
      var headX = 24 + (sweepT / 11.4) * (1652 - 24);
      state.playhead.setAttribute('x1', headX.toFixed(1));
      state.playhead.setAttribute('x2', headX.toFixed(1));

      state.cutMark.setAttribute('opacity', M.seg(localT, 2.4, 0.3, E.power3Out).toFixed(3));
      state.rebMark.setAttribute('opacity', M.seg(localT, 3.5, 0.35, E.power3Out).toFixed(3));
      state.resMark.setAttribute('opacity', M.seg(localT, 8.1, 0.35, E.power3Out).toFixed(3));

      for (var pn = 0; pn < state.probeNodes.length; pn++) {
        var node = state.probeNodes[pn];
        var lit = M.seg(localT, node.t - 0.08, 0.16, E.power3Out);
        var op = M.lerp(0.16, 1.0, lit);
        node.el.setAttribute('opacity', op.toFixed(3));
      }
    }
  });
})();
