import streamlit as st

from config import STYLES


def render_sidebar():
    st.sidebar.markdown("## ⚙️ Production settings")
    st.sidebar.success("Exam detection: AUTO")
    st.sidebar.caption("The uploaded paper is identified from its title, instructions and section headers. The app then determines subject/question ranges before cropping.")
    dpi = st.sidebar.slider("Render quality (DPI)", 150, 360, 240, 15)
    pad_x = st.sidebar.slider("Crop safety margin", 0, 80, 18)
    pad_y = st.sidebar.slider("Top/boundary margin", 0, 60, 10)
    style = st.sidebar.selectbox("Image treatment", STYLES, index=0)
    use_ocr = st.sidebar.checkbox("OCR scanned pages automatically", value=True)
    transparent = st.sidebar.checkbox("Remove white page background", value=True)
    st.sidebar.caption("Native PDF text is always preferred. OCR is used only when native text is insufficient.")
    return {
        "subjects": [],
        "pad_x": pad_x,
        "pad_y": pad_y,
        "render_dpi": dpi,
        "style": style,
        "use_ocr": use_ocr,
        "transparent_background": transparent,
    }
