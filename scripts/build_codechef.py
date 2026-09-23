#!/usr/bin/env python3
"""
Build assets/codechef-card.svg by scraping the public CodeChef profile page
(CodeChef has no public stats API, unlike LeetCode/Codeforces). Self-hosted
rather than depending on a third-party card generator, since the two that
existed for CodeChef were both found dead when this was built.

Regenerated on a schedule (see .github/workflows/widget.yml) so it stays
live. If CodeChef changes its page markup, fields degrade to "N/A" instead
of crashing the whole build.
"""
import os
import re

import requests

USERNAME = os.environ.get("CODECHEF_USERNAME", "ionik_0")
OUT_PATH = os.environ.get("CODECHEF_OUT", "assets/codechef-card.svg")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


def extract(pattern, text, default="N/A", group=1, flags=re.DOTALL):
    m = re.search(pattern, text, flags)
    return m.group(group).strip() if m else default


def parse_stats(html):
    idx = html.find("rating-header text-center")
    header = html[idx:idx + 2000] if idx != -1 else html

    rating = extract(r'rating-number"[^>]*>\s*([\d?]+)', header)
    division = extract(r'\(Div\s*(\d+)\)', header, default="")
    highest = extract(r'Highest Rating\s*(\d+)', header, default=rating)

    star_block_match = re.search(r'rating-star.{0,300}', header, re.DOTALL)
    stars = len(re.findall(r'&#9733;', star_block_match.group(0))) if star_block_match else 0

    global_rank = extract(r'ratings/all["\'][^>]*>\s*<strong>\s*([\d,]+)', header)
    country_rank = extract(r'ratings/all\?filterBy[^>]*>\s*<strong>\s*([\d,]+)', header)

    country = extract(r'user-country-name[^>]*>\s*([^<]+)', html)

    return dict(rating=rating, division=division, highest=highest, stars=stars,
                global_rank=global_rank, country_rank=country_rank, country=country)


def fetch_stats():
    r = requests.get(f"https://www.codechef.com/users/{USERNAME}", headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    return parse_stats(r.text)


def build_svg(stats):
    W, H = 300, 165
    mono = "font-family:'Courier New',monospace"
    star_row = "&#9733;" * max(stats["stars"], 1)

    rating_label = f'{stats["rating"]}' + (f' (Div {stats["division"]})' if stats["division"] else "")

    rows = [
        ("Highest Rating", stats["highest"]),
        ("Global Rank", stats["global_rank"]),
        ("Country Rank", f'{stats["country_rank"]} ({stats["country"]})' if stats["country"] != "N/A" else stats["country_rank"]),
    ]

    row_svg = []
    y = 108
    for label, value in rows:
        row_svg.append(
            f'<text x="18" y="{y}" font-size="12" fill="#c9c2b8" style="{mono}">{label}</text>'
            f'<text x="282" y="{y}" font-size="12" font-weight="bold" fill="#ffffff" text-anchor="end" style="{mono}">{value}</text>'
        )
        y += 20

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="ccBg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#3a2a1e"/>
      <stop offset="100%" stop-color="#1c140d"/>
    </linearGradient>
  </defs>
  <rect x="0" y="0" width="{W}" height="{H}" rx="10" fill="url(#ccBg)"/>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="10" fill="none" stroke="#5b4638" stroke-width="1"/>

  <text x="18" y="30" font-size="15" font-weight="bold" fill="#ffffff" style="{mono}">CodeChef</text>
  <text x="282" y="30" font-size="13" fill="#e3b341" text-anchor="end" style="{mono}">{star_row}</text>
  <line x1="18" y1="40" x2="282" y2="40" stroke="#5b4638" stroke-width="1"/>

  <text x="18" y="72" font-size="13" fill="#c9c2b8" style="{mono}">Rating</text>
  <text x="282" y="76" font-size="26" font-weight="bold" fill="#ffffff" text-anchor="end" style="{mono}">{rating_label}</text>

  {"".join(row_svg)}
</svg>
'''


def main():
    stats = fetch_stats()
    svg = build_svg(stats)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        f.write(svg)
    print(f"wrote {OUT_PATH} | {stats}")


if __name__ == "__main__":
    main()
