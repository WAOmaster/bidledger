"""BidLedger: turn a shouted open-cry auction recording into a verified sales ledger.

  1. Muse Voice Transcribe (DIARIZATION) -> who said what, when.
  2. Muse Spark -> lots, bids, winners and prices (understands English, Hindi
     and Tamil numbers), each tied to the turn where the hammer fell.
  3. ffmpeg cuts the audio proof clip of each winning call.
  4. The commission agent's written slip is checked against the audio.
  5. WhatsApp receipts (Cloud API template payloads) for buyer and farmer.
  6. out/report.html shows it all.

Usage: python bidledger.py samples/auction.wav [--slip samples/agent_slip.json] [--truth samples/ground_truth.json]
"""
import argparse, html, json, os, re, subprocess, sys, time
from pathlib import Path
import requests

API = "https://api.meta.ai/v1"
OUT = Path(__file__).parent / "out"


def api_key():
    k = os.environ.get("MODEL_API_KEY")
    if not k:
        import keyring
        k = keyring.get_password("dev.meta.ai", "metaai")
    if not k:
        sys.exit("Set MODEL_API_KEY (or save it in Windows Credentials as dev.meta.ai / metaai).")
    return k


def transcribe(wav: Path, key: str) -> dict:
    req = {"model": "muse-voice-transcribe-1.0", "audioEncoding": "WAV", "mode": "DIARIZATION",
           "languageBias": ["English", "Hindi", "Tamil"],
           "keywords": ["lot", "sold", "per kilo", "going once", "going twice",
                        "Lakshmi", "Ravi", "Murugan", "carrots", "leeks", "beans", "cabbage"]}
    with open(wav, "rb") as f:
        r = requests.post(f"{API}/asr/transcribe", headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
                          files={"request": (None, json.dumps(req), "application/json"),
                                 "audio": (wav.name, f, "audio/wav")}, timeout=300)
    if r.status_code != 200:
        sys.exit(f"Transcribe failed {r.status_code}: {r.text[:300]}")
    return r.json()


PROMPT = """You are the clerk of an open-cry produce auction. Below is a diarized transcript
(speaker labels are anonymous: A, B, C...). Bids may be spoken in English, Hindi or Tamil; convert
every number to an integer in rupees per kilo.

Work out:
- which label is the auctioneer, and the trader name behind each other label (the auctioneer names
  the winner when the lot is sold);
- for every lot: lot number, item, quantity in kg, every bid in order (speaker label, price),
  the winner's name and label, the final price per kilo, and the turnId where the sale was declared;
- any problem: a sale price that does not match the highest bid, a winner who never bid, a
  bid you could not read. Put these in "issues".

Reply with JSON only, no prose:
{"speakers": {"A": "auctioneer", "B": "<name>"}, "lots": [{"lot": 1, "item": "", "qty_kg": 0,
"bids": [{"speaker": "B", "price_per_kg": 0, "turnId": 0}], "winner": "", "winner_label": "",
"price_per_kg": 0, "sold_turnId": 0}], "issues": []}

Transcript:
"""


def extract_ledger(transcript: dict, key: str) -> dict:
    lines = "\n".join(f'[turn {t["turnId"]} {t["startMs"]/1000:.1f}s] {t.get("speaker", "?")}: {t["transcript"]}'
                      for t in transcript["turns"])
    body = {"model": "muse-spark-1.3", "messages": [{"role": "user", "content": PROMPT + lines}], "temperature": 0}
    for attempt in range(3):
        r = requests.post(f"{API}/chat/completions", headers={"Authorization": f"Bearer {key}"}, json=body, timeout=300)
        if r.status_code == 200:
            text = r.json()["choices"][0]["message"]["content"]
            m = re.search(r"\{.*\}", text, re.S)
            try:
                return json.loads(m.group(0))
            except (AttributeError, json.JSONDecodeError):
                body["messages"].append({"role": "assistant", "content": text})
                body["messages"].append({"role": "user", "content": "That was not valid JSON. Reply with the JSON object only."})
                continue
        if r.status_code in (429, 500, 503):
            time.sleep(2 ** attempt * 3)
            continue
        sys.exit(f"Spark failed {r.status_code}: {r.text[:300]}")
    sys.exit("Spark did not return a usable ledger after 3 tries.")


def cut_clips(wav: Path, transcript: dict, ledger: dict):
    """Proof clip per lot: from the last bid to the end of the 'sold' call."""
    turns = {t["turnId"]: t for t in transcript["turns"]}
    (OUT / "clips").mkdir(parents=True, exist_ok=True)
    for lot in ledger["lots"]:
        sold = turns.get(lot.get("sold_turnId"))
        if not sold:
            lot["clip"] = None
            continue
        bid_turns = [turns[b["turnId"]] for b in lot.get("bids", []) if b.get("turnId") in turns]
        start = (bid_turns[-1]["startMs"] if bid_turns else sold["startMs"]) / 1000 - 0.3
        end = sold["endMs"] / 1000 + 0.3
        clip = OUT / "clips" / f"lot{lot['lot']}.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{max(start, 0):.2f}", "-to", f"{end:.2f}",
                        "-i", str(wav), str(clip)], check=True)
        lot["clip"] = f"clips/{clip.name}"
        lot["clip_span"] = [round(max(start, 0), 1), round(end, 1)]


def check_slip(ledger: dict, slip: list) -> list:
    flags = []
    by_lot = {l["lot"]: l for l in ledger["lots"]}
    for s in slip:
        l = by_lot.get(s["lot"])
        if not l:
            flags.append({"lot": s["lot"], "problem": "Lot on the slip was never auctioned on the recording"})
            continue
        if s["price_per_kg"] != l["price_per_kg"]:
            loss = (l["price_per_kg"] - s["price_per_kg"]) * l.get("qty_kg", 0)
            flags.append({"lot": s["lot"], "problem": f"Slip says Rs {s['price_per_kg']}/kg, the floor said Rs {l['price_per_kg']}/kg",
                          "farmer_shortfall_rs": loss})
        if s["buyer"].lower() != str(l["winner"]).lower():
            flags.append({"lot": s["lot"], "problem": f"Slip buyer {s['buyer']} but {l['winner']} won on the floor"})
    return flags


def receipts(ledger: dict) -> list:
    """WhatsApp Cloud API utility-template payloads (one to the buyer, one to the farmer, per lot)."""
    out = []
    for l in ledger["lots"]:
        total = l["price_per_kg"] * l.get("qty_kg", 0)
        params = [str(l["lot"]), l["item"], str(l.get("qty_kg", "")), str(l["price_per_kg"]), f"{total:,}"]
        for role, to in (("buyer", f"<{l['winner']} phone>"), ("farmer", "<farmer phone>")):
            out.append({"messaging_product": "whatsapp", "to": to, "type": "template",
                        "template": {"name": f"bidledger_sale_{role}", "language": {"code": "en"},
                                     "components": [{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}]},
                        "_attach_audio_proof": l.get("clip")})
    return out


def score(ledger: dict, truth: list) -> dict:
    by_lot = {l["lot"]: l for l in ledger["lots"]}
    ok = sum(1 for t in truth if (l := by_lot.get(t["lot"])) and l["price_per_kg"] == t["price_per_kg"]
             and str(l["winner"]).lower() == t["winner"].lower())
    return {"lots_correct": ok, "lots_total": len(truth)}


def report(transcript, ledger, flags, acc, secs):
    e = html.escape
    rows = "".join(
        f"<tr><td>{l['lot']}</td><td>{e(l['item'])}</td><td>{l.get('qty_kg','')}</td><td>{e(str(l['winner']))}</td>"
        f"<td>Rs {l['price_per_kg']}</td><td>Rs {l['price_per_kg']*l.get('qty_kg',0):,}</td>"
        f"<td>{'<audio controls src=%s></audio>' % l['clip'] if l.get('clip') else '-'}</td></tr>" for l in ledger["lots"])
    turns = "".join(f"<li><b>{e(t.get('speaker','?'))} ({e(ledger['speakers'].get(t.get('speaker',''),'?'))})</b> "
                    f"<span>{t['startMs']/1000:.1f}s</span> {e(t['transcript'])}</li>" for t in transcript["turns"])
    fl = "".join(f"<li>Lot {f['lot']}: {e(f['problem'])}" + (f" — farmer short <b>Rs {f['farmer_shortfall_rs']:,}</b>" if f.get('farmer_shortfall_rs') else "") + "</li>" for f in flags) or "<li>Slip matches the floor.</li>"
    issues = "".join(f"<li>{e(str(i))}</li>" for i in ledger.get("issues", [])) or "<li>None</li>"
    acc_txt = f"{acc['lots_correct']}/{acc['lots_total']} lots match ground truth" if acc else ""
    page = f"""<!doctype html><meta charset=utf-8><title>BidLedger</title>
<style>body{{font:16px system-ui;margin:24px;max-width:1000px;background:#fafafa;color:#111}}h1{{margin:0}}
table{{border-collapse:collapse;width:100%;background:#fff}}td,th{{border:1px solid #ddd;padding:6px 8px;text-align:left}}
.flag{{background:#fff1f0;border-left:5px solid #d93025;padding:8px 16px}}.ok{{color:#137333}}li span{{color:#888}}
ul.t{{max-height:320px;overflow:auto;background:#fff;border:1px solid #ddd;padding:8px 28px}}</style>
<h1>BidLedger</h1><p>Open-cry auction to verified ledger in {secs:.0f} s · Muse Voice Transcribe + Muse Spark · <span class=ok>{acc_txt}</span></p>
<h2>Sales ledger (audio proof per lot)</h2><table><tr><th>Lot</th><th>Item</th><th>kg</th><th>Buyer</th><th>Price/kg</th><th>Total</th><th>Proof</th></tr>{rows}</table>
<h2>Agent slip check</h2><div class=flag><ul>{fl}</ul></div>
<h2>Clerk notes from Muse Spark</h2><ul>{issues}</ul>
<h2>Diarized transcript</h2><ul class=t>{turns}</ul>"""
    (OUT / "report.html").write_text(page, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav", type=Path)
    ap.add_argument("--slip", type=Path)
    ap.add_argument("--truth", type=Path)
    ap.add_argument("--reuse", action="store_true", help="reuse out/transcript.json instead of calling Muse Voice again")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    key = api_key()
    t0 = time.time()
    tpath = OUT / "transcript.json"
    transcript = json.loads(tpath.read_text(encoding="utf-8")) if a.reuse and tpath.exists() else transcribe(a.wav, key)
    tpath.write_text(json.dumps(transcript, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"transcribed: {len(transcript['turns'])} turns, {len({t.get('speaker') for t in transcript['turns']})} speakers")
    ledger = extract_ledger(transcript, key)
    cut_clips(a.wav, transcript, ledger)
    flags = check_slip(ledger, json.loads(a.slip.read_text())) if a.slip else []
    acc = score(ledger, json.loads(a.truth.read_text())) if a.truth else None
    secs = time.time() - t0
    (OUT / "ledger.json").write_text(json.dumps({"ledger": ledger, "slip_flags": flags, "accuracy": acc, "seconds": round(secs, 1)}, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "whatsapp_receipts.json").write_text(json.dumps(receipts(ledger), indent=2, ensure_ascii=False), encoding="utf-8")
    report(transcript, ledger, flags, acc, secs)
    print(json.dumps({"accuracy": acc, "slip_flags": flags, "seconds": round(secs)}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
