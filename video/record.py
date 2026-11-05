"""Record each scene of stage.html with Playwright (1280x720), mux narration (+ the real auction audio in s04),
add the music bed, write ../demo/bidledger-demo.mp4."""
import json, subprocess, wave
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
RAW, SEG = HERE / "raw", HERE / "seg"
FF = ["ffmpeg", "-y", "-loglevel", "error"]
SCENES = [k for k, _ in json.loads((HERE / "narration.json").read_text(encoding="utf-8"))]
DUR = {p.stem: wave.open(str(p)).getnframes() / 24000 for p in (HERE / "audio").glob("*.wav")}
PAD = {"s01_open": 1.8, "s03_intro": 2.0, "s04_record": 8.0, "s07_slip": 1.6, "s08_whatsapp": 1.6, "s10_close": 3.5}
AUCTION_AT = {"s04_record": 0.4}  # real auction audio starts here in that scene (s), under then after the narration
BED = Path(r"F:\Dev\Agent Os\projects\Ai Builder Cup 2026\production\video\fairfreeze-bed.wav")


def run(*a):
    subprocess.run([*FF, *a], check=True)


def record():
    for d in (RAW, SEG):
        d.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        for s in SCENES:
            dur = DUR[s] + PAD.get(s, 1.0)
            ctx = b.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=str(RAW / s),
                                record_video_size={"width": 1280, "height": 720})
            page = ctx.new_page()
            page.goto((HERE / "stage.html").as_uri() + f"?s={s}")
            page.wait_for_timeout(dur * 1000 + 700)
            vid = Path(page.video.path())
            ctx.close()
            run("-ss", "0.7", "-i", str(vid), "-t", f"{dur:.2f}", "-an", "-r", "30", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "-crf", "20", str(SEG / f"{s}.mp4"))
            print(s, f"{dur:.1f}s", flush=True)
        b.close()


def scene_dur(s):
    return DUR[s] + PAD.get(s, 1.0)


def join():
    """Video: concat of silent scenes. Audio: ONE continuous mix (no per-scene audio joins, so no clicks):
    every narration line faded in/out and placed at its absolute time, real market floor under the
    opening and the recording scene, music bed under everything."""
    lst = SEG / "list.txt"
    lst.write_text("".join("file '" + (SEG / f"{s}.mp4").as_posix() + "'\n" for s in SCENES))
    body = SEG / "_body.mp4"
    run("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(body))
    starts, t = {}, 0.0
    for s in SCENES:
        starts[s] = t; t += scene_dur(s)
    total = t
    inputs, chains, labels = [], [], []
    for i, s in enumerate(SCENES):
        inputs += ["-i", str(HERE / "audio_clean" / f"{s}.wav")]
        d = DUR[s]; ms = int((starts[s] + 0.3) * 1000)
        chains.append(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo,afade=t=in:d=0.04,"
                      f"afade=t=out:st={max(d - 0.15, 0):.2f}:d=0.15,adelay={ms}|{ms}[n{i}]")
        labels.append(f"[n{i}]")
    k = len(SCENES)
    floor = HERE.parent / "samples" / "auction_market.wav"
    # market floor ambience under s01-s02 (quiet), then the full recording in s04 (loud after the narration)
    inputs += ["-i", str(floor), "-i", str(floor)]
    a_end = starts["s03_intro"]
    chains.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{a_end:.2f},"
                  f"volume=0.16,afade=t=in:d=1.5,afade=t=out:st={a_end - 1.2:.2f}:d=1.2[amb]")
    r0, rd, nd = starts["s04_record"] + 0.4, scene_dur("s04_record") - 0.6, DUR["s04_record"] + 0.4
    chains.append(f"[{k + 1}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{rd:.2f},"
                  f"volume='if(lt(t,{nd:.2f}),0.22,0.95)':eval=frame,afade=t=in:d=0.4,afade=t=out:st={rd - 0.8:.2f}:d=0.8,"
                  f"adelay={int(r0 * 1000)}|{int(r0 * 1000)}[rec]")
    inputs += ["-stream_loop", "-1", "-i", str(BED)]
    chains.append(f"[{k + 2}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{total:.2f},volume=0.09,"
                  f"afade=t=in:d=2,afade=t=out:st={total - 3:.2f}:d=3[bed]")
    mix = ";".join(chains) + ";" + "".join(labels) + f"[amb][rec][bed]amix=inputs={k + 3}:duration=longest:normalize=0,"
    mix += f"atrim=0:{total:.2f},alimiter=limit=0.95[a]"
    audio = SEG / "_audio.wav"
    run(*inputs, "-filter_complex", mix, "-map", "[a]", "-c:a", "pcm_s16le", str(audio))
    out = HERE.parent / "demo" / "bidledger-demo.mp4"
    out.parent.mkdir(exist_ok=True)
    run("-i", str(body), "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(out))
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                             capture_output=True, text=True).stdout)
    print(out, f"{d:.0f}s")


if __name__ == "__main__":
    import sys
    if "--join" not in sys.argv:
        record()
    join()
