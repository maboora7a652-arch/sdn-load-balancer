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

  function applyFadeSlide(node, p, dy, scaleFrom) {
    var clamped = p < 0 ? 0 : p > 1 ? 1 : p;
    var y = (1 - clamped) * (dy === undefined ? 22 : dy);
    var sf = scaleFrom === undefined ? 0.95 : scaleFrom;
    var sc = sf + (1 - sf) * clamped;
    node.style.opacity = clamped.toFixed(4);
    node.style.transform = 'translate3d(0,' + y.toFixed(2) + 'px,0) scale(' + sc.toFixed(4) + ')';
  }

  var LINKS_ORDER = ['S1-S2', 'S2-S3', 'S3-S6', 'S1-S4', 'S4-S5', 'S5-S6', 'S2-S5'];
  var ALL_SWITCHES = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6'];

  window.SDN_VIDEO.registerScene({
    id: 'scene1-hook',
    index: 0,
    title: 'Intelligent SDN Load Balancer',
    chapter: '01 / OVERVIEW',
    start: 0,
    duration: 9,

    mount: function (rootEl, api) {
      var C = api.COLORS;
      rootEl.innerHTML = '';

      var wrap = el(
        'div',
        'position:absolute;inset:0;width:1920px;height:1080px;overflow:hidden;' +
        'font-family:' + FONT_SANS + ';color:' + C.text + ';'
      );

      // Ambient subtle emerald/cyan radial glow behind the right topology card
      var glowOrb = el(
        'div',
        'position:absolute;left:980px;top:140px;width:820px;height:780px;border-radius:50%;' +
        'background:radial-gradient(circle, rgba(16,185,129,0.13) 0%, rgba(34,211,238,0.05) 45%, rgba(7,14,13,0) 72%);' +
        'pointer-events:none;will-change:transform,opacity;'
      );
      wrap.appendChild(glowOrb);

      // LEFT HERO COLUMN: x: 96..880 (width 784px), y: 120..980
      var leftCol = el(
        'div',
        'position:absolute;left:96px;top:138px;width:784px;height:842px;' +
        'display:flex;flex-direction:column;justify-content:center;'
      );

      // Eyebrow pill
      var eyebrowWrap = el(
        'div',
        'display:inline-flex;align-items:center;gap:12px;align-self:flex-start;' +
        'padding:10px 22px;border-radius:999px;background:rgba(20,117,85,0.22);' +
        'border:1px solid rgba(16,185,129,0.55);margin-bottom:28px;will-change:transform,opacity;'
      );
      var eyebrowDot = el(
        'span',
        'width:11px;height:11px;border-radius:50%;background:' + C.emeraldBright + ';' +
        'box-shadow:0 0 12px ' + C.emerald + ';display:inline-block;'
      );
      var eyebrowText = el(
        'span',
        'font-family:' + FONT_MONO + ';font-size:20px;font-weight:700;letter-spacing:0.10em;' +
        'color:' + C.emeraldBright + ';text-transform:uppercase;',
        'ECE2606 · SDN TRACK 1'
      );
      eyebrowWrap.appendChild(eyebrowDot);
      eyebrowWrap.appendChild(eyebrowText);
      leftCol.appendChild(eyebrowWrap);

      // Hero Title (82px bold)
      var heroTitle = el(
        'h1',
        'margin:0 0 24px 0;font-size:82px;font-weight:700;line-height:1.05;' +
        'letter-spacing:-0.03em;color:' + C.text + ';will-change:transform,opacity;'
      );
      var line1 = el('div', '', 'Intelligent SDN');
      var line2 = el('div', 'color:' + C.emeraldBright + ';', 'Load Balancer');
      heroTitle.appendChild(line1);
      heroTitle.appendChild(line2);
      leftCol.appendChild(heroTitle);

      // Subtitle (32px)
      var subtitle = el(
        'p',
        'margin:0 0 34px 0;font-size:32px;font-weight:500;line-height:1.35;' +
        'color:' + C.textMuted + ';max-width:740px;will-change:transform,opacity;',
        'Congestion-Aware Routing & Automatic Fault Tolerance'
      );
      leftCol.appendChild(subtitle);

      // Accent rule
      var ruleTrack = el(
        'div',
        'width:320px;height:4px;border-radius:2px;background:rgba(31,59,52,0.85);' +
        'overflow:hidden;margin-bottom:36px;'
      );
      var ruleFill = el(
        'div',
        'width:100%;height:100%;transform-origin:left center;' +
        'background:linear-gradient(90deg,' + C.emerald + ',' + C.cyan + ');will-change:transform;'
      );
      ruleTrack.appendChild(ruleFill);
      leftCol.appendChild(ruleTrack);

      // Tech Stack Pills
      var pillsGrid = el(
        'div',
        'display:flex;flex-wrap:wrap;gap:14px;margin-bottom:44px;max-width:760px;'
      );
      var pillSpecs = [
        { label: 'OS-Ken 3.1.1', color: C.cyan },
        { label: 'OpenFlow 1.3', color: C.cyan },
        { label: 'Mininet 2.3 + OVS', color: C.emerald },
        { label: 'REST API + Live Dashboard', color: C.emeraldBright }
      ];
      var pillEls = [];
      for (var i = 0; i < pillSpecs.length; i++) {
        var ps = pillSpecs[i];
        var pill = el(
          'div',
          'display:inline-flex;align-items:center;gap:11px;padding:12px 20px;' +
          'border-radius:12px;background:' + C.surface + ';border:1px solid ' + C.border + ';' +
          'font-family:' + FONT_MONO + ';font-size:21px;font-weight:600;color:' + C.text + ';' +
          'will-change:transform,opacity;'
        );
        var dot = el(
          'span',
          'width:10px;height:10px;border-radius:50%;background:' + ps.color + ';' +
          'box-shadow:0 0 10px ' + ps.color + ';flex-shrink:0;'
        );
        var txt = el('span', '', ps.label);
        pill.appendChild(dot);
        pill.appendChild(txt);
        pillsGrid.appendChild(pill);
        pillEls.push(pill);
      }
      leftCol.appendChild(pillsGrid);

      // Bottom subtle badge
      var footerBadge = el(
        'div',
        'display:flex;align-items:center;gap:14px;padding:14px 20px;border-radius:12px;' +
        'background:rgba(15,30,27,0.72);border-left:4px solid ' + C.emerald + ';' +
        'border-top:1px solid ' + C.border + ';border-right:1px solid ' + C.border + ';' +
        'border-bottom:1px solid ' + C.border + ';align-self:flex-start;will-change:transform,opacity;'
      );
      var footerText = el(
        'span',
        'font-family:' + FONT_MONO + ';font-size:20px;font-weight:500;color:' + C.textMuted + ';',
        'Measured on Ubuntu Mininet/OVS · Helwan National University'
      );
      footerBadge.appendChild(footerText);
      leftCol.appendChild(footerBadge);

      wrap.appendChild(leftCol);

      // RIGHT HERO GRID CARD: x: 920..1824 (width 904px), y: 126..964
      var rightCard = el(
        'div',
        'position:absolute;left:920px;top:126px;width:904px;height:838px;' +
        'background:rgba(15,30,27,0.86);border:1px solid ' + C.border + ';border-radius:20px;' +
        'box-shadow:0 24px 64px rgba(0,0,0,0.45);display:flex;flex-direction:column;' +
        'overflow:hidden;will-change:transform,opacity;'
      );

      // Card Header Bar
      var cardHead = el(
        'div',
        'display:flex;align-items:center;justify-content:space-between;padding:18px 26px;' +
        'background:' + C.header + ';border-bottom:1px solid ' + C.border + ';'
      );
      var headTitle = el(
        'div',
        'font-family:' + FONT_MONO + ';font-size:20px;font-weight:700;letter-spacing:0.06em;' +
        'color:' + C.text + ';',
        '2×3 LAB GRID · 6 SWITCHES · 7 LINKS'
      );
      var headStatus = el(
        'div',
        'display:inline-flex;align-items:center;gap:9px;padding:6px 14px;border-radius:999px;' +
        'background:rgba(16,185,129,0.18);border:1px solid rgba(16,185,129,0.55);' +
        'font-family:' + FONT_MONO + ';font-size:18px;font-weight:700;color:' + C.emeraldBright + ';',
        '● OPENFLOW 1.3 ACTIVE'
      );
      cardHead.appendChild(headTitle);
      cardHead.appendChild(headStatus);
      rightCard.appendChild(cardHead);

      // SVG Grid Stage inside card
      var svgHost = el(
        'div',
        'flex:1;display:flex;align-items:center;justify-content:center;padding:18px 16px 8px 16px;position:relative;'
      );
      var grid = api.createGridDiagram({ showController: true });
      grid.svg.style.width = '100%';
      grid.svg.style.height = '100%';
      grid.svg.style.maxHeight = '655px';
      grid.svg.style.display = 'block';
      svgHost.appendChild(grid.svg);
      rightCard.appendChild(svgHost);

      // Card Footer Legend
      var cardFoot = el(
        'div',
        'display:flex;align-items:center;justify-content:space-between;padding:16px 26px;' +
        'background:rgba(7,14,13,0.55);border-top:1px solid ' + C.border + ';' +
        'font-family:' + FONT_MONO + ';font-size:18px;color:' + C.textMuted + ';'
      );
      var leg1 = el('span', 'color:' + C.emeraldBright + ';font-weight:600;', '━━ Active Paths: P1 & P3');
      var leg2 = el('span', 'color:' + C.cyan + ';font-weight:600;', '┈┈ Control Plane (:6653)');
      var leg3 = el('span', 'font-variant-numeric:tabular-nums;', '100 Mbps · 2 ms TCLinks');
      cardFoot.appendChild(leg1);
      cardFoot.appendChild(leg2);
      cardFoot.appendChild(leg3);
      rightCard.appendChild(cardFoot);

      wrap.appendChild(rightCard);
      rootEl.appendChild(wrap);

      return {
        glowOrb: glowOrb,
        eyebrowWrap: eyebrowWrap,
        eyebrowDot: eyebrowDot,
        heroTitle: heroTitle,
        subtitle: subtitle,
        ruleFill: ruleFill,
        pillEls: pillEls,
        footerBadge: footerBadge,
        rightCard: rightCard,
        grid: grid
      };
    },

    update: function (state, localT, globalT, api) {
      var C = api.COLORS;
      var E = api.EASE;
      var M = api.math;

      // Hero visible by localT <= 0.5s
      var pEyebrow = M.seg(localT, 0.0, 0.40, E.power4Out);
      var pTitle = M.seg(localT, 0.05, 0.45, E.power4Out);
      var pSub = M.seg(localT, 0.22, 0.48, E.power3Out);
      var pRule = M.seg(localT, 0.35, 0.50, E.expoInOut);
      var pFooter = M.seg(localT, 0.72, 0.50, E.power3Out);
      var pCard = M.seg(localT, 0.04, 0.46, E.power4Out);

      applyFadeSlide(state.eyebrowWrap, pEyebrow, 16, 0.96);
      applyFadeSlide(state.heroTitle, pTitle, 24, 0.95);
      applyFadeSlide(state.subtitle, pSub, 20, 0.96);
      state.ruleFill.style.transform = 'scaleX(' + pRule.toFixed(4) + ')';
      applyFadeSlide(state.footerBadge, pFooter, 16, 0.96);
      applyFadeSlide(state.rightCard, pCard, 18, 0.96);

      // Pills staggered 60ms each (total 240ms <= 500ms)
      for (var i = 0; i < state.pillEls.length; i++) {
        var pp = M.stagger(localT, 0.42, i, 0.06, 0.40, E.power3Out);
        applyFadeSlide(state.pillEls[i], pp, 14, 0.95);
      }

      // Calm breathing pulse on ambient orb & eyebrow dot
      var pulse = 0.5 + 0.5 * Math.sin(localT * 2.1);
      state.glowOrb.style.opacity = (0.65 + 0.25 * pulse).toFixed(4);
      state.glowOrb.style.transform = 'scale(' + (0.98 + 0.03 * pulse).toFixed(4) + ')';
      state.eyebrowDot.style.opacity = (0.72 + 0.28 * pulse).toFixed(4);

      // Update 2x3 Grid SVG deterministically
      var grid = state.grid;
      if (typeof grid.reset === 'function') grid.reset();
      if (typeof grid.updateController === 'function') {
        grid.updateController({
          pulse: 0.35 + 0.65 * pulse,
          dashOffset: -(localT * 26),
          color: C.cyan
        });
      }

      var pP1Active = M.seg(localT, 1.05, 0.65, E.power3Out);
      var pP3Active = M.seg(localT, 2.00, 0.75, E.power3Out);

      // Draw all 7 links smoothly with staggered stroke-dashoffset
      for (var l = 0; l < LINKS_ORDER.length; l++) {
        var linkId = LINKS_ORDER[l];
        var drawP = M.stagger(localT, 0.12, l, 0.06, 0.85, E.power3Out);
        var isP1 = linkId === 'S1-S2' || linkId === 'S2-S3' || linkId === 'S3-S6';
        var isP3 = linkId === 'S1-S4' || linkId === 'S4-S5' || linkId === 'S5-S6';

        var color = C.linkIdle;
        var width = 3.5;
        var opacity = 0.55;
        var glow = null;
        var label = '';
        var labelColor = C.textMuted;

        if (isP1 && pP1Active > 0.01) {
          color = C.emerald;
          width = M.lerp(3.5, 5.5, pP1Active);
          opacity = M.lerp(0.55, 1.0, pP1Active);
          glow = pP1Active > 0.4 ? 'emerald' : null;
          if (linkId === 'S2-S3' && pP1Active > 0.6) {
            label = 'P1';
            labelColor = C.emeraldBright;
          }
        } else if (isP3 && pP3Active > 0.01) {
          color = C.emeraldBright;
          width = M.lerp(3.5, 5.2, pP3Active);
          opacity = M.lerp(0.55, 0.96, pP3Active);
          glow = pP3Active > 0.4 ? 'emerald' : null;
          if (linkId === 'S4-S5' && pP3Active > 0.6) {
            label = 'P3';
            labelColor = C.emeraldBright;
          }
        }

        grid.updateLink(linkId, {
          color: color,
          width: width,
          opacity: opacity,
          drawProgress: drawP,
          glow: glow,
          label: label,
          labelColor: labelColor
        });
      }

      // Switches: calm cyan control-plane scan wave across S1..S6
      for (var s = 0; s < ALL_SWITCHES.length; s++) {
        var swId = ALL_SWITCHES[s];
        var swWave = 0.5 + 0.5 * Math.sin(localT * 2.4 - s * 0.7);
        var isCyanPulse = swWave > 0.72 && localT > 1.2;
        grid.updateSwitch(swId, {
          stroke: isCyanPulse ? C.cyan : (localT > 1.0 ? C.emerald : C.switchStroke),
          fill: C.surface,
          glow: isCyanPulse ? 'cyan' : (localT > 1.3 ? 'emerald' : null),
          badgeText: isCyanPulse ? 'OF1.3' : '',
          badgeColor: C.cyan,
          badgeOpacity: isCyanPulse ? M.clamp((swWave - 0.72) / 0.28, 0, 1) * 0.85 : 0,
          scale: 1 + 0.015 * swWave
        });
      }

      // Active Hosts
      grid.updateHost('H1', { active: pP1Active > 0.2, color: C.emeraldBright, rateText: pP1Active > 0.4 ? 'SRC · P1 / P3' : '' });
      grid.updateHost('H6', { active: pP1Active > 0.2, color: C.emeraldBright, rateText: pP1Active > 0.4 ? 'DST · ACTIVE' : '' });
      grid.updateHost('H2', { active: pP3Active > 0.3, color: C.cyan, rateText: '' });
      grid.updateHost('H3', { active: false, color: C.textMuted, rateText: '' });
      grid.updateHost('H4', { active: false, color: C.textMuted, rateText: '' });
      grid.updateHost('H5', { active: false, color: C.textMuted, rateText: '' });

      // Smooth deterministic emerald packet streams across P1 and P3
      if (pP1Active > 0.15) {
        grid.setPackets('p1', ['H1', 'S1', 'S2', 'S3', 'S6', 'H6'], {
          t: localT,
          speed: 0.28,
          count: 7,
          color: C.emeraldBright,
          radius: 5.5,
          opacity: pP1Active
        });
      }
      if (pP3Active > 0.15) {
        grid.setPackets('p3', ['H1', 'S1', 'S4', 'S5', 'S6', 'H6'], {
          t: localT + 0.35,
          speed: 0.24,
          count: 6,
          color: C.emerald,
          radius: 5,
          opacity: pP3Active * 0.9
        });
      }
    }
  });
})();
