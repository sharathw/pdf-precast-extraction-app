import streamlit as st
import pandas as pd
import re
import io
import fitz  # PyMuPDF
import pdfplumber
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract

from user_auth import init_user_db, authenticate_user
from db_logger import init_db, log_event

st.set_page_config(page_title="Prefab Parser for Singapore PPVC/Precast", layout="centered")

# Initialize databases
init_user_db()
init_db()

# Session state setup
for key in ["is_authenticated", "user_name", "user_email", "user_role", "df", "emoji_rating", "rated_method", "feedback_type", "show_toast"]:
    if key not in st.session_state:
        st.session_state[key] = None if key == "df" else False if key == "is_authenticated" else ""

# Login

if not st.session_state.is_authenticated:
    st.title("Prefab Parser for Singapore PPVC/Precast")
    st.text("🔐 Login or Register")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login"):
            auth = authenticate_user(login_email, login_password)
            if auth:
                name, role = auth[0], auth[1]
                st.session_state.is_authenticated = True
                st.session_state.user_name = name
                st.session_state.user_email = login_email
                st.session_state.user_role = role
                st.rerun()
            else:
                st.error("Invalid credentials.")

    with tab2:
        from user_auth import add_user
        reg_name = st.text_input("Name")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_pass")

        if st.button("Register"):
            if reg_name and reg_email and reg_password:
                try:
                    add_user(reg_name, reg_email, "user", reg_password)
                    st.success("🎉 Registration successful. Please log in.")
                except Exception as e:
                    st.error(f"⚠️ Error: {e}")
            else:
                st.warning("Please fill in all fields.")

    st.stop()

    st.title("🔐 Login Required")
    login_email = st.text_input("Email")
    login_password = st.text_input("Password", type="password")

    if st.button("Login"):
        auth = authenticate_user(login_email, login_password)
        if auth:
            name, role = auth[0], auth[1]
            st.session_state.is_authenticated = True
            st.session_state.user_name = name
            st.session_state.user_email = login_email
            st.session_state.user_role = role
            st.rerun()
        else:
            st.error("Invalid credentials.")
    st.stop()

# Logout button
if st.button("Logout"):
    for key in st.session_state.keys():
        st.session_state[key] = None if key == "df" else False if key == "is_authenticated" else ""
    st.rerun()

st.title(f"Welcome, {st.session_state.user_name}!")

# Admin Dashboard
if st.session_state.user_role == "admin":
    st.header("🔧 Admin Dashboard: All User Uploads")
    import sqlite3
    conn = sqlite3.connect("data/extraction_log.db")
    df_logs = pd.read_sql_query("SELECT * FROM extraction_logs ORDER BY timestamp DESC", conn)
    conn.close()
    st.dataframe(df_logs)
    st.download_button("📥 Download Log", df_logs.to_csv(index=False), "logs.csv", "text/csv")
    st.stop()

# App for Users
uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
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
        with st.spinner("🔄 Extracting..."):
            uploaded_file.seek(0)
            full_text = extract_text(uploaded_file, method)
            pairs = extract_component_with_levels(full_text)
            df = pd.DataFrame(pairs, columns=["Component Code", "Level(s)"])
            df = df.drop_duplicates().sort_values("Component Code").reset_index(drop=True)
            st.session_state.df = df

            log_event(
                user_email=st.session_state.user_email,
                filename=uploaded_file.name,
                file_bytes=uploaded_file.getvalue(),
                method=method,
                count=len(df),
                feedback=None,
                feedback_type=None
            )

            st.toast(f"✅ Extracted {len(df)} components using {method}.")

if st.session_state.df is not None:
    st.dataframe(st.session_state.df, use_container_width=True)

    # Excel download
    towrite = io.BytesIO()
    st.session_state.df.to_excel(towrite, index=False, sheet_name="Components")
    towrite.seek(0)
    if st.download_button("📥 Download Excel", towrite, "components_with_levels.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"):
        log_event(
            user_email=st.session_state.user_email,
            filename=st.session_state.rated_method + "_download",
            file_bytes=None,
            method=st.session_state.rated_method or "unknown",
            count=len(st.session_state.df),
            feedback="📥 Downloaded Excel",
            feedback_type="download"
        )
        st.toast("📦 Excel file downloaded successfully.")

    # Feedback
    emoji_map = {1: "😠", 2: "😕", 3: "😐", 4: "🙂", 5: "😄"}
    rating_label = {1: "Very Bad", 2: "Bad", 3: "Neutral", 4: "Good", 5: "Very Good"}

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
        feedback = "👎" if st.session_state.feedback_type == "downvote" else emoji_map[st.session_state.emoji_rating]
        feedback_type = st.session_state.feedback_type
        log_event(
            user_email=st.session_state.user_email,
            filename=st.session_state.rated_method + "_feedback",
            file_bytes=None,
            method=method,
            count=len(st.session_state.df),
            feedback=feedback,
            feedback_type=feedback_type
        )
        st.toast(f"You rated: {feedback} — Method: {method}")
        st.session_state.show_toast = False

    # Feedback summary
    if st.session_state.feedback_type == "emoji":
        emoji = emoji_map[st.session_state.emoji_rating]
        label = rating_label[st.session_state.emoji_rating]
        st.markdown(f"### Your Feedback: {emoji} **{label}**")
    elif st.session_state.feedback_type == "downvote":
        st.markdown("### Your Feedback: 👎 This method did not work well")

    # Show user history
    import sqlite3
    conn = sqlite3.connect("data/extraction_log.db")
    user_logs = pd.read_sql_query(
        f"SELECT filename, method, component_count, timestamp, feedback FROM extraction_logs WHERE user_email = '{st.session_state.user_email}' ORDER BY timestamp DESC",
        conn
    )
    conn.close()

    st.markdown("### 📂 History")
    
    user_logs['timestamp'] = pd.to_datetime(user_logs['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
    st.dataframe(user_logs)
