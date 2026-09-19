import streamlit as st

from config import EXAMS, STYLES, get_subjects


def render_sidebar():
    st.sidebar.markdown("## ⚙️ Production settings")
    exam_type = st.sidebar.selectbox("Exam", EXAMS)
    dpi = st.sidebar.slider("Render quality (DPI)", 120, 360, 240, 20)
    pad_x = st.sidebar.slider("Horizontal crop margin", 0, 80, 24)
    pad_y = st.sidebar.slider("Vertical crop margin", 0, 60, 14)
    style = st.sidebar.selectbox("Image treatment", STYLES)
    use_ocr = st.sidebar.checkbox("OCR scanned pages automatically", value=True)
    st.sidebar.caption("Native PDF text is always preferred. OCR is used only when native text is insufficient.")
    return {
        "exam_type": exam_type,
        "subjects": get_subjects(exam_type),
        "pad_x": pad_x,
        "pad_y": pad_y,
        "render_dpi": dpi,
        "style": style,
        "use_ocr": use_ocr,
    }
