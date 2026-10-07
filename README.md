# Insight Downloader 0.7.2

Insight Downloader is a compact Windows desktop downloader built on `yt-dlp`, PySide6 Essentials and FFmpeg.
Version 0.7 focuses on product-grade UI/UX while keeping the lightweight runtime architecture introduced in 0.6.

## Product UI

The main window is intentionally fixed at **1000×720** and does not maximize. The complete download flow fits in one window without scrolling:

1. Paste or drop a link.
2. Analyze it.
3. Choose Video / MP3 / WAV.
4. Pick video or audio quality.
5. Download.

The 0.7 design system uses:

- Segoe UI Variable / Segoe UI
- neutral dark/light surfaces
- minimal borders and separators
- one restrained purple primary accent
- subtle hover feedback
- explicit select chevrons
- modal bottom-sheet errors
- compact success states instead of permanent 100% progress bars
- system / dark / light themes

## Audio quality

MP3 presets:

- 320 kbps
- 256 kbps
- 192 kbps
- 128 kbps

WAV presets:

- source sample rate · 16-bit PCM
- 48 kHz · 24-bit PCM
- 48 kHz · 16-bit PCM
- 44.1 kHz · 16-bit PCM

Insight downloads the best available source audio first and performs the selected conversion with FFmpeg.

## Settings

Settings contains normal user-facing options only:

- theme
- default download directory
- automatic update checks
- current version / update check

Technical runtime information is hidden under **Diagnostics**.

## Development setup

Windows 10/11 x64 is the primary release target.

```bat
setup_windows.cmd
run.cmd
```

For local media downloads, place:

```text
bin/ffmpeg.exe
bin/ffprobe.exe
```

QuickJS is prepared automatically by the setup script.

## Production release

Requirements:

- Python 3.11
- Inno Setup 6
- Git
- GitHub CLI (`gh`) for publishing
- `bin/ffmpeg.exe`
- `bin/ffprobe.exe`

Build:

```bat
build_release.cmd
```

Expected output:

```text
release/
├── InsightDownloaderSetup-v0.7.2.exe
├── InsightDownloader-update.zip
├── InsightDownloader-update.zip.sha256
├── InsightMediaRuntime.7z
└── InsightMediaRuntime.7z.sha256
```

Publish:

```bat
publish_release.cmd
```

## Distribution architecture

The main installer contains the application, Qt Essentials, yt-dlp and QuickJS, but not FFmpeg.
FFmpeg is distributed once as `InsightMediaRuntime.7z` and installed to the user's local app data on first use.
Normal application updates therefore do not re-download the media runtime.

## YouTube

YouTube support uses:

- yt-dlp
- yt-dlp-ejs
- QuickJS-NG
- WPC PO Token provider
- a managed Chromium instance for token acquisition

Insight does not read the user's Chrome cookie database.

## Legal

Use Insight Downloader only for content you are permitted to save. The application does not bypass DRM.
