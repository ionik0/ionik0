#!/usr/bin/env python3
"""
Build assets/kitten-pet.svg: the cut-out kitten photo (assets/kitten_source.png,
background already removed with OpenCV GrabCut) walking back and forth across
a horizontal strip - the same "lines" motion the old GitAnimals capybara had -
with a speech bubble cycling through a few one-liners.

One-shot build (no live data source), unlike scripts/build_avatar.py.
"""
import base64
import os

SRC = os.environ.get("KITTEN_SRC", "assets/kitten_source.png")
OUT = os.environ.get("KITTEN_OUT", "assets/kitten-pet.svg")

PHRASES = [
    "i can't code",
    "what bug is a debug?",
    "turn it off and on?",
    "404: motivation not found",
]

W, H = 900, 150
CAT_H = 96
BUBBLE_W, BUBBLE_H = 175, 24
GROUND_Y = 137


def text_animation(i, n, cycle_dur):
    """Opacity keyframes so exactly one phrase shows at a time, evenly split
    across `cycle_dur`, with a short crossfade between neighbors."""
    seg = 1 / n
    a, b = i * seg, (i + 1) * seg
    fade = 0.02
    if i == 0:
        keytimes = [0, a + seg - fade, b, 1]
        values = [1, 1, 0, 0]
    else:
        keytimes = [0, a, a + fade, b - fade, b, 1]
        values = [0, 0, 1, 1, 0, 0]
    kt = ";".join(f"{k:.4f}" for k in keytimes)
    vals = ";".join(str(v) for v in values)
    return (
        f'<animate attributeName="opacity" begin="0s" dur="{cycle_dur}s" '
        f'repeatCount="indefinite" calcMode="linear" keyTimes="{kt}" values="{vals}"/>'
    )


def main():
    with open(SRC, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    from PIL import Image
    src_w, src_h = Image.open(SRC).size
    cat_w = round(CAT_H * src_w / src_h)

    bubble_w, bubble_h = BUBBLE_W, BUBBLE_H
    bubble_overflow = max(0, (bubble_w - cat_w) / 2) + 8
    walk_min = max(20, bubble_overflow)
    walk_max = min(W - cat_w - 20, W - cat_w - bubble_overflow)
    walk_dur = 16
    speech_cycle = 12

    bubble_x = cat_w / 2 - bubble_w / 2
    bubble_y = -38

    texts = []
    for i, phrase in enumerate(PHRASES):
        anim = text_animation(i, len(PHRASES), speech_cycle)
        texts.append(
            f'<text x="{cat_w/2}" y="{bubble_y + bubble_h/2 + 4}" '
            f'text-anchor="middle" font-size="10" font-family="Courier New,monospace" '
            f'fill="#1f2328" opacity="0">{phrase}{anim}</text>'
        )
    texts_svg = "\n    ".join(texts)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <line x1="0" y1="{GROUND_Y}" x2="{W}" y2="{GROUND_Y}" stroke="#d0d7de" stroke-width="1" stroke-dasharray="4 4"/>

  <g>
    <animateTransform attributeName="transform" type="translate"
      dur="{walk_dur}s" repeatCount="indefinite"
      keyTimes="0;0.5;1" values="{walk_min},{GROUND_Y-CAT_H};{walk_max},{GROUND_Y-CAT_H};{walk_min},{GROUND_Y-CAT_H}"/>

    <g>
      <rect x="{bubble_x}" y="{bubble_y}" width="{bubble_w}" height="{bubble_h}" rx="10"
        fill="#ffffff" stroke="#1f2328" stroke-width="1.5"/>
      <polygon points="{cat_w/2-6},{bubble_y+bubble_h} {cat_w/2+6},{bubble_y+bubble_h} {cat_w/2},{bubble_y+bubble_h+8}"
        fill="#ffffff" stroke="#1f2328" stroke-width="1.5"/>
      <rect x="{cat_w/2-6}" y="{bubble_y+bubble_h-1}" width="12" height="2" fill="#ffffff"/>
      {texts_svg}
    </g>

    <g>
      <animateTransform attributeName="transform" type="translate"
        dur="0.5s" repeatCount="indefinite"
        keyTimes="0;0.5;1" values="0,0;0,-4;0,0"/>
      <image x="0" y="0" width="{cat_w}" height="{CAT_H}" href="data:image/png;base64,{b64}"/>
    </g>
  </g>
</svg>
'''

    with open(OUT, "w") as f:
        f.write(svg)
    print(f"wrote {OUT} ({len(svg)} bytes), cat {cat_w}x{CAT_H}")


if __name__ == "__main__":
    main()
