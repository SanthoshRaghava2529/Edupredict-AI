"""Create a simple navy logo used by the desktop application."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import PROJECT_ROOT


def create_logo() -> Path:
    path = PROJECT_ROOT / "assets" / "images" / "logo.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (256, 256), "#0B1D36")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((28, 28, 228, 228), radius=36, outline="#3B82F6", width=8)
    draw.ellipse((78, 70, 178, 170), outline="#93C5FD", width=6)
    try:
        font = ImageFont.truetype("arial.ttf", 42)
    except OSError:
        font = ImageFont.load_default()
    draw.text((78, 175), "AI", fill="white", font=font)
    image.save(path)
    icon = image.resize((64, 64))
    icon_path = PROJECT_ROOT / "assets" / "icons" / "app_icon.png"
    icon.save(icon_path)
    return path


if __name__ == "__main__":
    print(create_logo())
