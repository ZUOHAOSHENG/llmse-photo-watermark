import argparse
import os
from pathlib import Path
from typing import Optional, Tuple, Iterable

from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageOps

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
EXIF_TAG_DATETIME_ORIGINAL = 36867  # DateTimeOriginal
EXIF_TAG_DATETIME = 306             # DateTime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="读取图片 EXIF 拍摄日期(年月日)作为水印绘制到图片上，输出到原目录名_watermark 子目录。"
    )
    parser.add_argument("path", help="图片文件或目录路径")
    parser.add_argument("--font-size", type=int, default=36, dest="font_size", help="字体大小(像素)，默认 36")
    parser.add_argument(
        "--color",
        type=str,
        default="#FFFFFF",
        help="水印颜色，支持颜色名(如 white)或十六进制(#RRGGBB 或 #AARRGGBB)，默认 #FFFFFF",
    )
    parser.add_argument(
        "--position",
        type=str,
        default="bottom-right",
        choices=[
            "top-left",
            "top-right",
            "center",
            "bottom-left",
            "bottom-right",
        ],
        help="水印位置，默认 bottom-right",
    )
    parser.add_argument(
        "--font-path",
        type=str,
        default=None,
        help="可选 TrueType 字体路径，例如 C:/Windows/Fonts/arial.ttf",
    )
    return parser.parse_args()


def is_image_file(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() in SUPPORTED_EXTS


def walk_images(root: Path) -> Iterable[Path]:
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            p = Path(dirpath) / name
            if is_image_file(p):
                yield p


def ensure_output_root(input_path: Path) -> Path:
    if input_path.is_file():
        base_dir = input_path.parent
    else:
        base_dir = input_path
    out_root = base_dir / f"{base_dir.name}_watermark"
    out_root.mkdir(parents=True, exist_ok=True)
    return out_root


def exif_date_text(img: Image.Image) -> Optional[str]:
    try:
        exif = img.getexif()
    except Exception:
        exif = None
    if not exif:
        return None
    raw = exif.get(EXIF_TAG_DATETIME_ORIGINAL) or exif.get(EXIF_TAG_DATETIME)
    if not raw:
        return None
    # EXIF DateTime format: "YYYY:MM:DD HH:MM:SS"
    try:
        s = str(raw)
        date_part = s.split(" ")[0]
        y, m, d = date_part.split(":")[:3]
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    except Exception:
        return None


def load_font(font_path: Optional[str], size: int) -> ImageFont.ImageFont:
    # 1) user provided
    if font_path:
        try:
            return ImageFont.truetype(font_path, size=size)
        except Exception:
            print(f"[警告] 无法加载字体: {font_path}，将尝试使用内置字体。")
    # 2) try Pillow's DejaVuSans
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except Exception:
        pass
    # 3) fallback default
    return ImageFont.load_default()


def parse_color(color: str) -> Tuple[int, int, int, int]:
    c = color.strip()
    # Support #AARRGGBB explicitly
    if c.startswith("#"):
        hexstr = c[1:]
        if len(hexstr) == 8:  # AARRGGBB
            try:
                a = int(hexstr[0:2], 16)
                r = int(hexstr[2:4], 16)
                g = int(hexstr[4:6], 16)
                b = int(hexstr[6:8], 16)
                return r, g, b, a
            except ValueError:
                pass
        elif len(hexstr) == 6:  # RRGGBB
            try:
                r = int(hexstr[0:2], 16)
                g = int(hexstr[2:4], 16)
                b = int(hexstr[4:6], 16)
                return r, g, b, 255
            except ValueError:
                pass
        # Fallback to Pillow parser
    try:
        rgba = ImageColor.getcolor(c, "RGBA")
        # ensure 4-tuple
        if len(rgba) == 3:
            rgba = (rgba[0], rgba[1], rgba[2], 255)
        return rgba  # type: ignore
    except Exception:
        print(f"[警告] 颜色 '{color}' 无法解析，使用白色。")
        return 255, 255, 255, 255


def calc_position(img_w: int, img_h: int, text_w: int, text_h: int, pos: str, margin: int = 10) -> Tuple[int, int]:
    if pos == "top-left":
        return margin, margin
    if pos == "top-right":
        return max(img_w - text_w - margin, margin), margin
    if pos == "center":
        return (img_w - text_w) // 2, (img_h - text_h) // 2
    if pos == "bottom-left":
        return margin, max(img_h - text_h - margin, margin)
    # bottom-right
    return max(img_w - text_w - margin, margin), max(img_h - text_h - margin, margin)


def draw_watermark(img: Image.Image, text: str, font: ImageFont.ImageFont, color_rgba: Tuple[int, int, int, int], position: str) -> Image.Image:
    # Ensure correct orientation
    img = ImageOps.exif_transpose(img)

    # Convert to RGBA for alpha-safe drawing, then back to original mode
    orig_mode = img.mode
    if img.mode != "RGBA":
        base = img.convert("RGBA")
    else:
        base = img.copy()

    txt_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt_layer)

    # Measure text size
    # Prefer textbbox for accurate size
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x, y = calc_position(base.width, base.height, text_w, text_h, position)

    # Optional soft shadow to improve readability
    shadow = (0, 0, 0, min(120, color_rgba[3]))
    for dx, dy in ((1, 1), (2, 2)):
        draw.text((x + dx, y + dy), text, font=font, fill=shadow)

    draw.text((x, y), text, font=font, fill=color_rgba)

    out = Image.alpha_composite(base, txt_layer)
    if orig_mode != "RGBA":
        out = out.convert(orig_mode)
    return out


def process_file(in_file: Path, out_root: Path, source_root: Path, font: ImageFont.ImageFont, color_rgba: Tuple[int, int, int, int], position: str) -> None:
    try:
        with Image.open(in_file) as im:
            text = exif_date_text(im)
            if not text:
                print(f"[跳过] 无 EXIF 日期: {in_file}")
                return
            out_img = draw_watermark(im, text, font, color_rgba, position)

            # Build output path relative to the provided source root
            try:
                rel_path = in_file.relative_to(source_root)
            except Exception:
                rel_path = Path(in_file.name)

            out_path = out_root / rel_path
            out_path.parent.mkdir(parents=True, exist_ok=True)

            save_kwargs = {}
            # try preserve original format
            fmt = (im.format or "PNG").upper()
            if fmt == "JPEG":
                save_kwargs.update({"quality": 95, "subsampling": 2})
            # Best effort keep EXIF except orientation to avoid double-rotation
            try:
                exif_bytes = im.info.get("exif")
                if exif_bytes and fmt in {"JPEG", "TIFF"}:
                    save_kwargs["exif"] = exif_bytes
            except Exception:
                pass

            out_path = out_path.with_suffix(in_file.suffix)
            out_img.save(out_path, format=fmt, **save_kwargs)
            print(f"[完成] {in_file} -> {out_path}")
    except Exception as e:
        print(f"[错误] 处理失败 {in_file}: {e}")


def main():
    args = parse_args()
    input_path = Path(args.path)
    if not input_path.exists():
        print(f"[错误] 路径不存在: {input_path}")
        return

    color_rgba = parse_color(args.color)
    font = load_font(args.font_path, args.font_size)

    out_root = ensure_output_root(input_path if input_path.is_dir() else input_path)

    if input_path.is_file():
        source_root = input_path.parent
        process_file(input_path, out_root, source_root, font, color_rgba, args.position)
    else:
        # directory: walk and mirror structure
        source_root = input_path
        count = 0
        for img_path in walk_images(input_path):
            process_file(img_path, out_root, source_root, font, color_rgba, args.position)
            count += 1
        if count == 0:
            print("[提示] 目录中未找到支持的图片文件。")


if __name__ == "__main__":
    main()
