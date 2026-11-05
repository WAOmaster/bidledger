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
            # trim the blank load (first ~0.7 s), mux narration (delayed 0.3 s)
            parts = ["-ss", "0.7", "-i", str(vid), "-i", str(HERE / "audio" / f"{s}.wav")]
            mix = "[1:a]adelay=300|300,apad[n]"
            if s in AUCTION_AT:
                parts += ["-i", str(HERE.parent / "samples" / "auction.wav")]
                ms = int(AUCTION_AT[s] * 1000)
                mix = (f"[1:a]adelay=300|300,apad[n0];[2:a]atrim=0:{dur:.1f},adelay={ms}|{ms},"
                       f"volume='if(lt(t,{DUR[s] + 0.6:.1f}),0.25,1.0)':eval=frame,apad[au];[n0][au]amix=inputs=2:duration=first:normalize=0[n]")
            run(*parts, "-filter_complex", mix + ";[n]aformat=sample_rates=48000:channel_layouts=stereo[a]",
                "-map", "0:v", "-map", "[a]", "-t", f"{dur:.2f}", "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-crf", "20", "-c:a", "aac", "-b:a", "160k", str(SEG / f"{s}.mp4"))
            print(s, f"{dur:.1f}s", flush=True)
        b.close()


def join():
    lst = SEG / "list.txt"
    lst.write_text("".join(f"file '{(SEG / f'{s}.mp4').as_posix()}'\n" for s in SCENES))
    body = SEG / "_body.mp4"
    run("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(body))
    out = HERE.parent / "demo" / "bidledger-demo.mp4"
    out.parent.mkdir(exist_ok=True)
    run("-i", str(body), "-stream_loop", "-1", "-i", str(BED), "-filter_complex",
        "[1:a]volume=0.10,aformat=sample_rates=48000:channel_layouts=stereo[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out))
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                             capture_output=True, text=True).stdout)
    print(out, f"{d:.0f}s")


if __name__ == "__main__":
    record()
    join()
