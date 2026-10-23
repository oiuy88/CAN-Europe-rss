from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://caneurope.org/publications/"
FEED_URL = "https://oiuy88.github.io/CAN-Europe-rss/feed.xml"
OUTPUT_FILE = Path("feed.xml")
MAX_ITEMS = 50


#def fetch_publications():
    #response = requests.get(
        #SOURCE_URL,
        #headers={"User-Agent": "CAN-Europe-RSS/1.0"},
        #timeout=30,
    #)
    #response.raise_for_status()

def fetch_publications():
    response = requests.get(
        SOURCE_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
        timeout=30,
    )

    print("Status:", response.status_code)
    print("Final URL:", response.url)
    print("Content-Type:", response.headers.get("Content-Type"))
    print("Server:", response.headers.get("Server"))
    print("Response preview:", response.text[:1000])

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    publications = []
    seen_urls = set()

    for heading in soup.select("h3.card-v4__title"):
        title = heading.get_text(" ", strip=True)
        link = heading.find("a", href=True)

        # Some layouts put the link around the heading instead.
        if link is None:
            link = heading.find_parent("a", href=True)

        if not title or link is None:
            continue

        url = urljoin(SOURCE_URL, link["href"])

        # Only include CAN Europe publication pages.
        if not url.startswith("https://caneurope.org/publications/"):
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)
        publications.append({"title": title, "url": url})

    if not publications:
        raise RuntimeError(
            "No publications found. The page structure may have changed."
        )

    return publications[:MAX_ITEMS]


def generate_feed(publications):
    now = datetime.now(timezone.utc)

    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = "CAN Europe Publications"
    ET.SubElement(channel, "link").text = SOURCE_URL
    ET.SubElement(channel, "description").text = (
        "Latest publications from Climate Action Network Europe."
    )
    ET.SubElement(channel, "language").text = "en"
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(now)

    for publication in publications:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = publication["title"]
        ET.SubElement(item, "link").text = publication["url"]
        ET.SubElement(item, "guid", isPermaLink="true").text = (
            publication["url"]
        )

    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")

    tree.write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True,
    )


def main():
    publications = fetch_publications()
    generate_feed(publications)
    print(f"Wrote {len(publications)} publications to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
