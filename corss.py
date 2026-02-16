#!/usr/bin/env python3
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from collections import defaultdict
from email.utils import format_datetime
import html

# Constants
API_URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
STORE_URL = "https://store.epicgames.com/p/"
CHECKOUT_BASE = "https://store.epicgames.com/purchase?offers="
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

def create_rss(grouped_games):
    """Generate RSS XML tree for grouped free games."""
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Epic Games Free Games"
    ET.SubElement(channel, "link").text = STORE_URL
    ET.SubElement(channel, "description").text = "Automatically generated feed of free Epic Games"

    # Sort promotion dates descending, limit to MAX_ITEMS
    sorted_dates = sorted(
        grouped_games.keys(),
        key=lambda d: datetime.fromisoformat(d.replace("Z", "+00:00")),
        reverse=True
    )[:MAX_ITEMS]

    for start_date in sorted_dates:
        games = grouped_games[start_date]
        if not games:
            continue

        item = ET.SubElement(channel, "item")
        dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        ET.SubElement(item, "pubDate").text = format_datetime(dt)

        # Generate item title
        titles = [g["title"] for g in games]
        article_title = ", ".join(titles[:2]) + (" and more" if len(titles) > 2 else "")
        ET.SubElement(item, "title").text = f"\n {article_title}"

        description_parts = []
        checkout_offers = []

        for i, game in enumerate(games):
            # Resolve namespace and id
            namespace = game.get("namespace") or (game.get("items")[0].get("namespace") if game.get("items") else None)
            game_id = game.get("id") or (game.get("items")[0].get("id") if game.get("items") else None)
            if not (namespace and game_id):
                continue

            product_link = f"{STORE_URL}{game['pageSlug']}"
            checkout_offers.append(f"1-{namespace}-{game_id}")

            safe_title = html.escape(game["title"])
            description_parts.append(f'{"<br>" if i == 0 else ""}{safe_title}: <a href="{product_link}">To Game Page</a>')

        # Combined checkout link
        if checkout_offers:
            checkout_url = CHECKOUT_BASE + "&offers=".join(checkout_offers) + "#/purchase/payment-methods"
            description_parts.append(f'<br><a href="{checkout_url}">Checkout all free games</a>')

        description_html = "<br>".join(description_parts)

        # Add description and content:encoded
        #ET.SubElement(item, "description").text = f"<![CDATA[{description_html}"
        ET.SubElement(item, "{http://purl.org/rss/1.0/modules/content/}encoded").text = f"<![CDATA[{description_html}"

    return ET.ElementTree(rss)

def main():
    games = fetch_free_games()
    if not games:
        print("No free games found to generate RSS feed")
        return

    grouped = group_by_date(games)
    rss_tree = create_rss(grouped)
    rss_tree.write("epicFreeGamesCO.xml", encoding="utf-8", xml_declaration=True)
    print("RSS feed generated: epicFreeGamesCO.xml")

if __name__ == "__main__":
    main()
