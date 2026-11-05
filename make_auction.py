"""Build a synthetic open-cry vegetable auction recording for testing BidLedger.

Four voices (auctioneer + 3 traders) speak a scripted floor auction in English,
Hindi and Tamil, over market noise. Writes samples/auction.wav (24 kHz mono
16-bit, the format Muse Voice Transcribe accepts) and samples/ground_truth.json.
"""
import asyncio, json, subprocess, tempfile
from pathlib import Path
import edge_tts

OUT = Path(__file__).parent / "samples"
VOICES = {
    "auctioneer": ("en-IN-PrabhatNeural", "+12%"),
    "Lakshmi":    ("en-IN-NeerjaNeural", "+5%"),
    "Ravi":       ("hi-IN-MadhurNeural", "+5%"),
    "Murugan":    ("ta-IN-ValluvarNeural", "+5%"),
}
# (speaker, line). Prices are rupees per kilo.
SCRIPT = [
    ("auctioneer", "Lot one. Carrots from Nuwara Eliya, six hundred kilos, grade A. Opening at one twenty per kilo."),
    ("Lakshmi", "One twenty five."),
    ("Ravi", "एक सौ तीस।"),                       # 130 in Hindi
    ("Lakshmi", "One thirty five."),
    ("Murugan", "நூற்று நாற்பது."),                # 140 in Tamil
    ("auctioneer", "One forty from Murugan. Going once, going twice. Sold, carrots, to Murugan at one forty."),
    ("auctioneer", "Lot two. Leeks, four hundred kilos. Opening at ninety."),
    ("Ravi", "Ninety five."),
    ("Lakshmi", "One hundred."),
    ("Ravi", "एक सौ पाँच।"),                      # 105
    ("auctioneer", "One oh five, Ravi. Any more? Sold, leeks, to Ravi at one hundred and five."),
    ("auctioneer", "Lot three. Beans, two hundred and fifty kilos, bit soft. Opening at two hundred."),
    ("Murugan", "Two ten."),
    ("Lakshmi", "Two twenty."),
    ("Murugan", "இருநூற்று முப்பது."),             # 230
    ("Lakshmi", "Two forty."),
    ("auctioneer", "Two forty to Lakshmi. Sold, beans, to Lakshmi at two hundred and forty."),
    ("auctioneer", "Lot four. Cabbage, one thousand kilos. Opening at fifty."),
    ("Ravi", "पचपन।"),                            # 55
    ("Murugan", "Sixty."),
    ("auctioneer", "Sixty to Murugan. Sold, cabbage, to Murugan at sixty rupees."),
]
TRUTH = [
    {"lot": 1, "item": "carrots", "qty_kg": 600, "winner": "Murugan", "price_per_kg": 140},
    {"lot": 2, "item": "leeks", "qty_kg": 400, "winner": "Ravi", "price_per_kg": 105},
    {"lot": 3, "item": "beans", "qty_kg": 250, "winner": "Lakshmi", "price_per_kg": 240},
    {"lot": 4, "item": "cabbage", "qty_kg": 1000, "winner": "Murugan", "price_per_kg": 60},
]

def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)

async def main():
    OUT.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    parts = []
    for i, (who, text) in enumerate(SCRIPT):
        voice, rate = VOICES[who]
        mp3 = tmp / f"{i:02d}.mp3"
        await edge_tts.Communicate(text, voice, rate=rate).save(str(mp3))
        wav = tmp / f"{i:02d}.wav"
        # short gap after each line; traders sometimes jump in quickly
        gap = 0.35 if who != "auctioneer" else 0.6
        ff("-i", str(mp3), "-af", f"apad=pad_dur={gap}", "-ac", "1", "-ar", "24000", str(wav))
        parts.append(wav)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts))
    voice_only = tmp / "voices.wav"
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(voice_only))
    # market crowd: brown noise at low level under the voices
    ff("-i", str(voice_only), "-f", "lavfi", "-i", "anoisesrc=color=brown:amplitude=0.04:sample_rate=24000",
       "-filter_complex", "[0][1]amix=inputs=2:duration=first:weights=1 0.6",
       "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", "-map_metadata", "-1", str(OUT / "auction.wav"))
    (OUT / "ground_truth.json").write_text(json.dumps(TRUTH, indent=2))
    # The commission agent's handwritten slip, typed up: lot 1 recorded lower than the floor price.
    (OUT / "agent_slip.json").write_text(json.dumps([
        {"lot": 1, "item": "carrots", "buyer": "Murugan", "price_per_kg": 125},
        {"lot": 2, "item": "leeks", "buyer": "Ravi", "price_per_kg": 105},
        {"lot": 3, "item": "beans", "buyer": "Lakshmi", "price_per_kg": 240},
        {"lot": 4, "item": "cabbage", "buyer": "Murugan", "price_per_kg": 60},
    ], indent=2))
    print("wrote", OUT / "auction.wav")

if __name__ == "__main__":
    asyncio.run(main())
