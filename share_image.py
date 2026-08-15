import glob
import io
import os
import random

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1080, 1920
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")
BACKGROUNDS = sorted(glob.glob(os.path.join(BASE_DIR, "backgrounds", "*.jpg")))

SENDER_NAME = "Голос души"


def _load_background():
    path = random.choice(BACKGROUNDS)
    img = Image.open(path).convert("RGB")
    if img.size != (WIDTH, HEIGHT):
        img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)
    return img


def _add_bottom_scrim(img):
    """Тёмный градиент внизу — чтобы подпись бренда читалась на любом фото."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    scrim_height = 260
    for y in range(scrim_height):
        alpha = int(140 * (y / scrim_height))
        draw.line([(0, HEIGHT - scrim_height + y), (WIDTH, HEIGHT - scrim_height + y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), layer)


def _wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_share_image(phrase: str) -> io.BytesIO:
    img = _load_background()
    img = _add_bottom_scrim(img)
    draw = ImageDraw.Draw(img, "RGBA")

    font_regular = ImageFont.truetype(os.path.join(FONT_DIR, "PTSans-Regular.ttf"), 44)
    font_bold = ImageFont.truetype(os.path.join(FONT_DIR, "PTSans-Bold.ttf"), 38)
    font_small = ImageFont.truetype(os.path.join(FONT_DIR, "PTSans-Regular.ttf"), 28)
    font_avatar = ImageFont.truetype(os.path.join(FONT_DIR, "PTSans-Bold.ttf"), 36)
    font_brand = ImageFont.truetype(os.path.join(FONT_DIR, "PTSans-Regular.ttf"), 30)

    bubble_width = 920
    bubble_x = (WIDTH - bubble_width) // 2
    padding = 48
    text_max_width = bubble_width - padding * 2 - 20

    lines = _wrap_text(draw, phrase, font_regular, text_max_width)
    line_height = 58
    header_height = 80
    bubble_height = header_height + len(lines) * line_height + padding * 2

    bubble_y = (HEIGHT - bubble_height) // 2

    draw.rounded_rectangle(
        [bubble_x, bubble_y, bubble_x + bubble_width, bubble_y + bubble_height],
        radius=48,
        fill=(20, 20, 30, 230),
    )

    avatar_r = 34
    avatar_cx = bubble_x + padding + avatar_r
    avatar_cy = bubble_y + padding + avatar_r
    draw.ellipse(
        [avatar_cx - avatar_r, avatar_cy - avatar_r, avatar_cx + avatar_r, avatar_cy + avatar_r],
        fill=(240, 235, 245, 255),
    )
    letter = "А"
    letter_bbox = draw.textbbox((0, 0), letter, font=font_avatar)
    letter_w = letter_bbox[2] - letter_bbox[0]
    letter_h = letter_bbox[3] - letter_bbox[1]
    draw.text(
        (avatar_cx - letter_w / 2, avatar_cy - letter_h / 2 - letter_bbox[1]),
        letter,
        font=font_avatar,
        fill=(80, 70, 110, 255),
    )

    name_x = avatar_cx + avatar_r + 22
    draw.text((name_x, bubble_y + padding - 4), SENDER_NAME, font=font_bold, fill=(255, 255, 255, 255))

    now_text = "сейчас"
    now_w = draw.textlength(now_text, font=font_small)
    draw.text(
        (bubble_x + bubble_width - padding - now_w, bubble_y + padding + 2),
        now_text,
        font=font_small,
        fill=(200, 200, 210, 200),
    )

    text_y = bubble_y + padding + header_height
    for line in lines:
        draw.text((bubble_x + padding, text_y), line, font=font_regular, fill=(245, 245, 250, 255))
        text_y += line_height

    brand_text = "Голос души"
    brand_w = draw.textlength(brand_text, font=font_brand)
    draw.text(
        ((WIDTH - brand_w) / 2, HEIGHT - 140),
        brand_text,
        font=font_brand,
        fill=(60, 55, 70, 180),
    )

    buffer = io.BytesIO()
    buffer.name = "angel.png"
    img.convert("RGB").save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
