import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin import auth
import json
import google.generativeai as genai
from gtts import gTTS
import base64
import smtplib
import random
from datetime import datetime, timedelta
from email.mime.text import MIMEText
import hashlib
import os
            
# ---------------- FIREBASE SETUP ----------------
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["FIREBASE"]))
    firebase_admin.initialize_app(cred)

# Always set db after Firebase is initialized (even if it was already initialized)
db = firestore.client()
    
st.markdown("""
<style>
/* Make radio button text white */
.stRadio > div > label > div {
    color: white !important;
}

.stRadio > div > label {
    color: white !important;
}

/* Target the actual text content */
div[data-baseweb="radio"] label span {
    color: white !important;
}

/* More comprehensive targeting */
.stRadio * {
    color: white !important;
}

/* Specific targeting for radio button text */
div[role="radiogroup"] label {
    color: white !important;
    font-weight: 500 !important;
}

div[role="radiogroup"] label > div {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Overall App Background */
.stApp {
    background-color: rgba(15, 23, 42, 0.95);
    color: white !important;
}

/* Desktop-specific improvements */
@media (min-width: 768px) {
    /* Force ALL text to be white with better rendering on desktop */
    * {
        color: white !important;
        -webkit-font-smoothing: antialiased !important;
        -moz-osx-font-smoothing: grayscale !important;
        text-rendering: optimizeLegibility !important;
    }
    
    /* Input fields - Desktop optimized */
    .stTextInput > div > div > input,
    .stTextArea > div > textarea,
    input[type="text"],
    input[type="password"],
    input[type="email"],
    textarea {
        background-color: rgba(0, 0, 0, 0.6) !important;
        color: white !important;
        border: 2px solid rgba(255, 255, 255, 0.4) !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        text-shadow: 0 0 1px rgba(255, 255, 255, 0.3) !important;
        letter-spacing: 0.5px !important;
    }
    
    /* Radio button text - Desktop specific */
    .stRadio label,
    .stRadio > div,
    .stRadio * {
        color: white !important;
        font-weight: 700 !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5) !important;
        font-size: 16px !important;
    }
}

/* Mobile styles (keep current behavior) */
@media (max-width: 767px) {
    * {
        color: white !important;
    }
    
    .stTextInput > div > div > input,
    .stTextArea > div > textarea,
    input, textarea {
        background-color: rgba(0, 0, 0, 0.4) !important;
        color: white !important;
        border: 2px solid rgba(255, 255, 255, 0.3) !important;
        font-weight: 500 !important;
    }
}

/* Universal improvements */
input::placeholder,
textarea::placeholder {
    color: rgba(255, 255, 255, 0.8) !important;
    font-weight: 500 !important;
}

/* Headings */
h1, h2, h3, h4, h5, h6 {
    color: white !important;
    font-weight: bold !important;
    text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3) !important;
}

/* Labels */
label {
    color: white !important;
    font-weight: 600 !important;
    text-shadow: 0 0 1px rgba(255, 255, 255, 0.2) !important;
}

/* Buttons */
.stButton > button {
    background-color: rgba(34, 197, 94, 0.9);
    color: white !important;
    font-weight: bold;
    border-radius: 6px;
    border: none;
    text-shadow: none !important;
}

.stButton > button:hover {
    background-color: rgba(21, 128, 61, 1.0);
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Sidebar background - Dark blue with rgba */
.css-1d391kg, 
.st-emotion-cache-16idsys,
section[data-testid="stSidebar"] {
    background-color: rgba(30, 58, 138, 1) !important; /* Dark blue */
}

section[data-testid="stSidebar"] > div {
    background-color: rgba(30, 58, 138, 0.95) !important; /* Dark blue with slight transparency */
}

/* Alternative rgba dark blue options - choose one */
/* background-color: rgba(30, 64, 175, 0.95) !important; */ /* Slightly lighter blue */
/* background-color: rgba(29, 78, 216, 0.95) !important; */ /* Medium blue */
/* background-color: rgba(15, 23, 42, 0.95) !important; */ /* Very dark blue-gray - matches main */
/* background-color: rgba(30, 41, 59, 0.95) !important; */ /* Dark slate blue */
/* background-color: rgba(12, 74, 110, 0.95) !important; */ /* Dark cyan-blue */

/* Sidebar content text to remain white */
section[data-testid="stSidebar"] * {
    color: white !important;
}

/* Your existing styles... */
.stApp {
    background-color: rgba(15, 23, 42, 0.95);
    color: white !important;
}

/* Rest of your existing CSS... */
</style>
""", unsafe_allow_html=True)


# ---------------- SESSION ----------------
st.set_page_config(page_title="SkillSwap Cloud", layout="wide")
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""


# === SESSION SETUP & THEME ===
st.set_page_config(page_title="SkillSwap Cloud", layout="wide")
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = ""
if "dark_mode" not in st.session_state: st.session_state.dark_mode = True

def theme_toggle():
    theme = st.sidebar.checkbox("🌗 Dark Mode", value=st.session_state.dark_mode)
    st.session_state.dark_mode = theme
    css = "<style>"
    if theme:
        css += "body{color:white;background-color:#222;} .stButton>button{color:white;background:#5c5c8a;}"
    else:
        css += "body{color:black;background-color:#f5f5fa;} .stButton>button{color:black;background:#e0e0e0;}"
    css += "</style>"
    st.markdown(css, unsafe_allow_html=True)

theme_toggle()

# === GLOBAL CSS for WhatsApp style ===
st.markdown("""
<style>
body {font-family:'Segoe UI',sans-serif;background-color:#e5ddd5;}
.sidebar .sidebar-content{background:#075e54;color:white;}
.chat-header{background:#075e54;padding:15px;color:white;border-radius:0 0 5px 5px;}
.message-bubble{padding:10px 14px;border-radius:12px;margin:6px 0;max-width:75%;box-shadow:0 1px 3px rgba(0,0,0,0.1);clear:both;}
.message-sent{background:#dcf8c6;float:right;}
.message-received{background:white;float:left;}
.clearfix::after{content:'';clear:both;display:table;}
</style>
""", unsafe_allow_html=True)



# --- Utility Functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_data(username):
    if not username.strip():
        return None
    doc = db.collection("users").document(username).get()
    return doc.to_dict() if doc.exists else None

def generate_otp():
    return str(random.randint(100000, 999999))

def send_email_otp(receiver_email, otp_code):
    sender_email = st.secrets["EMAIL_SENDER"]
    sender_password = st.secrets["EMAIL_PASSWORD"]
    msg = MIMEText(f"Your SkillSwap verification code is: {otp_code}")
    msg['Subject'] = "SkillSwap OTP Verification"
    msg['From'] = sender_email
    msg['To'] = receiver_email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send OTP: {e}")
        return False

def send_password_reset_otp(email):
    users = db.collection("users").stream()
    for user in users:
        d = user.to_dict()
        if d.get("email") == email:
            code = generate_otp()
            db.collection("reset_otps").document(email).set({
                "code": code,
                "timestamp": datetime.utcnow().isoformat()
            })
            return send_email_otp(email, code)
    st.error("Email not found.")
    return False

def verify_reset_otp(email, entered_code):
    doc = db.collection("reset_otps").document(email).get()
    if doc.exists:
        data = doc.to_dict()
        timestamp = datetime.fromisoformat(data["timestamp"])
        if (datetime.utcnow() - timestamp).total_seconds() > 600:
            st.error("Code expired.")
            return False
        if entered_code == data["code"]:
            db.collection("reset_otps").document(email).delete()
            return True
        st.error("Incorrect code.")
    else:
        st.error("No OTP request found.")
    return False

# --- Login Page ---
def login_page():
    st.subheader("🔐 Login")
    u = st.text_input("Username", key="login_username")
    p = st.text_input("Password", type="password", key="login_password")
    if st.button("Login", key="login_button"):
        d = get_user_data(u)
        if d and d.get("password") == hash_password(p):
            if not d.get("verified"):
                st.warning("Please verify your email.")
                return
            st.session_state.logged_in = True
            st.session_state.username = u
            st.success(f"Welcome back, {u}!")
            st.rerun()
        else:
            st.error("Invalid credentials.")

# --- Password Reset Page ---
def password_reset():
    st.subheader("🔑 Forgot Password")
    step = st.session_state.get("reset_step", "request")

    if step == "request":
        email = st.text_input("Enter your email", key="reset_email_input")
        if st.button("Send Reset OTP", key="reset_send_otp"):
            if send_password_reset_otp(email):
                st.session_state.reset_email = email
                st.session_state.reset_step = "verify"
                st.rerun()

    elif step == "verify":
        code = st.text_input("Enter OTP code", key="reset_verify_code")
        if st.button("Verify Code", key="reset_verify_btn"):
            if verify_reset_otp(st.session_state.reset_email, code.strip()):
                st.session_state.reset_step = "set_password"
                st.rerun()

    elif step == "set_password":
        new_pass = st.text_input("Enter new password", type="password", key="reset_new_pass")
        if st.button("Reset Password", key="reset_pass_btn"):
            users = db.collection("users").stream()
            for user in users:
                d = user.to_dict()
                if d.get("email") == st.session_state.reset_email:
                    db.collection("users").document(user.id).update({
                        "password": hash_password(new_pass)
                    })
                    st.success("Password updated!")
                    del st.session_state.reset_email
                    st.session_state.reset_step = "request"
                    break

# --- Signup Page ---
def signup_page():
    st.subheader("📝 Sign Up")
    u = st.text_input("Username", key="signup_username")
    email = st.text_input("Email", key="signup_email")
    p = st.text_input("Password", type="password", key="signup_password")

    cooldown_remaining = None
    if u:
        ver_doc = db.collection("email_verifications").document(u).get()
        if ver_doc.exists:
            data = ver_doc.to_dict()
            last_time = datetime.fromisoformat(data.get("timestamp"))
            elapsed = (datetime.utcnow() - last_time).total_seconds()
            if elapsed < 60:
                cooldown_remaining = int(90 - elapsed)
                countdown_placeholder = st.empty()

    send_button_disabled = cooldown_remaining is not None
    if send_button_disabled:
        countdown_placeholder.warning(f"⏳ Please wait {cooldown_remaining} seconds before requesting another code.")

    send_clicked = st.button("Send Verification Code", key="signup_send_code", disabled=send_button_disabled)

    if send_clicked:
        if not u or not email or not p:
            st.error("All fields required.")
        elif get_user_data(u):
            st.error("Username taken.")
        else:
            now = datetime.utcnow()
            code = generate_otp()
            if send_email_otp(email, code):
                db.collection("email_verifications").document(u).set({
                    "email": email,
                    "code": code,
                    "password": hash_password(p),
                    "verified": False,
                    "timestamp": now.isoformat()
                })
                st.session_state.signup_user = u
                st.success("Code sent. Enter below.")

    if "signup_user" in st.session_state:
        st.info(f"Verify account for {st.session_state.signup_user}")
        input_code = st.text_input("Verification Code", key="signup_verification_code")
        if st.button("Verify", key="signup_verify_button"):
            doc = db.collection("email_verifications").document(st.session_state.signup_user).get()
            if doc.exists:
                data = doc.to_dict()
                if input_code == data.get("code"):
                    db.collection("users").document(st.session_state.signup_user).set({
                        "email": data["email"],
                        "password": data["password"],
                        "verified": True,
                        "signup_time": datetime.utcnow()  # ✅ Add signup timestamp here
                    })
                    db.collection("email_verifications").document(st.session_state.signup_user).delete()
                    st.success("Account created!")
                    del st.session_state.signup_user
                else:
                    st.error("Incorrect code.")

#--- App Page Config ---
st.set_page_config(page_title="SkillSwap Secure Auth", layout="centered")
                
# === INTERFACE FUNCTIONS ===
def profile_edit():
    d = get_user_data(st.session_state.username)
    if d:
        st.sidebar.header("👤 Edit Profile")
        bio = st.sidebar.text_area("Bio", value=d.get("bio", ""), key="profile_bio")
        role = st.sidebar.selectbox(
            "Role", ["Student", "Teacher"],
            index=["Student", "Teacher"].index(d.get("role", "Student")),
            key="profile_role"
        )
        if st.sidebar.button("Update Profile", key="update_profile_btn"):
            db.collection("users").document(st.session_state.username).update({
                "bio": bio,
                "role": role
            })
            st.sidebar.success("Profile updated!", icon="✅")
            
def show_notifications():
    d = get_user_data(st.session_state.username)
    if d and d.get("notifications"):
        st.sidebar.header("🔔 Notifications")
        for n in d["notifications"]:
            st.sidebar.info(n)
        if st.sidebar.button("Clear All"):
            db.collection("users").document(st.session_state.username).update({"notifications":[]})
            st.sidebar.success("Cleared!")

import time  # Place this at the top of your script
def chat_interface():
    import time
    from datetime import datetime

    # Initialize dynamic message input key
    if "msg_key" not in st.session_state:
        st.session_state["msg_key"] = "msg_input_1"

    st.markdown("""
    <style>
    /* Basic layout fixes */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Sidebar styling */
    .stSidebar > div {
        background-color: #1e1e1e;
    }

    /* Text colors */
    .stMarkdown h3 {
        color: white;
    }

    /* Selectbox styling */
    .stSelectbox label {
        color: white;
        font-weight: 600;
    }

    /* Text input styling */
    .stTextInput input {
        background-color: #f0f0f0;
        color: #333;
        border-radius: 25px;
        padding: 12px 20px;
        border: 1px solid #ddd;
    }

    /* Send button styling */
    .stButton button {
        background-color: #007bff;
        color: white;
        border: none;
        border-radius: 8px;
        width: 50px;
        height: 50px;
        font-size: 18px;
    }

    .stButton button:hover {
        background-color: #0056b3;
    }

    /* Chat header */
    .chat-header {
        background: #0f172a;
        padding: 15px 20px;
        border-radius: 10px 10px 0 0;
        border: 1px solid #ddd;
        color: #333;
        margin-bottom: 0;
    }

    .partner-avatar {
        width: 45px; 
        height: 45px; 
        border-radius: 50%;
        background: #6c757d; 
        color: white;
        display: flex; 
        align-items: center; 
        justify-content: center;
        font-weight: bold;
        font-size: 18px;
    }

    /* Messages container */
    .messages-container {
        height: 400px; 
        overflow-y: auto;
        padding: 15px;
        background: #ffffff;
        border: 1px solid #ddd;
        border-top: none;
        border-radius: 0 0 10px 10px;
    }

    /* Message bubbles */
    .message-sent {
        background: #007bff;
        color: white;
        padding: 8px 12px;
        border-radius: 18px;
        margin: 5px 0 5px auto;
        max-width: 70%;
        font-size: 14px;
        word-wrap: break-word;
        display: block;
        width: fit-content;
        margin-left: auto;
    }

    .message-received {
        background: #f1f3f4;
        color: #333;
        padding: 8px 12px;
        border-radius: 18px;
        margin: 5px auto 5px 0;
        max-width: 70%;
        font-size: 14px;
        word-wrap: break-word;
        display: block;
        width: fit-content;
        margin-right: auto;
    }

    .message-time {
        font-size: 11px;
        color: #666;
        text-align: right;
        margin-top: 4px;
    }

    .no-messages {
        text-align: center;
        color: #666;
        padding: 40px;
        font-style: italic;
    }

    /* Input area */
    .input-area {
        background: #0f172a;
        padding: 10px 15px;
        border: 1px solid #ccc;
        border-top: 1px solid #ddd;
        border-radius: 0 0 10px 10px;
    }

    /* Back button styling */
    .stButton button[title="Go back to contact selection"] {
        background-color: #34495e;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 14px;
        width: auto;
        height: auto;
    }

    .stButton button[title="Go back to contact selection"]:hover {
        background-color: #2c3e50;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 👥 Select Chat Partner")

    # Load users
    try:
        users = [doc.id for doc in db.collection("users").stream() if doc.id != st.session_state.username]
        if not users:
            st.warning("⚠️ No other users available to chat with.")
            return
    except Exception as e:
        st.error(f"❌ Error loading users: {str(e)}")
        return

    # Initialize chat state
    if "current_partner" not in st.session_state:
        st.session_state["current_partner"] = ""
    if "reset_selectbox" not in st.session_state:
        st.session_state["reset_selectbox"] = False
    
    # Reset selectbox if needed
    if st.session_state["reset_selectbox"]:
        st.session_state["reset_selectbox"] = False
        st.rerun()
    
    partner = st.selectbox(
        "Choose a contact:", 
        [""] + users, 
        key="partner_select",
        index=0 if st.session_state["current_partner"] == "" else ([""] + users).index(st.session_state["current_partner"]) if st.session_state["current_partner"] in users else 0
    )
    
    # Update current partner when selection changes
    if partner != st.session_state.get("current_partner", ""):
        st.session_state["current_partner"] = partner
    
    # Use current_partner for chat logic
    if not st.session_state["current_partner"]:
        st.info("💬 Select a contact to start chatting")
        return

    chat_id = "_".join(sorted([st.session_state.username, st.session_state["current_partner"]]))

    # Chat container with fixed dimensions
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    header_col1, header_col2 = st.columns([1, 10])
    
    with header_col1:
        if st.button("← Back", key="back_btn", help="Go back to contact selection"):
            # Clear the current partner and trigger selectbox reset
            st.session_state["current_partner"] = ""
            st.session_state["reset_selectbox"] = True
            if 'live_chat' in st.session_state:
                st.session_state.live_chat = False
            st.rerun()
    
    with header_col2:
        partner_initial = st.session_state["current_partner"][0].upper()
        st.markdown(f'''
            <div class="chat-header">
                <div style="display:flex;align-items:center;gap:12px;">
                    <div class="partner-avatar">{partner_initial}</div>
                    <div>
                        <h4 style="margin:0;color:#333;">{st.session_state["current_partner"]}</h4>
                        <div style="color:#28a745;font-size:12px;">● online</div>
                    </div>
                </div>
            </div>
        ''', unsafe_allow_html=True)

    # Messages area
    st.markdown('<div class="messages-container">', unsafe_allow_html=True)
    
    try:
        messages = db.collection("chats").document(chat_id).collection("messages").order_by("timestamp").stream()
        message_count = 0
        
        for m in messages:
            d = m.to_dict()
            if not d or 'text' not in d:
                continue
                
            message_count += 1
            sent = d["sender"] == st.session_state.username
            bubble_class = "message-sent" if sent else "message-received"
            
            # Format timestamp
            try:
                time_str = d.get("timestamp", datetime.now()).strftime("%H:%M")
            except:
                time_str = "00:00"
            
            # Clean message text
            message_text = str(d['text']).replace('<', '&lt;').replace('>', '&gt;')
            
            st.markdown(f'''
                <div class="{bubble_class}">
                    <div>{message_text}</div>
                    <div class="message-time">{time_str}</div>
                </div>
            ''', unsafe_allow_html=True)
        
        if message_count == 0:
            st.markdown('<div class="no-messages">🤝 Start your conversation below</div>', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"❌ Error loading messages: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

    # Message input
    st.markdown('<div class="input-area">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([5, 1])
    
    with col1:
        msg = st.text_input(
            "",
            value="",
            placeholder="Type a message...",
            key=st.session_state["msg_key"],
            label_visibility="collapsed"
        )
    
    with col2:
        send_pressed = st.button("➤", key="send_btn")
    
    st.markdown('</div>', unsafe_allow_html=True)

    # Handle sending message
    if send_pressed and msg.strip():
        try:
            db.collection("chats").document(chat_id).collection("messages").add({
                "sender": st.session_state.username,
                "receiver": partner,
                "text": msg.strip(),
                "timestamp": datetime.now()
            })
            # Automatically clear input after sending
            current_key = int(st.session_state["msg_key"].split("_")[-1])
            st.session_state["msg_key"] = f"msg_input_{current_key + 1}"
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error sending message: {str(e)}")
    elif send_pressed:
        st.warning("⚠️ Please enter a message")

    # Auto-clear input if Enter key is pressed (simulate send)
    if msg and msg != st.session_state.get("last_msg", ""):
        # Check if user pressed Enter by detecting new line or if message changed significantly
        st.session_state["last_msg"] = msg

    # Controls - Only Live Chat checkbox now
    st.markdown("---")
    
    live = st.checkbox("🔴 Live Chat", value=True)

    st.markdown('</div>', unsafe_allow_html=True)  # Close chat wrapper

    # Smart refresh - only refresh if needed and reduce frequency when stable
    if live:
        current_time = time.time()
        
        # Only refresh every 1 second instead of 0.2 to reduce flicker
        if current_time - st.session_state.get("last_refresh_time", 0) > 1.0:
            st.session_state["last_refresh_time"] = current_time
            st.rerun()
        else:
            # Sleep without refresh to maintain responsiveness
            time.sleep(0.1)
                    
def view_profiles():
    st.subheader("🧑‍🏫 Browse Users")
    search = st.text_input("Search skill or role")
    us = [(doc.id,doc.to_dict()) for doc in db.collection("users").stream()]
    us = [u for u in us if u[0]!=st.session_state.username]
    us = sorted(us, key=lambda x: (x[1].get("skills",[""])[0].lower() if x[1].get("skills") else ""))
    for uname,d in us:
        if search and search.lower() not in d.get("role","").lower() and not any(search.lower() in s.lower() for s in d.get("skills",[])):
            continue
        st.markdown(f"### 👤 {uname}\n**Role**: {d.get('role','N/A')}\n**Bio**: {d.get('bio','')}\n**Skills**: {', '.join(d.get('skills',[])) or 'None'}\n---")



def channel_interface():
    st.markdown("<div class='chat-header'><h4>📢 SkillSwap Channels</h4></div>", unsafe_allow_html=True)
    channels = [c.to_dict() for c in db.collection("channels").stream()]
    st.sidebar.markdown("---")
    st.markdown("### Available Channels")
    for ch in channels:
        st.markdown(f"**{ch['name']}** — by {ch['created_by']}")
        if st.button(f"Follow {ch['name']}", key=f"follow_{ch['name']}"):
            db.collection("channels").document(ch['name'].lower()).update({"followers":firestore.ArrayUnion([st.session_state.username])})
            st.success("Now following.")

# === MAIN ===
if not st.session_state.logged_in:
    option = st.radio("Choose Option", ["🔐 Login", "📝 Sign Up", "🔑 Forgot Password"], key="auth_radio")

    if option == "🔐 Login":
        login_page()
    elif option == "📝 Sign Up":
        signup_page()
    elif option == "🔑 Forgot Password":
        password_reset()
else:
    st.markdown(f"<div class='chat-header'><h2 style='margin:0;'>🌐 SkillSwap</h2><span style='font-size:14px;'>Hello, {st.session_state.username}</span></div>", unsafe_allow_html=True)

    section = st.sidebar.radio(
        "📂 Menu",
        ["💬 Chat", "🧑‍💻 Profiles", "🚪 Rooms", "👤 Profile", "🔔 Notifications"],
        key="main_menu_radio"
    )

    st.sidebar.markdown("---")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    # Render only the selected section
    if section == "💬 Chat":
        chat_interface()
    elif section == "🧑‍💻 Profiles":
        view_profiles()
    elif section == "🚪 Rooms":
        channel_interface()
    elif section == "👤 Profile":
        profile_edit()
    elif section == "🔔 Notifications":
        show_notifications()

    st.markdown("---")
    st.caption(f"✅ Logged in as: **{st.session_state.username}**  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  Peer‑to‑peer learning with WhatsApp‑style UI")
