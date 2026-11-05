"""Market background stills with Muse Image (muse-image-1.0)."""
import base64, json, sys, keyring, requests
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
KEY = keyring.get_password("dev.meta.ai", "metaai")
OUT = Path(__file__).parent / "img"
SHOTS = {
 "m1_dawn": "Documentary photograph, wide shot of a busy South Asian wholesale vegetable market at dawn, trucks unloading sacks of carrots, leeks and cabbages, workers carrying crates, warm early light, haze, realistic, 16:9",
 "m2_auction": "Documentary photograph of an open-cry produce auction in an Indian mandi: an auctioneer standing on crates calling a lot of carrots, a crowd of traders raising hands and shouting bids, motion and noise, realistic, 16:9",
 "m3_slip": "Close-up documentary photograph of a commission agent's hand writing prices on a small paper slip with a ballpoint pen at a vegetable market stall, carbon copy book, rupee notes nearby, shallow depth of field, realistic",
 "m4_farmer": "Documentary portrait of a tired Sri Lankan vegetable farmer in his fifties standing beside sacks of carrots at a wholesale market, looking at a paper slip with worry, natural light, realistic, 16:9",
 "m5_phone": "Documentary photograph of a smartphone held up on a stand recording audio at a crowded vegetable auction floor, traders blurred in background, realistic, 16:9",
 "m6_whatsapp": "Documentary photograph of a smiling farmer checking a message on his phone next to his empty truck at a market at sunrise, realistic, 16:9",
}
def gen(item):
    name, prompt = item
    for _ in range(2):
        r = requests.post("https://api.meta.ai/v1/images/generations", headers={"Authorization": f"Bearer {KEY}"},
                          json={"model": "muse-image-1.0", "prompt": prompt, "n": 1, "size": "1536x1024"}, timeout=600)
        if r.status_code == 200:
            d = r.json()["data"][0]
            data = base64.b64decode(d["b64_json"]) if d.get("b64_json") else requests.get(d["url"], timeout=120).content
            (OUT / f"{name}.png").write_bytes(data); return f"{name} ok"
        err = r.text[:200]
        if "size" in err.lower(): prompt_only = True
    return f"{name} FAIL {r.status_code} {err}"
with ThreadPoolExecutor(6) as ex:
    for line in ex.map(gen, SHOTS.items()): print(line, flush=True)
