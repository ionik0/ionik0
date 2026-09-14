#!/usr/bin/env python3
"""
Rebuild assets/retro-camera-avatar.svg from the live GitHub avatar and
live contribution stats. Run on a schedule so it always reflects whoever
GITHUB_USERNAME currently is / however many contributions they now have.

Effect note: this reimplements a VHS-style degrade (chroma noise, luma
downsample/upsample compression artifacts, row-wave distortion) as
original code. It does not vendor any third-party effect library.
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
OUT_PATH = os.environ.get("AVATAR_OUT", "assets/retro-camera-avatar.svg")

API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"


def fetch_user():
    r = requests.get(f"{API}/users/{USERNAME}", timeout=20)
    r.raise_for_status()
    return r.json()


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

    # luma-ish compression artifact: downscale then upscale
    small = Image.fromarray(arr.astype(np.uint8)).resize((w // 3, h), Image.BILINEAR)
    arr = np.array(small.resize((w, h), Image.BILINEAR)).astype(np.float32)

    # per-channel color noise (chroma bleed)
    for c, strength in enumerate((10, 14, 16)):
        arr[:, :, c] += rng.normal(0, strength, (h, w))

    # overall luma grain
    arr += rng.normal(0, 6, (h, w, 1))
    arr = np.clip(arr, 0, 255)

    # horizontal tape-wave distortion
    rows, cols = np.indices((h, w))
    offset = (1.4 * np.sin(2 * np.pi * rows[:, 0] / 45)).astype(int)
    shifted = np.empty_like(arr)
    for y in range(h):
        shifted[y] = np.roll(arr[y], offset[y], axis=0)
    arr = shifted

    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return out


def build_svg(photo: Image.Image, contributions: int, streak: int, followers: int) -> str:
    buf = io.BytesIO()
    photo.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    W, H = 380, 400
    vx, vy, vw, vh = 60, 54, 260, 260
    mono = "font-family:'Courier New',monospace"

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <clipPath id="vidClip"><rect x="{vx}" y="{vy}" width="{vw}" height="{vh}"/></clipPath>
    <linearGradient id="titleGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#0a246a"/>
      <stop offset="100%" stop-color="#a6caf0"/>
    </linearGradient>
  </defs>

  <rect x="0" y="0" width="{W}" height="{H}" fill="#c8c4bc"/>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" fill="none" stroke="#404040" stroke-width="1"/>
  <rect x="2" y="2" width="{W-4}" height="{H-4}" fill="none" stroke="#ffffff" stroke-width="1" opacity="0.6"/>

  <rect x="2" y="2" width="{W-4}" height="20" fill="url(#titleGrad)"/>
  <text x="8" y="16" fill="#ffffff" font-size="12" font-weight="bold" style="{mono}">{USERNAME}.avi - Player</text>
  <rect x="{W-58}" y="5" width="14" height="14" fill="#c8c4bc" stroke="#404040" stroke-width="1"/>
  <text x="{W-54}" y="16" font-size="10" style="{mono}">_</text>
  <rect x="{W-40}" y="5" width="14" height="14" fill="#c8c4bc" stroke="#404040" stroke-width="1"/>
  <rect x="{W-37}" y="8" width="8" height="8" fill="none" stroke="#000" stroke-width="1"/>
  <rect x="{W-22}" y="5" width="14" height="14" fill="#c8c4bc" stroke="#404040" stroke-width="1"/>
  <text x="{W-19}" y="16" font-size="10" font-weight="bold" style="{mono}">x</text>

  <text x="10" y="38" font-size="11" fill="#000" style="{mono}">File   View   Play   Tools   Help</text>
  <line x1="0" y1="46" x2="{W}" y2="46" stroke="#808080" stroke-width="1"/>
  <line x1="0" y1="47" x2="{W}" y2="47" stroke="#ffffff" stroke-width="1"/>

  <rect x="{vx-3}" y="{vy-3}" width="{vw+6}" height="{vh+6}" fill="#000"/>
  <rect x="{vx-3}" y="{vy-3}" width="{vw+6}" height="{vh+6}" fill="none" stroke="#404040" stroke-width="2"/>
  <rect x="{vx-1}" y="{vy-1}" width="{vw+2}" height="{vh+2}" fill="none" stroke="#ffffff" stroke-width="1" opacity="0.4"/>

  <g clip-path="url(#vidClip)">
    <image x="{vx}" y="{vy}" width="{vw}" height="{vh}" href="data:image/png;base64,{b64}" preserveAspectRatio="xMidYMid slice"/>

    <circle cx="{vx+14}" cy="{vy+14}" r="5" fill="#ff2020"/>
    <text x="{vx+24}" y="{vy+18}" font-size="11" font-weight="bold" fill="#ffffff" style="{mono}">REC</text>

    <rect x="{vx}" y="{vy+vh-26}" width="{vw}" height="26" fill="#000000" opacity="0.55"/>
    <text x="{vx+8}" y="{vy+vh-10}" font-size="10" fill="#39FF14" style="{mono}">{contributions} contribs</text>
    <text x="{vx+vw-84}" y="{vy+vh-10}" font-size="10" fill="#39FF14" style="{mono}">{streak}d streak</text>
  </g>
  <rect x="{vx}" y="{vy}" width="{vw}" height="{vh}" fill="none" stroke="#000" stroke-width="1"/>

  <rect x="{vx-40}" y="304" width="{vw+80}" height="10" fill="#e8e6e0" stroke="#808080" stroke-width="1"/>
  <rect x="{vx-40}" y="304" width="{int((vw+80)*0.32)}" height="10" fill="#3a6ea5"/>
  <rect x="{vx-40+int((vw+80)*0.32)-3}" y="302" width="6" height="14" fill="#c8c4bc" stroke="#404040" stroke-width="1"/>

  <g transform="translate({W/2-54},324)">
    <rect x="0" y="0" width="30" height="24" fill="#c8c4bc" stroke="#404040" stroke-width="1"/>
    <polygon points="20,4 20,20 8,12" fill="#000"/>
    <rect x="6" y="4" width="3" height="16" fill="#000"/>

    <rect x="36" y="0" width="30" height="24" fill="#c8c4bc" stroke="#404040" stroke-width="1"/>
    <polygon points="45,4 45,20 59,12" fill="#000"/>

    <rect x="72" y="0" width="30" height="24" fill="#c8c4bc" stroke="#404040" stroke-width="1"/>
    <polygon points="78,4 78,20 90,12" fill="#000"/>
    <rect x="91" y="4" width="3" height="16" fill="#000"/>
  </g>

  <rect x="2" y="{H-22}" width="{W-4}" height="18" fill="#c8c4bc" stroke="#808080" stroke-width="1"/>
  <text x="10" y="{H-9}" font-size="11" fill="#000" style="{mono}">Ready &#183; {followers} followers</text>
</svg>
'''


def main():
    user = fetch_user()
    avatar_url = user["avatar_url"]
    followers = user["followers"]

    contributions, days = (0, [])
    if TOKEN:
        try:
            contributions, days = fetch_calendar()
        except Exception as e:
            print(f"warning: contribution calendar fetch failed: {e}", file=sys.stderr)
    streak = longest_streak(days) if days else 0

    r = requests.get(avatar_url, timeout=20)
    r.raise_for_status()
    photo = Image.open(io.BytesIO(r.content)).convert("RGB")

    processed = vhs_effect(photo)
    svg = build_svg(processed, contributions, streak, followers)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        f.write(svg)
    print(f"wrote {OUT_PATH} ({len(svg)} bytes) | contributions={contributions} streak={streak} followers={followers}")


if __name__ == "__main__":
    main()
