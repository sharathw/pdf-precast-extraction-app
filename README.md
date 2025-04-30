# 🧠 Smart PDF Component Extractor

A Streamlit-based web app to extract components from precast construction drawings using multiple methods, with support for visual zone selection, user feedback, and logging.

---

## 🚀 Features
- PDF upload and preview
- Visual zone selection using drawing canvas
- Three extraction methods:
  - `pdfplumber`
  - `PyMuPDF` (block-level)
  - `OCR` (Tesseract + pdf2image)
- Regex-based parsing to extract components and levels
- Excel export
- Confidence rating system
- SQLite logging and downloadable log file

---

## 🖥️ Run Locally

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/pdf-extraction-app.git
cd pdf-extraction-app
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Install external dependencies
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [Poppler for PDF](http://blog.alivate.com.au/poppler-windows/) (for Windows)

Make sure both are added to your system PATH.

### 4. Run the app
```bash
streamlit run app.py
```

App will launch in your browser at `http://localhost:8501`

---

## ☁️ Deploy to Streamlit Cloud

### 1. Push your project to GitHub
Create a new repo and push all files:
```bash
git init
git remote add origin https://github.com/yourusername/pdf-extraction-app.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

### 2. Go to [streamlit.io/cloud](https://streamlit.io/cloud)
- Log in with GitHub
- Click **New app**
- Connect to your `pdf-extraction-app` repo
- Set `app.py` as the main file
- Deploy 🚀

---

## 📂 Project Structure
```plaintext
pdf-extraction-app/
├── app.py               # Streamlit GUI
├── utils.py             # Text extraction and parsing logic
├── db.py                # SQLite + log file logging
├── requirements.txt     # Python dependencies
├── README.md            # You are here
└── data/                # SQLite DB lives here
```

---

## ✅ To Do / Optional Extensions
- User authentication
- Feedback dashboard
- Batch processing multiple PDFs
- Multi-zone extraction

---

Built with ❤️ using Streamlit + Python
