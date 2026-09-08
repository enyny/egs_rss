#!/usr/bin/env python3
import requests
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from feedgen.feed import FeedGenerator

URL = "https://raw.githubusercontent.com/josephmate/EpicFreeGamesList/refs/heads/main/epic_free_games.json"
RSS_FILE = "epic_free_games.xml"

# Date window: last 30 days (UTC)
today = datetime.now(timezone.utc).date()
cutoff = today - timedelta(days=30)

# Fetch JSON
data = requests.get(URL, timeout=15).json()

# Group items by freeDate
grouped = defaultdict(list)

for item in data:
    title = item.get("gameTitle")
    free_date_str = item.get("freeDate")
    link = item.get("epicStoreLink")
    platform = item.get("platform", "").lower()

    if not title or not free_date_str or not link:
        continue

    free_date = datetime.strptime(free_date_str, "%Y-%m-%d").date()
    if free_date < cutoff:
        continue

    grouped[free_date_str].append({
        "title": title,
        "platform": platform,
        "link": link
    })

# Sort dates newest first
sorted_dates = sorted(grouped.keys(), reverse=True)

# Build RSS feed
fg = FeedGenerator()
fg.id("epic-free-games-grouped")
fg.title("Epic Free Games (30 days)")
fg.link(href="https://store.epicgames.com/")
fg.description("Epic free games grouped by freeDate (last 30 days)")
fg.language("en")

for free_date_str in sorted_dates:
    entries = grouped[free_date_str]

    # Unique titles (preserve order)
    seen_titles = []
    for e in entries:
        if e["title"] not in seen_titles:
            seen_titles.append(e["title"])

    # Title: quoted, comma-separated
    rss_title = ", ".join(f'"{t}"' for t in seen_titles)

    # Body
    lines = []
    guids = []
    for e in entries:
        lines.append(
            f'{e["title"]} - {e["platform"]}: '
            f'<a href="{e["link"]}">Link</a>'
        )
        guids.append(e["link"])

    fe = fg.add_entry()
    fe.id("|".join(guids) + f"|{free_date_str}")  # stable GUID
    fe.title(rss_title)
    fe.link(href=guids[0])
    fe.description("<br>".join(lines))

    fe.pubDate(
        datetime.strptime(free_date_str, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    )

# Write RSS
fg.rss_file(RSS_FILE)

print(f"RSS generated with {len(sorted_dates)} items")

