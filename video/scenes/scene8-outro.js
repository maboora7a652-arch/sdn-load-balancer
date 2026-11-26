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
    id: 'scene8-outro',
    index: 7,
    title: 'Fat-Tree Scale, Local Dashboard & Honest Engineering Scope',
    chapter: '08 / SCALE, LIMITS & REPO',
    start: 86,
    duration: 10,

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

      // ── Header (x: 96..1824, y: 90..170) ─────────────────────────────
      var header = el('div', {
        position: 'absolute',
        left: '96px',
        top: '90px',
        width: '1728px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      });
      header.appendChild(el('div', {
        fontSize: '44px',
        fontWeight: '700',
        letterSpacing: '-0.025em',
        lineHeight: '1.1',
        color: C.text
      }, 'Fat-Tree Scale, Local Dashboard & Honest Engineering Scope'));
      wrap.appendChild(header);

      // ── Left Card (x: 96..930, w: 834, y: 184..862, h: 678) ──────────
      var leftCard = el('div', {
        position: 'absolute',
        left: '96px',
        top: '184px',
        width: '834px',
        height: '678px',
        backgroundColor: C.surface,
        border: '1.5px solid ' + C.border,
        borderRadius: '18px',
        boxSizing: 'border-box',
        padding: '22px 26px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between'
      });
      wrap.appendChild(leftCard);

      var ftHeader = el('div', {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px'
      });
      ftHeader.appendChild(el('span', {
        fontFamily: FONT_MONO,
        fontSize: '20px',
        fontWeight: '700',
        letterSpacing: '0.06em',
        color: C.cyan,
        textTransform: 'uppercase'
      }, 'k = 4 FAT-TREE TOPOLOGY'));
      ftHeader.appendChild(el('span', {
        padding: '5px 12px',
        borderRadius: '999px',
        fontFamily: FONT_MONO,
        fontSize: '18px',
        fontWeight: '700',
        backgroundColor: hexAlpha(C.emerald, 0.14),
        border: '1px solid ' + hexAlpha(C.emerald, 0.6),
        color: C.emeraldBright
      }, '240/240 pingall'));
      leftCard.appendChild(ftHeader);

      // Animated miniature k=4 Fat-Tree SVG (782 x 356)
      // 4 Core (S17..S20), 8 Agg (S9..S16), 8 Edge (S1..S8), 16 Hosts (H1..H16)
      var ftSvg = sEl('svg', { viewBox: '0 0 782 362', width: '782', height: '352' });

      // Tier labels on left margin
      var tierLabels = [
        { y: 48, txt: 'CORE (4)', col: C.cyan },
        { y: 152, txt: 'AGG (8)', col: C.textMuted },
        { y: 256, txt: 'EDGE (8)', col: C.textMuted },
        { y: 344, txt: 'HOSTS (16)', col: C.emeraldBright }
      ];
      for (var tl = 0; tl < tierLabels.length; tl++) {
        ftSvg.appendChild(sEl('text', {
          x: '2', y: String(tierLabels[tl].y + 5),
          fill: tierLabels[tl].col,
          'font-family': FONT_MONO,
          'font-size': '18',
          'font-weight': '700'
        }, tierLabels[tl].txt));
      }

      // Compute exact node coordinates (x in 134..762)
      var coreNodes = [];
      for (var ci = 0; ci < 4; ci++) {
        coreNodes.push({ id: 'S' + (17 + ci), x: 230 + ci * 144, y: 46 });
      }
      var aggNodes = [];
      var edgeNodes = [];
      var hostNodes = [];
      for (var pod = 0; pod < 4; pod++) {
        var podBaseX = 148 + pod * 164;
        for (var j = 0; j < 2; j++) {
          var sx = podBaseX + j * 64;
          aggNodes.push({ id: 'S' + (9 + pod * 2 + j), pod: pod, idx: j, x: sx, y: 150 });
          edgeNodes.push({ id: 'S' + (1 + pod * 2 + j), pod: pod, idx: j, x: sx, y: 254 });
          hostNodes.push({ x: sx - 16, y: 342, edgeIdx: pod * 2 + j });
          hostNodes.push({ x: sx + 16, y: 342, edgeIdx: pod * 2 + j });
        }
      }

      // 32 Inter-Switch Links + 16 Host Links
      var ftLinks = [];
      function addLink(x1, y1, x2, y2, isHighlight, tier) {
        var dx = x2 - x1;
        var dy = y2 - y1;
        var len = Math.sqrt(dx * dx + dy * dy);
        var line = sEl('line', {
          x1: x1.toFixed(1), y1: y1.toFixed(1),
          x2: x2.toFixed(1), y2: y2.toFixed(1),
          stroke: isHighlight ? C.emeraldBright : C.linkIdle,
          'stroke-width': isHighlight ? '3.5' : '1.7',
          'stroke-opacity': isHighlight ? '0.95' : '0.52',
          'stroke-dasharray': len.toFixed(1),
          'stroke-dashoffset': len.toFixed(1)
        });
        ftSvg.appendChild(line);
        ftLinks.push({ el: line, len: len, tier: tier, hi: isHighlight });
      }

      // Highlight real calibration path from #6: H1 -> S1(e0) -> S9(a0) -> S17(c0) -> S15(a6) -> S8(e7) -> H16
      // 16 Agg <-> Core links (index-0 agg -> core 0,1; index-1 agg -> core 2,3)
      for (var ai = 0; ai < aggNodes.length; ai++) {
        var a = aggNodes[ai];
        var cTargets = a.idx === 0 ? [0, 1] : [2, 3];
        for (var ct = 0; ct < cTargets.length; ct++) {
          var c = coreNodes[cTargets[ct]];
          var hiAC = (ai === 0 && cTargets[ct] === 0) || (ai === 6 && cTargets[ct] === 0);
          addLink(a.x, a.y, c.x, c.y, hiAC, 0);
        }
      }
      // 16 Edge <-> Agg links (full 2x2 per pod)
      for (var pod2 = 0; pod2 < 4; pod2++) {
        for (var eOff = 0; eOff < 2; eOff++) {
          for (var aOff = 0; aOff < 2; aOff++) {
            var eNode = edgeNodes[pod2 * 2 + eOff];
            var aNode = aggNodes[pod2 * 2 + aOff];
            var hiEA = (pod2 === 0 && eOff === 0 && aOff === 0) || (pod2 === 3 && eOff === 1 && aOff === 0);
            addLink(eNode.x, eNode.y, aNode.x, aNode.y, hiEA, 1);
          }
        }
      }
      // 16 Host <-> Edge links
      for (var hi = 0; hi < hostNodes.length; hi++) {
        var hn = hostNodes[hi];
        var en = edgeNodes[hn.edgeIdx];
        var hiHE = (hi === 0 || hi === 15);
        addLink(hn.x, hn.y, en.x, en.y, hiHE, 2);
      }

      // Draw switch nodes
      var coreCircles = [];
      for (var ci2 = 0; ci2 < coreNodes.length; ci2++) {
        var cn = coreNodes[ci2];
        var rect = sEl('rect', {
          x: (cn.x - 16).toFixed(1), y: (cn.y - 12).toFixed(1),
          width: '32', height: '24', rx: '6',
          fill: C.surface, stroke: ci2 === 0 ? C.emeraldBright : C.cyan, 'stroke-width': '2'
        });
        ftSvg.appendChild(rect);
        coreCircles.push(rect);
      }
      for (var ai2 = 0; ai2 < aggNodes.length; ai2++) {
        var an = aggNodes[ai2];
        ftSvg.appendChild(sEl('rect', {
          x: (an.x - 13).toFixed(1), y: (an.y - 10).toFixed(1),
          width: '26', height: '20', rx: '5',
          fill: C.surface, stroke: (ai2 === 0 || ai2 === 6) ? C.emeraldBright : C.switchStroke, 'stroke-width': '2'
        }));
      }
      for (var ei2 = 0; ei2 < edgeNodes.length; ei2++) {
        var en2 = edgeNodes[ei2];
        ftSvg.appendChild(sEl('rect', {
          x: (en2.x - 13).toFixed(1), y: (en2.y - 10).toFixed(1),
          width: '26', height: '20', rx: '5',
          fill: C.surface, stroke: (ei2 === 0 || ei2 === 7) ? C.emeraldBright : C.switchStroke, 'stroke-width': '2'
        }));
      }
      for (var hi2 = 0; hi2 < hostNodes.length; hi2++) {
        var hn2 = hostNodes[hi2];
        ftSvg.appendChild(sEl('circle', {
          cx: hn2.x.toFixed(1), cy: hn2.y.toFixed(1), r: '5.5',
          fill: (hi2 === 0 || hi2 === 15) ? C.emeraldBright : C.linkIdle
        }));
      }

      // Deterministic animated packets along H1->S1->S9->S17->S15->S8->H16
      var ftPathPts = [
        hostNodes[0], edgeNodes[0], aggNodes[0], coreNodes[0], aggNodes[6], edgeNodes[7], hostNodes[15]
      ];
      var ftPackets = [];
      for (var fp = 0; fp < 5; fp++) {
        var pkt = sEl('circle', { cx: '0', cy: '0', r: '4.5', fill: C.emeraldBright, opacity: '0' });
        ftSvg.appendChild(pkt);
        ftPackets.push(pkt);
      }

      leftCard.appendChild(ftSvg);

      // Topology & Verified Connectivity Summary (recorded Ubuntu terminal output)
      var connBox = el('div', {
        fontFamily: FONT_MONO,
        fontSize: '18px',
        fontWeight: '600',
        color: C.text,
        padding: '10px 14px',
        borderRadius: '10px',
        backgroundColor: hexAlpha(C.bg, 0.72),
        border: '1px solid ' + C.border,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontVariantNumeric: 'tabular-nums'
      });
      connBox.appendChild(el('span', { color: C.textMuted }, '20 Sw · 32 Links · 16 Hosts'));
      connBox.appendChild(el('span', { color: C.emeraldBright, fontWeight: '700' }, 'Grid 30/30 · Fat-Tree 240/240 (Ubuntu)'));
      leftCard.appendChild(connBox);

      // Live REST API + C4 Calibration + Offline Regressions Strip
      var apiBox = el('div', {
        borderTop: '1.5px solid ' + C.border,
        paddingTop: '14px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
      });
      var apiRow = el('div', {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontFamily: FONT_MONO,
        fontSize: '18px'
      });
      apiRow.appendChild(el('span', { fontWeight: '700', color: C.cyan }, 'GET /topology · /links · /flows · /sdn/status'));
      apiRow.appendChild(el('span', { fontWeight: '700', color: C.textMuted }, 'Dashboard :8081'));
      apiBox.appendChild(apiRow);

      var pillRow = el('div', { display: 'flex', gap: '12px' });
      pillRow.appendChild(el('div', {
        flex: '1',
        padding: '10px 12px',
        borderRadius: '10px',
        backgroundColor: hexAlpha(C.cyan, 0.12),
        border: '1px solid ' + hexAlpha(C.cyan, 0.55),
        fontFamily: FONT_MONO,
        fontSize: '18px',
        fontWeight: '700',
        color: C.cyan,
        textAlign: 'center',
        fontVariantNumeric: 'tabular-nums',
        whiteSpace: 'nowrap'
      }, 'C4 Calib: 3.116 ± 0.181% (<10%)'));
      pillRow.appendChild(el('div', {
        flex: '1',
        padding: '10px 12px',
        borderRadius: '10px',
        backgroundColor: hexAlpha(C.emerald, 0.16),
        border: '1px solid ' + hexAlpha(C.emerald, 0.65),
        fontFamily: FONT_MONO,
        fontSize: '18px',
        fontWeight: '700',
        color: C.emeraldBright,
        textAlign: 'center',
        fontVariantNumeric: 'tabular-nums',
        whiteSpace: 'nowrap'
      }, 'Ubuntu Regressions: 16/16 PASS'));
      apiBox.appendChild(pillRow);
      leftCard.appendChild(apiBox);

      // ── Right Card (x: 966..1824, w: 858, y: 184..862, h: 678) ───────
      var rightCard = el('div', {
        position: 'absolute',
        left: '966px',
        top: '184px',
        width: '858px',
        height: '678px',
        backgroundColor: C.surface,
        border: '1.5px solid ' + hexAlpha(C.amber, 0.55),
        borderTop: '4px solid ' + C.amber,
        borderRadius: '18px',
        boxSizing: 'border-box',
        padding: '24px 28px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between'
      });
      wrap.appendChild(rightCard);

      var limHead = el('div', { display: 'flex', flexDirection: 'column', gap: '6px' });
      limHead.appendChild(el('div', {
        fontFamily: FONT_MONO,
        fontSize: '20px',
        fontWeight: '700',
        letterSpacing: '0.07em',
        color: C.amber,
        textTransform: 'uppercase'
      }, 'HONEST ENGINEERING SCOPE & LIMITATIONS'));
      limHead.appendChild(el('div', {
        fontSize: '20px',
        fontWeight: '500',
        color: C.textMuted,
        lineHeight: '1.3'
      }, 'Reported candidly from verified Ubuntu Mininet / OVS logs — no hidden caveats:'));
      rightCard.appendChild(limHead);

      var bullets = [
        {
          num: '01',
          accent: C.cyan,
          lead: 'Batch Provenance: ',
          text: 'Performance comparisons are Nov 25 (64k HTB burst/cburst) before the Nov 26 LLDP wait change; latest calibration (3.116%) is a separate Nov 26 batch (not pooled).'
        },
        {
          num: '02',
          accent: C.amber,
          lead: 'Stability Caution: ',
          text: 'Controller logs still show occasional link-deletion / relearning episodes — completed calibration ≠ general stability guarantee.'
        },
        {
          num: '03',
          accent: C.cyan,
          lead: 'Hold-Down & Flow Scope: ',
          text: '30 s hold-down is unit-tested (16/16) but not isolated live; flows are directed IPv4 MAC pairs; Port TX includes framing/background (distinct from rx Mbps, RTT & jitter).'
        }
      ];
      var bulletEls = [];
      var bStack = el('div', { display: 'flex', flexDirection: 'column', gap: '14px' });
      for (var bi = 0; bi < bullets.length; bi++) {
        var bItem = el('div', {
          padding: '16px 20px',
          borderRadius: '14px',
          backgroundColor: hexAlpha(C.bg, 0.76),
          border: '1.5px solid ' + C.border,
          borderLeft: '5px solid ' + bullets[bi].accent,
          display: 'flex',
          alignItems: 'flex-start',
          gap: '16px'
        });
        bItem.appendChild(el('span', {
          fontFamily: FONT_MONO,
          fontSize: '21px',
          fontWeight: '700',
          color: bullets[bi].accent,
          lineHeight: '1.35',
          flexShrink: '0'
        }, bullets[bi].num));
        var bText = el('div', {
          fontSize: '20px',
          fontWeight: '500',
          color: C.text,
          lineHeight: '1.38'
        });
        bText.appendChild(el('span', { fontWeight: '700', color: bullets[bi].accent }, bullets[bi].lead));
        bText.appendChild(el('span', { color: C.text }, bullets[bi].text));
        bItem.appendChild(bText);
        bStack.appendChild(bItem);
        bulletEls.push(bItem);
      }
      rightCard.appendChild(bStack);

      // Calibration footnote inside right card (Nov 26 separate batch)
      rightCard.appendChild(el('div', {
        borderTop: '1.5px solid ' + C.border,
        paddingTop: '14px',
        fontFamily: FONT_MONO,
        fontSize: '18px',
        color: C.textMuted,
        fontVariantNumeric: 'tabular-nums'
      }, 'C4 calibration (Nov 26): 3.116 ± 0.181% error (n = 5, <10% target)'));

      // ── Bottom GitHub Outro Bar (x: 96..1824, y: 882..992, h: 110) ───
      var outroBar = el('div', {
        position: 'absolute',
        left: '96px',
        top: '882px',
        width: '1728px',
        height: '110px',
        backgroundColor: C.header,
        border: '1.5px solid ' + hexAlpha(C.emerald, 0.65),
        borderRadius: '16px',
        boxSizing: 'border-box',
        padding: '0 32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '24px'
      });
      wrap.appendChild(outroBar);

      var brandCol = el('div', { display: 'flex', flexDirection: 'column', gap: '3px' });
      brandCol.appendChild(el('div', {
        fontSize: '30px',
        fontWeight: '700',
        letterSpacing: '-0.02em',
        color: C.text
      }, 'SDN Track 1: Intelligent Load Balancer'));
      brandCol.appendChild(el('div', {
        fontFamily: FONT_MONO,
        fontSize: '18px',
        color: C.textMuted
      }, 'ECE2606 · Helwan National University'));
      outroBar.appendChild(brandCol);

      outroBar.appendChild(el('div', {
        padding: '12px 22px',
        borderRadius: '12px',
        backgroundColor: hexAlpha(C.bg, 0.82),
        border: '1.5px solid ' + hexAlpha(C.emerald, 0.55),
        fontFamily: FONT_MONO,
        fontSize: '21px',
        fontWeight: '700',
        color: C.emeraldBright,
        whiteSpace: 'nowrap'
      }, 'Ubuntu Standalone: bash ubuntu/run.sh'));

      outroBar.appendChild(el('div', {
        fontFamily: FONT_MONO,
        fontSize: '20px',
        fontWeight: '700',
        color: C.cyan,
        textAlign: 'right',
        whiteSpace: 'nowrap'
      }, 'OS-Ken 3.1.1 · OpenFlow 1.3 · Mininet 2.3'));

      return {
        header: header,
        leftCard: leftCard,
        rightCard: rightCard,
        outroBar: outroBar,
        bulletEls: bulletEls,
        ftLinks: ftLinks,
        ftPathPts: ftPathPts,
        ftPackets: ftPackets
      };
    },

    update: function (state, localT, globalT, api) {
      var E = api.EASE;
      var M = api.math;
      var D = api.dom;

      // Smooth entrances (hero visible <= 0.5s, capped staggers <= 0.45s)
      D.setFadeSlide(state.header, M.seg(localT, 0.0, 0.42, E.power3Out), 18, 0.98);
      D.setFadeSlide(state.leftCard, M.seg(localT, 0.08, 0.50, E.power3Out), 22, 0.95);
      D.setFadeSlide(state.rightCard, M.seg(localT, 0.16, 0.50, E.power3Out), 22, 0.95);
      D.setFadeSlide(state.outroBar, M.seg(localT, 0.34, 0.50, E.power3Out), 20, 0.96);

      // Right-card bullets stagger smoothly (0.55..1.15s)
      for (var bi = 0; bi < state.bulletEls.length; bi++) {
        var bp = M.stagger(localT, 0.55, bi, 0.12, 0.45, E.power3Out);
        D.setFadeSlide(state.bulletEls[bi], bp, 14, 0.97);
      }

      // Fat-Tree 32 inter-switch links + 16 host links draw top-down by tier
      for (var li = 0; li < state.ftLinks.length; li++) {
        var lnk = state.ftLinks[li];
        var drawStart = 0.35 + lnk.tier * 0.28;
        var p = M.seg(localT, drawStart, 0.70, E.power3Out);
        D.setDraw(lnk.el, lnk.len, p);
      }

      // Deterministic packets flowing along H1 -> S1 -> S9 -> S17 -> S15 -> S8 -> H16
      var pktOp = M.seg(localT, 1.55, 0.45, E.power3Out);
      var pts = state.ftPathPts;
      var segCount = pts.length - 1;
      for (var fp = 0; fp < state.ftPackets.length; fp++) {
        var rawU = ((localT * 0.36) + (fp / state.ftPackets.length)) % 1;
        var u = rawU < 0 ? rawU + 1 : rawU;
        var segFloat = u * segCount;
        var sIdx = Math.min(segCount - 1, Math.floor(segFloat));
        var sFrac = segFloat - sIdx;
        var px = M.lerp(pts[sIdx].x, pts[sIdx + 1].x, sFrac);
        var py = M.lerp(pts[sIdx].y, pts[sIdx + 1].y, sFrac);
        state.ftPackets[fp].setAttribute('cx', px.toFixed(1));
        state.ftPackets[fp].setAttribute('cy', py.toFixed(1));
        state.ftPackets[fp].setAttribute('opacity', pktOp.toFixed(3));
      }
    }
  });
})();
