"""Render the ~2.5 minute demo video from the real pipeline output (out/ledger.json, out/report.html).

Slides are HTML rendered by headless Chrome, narration by edge-tts, joined by ffmpeg.
Writes demo/bidledger-demo.mp4.
"""
import asyncio, json, subprocess, tempfile
from pathlib import Path
import edge_tts

ROOT = Path(__file__).parent
OUT, DEMO = ROOT / "out", ROOT / "demo"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
VOICE = "en-IN-NeerjaNeural"
W, H = 1280, 720


def ff(*a):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a], check=True)


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True).stdout)


def shot(html_path: Path, png: Path, h=H):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={W},{h}",
                    f"--screenshot={png}", html_path.as_uri()], check=True, capture_output=True)


CSS = """<style>body{margin:0;width:1280px;height:720px;font-family:system-ui,Segoe UI;background:#0b1d33;color:#fff;
display:flex;flex-direction:column;justify-content:center;padding:0 90px;box-sizing:border-box}
h1{font-size:64px;margin:0 0 18px}h2{font-size:44px;margin:0 0 24px;color:#7cc4ff}p,li{font-size:30px;line-height:1.45}
.big{font-size:88px;font-weight:800;color:#5ee38a}.red{color:#ff7b72}.dim{color:#9fb3c8;font-size:24px}
.box{display:flex;gap:18px;align-items:center;font-size:26px}.box div{background:#15325a;padding:18px 22px;border-radius:12px}
.arrow{background:none!important;padding:0!important;font-size:34px}</style>"""


def slides(data):
    led, flags, acc, secs = data["ledger"], data["slip_flags"], data["accuracy"], data.get("seconds", 60)
    short = sum(f.get("farmer_shortfall_rs", 0) for f in flags)
    lots = len(led["lots"])
    return [
        (f"<h1>BidLedger</h1><h2>Every shouted bid, on the record.</h2><p class=dim>Meta Global AI Developer Hackathon · Build for Your World</p>",
         "BidLedger. Every shouted bid, on the record."),
        ("<h2>The problem</h2><ul><li>Fresh produce in South Asia is sold by open-cry auction: one auctioneer, many traders shouting.</li>"
         "<li>The only record is the commission agent's handwritten slip.</li><li>The farmer is paid from that slip, not from what was shouted.</li>"
         "<li class=red>If the slip is wrong, nobody can prove it.</li></ul>",
         "In wholesale markets across India and Sri Lanka, farmers' produce is sold by open-cry auction. An auctioneer calls the lot, and traders shout bids, "
         "often in different languages. The only record is the commission agent's handwritten slip, and the farmer is paid from that slip. "
         "If the price on the slip is lower than what was shouted, the farmer has no way to prove it."),
        ("<h2>Listen: a real-time floor auction</h2><p>Auctioneer plus three traders bidding in English, Hindi and Tamil, over market noise.</p>"
         "<p class=dim>Test recording made with synthetic voices for this demo.</p>",
         "Here is the kind of recording BidLedger works on. One auctioneer and three traders, bidding in English, Hindi and Tamil, over market noise. "
         "For this demo the voices are synthetic, so we know the true result of every lot."),
        ("AUDIO", None),
        ("<h2>How it works</h2><div class=box><div>Phone records<br>the floor</div><div class=arrow>→</div><div><b>Muse Voice Transcribe</b><br>diarization: who said what</div>"
         "<div class=arrow>→</div><div><b>Muse Spark</b><br>lots, bids, winners,<br>Hindi + Tamil numbers</div><div class=arrow>→</div>"
         "<div>Proof clip +<br>WhatsApp receipt</div></div>",
         "BidLedger needs one phone on the auction floor. Muse Voice Transcribe, in diarization mode, separates the speakers and gives every turn a timestamp. "
         "Muse Spark acts as the auction clerk. It works out which voice is the auctioneer, which trader is behind each voice, and reads bids spoken as Hindi or Tamil numbers. "
         "For every lot it records the winner, the price, and the exact moment the hammer fell. Then BidLedger cuts that moment out as an audio proof clip."),
        ("REPORT_TOP", f"Here is the real output for this recording. {acc['lots_correct']} of {acc['lots_total']} lots have the right buyer and price, and each lot has its proof clip attached."),
        ("REPORT_FLAG", f"Then BidLedger checks the commission agent's slip against the floor. On lot one, the slip says one hundred and twenty five rupees a kilo, "
         f"but the auction was won at one hundred and forty. That is a shortfall of {short:,} rupees to the farmer, caught automatically, with the clip to prove it."),
        ("<h2>Receipts on WhatsApp</h2><div class=box><div style='background:#e7ffdb;color:#111;max-width:520px'>✅ <b>BidLedger sale receipt</b><br>Lot 1 · carrots · 600 kg<br>"
         "Buyer: Murugan · Rs 140/kg<br>Total <b>Rs 84,000</b><br>🔊 proof clip attached</div></div><p class=dim>WhatsApp Cloud API utility templates: one to the buyer, one to the farmer, per lot.</p>",
         "Each sale becomes two WhatsApp utility messages, one to the buyer and one to the farmer, with the audio proof attached. The farmer no longer has to trust a slip."),
        (f"<h2>Before → after</h2><p>Ledger for a {lots}-lot auction: <span class=big>{secs:.0f} s</span></p>"
         f"<p>Farmer underpayment caught: <b class=red>Rs {short:,}</b> on one lot</p><p>Accuracy on this test: <b>{acc['lots_correct']}/{acc['lots_total']} lots</b></p>",
         f"Before, the record was one person's handwriting. After, the full ledger for this auction took about {secs:.0f} seconds, and the underpayment was caught with evidence. "
         "Every lot carries two WhatsApp messages, so every market that uses BidLedger is also new business messaging for Meta."),
        ("<h2>Built during the hackathon</h2><ul><li>Synthetic multilingual auction generator with ground truth</li><li>Diarized transcription + Spark clerk + slip checker</li>"
         "<li>Audio proof clips, WhatsApp payloads, report</li></ul><p class=dim>Next: live floor test, SAM 3.1 hand-raise tracking, Sinhala.</p>",
         "Everything shown was built during the hackathon: the test auction generator, the pipeline and the report. Next steps are a live market test, "
         "SAM 3.1 to track raised hands for silent bids, and more languages. BidLedger. Every shouted bid, on the record."),
    ]


async def main():
    data = json.loads((OUT / "ledger.json").read_text(encoding="utf-8"))
    data["seconds"] = data.get("seconds") or json.loads((OUT / "timing.json").read_text())["seconds"]
    DEMO.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    # Report screenshots: top (ledger) and flag section.
    shot(OUT / "report.html", tmp / "report_full.png", h=1500)
    ff("-i", str(tmp / "report_full.png"), "-vf", f"crop={W}:{H}:0:0", str(tmp / "REPORT_TOP.png"))
    ff("-i", str(tmp / "report_full.png"), "-vf", f"crop={W}:{H}:0:420", str(tmp / "REPORT_FLAG.png"))
    segs = []
    for i, (content, narration) in enumerate(slides(data)):
        seg = tmp / f"seg{i:02d}.mp4"
        if content == "AUDIO":
            ff("-t", "18", "-i", str(ROOT / "samples" / "auction.wav"), "-filter_complex",
               f"[0:a]showwaves=s={W}x{H}:mode=cline:colors=0x5ee38a,format=yuv420p[v]", "-map", "[v]", "-map", "0:a",
               "-c:v", "libx264", "-c:a", "aac", "-ar", "48000", "-ac", "2", str(seg))
            segs.append(seg)
            continue
        png = tmp / f"{content}.png" if content.startswith("REPORT") else tmp / f"s{i:02d}.png"
        if not content.startswith("REPORT"):
            page = tmp / f"s{i:02d}.html"
            page.write_text("<!doctype html><meta charset=utf-8>" + CSS + "<body>" + content, encoding="utf-8")
            shot(page, png)
        mp3 = tmp / f"n{i:02d}.mp3"
        await edge_tts.Communicate(narration, VOICE, rate="+14%").save(str(mp3))
        d = dur(mp3) + 0.6
        ff("-loop", "1", "-i", str(png), "-i", str(mp3), "-t", f"{d:.2f}", "-vf", "format=yuv420p",
           "-c:v", "libx264", "-c:a", "aac", "-ar", "48000", "-ac", "2", "-af", "apad", str(seg))
        segs.append(seg)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{s.as_posix()}'\n" for s in segs))
    final = DEMO / "bidledger-demo.mp4"
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(final))
    print(final, f"{dur(final):.0f}s")


if __name__ == "__main__":
    asyncio.run(main())
