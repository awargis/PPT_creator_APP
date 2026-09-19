import json
import re

import streamlit as st

from answer_key.parser import parse
from answer_key.validator import validate
from image.enhancement import enhance
from pipeline.orchestrator import run_pipeline
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
    with st.status("Processing document…", expanded=True) as status:
        st.write("Rendering PDF pages…")
        try:
            regions, report = run_pipeline(
                pdf.getvalue(),
                settings["exam_type"],
                settings["subjects"],
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
            st.session_state["exam_type"] = settings["exam_type"]
            status.update(label=f"Detected {len(regions)} question(s)", state="complete")
        except Exception as exc:
            status.update(label="Processing failed", state="error")
            st.exception(exc)
            st.stop()

if "regions" in st.session_state:
    regions = st.session_state["regions"]
    answers = st.session_state.setdefault("answers", {})
    report = st.session_state["report"]

    render_report(report)
    render_review(regions, settings["subjects"], answers)

    if st.button("📦 Generate production ZIP", type="primary", use_container_width=True):
        # Recompute answer validation after manual review edits.
        report.missing_answers = validate(regions, answers)["missing"]
        with st.spinner("Building template-based presentations, crops and manifest…"):
            try:
                archive, manifest = create_subject_outputs(
                    st.session_state["template_bytes"], regions, answers, settings["style"]
                )
                filename = f"{re.sub(r'[^A-Za-z0-9_-]+', '_', st.session_state['exam_type'])}_Discussion_Studio.zip"
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
