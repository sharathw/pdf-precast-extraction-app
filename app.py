import streamlit as st
import pandas as pd
import re
import io
import fitz  # PyMuPDF
import pdfplumber
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
from db_logger import init_db, log_event

st.set_page_config(page_title="Component Code Extractor", layout="centered")
st.title("🧱 Extract Component Codes with Levels")

init_db()

uploaded_file = st.file_uploader("Upload a PDF (max 50MB)", type=["pdf"])

component_pattern = r'\b[1-2][A-Z]{1,3}[0-9a-zA-Z\-]*\b'
bracket_pattern = r'\((?:\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)\)'

def extract_component_with_levels(text):
    pairs = []
    tokens = re.findall(rf'{component_pattern}|{bracket_pattern}', text)
    current_component = None
    levels = []

    for token in tokens:
        if re.match(component_pattern, token):
            if current_component:
                pairs.append((current_component, ", ".join(levels) if levels else ""))
            current_component = token
            levels = []
        elif re.match(bracket_pattern, token):
            levels.append(token)
    if current_component:
        pairs.append((current_component, ", ".join(levels) if levels else ""))
    return pairs

def extract_text(file, method):
    text = ""
    if method == "pdfplumber":
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    elif method == "PyMuPDF":
        doc = fitz.open(stream=file.read(), filetype="pdf")
        for page in doc:
            text += page.get_text()
    elif method == "Tesseract OCR":
        images = convert_from_bytes(file.read())
        for img in images:
            text += pytesseract.image_to_string(img)
    return text

# Session state setup
if "df" not in st.session_state:
    st.session_state.df = None
if "emoji_rating" not in st.session_state:
    st.session_state.emoji_rating = 0
if "rated_method" not in st.session_state:
    st.session_state.rated_method = None
if "feedback_type" not in st.session_state:
    st.session_state.feedback_type = None
if "show_toast" not in st.session_state:
    st.session_state.show_toast = False

# PDF Preview
if uploaded_file:
    st.subheader("👁️ Preview - Page 1")
    try:
        uploaded_file.seek(0)
        pages = convert_from_bytes(uploaded_file.read(), first_page=1, last_page=1)
        st.image(pages[0], caption="First Page", use_container_width=True)
    except Exception as e:
        st.error(f"Preview failed: {e}")
    uploaded_file.seek(0)

    method = st.radio("Choose extraction method", ["pdfplumber", "PyMuPDF", "Tesseract OCR"])

    if method != st.session_state.rated_method:
        st.session_state.emoji_rating = 0
        st.session_state.feedback_type = None
        st.session_state.rated_method = None
        st.session_state.show_toast = False

    if st.button("Extract Components & Levels"):
        with st.spinner("🔄 Extracting components... please wait"):
            uploaded_file.seek(0)
            full_text = extract_text(uploaded_file, method)
            pairs = extract_component_with_levels(full_text)
            df = pd.DataFrame(pairs, columns=["Component Code", "Level(s)"])
            df = df.drop_duplicates().sort_values("Component Code").reset_index(drop=True)
            st.session_state.df = df

            # Log extraction event
            file_bytes = uploaded_file.getvalue()
            filename = uploaded_file.name
            log_event(
                filename=filename,
                file_bytes=file_bytes,
                method=method,
                count=len(df),
                feedback=None,
                feedback_type=None
            )

            st.toast(f"✅ Extracted {len(df)} components using {method}.")

# Show results and feedback
if st.session_state.df is not None:
    st.success(f"✅ Successfully extracted {len(st.session_state.df)} components.")
    st.dataframe(st.session_state.df, use_container_width=True)

    # Download Excel + log
    towrite = io.BytesIO()
    st.session_state.df.to_excel(towrite, index=False, sheet_name="Components")
    towrite.seek(0)

    if st.download_button(
        "📥 Download Excel",
        towrite,
        file_name="components_with_levels.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ):
        st.toast("📦 Excel file downloaded successfully.")
        log_event(
            filename=st.session_state.rated_method + "_download" if st.session_state.rated_method else "unknown_download",
            file_bytes=None,
            method=st.session_state.rated_method or "unknown",
            count=len(st.session_state.df),
            feedback="📥 Downloaded Excel",
            feedback_type="download"
        )

    # --- Feedback Section ---
    emoji_map = {
        1: "😠",
        2: "😕",
        3: "😐",
        4: "🙂",
        5: "😄"
    }

    rating_label = {
        1: "Very Bad",
        2: "Bad",
        3: "Neutral",
        4: "Good",
        5: "Very Good"
    }

    if st.session_state.feedback_type is None:
        st.markdown("### 😊 How was the extraction result?")
        emoji_cols = st.columns(5)
        for i in range(1, 6):
            if emoji_cols[i - 1].button(emoji_map[i], key=f"emoji_{method}_{i}"):
                st.session_state.emoji_rating = i
                st.session_state.feedback_type = "emoji"
                st.session_state.rated_method = method
                st.session_state.show_toast = True
                st.rerun()

        if st.checkbox("👎 This method did not work well", key=f"downvote_{method}"):
            st.session_state.emoji_rating = 0
            st.session_state.feedback_type = "downvote"
            st.session_state.rated_method = method
            st.session_state.show_toast = True
            st.rerun()

    if st.session_state.show_toast:
        count = len(st.session_state.df)
        feedback = "👎" if st.session_state.feedback_type == "downvote" else emoji_map[st.session_state.emoji_rating]
        feedback_label = "downvote" if st.session_state.feedback_type == "downvote" else "emoji"
        log_event(
            filename=st.session_state.rated_method + "_feedback",
            file_bytes=None,
            method=method,
            count=count,
            feedback=feedback,
            feedback_type=feedback_label
        )

        if feedback_label == "emoji":
            label = rating_label[st.session_state.emoji_rating]
            st.toast(f"You rated {feedback} {label} — Extracted {count} components using {method}.")
        else:
            st.toast(f"👎 You marked this method as not working — Extracted {count} components using {method}.")
        st.session_state.show_toast = False

    if st.session_state.feedback_type == "emoji":
        emoji = emoji_map[st.session_state.emoji_rating]
        label = rating_label[st.session_state.emoji_rating]
        st.markdown("---")
        st.markdown(f"### Your Feedback: {emoji} **{label}**")
    elif st.session_state.feedback_type == "downvote":
        st.markdown("---")
        st.markdown("### Your Feedback: 👎 This method did not work well")
