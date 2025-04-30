# app.py
import streamlit as st
from streamlit_drawable_canvas import st_canvas
import datetime
import os
from utils import extract_text_and_parse
from db import log_extraction
import pandas as pd
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from PIL import Image, ImageDraw

st.set_page_config(page_title="Smart PDF Extractor", layout="wide")
st.title("📄 Smart PDF Component Extractor")

zone = None

# Sidebar setup
with st.sidebar:
    st.header("Upload & Options")
    pdf_file = st.file_uploader("Upload PDF", type=["pdf"])
    method = st.selectbox("Choose extraction method", ["pdfplumber", "PyMuPDF", "OCR"])
    draw_zone = st.checkbox("Enable zone selection (draw below)", value=False)
    zoom_factor = st.slider("Zoom", min_value=0.1, max_value=3.0, value=1.0, step=0.1)
    extract_now = st.button("🔍 Extract Components")

if pdf_file:
    with st.spinner("Preparing PDF preview..."):
        # Save uploaded file temporarily
        file_path = os.path.join("temp", pdf_file.name)
        os.makedirs("temp", exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(pdf_file.getbuffer())

        # Convert first page of PDF to image for preview
        preview_img = convert_from_path(file_path, first_page=1, last_page=1, dpi=150)[0]

    if draw_zone:
        st.subheader("🖍️ Draw a zone on the highlighted area below")
        with st.spinner("Loading drawing canvas..."):
            # Create a preview image with highlighted border
            highlight_img = preview_img.copy()
            draw = ImageDraw.Draw(highlight_img)
            draw.rectangle([(5, 5), (highlight_img.width - 5, highlight_img.height - 5)], outline="red", width=3)

            # Ensure the image is in RGB mode
            if highlight_img.mode != "RGB":
                highlight_img = highlight_img.convert("RGB")

            # Resize image based on zoom factor
            canvas_width = int(highlight_img.width * zoom_factor)
            canvas_height = int(highlight_img.height * zoom_factor)
            resized_img = highlight_img.resize((canvas_width, canvas_height))

            canvas_result = st_canvas(
                fill_color="rgba(0, 0, 255, 0.2)",
                stroke_width=2,
                background_image=resized_img,
                update_streamlit=True,
                height=canvas_height,
                width=canvas_width,
                drawing_mode="rect",
                key="canvas",
            )

            if canvas_result.json_data and len(canvas_result.json_data["objects"]):
                obj = canvas_result.json_data["objects"][0]
                x, y, w, h = obj["left"], obj["top"], obj["width"], obj["height"]
                # Scale coordinates back to original resolution
                zone = (x / zoom_factor, y / zoom_factor, (x + w) / zoom_factor, (y + h) / zoom_factor)
    else:
        st.image(preview_img, caption="PDF Preview (Page 1)", use_container_width=True)

    if extract_now:
        with st.spinner("Extracting and parsing text..."):
            df, raw_text = extract_text_and_parse(file_path, method, zone)

        if df.empty:
            st.error("No components found using the selected method.")
        else:
            st.success("Extraction complete!")
            st.dataframe(df)

            # Download Excel
            excel_filename = pdf_file.name.replace(".pdf", f"_list_{method}.xlsx")
            df.to_excel(excel_filename, index=False)
            with open(excel_filename, "rb") as f:
                st.download_button("📥 Download Excel", f, file_name=excel_filename)

            # Feedback
            rating = st.slider("Rate the quality of this extraction (1=Poor, 5=Perfect)", 1, 5, 3)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"log_{timestamp}.txt"

            # Log to DB and file
            log_extraction(pdf_file.name, method, zone, rating, log_file)
            with open(log_file, "rb") as lf:
                st.download_button("📄 Download Log", lf, file_name=log_file)
else:
    st.info("Upload a PDF to get started.")
