import streamlit as st


def render_review(regions, subjects, answers):
    """Interactive review editor. Changes persist in Streamlit session state."""
    st.subheader("Review & correct")
    st.caption("Edit question number, subject, answer, or exclude a bad detection before exporting.")

    for idx, region in enumerate(regions):
        with st.container(border=True):
            cols = st.columns([1.2, 1.6, 1.6, 0.8, 2.5])
            with cols[0]:
                region.included = st.checkbox("Include", value=region.included, key=f"inc_{idx}")
            with cols[1]:
                region.number = int(st.number_input("Question", min_value=1, max_value=999, value=int(region.number), key=f"num_{idx}"))
            with cols[2]:
                current = region.subject if region.subject in subjects else subjects[0]
                options = subjects + ["Unclassified"] if "Unclassified" not in subjects else subjects
                region.subject = st.selectbox("Subject", options, index=options.index(current), key=f"sub_{idx}")
            with cols[3]:
                answer_default = answers.get(region.number, region.answer or "")
                answer = st.text_input("Answer", value=answer_default, key=f"ans_{idx}")
                if answer:
                    answers[region.number] = answer.strip().upper()
                    region.answer = answers[region.number]
            with cols[4]:
                badge = "🔴 Review" if region.needs_review else "🟢 Good"
                st.markdown(f"**{badge}** · confidence {region.confidence:.0%} · page {region.page_index + 1}")
                st.image(region.image, use_container_width=True)
