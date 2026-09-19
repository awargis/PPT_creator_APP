import json
import re

import streamlit as st

from answer_key.parser import parse
from answer_key.validator import validate
from image.enhancement import enhance
from pipeline.orchestrator import run_pipeline
from pipeline.exam_detector import detect_exam_type
from config import get_subjects
from services.output_service import create_subject_outputs
from ui.report import render_report
from ui.review import render_review
from ui.sidebar import render_sidebar


st.set_page_config(
    page_title="Vidyapeeth Test Presentation Studio",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("# 📚 Vidyapeeth Test Presentation Studio")
st.caption("Local-first • Native PDF extraction • OCR fallback • Template-based PPTX • No Gemini/API dependency")

settings = render_sidebar()

with st.expander("How the production pipeline works", expanded=False):
    st.markdown(
        "**PDF → native text → OCR fallback → layout/columns → question detection → "
        "subject classification → confidence review → crop enhancement → template-based PPTX → ZIP.**"
    )

pdf = st.file_uploader("### 1 · Question paper PDF", type=["pdf"], key="pdf")
template = st.file_uploader("### 2 · Discussion PPT template", type=["pptx"], key="template")
answer_text = st.text_area(
    "### 3 · Answer key (optional)",
    placeholder="1: A\n2: B\n3: C\n4: D",
    height=120,
)

analyze = st.button("🚀 Analyze question paper", type="primary", use_container_width=True)

if analyze:
    if not pdf:
        st.error("Please upload the question-paper PDF.")
        st.stop()
    if not template:
        st.error("Please upload the discussion PPT template.")
        st.stop()

    answers = parse(answer_text)
    st.session_state["answers"] = answers

    detection = detect_exam_type(pdf.getvalue())
    if settings["exam_type"] == "Auto-detect":
        effective_exam = detection.exam_type
    else:
        effective_exam = settings["exam_type"]
    effective_subjects = get_subjects(effective_exam)
    st.session_state["detected_exam"] = detection
    st.session_state["effective_exam"] = effective_exam
    st.session_state["effective_subjects"] = effective_subjects

    with st.status("Processing document…", expanded=True) as status:
        st.write(
            f"Exam: **{effective_exam}** "
            f"(auto-detection confidence {detection.confidence:.0%})"
            if settings["exam_type"] == "Auto-detect"
            else f"Exam: **{effective_exam}** (manual selection)"
        )
        st.write("Rendering PDF pages…")
        try:
            regions, report = run_pipeline(
                pdf.getvalue(),
                effective_exam,
                effective_subjects,
                settings["render_dpi"],
                settings["pad_x"],
                settings["pad_y"],
                settings["use_ocr"],
                answers,
            )
            for region in regions:
                if region.image is not None:
                    region.image = enhance(region.image, settings["style"])
            report.missing_answers = validate(regions, answers)["missing"]
            st.session_state["regions"] = regions
            st.session_state["report"] = report
            st.session_state["template_bytes"] = template.getvalue()
            st.session_state["effective_exam"] = effective_exam
            status.update(label=f"Detected {len(regions)} question(s)", state="complete")
        except Exception as exc:
            status.update(label="Processing failed", state="error")
            st.exception(exc)
            st.stop()

if "regions" in st.session_state:
    regions = st.session_state["regions"]
    answers = st.session_state.setdefault("answers", {})
    report = st.session_state["report"]
    effective_subjects = st.session_state.get("effective_subjects", settings["subjects"])
    effective_exam = st.session_state.get("effective_exam", settings["exam_type"])

    if "detected_exam" in st.session_state and settings["exam_type"] == "Auto-detect":
        detection = st.session_state["detected_exam"]
        evidence = ", ".join(detection.evidence) if detection.evidence else "No strong marker"
        st.info(f"Auto-detected **{effective_exam}** · confidence {detection.confidence:.0%} · evidence: {evidence}")

    render_report(report)
    render_review(regions, effective_subjects, answers)

    if st.button("📦 Generate production ZIP", type="primary", use_container_width=True):
        # Recompute answer validation after manual review edits.
        report.missing_answers = validate(regions, answers)["missing"]
        with st.spinner("Building template-based presentations, crops and manifest…"):
            try:
                archive, manifest = create_subject_outputs(
                    st.session_state["template_bytes"], regions, answers, settings["style"]
                )
                filename = f"{re.sub(r'[^A-Za-z0-9_-]+', '_', st.session_state['effective_exam'])}_Discussion_Studio.zip"
                st.success(
                    f"Ready: {len(manifest['presentations'])} presentation(s), "
                    f"{len(manifest['questions'])} crop(s)."
                )
                st.download_button(
                    "⬇️ Download complete project output",
                    archive.getvalue(),
                    filename,
                    "application/zip",
                    type="primary",
                    use_container_width=True,
                )
                with st.expander("Manifest", expanded=False):
                    st.json(manifest)
            except Exception as exc:
                st.error(f"PPT generation failed: {exc}")
                st.exception(exc)
