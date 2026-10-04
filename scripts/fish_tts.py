"""Generate a local MP3 narration through Fish Audio's documented REST API."""

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


API_URL = "https://api.fish.audio/v1/tts"
# Keep this allowlist aligned with the documented /v1/tts model header. Fish
# silently uses s2.1-pro for an unrecognized value, so never send one blindly.
MODELS = {"s2.1-pro-free", "s2.1-pro", "s2-pro", "s1", "drama-3-preview"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text-file", type=Path, required=True, help="UTF-8 narration text")
    parser.add_argument("--output", type=Path, required=True, help="Output MP3 path")
    parser.add_argument("--voice-id", help="Saved Fish Audio voice model ID")
    parser.add_argument(
        "--model", choices=sorted(MODELS), default="s2.1-pro-free",
        help="Exact Fish Audio TTS model (default: s2.1-pro-free)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs without sending audio request")
    args = parser.parse_args()

    try:
        spoken_text = args.text_file.read_text(encoding="utf-8-sig").strip()
    except OSError as exc:
        parser.error(f"Cannot read text file: {exc}")
    if not spoken_text:
        parser.error("Text file is empty")
    if args.output.suffix.lower() != ".mp3":
        parser.error("Output path must end in .mp3")
    voice_id = args.voice_id or os.environ.get("FISH_VOICE_ID", "").strip()
    payload = {"text": spoken_text, "format": "mp3"}
    if voice_id:
        payload["reference_id"] = voice_id

    if args.dry_run:
        print(f"Valid request: {len(spoken_text)} characters, model={args.model}, voice={'set' if voice_id else 'default'}")
        return 0

    api_key = os.environ.get("FISH_API_KEY", "").strip()
    if not api_key:
        print("FISH_API_KEY is missing. Set it in the environment and retry.", file=sys.stderr)
        return 2

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
            "model": args.model,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            content_type = response.headers.get("Content-Type", "")
            audio = response.read()
    except urllib.error.HTTPError as exc:
        # Provider error bodies may contain request details. Do not echo them
        # into chat or logs, where they might expose private input or a token.
        advice = {
            401: "authentication failed; check FISH_API_KEY",
            402: "payment or quota limit; check account access for the selected model",
            503: "service temporarily unavailable; retry the same model later",
        }.get(exc.code, "request failed; check model and voice IDs or account status")
        print(f"Fish Audio HTTP {exc.code}: {advice}.", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Fish Audio connection error: {exc.reason}", file=sys.stderr)
        return 1

    is_mp3 = audio.startswith(b"ID3") or (
        len(audio) >= 2 and audio[0] == 0xFF and audio[1] & 0xE0 == 0xE0
    )
    if not is_mp3:
        print(f"Fish Audio returned no valid MP3 (Content-Type: {content_type})", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=".mp3", prefix="fish-tts-", dir=args.output.parent, delete=False
    ) as file:
        temporary = Path(file.name)
        file.write(audio)
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=codec_name:format=duration:packet=pts_time,duration_time",
             "-of", "json", str(temporary)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        metadata = json.loads(probe.stdout) if probe.returncode == 0 else {}
        duration = float(metadata.get("format", {}).get("duration", 0))
        streams = metadata.get("streams", [])
        packets = metadata.get("packets", [])
        if not streams or streams[0].get("codec_name") != "mp3" or not packets or not math.isfinite(duration) or duration <= 0:
            raise ValueError("audio is not a decodable MP3 with positive duration")
        last_packet = packets[-1]
        last_end = float(last_packet["pts_time"]) + float(last_packet["duration_time"])
        if not math.isfinite(last_end) or last_end < duration - min(0.25, max(0.1, duration * 0.02)):
            raise ValueError("MP3 ends before its declared duration")
        temporary.replace(args.output)
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError) as exc:
        print(f"Fish Audio MP3 validation failed: {exc}", file=sys.stderr)
        return 1
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Saved {args.output.resolve()} ({len(audio)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
