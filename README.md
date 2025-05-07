
# 🧠 Smart PDF Component Extractor

A Streamlit-based web app to extract component codes from precast construction drawings. Includes visual zone selection, OCR options, regex-based parsing of levels, and automatic quantity calculation.

---

## 🚀 Features

- Upload and preview PDF drawings
- Draw visual zones to extract only selected regions
- Choose from **five text extraction methods**:
  - `pdfplumber`
  - `PyMuPDF` (block-level)
  - `OCR Space API`
  - `Microsoft Azure OCR`
  - `Google Vision OCR`
- Regex parsing to extract:
  - **Component codes** (e.g., `1B201`, `2A-RC01`)
  - **Levels** (e.g., `(2)`, `(3, 4-5)`)
  - **Total quantity** from levels
- Export results to Excel
- Collect user feedback with emoji-based rating
- Log actions securely to a local SQLite database (supports user-based filtering)

---

## 🖥️ Run Locally

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/pdf-extraction-app.git
cd pdf-extraction-app
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install system dependencies

These are required for OCR and PDF rendering:

- **Tesseract OCR**  
  [https://github.com/tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract)

- **Poppler**  
  - **Windows**: [Download guide](http://blog.alivate.com.au/poppler-windows/)
  - **macOS** (Homebrew):
    ```bash
    brew install poppler
    ```
  - **Linux** (Debian/Ubuntu):
    ```bash
    sudo apt update && sudo apt install poppler-utils tesseract-ocr
    ```

> ✅ These are also declared in `packages.txt` for Streamlit Cloud deployment.

### 4. Run the app

```bash
streamlit run app.py
```

Then go to `http://localhost:8501` in your browser.

---

## ☁️ Deploy to Streamlit Cloud

### 1. Required files

Make sure your GitHub repo includes:
- `app.py`
- `requirements.txt` (Python dependencies)
- `packages.txt` (System dependencies like `poppler-utils`, `tesseract-ocr`)

### 2. Push your project

```bash
git init
git remote add origin https://github.com/yourusername/pdf-extraction-app.git
git add .
git commit -m "Deployable version"
git push -u origin main
```

### 3. Deploy at [streamlit.io/cloud](https://streamlit.io/cloud)

- Log in with GitHub
- Create a new app
- Set `app.py` as the entry point
- Streamlit will install everything automatically from both `.txt` files

---

## 📂 Project Structure

```plaintext
pdf-extraction-app/
├── app.py               # Main Streamlit GUI logic
├── requirements.txt     # Python package list
├── packages.txt         # System packages for cloud
├── db.py                # SQLite logging logic
├── README.md            # This file
└── data/                # For SQLite DB + logs
```

---

## ✅ Future Add-ons

- User authentication (already partially implemented)
- Analytics dashboard for feedback
- Multi-zone PDF extraction
- Component library matching (from CSV)

---

Built with ❤️ using Streamlit + Python
