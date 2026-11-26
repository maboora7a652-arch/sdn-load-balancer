# SDN Track 1 — Offline Motion Graphics Explainer

Self-contained, 100% offline 1920×1080 @ 30fps motion graphics explainer for the **SDN Track 1: Intelligent Load Balancer with Fault Tolerance** project.

## Interactive Preview (No Build or Server Required)

Open `video/index.html` directly in Chrome or Edge (`file://...`).

- **Space** — Play / Pause
- **Left / Right Arrow** — Step backward / forward by 1 frame (`1/30 s`)
- **01–08 buttons** — Jump directly to any chapter
- Add `?render=1` to hide playback chrome and lock the stage to 1:1 `1920×1080`

## Deterministic Offline Rendering

All rendering runs locally with zero network requests using the installed Playwright Chromium headless shell and full GPL FFmpeg binary (`libx264` + 2-pass Lanczos GIF).

```powershell
# 1. Capture QA keyframe PNG stills to output/video/stills/
node video/render.mjs --stills 2,14,27,40,52,65,78,91

# 2. Verify seek determinism (forward vs backward SHA-256 pixel hash check)
node video/render.mjs --verify-determinism

# 3. Render full 96s 1920x1080 30fps H.264 MP4 -> output/video/sdn-load-balancer-explainer.mp4
node video/render.mjs --mp4

# 4. Build concise README highlight GIF -> output/video/sdn-load-balancer-preview.gif
node video/render.mjs --gif
```

Optional environment overrides if local paths differ: `CHROME_PATH`, `FFMPEG_PATH`, `PLAYWRIGHT_CORE_PATH`.

## Architecture

- `video/index.html` — Plain-script stage host and optional preview scrubber
- `video/styles.css` — Dark SDN telemetry design system (zero CSS transitions/keyframes inside `#stage`)
- `video/engine.js` — Deterministic timeline engine (`window.__seek(timeSec)`), smooth engineering easings, persistent HUD chrome
- `video/grid-svg.js` — Reusable 2×3 Lab Grid (`S1–S6`, 7 links, `H1–H6`, deterministic packet flows, link-cut FX)
- `video/scenes/scene1-hook.js` .. `scene8-outro.js` — 8 modular scenes grounded in verified repository data
- `video/render.mjs` — Parallel headless Chromium CDP PNG pipe to FFmpeg H.264 MP4 & 2-pass GIF
