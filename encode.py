import argparse
import subprocess
import sys
import os

def encode_video(input_file, output_file, font_path, text, x, y, fontsize, fontcolor,
                bitrate, audio_bitrate, maxrate, bufsize, pix_fmt, sample_rate,
                resolution, soft_sub=None, burn_sub=None, lang='eng'):
    print(f"Processing: {input_file} -> {output_file}")

    # Build video filter chain: scaling + optional burn-in + text overlay
    filters = [f"scale={resolution}"]
    if burn_sub:
        filters.append(f"subtitles='{burn_sub}'")
    filters.append(
        f"drawtext=fontfile='{font_path}':text='{text}':x={x}:y={y}:fontsize={fontsize}:fontcolor={fontcolor}"
    )
    filter_complex = ",".join(filters)

    # Start building ffmpeg command
    ffmpeg_cmd = ["ffmpeg", "-threads", "0", "-i", input_file]

    # Soft subtitle input should be added as a separate stream
    if soft_sub:
        ffmpeg_cmd += ["-i", soft_sub]

    # Apply video filters
    ffmpeg_cmd += ["-vf", filter_complex]

    # Stream mapping: video and audio always
    ffmpeg_cmd += ["-map", "0:v", "-map", "0:a"]

    # If soft subtitles, map the subtitle stream
    if soft_sub:
        ffmpeg_cmd += ["-map", f"1:0"]

    # Video encoding settings
    ffmpeg_cmd += [
        "-c:v", "libx264",
        "-profile:v", "high",
        "-pix_fmt", pix_fmt,
        "-b:v", bitrate,
        "-maxrate", maxrate,
        "-bufsize", bufsize,
        "-preset", "medium",
    ]

    # Audio encoding settings
    ffmpeg_cmd += [
        "-c:a", "aac",
        "-b:a", audio_bitrate,
        "-ar", str(sample_rate),
        "-ac", "2",
    ]

    # Soft subtitle stream encoding and metadata
    if soft_sub:
        ffmpeg_cmd += [
            "-c:s", "mov_text",
            f"-metadata:s:s:0", f"language={lang}"
        ]

    # Global flags and output
    ffmpeg_cmd += [
        "-map_metadata", "-1",
        "-map_chapters", "-1",
        "-movflags", "+faststart",
        "-dn",
        output_file
    ]

    print("Running FFmpeg:\n" + " ".join(ffmpeg_cmd))
    process = subprocess.run(ffmpeg_cmd)
    if process.returncode != 0:
        print("Error: Encoding failed!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.realpath(__file__))
    font_path = os.path.join(script_dir, "NeometricAlt-HeavyItalic.ttf")

    parser = argparse.ArgumentParser(
        description="Encode video with optional soft or burn-in subtitles, watermark, and multi-resolution."
    )
    parser.add_argument("input", help="Input video file")
    parser.add_argument("output", help="Base output file name (without extension)")
    parser.add_argument("--x", type=int, default=20, help="X position for the text")
    parser.add_argument("--y", type=int, default=40, help="Y position for the text")
    parser.add_argument("--fontsize", type=int, default=30, help="Font size for the text")
    parser.add_argument("--fontcolor", default="white@0.5", help="Font color for the text")
    parser.add_argument("--pix_fmt", default="yuv420p", help="Pixel format, default is yuv420p")
    subs_group = parser.add_mutually_exclusive_group()
    subs_group.add_argument("--soft", help="Path to subtitle file for soft embedding (separate stream)")
    subs_group.add_argument("--burn", help="Path to subtitle file to burn into video (hard subtitles)")
    parser.add_argument("--lang", default="ar", help="Subtitle language code (ISO 639) for soft subtitles")
    parser.add_argument(
        "--watermark", default="HALASHOW.COM", help="Watermark text to overlay"
    )
    parser.add_argument(
        "--resolutions", choices=["all", "1080p", "720p", "480p", "360p"],
        default=["all"], nargs='+', help="Resolutions to encode"
    )

    args = parser.parse_args()

    resolutions = {
        "1080p": {"res": "1920x1080", "bitrate": "3000k", "maxrate": "3500k", "bufsize": "6000k", "audio": "125k", "sample_rate": 48000},
        "720p":  {"res": "1280x720",  "bitrate": "2000k", "maxrate": "2500k", "bufsize": "4000k", "audio": "110k", "sample_rate": 48000},
        "480p":  {"res": "854x480",   "bitrate": "1000k", "maxrate": "1500k", "bufsize": "2000k", "audio": "90k",  "sample_rate": 44100},
        "360p":  {"res": "640x360",   "bitrate": "700k",  "maxrate": "1200k", "bufsize": "1400k", "audio": "75k",  "sample_rate": 44100},
    }

    # Select resolutions
    selected = resolutions if "all" in args.resolutions else {r: resolutions[r] for r in args.resolutions if r in resolutions}

    # Process each resolution
    for name, opts in selected.items():
        out_file = f"{args.output}_{name}.mp4"
        encode_video(
            args.input, out_file, font_path, args.watermark,
            args.x, args.y, args.fontsize, args.fontcolor,
            opts["bitrate"], opts["audio"], opts["maxrate"], opts["bufsize"],
            args.pix_fmt, opts["sample_rate"], opts["res"],
            soft_sub=args.soft, burn_sub=args.burn, lang=args.lang
        )

    print("Encoding complete!")
