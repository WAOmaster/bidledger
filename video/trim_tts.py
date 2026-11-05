"""Cut the loud burst Gemini TTS appends after the last word; write audio_clean/<name>.wav with a short fade."""
import sys, wave, glob, numpy as np
from pathlib import Path
names = sys.argv[1:] or [Path(f).stem for f in glob.glob("audio/*.wav")]
for name in names:
    w = wave.open(f"audio/{name}.wav"); sr = w.getframerate()
    xf = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    win = sr // 50; n = len(xf) // win; q = np.sqrt((xf[:n * win].reshape(n, win) ** 2).mean(1)) <= 0.02
    cut, run = len(xf), 0
    for i in range(n - 1, -1, -1):  # latest run of >= 160 ms silence = gap before the burst
        run = run + 1 if q[i] else 0
        if run >= 8:
            j = i
            while j > 0 and q[j - 1]: j -= 1
            cut = (j + 6) * win; break
    y = xf[:cut].copy(); fo = int(0.06 * sr); y[-fo:] *= np.linspace(1, 0, fo)
    o = wave.open(f"audio_clean/{name}.wav", "wb"); o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr)
    o.writeframes((y * 32767).astype(np.int16).tobytes()); o.close(); print(name, f"{cut / sr:.2f}s")
