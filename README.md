# BidLedger — every shouted bid, on the record

Fresh produce across South Asia is sold by **open-cry auction**: an auctioneer calls a lot and traders shout bids, often in different languages. The only record is the commission agent's handwritten slip, and the farmer is paid from that slip. If the slip is lower than what was shouted, the farmer cannot prove it.

BidLedger turns one phone recording of the auction floor into a **verified sales ledger with audio proof**:

1. **Muse Voice Transcribe** (`DIARIZATION` mode, English/Hindi/Tamil bias, auction keywords) separates the speakers and timestamps every turn.
2. **Muse Spark 1.3** acts as the auction clerk: identifies the auctioneer, maps each voice to a trader, reads bids spoken as Hindi or Tamil numbers, and returns every lot's bids, winner, price and the turn where the sale was declared.
3. **ffmpeg** cuts the proof clip of each winning call.
4. The commission agent's slip is checked against the floor; any shortfall to the farmer is flagged with the rupee amount.
5. Each sale becomes two **WhatsApp Cloud API** utility-template messages (buyer and farmer) carrying the proof clip.
6. `out/report.html` shows the ledger, flags, clips and diarized transcript.

## Run

```bash
pip install -r requirements.txt
python make_auction.py                      # synthetic test auction + ground truth
set MODEL_API_KEY=...                       # or Windows Credentials: dev.meta.ai / metaai
python bidledger.py samples/auction.wav --slip samples/agent_slip.json --truth samples/ground_truth.json
python make_video.py                        # demo video from the real output
```

## What was built during the hackathon

All of it, between 26 Oct and 5 Nov 2026: the multilingual test-auction generator with ground truth, the transcription + Spark clerk pipeline, slip checker, proof clips, WhatsApp payloads, report and demo video.

## Honest limits

- The test auction uses **synthetic voices** (edge-tts, four distinct voices) so every lot has a known true result. A live market floor is the next test.
- WhatsApp messages are produced as Cloud API payloads; sending needs a verified business number.
- Sinhala is not among Muse Voice's 25 languages yet.

## Next

Live floor test at a wholesale market · SAM 3.1 tracking raised hands for silent bids · realtime mode on the floor (`wss://api.meta.ai/v1/asr/realtime`) so receipts go out as the hammer falls.
