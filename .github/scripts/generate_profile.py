#!/usr/bin/env python3
import html
import json
import random
from collections import deque
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[2]
WIDTH = 1180
HEIGHT = 610
PIXEL_COLUMNS = 144
PIXEL_ROWS = 190
DOT_STEP = 1.88
DOT_SIZE = 1.16
PALETTES = {
    "dark": {
        "background": "#080D19",
        "panel": "#0A101F",
        "text": "#F8FAFC",
        "muted": "#94A3B8",
        "dim": "#64748B",
        "leader": "#334155",
        "cyan": "#22D3EE",
        "violet": "#A78BFA",
        "violet_dark": "#7C3AED",
        "emerald": "#10B981",
        "frame": "#22D3EE",
    },
    "light": {
        "background": "#F8FAFC",
        "panel": "#FFFFFF",
        "text": "#0F172A",
        "muted": "#475569",
        "dim": "#64748B",
        "leader": "#CBD5E1",
        "cyan": "#0891B2",
        "violet": "#7C3AED",
        "violet_dark": "#6D28D9",
        "emerald": "#059669",
        "frame": "#0891B2",
    },
}


def escape(value):
    return html.escape(str(value), quote=True)


def flat_background_mask(image):
    pixels = image.load()
    width, height = image.size
    corner_size = max(4, min(width, height) // 12)
    corners = []
    for left, top in (
        (0, 0),
        (width - corner_size, 0),
        (0, height - corner_size),
        (width - corner_size, height - corner_size),
    ):
        samples = [
            pixels[x, y]
            for y in range(top, top + corner_size)
            for x in range(left, left + corner_size)
        ]
        corners.append(
            tuple(sum(color[channel] for color in samples) / len(samples) for channel in range(3))
        )
    background = tuple(
        sum(corner[channel] for corner in corners) / len(corners) for channel in range(3)
    )
    if max(
        sum((corner[channel] - background[channel]) ** 2 for channel in range(3)) ** 0.5
        for corner in corners
    ) > 38:
        return None

    raw_mask = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            color = pixels[x, y]
            distance = sum((color[channel] - background[channel]) ** 2 for channel in range(3)) ** 0.5
            raw_mask[y * width + x] = 255 if distance > 58 else 0
    mask_image = Image.frombytes("L", image.size, bytes(raw_mask))
    mask_image = mask_image.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    mask = [value >= 128 for value in mask_image.tobytes()]

    def flood_fill(seed_points, target, replacement, visited):
        queue = deque(seed_points)
        while queue:
            index = queue.popleft()
            if visited[index] or mask[index] != target:
                continue
            visited[index] = True
            mask[index] = replacement
            x = index % width
            y = index // width
            if x:
                queue.append(index - 1)
            if x + 1 < width:
                queue.append(index + 1)
            if y:
                queue.append(index - width)
            if y + 1 < height:
                queue.append(index + width)

    border = list(range(width)) + list(range((height - 1) * width, height * width))
    border.extend(y * width for y in range(height))
    border.extend(y * width + width - 1 for y in range(height))
    background_visited = [False] * (width * height)
    flood_fill(border, False, False, background_visited)
    mask = [foreground or not background_visited[index] for index, foreground in enumerate(mask)]

    largest_component = []
    visited = [False] * (width * height)
    for index, foreground in enumerate(mask):
        if not foreground or visited[index]:
            continue
        component = []
        queue = deque([index])
        visited[index] = True
        while queue:
            current = queue.popleft()
            component.append(current)
            x = current % width
            y = current // width
            for neighbor in (
                current - 1 if x else -1,
                current + 1 if x + 1 < width else -1,
                current - width if y else -1,
                current + width if y + 1 < height else -1,
            ):
                if neighbor >= 0 and mask[neighbor] and not visited[neighbor]:
                    visited[neighbor] = True
                    queue.append(neighbor)
        if len(component) > len(largest_component):
            largest_component = component
    if len(largest_component) < width * height // 20:
        return None
    foreground = bytearray(width * height)
    for index in largest_component:
        foreground[index] = 1
    return foreground


def portrait_paths(source, remove_flat_background, fallback_mask=None):
    image = Image.open(source).convert("RGB")
    image = ImageOps.fit(
        image,
        (PIXEL_COLUMNS, PIXEL_ROWS),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.45),
    )
    grayscale = ImageOps.autocontrast(ImageOps.grayscale(image), cutoff=1)
    grayscale = ImageEnhance.Contrast(grayscale).enhance(1.3)
    grayscale = grayscale.filter(
        ImageFilter.UnsharpMask(radius=3, percent=140, threshold=3)
    )
    dithered = grayscale.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    mask = flat_background_mask(image) if remove_flat_background else None
    if mask is None and remove_flat_background and fallback_mask:
        mask_image = Image.new("L", image.size)
        ImageDraw.Draw(mask_image).polygon(fallback_mask, fill=1)
        mask = mask_image.tobytes()
    foreground_points = (
        [
            (index % PIXEL_COLUMNS, index // PIXEL_COLUMNS)
            for index, value in enumerate(mask)
            if value
        ]
        if mask is not None
        else []
    )
    if foreground_points:
        min_x = min(point[0] for point in foreground_points)
        max_x = max(point[0] for point in foreground_points)
        min_y = min(point[1] for point in foreground_points)
        max_y = max(point[1] for point in foreground_points)
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
    paths = []
    for y in range(PIXEL_ROWS):
        for x in range(PIXEL_COLUMNS):
            if dithered.getpixel((x, y)) == 0 and (
                mask is None or mask[y * PIXEL_COLUMNS + x]
            ):
                if foreground_points:
                    px = 243 + (x - center_x) * 3.6
                    py = 326 + (y - center_y) * 3.2
                else:
                    px = 87 + x * DOT_STEP
                    py = 104 + y * DOT_STEP
                paths.append(
                    f"M{px:.1f} {py:.1f}h{DOT_SIZE}v{DOT_SIZE}h-{DOT_SIZE}z"
                )
    return paths


def portrait_markup(paths, theme):
    color = PALETTES[theme]["violet"]
    shuffled = list(paths)
    random.Random(20261020).shuffle(shuffled)
    count = 36
    groups = [[] for _ in range(count)]
    for index, path in enumerate(shuffled):
        groups[index % count].append(path)
    markup = []
    for index, group in enumerate(groups):
        delay = index * 0.035
        path_data = "".join(group)
        markup.append(
            f'<path fill="{color}" opacity="0" shape-rendering="crispEdges" '
            f'd="{path_data}"><animate attributeName="opacity" from="0" to="1" '
            f'dur="1.7s" begin="{delay:.3f}s" fill="freeze"/></path>'
        )
    return "\n".join(markup)


def banner(profile, paths, theme):
    colors = PALETTES[theme]
    username = escape(profile["username"])
    full_name = escape(profile["name"])
    role = escape(profile["role"])
    email = escape(profile["email"])
    details = [
        ("Subject", profile["name"]),
        ("Role", profile["role"]),
        ("Company", profile["company"]),
        ("Project", f'{profile["client"]} · Global Law Firm'),
        ("Origin", f'{profile["location"]}  🇮🇳'),
        ("Status", "Building · Learning · Shipping"),
        ("ToolChain", "VS Code · Git · AI"),
        ("Core.Lang", ", ".join(profile["languages"])),
        ("Core.Frontend", ", ".join(profile["frontend"])),
        ("Core.Backend", "AEM · Java · .NET"),
        ("Core.Database", "SQL · Supabase"),
        ("Core.Infra", "Git · Netlify"),
        ("Grid.Mail", profile["email"]),
        ("Grid.Portfolio", profile["portfolio"]),
        ("Grid.LinkedIn", profile["linkedin"]),
        ("Grid.GitHub", f'@{profile["username"]}'),
    ]
    row_start = 165
    row_spacing = 23
    rows = []
    for index, (label, value) in enumerate(details):
        y = row_start + index * row_spacing
        label_width = max(68, len(label) * 8)
        leader_start = 490 + label_width
        value_width = min(470, max(115, len(value) * 7.45))
        value_start = WIDTH - 46 - value_width
        rows.append(
            f'<text x="490" y="{y}" fill="{colors["cyan"]}" font-size="13">{escape(label)}</text>'
            f'<path d="M{leader_start} {y - 4}H{value_start - 15}" stroke="{colors["leader"]}" '
            f'stroke-width="1.5" stroke-dasharray="1 5"/>'
            f'<text x="{WIDTH - 46}" y="{y}" text-anchor="end" textLength="{value_width:.0f}" '
            f'lengthAdjust="spacingAndGlyphs" fill="{colors["text"]}" font-size="14" '
            f'font-weight="600">{escape(value)}</text>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">
<title id="title">{full_name} — {role}</title>
<desc id="desc">A terminal-style pixel portrait profile with Shashank's skills, location, work, projects and contact details.</desc>
<defs>
  <linearGradient id="background" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{colors["background"]}"/><stop offset="1" stop-color="{colors["panel"]}"/></linearGradient>
  <linearGradient id="frame" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{colors["cyan"]}"/><stop offset="1" stop-color="{colors["violet_dark"]}"/></linearGradient>
  <clipPath id="portrait"><rect x="56" y="99" width="374" height="454" rx="7"/></clipPath>
  <style>
    @keyframes blink {{ 50% {{ opacity: .25; }} }}
    .live-dot {{ animation: blink 1.2s ease-in-out infinite; }}
  </style>
</defs>
<rect width="{WIDTH}" height="{HEIGHT}" rx="20" fill="url(#background)"/>
<rect x="1" y="1" width="{WIDTH - 2}" height="{HEIGHT - 2}" rx="19" fill="none" stroke="{colors["leader"]}"/>
<g font-family="SFMono-Regular,Consolas,'Liberation Mono',monospace">
  <circle cx="37" cy="34" r="6" fill="#FB7185"/><circle cx="58" cy="34" r="6" fill="#FBBF24"/><circle cx="79" cy="34" r="6" fill="#34D399"/>
  <text x="101" y="39" fill="{colors["muted"]}" font-size="14" letter-spacing="1">profile.sh --live</text>
  <text x="1138" y="39" text-anchor="end" fill="{colors["dim"]}" font-size="12">{username}  /  MAIN</text>
  <path d="M27 65H1153" stroke="{colors["leader"]}"/>
  <text x="58" y="88" fill="{colors["dim"]}" font-size="10" letter-spacing="2">VISUAL.MAP</text>
  <rect x="43" y="95" width="400" height="468" rx="11" fill="{colors["panel"]}" stroke="url(#frame)" stroke-width="1.5"/>
  <path d="M56 124V109Q56 99 66 99H86M430 124V109Q430 99 420 99H400M56 526V543Q56 553 66 553H86M430 526V543Q430 553 420 553H400" fill="none" stroke="{colors["frame"]}" stroke-width="2"/>
  <g clip-path="url(#portrait)" transform="translate(-5 -4)">
    {portrait_markup(paths, theme)}
  </g>
  <text x="161" y="580" text-anchor="middle" fill="{colors["dim"]}" font-size="10" letter-spacing="1">FLOYD–STEINBERG</text>
  <g text-anchor="middle" font-size="10" font-weight="700" letter-spacing="1">
    <text x="345" y="580" fill="{colors["violet"]}" opacity="0">AEM<animate attributeName="opacity" values="1;0;0;1" keyTimes="0;.34;.67;1" calcMode="discrete" dur="6s" repeatCount="indefinite"/></text>
    <text x="345" y="580" fill="{colors["cyan"]}" opacity="0">JAVA<animate attributeName="opacity" values="0;1;0;0" keyTimes="0;.34;.67;1" calcMode="discrete" dur="6s" repeatCount="indefinite"/></text>
    <text x="345" y="580" fill="{colors["emerald"]}" opacity="0">.NET<animate attributeName="opacity" values="0;0;1;0" keyTimes="0;.34;.67;1" calcMode="discrete" dur="6s" repeatCount="indefinite"/></text>
  </g>
  <text x="490" y="91" fill="{colors["cyan"]}" font-size="13" font-weight="700" letter-spacing="1.5">SYSTEM.INFO</text>
  <path d="M600 86H1087" stroke="{colors["leader"]}" opacity=".7"/>
  <circle class="live-dot" cx="1105" cy="86" r="4" fill="#FB7185"/>
  <text x="1117" y="90" fill="{colors["dim"]}" font-size="11">LIVE</text>
  <rect x="490" y="105" width="270" height="24" rx="4" fill="{colors["violet_dark"]}" fill-opacity=".78"/>
  <text x="500" y="122" fill="#FFFFFF" font-size="13" font-weight="700">{email}</text>
  {"".join(rows)}
  <path d="M490 557H1138" stroke="{colors["leader"]}"/>
  <text x="490" y="581" fill="{colors["muted"]}" font-size="12">Projects, activity &amp; links below in README</text>
  <rect x="792" y="570" width="7" height="13" rx="1" fill="{colors["cyan"]}" class="live-dot"/>
</g>
</svg>"""


def main():
    profile_path = ROOT / "profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    avatar = ROOT / profile["avatar"]
    for theme in PALETTES:
        paths = portrait_paths(
            avatar,
            remove_flat_background=True,
            fallback_mask=profile.get("avatar_mask_polygon"),
        )
        output = ROOT / f"profile-{theme}.svg"
        output.write_text(banner(profile, paths, theme), encoding="utf-8")
        print(f"Generated {output.name} from {avatar.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
