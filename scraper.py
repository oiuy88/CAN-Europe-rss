import html
import re
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://caneurope.org"
LIST_URL = f"{BASE_URL}/publications/"
OUTPUT_FILE = "can-europe-publications.xml"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PAN-Europe-RSS/1.0; "
        "+https://github.com/)"
    )
}

DATE_PATTERN = re.compile(
    r"(January|February|March|April|May|June|July|"
    r"August|September|October|November|December)"
    r"\s+\d{1,2},\s+\d{4}\s+-\s+\d{2}:\d{2}"
)


def get_page(page_number):
    if page_number == 0:
        url = LIST_URL
    else:
        url = f"{LIST_URL}?page={page_number}"

    print(f"Fetching {url}")

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


def parse_date(date_string):
    return datetime.strptime(
        date_string,
        "%B %d, %Y - %H:%M",
    ).replace(tzinfo=timezone.utc)


def find_article_container(title_link):
    """
    Walk upward from the title until we find a container
    containing the publication date.
    """

    element = title_link

    for _ in range(8):
        element = element.parent

        if element is None:
            return None

        text = element.get_text(" ", strip=True)

        if DATE_PATTERN.search(text):
            return element

    return None


def extract_articles(soup):
    articles = {}

    # Find publication titles.
    for heading in soup.find_all("h3"):
        title_link = heading.find("a", href=True)

        if not title_link:
            continue

        href = urljoin(BASE_URL, title_link["href"])

        # Only accept CAN Europe publication URLs.
        if not re.match(
            r"^https?://(?:www\.)?caneurope\.org/publications/.+",
            href,
        ):
            continue

        title = title_link.get_text(" ", strip=True)

        if not title:
            continue

        container = find_article_container(title_link)

        if container is None:
            print(f"Could not find date for: {title}")
            continue

        container_text = container.get_text(" ", strip=True)
        date_match = DATE_PATTERN.search(container_text)

        if not date_match:
            continue

        published = parse_date(date_match.group(0))

        # Extract a reasonably clean teaser.
        description = container_text

        description = description.replace(
            date_match.group(0), "", 1
        )

        description = description.replace(title, "", 1)

        description = re.sub(
            r"\bRead more\b",
            "",
            description,
            flags=re.IGNORECASE,
        )

        description = re.sub(
            r"\s+",
            " ",
            description,
        ).strip()

        articles[href] = {
            "title": title,
            "url": href,
            "published": published,
            "description": description,
        }

    return list(articles.values())

def collect_articles():
    articles = {}

    page = 0

    while True:

        soup = get_page(page)

        page_articles = extract_articles(soup)

        print(
            f"Found {len(page_articles)} articles on page {page}"
        )

        if not page_articles:
            print("No more articles found.")
            break

        old_count = len(articles)

        for article in page_articles:
            articles[article["url"]] = article

        # If a page produces no new URLs, stop.
        if len(articles) == old_count:
            print("No new articles found.")
            break

        page += 1

        # Safety limit so a website change cannot create
        # an infinite loop.
        if page > 100:
            print("Reached safety limit.")
            break

    return sorted(
        articles.values(),
        key=lambda article: article["published"],
        reverse=True,
    )


def create_rss(articles):

    rss = ET.Element(
        "rss",
        {
            "version": "2.0",
        },
    )

    channel = ET.SubElement(rss, "channel")

    ET.SubElement(
        channel,
        "title",
    ).text = "CAN Europe publications"

    ET.SubElement(
        channel,
        "link",
    ).text = LIST_URL

    ET.SubElement(
        channel,
        "description",
    ).text = "Latest publications from CAN Europe"

    ET.SubElement(
        channel,
        "language",
    ).text = "en"

    ET.SubElement(
        channel,
        "lastBuildDate",
    ).text = format_datetime(
        datetime.now(timezone.utc)
    )

    for article in articles:

        item = ET.SubElement(
            channel,
            "item",
        )

        ET.SubElement(
            item,
            "title",
        ).text = article["title"]

        ET.SubElement(
            item,
            "link",
        ).text = article["url"]

        ET.SubElement(
            item,
            "guid",
            {
                "isPermaLink": "true",
            },
        ).text = article["url"]

        ET.SubElement(
            item,
            "pubDate",
        ).text = format_datetime(
            article["published"]
        )

        # XML-safe description.
        description = article["description"]
            

        ET.SubElement(
            item,
            "description",
        ).text = description

    return ET.ElementTree(rss)


def main():

    articles = collect_articles()

    print()
    print(f"Total articles: {len(articles)}")

    if not articles:
        raise RuntimeError(
            "No publications found. "
            "The CAN Europe page structure may have changed."
        )

    rss = create_rss(articles)

    ET.indent(
        rss,
        space="  ",
    )

    rss.write(
        OUTPUT_FILE,
        encoding="utf-8",
        xml_declaration=True,
    )

    print(f"RSS written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
