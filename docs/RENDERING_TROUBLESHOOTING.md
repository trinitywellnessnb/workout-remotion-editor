# Real-media rendering and troubleshooting

## Validated workflow

Install Node 24+, FFmpeg/FFprobe, and a Chromium-compatible Remotion browser. Then run:

```bash
npm install
npm run validate:render
```

`validate:render` generates only rights-safe encoded sources (portrait 30 FPS with an obvious source tone, landscape 24 FPS, workout-like repetitive motion, click track, and rising soundtrack), bundles Remotion, renders the hybrid smoke MP4 through the production render bridge, probes it, writes `renders/phase18-smoke.mp4.qa.json`, and extracts representative PNG frames. For local personal footage, keep files beside the timeline JSON, run `npm run preflight -- --timeline ./plan.json`, use `--quality preview`, inspect locally, then render `--quality standard` or `high`. No upload is required.

## Common failures

- **FFmpeg/FFprobe missing:** install both from the operating system package manager and confirm `ffmpeg -version` and `ffprobe -version`.
- **npm install fails:** verify registry/network access and use the Node version above; dependencies are exactly pinned in `package.json`.
- **Chromium launch fails:** install the system libraries/browser reported by Remotion, or configure Remotion's supported browser executable. Do not disable sandboxing globally.
- **Missing, corrupt, or short media:** preflight names the segment, source, requested end, and probed duration before bundling.
- **Unsupported codec:** transcode a local working copy to H.264/yuv420p video and AAC audio; never overwrite the original.
- **Render crash:** retain the timeline and console stage error, retry preview at conservative concurrency (`--concurrency 1`), then inspect the named segment/source.
- **Audio absent:** confirm the plan has a soundtrack and valid trim. Source audio is intentionally muted by default.
- **Wrong duration:** compare planned and actual values in the `.qa.json`; more than one frame plus 10 ms is a validation failure.
