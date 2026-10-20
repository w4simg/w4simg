"""
Self-hosted GitHub profile views counter.
- Fetches real view counts from GitHub Traffic API
- Accumulates totals in profile/views-count.json
- Generates a styled SVG badge at profile/views.svg
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone


# ── Config ────────────────────────────────────────────────────────────────────

REPO        = os.environ.get("REPO", "w4simg/w4simg")
TOKEN       = os.environ.get("TRAFFIC_TOKEN", "")
COUNT_FILE  = "profile/views-count.json"
SVG_FILE    = "profile/views.svg"

# Badge colours (hex without #)
COLOR_LABEL = "1a1b27"   # dark background for label
COLOR_VALUE = "0078d7"   # accent blue for value
LABEL_TEXT  = "PROFILE VIEWS"


# ── Helpers ───────────────────────────────────────────────────────────────────

def gh_get(path: str) -> dict:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "profile-views-counter/1.0",
    })
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read())


def load_count() -> dict:
    os.makedirs("profile", exist_ok=True)
    try:
        with open(COUNT_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"total": 0, "seen_timestamps": [], "last_updated": None}


def save_count(data: dict) -> None:
    with open(COUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


# ── SVG generation ────────────────────────────────────────────────────────────

def _text_width(text: str, font_size: int = 10, bold: bool = True) -> int:
    """Rough pixel-width estimate for Verdana-like fonts."""
    # Average character widths at 10px bold (empirically tuned for for-the-badge style)
    narrow = set("iIl|!.,:;1 ")
    wide   = set("mMwW@")
    width  = 0
    ratio  = font_size / 10
    for ch in text:
        if ch in narrow:
            width += 5
        elif ch in wide:
            width += 12
        else:
            width += 7.5
    return int(width * ratio * (1.1 if bold else 1.0))


def generate_svg(count: int) -> str:
    value = f"{count:,}"

    font_size   = 10
    height      = 28
    pad         = 16          # horizontal padding per side
    label_w     = _text_width(LABEL_TEXT, font_size, bold=True) + pad * 2
    value_w     = _text_width(value, font_size, bold=True) + pad * 2
    total_w     = label_w + value_w

    label_mid   = label_w // 2
    value_mid   = label_w + value_w // 2
    text_y      = height // 2 + font_size // 2 - 1   # vertical centre

    # Shadow offset
    sh = text_y + 1

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{height}" role="img" aria-label="{LABEL_TEXT}: {value}">
  <title>{LABEL_TEXT}: {value}</title>
  <defs>
    <linearGradient id="g" x2="0" y2="100%">
      <stop offset="0"   stop-color="#fff" stop-opacity=".12"/>
      <stop offset="0.3" stop-color="#fff" stop-opacity=".04"/>
      <stop offset="1"   stop-color="#000" stop-opacity=".14"/>
    </linearGradient>
    <clipPath id="c">
      <rect width="{total_w}" height="{height}" rx="4"/>
    </clipPath>
  </defs>
  <g clip-path="url(#c)">
    <rect width="{label_w}" height="{height}" fill="#{COLOR_LABEL}"/>
    <rect x="{label_w}" width="{value_w}" height="{height}" fill="#{COLOR_VALUE}"/>
    <rect width="{total_w}" height="{height}" fill="url(#g)"/>
  </g>
  <g font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="{font_size}" font-weight="bold"
     text-anchor="middle" fill="#fff" letter-spacing="0.8">
    <text x="{label_mid}" y="{sh}" fill="#000" fill-opacity=".25">{LABEL_TEXT}</text>
    <text x="{label_mid}" y="{text_y}">{LABEL_TEXT}</text>
    <text x="{value_mid}" y="{sh}" fill="#000" fill-opacity=".25">{value}</text>
    <text x="{value_mid}" y="{text_y}">{value}</text>
  </g>
</svg>"""
    return svg


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    data = load_count()

    if TOKEN:
        try:
            traffic = gh_get(f"/repos/{REPO}/traffic/views")
            seen    = set(data.get("seen_timestamps", []))
            new     = 0

            for entry in traffic.get("views", []):
                ts = entry["timestamp"]
                if ts not in seen:
                    new += entry["count"]
                    seen.add(ts)

            # Prune old timestamps (keep last 300 to stay manageable)
            data["total"]            = data.get("total", 0) + new
            data["seen_timestamps"]  = sorted(seen)[-300:]
            data["last_updated"]     = datetime.now(timezone.utc).isoformat()

            print(f"Traffic API: +{new} new views → total = {data['total']}")

        except urllib.error.HTTPError as exc:
            print(f"Traffic API HTTP {exc.code}: {exc.reason} — keeping current count")
        except Exception as exc:
            print(f"Traffic API error: {exc} — keeping current count")
    else:
        print("TRAFFIC_TOKEN not set — keeping current count")

    save_count(data)

    svg = generate_svg(data["total"])
    with open(SVG_FILE, "w", encoding="utf-8") as f:
        f.write(svg)
        f.write("\n")

    print(f"SVG written to {SVG_FILE}  (count = {data['total']:,})")


if __name__ == "__main__":
    main()
