# Validation and remaining live checks

Performed locally on Windows with Python 3.12, Pillow 13.0.0, NumPy 2.3.5 and FFmpeg/ffprobe 9.0.1.

- 34 offline unit/regression tests: evidence excerpts, numeric claims, chart values, source IDs, unsupported 3D choices, caption timing, license filtering, duration-weighted media thresholds, silence/clipping, failed probes, duplicate-upload receipts and both graphic orientations.
- 3 real FFmpeg integration tests: graphic/photo/video decoding and concatenation; 1080×1920 rendering with audio; complete preview orchestration through rendering, thumbnail, credits, metadata and QC with fixture research/media/voice providers.
- Rendered and visually inspected a 30-second 1920×1080/24fps graphics demo and its contact sheet. The demonstration has fictional data and intentionally no narration. It cannot be published by the demo path.
- Compiled all production modules and entry point.

Not tested live here: Gemini/Groq/OpenRouter calls, RSS/search extraction against current sites, Commons/Pexels download services, premium or Edge narration, GitHub Actions execution, OAuth authorization, YouTube upload and GitHub Pages deployment. GitHub Secrets were not accessible, and external package installation was unavailable in this execution environment. Provider payloads follow the linked official references; the configured GitHub preview is still needed to validate these external services.

No actual YouTube video was uploaded and no old uploads/channel settings were changed during this work. Tests use generated video patterns and test signals, not premium voice samples. Run all test commands in README again after changing providers, dependencies or rendering code.
