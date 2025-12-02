import aiohttp
import asyncio
import json
import sys

API_URL = "http://api.polymarket.com/markets?interval=15m"


async def fetch_market_ids():
    print("🔄 Fetching Polymarket 15-minute market IDs...\n")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL) as resp:
                if resp.status != 200:
                    print(f"❌ API Error: HTTP {resp.status}")
                    sys.exit()

                data = await resp.json()

    except Exception as e:
        print(f"❌ ERROR connecting to Polymarket API: {e}")
        sys.exit()

    if not data:
        print("❌ ERROR: No data returned from Polymarket.")
        sys.exit()

    market_ids = {
        "BTC_UP": None,
        "BTC_DOWN": None,
        "ETH_UP": None,
        "ETH_DOWN": None,
        "SOL_UP": None,
        "SOL_DOWN": None,
        "XRP_UP": None,
        "XRP_DOWN": None
    }

    # Parse the data
    for m in data:
        slug = m.get("slug", "").lower()
        market_id = m.get("id")

        if not slug or not market_id:
            continue

        if "btc" in slug and "up" in slug:
            market_ids["BTC_UP"] = market_id
        if "btc" in slug and "down" in slug:
            market_ids["BTC_DOWN"] = market_id

        if "eth" in slug and "up" in slug:
            market_ids["ETH_UP"] = market_id
        if "eth" in slug and "down" in slug:
            market_ids["ETH_DOWN"] = market_id

        if "sol" in slug and "up" in slug:
            market_ids["SOL_UP"] = market_id
        if "sol" in slug and "down" in slug:
            market_ids["SOL_DOWN"] = market_id

        if "xrp" in slug and "up" in slug:
            market_ids["XRP_UP"] = market_id
        if "xrp" in slug and "down" in slug:
            market_ids["XRP_DOWN"] = market_id

    print("✅ Market IDs Fetched:\n")
    print(json.dumps(market_ids, indent=4))

    # Save file
    try:
        with open("market_ids.json", "w") as f:
            json.dump(market_ids, f, indent=4)
        print("\n💾 Saved to market_ids.json successfully!")
    except Exception as e:
        print(f"❌ ERROR saving file: {e}")

    print("\n✨ Done.")

if __name__ == "__main__":
    asyncio.run(fetch_market_ids())
