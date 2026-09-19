from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import numpy as np


def _remove_paper_background(image: Image.Image) -> Image.Image:
    """Make near-white paper transparent while preserving text/diagrams.

    This is intentionally conservative: only low-saturation, very bright
    pixels are removed. Colored diagrams and light mathematical marks remain.
    """
    rgb = image.convert("RGB")
    arr = np.asarray(rgb).astype(np.uint8)
    mx = arr.max(axis=2)
    mn = arr.min(axis=2)
    spread = mx.astype(np.int16) - mn.astype(np.int16)
    luminance = (
        0.299 * arr[:, :, 0]
        + 0.587 * arr[:, :, 1]
        + 0.114 * arr[:, :, 2]
    )

    # Fully remove white paper; feather the boundary so anti-aliased text
    # remains visually clean instead of getting jagged.
    alpha = np.where(
        (luminance >= 248) & (spread <= 10),
        0,
        np.where(
            (luminance >= 232) & (spread <= 16),
            ((248 - luminance) / 16 * 255).clip(20, 255),
            255,
        ),
    ).astype(np.uint8)

    rgba = np.dstack([arr, alpha])
    result = Image.fromarray(rgba, "RGBA")

    # Remove transparent outer margins. This makes the question occupy the
    # PPT placeholder instead of carrying a large invisible page rectangle.
    bbox = result.getbbox()
    if bbox:
        result = result.crop(bbox)
    return result


def enhance(image: Image.Image, style="Premium Light") -> Image.Image:
    """Improve legibility and remove paper background without altering content."""
    result = ImageOps.exif_transpose(image).convert("RGB")
    result = ImageOps.autocontrast(result, cutoff=0.5)
    result = ImageEnhance.Contrast(result).enhance(1.10)
    result = ImageEnhance.Sharpness(result).enhance(1.22)

    if style == "High Contrast":
        result = ImageEnhance.Contrast(result).enhance(1.16)
        result = result.filter(ImageFilter.UnsharpMask(radius=1.0, percent=120, threshold=3))
    elif style == "Premium Dark":
        result = ImageEnhance.Brightness(result).enhance(0.98)

    return _remove_paper_background(result)
