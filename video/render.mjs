#!/usr/bin/env node
/**
 * 100% OFFLINE deterministic renderer for video/index.html
 * Uses local playwright-core + chrome-headless-shell.exe + full GPL ffmpeg-win-x86_64-v9.0.2.exe
 *
 * Examples:
 *   node video/render.mjs --stills 2,14,27,40,52,65,78,91
 *   node video/render.mjs --verify-determinism
 *   node video/render.mjs --mp4
 *   node video/render.mjs --gif
 */

import { spawn } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..");

const DEFAULT_PW_CORE =
  process.env.PLAYWRIGHT_CORE_PATH ||
  String.raw`C:\Users\Fouad\AppData\Roaming\npm\node_modules\omniroute\node_modules\playwright-core`;

const DEFAULT_CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  String.raw`C:\Users\Fouad\AppData\Local\ms-playwright\chromium_headless_shell-1228\chrome-headless-shell-win64\chrome-headless-shell.exe`,
  String.raw`C:\Users\Fouad\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe`
].filter(Boolean);

const DEFAULT_FFMPEG_CANDIDATES = [
  process.env.FFMPEG_PATH,
  String.raw`C:\Users\Fouad\AppData\Local\Programs\Python\Python311\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v9.0.2.exe`,
  String.raw`C:\Users\Fouad\.gemini\antigravity\scratch\ece2606-motion-v3\node_modules\@remotion\compositor-win32-x64-msvc\ffmpeg.exe`
].filter(Boolean);

function pickFirstExisting(candidates, label) {
  for (const p of candidates) {
    if (p && fs.existsSync(p)) return p;
  }
  throw new Error(`Missing required ${label}. Checked:\n  - ${candidates.join("\n  - ")}`);
}

function parseArgs(argv) {
  const args = {
    stills: null,
    verifyDeterminism: false,
    mp4: false,
    gif: false,
    gifFull: false,
    workers: 4,
    fps: 30,
    crf: 18,
    preset: "medium",
    mp4Out: path.join(REPO_ROOT, "output", "video", "sdn-load-balancer-explainer.mp4"),
    gifOut: path.join(REPO_ROOT, "output", "video", "sdn-load-balancer-preview.gif"),
    stillsDir: path.join(REPO_ROOT, "output", "video", "stills")
  };

  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--stills") {
      args.stills = (argv[++i] || "").split(",").map((s) => Number(s.trim())).filter(Number.isFinite);
    } else if (a === "--verify-determinism") {
      args.verifyDeterminism = true;
    } else if (a === "--mp4") {
      args.mp4 = true;
    } else if (a === "--gif") {
      args.gif = true;
    } else if (a === "--gif-full") {
      args.gif = true;
      args.gifFull = true;
    } else if (a === "--workers") {
      args.workers = Math.max(1, Math.min(8, Number(argv[++i]) || 4));
    } else if (a === "--fps") {
      args.fps = Math.max(1, Number(argv[++i]) || 30);
    } else if (a === "--crf") {
      args.crf = Number(argv[++i]) || 18;
    } else if (a === "--preset") {
      args.preset = argv[++i] || "medium";
    } else if (a === "--out") {
      args.mp4Out = path.resolve(argv[++i]);
    } else if (a === "--gif-out") {
      args.gifOut = path.resolve(argv[++i]);
    } else if (a === "--stills-dir") {
      args.stillsDir = path.resolve(argv[++i]);
    }
  }
  return args;
}

function loadPlaywrightChromium() {
  if (!fs.existsSync(DEFAULT_PW_CORE)) {
    throw new Error(`playwright-core not found at ${DEFAULT_PW_CORE}`);
  }
  const require = createRequire(import.meta.url);
  return require(DEFAULT_PW_CORE).chromium;
}

async function openRenderPage(browser, pageUrl) {
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (err) => errors.push(`pageerror: ${err.message}`));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(`console.error: ${msg.text()}`);
  });

  const cdp = await context.newCDPSession(page);
  await page.goto(pageUrl, { waitUntil: "load" });
  await page.evaluate(async () => {
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
  });
  return { context, page, cdp, errors };
}

async function captureFrameAt(worker, timeSec) {
  await worker.page.evaluate((t) => {
    return new Promise((resolve) => {
      window.__seek(t);
      requestAnimationFrame(() => requestAnimationFrame(resolve));
    });
  }, timeSec);
  const { data } = await worker.cdp.send("Page.captureScreenshot", { format: "png" });
  return Buffer.from(data, "base64");
}

function sha256(buf) {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

function runFfmpeg(ffmpegPath, ffArgs, label) {
  return new Promise((resolve, reject) => {
    const proc = spawn(ffmpegPath, ffArgs, { stdio: ["ignore", "ignore", "pipe"] });
    let stderr = "";
    proc.stderr.on("data", (d) => { stderr += d.toString(); });
    proc.on("close", (code) => {
      if (code === 0) resolve(stderr);
      else reject(new Error(`${label} failed (exit ${code}):\n${stderr.slice(-1500)}`));
    });
  });
}

async function probeStreamLine(ffmpegPath, filePath) {
  return new Promise((resolve) => {
    const proc = spawn(ffmpegPath, ["-i", filePath], { stdio: ["ignore", "ignore", "pipe"] });
    let stderr = "";
    proc.stderr.on("data", (d) => { stderr += d.toString(); });
    proc.on("close", () => {
      const line = stderr.split(/\r?\n/).find((l) => l.includes("Video:")) || "";
      resolve(line.trim());
    });
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.stills && !args.verifyDeterminism && !args.mp4 && !args.gif) {
    console.log("Usage: node video/render.mjs [--stills 2,14,27,...] [--verify-determinism] [--mp4] [--gif] [--gif-full]");
    process.exit(0);
  }

  const indexHtml = path.join(__dirname, "index.html");
  if (!fs.existsSync(indexHtml)) {
    throw new Error(`Missing composition entry: ${indexHtml}`);
  }
  const renderUrl = pathToFileURL(indexHtml).href + "?render=1";

  const needsBrowser = Boolean(args.stills || args.verifyDeterminism || args.mp4);
  const needsFfmpeg = Boolean(args.mp4 || args.gif);
  const ffmpegPath = needsFfmpeg ? pickFirstExisting(DEFAULT_FFMPEG_CANDIDATES, "FFmpeg binary") : null;

  let browser = null;
  const workers = [];

  try {
    if (needsBrowser) {
      const chromePath = pickFirstExisting(DEFAULT_CHROME_CANDIDATES, "Chromium headless binary");
      const chromium = loadPlaywrightChromium();
      console.log(`[render] Browser: ${chromePath}`);
      browser = await chromium.launch({
        executablePath: chromePath,
        headless: true,
        args: [
          "--no-sandbox",
          "--disable-gpu",
          "--hide-scrollbars",
          "--disable-background-timer-throttling",
          "--font-render-hinting=none"
        ]
      });

      const workerCount = args.mp4 ? args.workers : 1;
      for (let i = 0; i < workerCount; i++) {
        workers.push(await openRenderPage(browser, renderUrl));
      }
      const meta = await workers[0].page.evaluate(() => window.__meta);
      console.log(`[render] Loaded composition: ${meta.width}x${meta.height} @ ${meta.fps}fps, duration=${meta.durationSec}s`);

      // 1. Stills capture
      if (args.stills && args.stills.length > 0) {
        fs.mkdirSync(args.stillsDir, { recursive: true });
        for (const sec of args.stills) {
          const buf = await captureFrameAt(workers[0], sec);
          const name = `still_${String(sec).replace(/\./g, "_")}s.png`;
          const outPath = path.join(args.stillsDir, name);
          fs.writeFileSync(outPath, buf);
          console.log(`[stills] t=${sec}s -> ${outPath} (${(buf.length / 1024).toFixed(1)} KB)`);
        }
      }

      // 2. Determinism check (forward vs backward seek pixel hash)
      if (args.verifyDeterminism) {
        const checks = [
          { target: 12.0, jump: 62.5 },
          { target: 48.0, jump: 88.0 }
        ];
        for (const chk of checks) {
          const bufA = await captureFrameAt(workers[0], chk.target);
          await captureFrameAt(workers[0], chk.jump);
          const bufB = await captureFrameAt(workers[0], chk.target);
          const hashA = sha256(bufA);
          const hashB = sha256(bufB);
          if (hashA !== hashB) {
            throw new Error(`Determinism FAILED at t=${chk.target}s:\n  direct:   ${hashA}\n  backward: ${hashB}`);
          }
          console.log(`[determinism] PASS t=${chk.target}s (after jump ${chk.jump}s) sha256=${hashA.slice(0, 16)}...`);
        }
      }

      // 3. Full H.264 MP4 render (4-page parallel capture -> sequential PNG pipe to FFmpeg)
      if (args.mp4) {
        fs.mkdirSync(path.dirname(args.mp4Out), { recursive: true });
        const totalFrames = Math.round(meta.durationSec * args.fps);
        console.log(`[mp4] Rendering ${totalFrames} frames (${meta.durationSec}s @ ${args.fps}fps) with ${workers.length} workers -> ${args.mp4Out}`);

        const ff = spawn(ffmpegPath, [
          "-y",
          "-f", "image2pipe",
          "-vcodec", "png",
          "-framerate", String(args.fps),
          "-i", "-",
          "-c:v", "libx264",
          "-preset", args.preset,
          "-crf", String(args.crf),
          "-pix_fmt", "yuv420p",
          "-movflags", "+faststart",
          args.mp4Out
        ], { stdio: ["pipe", "ignore", "pipe"] });

        let ffErr = "";
        ff.stderr.on("data", (d) => { ffErr += d.toString(); });

        const t0 = Date.now();
        for (let base = 0; base < totalFrames; base += workers.length) {
          const batchSize = Math.min(workers.length, totalFrames - base);
          const promises = [];
          for (let j = 0; j < batchSize; j++) {
            const frameIdx = base + j;
            promises.push(captureFrameAt(workers[j], frameIdx / args.fps));
          }
          const buffers = await Promise.all(promises);
          for (const buf of buffers) {
            if (!ff.stdin.write(buf)) {
              await new Promise((r) => ff.stdin.once("drain", r));
            }
          }
          const done = base + batchSize;
          if (done % 120 === 0 || done === totalFrames) {
            const elapsed = (Date.now() - t0) / 1000;
            const fpsActual = done / Math.max(0.01, elapsed);
            const eta = (totalFrames - done) / Math.max(0.01, fpsActual);
            console.log(`[mp4] ${done}/${totalFrames} frames (${((done / totalFrames) * 100).toFixed(1)}%) · ${fpsActual.toFixed(1)} fps · ETA ${eta.toFixed(0)}s`);
          }
        }

        ff.stdin.end();
        const exitCode = await new Promise((res) => ff.on("close", res));
        if (exitCode !== 0) {
          throw new Error(`FFmpeg MP4 encode failed (exit ${exitCode}):\n${ffErr.slice(-1500)}`);
        }
        const stat = fs.statSync(args.mp4Out);
        const stream = await probeStreamLine(ffmpegPath, args.mp4Out);
        console.log(`[mp4] DONE: ${(stat.size / (1024 * 1024)).toFixed(2)} MB | ${stream}`);
      }

      // Check for any runtime console/page errors
      const allErrors = workers.flatMap((w) => w.errors);
      if (allErrors.length > 0) {
        throw new Error(`Page runtime errors detected:\n  ${allErrors.join("\n  ")}`);
      }
    }

    // 4. 2-Pass Lanczos Palette GIF preview
    if (args.gif) {
      if (!fs.existsSync(args.mp4Out)) {
        throw new Error(`Cannot build GIF: MP4 not found at ${args.mp4Out}. Run with --mp4 first.`);
      }
      fs.mkdirSync(path.dirname(args.gifOut), { recursive: true });
      if (args.gifFull) {
        console.log(`[gif] Encoding full overview GIF -> ${args.gifOut}`);
        await runFfmpeg(ffmpegPath, [
          "-y", "-i", args.mp4Out,
          "-vf", "fps=10,scale=800:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer",
          args.gifOut
        ], "GIF full encode");
      } else {
        // Concise ~13s README highlight reel across key visual beats:
        // Hook (0.5-3.0s), Bottleneck (13.5-16.5s), MBB Reroute (48.0-52.0s), Failover (60.5-64.5s)
        console.log(`[gif] Encoding 13.5s README highlight GIF -> ${args.gifOut}`);
        const filter = [
          "[0:v]trim=start=0.5:end=3.0,setpts=PTS-STARTPTS[v0]",
          "[0:v]trim=start=13.5:end=16.5,setpts=PTS-STARTPTS[v1]",
          "[0:v]trim=start=48.0:end=52.0,setpts=PTS-STARTPTS[v2]",
          "[0:v]trim=start=60.5:end=64.5,setpts=PTS-STARTPTS[v3]",
          "[v0][v1][v2][v3]concat=n=4:v=1:a=0,fps=12,scale=800:-1:flags=lanczos,split[s0][s1]",
          "[s0]palettegen=max_colors=128:stats_mode=diff[p]",
          "[s1][p]paletteuse=dither=bayer:bayer_scale=3"
        ].join(";");
        await runFfmpeg(ffmpegPath, [
          "-y", "-i", args.mp4Out,
          "-filter_complex", filter,
          args.gifOut
        ], "GIF highlight encode");
      }
      const gStat = fs.statSync(args.gifOut);
      console.log(`[gif] DONE: ${(gStat.size / (1024 * 1024)).toFixed(2)} MB -> ${args.gifOut}`);
    }
  } finally {
    for (const w of workers) {
      try { await w.context.close(); } catch {}
    }
    if (browser) {
      try { await browser.close(); } catch {}
    }
  }
}

main().catch((err) => {
  console.error("[render] ERROR:", err.message || err);
  process.exit(1);
});
