#!/usr/bin/env python3
import html
import json
import math
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WIDTH = 1180
CARD_WIDTH = 570
CARD_HEIGHT = 210
GAP = 16
THEMES = {
    "dark": {
        "background": "#0A101F",
        "panel": "#0C1426",
        "bar": "#0B1222",
        "cyan": "#22D3EE",
        "violet": "#A78BFA",
        "green": "#10B981",
        "text": "#F8FAFC",
        "muted": "#94A3B8",
        "dim": "#64748B",
        "stroke": "#334155",
        "pill": "#211B3C",
    },
    "light": {
        "background": "#F8FAFC",
        "panel": "#FFFFFF",
        "bar": "#F1F5F9",
        "cyan": "#0891B2",
        "violet": "#7C3AED",
        "green": "#059669",
        "text": "#0F172A",
        "muted": "#475569",
        "dim": "#64748B",
        "stroke": "#CBD5E1",
        "pill": "#F3E8FF",
    },
}
LANGUAGE_COLORS = ["#A78BFA", "#22D3EE", "#10B981", "#F472B6"]


def esc(value):
    return html.escape(str(value), quote=True)


def updated_label(value):
    if not value:
        return "activity data unavailable"
    try:
        pushed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        elapsed = datetime.now(timezone.utc) - pushed
    except ValueError:
        return "activity data unavailable"
    if elapsed.days >= 365:
        return f"updated {elapsed.days // 365}y ago"
    if elapsed.days >= 30:
        return f"updated {elapsed.days // 30}mo ago"
    if elapsed.days:
        return f"updated {elapsed.days}d ago"
    hours = elapsed.seconds // 3600
    return f"updated {hours}h ago" if hours else "updated today"


def is_recent(value):
    if not value:
        return False
    try:
        pushed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return (datetime.now(timezone.utc) - pushed).days <= 14


def language_bar(project, x, y, theme):
    languages = project.get("languages") or {}
    ordered = sorted(
        ((name, amount) for name, amount in languages.items() if amount > 0),
        key=lambda item: item[1],
        reverse=True,
    )[:4]
    if not ordered:
        return f'<text x="{x}" y="{y + 4}" fill="{theme["dim"]}" font-size="11">Language data unavailable</text>'
    total = sum(amount for _, amount in ordered)
    bar_width = 320
    markup = []
    cursor = x
    for index, (name, amount) in enumerate(ordered):
        width = bar_width * amount / total
        markup.append(
            f'<rect x="{cursor:.1f}" y="{y}" width="{width:.1f}" height="7" '
            f'rx="3.5" fill="{LANGUAGE_COLORS[index % len(LANGUAGE_COLORS)]}"/>'
        )
        cursor += width
    legends = []
    for index, (name, amount) in enumerate(ordered[:3]):
        percentage = amount / total * 100
        legends.append(
            f'<circle cx="{x + index * 110}" cy="{y + 28}" r="4" fill="{LANGUAGE_COLORS[index]}"/>'
            f'<text x="{x + index * 110 + 11}" y="{y + 32}" fill="{theme["muted"]}" '
            f'font-size="10">{esc(name)} {percentage:.0f}%</text>'
        )
    return "".join(markup + legends)


def card(project, index, x, y, theme):
    repo = esc(project["repo"])
    name = esc(project["name"])
    description = project.get("description", "")
    description_lines = textwrap.wrap(description, width=59, max_lines=2, placeholder="…")
    tags = project.get("tags", [])[:3]
    initials = esc("".join(word[0] for word in project["name"].split()[:2]).upper())
    tag_markup = []
    tag_x = x + 77
    for tag in tags:
        width = max(62, len(tag) * 7 + 18)
        tag_markup.append(
            f'<rect x="{tag_x}" y="112" width="{width}" height="21" rx="10" fill="{theme["pill"]}" '
            f'stroke="{theme["violet"]}" stroke-opacity=".5"/>'
            f'<text x="{tag_x + width / 2}" y="126" text-anchor="middle" '
            f'fill="{theme["violet"]}" font-size="10">{esc(tag)}</text>'
        )
        tag_x += width + 9
    link = project.get("homepage", "")
    recently_updated = is_recent(project.get("pushed_at"))
    status_color = theme["green"] if recently_updated else theme["dim"]
    status_animation = (
        '<animate attributeName="opacity" values="1;.35;1" dur="2.2s" repeatCount="indefinite"/>'
        if recently_updated
        else ""
    )
    return f"""<g transform="translate({x} {y})">
  <rect width="{CARD_WIDTH}" height="{CARD_HEIGHT}" rx="13" fill="{theme["panel"]}" stroke="{theme["stroke"]}"/>
  <path d="M13 1H{CARD_WIDTH - 13}" stroke="{theme["cyan"]}" stroke-opacity=".6"/>
  <rect x="1" y="1" width="{CARD_WIDTH - 2}" height="32" rx="12" fill="{theme["bar"]}"/>
  <path d="M1 20V32H{CARD_WIDTH - 1}V20" fill="{theme["bar"]}"/>
  <path d="M1 33H{CARD_WIDTH - 1}" stroke="{theme["stroke"]}" stroke-opacity=".55"/>
  <text x="16" y="21" fill="{theme["muted"]}" font-size="10">PROJECT.{index + 1}  /  {repo}</text>
  <circle cx="{CARD_WIDTH - 18}" cy="16" r="4" fill="{status_color}">{status_animation}</circle>
  <rect x="18" y="51" width="44" height="44" rx="10" fill="{theme["violet"]}" fill-opacity=".18" stroke="{theme["violet"]}" stroke-opacity=".7"/>
  <text x="40" y="79" text-anchor="middle" fill="{theme["violet"]}" font-size="17" font-weight="700">{initials}</text>
  <text x="77" y="62" fill="{theme["text"]}" font-size="17" font-weight="700">{name}</text>
  <text x="77" y="85" fill="{theme["muted"]}" font-size="11">{esc(description_lines[0] if description_lines else "")}</text>
  <text x="77" y="101" fill="{theme["muted"]}" font-size="11">{esc(description_lines[1] if len(description_lines) > 1 else "")}</text>
  {"".join(tag_markup)}
  <text x="18" y="151" fill="{theme["muted"]}" font-size="10"><tspan fill="{theme["cyan"]}">★</tspan> {project.get("stars", 0)}  ·  {esc(updated_label(project.get("pushed_at")))}</text>
  {language_bar(project, 232, 165, theme)}
  {f'<text x="{CARD_WIDTH - 16}" y="190" text-anchor="end" fill="{theme["cyan"]}" font-size="10">LIVE ↗</text>' if link else ""}
</g>"""


def build(projects, theme_name):
    theme = THEMES[theme_name]
    rows = math.ceil(len(projects) / 2)
    height = 55 + rows * (CARD_HEIGHT + GAP) + 4
    cards = []
    for index, project in enumerate(projects):
        row, column = divmod(index, 2)
        x = 6 + column * (CARD_WIDTH + GAP)
        y = 42 + row * (CARD_HEIGHT + GAP)
        cards.append(card(project, index, x, y, theme))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-labelledby="title desc">
<title id="title">Shashank's featured projects</title>
<desc id="desc">Live GitHub details for the SSB Portfolio and Wolf Journal projects.</desc>
<rect width="{WIDTH}" height="{height}" rx="12" fill="{theme["background"]}"/>
<text x="8" y="24" fill="{theme["cyan"]}" font-family="monospace" font-size="12" letter-spacing="2">PROJECTS.LIST</text>
<text x="178" y="24" fill="{theme["dim"]}" font-family="monospace" font-size="10">./projects.sh --featured</text>
<circle cx="1165" cy="20" r="4" fill="{theme["green"]}"><animate attributeName="opacity" values="1;.35;1" dur="2s" repeatCount="indefinite"/></circle>
<g font-family="SFMono-Regular,Consolas,'Liberation Mono',monospace">{"".join(cards)}</g>
</svg>"""


def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "merged-projects.json"
    destination = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "out"
    if not source.is_absolute():
        source = ROOT / source
    if not destination.is_absolute():
        destination = ROOT / destination
    projects = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(projects, list) or len(projects) != 2:
        raise ValueError("The featured-project panel must contain exactly two projects")
    destination.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        output = destination / f"projects-{theme}.svg"
        output.write_text(build(projects, theme), encoding="utf-8")
        print(f"Generated {output}")


if __name__ == "__main__":
    main()
