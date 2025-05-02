import streamlit as st
import streamlit.components.v1 as components
import requests

# Set page config first
st.set_page_config(page_title="Welcome to Component Extractor", layout="centered")

st.title("👋 Welcome to the Precast Component Extractor")
st.markdown("Please verify that you are human before continuing to the login page.")

# Session to track CAPTCHA verification
if "captcha_verified" not in st.session_state:
    st.session_state.captcha_verified = False

# Debug button - keep this during testing
if st.button("DEBUG: Force Verification"):
    st.session_state.captcha_verified = True
    st.rerun()

# Turnstile component
components.html(f"""
    <script>
    function postCaptcha(token) {{
        // Send token to parent window
        window.parent.postMessage({{ type: 'setCaptchaToken', token: token }}, '*');
        console.log("Token sent to parent:", token);
    }}
    </script>
    <div class="cf-turnstile" data-sitekey="{st.secrets['turnstile']['sitekey']}" data-callback="postCaptcha"></div>
    <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
""", height=120)

# JavaScript to handle the message from the iframe
components.html("""
    <script>
    window.addEventListener("message", (event) => {
        if (event.data && event.data.type === 'setCaptchaToken') {
            const token = event.data.token;
            console.log("Token received in parent:", token);
            
            // Find the hidden input field
            const streamlitInput = document.querySelector('input[data-testid="stTextInput"][aria-label="CAPTCHA"]');
            if (streamlitInput) {
                // Set value and trigger input event to notify Streamlit
                streamlitInput.value = token;
                streamlitInput.dispatchEvent(new Event('input', { bubbles: true }));
                
                // Submit the form automatically
                setTimeout(() => {
                    const verifyButton = document.querySelector('button[kind="primaryFormSubmit"]');
                    if (verifyButton) {
                        verifyButton.click();
                    }
                }, 500);
            }
        }
    });
    </script>
""", height=0)

# Hidden field to hold the token
captcha_token = st.text_input("CAPTCHA", key="captcha_token", label_visibility="hidden")

# Verification
if not st.session_state.captcha_verified and captcha_token:
    with st.form("verify_form"):
        st.write("Verifying your CAPTCHA...")
        submitted = st.form_submit_button("Verify", type="primary")
        
        if submitted or captcha_token:
            response = requests.post("https://challenges.cloudflare.com/turnstile/v0/siteverify", data={
                "secret": st.secrets["turnstile"]["secret"],
                "response": captcha_token
            }).json()
            
            if response.get("success"):
                st.session_state.captcha_verified = True
                st.success("✅ Verified! You may now continue to the login page.")
            else:
                st.error("❌ CAPTCHA verification failed.")

# Redirect logic
if st.session_state.captcha_verified:
    st.success("✅ You are verified!")
    
    # IMPORTANT: This is the correct format - just the filename without the directory
    if st.button("➡️ Continue to Login", type="primary"):
        try:
            # Just use the filename without 'pages/'
            st.switch_page("app.py")
        except Exception as e:
            st.error(f"Error during page switch: {e}")
            st.write("Available pages:")
            import os
            if os.path.exists("pages"):
                st.write([f for f in os.listdir("pages") if f.endswith(".py")])
            else:
                st.write("No 'pages' directory found")

                # Add this debugging code to intro.py to check your setup:

#testing code -> delete later

import os
import streamlit as st

# Check if pages directory exists
st.write(f"Current working directory: {os.getcwd()}")
pages_dir = os.path.join(os.getcwd(), "pages")
st.write(f"Pages directory exists: {os.path.exists(pages_dir)}")

# List all pages
if os.path.exists(pages_dir):
    page_files = [f for f in os.listdir(pages_dir) if f.endswith(".py")]
    st.write(f"Available pages: {page_files}")
else:
    st.write("No 'pages' directory found")

# Try manual navigation with buttons
if st.button("Try Direct Navigation"):
    try:
        st.switch_page("app.py")
    except Exception as e:
        st.error(f"Error: {e}")