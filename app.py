import streamlit as st
import pandas as pd
import re
import io
import fitz  # PyMuPDF
import pdfplumber
from pdf2image import convert_from_bytes
from PIL import Image
import sqlite3
import hashlib
import secrets
import time
import threading

import requests
import streamlit.components.v1 as components

import json
from google.cloud import vision

gcp_key = json.loads(st.secrets["gcp"]["key_json"])
client = vision.ImageAnnotatorClient.from_service_account_info(gcp_key)

from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials

from user_auth import init_user_db, authenticate_user, add_user
from db_logger import init_db, log_event, get_user_logs


st.set_page_config(page_title="Prefab Parser for Singapore PPVC/Precast", layout="centered")

#self pinging code to keep streamlit app always running
def ping_app():
    while True:
        try:
            # Replace with your app's URL
            requests.get("https://prefabparser.streamlit.app")
            time.sleep(300)  # Ping every 5 minutes
        except:
            time.sleep(300)  # Wait and retry if error

# Start pinging in a separate thread
if not hasattr(st, 'already_started_server'):
    st.already_started_server = True
    t = threading.Thread(target=ping_app)
    t.daemon = True
    t.start()


# Initialize databases
init_user_db()
init_db()

# Initialize the Azure OCR client
def init_azure_client(endpoint, key):
    return ComputerVisionClient(endpoint, CognitiveServicesCredentials(key))

# Session state setup with CSRF protection
if "csrf_token" not in st.session_state:
    st.session_state.csrf_token = secrets.token_hex(16)

for key in ["is_authenticated", "user_name", "user_email", "user_role", "df", 
            "emoji_rating", "rated_method", "feedback_type", "show_toast", 
            "login_attempts", "last_attempt_time"]:
    if key not in st.session_state:
        if key == "df":
            st.session_state[key] = None
        elif key == "is_authenticated":
            st.session_state[key] = False
        elif key == "login_attempts":
            st.session_state[key] = 0
        elif key == "last_attempt_time":
            st.session_state[key] = 0
        else:
            st.session_state[key] = ""

# Rate limiting for login attempts
def check_rate_limit():
    current_time = time.time()
    st.session_state.login_attempts = int(st.session_state.get("login_attempts", 0))
    if st.session_state.login_attempts >= 5:
        if current_time - st.session_state.last_attempt_time < 300:  # 5 minutes cooldown
            remaining = 300 - (current_time - st.session_state.last_attempt_time)
            st.error(f"Too many login attempts. Please try again in {int(remaining)} seconds.")
            return False
        else:
            st.session_state.login_attempts = 0
    return True

# Function to display footer with Lean Station logo
def display_footer():
    st.markdown("""---""")
    cols = st.columns([1, 2, 1])
    with cols[1]:
        # CSS for the footer
        st.markdown("""
        <style>
        .footer {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-top: 20px;
            opacity: 0.8;
        }
        .footer img {
            height: 40px;
            margin-right: 10px;
        }
        .footer a {
            color: #FF5500;
            text-decoration: none;
        }
        .footer a:hover {
            text-decoration: underline;
        }
        </style>
        <div class="footer">
            <img src="https://leanstation.com/wp-content/uploads/2020/08/cropped-logo-3-1.png" alt="Lean Station">
            <a href="https://leanstation.com" target="_blank">Open Source Initiative</a>
        </div>
        """, unsafe_allow_html=True)

# Login
if not st.session_state.is_authenticated:
    st.title("Prefab Parser for Singapore PPVC/Precast")
    with st.expander("ℹ️ What does this app do?"):
        st.markdown("""
                Welcome! This app shall automatic precast or PPVC component identification directly from your construction drawings.

                Upload a PDF and choose from one of several advanced extraction methods.

                **Example Component Code Format:** `1TD2aX-3`

                Each part is decoded as:
                - `1` or `2`: Piece / Precast Type: 1-precast standard Piece type or 2-Secondary/reinforced/specialized piece 
                
                - `TD`, `AC`, `TC`, etc.: Structural type: - A = Architectural panel - T = Top floor related - C = Corridor panel - D = Door/partition related - S = Slab - W = Wall
                
                - `2a`, `2bX`: Unit Type: building block, or design variant
                
                - `-3`: Piece sequence number (where it fits in that block)
                
                - `-CS` or `-E` or `-P` or `-M` or `-L`: Addiitonal Suffix: Special characteristics:- CS = Corner Section- E = End piece- P = Panel- M = Mirror (mirrored side)- L = Left Handed version    

                The app detects level indicators like `(2, 4-6)` and calculates total quantities based on this.

                🔍 Export extracted data to Excel, give confidence feedback, and store everything securely in a database.
                
                ---
            """)
    st.text("🔐 Login or Register")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")

        # Hidden field for CSRF protection
        st.markdown(f'<input type="hidden" name="csrf_token" value="{st.session_state.csrf_token}">', unsafe_allow_html=True)

    if st.button("Login"):
        if not check_rate_limit():
            st.stop()
        st.session_state.login_attempts += 1
        st.session_state.last_attempt_time = time.time()

        auth = authenticate_user(login_email, login_password)
        if auth:
            name, role = auth[0], auth[1]
            st.session_state.is_authenticated = True
            st.session_state.user_name = name
            st.session_state.user_email = login_email
            st.session_state.user_role = role
            st.session_state.login_attempts = 0
            st.rerun()
        else:
            st.error("Invalid credentials.")


    with tab2:
        reg_name = st.text_input("Name")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_pass")
        reg_confirm_password = st.text_input("Confirm Password", type="password")

        if st.button("Register"):
            if not check_rate_limit():
                st.stop()

            if reg_password != reg_confirm_password:
                st.error("Passwords do not match.")
            elif reg_name and reg_email and reg_password:
                try:
                    add_user(reg_name, reg_email, "user", reg_password)
                    st.success("🎉 Registration successful. Please log in.")
                    st.session_state.login_attempts = 0
                except Exception as e:
                    st.error(f"⚠️ Error: {e}")
            else:
                st.warning("Please fill in all fields.")
    
    # Display footer on login page
    display_footer()
    st.stop()

# Logout button
if st.button("Logout"):
    for key in st.session_state.keys():
        if key == "df":
            st.session_state[key] = None
        elif key == "is_authenticated":
            st.session_state[key] = False
        elif key == "csrf_token":
            st.session_state[key] = secrets.token_hex(16)
        else:
            st.session_state[key] = ""
    st.rerun()

st.title(f"Welcome, {st.session_state.user_name}!")

# Admin Dashboard with secure queries
if st.session_state.user_role == "admin":
    st.header("🔧 Admin Dashboard: All User Uploads")
    conn = sqlite3.connect("data/extraction_log.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM extraction_logs ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    conn.close()

    # Get column names
    conn = sqlite3.connect("data/extraction_log.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(extraction_logs)")
    columns = [info[1] for info in cursor.fetchall()]
    conn.close()

    df_logs = pd.DataFrame(logs, columns=columns)
    st.dataframe(df_logs)
    st.download_button("📥 Download Log", df_logs.to_csv(index=False), "logs.csv", "text/csv")
    st.stop()

# App for Users
uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])

# Perform OCR using Azure
def perform_azure_ocr(image_stream, client):
    read_response = client.read_in_stream(image_stream, raw=True)
    operation_location = read_response.headers["Operation-Location"]
    operation_id = operation_location.split("/")[-1]

    # Wait for OCR result
    while True:
        result = client.get_read_result(operation_id)
        if result.status not in ['notStarted', 'running']:
            break
        time.sleep(1)

    extracted_text = ""
    if result.status == 'succeeded':
        for page in result.analyze_result.read_results:
            for line in page.lines:
                extracted_text += line.text + "\n"
    #debug
   # st.text_area("🧾 Raw OCR Output", extracted_text, height=300)

    return extracted_text

#perform OCR using OCR Space
def ocr_space_file(file, api_key, language='eng'):
    """ OCR.Space API request with local file """
    payload = {
        'isOverlayRequired': False,
        'apikey': api_key,
        'language': language,
        'OCREngine': 2  # optional: use engine 1 or 2
    }
    r = requests.post(
        'https://api.ocr.space/parse/image',
        files={'file': file},
        data=payload,
    )
    result = r.json()
    if result.get("IsErroredOnProcessing") or "ParsedResults" not in result:
        return ""
    return result["ParsedResults"][0]["ParsedText"]

# perform OCR using Google Vision OCR
def extract_text_google_vision(image):
    from google.cloud.vision_v1 import types
    import io

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    content = img_byte_arr.read()
    image = types.Image(content=content)

    response = client.text_detection(image=image)
    texts = response.text_annotations
    return texts[0].description if texts else ""

#Patterns using regex
component_pattern = r'\b[1-2][A-Z]{1,3}[0-9a-zA-Z\-]*\b'
bracket_pattern = r'\((?:\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)\)'

def count_levels(level_str):
    level_str = level_str.strip("()")
    total = 0
    for part in level_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = map(int, part.split("-"))
            total += (end - start + 1)
        elif part.isdigit():
            total += 1
    return total

def extract_component_with_levels(text):
    pairs = []
    tokens = re.findall(rf'{component_pattern}|{bracket_pattern}', text)
    current_component = None
    levels = []

    for token in tokens:
        if re.match(component_pattern, token):
            if current_component:
                level_text = ", ".join(levels)
                total_qty = sum(count_levels(lvl) for lvl in levels)
                pairs.append((current_component, level_text, total_qty))
            current_component = token
            levels = []
        elif re.match(bracket_pattern, token):
            levels.append(token)

    if current_component:
        level_text = ", ".join(levels)
        total_qty = sum(count_levels(lvl) for lvl in levels)
        pairs.append((current_component, level_text, total_qty))

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
    
    elif method == "OCR Space API":
        images = convert_from_bytes(file.read(), dpi=300)
        for img in images:
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            text += ocr_space_file(img_byte_arr, api_key=st.secrets["ocr_space"]["key"])

    elif method == "Microsoft Azure OCR":
        AZURE_ENDPOINT = st.secrets["azure"]["endpoint"]
        AZURE_KEY = st.secrets["azure"]["key"]
        client = init_azure_client(AZURE_ENDPOINT, AZURE_KEY)

        images = convert_from_bytes(file.read())
        for img in images:
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            text += perform_azure_ocr(img_byte_arr, client)
    
    elif method == "Google Vision OCR":
        images = convert_from_bytes(file.read(), dpi=300)
        for img in images:
            text += extract_text_google_vision(img)
    
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

    # the methods of extraction, this list can be expanded as time goes by..
    methods = [
        "pdfplumber",
        "PyMuPDF",
        "OCR Space API",
        "Microsoft Azure OCR",
        "Google Vision OCR"
    ]
        
    method_desc = {
        "pdfplumber": "Extracts text using layout-aware parsing from PDF text layers.",
        "PyMuPDF": "Extracts block-level structured text using the PyMuPDF engine.",
        "OCR Space API": "Uses the OCR.Space cloud API for full image-based text recognition.",
        "Microsoft Azure OCR": "Extracts text via Microsoft Azure's Computer Vision OCR service.",
        "Google Vision OCR": "Uses Google Vision API for advanced OCR extraction with layout detection."
    }

    # method = st.radio("Choose extraction method", ["pdfplumber", "PyMuPDF", "OCR Space", "Microsoft Azure OCR", "Google Vision"])
    method = st.radio("Choose Extraction Method", methods)

    with st.expander("ℹ️ Description of selected method"):
        st.markdown(method_desc[method])
        if method != st.session_state.rated_method:
            st.session_state.emoji_rating = 0
            st.session_state.feedback_type = None
            st.session_state.rated_method = None
            st.session_state.show_toast = False

    # Store extraction method in session state to persist across reruns
    if "current_method" not in st.session_state:
        st.session_state.current_method = method
    else:
        st.session_state.current_method = method

    # Extract button
    if st.button("Extract Components & Levels"):
        with st.spinner("🔄 Extracting..."):
            uploaded_file.seek(0)
            full_text = extract_text(uploaded_file, method)
            pairs = extract_component_with_levels(full_text)
            df = pd.DataFrame(pairs, columns=["Component Code", "Level(s)", "Component Quanity"])
            df = df.drop_duplicates().sort_values("Component Code").reset_index(drop=True)
            st.session_state.df = df
            
            # Clear previous download state on new extraction
            if "download_clicked" in st.session_state:
                st.session_state.download_clicked = False
            if "excel_bytes" in st.session_state:
                del st.session_state.excel_bytes

        # Secure logging
        log_event(
            user_email=st.session_state.user_email,
            filename=uploaded_file.name,
            method=method,
            count=len(df),
            feedback=None,
            feedback_type=None,
            file_bytes=uploaded_file.getvalue()
        )

        st.toast(f"✅ Extracted {len(df)} components using {method}.")

        if st.session_state.df is not None:
            st.dataframe(st.session_state.df, use_container_width=True)
            
            # Excel download
            towrite = io.BytesIO()
            if st.session_state.get("df") is not None:
                st.session_state.df.to_excel(towrite, index=False, sheet_name="Components")
                towrite.seek(0)
                
                # Store the Excel bytes in session state to prevent recomputation
                if "excel_bytes" not in st.session_state:
                    st.session_state.excel_bytes = towrite.getvalue()
                
                # Check if download was clicked previously
                if "download_clicked" not in st.session_state:
                    st.session_state.download_clicked = False
                
                # Create a download button
                download_clicked = st.download_button(
                    "📥 Download Excel", 
                    st.session_state.excel_bytes, 
                    "components_with_levels.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_excel_button"
                )
                
                # Only log if newly clicked
                if download_clicked and not st.session_state.download_clicked:
                    st.session_state.download_clicked = True
                    try:
                        # Fix for NoneType + str issue
                        method_name = st.session_state.rated_method if st.session_state.rated_method else method
                        log_event(
                            user_email=st.session_state.user_email,
                            filename=f"{method_name}_download",
                            method=method_name,
                            count=len(st.session_state.df),
                            feedback="📥 Downloaded Excel",
                            feedback_type="download"
                        )
                        st.toast("📦 Excel file downloaded successfully.")
                    except Exception as e:
                        st.warning(f"Logging issue: {e}")
            else:
                st.warning("⚠️ No data available to export. Please run an extraction first.")
            

    # Feedback section in a container to ensure persistence
    with st.container():
        st.markdown("### 😊 Feedback")
        
        emoji_map = {1: "😠", 2: "😕", 3: "😐", 4: "🙂", 5: "😄"}
        rating_label = {1: "Very Bad", 2: "Bad", 3: "Neutral", 4: "Good", 5: "Very Good"}
        
        # Create a unique key based on the method and file
        feedback_key = f"{method}_{uploaded_file.name}" if uploaded_file else f"{method}_feedback"
        
        # Set up persistent state keys for this feedback session
        if f"feedback_given_{feedback_key}" not in st.session_state:
            st.session_state[f"feedback_given_{feedback_key}"] = False
        
        # Show feedback options if feedback hasn't been given
        if not st.session_state[f"feedback_given_{feedback_key}"]:
            st.markdown("#### How was the extraction result?")
            
            # Create columns for emoji ratings
            emoji_cols = st.columns(5)
            for i in range(1, 6):
                if emoji_cols[i - 1].button(emoji_map[i], key=f"emoji_{feedback_key}_{i}"):
                    st.session_state.emoji_rating = i
                    st.session_state.feedback_type = "emoji"
                    st.session_state.rated_method = method
                    st.session_state.show_toast = True
                    st.session_state[f"feedback_given_{feedback_key}"] = True
                    st.rerun()
            
            # Downvote option
            if st.button("👎 This method did not work well", key=f"downvote_{feedback_key}"):
                st.session_state.emoji_rating = 0
                st.session_state.feedback_type = "downvote"
                st.session_state.rated_method = method
                st.session_state.show_toast = True
                st.session_state[f"feedback_given_{feedback_key}"] = True
                st.rerun()
        # If feedback was already given, show a summary
        else:
            if st.session_state.feedback_type == "emoji" and st.session_state.emoji_rating in emoji_map:
                emoji = emoji_map[st.session_state.emoji_rating]
                label = rating_label[st.session_state.emoji_rating]
                st.success(f"Your Feedback: {emoji} **{label}**")
            elif st.session_state.feedback_type == "downvote":
                st.info("Your Feedback: 👎 This method did not work well")
            
            # Option to give new feedback
            if st.button("Change your feedback?", key=f"reset_feedback_{feedback_key}"):
                st.session_state[f"feedback_given_{feedback_key}"] = False
                st.rerun()

            # Process feedback if toast needs to be shown
            if st.session_state.show_toast:
                # Initialize feedback variable with default values
                feedback = "👎" if st.session_state.feedback_type == "downvote" else (
                    emoji_map[st.session_state.emoji_rating] if st.session_state.emoji_rating in emoji_map else "Unknown"
                )
                feedback_type = st.session_state.feedback_type or "unknown"
                
                try:
                    # Fix for NoneType + str issue
                    method_name = st.session_state.rated_method if st.session_state.rated_method else method
                    log_event(
                        user_email=st.session_state.user_email,
                        filename=f"{method_name}_feedback",
                        method=method_name,
                        count=len(st.session_state.df) if st.session_state.df is not None else 0,
                        feedback=feedback,
                        feedback_type=feedback_type
                    )
                    # Show toast and update history immediately
                    st.toast(f"You rated: {feedback} — Method: {method}")
                except Exception as e:
                    st.warning(f"Logging issue: {e}")
                
                # Reset toast flag after processing
                st.session_state.show_toast = False

    # Show user history with secure queries
    # This is outside the feedback and Excel download sections to always be visible
    st.markdown("---")
    st.markdown("### 📂 History")
    
    # Force refresh history after actions by using a timestamp key
    if "history_refresh_key" not in st.session_state:
        st.session_state.history_refresh_key = time.time()
        
    # Add a refresh button for history
    if st.button("🔄 Refresh History"):
        st.session_state.history_refresh_key = time.time()
        st.rerun()
        
    try:
        user_logs = get_user_logs(st.session_state.user_email)
        df_user_logs = pd.DataFrame(user_logs, columns=["Events", "method", "components count", "timestamp", "Activity"])
        df_user_logs['timestamp'] = pd.to_datetime(df_user_logs['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Display history in a container
        with st.container():
            st.dataframe(df_user_logs, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not display history: {e}")

    # Display footer at the bottom of every page
    display_footer()



