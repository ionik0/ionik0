#!/usr/bin/env python3
"""
Build assets/retro-widget.svg: ONE 1990s-computer-style window containing
three panels - live avatar (left), live GitHub stats (top right), and the
kitten walking animation (bottom right, "KITTY PLAYGROUND").

Everything in this file regenerates on a schedule (see .github/workflows/
avatar.yml): live avatar_url, live contribution/streak/follower/repo/star
counts, and the kitten re-embedded from its committed source photo. The
kitten's photo and jokes are fixed, but it's still rebuilt into the SVG
every run so the whole window is always one consistent, freshly generated
artifact rather than several separately-hosted images.

The VHS degrade is an original re-implementation (chroma noise, luma
downsample/upsample, row-wave distortion), not vendored from any
third-party effect library.
"""
import base64
import io
import os
import sys

import numpy as np
import requests
from PIL import Image

USERNAME = os.environ.get("GITHUB_USERNAME", "ionik0")
TOKEN = os.environ.get("GITHUB_TOKEN")
OUT_PATH = os.environ.get("WIDGET_OUT", "assets/retro-widget.svg")
KITTEN_SRC = os.environ.get("KITTEN_SRC", "assets/kitten_source.png")

API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"
MONO = "font-family:'Courier New',monospace"

PHRASES = [
    "i can't code",
    "what bug is a debug?",
    "turn it off and on?",
    "404: motivation not found",
]

# ---- window geometry (1990s computer window: title bar, menu bar, status bar) ----
W, H = 760, 390
CONTENT_Y0, CONTENT_Y1 = 54, 354
AVATAR = dict(x=20, y=CONTENT_Y0, w=330, h=CONTENT_Y1 - CONTENT_Y0)
RIGHT_X, RIGHT_W = AVATAR["x"] + AVATAR["w"] + 16, W - (AVATAR["x"] + AVATAR["w"] + 16) - 20
STATS = dict(x=RIGHT_X, y=CONTENT_Y0, w=RIGHT_W, h=150)
KITTY = dict(x=RIGHT_X, y=STATS["y"] + STATS["h"] + 14, w=RIGHT_W,
             h=CONTENT_Y1 - (STATS["y"] + STATS["h"] + 14))


def fetch_user():
    r = requests.get(f"{API}/users/{USERNAME}", timeout=20)
    r.raise_for_status()
    return r.json()


def fetch_repo_stars():
    r = requests.get(f"{API}/users/{USERNAME}/repos", params={"per_page": 100}, timeout=20)
    r.raise_for_status()
    return sum(repo.get("stargazers_count", 0) for repo in r.json())


def fetch_calendar():
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }
    """
    r = requests.post(
        GRAPHQL,
        json={"query": query, "variables": {"login": USERNAME}},
        headers={"Authorization": f"bearer {TOKEN}"},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for w in data["weeks"] for d in w["contributionDays"]]
    return data["totalContributions"], days


def longest_streak(days):
    best = cur = 0
    for d in days:
        if d["contributionCount"] > 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def vhs_effect(img: Image.Image) -> Image.Image:
    """Original re-implementation of a VHS-style degrade: chroma/luma
    noise, a downsample/upsample compression pass, and a row-wave
    distortion. Not derived from any third-party source."""
    rng = np.random.default_rng()
    arr = np.array(img.convert("RGB")).astype(np.float32)
    h, w, _ = arr.shape

    small = Image.fromarray(arr.astype(np.uint8)).resize((w // 3, h), Image.BILINEAR)
    arr = np.array(small.resize((w, h), Image.BILINEAR)).astype(np.float32)

    for c, strength in enumerate((10, 14, 16)):
        arr[:, :, c] += rng.normal(0, strength, (h, w))
    arr += rng.normal(0, 6, (h, w, 1))
    arr = np.clip(arr, 0, 255)

    rows, cols = np.indices((h, w))
    offset = (1.4 * np.sin(2 * np.pi * rows[:, 0] / 45)).astype(int)
    shifted = np.empty_like(arr)
    for y in range(h):
        shifted[y] = np.roll(arr[y], offset[y], axis=0)
    arr = shifted

    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def group_box(x, y, w, h, label):
    """Classic Win95 'group box': a border with the label breaking it."""
    label_w = len(label) * 6.2 + 10
    return f'''
  <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="#808080" stroke-width="1"/>
  <rect x="{x+1}" y="{y+1}" width="{w-2}" height="{h-2}" fill="none" stroke="#ffffff" stroke-width="1"/>
  <rect x="{x+10}" y="{y-1}" width="{label_w}" height="3" fill="#c8c4bc"/>
  <text x="{x+14}" y="{y+3}" font-size="11" font-weight="bold" fill="#000" style="{MONO}">{label}</text>'''


def window_chrome():
    return f'''
  <rect x="0" y="0" width="{W}" height="{H}" fill="#c8c4bc"/>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" fill="none" stroke="#404040" stroke-width="1"/>
  <rect x="2" y="2" width="{W-4}" height="{H-4}" fill="none" stroke="#ffffff" stroke-width="1" opacity="0.6"/>

  <rect x="2" y="2" width="{W-4}" height="20" fill="url(#titleGrad)"/>
  <text x="8" y="16" fill="#ffffff" font-size="12" font-weight="bold" style="{MONO}">{USERNAME}.avi - Player</text>
  <rect x="{W-58}" y="5" width="14" height="14" fill="#c8c4bc" stroke="#404040" stroke-width="1"/>
  <text x="{W-54}" y="16" font-size="10" style="{MONO}">_</text>
  <rect x="{W-40}" y="5" width="14" height="14" fill="#c8c4bc" stroke="#404040" stroke-width="1"/>
  <rect x="{W-37}" y="8" width="8" height="8" fill="none" stroke="#000" stroke-width="1"/>
  <rect x="{W-22}" y="5" width="14" height="14" fill="#c8c4bc" stroke="#404040" stroke-width="1"/>
  <text x="{W-19}" y="16" font-size="10" font-weight="bold" style="{MONO}">x</text>

  <text x="10" y="38" font-size="11" fill="#000" style="{MONO}">File   View   Play   Tools   Help</text>
  <line x1="0" y1="46" x2="{W}" y2="46" stroke="#808080" stroke-width="1"/>
  <line x1="0" y1="47" x2="{W}" y2="47" stroke="#ffffff" stroke-width="1"/>'''


def avatar_panel(photo_b64):
    x, y, w, h = AVATAR["x"], AVATAR["y"], AVATAR["w"], AVATAR["h"]
    return f'''
  <rect x="{x-3}" y="{y-3}" width="{w+6}" height="{h+6}" fill="#000"/>
  <rect x="{x-3}" y="{y-3}" width="{w+6}" height="{h+6}" fill="none" stroke="#404040" stroke-width="2"/>
  <rect x="{x-1}" y="{y-1}" width="{w+2}" height="{h+2}" fill="none" stroke="#ffffff" stroke-width="1" opacity="0.4"/>
  <clipPath id="avClip"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath>
  <g clip-path="url(#avClip)">
    <image x="{x}" y="{y}" width="{w}" height="{h}" href="data:image/png;base64,{photo_b64}" preserveAspectRatio="xMidYMid slice"/>
    <circle cx="{x+14}" cy="{y+14}" r="5" fill="#ff2020"/>
    <text x="{x+24}" y="{y+18}" font-size="11" font-weight="bold" fill="#ffffff" style="{MONO}">REC</text>
  </g>
  <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="#000" stroke-width="1"/>'''


def stats_panel(stats):
    x, y, w, h = STATS["x"], STATS["y"], STATS["w"], STATS["h"]
    rows = [
        ("Contributions", stats["contributions"]),
        ("Longest streak", f'{stats["streak"]}d'),
        ("Followers", stats["followers"]),
        ("Public repos", stats["repos"]),
        ("Total stars", stats["stars"]),
    ]
    lines = []
    row_y = y + 44
    for label, value in rows:
        lines.append(
            f'<text x="{x+14}" y="{row_y}" font-size="11" fill="#000" style="{MONO}">{label}</text>'
            f'<text x="{x+w-14}" y="{row_y}" font-size="11" fill="#000" text-anchor="end" '
            f'font-weight="bold" style="{MONO}">{value}</text>'
        )
        row_y += 22
    return group_box(x, y, w, h, "GITHUB STATS") + "\n  " + "\n  ".join(lines)


def kitten_panel(kitten_b64, src_w, src_h):
    x, y, w, h = KITTY["x"], KITTY["y"], KITTY["w"], KITTY["h"]
    label_h = 22
    fx, fy = x + 10, y + label_h
    fw, fh = w - 20, h - label_h - 8

    cat_h = round(fh * 0.6)
    cat_w = round(cat_h * src_w / src_h)
    bubble_w, bubble_h = 170, 22
    bubble_overflow = max(0, (bubble_w - cat_w) / 2) + 6
    walk_min = bubble_overflow
    walk_max = max(walk_min, fw - cat_w - bubble_overflow)
    walk_dur = 14
    speech_cycle = 12
    ground_y = fh - 4

    bubble_x = cat_w / 2 - bubble_w / 2
    bubble_y = -(bubble_h + 12)

    texts = []
    n = len(PHRASES)
    for i, phrase in enumerate(PHRASES):
        seg = 1 / n
        a, b = i * seg, (i + 1) * seg
        fade = 0.02
        if i == 0:
            kt, vals = [0, a + seg - fade, b, 1], [1, 1, 0, 0]
        else:
            kt, vals = [0, a, a + fade, b - fade, b, 1], [0, 0, 1, 1, 0, 0]
        kt_s = ";".join(f"{k:.4f}" for k in kt)
        vals_s = ";".join(str(v) for v in vals)
        anim = (f'<animate attributeName="opacity" begin="0s" dur="{speech_cycle}s" '
                f'repeatCount="indefinite" calcMode="linear" keyTimes="{kt_s}" values="{vals_s}"/>')
        texts.append(
            f'<text x="{cat_w/2}" y="{bubble_y + bubble_h/2 + 4}" text-anchor="middle" '
            f'font-size="9.5" font-family="Courier New,monospace" fill="#1f2328" opacity="0">{phrase}{anim}</text>'
        )
    texts_svg = "\n        ".join(texts)

    box = group_box(x, y, w, h, "KITTY PLAYGROUND")
    anim_group = f'''
    <clipPath id="kittyClip"><rect x="{fx}" y="{fy}" width="{fw}" height="{fh}"/></clipPath>
    <g clip-path="url(#kittyClip)">
      <line x1="{fx}" y1="{fy+ground_y}" x2="{fx+fw}" y2="{fy+ground_y}" stroke="#a8a296" stroke-width="1" stroke-dasharray="3 3"/>
      <g transform="translate({fx},{fy})">
        <g>
          <animateTransform attributeName="transform" type="translate" dur="{walk_dur}s" repeatCount="indefinite"
            keyTimes="0;0.5;1" values="{walk_min},{ground_y-cat_h};{walk_max},{ground_y-cat_h};{walk_min},{ground_y-cat_h}"/>
          <g>
            <rect x="{bubble_x}" y="{bubble_y}" width="{bubble_w}" height="{bubble_h}" rx="8"
              fill="#ffffff" stroke="#1f2328" stroke-width="1.3"/>
            <polygon points="{cat_w/2-5},{bubble_y+bubble_h} {cat_w/2+5},{bubble_y+bubble_h} {cat_w/2},{bubble_y+bubble_h+7}"
              fill="#ffffff" stroke="#1f2328" stroke-width="1.3"/>
            <rect x="{cat_w/2-5}" y="{bubble_y+bubble_h-1}" width="10" height="2" fill="#ffffff"/>
            {texts_svg}
          </g>
          <g>
            <animateTransform attributeName="transform" type="translate" dur="0.5s" repeatCount="indefinite"
              keyTimes="0;0.5;1" values="0,0;0,-3;0,0"/>
            <image x="0" y="0" width="{cat_w}" height="{cat_h}" href="data:image/png;base64,{kitten_b64}"/>
          </g>
        </g>
      </g>
    </g>'''
    return box + anim_group


def build_svg(photo, stats, kitten_b64, kitten_w, kitten_h):
    buf = io.BytesIO()
    photo.save(buf, format="PNG")
    photo_b64 = base64.b64encode(buf.getvalue()).decode()

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="titleGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#0a246a"/>
      <stop offset="100%" stop-color="#a6caf0"/>
    </linearGradient>
  </defs>
  {window_chrome()}
  {avatar_panel(photo_b64)}
  {stats_panel(stats)}
  {kitten_panel(kitten_b64, kitten_w, kitten_h)}
  <rect x="2" y="{H-22}" width="{W-4}" height="18" fill="#c8c4bc" stroke="#808080" stroke-width="1"/>
  <text x="10" y="{H-9}" font-size="11" fill="#000" style="{MONO}">Ready</text>
</svg>
'''


def main():
    user = fetch_user()
    avatar_url = user["avatar_url"]
    followers = user["followers"]
    repos = user["public_repos"]

    contributions, days = (0, [])
    if TOKEN:
        try:
            contributions, days = fetch_calendar()
        except Exception as e:
            print(f"warning: contribution calendar fetch failed: {e}", file=sys.stderr)
    streak = longest_streak(days) if days else 0

    try:
        stars = fetch_repo_stars()
    except Exception as e:
        print(f"warning: repo star fetch failed: {e}", file=sys.stderr)
        stars = 0

    r = requests.get(avatar_url, timeout=20)
    r.raise_for_status()
    photo = Image.open(io.BytesIO(r.content)).convert("RGB")
    processed = vhs_effect(photo)

    with open(KITTEN_SRC, "rb") as f:
        kitten_b64 = base64.b64encode(f.read()).decode()
    kitten_w, kitten_h = Image.open(KITTEN_SRC).size

    stats = dict(contributions=contributions, streak=streak, followers=followers,
                 repos=repos, stars=stars)
    svg = build_svg(processed, stats, kitten_b64, kitten_w, kitten_h)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        f.write(svg)
    print(f"wrote {OUT_PATH} ({len(svg)} bytes) | {stats}")


if __name__ == "__main__":
    main()
