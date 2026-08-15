import io
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT = 1080, 1920
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

GRADIENTS = [
    ((255, 214, 186), (214, 189, 255)),  # персик -> лаванда
    ((186, 214, 255), (255, 202, 212)),  # пыльный синий -> розовый
    ((255, 236, 210), (255, 183, 197)),  # кремовый -> коралловый
    ((205, 232, 210), (255, 245, 224)),  # шалфей -> кремовый
]

SENDER_NAME = "Твой ангел-хранитель"


def _vertical_gradient(size, top_color, bottom_color):
    width, height = size
    base = Image.new("RGB", size, top_color)
    draw = ImageDraw.Draw(base)
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return base


def _add_bokeh(img, top_color, bottom_color):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    palette = [top_color, bottom_color, (255, 255, 255)]
    for _ in range(6):
        color = random.choice(palette)
        r = random.randint(120, 320)
        cx = random.randint(0, WIDTH)
        cy = random.randint(0, HEIGHT)
        alpha = random.randint(50, 110)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(80))
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
    top_color, bottom_color = random.choice(GRADIENTS)
    img = _vertical_gradient((WIDTH, HEIGHT), top_color, bottom_color)
    img = _add_bokeh(img, top_color, bottom_color)
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

    brand_text = "Твой ангел-хранитель"
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
