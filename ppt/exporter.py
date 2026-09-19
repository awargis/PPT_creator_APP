import io

from .slide_builder import build_slides


def export_subject_ppts(template_bytes, regions, answers, style="Premium Light"):
    """Build one PPTX per subject from the uploaded template."""
    result = {}
    active = [region for region in regions if getattr(region, "included", True) and region.image is not None]
    subjects = sorted({region.subject for region in active})
    for subject in subjects:
        selected = sorted(
            [region for region in active if region.subject == subject],
            key=lambda region: (region.number, region.page_index, region.box.y0),
        )
        if not selected:
            continue
        prs = build_slides(template_bytes, selected, answers, style=style)
        output = io.BytesIO()
        prs.save(output)
        data = output.getvalue()
        if len(data) < 1000:
            raise ValueError(f"Generated PPT for {subject} is unexpectedly small.")
        result[subject] = data
    return result
