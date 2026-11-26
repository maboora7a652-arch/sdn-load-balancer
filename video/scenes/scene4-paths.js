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
    var y = (1 - c) * (dy === undefined ? 18 : dy);
    var sf = scaleFrom === undefined ? 0.95 : scaleFrom;
    var sc = sf + (1 - sf) * c;
    node.style.opacity = c.toFixed(4);
    node.style.transform = 'translate3d(0,' + y.toFixed(2) + 'px,0) scale(' + sc.toFixed(4) + ')';
  }

  var ALL_LINKS = ['S1-S2', 'S2-S3', 'S3-S6', 'S1-S4', 'S4-S5', 'S5-S6', 'S2-S5'];
  var ALL_SWITCHES = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6'];

  window.SDN_VIDEO.registerScene({
    id: 'scene4-paths',
    index: 3,
    title: "Yen's k=3 Path Selection & Hysteresis Guardrails",
    chapter: '04 / YEN k=3 PATH SELECTION',
    start: 34,
    duration: 12,

    mount: function (rootEl, api) {
      var C = api.COLORS;
      rootEl.innerHTML = '';

      var wrap = el(
        'div',
        'position:absolute;inset:0;width:1920px;height:1080px;overflow:hidden;' +
        'font-family:' + FONT_SANS + ';color:' + C.text + ';'
      );

      // HEADER (y: 94..160)
      var header = el(
        'div',
        'position:absolute;left:96px;top:94px;width:1728px;display:flex;' +
        'align-items:center;justify-content:space-between;will-change:transform,opacity;'
      );
      header.appendChild(
        el(
          'h2',
          'margin:0;font-size:48px;font-weight:700;letter-spacing:-0.025em;color:' + C.text + ';',
          "Yen's k=3 Path Selection & Hysteresis Guardrails"
        )
      );
      header.appendChild(
        el(
          'div',
          'padding:9px 20px;border-radius:999px;background:' + C.surface + ';' +
          'border:1px solid ' + C.border + ';font-family:' + FONT_MONO + ';font-size:19px;' +
          'font-weight:600;color:' + C.emeraldBright + ';',
          'ELEPHANT: H1 → H6 (85 MBPS)'
        )
      );
      wrap.appendChild(header);

      // LEFT COLUMN: 2x3 Grid Diagram + Tie-Break Rule Bar (x: 96..980, width 884px, y: 184..986)
      var leftCol = el(
        'div',
        'position:absolute;left:96px;top:184px;width:884px;height:802px;' +
        'display:flex;flex-direction:column;gap:18px;'
      );

      var gridCard = el(
        'div',
        'flex:1;background:rgba(15,30,27,0.88);border:1px solid ' + C.border + ';border-radius:18px;' +
        'display:flex;flex-direction:column;overflow:hidden;will-change:transform,opacity;'
      );

      var gridHead = el(
        'div',
        'display:flex;align-items:center;justify-content:space-between;padding:16px 24px;' +
        'background:' + C.header + ';border-bottom:1px solid ' + C.border + ';'
      );
      var stageBadge = el(
        'div',
        'font-family:' + FONT_MONO + ';font-size:21px;font-weight:700;color:' + C.amber + ';',
        'CANDIDATE 1/3 · P1: S1 → S2 → S3 → S6'
      );
      var stageTag = el(
        'span',
        'padding:5px 14px;border-radius:8px;background:rgba(7,14,13,0.72);' +
        'border:1px solid ' + C.border + ';font-family:' + FONT_MONO + ';font-size:18px;' +
        'font-weight:700;color:' + C.amber + ';',
        '115% BOTTLENECK'
      );
      gridHead.appendChild(stageBadge);
      gridHead.appendChild(stageTag);
      gridCard.appendChild(gridHead);

      var svgHost = el(
        'div',
        'flex:1;display:flex;align-items:center;justify-content:center;padding:10px 18px;'
      );
      var grid = api.createGridDiagram({ showController: false });
      grid.svg.style.width = '100%';
      grid.svg.style.height = '100%';
      grid.svg.style.maxHeight = '560px';
      grid.svg.style.display = 'block';
      svgHost.appendChild(grid.svg);
      gridCard.appendChild(svgHost);
      leftCol.appendChild(gridCard);

      // Tie-break ranking tuple card
      var tupleBar = el(
        'div',
        'padding:18px 24px;border-radius:16px;background:' + C.surface + ';' +
        'border:1px solid ' + C.border + ';display:flex;align-items:center;' +
        'justify-content:space-between;gap:14px;will-change:transform,opacity;'
      );
      tupleBar.appendChild(
        el(
          'span',
          'font-family:' + FONT_MONO + ';font-size:18px;font-weight:700;letter-spacing:0.06em;color:' + C.cyan + ';',
          'RANKING ORDER'
        )
      );
      tupleBar.appendChild(
        el(
          'span',
          'font-family:' + FONT_MONO + ';font-size:19px;font-weight:600;color:' + C.text + ';',
          '1. Projected Bottleneck %   →   2. Hops   →   3. Shared Links'
        )
      );
      leftCol.appendChild(tupleBar);
      wrap.appendChild(leftCol);

      // RIGHT COLUMN: 3 Path-Scoring Cards + Hysteresis Guardrail Strip (x: 1020..1824, width 804px, y: 184..986)
      var rightCol = el(
        'div',
        'position:absolute;left:1020px;top:184px;width:804px;height:802px;' +
        'display:flex;flex-direction:column;justify-content:space-between;gap:16px;'
      );

      function makePathCard(opts) {
        var card = el(
          'div',
          'background:' + C.surface + ';border:2px solid ' + C.border + ';border-radius:16px;' +
          'padding:18px 24px;display:flex;flex-direction:column;gap:12px;' +
          'will-change:transform,opacity;'
        );
        var top = el('div', 'display:flex;align-items:center;justify-content:space-between;gap:12px;');
        var pathLabel = el(
          'div',
          'font-family:' + FONT_MONO + ';font-size:25px;font-weight:700;color:' + C.text + ';',
          opts.path
        );
        var statusPill = el(
          'span',
          'padding:6px 14px;border-radius:999px;background:' + opts.pillBg + ';' +
          'border:1px solid ' + opts.accent + ';font-family:' + FONT_MONO + ';font-size:18px;' +
          'font-weight:700;color:' + opts.pillText + ';white-space:nowrap;',
          opts.status
        );
        top.appendChild(pathLabel);
        top.appendChild(statusPill);
        card.appendChild(top);

        var mid = el('div', 'display:flex;align-items:center;justify-content:space-between;gap:20px;');
        var costBlock = el('div', 'display:flex;align-items:baseline;gap:12px;');
        costBlock.appendChild(
          el('span', 'font-size:19px;color:' + C.textMuted + ';', 'Projected Bottleneck')
        );
        costBlock.appendChild(
          el(
            'span',
            'font-family:' + FONT_MONO + ';font-size:32px;font-weight:700;font-variant-numeric:tabular-nums;color:' + opts.accent + ';',
            opts.bottleneck
          )
        );
        var hopsBlock = el(
          'div',
          'font-family:' + FONT_MONO + ';font-size:20px;font-weight:600;color:' + C.textMuted + ';',
          opts.meta
        );
        mid.appendChild(costBlock);
        mid.appendChild(hopsBlock);
        card.appendChild(mid);

        // Bottleneck bar (scaleX out of 120%)
        var track = el(
          'div',
          'height:12px;border-radius:6px;background:rgba(7,14,13,0.82);' +
          'border:1px solid ' + C.border + ';overflow:hidden;position:relative;'
        );
        var fill = el(
          'div',
          'width:100%;height:100%;transform-origin:left center;background:' + opts.accent + ';will-change:transform;'
        );
        // 100% mark at 100/120 = 83.3%
        var mark = el(
          'div',
          'position:absolute;top:0;bottom:0;left:83.3%;width:2px;background:' + C.text + ';opacity:0.65;'
        );
        track.appendChild(fill);
        track.appendChild(mark);
        card.appendChild(track);

        return { card: card, fill: fill, accent: opts.accent };
      }

      var cardP1 = makePathCard({
        path: 'P1: S1 → S2 → S3 → S6',
        status: 'Current (Congested)',
        bottleneck: '115%',
        meta: '3 hops · Active',
        accent: C.amber,
        pillBg: 'rgba(191,84,26,0.28)',
        pillText: C.amber
      });

      var cardP2 = makePathCard({
        path: 'P2: S1 → S2 → S5 → S6',
        status: '1 shared link (S1–S2)',
        bottleneck: '85%',
        meta: '3 hops · Tie-break #2',
        accent: C.cyan,
        pillBg: 'rgba(34,211,238,0.14)',
        pillText: C.cyan
      });

      var cardP3 = makePathCard({
        path: 'P3: S1 → S4 → S5 → S6',
        status: '0 shared links · SELECTED ✓',
        bottleneck: '85%',
        meta: '3 hops · Link-Disjoint',
        accent: C.emeraldBright,
        pillBg: 'rgba(20,117,85,0.45)',
        pillText: C.emeraldBright
      });

      rightCol.appendChild(cardP1.card);
      rightCol.appendChild(cardP2.card);
      rightCol.appendChild(cardP3.card);

      // Bottom-Right Hysteresis Guardrail Strip
      var guardCard = el(
        'div',
        'background:rgba(15,30,27,0.92);border:1px solid rgba(16,185,129,0.48);border-radius:16px;' +
        'padding:18px 22px;display:flex;flex-direction:column;gap:12px;will-change:transform,opacity;'
      );
      guardCard.appendChild(
        el(
          'div',
          'font-family:' + FONT_MONO + ';font-size:18px;font-weight:700;letter-spacing:0.08em;color:' + C.cyan + ';',
          'HYSTERESIS & ANTI-OSCILLATION GUARDRAILS'
        )
      );

      var guardRow = el('div', 'display:grid;grid-template-columns:1.15fr 1fr;gap:12px;');

      var gGain = el(
        'div',
        'padding:12px 16px;border-radius:12px;background:rgba(20,117,85,0.24);' +
        'border:1px solid rgba(16,185,129,0.55);display:flex;flex-direction:column;gap:3px;'
      );
      gGain.appendChild(el('div', 'font-family:' + FONT_MONO + ';font-size:18px;color:' + C.textMuted + ';', 'Gain ≥ 15 pp'));
      gGain.appendChild(
        el(
          'div',
          'font-family:' + FONT_MONO + ';font-size:21px;font-weight:700;font-variant-numeric:tabular-nums;color:' + C.emeraldBright + ';',
          '115% → 85% = 30 pp ✓'
        )
      );

      var gHold = el(
        'div',
        'padding:12px 16px;border-radius:12px;background:rgba(34,211,238,0.10);' +
        'border:1px solid rgba(34,211,238,0.42);display:flex;flex-direction:column;gap:3px;'
      );
      gHold.appendChild(el('div', 'font-family:' + FONT_MONO + ';font-size:18px;color:' + C.textMuted + ';', 'Anti-Oscillation'));
      gHold.appendChild(
        el(
          'div',
          'font-family:' + FONT_MONO + ';font-size:21px;font-weight:700;font-variant-numeric:tabular-nums;color:' + C.cyan + ';',
          '30 s Per-Flow Hold-Down'
        )
      );

      guardRow.appendChild(gGain);
      guardRow.appendChild(gHold);
      guardCard.appendChild(guardRow);

      // Required 20px factual footnote
      guardCard.appendChild(
        el(
          'div',
          'font-size:20px;font-weight:500;color:' + C.textMuted + ';line-height:1.3;',
          'Offered-load cost model ≠ measured C4 utilization'
        )
      );
      rightCol.appendChild(guardCard);

      wrap.appendChild(rightCol);
      rootEl.appendChild(wrap);

      return {
        header: header,
        gridCard: gridCard,
        stageBadge: stageBadge,
        stageTag: stageTag,
        tupleBar: tupleBar,
        cardP1: cardP1,
        cardP2: cardP2,
        cardP3: cardP3,
        guardCard: guardCard,
        grid: grid
      };
    },

    update: function (state, localT, globalT, api) {
      var C = api.COLORS;
      var E = api.EASE;
      var M = api.math;

      // Immediate visibility <= 0.5s
      applyFadeSlide(state.header, M.seg(localT, 0.0, 0.40, E.power4Out), 16, 0.96);
      applyFadeSlide(state.gridCard, M.seg(localT, 0.05, 0.44, E.power4Out), 18, 0.96);
      applyFadeSlide(state.tupleBar, M.seg(localT, 0.45, 0.44, E.power3Out), 14, 0.96);

      // Three candidate path cards animate in sync with Grid spotlights
      var p1In = M.seg(localT, 0.55, 0.48, E.power4Out);
      var p2In = M.seg(localT, 3.85, 0.48, E.power4Out);
      var p3In = M.seg(localT, 6.85, 0.48, E.power4Out);
      var pGuard = M.seg(localT, 7.65, 0.50, E.power3Out);

      // Active stage: 0 = P1 (0..4s), 1 = P2 (4..7s), 2 = P3 (7..12s)
      var stage = localT < 4.0 ? 0 : (localT < 7.0 ? 1 : 2);

      function styleScoreCard(item, pIn, isActive, isWinner, barFrac) {
        var c = M.clamp(pIn, 0, 1);
        var dy = (1 - c) * 18;
        var baseScale = isActive ? 1.0 : 0.985;
        var sc = M.lerp(0.95, baseScale, c);
        item.card.style.opacity = (c * (isActive ? 1.0 : 0.66)).toFixed(4);
        item.card.style.transform = 'translate3d(0,' + dy.toFixed(2) + 'px,0) scale(' + sc.toFixed(4) + ')';
        item.card.style.borderColor = isActive ? item.accent : C.border;
        item.card.style.boxShadow = isWinner
          ? '0 0 32px rgba(16,185,129,0.28), 0 12px 30px rgba(0,0,0,0.35)'
          : (isActive ? '0 10px 28px rgba(0,0,0,0.32)' : 'none');
        item.fill.style.transform = 'scaleX(' + (c * barFrac).toFixed(4) + ')';
      }

      styleScoreCard(state.cardP1, p1In, stage === 0, false, 115 / 120);
      styleScoreCard(state.cardP2, p2In, stage === 1, false, 85 / 120);
      styleScoreCard(state.cardP3, p3In, stage === 2, stage === 2, 85 / 120);
      applyFadeSlide(state.guardCard, pGuard, 16, 0.96);

      // Top status banner inside Grid card
      if (stage === 0) {
        state.stageBadge.textContent = 'CANDIDATE 1/3 · P1: S1 → S2 → S3 → S6';
        state.stageBadge.style.color = C.amber;
        state.stageTag.textContent = '115% BOTTLENECK';
        state.stageTag.style.color = C.amber;
        state.stageTag.style.borderColor = C.amber;
      } else if (stage === 1) {
        state.stageBadge.textContent = 'CANDIDATE 2/3 · P2: S1 → S2 → S5 → S6';
        state.stageBadge.style.color = C.cyan;
        state.stageTag.textContent = '85% · 1 SHARED LINK';
        state.stageTag.style.color = C.cyan;
        state.stageTag.style.borderColor = C.cyan;
      } else {
        state.stageBadge.textContent = 'SELECTED 3/3 · P3: S1 → S4 → S5 → S6';
        state.stageBadge.style.color = C.emeraldBright;
        state.stageTag.textContent = '85% · 0 SHARED · SELECTED ✓';
        state.stageTag.style.color = C.emeraldBright;
        state.stageTag.style.borderColor = C.emeraldBright;
      }

      // Update 2x3 Grid SVG deterministically
      var grid = state.grid;
      if (typeof grid.reset === 'function') grid.reset();

      var p1Links = { 'S1-S2': true, 'S2-S3': true, 'S3-S6': true };
      var p2Links = { 'S1-S2': true, 'S2-S5': true, 'S5-S6': true };
      var p3Links = { 'S1-S4': true, 'S4-S5': true, 'S5-S6': true };

      var pulse = 0.5 + 0.5 * Math.sin(localT * 5.0);

      for (var l = 0; l < ALL_LINKS.length; l++) {
        var id = ALL_LINKS[l];
        var drawP = M.stagger(localT, 0.08, l, 0.04, 0.55, E.power3Out);
        var opts = {
          color: C.linkIdle,
          width: 3.2,
          opacity: 0.35,
          dashed: false,
          dashOffset: 0,
          drawProgress: drawP,
          label: '',
          labelColor: C.textMuted,
          glow: null
        };

        if (stage === 0 && p1Links[id]) {
          opts.color = C.amber;
          opts.width = id === 'S2-S3' ? 6.8 : 5.5;
          opts.opacity = 1.0;
          opts.dashed = id === 'S2-S3';
          opts.dashOffset = id === 'S2-S3' ? -(localT * 46) : 0;
          opts.glow = 'amber';
          if (id === 'S2-S3') {
            opts.label = '115% PEAK';
            opts.labelColor = C.amber;
          }
        } else if (stage === 1) {
          if (p2Links[id]) {
            var isShared = id === 'S1-S2';
            opts.color = isShared ? C.amber : C.cyan;
            opts.width = isShared ? 6.2 : 5.5;
            opts.opacity = 1.0;
            opts.dashed = isShared;
            opts.dashOffset = isShared ? -(localT * 30) : 0;
            opts.glow = isShared ? 'amber' : 'cyan';
            if (isShared) {
              opts.label = 'SHARED S1–S2';
              opts.labelColor = C.amber;
            } else if (id === 'S2-S5') {
              opts.label = '85%';
              opts.labelColor = C.cyan;
            }
          } else if (id === 'S2-S3') {
            opts.color = C.amber;
            opts.opacity = 0.32;
            opts.dashed = true;
          }
        } else if (stage === 2) {
          if (p3Links[id]) {
            opts.color = C.emeraldBright;
            opts.width = 6.2 + 0.6 * pulse;
            opts.opacity = 1.0;
            opts.glow = 'emerald';
            if (id === 'S4-S5') {
              opts.label = 'P3 · 85% ✓';
              opts.labelColor = C.emeraldBright;
            }
          } else if (p1Links[id]) {
            opts.color = C.amber;
            opts.width = 3.2;
            opts.opacity = 0.28;
            opts.dashed = true;
          }
        }

        grid.updateLink(id, opts);
      }

      // Switches
      var activeSw = stage === 0
        ? { S1: C.amber, S2: C.amber, S3: C.amber, S6: C.amber }
        : (stage === 1
          ? { S1: C.amber, S2: C.amber, S5: C.cyan, S6: C.cyan }
          : { S1: C.emeraldBright, S4: C.emeraldBright, S5: C.emeraldBright, S6: C.emeraldBright });

      for (var s = 0; s < ALL_SWITCHES.length; s++) {
        var sw = ALL_SWITCHES[s];
        var col = activeSw[sw];
        var gl = col === C.amber ? 'amber' : (col === C.cyan ? 'cyan' : (col === C.emeraldBright ? 'emerald' : null));
        grid.updateSwitch(sw, {
          stroke: col || C.switchStroke,
          fill: C.surface,
          glow: gl,
          badgeText: (stage === 2 && col) ? 'P3' : '',
          badgeColor: C.emeraldFill,
          badgeOpacity: (stage === 2 && col) ? 0.92 : 0,
          scale: col ? 1.02 : 1.0
        });
      }

      // Hosts
      var hostCol = stage === 0 ? C.amber : (stage === 1 ? C.cyan : C.emeraldBright);
      grid.updateHost('H1', { active: true, color: hostCol, rateText: '85 Mbps' });
      grid.updateHost('H6', { active: true, color: hostCol, rateText: 'DST' });
      grid.updateHost('H3', { active: false, color: C.textMuted, rateText: '' });
      grid.updateHost('H5', { active: false, color: C.textMuted, rateText: '' });
      grid.updateHost('H2', { active: false, color: C.textMuted, rateText: '' });
      grid.updateHost('H4', { active: false, color: C.textMuted, rateText: '' });

      // Animated path preview packets
      if (stage === 0 && localT > 0.6) {
        grid.setPackets('cand', ['H1', 'S1', 'S2', 'S3', 'S6', 'H6'], {
          t: localT,
          speed: 0.30,
          count: 7,
          color: C.amber,
          radius: 5.5,
          opacity: M.seg(localT, 0.6, 0.4, E.power3Out)
        });
      } else if (stage === 1) {
        grid.setPackets('cand', ['H1', 'S1', 'S2', 'S5', 'S6', 'H6'], {
          t: localT,
          speed: 0.32,
          count: 7,
          color: C.cyan,
          radius: 5.5,
          opacity: M.seg(localT, 4.0, 0.35, E.power3Out)
        });
      } else if (stage === 2) {
        grid.setPackets('cand', ['H1', 'S1', 'S4', 'S5', 'S6', 'H6'], {
          t: localT,
          speed: 0.34,
          count: 8,
          color: C.emeraldBright,
          radius: 6,
          opacity: M.seg(localT, 7.0, 0.35, E.power3Out)
        });
      }
    }
  });
})();
