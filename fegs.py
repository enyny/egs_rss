#!/usr/bin/env python3
import requests
import tls_client

ANDROID_URL = "https://egs-platform-service.store.epicgames.com/api/v2/public/discover/home?count=10&country=US&locale=en&platform=android&start=0&store=EGS"
IOS_URL = "https://egs-platform-service.store.epicgames.com/api/v2/public/discover/home?count=10&country=US&locale=en&platform=ios&start=0&store=EGS"

FREE_GAMES_API = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"

FREE_GAMES_PARAMS = {
    "locale": "en-US",
    "country": "US",
    "allowCountries": "US"
}


def extract_mobile_free_offers(data):
    found = set()


    def search(obj):
        if isinstance(obj, dict):
            if "purchase" in obj and isinstance(obj["purchase"], list):
                for item in obj["purchase"]:
                    if item.get("discount", {}).get("discountAmountDisplay") == "-100%":
                        sandbox = item.get("purchasePayload", {}).get("sandboxId")
                        offer = item.get("purchasePayload", {}).get("offerId")
                        if sandbox and offer:
                            found.add((sandbox, offer))

            for value in obj.values():
                search(value)

        elif isinstance(obj, list):
            for item in obj:
                search(item)

    search(data)
    return found


def extract_free_games_promotions():
    offers = set()

    response = requests.get(FREE_GAMES_API, params=FREE_GAMES_PARAMS, timeout=20)
    data = response.json()

    games = data["data"]["Catalog"]["searchStore"]["elements"]

    for game in games:
        price_info = game.get("price", {}).get("totalPrice", {})
        discount_price = price_info.get("discountPrice")

        if discount_price == 0:
            namespace = game.get("namespace")
            offer_id = game.get("id")

            if namespace and offer_id:
                offers.add((namespace, offer_id))

    return offers


def fetch_mobile_json(session, url):
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "sec-ch-ua": '"Google Chrome";v="124", "Chromium";v="124", "Not=A?Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }

    response = session.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"{url} -> {response.status_code}")

    return response.json()


def build_combined_url(offers):
    if not offers:
        return None

    base = "https://store.epicgames.com/purchase?"
    params = [f"offers=1-{ns}-{offer}" for ns, offer in sorted(offers)]
    return base + "&".join(params) + "#/purchase/payment-methods"


def main():
    all_offers = set()

    session = tls_client.Session(
        client_identifier="chrome_124",
        random_tls_extension_order=True
    )

    # Mobile discover (Android + iOS)
    for url in [ANDROID_URL, IOS_URL]:
        try:
            data = fetch_mobile_json(session, url)
            mobile_offers = extract_mobile_free_offers(data)
            all_offers.update(mobile_offers)
        except Exception as e:
            print("Mobile API error:", e)

    # FreeGamesPromotions API
    try:
        promo_offers = extract_free_games_promotions()
        all_offers.update(promo_offers)
    except Exception as e:
        print("FreeGames API error:", e)

    # Build final combined URL
    combined_url = build_combined_url(all_offers)

    if combined_url:
        print("\nCombined Checkout URL:\n")
        print(combined_url)
    else:
        print("No completely free offers found.")

if __name__ == "__main__":
    main()
