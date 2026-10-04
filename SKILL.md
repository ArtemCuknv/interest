---
name: russian-video-fish-hyperframes
description: Create a finished Russian narrated video from a topic using Fish Audio for voiceover and HyperFrames for visuals, synchronization, and MP4 rendering. Use when the user asks for a complete video from a topic with Russian narration.
---

# Russian video from a topic

Produce a playable MP4 and show it in chat. A topic is sufficient input. Infer reasonable defaults: 30–60 seconds, 16:9, Russian narration, 1080p, one narrator, and a clear visual style suited to the topic. Honor the user's duration, aspect ratio, style, source footage, and voice choices. Do not pause for optional choices when the user asked for the finished video.

## Workflow

1. Read the current `hyperframes` entry skill and follow its route for this particular video. Read `hyperframes-core`, `hyperframes-cli`, and their relevant references before authoring or rendering. If the video needs other media, use the appropriate domain skills. The user's request for an automatically completed MP4 authorizes the render in that run.
2. Check `node`, `npx`, `python`, `ffmpeg`, and `ffprobe`. Resolve missing prerequisites using the current HyperFrames CLI guidance. Use `npx hyperframes` to initialize and run the project; follow the project's pinned CLI when present.
3. Write a concise Russian script with a visual beat for every passage. Fact-check claims that depend on current or niche facts. Save the full script, visual plan, and source links in the project. Keep the spoken copy natural and punctuation clear; write numbers and abbreviations as they should be pronounced.
4. Use the user's exact Fish Audio TTS model version, or `s2.1-pro-free` when none is specified. Record the choice in the project and pass it with `--model` on every request; never switch models silently. Fish Audio can silently fall back to `s2.1-pro` for an unrecognized name. If the requested name is absent from the helper's `MODELS` set, verify it against the current [TTS endpoint documentation](https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech), add the exact documented ID to `MODELS` in `scripts/fish_tts.py`, and run `--dry-run` before synthesis. If it is unsupported or unavailable, stop and ask the user for another model.
5. Check only whether `FISH_API_KEY` is set in the process environment; do not print, search for, or save its value. If absent, finish everything possible up to synthesis and ask the user to set it locally. The optional `FISH_VOICE_ID` selects a saved voice; otherwise use Fish Audio's default voice. Distinguish a *TTS model version* (the `model` header) from a *voice model ID* (`reference_id`). If the user specifies a voice ID, pass it via `--voice-id` without substituting another voice.
6. Generate narration with `scripts/fish_tts.py` from the Russian script. The helper uses the JSON REST API and needs no third-party Python packages. For long scripts, split on sentence boundaries, synthesize passages separately with the chosen model and voice, and join them with FFmpeg. Report authentication, quota, and voice/model errors as blockers.
7. Measure the *actual* narration duration with `ffprobe`; time visual beats to the audio, leaving comfortable opening and ending space. Add the narration as a local `<audio>` track with a unique `id` in HyperFrames. Any music must be subordinate to narration; check levels in the rendered output. Do not load audio from the network at render time.
8. Run HyperFrames `check`, inspect representative frames, render MP4, and verify it with `ffprobe` for video stream, audio stream, duration, and nonzero file size. Fix concrete failures and repeat the affected gate. Include the MP4 in the final chat response as an absolute-path Markdown media embed and link the editable project.

## Fish Audio helper

From the skill directory, run:

```powershell
python scripts\fish_tts.py --text-file narration.txt --output narration.mp3 --model s2.1-pro-free
```

Optional: `--voice-id ID`, `--dry-run`. The helper uses `FISH_API_KEY` and optional `FISH_VOICE_ID`. Its API contract is documented at [Fish Audio TTS](https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech) and [model overview](https://docs.fish.audio/developer-guide/models-pricing/models-overview).
