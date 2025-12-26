#!/usr/bin/env python3
import requests
import json
from datetime import datetime, timedelta, timezone
from feedgen.feed import FeedGenerator

URL = "https://raw.githubusercontent.com/josephmate/EpicFreeGamesList/refs/heads/main/epic_free_games.json"
RSS_FILE = "epic_free_games.xml"

# Date window: last 30 days (UTC)
today = datetime.now(timezone.utc).date()
cutoff = today - timedelta(days=30)

# Fetch JSON
data = requests.get(URL, timeout=15).json()

# Filter + sort (newest first)
items = []
for item in data:
    title = item.get("gameTitle")
    free_date_str = item.get("freeDate")
    link = item.get("epicStoreLink")

    if not title or not free_date_str or not link:
        continue

    free_date = datetime.strptime(free_date_str, "%Y-%m-%d").date()
    if free_date < cutoff:
        continue

    items.append((free_date, item))

items.sort(key=lambda x: x[0], reverse=True)

# Build RSS
fg = FeedGenerator()
fg.id("epic-free-games")
fg.title("Epic Free Games – Last 30 Days")
fg.link(href="https://store.epicgames.com/")
fg.description("Epic free games from the last 30 days")
fg.language("en")

for free_date, item in items:
    title = item["gameTitle"]
    free_date_str = item["freeDate"]
    link = item["epicStoreLink"]
    platform = item.get("platform", "").lower()

    body = "<pre>" + json.dumps(item, indent=2) + "</pre>"

    fe = fg.add_entry()
    fe.id(f"{title}|{free_date_str}")
    fe.title(f"{platform} - {title}" if platform else title)
    fe.link(href=link)
    fe.description(
        f'<p><a href="{link}">Open on Epic Games Store</a></p>{body}'
    )

    fe.pubDate(
        datetime.strptime(free_date_str, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    )

# Write RSS
fg.rss_file(RSS_FILE)

print(f"RSS generated with {len(items)} items")

