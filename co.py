#!/usr/bin/env python3
import requests

API_URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"

params = {
    "locale": "en-US",
    "country": "US",
    "allowCountries": "US"
}

response = requests.get(API_URL, params=params)
data = response.json()

games = data["data"]["Catalog"]["searchStore"]["elements"]

offers = []

for game in games:
    # Check if currently free (discountPrice == 0)
    price_info = game.get("price", {}).get("totalPrice", {})
    discount_price = price_info.get("discountPrice")

    if discount_price == 0:
        namespace = game.get("namespace")
        offer_id = game.get("id")

        if namespace and offer_id:
            offers.append(f"1-{namespace}-{offer_id}")

if offers:
    checkout_url = (
        "https://store.epicgames.com/purchase?"
        + "&".join([f"offers={o}" for o in offers])
        + "#/purchase/payment-methods"
    )

    print("Checkout URL:")
    print(checkout_url)
else:
    print("No completely free games found.")
