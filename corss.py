#!/usr/bin/env python3
import requests
from datetime import datetime, timezone
from collections import defaultdict
from feedgen.feed import FeedGenerator
import html

# Constants
API_URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
STORE_URL = "https://store.epicgames.com/p/"
RSS_FILE = "epicFreeGamesCO.xml"
MAX_ITEMS = 30

def fetch_free_games():
    """Fetch all currently free games from Epic Games Store."""
    data = requests.get(API_URL, timeout=15).json()
    elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])

    free_games = []

    for game in elements:
        if game.get("status") != "ACTIVE":
            continue

        price = (game.get("price") or {}).get("totalPrice") or {}
        if price.get("discountPrice") != 0:
            continue

        promotions = (game.get("promotions") or {}).get("promotionalOffers") or []
        if not promotions:
            continue

        for group in promotions:
            for promo in group.get("promotionalOffers") or []:
                start_date = promo.get("startDate")
                if not start_date:
                    continue

                # Resolve page slug
                catalog_ns = game.get("catalogNs") or {}
                mappings = catalog_ns.get("mappings") or []
                page_slug = mappings[0].get("pageSlug") if mappings else game.get("urlSlug")
                if not page_slug:
                    continue

                free_games.append({
                    "title": game.get("title", "Unknown Game"),
                    "pageSlug": page_slug,
                    "namespace": game.get("namespace"),
                    "id": game.get("id"),
                    "items": game.get("items") or [],
                    "startDate": start_date
                })

    return free_games

def group_by_date(games):
    """Group free games by promotion start date."""
    grouped = defaultdict(list)
    for game in games:
        grouped[game["startDate"]].append(game)
    return grouped

def generate_feed(grouped_games):
    """Generate RSS feed using FeedGenerator."""
    fg = FeedGenerator()
    fg.id("epic-free-games")
    fg.title("Epic Free Games")
    fg.link(href=STORE_URL)
    fg.description("Automatically generated feed of free Epic Games")
    fg.language("en")

    # Sort dates newest first and limit
    sorted_dates = sorted(
        grouped_games.keys(),
        key=lambda d: datetime.fromisoformat(d.replace("Z", "+00:00")),
        reverse=True
    )[:MAX_ITEMS]

    for start_date in sorted_dates:
        games = grouped_games[start_date]
        if not games:
            continue

        # Unique game titles for RSS item title
        titles = []
        for g in games:
            if g["title"] not in titles:
                titles.append(g["title"])
        rss_title = ", ".join(titles[:2]) + (" and more" if len(titles) > 2 else "")

        # Build HTML description
        lines = []
        guids = []
        for g in games:
            namespace = g.get("namespace") or (g.get("items")[0].get("namespace") if g.get("items") else None)
            game_id = g.get("id") or (g.get("items")[0].get("id") if g.get("items") else None)
            if not (namespace and game_id):
                continue

            link = f"{STORE_URL}{g['pageSlug']}"
            lines.append(f'{html.escape(g["title"])}: <a href="{link}">Link</a>')
            guids.append(link)

        # Combined checkout link
        if guids:
            checkout_offers = [f"1-{g.get('namespace')}-{g.get('id')}" for g in games if g.get('namespace') and g.get('id')]
            if checkout_offers:
                checkout_url = "https://store.epicgames.com/purchase?offers=" + "&offers=".join(checkout_offers) + "#/purchase/payment-methods"
                lines.append(f'<br><a href="{checkout_url}">Checkout all free games</a>')

        # Create RSS entry
        fe = fg.add_entry()
        fe.id("|".join(guids) + f"|{start_date}")
        fe.title(rss_title)
        fe.link(href=guids[0] if guids else STORE_URL)
        fe.description("<br>".join(lines))
        fe.pubDate(datetime.fromisoformat(start_date.replace("Z", "+00:00")).replace(tzinfo=timezone.utc))

    fg.rss_file(RSS_FILE)
    print(f"RSS generated: {RSS_FILE} ({len(sorted_dates)} items)")

def main():
    games = fetch_free_games()
    grouped = group_by_date(games)
    generate_feed(grouped)

if __name__ == "__main__":
    main()
