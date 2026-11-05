# Noise test (live Meta Model API, 5 Nov 2026)

Same 4-lot auction script, harder floors. `--clean` = ffmpeg band-pass + spectral denoise + level normaliser before Muse Voice.

| Floor | File | Speech-to-noise | Raw: lots right | Raw: time | With --clean: lots right | With --clean: time |
|---|---|---|---|---|---|---|
| Clean (brown noise) | auction.wav | ~20 dB | 4/4 | 215 s | - | - |
| Busy market: crowd babble in 6 languages, crates, echo, bids cutting in | auction_market.wav | 7.1 dB | 4/4 | 154 s | 4/4 | 200 s |
| Very loud: heavier crowd, more overlap | auction_loud.wav | 3.2 dB | 4/4 | 140 s | 4/4 | 104 s |
| Extreme: crowd louder than the bidders | auction_extreme.wav | -1.5 dB | 4/4 | 140 s | 4/4 | 125 s |

Rs 9,000 slip shortfall caught in every run. Diarization degrades with noise (fewer, merged turns, 2 speakers at -1.5 dB) but Muse Spark still recovers every winner and price from the auctioneer's calls. `--clean` was faster on the loud floors (104 s vs 140 s, 125 s vs 140 s). Voices are synthetic; a live floor is the next test.