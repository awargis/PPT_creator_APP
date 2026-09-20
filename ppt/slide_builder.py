import copy
import io

from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

from .layout_engine import find_image_placeholder, fit_box
from .template_validator import validate_template

RELATIONSHIP_NAMESPACE = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
ANSWER_ORANGE = RGBColor(255, 166, 64)
ANSWER_WHITE = RGBColor(255, 255, 255)
ANSWER_DARK = RGBColor(11, 15, 22)


def _duplicate_slide(prs, source_index=0):
    source = prs.slides[source_index]
    target = prs.slides.add_slide(source.slide_layout)

    # python-pptx does not copy slide-level background formatting when a slide
    # is cloned. The supplied premium template uses a graphite background;
    # copy the source <p:bg> element explicitly or the new slides fall back to
    # white and the transparent white question text disappears.
    source_c_sld = source._element.cSld
    target_c_sld = target._element.cSld
    source_bg = source_c_sld.find("{http://schemas.openxmlformats.org/presentationml/2006/main}bg")
    target_bg = target_c_sld.find("{http://schemas.openxmlformats.org/presentationml/2006/main}bg")
    if target_bg is not None:
        target_c_sld.remove(target_bg)
    if source_bg is not None:
        target_c_sld.insert(0, copy.deepcopy(source_bg))

    for shape in list(target.shapes):
        shape._element.getparent().remove(shape._element)

    relationships = {}
    for relationship_id, relationship in source.part.rels.items():
        if "notesSlide" in relationship.reltype or "slideLayout" in relationship.reltype:
            continue
        relationships[relationship_id] = target.part.relate_to(
            relationship.target_ref if relationship.is_external else relationship.target_part,
            relationship.reltype,
            is_external=relationship.is_external,
        )

    for shape in source.shapes:
        element = copy.deepcopy(shape._element)
        for child in element.iter():
            for attribute, value in list(child.attrib.items()):
                if attribute.startswith(RELATIONSHIP_NAMESPACE) and value in relationships:
                    child.set(attribute, relationships[value])
        target.shapes._spTree.insert_element_before(element, "p:extLst")
    return target


def _answer_value(region, answers):
    value = answers.get(region.number, region.answer)
    if value is None:
        return ""
    return str(value).strip()


def _replace_tokens_in_shape(shape, replacements):
    if not shape.has_text_frame:
        return False
    changed = False
    for paragraph in shape.text_frame.paragraphs:
        # Normal case: token is wholly contained in one run, so formatting is
        # preserved. Also handle templates that have the token split across
        # runs by rebuilding that paragraph's text only when necessary.
        for run in paragraph.runs:
            old = run.text
            new = old
            for token, value in replacements.items():
                new = new.replace(token, str(value))
            if new != old:
                run.text = new
                changed = True
    return changed


def _replace_template_tokens(slide, region, answer):
    replacements = {
        "#QUESTION": f"Q{region.number}",
        "#ANSWER": answer or region.answer or "—",
        "#SUBJECT": region.subject,
    }
    for shape in slide.shapes:
        _replace_tokens_in_shape(shape, replacements)


def _remove_shape(shape):
    element = shape._element
    element.getparent().remove(element)


def _style_answer_token(slide, answer: str):
    """Make an existing #ANSWER footer visually prominent after replacement."""
    if not answer:
        return False
    changed = False
    for shape in slide.shapes:
        if not shape.has_text_frame or "ANSWER" not in (shape.text or "").upper():
            continue
        for paragraph in shape.text_frame.paragraphs:
            for run in paragraph.runs:
                if answer in run.text:
                    run.font.bold = True
                    run.font.color.rgb = ANSWER_ORANGE
                    run.font.size = Pt(20)
                    changed = True
    return changed


def _add_answer_badge(slide, answer: str, prs):
    """Guarantee a clearly visible answer on every generated question slide.

    This is intentionally independent of the uploaded template. If a custom
    template has no #ANSWER token, the answer is still shown on the same slide.
    """
    if not answer:
        return

    # Compact premium badge in the bottom-right area, above the footer edge.
    width = Inches(2.25)
    height = Inches(0.56)
    left = prs.slide_width - Inches(2.95)
    top = prs.slide_height - Inches(1.08)

    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = ANSWER_DARK
    shape.line.color.rgb = ANSWER_ORANGE
    shape.line.width = Pt(1.5)

    tf = shape.text_frame
    tf.clear()
    tf.margin_left = Inches(0.12)
    tf.margin_right = Inches(0.12)
    tf.margin_top = Inches(0.03)
    tf.margin_bottom = Inches(0.03)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = f"ANSWER  {answer}"
    r.font.bold = True
    r.font.size = Pt(18)
    r.font.color.rgb = ANSWER_ORANGE
    r.font.name = "Aptos Display"


def _add_question_image(slide, prs, region):
    if region.image is None:
        raise ValueError(f"Question {region.number} has no crop image.")
    stream = io.BytesIO()
    region.image.save(stream, "PNG", optimize=True)
    stream.seek(0)

    placeholder = find_image_placeholder(slide)
    if placeholder is not None:
        left, top, width, height = placeholder.left, placeholder.top, placeholder.width, placeholder.height
        _remove_shape(placeholder)
    else:
        left, top, width, height = fit_box(prs, region.image)
    slide.shapes.add_picture(stream, left, top, width=width, height=height)


def build_slides(template_bytes, regions, answers, style="Premium Light"):
    """Clone the first template slide once per question and inject the crop.

    Answer mapping is always by the canonical question number, never by slide
    index or subject order.
    """
    prs = validate_template(template_bytes)
    source_index = 0
    answers = answers or {}
    for region in regions:
        answer = _answer_value(region, answers)
        slide = _duplicate_slide(prs, source_index)
        _replace_template_tokens(slide, region, answer)
        answer_styled = _style_answer_token(slide, answer)
        _add_question_image(slide, prs, region)
        if not answer_styled:
            _add_answer_badge(slide, answer, prs)

    slide_ids = prs.slides._sldIdLst
    slide_ids.remove(slide_ids[0])
    return prs
