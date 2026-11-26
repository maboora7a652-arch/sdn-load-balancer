(function () {
  "use strict";

  var WIDTH = 1920;
  var HEIGHT = 1080;
  var FPS = 30;
  var DURATION = 96.0;

  var COLORS = {
    bg: "#070E0D",
    bgRadial: "#0C1A17",
    surface: "#0F1E1B",
    border: "#1F3B34",
    header: "#163A31",
    text: "#F0F6F3",
    textMuted: "#93ACA1",
    linkIdle: "#4E6B60",
    switchStroke: "#71877B",
    emerald: "#10B981",
    emeraldBright: "#34D399",
    emeraldFill: "#147555",
    amber: "#F97316",
    amberFill: "#BF541A",
    crimson: "#EF4444",
    cyan: "#22D3EE"
  };

  function clamp(v, a, b) {
    return v < a ? a : (v > b ? b : v);
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function invLerp(a, b, v) {
    if (b === a) return 0;
    return clamp((v - a) / (b - a), 0, 1);
  }

  // Deterministic critically-damped spring (zeta = 1.0, zero overshoot, pure function of t)
  var SPRING_W = (2 * Math.PI) / 0.42;
  var SPRING_T = (function () {
    var eps = 0.001;
    var scan = 12 / SPRING_W;
    var n = 2400;
    for (var i = n; i >= 0; i--) {
      var t = (i / n) * scan;
      var pos = 1 - Math.exp(-SPRING_W * t) * (1 + SPRING_W * t);
      if (Math.abs(1 - pos) > eps) {
        return ((i + 1) / n) * scan;
      }
    }
    return scan;
  })();
  var SPRING_END = 1 - Math.exp(-SPRING_W * SPRING_T) * (1 + SPRING_W * SPRING_T);

  var EASE = {
    linear: function (t) {
      return clamp(t, 0, 1);
    },
    sineInOut: function (t) {
      var p = clamp(t, 0, 1);
      return -(Math.cos(Math.PI * p) - 1) / 2;
    },
    power2In: function (t) {
      var p = clamp(t, 0, 1);
      return p * p;
    },
    power2Out: function (t) {
      var p = clamp(t, 0, 1);
      return 1 - (1 - p) * (1 - p);
    },
    power3Out: function (t) {
      var p = clamp(t, 0, 1);
      var q = 1 - p;
      return 1 - q * q * q;
    },
    power3In: function (t) {
      var p = clamp(t, 0, 1);
      return p * p * p;
    },
    power4Out: function (t) {
      var p = clamp(t, 0, 1);
      var q = 1 - p;
      return 1 - q * q * q * q;
    },
    power4In: function (t) {
      var p = clamp(t, 0, 1);
      return p * p * p * p;
    },
    expoInOut: function (t) {
      var p = clamp(t, 0, 1);
      if (p === 0) return 0;
      if (p === 1) return 1;
      return p < 0.5
        ? Math.pow(2, 20 * p - 10) / 2
        : (2 - Math.pow(2, -20 * p + 10)) / 2;
    },
    springOut: function (t) {
      var p = clamp(t, 0, 1);
      if (p <= 0) return 0;
      if (p >= 1) return 1;
      var s = p * SPRING_T;
      var val = 1 - Math.exp(-SPRING_W * s) * (1 + SPRING_W * s);
      return clamp(val + p * (1 - SPRING_END), 0, 1);
    },
    steps: function (n) {
      var count = Math.max(1, Math.floor(n || 1));
      return function (t) {
        var p = clamp(t, 0, 1);
        if (p >= 1) return 1;
        return Math.floor(p * count) / count;
      };
    }
  };

  function seg(localT, start, dur, easeFn) {
    var fn = typeof easeFn === "function" ? easeFn : EASE.power3Out;
    if (dur <= 0) return localT >= start ? 1 : 0;
    return fn(clamp((localT - start) / dur, 0, 1));
  }

  function stagger(localT, start, idx, step, dur, easeFn) {
    return seg(localT, start + idx * step, dur, easeFn);
  }

  function hash(i, seed) {
    var x = (Math.imul((i | 0) + 374761393, 668265263) ^ Math.imul((seed | 0) + 1442695041, 2246822519)) | 0;
    x = Math.imul(x ^ (x >>> 13), 1274126177);
    x = (x ^ (x >>> 16)) >>> 0;
    return x / 4294967296;
  }

  var math = {
    clamp: clamp,
    lerp: lerp,
    invLerp: invLerp,
    seg: seg,
    stagger: stagger,
    hash: hash
  };

  var SVG_NS = "http://www.w3.org/2000/svg";

  function applyChildren(node, children) {
    if (children === null || children === undefined || children === false) return;
    if (Array.isArray(children)) {
      for (var i = 0; i < children.length; i++) applyChildren(node, children[i]);
    } else if (typeof children === "string" || typeof children === "number") {
      node.appendChild(document.createTextNode(String(children)));
    } else if (children instanceof Node) {
      node.appendChild(children);
    }
  }

  function h(tag, attrs, children) {
    var el = document.createElement(tag);
    if (attrs) {
      for (var k in attrs) {
        if (!Object.prototype.hasOwnProperty.call(attrs, k)) continue;
        var v = attrs[k];
        if (v === null || v === undefined || v === false) continue;
        if (k === "class" || k === "className") {
          el.className = String(v);
        } else if (k === "style") {
          if (typeof v === "string") {
            el.setAttribute("style", v);
          } else {
            for (var sk in v) {
              if (Object.prototype.hasOwnProperty.call(v, sk) && v[sk] !== undefined && v[sk] !== null) {
                el.style[sk] = String(v[sk]);
              }
            }
          }
        } else if (k === "text" || k === "textContent") {
          el.textContent = String(v);
        } else if (k === "html" || k === "innerHTML") {
          el.innerHTML = String(v);
        } else if (k === "dataset" && typeof v === "object") {
          for (var dk in v) {
            if (Object.prototype.hasOwnProperty.call(v, dk)) el.dataset[dk] = String(v[dk]);
          }
        } else {
          el.setAttribute(k, v === true ? "" : String(v));
        }
      }
    }
    applyChildren(el, children);
    return el;
  }

  function svgEl(tag, attrs, children) {
    var el = document.createElementNS(SVG_NS, tag);
    if (attrs) {
      for (var k in attrs) {
        if (!Object.prototype.hasOwnProperty.call(attrs, k)) continue;
        var v = attrs[k];
        if (v === null || v === undefined || v === false) continue;
        if (k === "text" || k === "textContent") {
          el.textContent = String(v);
        } else if (k === "style" && typeof v === "object") {
          for (var sk in v) {
            if (Object.prototype.hasOwnProperty.call(v, sk) && v[sk] !== undefined && v[sk] !== null) {
              el.style[sk] = String(v[sk]);
            }
          }
        } else {
          el.setAttribute(k, String(v));
        }
      }
    }
    applyChildren(el, children);
    return el;
  }

  function setFadeSlide(el, p, dy, scaleFrom, dx) {
    if (!el) return;
    var prog = clamp(p, 0, 1);
    var offsetY = (dy === undefined ? 24 : dy) * (1 - prog);
    var offsetX = (dx === undefined ? 0 : dx) * (1 - prog);
    var s0 = scaleFrom === undefined ? 0.95 : scaleFrom;
    var scale = lerp(s0, 1, prog);
    el.style.opacity = prog <= 0.0005 ? "0" : (prog >= 0.9995 ? "1" : prog.toFixed(4));
    el.style.transform =
      "translate3d(" + offsetX.toFixed(2) + "px, " + offsetY.toFixed(2) + "px, 0) scale(" + scale.toFixed(4) + ")";
  }

  function setDraw(pathEl, len, p) {
    if (!pathEl) return;
    var length = len;
    if (!(length > 0) && typeof pathEl.getTotalLength === "function") {
      try {
        length = pathEl.getTotalLength();
      } catch (e) {
        length = 100;
      }
    }
    var prog = clamp(p, 0, 1);
    pathEl.setAttribute("stroke-dasharray", length.toFixed(2));
    pathEl.setAttribute("stroke-dashoffset", (length * (1 - prog)).toFixed(2));
  }

  function fmt(n, d) {
    if (!Number.isFinite(n)) return "—";
    var digits = d === undefined ? 2 : d;
    return Number(n).toFixed(digits);
  }

  var dom = {
    h: h,
    svgEl: svgEl,
    setFadeSlide: setFadeSlide,
    setDraw: setDraw,
    fmt: fmt
  };

  function formatTimecode(sec) {
    var s = clamp(sec, 0, DURATION);
    var mins = Math.floor(s / 60);
    var rem = s - mins * 60;
    var mm = mins < 10 ? "0" + mins : String(mins);
    var ss = rem < 10 ? "0" + rem.toFixed(1) : rem.toFixed(1);
    return mm + ":" + ss;
  }

  var scenes = [];
  var mounted = false;
  var currentTime = 0;
  var playing = false;
  var rafId = null;
  var lastWallMs = 0;

  var bgCanvas = null;
  var bgCtx = null;
  var scenesLayer = null;
  var hudChapterText = null;
  var hudProgressFill = null;
  var hudTime = null;
  var hudTicks = null;
  var scrubberEl = null;
  var ctrlTimeEl = null;
  var btnPlayEl = null;
  var chapterBtnEls = [];

  function drawBackground(t) {
    if (!bgCtx) return;
    var ctx = bgCtx;

    // Base deep obsidian-forest backdrop
    ctx.fillStyle = COLORS.bg;
    ctx.fillRect(0, 0, WIDTH, HEIGHT);

    // Subtle slow ambient radial telemetry glow (pure function of t)
    var driftX = Math.sin(t * 0.14) * 90;
    var driftY = Math.cos(t * 0.11) * 45;
    var rad1 = ctx.createRadialGradient(960 + driftX, 460 + driftY, 60, 960 + driftX, 460 + driftY, 1080);
    rad1.addColorStop(0, "rgba(22, 58, 49, 0.34)");
    rad1.addColorStop(0.55, "rgba(12, 26, 23, 0.24)");
    rad1.addColorStop(1, "rgba(7, 14, 13, 0)");
    ctx.fillStyle = rad1;
    ctx.fillRect(0, 0, WIDTH, HEIGHT);

    // Secondary soft emerald/cyan atmospheric corner lift
    var rad2 = ctx.createRadialGradient(1680 - driftX * 0.5, 180 + driftY * 0.4, 20, 1680, 180, 620);
    rad2.addColorStop(0, "rgba(34, 211, 238, 0.06)");
    rad2.addColorStop(1, "rgba(7, 14, 13, 0)");
    ctx.fillStyle = rad2;
    ctx.fillRect(0, 0, WIDTH, HEIGHT);

    // Orthographic 48px technical grid with slow deterministic scroll
    var spacing = 48;
    var offX = ((t * 6) % spacing + spacing) % spacing;
    var offY = ((t * 3) % spacing + spacing) % spacing;

    ctx.strokeStyle = "rgba(166, 184, 172, 0.045)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (var x = offX; x < WIDTH; x += spacing) {
      var xi = Math.round(x) + 0.5;
      ctx.moveTo(xi, 0);
      ctx.lineTo(xi, HEIGHT);
    }
    for (var y = offY; y < HEIGHT; y += spacing) {
      var yi = Math.round(y) + 0.5;
      ctx.moveTo(0, yi);
      ctx.lineTo(WIDTH, yi);
    }
    ctx.stroke();

    // Subtle deterministic telemetry dust nodes at select grid intersections
    ctx.fillStyle = "rgba(52, 211, 153, 0.14)";
    for (var i = 0; i < 24; i++) {
      var gx = Math.floor(hash(i, 11) * 40) * spacing + offX;
      var gy = Math.floor(hash(i, 29) * 22) * spacing + offY;
      var pulse = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(t * 0.9 + hash(i, 73) * Math.PI * 2));
      ctx.globalAlpha = pulse * 0.28;
      ctx.fillRect(gx - 1.5, gy - 1.5, 3, 3);
    }
    ctx.globalAlpha = 1;

    // Subtle safe-area corner registration brackets (pure telemetry framing)
    ctx.strokeStyle = "rgba(147, 172, 161, 0.16)";
    ctx.lineWidth = 1.5;
    var mX = 64, mY = 58, bLen = 18;
    var corners = [
      [mX, mY, 1, 1],
      [WIDTH - mX, mY, -1, 1],
      [mX, HEIGHT - mY, 1, -1],
      [WIDTH - mX, HEIGHT - mY, -1, -1]
    ];
    ctx.beginPath();
    for (var c = 0; c < corners.length; c++) {
      var cx = corners[c][0], cy = corners[c][1], dx = corners[c][2], dy = corners[c][3];
      ctx.moveTo(cx + dx * bLen, cy);
      ctx.lineTo(cx, cy);
      ctx.lineTo(cx, cy + dy * bLen);
    }
    ctx.stroke();
  }

  function registerScene(sceneDef) {
    if (!sceneDef || !sceneDef.id) return;
    scenes.push({
      id: sceneDef.id,
      index: sceneDef.index !== undefined ? sceneDef.index : scenes.length,
      title: sceneDef.title || sceneDef.id,
      chapter: sceneDef.chapter || ("0" + (scenes.length + 1)),
      start: Number(sceneDef.start) || 0,
      duration: Number(sceneDef.duration) || 10,
      mount: sceneDef.mount,
      update: sceneDef.update,
      _el: null,
      _state: null
    });
  }

  function getActiveSceneIndex(t) {
    for (var i = 0; i < scenes.length; i++) {
      var s = scenes[i];
      var isLast = i === scenes.length - 1;
      if (t >= s.start && (isLast ? t <= s.start + s.duration + 0.001 : t < s.start + s.duration)) {
        return i;
      }
    }
    return scenes.length > 0 ? scenes.length - 1 : -1;
  }

  var TRANS_IN = 0.35;
  var TRANS_OUT = 0.28;

  function seek(timeSec) {
    if (!mounted) init();
    var t = clamp(Number(timeSec) || 0, 0, DURATION);
    currentTime = t;

    drawBackground(t);

    var activeIdx = getActiveSceneIndex(t);
    var activeScene = activeIdx >= 0 ? scenes[activeIdx] : null;

    // Update persistent HUD
    if (hudChapterText && activeScene) {
      hudChapterText.textContent = activeScene.chapter;
    }
    if (hudProgressFill) {
      hudProgressFill.style.transform = "scaleX(" + (t / DURATION).toFixed(5) + ")";
    }
    var tc = formatTimecode(t) + " / " + formatTimecode(DURATION);
    if (hudTime) hudTime.textContent = tc;
    if (ctrlTimeEl) ctrlTimeEl.textContent = tc;
    if (scrubberEl) scrubberEl.value = t.toFixed(4);

    for (var i = 0; i < scenes.length; i++) {
      var s = scenes[i];
      if (!s._el) continue;

      if (i === activeIdx) {
        s._el.style.display = "block";
        s._el.style.visibility = "visible";

        var localT = clamp(t - s.start, 0, s.duration);
        if (typeof s.update === "function") {
          s.update(s._state, localT, t, api);
        }

        // Velocity-matched transition envelope (zero double-exposure overlap)
        var op = 1;
        var shiftY = 0;
        var scale = 1;

        if (i > 0 && localT < TRANS_IN) {
          var pIn = EASE.power4Out(localT / TRANS_IN);
          op = pIn;
          shiftY = (1 - pIn) * 20;
          scale = lerp(0.985, 1, pIn);
        } else if (i < scenes.length - 1 && localT > s.duration - TRANS_OUT) {
          var pOut = EASE.power3In((localT - (s.duration - TRANS_OUT)) / TRANS_OUT);
          op = 1 - pOut;
          shiftY = -pOut * 16;
          scale = lerp(1, 0.988, pOut);
        }

        s._el.style.opacity = op.toFixed(4);
        s._el.style.transform =
          "translate3d(0, " + shiftY.toFixed(2) + "px, 0) scale(" + scale.toFixed(4) + ")";
      } else {
        s._el.style.display = "none";
        s._el.style.visibility = "hidden";
      }

      if (chapterBtnEls[i]) {
        chapterBtnEls[i].classList.toggle("active", i === activeIdx);
      }
    }
  }

  function fitStageToViewport() {
    if (document.body.classList.contains("render-mode")) return;
    var stage = document.getElementById("stage");
    var vp = document.getElementById("viewport");
    if (!stage || !vp) return;
    var rect = vp.getBoundingClientRect();
    var pad = 20;
    var sx = Math.max(0.1, (rect.width - pad) / WIDTH);
    var sy = Math.max(0.1, (rect.height - pad) / HEIGHT);
    var s = Math.min(sx, sy, 1);
    stage.style.transform = "scale(" + s.toFixed(4) + ")";
  }

  function setPlaying(next) {
    playing = Boolean(next);
    if (btnPlayEl) btnPlayEl.textContent = playing ? "Pause" : "Play";
    if (playing) {
      lastWallMs = performance.now();
      var tick = function (now) {
        if (!playing) return;
        var dt = (now - lastWallMs) / 1000;
        lastWallMs = now;
        var nextT = currentTime + dt;
        if (nextT >= DURATION) {
          seek(DURATION);
          setPlaying(false);
          return;
        }
        seek(nextT);
        rafId = requestAnimationFrame(tick);
      };
      rafId = requestAnimationFrame(tick);
    } else if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
  }

  function bindInteractiveControls() {
    btnPlayEl = document.getElementById("btn-play");
    var btnPrev = document.getElementById("btn-prev");
    var btnNext = document.getElementById("btn-next");
    scrubberEl = document.getElementById("scrubber");
    ctrlTimeEl = document.getElementById("ctrl-time");
    var chapterBox = document.getElementById("chapter-buttons");

    if (scrubberEl) {
      scrubberEl.max = String(DURATION);
      scrubberEl.addEventListener("input", function () {
        if (playing) setPlaying(false);
        seek(parseFloat(scrubberEl.value) || 0);
      });
    }
    if (btnPlayEl) {
      btnPlayEl.addEventListener("click", function () {
        if (!playing && currentTime >= DURATION - 0.05) seek(0);
        setPlaying(!playing);
      });
    }
    if (btnPrev) {
      btnPrev.addEventListener("click", function () {
        if (playing) setPlaying(false);
        seek(currentTime - 1 / FPS);
      });
    }
    if (btnNext) {
      btnNext.addEventListener("click", function () {
        if (playing) setPlaying(false);
        seek(currentTime + 1 / FPS);
      });
    }

    if (chapterBox) {
      chapterBox.innerHTML = "";
      chapterBtnEls = scenes.map(function (s, idx) {
        var b = document.createElement("button");
        b.type = "button";
        b.textContent = String(idx + 1).padStart(2, "0");
        b.title = s.chapter + " (" + s.start + "s)";
        b.addEventListener("click", function () {
          if (playing) setPlaying(false);
          seek(s.start + 0.05);
        });
        chapterBox.appendChild(b);
        return b;
      });
    }

    window.addEventListener("keydown", function (ev) {
      if (ev.code === "Space") {
        ev.preventDefault();
        if (!playing && currentTime >= DURATION - 0.05) seek(0);
        setPlaying(!playing);
      } else if (ev.code === "ArrowLeft") {
        ev.preventDefault();
        if (playing) setPlaying(false);
        seek(currentTime - 1 / FPS);
      } else if (ev.code === "ArrowRight") {
        ev.preventDefault();
        if (playing) setPlaying(false);
        seek(currentTime + 1 / FPS);
      }
    });

    window.addEventListener("resize", fitStageToViewport);
    fitStageToViewport();
  }

  function init() {
    if (mounted) return;
    mounted = true;

    var params = new URLSearchParams(window.location.search || "");
    var isRender = params.get("render") === "1";
    if (isRender) {
      document.body.classList.add("render-mode");
    }

    bgCanvas = document.getElementById("bg-canvas");
    bgCtx = bgCanvas ? bgCanvas.getContext("2d") : null;
    scenesLayer = document.getElementById("scenes-layer");
    hudChapterText = document.getElementById("hud-chapter-text");
    hudProgressFill = document.getElementById("hud-progress-fill");
    hudTime = document.getElementById("hud-time");
    hudTicks = document.getElementById("hud-ticks");

    scenes.sort(function (a, b) {
      return a.index - b.index || a.start - b.start;
    });

    if (scenes.length > 0) {
      var last = scenes[scenes.length - 1];
      var computedDur = last.start + last.duration;
      if (computedDur > 0) {
        DURATION = computedDur;
        api.DURATION = DURATION;
        window.__meta.durationSec = DURATION;
        window.__meta.totalFrames = Math.round(DURATION * FPS);
      }
    }

    // Render scene boundary tick markers on bottom rail
    if (hudTicks) {
      hudTicks.innerHTML = "";
      for (var tIdx = 1; tIdx < scenes.length; tIdx++) {
        var tick = document.createElement("div");
        tick.className = "hud-tick";
        tick.style.left = ((scenes[tIdx].start / DURATION) * 100).toFixed(3) + "%";
        hudTicks.appendChild(tick);
      }
    }

    // Mount all scenes upfront (hidden until active)
    if (scenesLayer) {
      scenesLayer.innerHTML = "";
      for (var i = 0; i < scenes.length; i++) {
        var s = scenes[i];
        var root = document.createElement("div");
        root.className = "scene";
        root.id = "scene-" + s.id;
        root.style.display = "none";
        scenesLayer.appendChild(root);
        s._el = root;
        s._state = typeof s.mount === "function" ? (s.mount(root, api) || {}) : {};
      }
    }

    if (!isRender) {
      bindInteractiveControls();
    }

    var startT = parseFloat(params.get("t"));
    seek(Number.isFinite(startT) ? startT : 0);
  }

  var api = {
    WIDTH: WIDTH,
    HEIGHT: HEIGHT,
    FPS: FPS,
    DURATION: DURATION,
    COLORS: COLORS,
    EASE: EASE,
    math: math,
    dom: dom,
    registerScene: registerScene,
    init: init,
    seek: seek,
    getScenes: function () { return scenes.slice(); }
  };

  window.SDN_VIDEO = api;
  window.__seek = seek;
  window.__meta = {
    width: WIDTH,
    height: HEIGHT,
    fps: FPS,
    durationSec: DURATION,
    totalFrames: Math.round(DURATION * FPS)
  };
})();
