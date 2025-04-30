# utils.py
import re
import pdfplumber
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract
import tempfile
import os
import pandas as pd

def extract_text_and_parse(path, method, zone=None):
    if method == "pdfplumber":
        text = extract_pdfplumber(path, zone)
    elif method == "PyMuPDF":
        text = extract_pymupdf(path, zone)
    elif method == "OCR":
        text = extract_ocr(path, zone)
    else:
        return pd.DataFrame(), ""
    return parse_components(text), text

def extract_pdfplumber(path, zone):
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            if zone:
                crop = page.within_bbox(zone)
                text += crop.extract_text() + " " if crop.extract_text() else ""
            else:
                page_text = page.extract_text()
                text += page_text + " " if page_text else ""
    return text

def extract_pymupdf(path, zone):
    doc = fitz.open(path)
    extracted = ""
    for page in doc:
        if zone:
            blocks = page.get_text("blocks")
            for b in blocks:
                x0, y0, x1, y1, text, *_ = b
                if x0 >= zone[0] and y0 >= zone[1] and x1 <= zone[2] and y1 <= zone[3]:
                    extracted += text + " "
        else:
            extracted += page.get_text("text") + " "
    return extracted

def extract_ocr(path, zone):
    extracted = ""
    with tempfile.TemporaryDirectory() as tmp:
        images = convert_from_path(path, dpi=300, output_folder=tmp)
        for img in images:
            if zone:
                x0, y0, x1, y1 = map(int, zone)
                img = img.crop((x0, y0, x1, y1))
            extracted += pytesseract.image_to_string(img)
    return extracted

def parse_components(text):
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\)\s*([A-Za-z0-9\-]+)", r") \1", text)
    pattern = r"\((\d+(?:-\d+)?)\)\s*([A-Za-z0-9\-]+)"
    matches = re.findall(pattern, text)
    return pd.DataFrame([{"Component": c, "Level Info": lvl} for lvl, c in matches])
