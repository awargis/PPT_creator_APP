from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def enhance(image: Image.Image, style="Premium Light") -> Image.Image:
    """Improve legibility without destroying mathematical symbols/diagrams."""
    result = ImageOps.exif_transpose(image).convert("RGB")
    result = ImageOps.autocontrast(result, cutoff=0.5)
    result = ImageEnhance.Contrast(result).enhance(1.06)
    result = ImageEnhance.Sharpness(result).enhance(1.18)

    if style == "High Contrast":
        result = ImageEnhance.Contrast(result).enhance(1.16)
        result = result.filter(ImageFilter.UnsharpMask(radius=1.0, percent=120, threshold=3))
    elif style == "Premium Dark":
        # Keep the original mathematical content readable; dark mode belongs
        # to the PPT template rather than thresholding the source question.
        result = ImageEnhance.Brightness(result).enhance(0.98)
    return result
