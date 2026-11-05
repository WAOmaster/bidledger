# How Meta makes money when BidLedger runs on its platform

Checked 5 Nov 2026. [U] = estimate, not sourced.

## Revenue lines, strongest first

| # | Meta product | How BidLedger feeds it | Money signal |
|---|---|---|---|
| 1 | **Meta Model API** (Muse Voice minutes + Muse Spark tokens) | Every auction minute is transcribed and reasoned over. A market running 4 h of auctions a day is ~240 audio minutes a day, every day | Recurring, usage-based. This is the line Meta is trying to grow with this hackathon. Per-minute price not published on the billing page [U] |
| 2 | **WhatsApp utility messages** | 2 receipts per lot (buyer + farmer), sent by the market's business number outside the customer window, so they are billable | India utility ≈ **$0.0014/msg**, Brazil ≈ $0.0068–0.008 (third-party rate cards, Apr 2026). Small per message, large in count: 500 lots/day × 2 × 1,522 e-NAM mandis ≈ 1.5 M msgs/day [U] |
| 3 | **WhatsApp Pay / in-chat payments** (UPI India, Pix Brazil) | The receipt carries a "Pay farmer" button: buyer settles the lot inside the same chat, farmer is paid from the verified price, not the slip | Moves the settlement of a ₹80,262 crore/yr channel (e-NAM FY25 turnover alone) into WhatsApp; Meta's interest is payments volume and stickiness |
| 4 | **Click-to-WhatsApp ads** | Commission agents and buyers advertise tomorrow's lots and verified prices; farmers tap to chat with a trusted agent | Ad spend from a group that today advertises on posters and word of mouth [U] |
| 5 | **Business AI / Business Agent** | The Spark clerk becomes the market's WhatsApp agent: "What did my carrots sell for?" answered from the ledger with the clip | Uses Meta's Business Agent push (1M+ businesses) |
| 6 | **Ray-Ban Meta glasses** | Auctioneer or market clerk wears glasses: hands-free, first-person recording; later SAM 3.1 tracks raised hands for silent bids | Hardware sale per market + a real work use case for glasses in Meta's growth markets |
| 7 | **Data → ads** (aggregated, consented) | Daily verified floor prices per crop and market | Agri-input brands (seed, fertiliser, tractors) target farmers with Advantage+ on Facebook/Instagram using price-season signals [U] |
| 8 | **Credit and insurance partners** | A farmer's verified sale history is the first credit file many have | Lenders and insurers send marketing and utility templates to farmers over WhatsApp [U] |

## Same engine, other spoken markets

From the Haiku scan (`OTHER-MARKETS.md`): Brazil construction day-labour (most receipts), India fish-landing auctions, India cattle fairs (highest value per receipt). Brazil's higher message price makes it about 5× the messaging revenue per receipt of India.

## Honest limits

- Utility templates sent inside an open customer service window are free, so only business-initiated receipts are billable.
- Message prices are third-party rate cards and Brazil figures disagree; Meta's own page is authoritative.
- Recording consent: needs the market's notice and each trader's opt-in (India DPDP Act, Brazil LGPD).

Sources: [WhatsApp pricing (Meta)](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing) · [India utility $0.0014, formbeep](https://formbeep.pages.dev/whatsapp-api-pricing/) · [Brazil $0.0068, Typebot](https://typebot.com/blog/whatsapp-business-api-pricing) · [Brazil $0.0080, Message Central](https://www.messagecentral.com/en-in/blog/whatsapp-business-api-pricing) · [e-NAM 1,522 mandis, Tripura Info](https://tripurainfo.com/NationalNewDetails.aspx?nId=7417) · [e-NAM FY25 turnover ₹80,262 cr](https://www.indiabusinesstrade.in/blogs/e-nam-2-0)
