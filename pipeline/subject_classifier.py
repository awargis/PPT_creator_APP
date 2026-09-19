"""Subject classification using explicit section headers first, numbering second."""

from services.subject_service import normalize_subject


def _key(obj):
    return (obj.page_index, 99 if obj.column_index == -1 else obj.column_index, obj.box.y0, obj.box.x0)


def classify_subjects(regions, headers, known_subjects, exam_type):
    headers = sorted(headers or [], key=_key)
    regions = sorted(regions, key=lambda r: (r.page_index, 99 if r.column_index == -1 else r.column_index, r.box.y0, r.box.x0))

    # Explicit section headers are authoritative. For this sample:
    # Physics = Q1-25, Chemistry = Q26-50, Mathematics = Q51-75.
    header_events = []
    for h in headers:
        subject = normalize_subject(h.text, known_subjects)
        if subject:
            # Header ordering is page/vertical, not column ordering.
            header_events.append(((h.page_index, h.box.y0, h.box.x0), subject))

    reset_mode = False
    if exam_type == "JEE Main" and not header_events:
        nums = [r.number for r in regions]
        reset_mode = any(b < a for a, b in zip(nums, nums[1:]))

    for idx, region in enumerate(regions):
        pos = (region.page_index, region.box.y0, region.box.x0)
        subject = None
        for hpos, hsubject in header_events:
            if hpos <= pos:
                subject = hsubject
            else:
                break

        # Strong deterministic fallback for JEE Main/NEET when a section header
        # is missing or extraction of a header failed.
        if subject is None:
            if exam_type == "JEE Main":
                if reset_mode:
                    block_index = 0
                    if idx:
                        resets = sum(1 for a, b in zip([r.number for r in regions[:idx]], [r.number for r in regions[1:idx+1]]) if b < a)
                        block_index = resets
                    subject = ["Physics", "Chemistry", "Mathematics"][min(block_index, 2)]
                else:
                    subject = "Physics" if region.number <= 25 else "Chemistry" if region.number <= 50 else "Mathematics"
            elif exam_type == "NEET UG":
                subject = ("Physics" if region.number <= 45 else "Chemistry" if region.number <= 90 else "Botany" if region.number <= 135 else "Zoology")

        region.subject = subject if subject in known_subjects else "Unclassified"
        region.needs_review = region.subject == "Unclassified"
    return regions
