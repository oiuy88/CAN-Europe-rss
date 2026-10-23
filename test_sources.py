import requests

BASE = "https://caneurope.org"

paths = [
    "/wp-json/",
    "/wp-json/wp/v2/types",
    "/wp-json/wp/v2/posts?per_page=3",
    "/wp-json/wp/v2/publications?per_page=3",
]

for path in paths:
    url = BASE + path
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "CAN-Europe-RSS/1.0"},
            timeout=20,
        )
        print(f"\n{path}")
        print("Status:", response.status_code)
        print("Content-Type:", response.headers.get("Content-Type"))
        print("Preview:", response.text[:300].replace("\n", " "))
    except requests.RequestException as exc:
        print(f"\n{path}: {exc}")
