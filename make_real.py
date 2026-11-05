"""Test auctions over REAL market recordings (Wikimedia Commons, see samples/real/CREDITS.md)."""
import asyncio
from pathlib import Path
import numpy as np
from make_market import build, load

REAL = Path(__file__).parent / "samples" / "real"
amb = np.concatenate([load(REAL / f) for f in ("gombe_main_market.ogg", "lagos_idumota_market.ogg", "cebu_carbon_market.ogg", "huancayo_market.ogg")])

async def main():
    await build("real", overlap=0.3, babble_gain=0.55, thumps_per_min=0, seed=31, ambience=amb)        # busy real floor
    await build("real_loud", overlap=0.6, babble_gain=1.0, thumps_per_min=0, seed=37, ambience=amb[len(amb)//3:])  # bidders as loud as the market

asyncio.run(main())
