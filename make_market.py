"""Harder, more realistic test auctions: the same script as make_auction.py, on a real-sounding market floor.

Adds what a phone on a real floor hears: a crowd of other people talking (multilingual babble), crates
and sacks banging, room echo, and traders cutting in before the auctioneer finishes.
Writes samples/auction_market.wav (busy) and samples/auction_loud.wav (very busy, overlapping bids).
"""
import asyncio, random, subprocess, tempfile
from pathlib import Path
import numpy as np
import edge_tts
from make_auction import SCRIPT, VOICES

SR = 24000
OUT = Path(__file__).parent / "samples"
CHATTER = [  # background talk around the floor, not part of the auction
    ("en-IN-NeerjaNeural", "Move that crate, move it, the truck is waiting."),
    ("hi-IN-SwaraNeural", "भैया, आज टमाटर का रेट क्या है?"),
    ("ta-IN-PallaviNeural", "இன்னைக்கு வெங்காயம் விலை ரொம்ப அதிகம்."),
    ("en-IN-PrabhatNeural", "Ten sacks to the left side, ten sacks."),
    ("hi-IN-MadhurNeural", "अरे जल्दी करो, गाड़ी निकालनी है।"),
    ("ta-IN-ValluvarNeural", "அண்ணா, அந்த மூட்டையை இங்கே கொண்டு வாங்க."),
    ("bn-IN-TanishaaNeural", "আজ বাজারে খুব ভিড়।"),
    ("te-IN-MohanNeural", "ఈ రోజు క్యాబేజీ బాగా వచ్చింది."),
    ("en-IN-NeerjaNeural", "Tea, tea, hot tea!"),
    ("hi-IN-MadhurNeural", "पैसे बाद में दूँगा, लिख लो।"),
    ("mr-IN-ManoharNeural", "गाडी इकडे लावा."),
    ("ta-IN-PallaviNeural", "சீக்கிரம் வாங்க, ஏலம் ஆரம்பிச்சாச்சு."),
]


def load(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def echo(x, delays=(0.045, 0.11, 0.19), gains=(0.35, 0.2, 0.1)):
    y = x.copy()
    for d, g in zip(delays, gains):
        n = int(d * SR)
        y[n:] += g * x[:-n]
    return y


def lowpass(x, a=0.15):  # cheap one-pole: far-away voices lose their highs
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc); y[i] = acc
    return y


async def tts(text, voice, rate, path, volume="+0%", pitch="+0Hz"):
    await edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch).save(str(path))
    return load(path)


async def build(name, overlap, babble_gain, thumps_per_min, seed):
    rng = random.Random(seed)
    tmp = Path(tempfile.mkdtemp())
    lines = []
    for i, (who, text) in enumerate(SCRIPT):
        voice, rate = VOICES[who]
        # shouted: faster, louder, a little higher
        lines.append((who, await tts(text, voice, "+18%" if who == "auctioneer" else "+12%", tmp / f"l{i}.mp3", "+20%", "+6Hz")))
    t, placed = 0.4, []
    for who, a in lines:
        if who != "auctioneer" and placed:
            t -= rng.uniform(0, overlap)  # trader cuts in before the previous line ends
        placed.append((max(t, 0), a)); t = max(t, 0) + len(a) / SR + rng.uniform(0.05, 0.3)
    total = int((t + 1.0) * SR)
    voices = np.zeros(total, np.float32)
    for st, a in placed:
        s = int(st * SR); voices[s:s + len(a)] += a[:total - s]
    voices = echo(voices)
    crowd = np.zeros(total, np.float32)
    chat = [await tts(txt, v, "+10%", tmp / f"c{i}.mp3") for i, (v, txt) in enumerate(CHATTER)]
    for _ in range(int(total / SR * 1.6)):  # roughly 1.6 background phrases per second, overlapping
        a = lowpass(rng.choice(chat)) * rng.uniform(0.4, 1.0)
        s = rng.randrange(0, max(1, total - len(a)))
        crowd[s:s + len(a)] += a
    crowd = echo(crowd, (0.07, 0.16, 0.3), (0.4, 0.25, 0.15))
    noise = np.random.default_rng(seed).normal(0, 0.012, total).astype(np.float32)  # fans, engines, hiss
    for _ in range(int(total / SR / 60 * thumps_per_min)):  # crates and sacks dropped
        s = rng.randrange(0, total - 3000)
        env = np.exp(-np.linspace(0, 9, 2600)).astype(np.float32)
        noise[s:s + 2600] += lowpass(np.random.default_rng(s).normal(0, 1, 2600).astype(np.float32), 0.08) * env * rng.uniform(1.5, 3.5)
    mix = voices + babble_gain * crowd / (np.abs(crowd).max() + 1e-6) * np.abs(voices).max() + noise
    mix = mix / np.abs(mix).max() * 0.9
    out = OUT / f"auction_{name}.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-c:a", "pcm_s16le", str(out)], input=mix.astype(np.float32).tobytes(), check=True)
    snr = 10 * np.log10((voices ** 2).mean() / ((babble_gain * crowd / (np.abs(crowd).max() + 1e-6) * np.abs(voices).max() + noise) ** 2).mean())
    print(out.name, f"{total / SR:.0f}s", f"speech-to-noise {snr:.1f} dB")


async def main():
    await build("market", overlap=0.25, babble_gain=0.45, thumps_per_min=10, seed=7)
    await build("loud", overlap=0.6, babble_gain=0.8, thumps_per_min=20, seed=11)


if __name__ == "__main__":
    asyncio.run(main())
