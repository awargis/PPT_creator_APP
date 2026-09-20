"""Premium question-image cleanup for dark presentation templates.

The source question is never re-rendered as typed text. The original PDF
raster is retained, then cleaned and made presentation-ready. When the page
background is made transparent, neutral dark mathematical text/lines are
recolored to a bright foreground so they remain readable on a dark PPT slide.
"""

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def remove_white_background(image: Image.Image, white_threshold: int = 248) -> Image.Image:
    rgb = np.array(image.convert("RGB"))
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    neutral = (maxc - minc) <= 10
    white = neutral & (minc >= white_threshold)

    alpha = np.full(rgb.shape[:2], 255, dtype=np.uint8)
    grey = rgb.mean(axis=2)

    # Fade only neutral light paper/watermark pixels. This removes the grey
    # institutional watermark while keeping dark text and diagrams opaque.
    fade = neutral & (grey >= 95)
    alpha[fade] = np.clip((125 - grey[fade]) * 8.0, 0, 255).astype(np.uint8)
    alpha[white] = 0

    return Image.fromarray(np.dstack([rgb, alpha]), "RGBA")


def recolor_dark_neutral_foreground(
    image: Image.Image,
    foreground=(255, 255, 255),
    threshold=165,
) -> Image.Image:
    """Turn dark neutral source text/lines into a bright slide foreground.

    PDF questions are normally black/dark-grey on white. After removing the
    white page, those pixels must not stay black because the production
    template uses a dark graphite background. Only neutral pixels are changed;
    coloured diagrams/illustrations are preserved.
    """
    rgba = np.array(image.convert("RGBA"))
    rgb = rgba[:, :, :3].astype(np.float32)
    alpha = rgba[:, :, 3]

    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    grey = rgb.mean(axis=2)
    neutral = (maxc - minc) <= 14
    dark = neutral & (grey < threshold) & (alpha > 0)

    # Preserve anti-aliased edges by using the original darkness to control
    # opacity. Fully dark glyphs remain solid; lighter anti-alias pixels fade.
    strength = np.clip((threshold - grey) / max(1, threshold - 45), 0.0, 1.0)
    alpha2 = alpha.copy().astype(np.float32)
    alpha2[dark] = np.maximum(alpha2[dark].astype(np.float32), 255.0 * strength[dark])

    for channel, value in enumerate(foreground):
        channel_data = rgba[:, :, channel]
        channel_data[dark] = value
        rgba[:, :, channel] = channel_data

    rgba[:, :, 3] = np.clip(alpha2, 0, 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def enhance(
    image: Image.Image,
    style: str = "Premium Light",
    transparent_background: bool = True,
) -> Image.Image:
    """Create a crisp presentation-ready question crop."""
    result = ImageOps.exif_transpose(image).convert("RGB")
    result = ImageOps.autocontrast(result, cutoff=0.35)
    result = ImageEnhance.Contrast(result).enhance(1.08)
    result = ImageEnhance.Sharpness(result).enhance(1.20)

    if style == "High Contrast":
        result = ImageEnhance.Contrast(result).enhance(1.18)
        result = result.filter(
            ImageFilter.UnsharpMask(radius=1.0, percent=125, threshold=3)
        )
    elif style == "Premium Dark":
        result = ImageEnhance.Contrast(result).enhance(1.04)

    if transparent_background:
        result = remove_white_background(result)
        # White is the safest default on the supplied graphite template. The
        # visual answer badge below uses orange as the accent colour.
        result = recolor_dark_neutral_foreground(result, foreground=(255, 255, 255))
        return result
    return result
