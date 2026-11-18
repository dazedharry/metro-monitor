#!/usr/bin/env python3
"""Fetch Metro RSS feed(s) and merge them into a rolling story archive.

Run it as often as you like (the workflow runs it every three hours). RSS feeds
only hold the latest items, so frequent runs prevent gaps in the archive.
Standard library only.
"""
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).parent
FEEDS_FILE = ROOT / "feeds.txt"
OUT = ROOT / "docs" / "data" / "stories.json"
KEEP_DAYS = 120
USER_AGENT = "Mozilla/5.0 (compatible; MetroMonitor/1.0; personal editorial research)"

NS = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "media": "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


def read_feed_urls():
    urls = []
    for line in FEEDS_FILE.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            urls.append(line)
    return urls


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def clean(text, limit=280):
    text = re.sub(r"<[^>]+>", " ", html.unescape(text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[: limit - 1] + "…" if len(text) > limit else text


def parse_date(raw):
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def image_of(item):
    for tag in ("media:content", "media:thumbnail"):
        el = item.find(tag, NS)
        if el is not None and el.get("url"):
            return el.get("url")
    enc = item.find("enclosure")
    if enc is not None and (enc.get("type") or "").startswith("image"):
        return enc.get("url")
    return None


def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    stories = []
    for item in root.iter("item"):
        link = (item.findtext("link") or "").strip()
        title = clean(item.findtext("title"), 300)
        published = parse_date(item.findtext("pubDate"))
        if not link or not title or not published:
            continue
        creator = (item.findtext("dc:creator", namespaces=NS) or "").strip()
        cats = []
        for c in item.findall("category"):
            name = clean(c.text, 60)
            if name and name not in cats:
                cats.append(name)
        stories.append({
            "link": link,
            "title": title,
            "published": published.isoformat().replace("+00:00", "Z"),
            "author": creator or None,
            "categories": cats,
            "summary": clean(item.findtext("description")),
            "image": image_of(item),
        })
    return stories


def main():
    now = datetime.now(timezone.utc)
    archive = {}
    if OUT.exists():
        try:
            for s in json.loads(OUT.read_text()).get("stories", []):
                archive[s["link"]] = s
        except (json.JSONDecodeError, KeyError):
            print("Existing archive unreadable; starting fresh", file=sys.stderr)

    urls = read_feed_urls()
    fetched, new, errors = 0, 0, []
    for url in urls:
        try:
            items = parse(fetch(url))
        except Exception as exc:  # network, HTTP or XML problems
            errors.append(f"{url}: {exc}")
            continue
        fetched += len(items)
        for s in items:
            old = archive.get(s["link"])
            s["first_seen"] = old["first_seen"] if old else now.isoformat().replace("+00:00", "Z")
            if not old:
                new += 1
            archive[s["link"]] = s

    if errors and len(errors) == len(urls):
        print("All feeds failed:\n" + "\n".join(errors), file=sys.stderr)
        sys.exit(1)

    cutoff = (now - timedelta(days=KEEP_DAYS)).isoformat().replace("+00:00", "Z")
    stories = sorted(
        (s for s in archive.values() if s["published"] >= cutoff),
        key=lambda s: s["published"],
        reverse=True,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "feeds": urls,
        "count": len(stories),
        "stories": stories,
    }, ensure_ascii=False, indent=1))
    print(f"Fetched {fetched} items, {new} new, {len(stories)} in archive.")
    for e in errors:
        print("Warning:", e, file=sys.stderr)


if __name__ == "__main__":
    main()
