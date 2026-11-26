(function () {
  'use strict';

  var FONT_SANS = '"Segoe UI", "Bahnschrift", Arial, sans-serif';
  var FONT_MONO = '"Cascadia Mono", "Cascadia Code", Consolas, monospace';

  function el(tag, style, text) {
    var node = document.createElement(tag);
    if (style) node.style.cssText = style;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function applyFadeSlide(node, p, dy, scaleFrom) {
    var c = p < 0 ? 0 : p > 1 ? 1 : p;
    var y = (1 - c) * (dy === undefined ? 20 : dy);
    var sf = scaleFrom === undefined ? 0.95 : scaleFrom;
    var sc = sf + (1 - sf) * c;
    node.style.opacity = c.toFixed(4);
    node.style.transform = 'translate3d(0,' + y.toFixed(2) + 'px,0) scale(' + sc.toFixed(4) + ')';
  }

  var ALL_LINKS = ['S1-S2', 'S2-S3', 'S3-S6', 'S1-S4', 'S4-S5', 'S5-S6', 'S2-S5'];

  window.SDN_VIDEO.registerScene({
    id: 'scene2-problem',
    index: 1,
    title: 'SDN Architecture & Static Bottleneck',
    chapter: '02 / ARCHITECTURE & BOTTLENECK',
    start: 9,
    duration: 12,

    mount: function (rootEl, api) {
      var C = api.COLORS;
      rootEl.innerHTML = '';

      var wrap = el(
        'div',
        'position:absolute;inset:0;width:1920px;height:1080px;overflow:hidden;' +
        'font-family:' + FONT_SANS + ';color:' + C.text + ';'
      );

      // HEADER (y: 94..160, x: 96..1824)
      var header = el(
        'div',
        'position:absolute;left:96px;top:94px;width:1728px;display:flex;' +
        'align-items:center;justify-content:space-between;will-change:transform,opacity;'
      );
      var title = el(
        'h2',
        'margin:0;font-size:48px;font-weight:700;letter-spacing:-0.025em;color:' + C.text + ';',
        '3-Layer SDN Architecture & Shortest-Path Bottleneck'
      );
      var specPill = el(
        'div',
        'padding:9px 20px;border-radius:999px;background:' + C.surface + ';' +
        'border:1px solid ' + C.border + ';font-family:' + FONT_MONO + ';font-size:19px;' +
        'font-weight:600;color:' + C.cyan + ';font-variant-numeric:tabular-nums;',
        '7 LINKS · 100 MBPS / 2 MS'
      );
      header.appendChild(title);
      header.appendChild(specPill);
      wrap.appendChild(header);

      // LEFT COLUMN: 3-Layer SDN Architecture Stack (x: 96..740, width 644px, y: 184..986)
      var leftCol = el(
        'div',
        'position:absolute;left:96px;top:184px;width:644px;height:802px;' +
        'display:flex;flex-direction:column;justify-content:space-between;'
      );

      var stackTitle = el(
        'div',
        'font-family:' + FONT_MONO + ';font-size:19px;font-weight:700;letter-spacing:0.09em;' +
        'color:' + C.textMuted + ';text-transform:uppercase;margin-bottom:4px;will-change:transform,opacity;',
        'THREE-LAYER CONTROL ARCHITECTURE'
      );
      leftCol.appendChild(stackTitle);

      function makeLayerCard(accentColor, badgeLabel, heading, lineA, chips) {
        var card = el(
          'div',
          'background:' + C.surface + ';border:1px solid ' + C.border + ';' +
          'border-left:5px solid ' + accentColor + ';border-radius:16px;' +
          'padding:20px 24px;box-shadow:0 12px 32px rgba(0,0,0,0.28);will-change:transform,opacity;'
        );
        var topRow = el(
          'div',
          'display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;'
        );
        var h3 = el(
          'div',
          'font-size:26px;font-weight:700;color:' + C.text + ';',
          heading
        );
        var tag = el(
          'span',
          'font-family:' + FONT_MONO + ';font-size:18px;font-weight:700;color:' + accentColor + ';' +
          'padding:4px 12px;border-radius:8px;background:rgba(7,14,13,0.65);border:1px solid ' + C.border + ';',
          badgeLabel
        );
        topRow.appendChild(h3);
        topRow.appendChild(tag);
        card.appendChild(topRow);

        var desc = el(
          'div',
          'font-family:' + FONT_MONO + ';font-size:20px;line-height:1.4;color:' + C.textMuted + ';margin-bottom:12px;',
          lineA
        );
        card.appendChild(desc);

        var chipRow = el('div', 'display:flex;flex-wrap:wrap;gap:10px;');
        for (var i = 0; i < chips.length; i++) {
          chipRow.appendChild(
            el(
              'span',
              'font-family:' + FONT_MONO + ';font-size:18px;font-weight:600;color:' + C.text + ';' +
              'background:rgba(22,58,49,0.55);border:1px solid ' + C.border + ';border-radius:8px;padding:5px 12px;',
              chips[i]
            )
          );
        }
        card.appendChild(chipRow);
        return card;
      }

      function makeConnector(labelText) {
        var row = el(
          'div',
          'display:flex;align-items:center;justify-content:center;gap:14px;padding:2px 0;will-change:transform,opacity;'
        );
        var arrowL = el('span', 'font-family:' + FONT_MONO + ';font-size:22px;font-weight:700;color:' + C.cyan + ';', '↕');
        var pill = el(
          'div',
          'padding:8px 18px;border-radius:999px;background:rgba(34,211,238,0.10);' +
          'border:1px solid rgba(34,211,238,0.45);font-family:' + FONT_MONO + ';font-size:19px;' +
          'font-weight:700;color:' + C.cyan + ';letter-spacing:0.02em;',
          labelText
        );
        var arrowR = el('span', 'font-family:' + FONT_MONO + ';font-size:22px;font-weight:700;color:' + C.cyan + ';', '↕');
        row.appendChild(arrowL);
        row.appendChild(pill);
        row.appendChild(arrowR);
        return row;
      }

      var layerApp = makeLayerCard(
        C.emeraldBright,
        'PORT :8081',
        'Application Layer',
        'Load Balancer Logic + Local Web Dashboard',
        ['C4 Monitor', 'Yen k=3', 'MBB Reroute']
      );
      var connNorth = makeConnector('Northbound REST API · 127.0.0.1:8080');
      var layerCtrl = makeLayerCard(
        C.cyan,
        'TCP :6653',
        'Control Plane',
        'OS-Ken 3.1.1 · OpenFlow 1.3 Controller',
        ['LLDP Discovery', 'Proxy ARP', 'OFP Stats']
      );
      var connSouth = makeConnector('Southbound OpenFlow 1.3 · FLOW_MOD');
      var layerData = makeLayerCard(
        C.emerald,
        'OVS + TCLINK',
        'Data Plane',
        'Mininet 2.3 + Open vSwitch · 100 Mbps / 2 ms',
        ['S1–S6 Switches', 'H1–H6 Hosts', '20 Ports']
      );

      var stackEls = [layerApp, connNorth, layerCtrl, connSouth, layerData];
      for (var k = 0; k < stackEls.length; k++) {
        leftCol.appendChild(stackEls[k]);
      }
      wrap.appendChild(leftCol);

      // RIGHT COLUMN: Animated 2x3 Grid + Bottleneck Callout (x: 780..1824, width 1044px, y: 184..986)
      var rightCol = el(
        'div',
        'position:absolute;left:780px;top:184px;width:1044px;height:802px;' +
        'display:flex;flex-direction:column;gap:14px;'
      );

      // Grid Viewport Card
      var gridCard = el(
        'div',
        'flex:1;min-height:0;background:rgba(15,30,27,0.88);border:1px solid ' + C.border + ';border-radius:18px;' +
        'display:flex;flex-direction:column;overflow:hidden;will-change:transform,opacity;'
      );

      // Grid Card Top Meter Bar (strictly single-line subtitle so SVG keeps full height)
      var meterBar = el(
        'div',
        'flex:0 0 auto;display:flex;align-items:center;justify-content:space-between;padding:12px 22px;' +
        'background:' + C.header + ';border-bottom:1px solid ' + C.border + ';gap:16px;'
      );
      var meterLeft = el('div', 'display:flex;flex-direction:column;gap:3px;min-width:0;');
      var meterTitle = el(
        'div',
        'font-family:' + FONT_MONO + ';font-size:18px;font-weight:700;letter-spacing:0.06em;color:' + C.textMuted + ';white-space:nowrap;',
        'SHARED LINK S2 → S3 OFFERED LOAD'
      );
      var meterSub = el(
        'div',
        'font-family:' + FONT_MONO + ';font-size:19px;font-weight:600;color:' + C.text + ';white-space:nowrap;',
        'H1→H6 (85M) on P1 [S1–S2–S3–S6]'
      );
      meterLeft.appendChild(meterTitle);
      meterLeft.appendChild(meterSub);

      var meterRight = el('div', 'display:flex;align-items:center;gap:16px;flex-shrink:0;');
      var loadNum = el(
        'div',
        'font-family:' + FONT_MONO + ';font-size:32px;font-weight:700;font-variant-numeric:tabular-nums;' +
        'color:' + C.emeraldBright + ';min-width:255px;text-align:right;white-space:nowrap;',
        '0 / 100 Mbps'
      );
      var barTrack = el(
        'div',
        'width:170px;height:15px;border-radius:8px;background:rgba(7,14,13,0.8);' +
        'border:1px solid ' + C.border + ';overflow:hidden;position:relative;'
      );
      var barFill = el(
        'div',
        'width:100%;height:100%;transform-origin:left center;background:' + C.emerald + ';will-change:transform;'
      );
      // 100% capacity marker at 86.9% of a 115% scale
      var capTick = el(
        'div',
        'position:absolute;top:0;bottom:0;left:86.9%;width:2px;background:' + C.text + ';opacity:0.75;'
      );
      barTrack.appendChild(barFill);
      barTrack.appendChild(capTick);
      meterRight.appendChild(loadNum);
      meterRight.appendChild(barTrack);

      meterBar.appendChild(meterLeft);
      meterBar.appendChild(meterRight);
      gridCard.appendChild(meterBar);

      // Grid SVG Body with generous bottom padding so H2/H4/H6 IPs & pills never clip
      var svgWrap = el(
        'div',
        'flex:1;min-height:0;display:flex;align-items:center;justify-content:center;padding:14px 20px 20px 20px;position:relative;'
      );
      var grid = api.createGridDiagram({ showController: false });
      grid.svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
      grid.svg.style.width = '100%';
      grid.svg.style.height = '100%';
      grid.svg.style.display = 'block';
      svgWrap.appendChild(grid.svg);
      gridCard.appendChild(svgWrap);
      rightCol.appendChild(gridCard);

      // Bottom Bottleneck Callout Card (compact so Grid SVG has full breathing room)
      var calloutCard = el(
        'div',
        'flex:0 0 auto;background:' + C.surface + ';border:2px solid ' + C.amber + ';border-radius:16px;' +
        'padding:16px 24px;display:flex;flex-direction:column;gap:8px;' +
        'box-shadow:0 12px 34px rgba(249,115,22,0.14);will-change:transform,opacity;'
      );
      var callTop = el('div', 'display:flex;align-items:center;justify-content:space-between;gap:16px;');
      var callBadge = el(
        'span',
        'padding:6px 14px;border-radius:8px;background:' + C.amberFill + ';' +
        'font-family:' + FONT_MONO + ';font-size:18px;font-weight:700;letter-spacing:0.06em;color:' + C.text + ';',
        'CONGESTION BOTTLENECK · 115% OFFERED'
      );
      var idleBadge = el(
        'span',
        'padding:6px 14px;border-radius:8px;background:rgba(78,107,96,0.22);border:1px solid ' + C.border + ';' +
        'font-family:' + FONT_MONO + ';font-size:18px;font-weight:700;color:' + C.textMuted + ';',
        'ALTERNATE P3 [S1–S4–S5–S6]: 0% IDLE'
      );
      callTop.appendChild(callBadge);
      callTop.appendChild(idleBadge);

      var callText = el(
        'div',
        'font-size:25px;font-weight:600;line-height:1.32;color:' + C.text + ';',
        'Static Shortest-Path Bottleneck: 115 Mbps offered on 100 Mbps S2–S3 while P3 sits unused.'
      );
      var callFoot = el(
        'div',
        'font-family:' + FONT_MONO + ';font-size:19px;color:' + C.textMuted + ';',
        'Canonical Dijkstra locks both H1→H6 (85M) and H3→H5 (30M) onto S2→S3 despite link-disjoint capacity below.'
      );
      calloutCard.appendChild(callTop);
      calloutCard.appendChild(callText);
      calloutCard.appendChild(callFoot);
      rightCol.appendChild(calloutCard);

      wrap.appendChild(rightCol);
      rootEl.appendChild(wrap);

      return {
        header: header,
        stackTitle: stackTitle,
        stackEls: stackEls,
        gridCard: gridCard,
        meterSub: meterSub,
        loadNum: loadNum,
        barFill: barFill,
        calloutCard: calloutCard,
        grid: grid
      };
    },

    update: function (state, localT, globalT, api) {
      var C = api.COLORS;
      var E = api.EASE;
      var M = api.math;

      // Immediate visible entry <= 0.5s
      applyFadeSlide(state.header, M.seg(localT, 0.0, 0.42, E.power4Out), 16, 0.96);
      applyFadeSlide(state.stackTitle, M.seg(localT, 0.08, 0.38, E.power3Out), 12, 0.96);
      applyFadeSlide(state.gridCard, M.seg(localT, 0.06, 0.44, E.power4Out), 18, 0.96);

      // 3-layer stack staggers in smoothly (5 items * 70ms = 350ms)
      for (var i = 0; i < state.stackEls.length; i++) {
        var sp = M.stagger(localT, 0.14, i, 0.07, 0.42, E.power3Out);
        applyFadeSlide(state.stackEls[i], sp, 16, 0.95);
      }

      // Phase timings:
      // 1.0..2.2s: H1->H6 (85 Mbps) ramps up on P1
      // 4.0..5.2s: H3->H5 (30 Mbps) joins on S2->S3 => 115 Mbps offered -> CONGESTED
      // 5.2..5.9s: P3 highlights as 0% IDLE + Bottleneck Callout Card enters
      var pFlow1 = M.seg(localT, 0.9, 1.1, E.power3Out);
      var pFlow2 = M.seg(localT, 4.0, 1.1, E.power3Out);
      var pIdleP3 = M.seg(localT, 5.2, 0.75, E.power3Out);
      var pCallout = M.seg(localT, 5.3, 0.55, E.power4Out);

      applyFadeSlide(state.calloutCard, pCallout, 20, 0.95);

      var offeredMbps = 85 * pFlow1 + 30 * pFlow2;
      var isCongested = localT >= 4.25;

      state.loadNum.textContent = Math.round(offeredMbps) + ' / 100 Mbps';
      state.loadNum.style.color = isCongested ? C.amber : C.emeraldBright;
      state.barFill.style.transform = 'scaleX(' + M.clamp(offeredMbps / 115, 0, 1).toFixed(4) + ')';
      state.barFill.style.background = isCongested ? C.amber : C.emerald;

      if (localT < 4.0) {
        state.meterSub.textContent = 'H1→H6 (85M) on P1 [S1–S2–S3–S6]';
        state.meterSub.style.color = C.text;
      } else {
        state.meterSub.textContent = 'H1→H6 (85M) + H3→H5 (30M) on S2→S3';
        state.meterSub.style.color = C.amber;
      }

      // Update 2x3 Grid SVG deterministically
      var grid = state.grid;
      if (typeof grid.reset === 'function') grid.reset();

      var amberPulse = 0.5 + 0.5 * Math.sin(localT * 6.0);

      for (var l = 0; l < ALL_LINKS.length; l++) {
        var id = ALL_LINKS[l];
        var drawP = M.stagger(localT, 0.12, l, 0.05, 0.72, E.power3Out);
        var isP1Outer = id === 'S1-S2' || id === 'S3-S6';
        var isBottleneck = id === 'S2-S3';
        var isP3 = id === 'S1-S4' || id === 'S4-S5' || id === 'S5-S6';

        var opts = {
          color: C.linkIdle,
          width: 3.5,
          opacity: 0.45,
          dashed: false,
          dashOffset: 0,
          drawProgress: drawP,
          label: '',
          labelColor: C.textMuted,
          glow: null
        };

        if (isP1Outer && pFlow1 > 0.05) {
          opts.color = C.emerald;
          opts.width = M.lerp(3.5, 5.5, pFlow1);
          opts.opacity = M.lerp(0.45, 0.98, pFlow1);
          opts.glow = pFlow1 > 0.5 ? 'emerald' : null;
          if (id === 'S1-S2') {
            opts.label = '85M';
            opts.labelColor = C.emeraldBright;
          }
        } else if (isBottleneck && pFlow1 > 0.05) {
          if (isCongested) {
            opts.color = C.amber;
            opts.width = 6.5 + 1.2 * amberPulse;
            opts.opacity = 1.0;
            opts.dashed = true;
            opts.dashOffset = -(localT * 48);
            opts.glow = 'amber';
            opts.label = '115M · CONGESTED';
            opts.labelColor = C.amber;
          } else {
            opts.color = C.emerald;
            opts.width = M.lerp(3.5, 5.5, pFlow1);
            opts.opacity = M.lerp(0.45, 1.0, pFlow1);
            opts.glow = 'emerald';
            opts.label = Math.round(offeredMbps) + 'M';
            opts.labelColor = C.emeraldBright;
          }
        } else if (isP3 && pIdleP3 > 0.05) {
          opts.color = C.cyan;
          opts.width = 3.8;
          opts.opacity = M.lerp(0.45, 0.62, pIdleP3);
          opts.dashed = true;
          opts.dashOffset = 0;
          if (id === 'S4-S5') {
            opts.label = 'P3 · 0% IDLE';
            opts.labelColor = C.cyan;
          }
        }

        grid.updateLink(id, opts);
      }

      // Switches
      var swIds = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6'];
      for (var s = 0; s < swIds.length; s++) {
        var sw = swIds[s];
        var hot = isCongested && (sw === 'S2' || sw === 'S3');
        var onP1 = pFlow1 > 0.2 && (sw === 'S1' || sw === 'S2' || sw === 'S3' || sw === 'S6');
        grid.updateSwitch(sw, {
          stroke: hot ? C.amber : (onP1 ? C.emerald : C.switchStroke),
          fill: C.surface,
          glow: hot ? 'amber' : (onP1 ? 'emerald' : null),
          badgeText: hot ? '115%' : (onP1 ? 'P20' : ''),
          badgeColor: hot ? C.amber : C.emeraldFill,
          badgeOpacity: hot ? (0.85 + 0.15 * amberPulse) : (onP1 ? 0.85 : 0),
          scale: hot ? (1.02 + 0.02 * amberPulse) : 1
        });
      }

      // Hosts
      grid.updateHost('H1', { active: pFlow1 > 0.1, color: C.emeraldBright, rateText: pFlow1 > 0.2 ? '85 Mbps' : '' });
      grid.updateHost('H6', { active: pFlow1 > 0.1, color: C.emeraldBright, rateText: pFlow1 > 0.2 ? 'RX' : '' });
      grid.updateHost('H3', { active: pFlow2 > 0.1, color: C.amber, rateText: pFlow2 > 0.2 ? '+30 Mbps' : '' });
      grid.updateHost('H5', { active: pFlow2 > 0.1, color: C.amber, rateText: pFlow2 > 0.2 ? 'RX' : '' });
      grid.updateHost('H2', { active: false, color: C.textMuted, rateText: '' });
      grid.updateHost('H4', { active: false, color: C.textMuted, rateText: '' });

      // Traffic packets
      if (pFlow1 > 0.15) {
        grid.setPackets('h1h6', ['H1', 'S1', 'S2', 'S3', 'S6', 'H6'], {
          t: localT,
          speed: 0.30,
          count: 8,
          color: C.emeraldBright,
          radius: 5.5,
          opacity: pFlow1
        });
      }
      if (pFlow2 > 0.1) {
        grid.setPackets('h3h5', ['H3', 'S2', 'S3', 'H5'], {
          t: localT + 0.15,
          speed: 0.42,
          count: 5,
          color: C.amber,
          radius: 5.5,
          opacity: pFlow2
        });
      }
    }
  });
})();
