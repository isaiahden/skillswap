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
        color: black;
        display: flex; 
        align-items: center; 
        justify-content: center;
        font-weight: bold;
        font-size: 18px;
    }

    /* Messages container */
    .messages-container {
        height: 50px; 
        overflow-y: auto;
        padding: 15px;
        background: #0f172b;
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

    /* ✅ Back button styling fixed */
    .stButton button[title="Go back to contact selection"] {
        background-color: #34495e;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 14px;
        font-size: 14px;
        white-space: nowrap;
        display: inline-block;
        width: auto;
        height: auto;
        text-align: center;
        vertical-align: middle;
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
    import time
    from datetime import datetime
    
    # WhatsApp Group Chat Styling
    st.markdown("""
        <style>
        /* FORCE ALL TEXT TO BE VISIBLE */
        * {
            color: white !important;
        }
        
        /* WhatsApp Group Chat Container */
        .whatsapp-group-chat {
            background: linear-gradient(to bottom, #0f4c75, #3282b8, #0f4c75);
            min-height: 600px;
            border-radius: 10px;
            padding: 0;
            margin: 10px 0;
            position: relative;
            overflow: hidden;
        }
        
        /* Group Chat Header */
        .group-header {
            background: #075e54;
            color: white !important;
            padding: 15px 20px;
            border-radius: 10px 10px 0 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        
        .group-info {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .group-avatar {
            width: 45px;
            height: 45px;
            border-radius: 50%;
            background: #25d366;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            color: white;
        }
        
        .group-details h4 {
            margin: 0 !important;
            color: white !important;
            font-weight: 600 !important;
            font-size: 16px !important;
        }
        
        .group-members {
            color: rgba(255,255,255,0.8) !important;
            font-size: 12px;
            margin: 0;
        }
        
        .join-btn {
            background: #25d366 !important;
            color: white !important;
            border: none !important;
            padding: 8px 16px !important;
            border-radius: 20px !important;
            font-size: 12px !important;
            font-weight: 600 !important;
        }
        
        /* Group Messages Container */
        .group-messages-container {
            padding: 15px;
            height: 450px;
            overflow-y: auto;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="group-bg" patternUnits="userSpaceOnUse" width="100" height="100"><circle cx="25" cy="25" r="1" fill="rgba(255,255,255,0.03)"/><circle cx="75" cy="75" r="1" fill="rgba(255,255,255,0.03)"/></pattern></defs><rect width="100" height="100" fill="url(%23group-bg)"/></svg>');
            background-color: #0a1929;
        }
        
        /* Group Message Bubbles */
        .group-message-wrapper {
            margin-bottom: 12px;
            clear: both;
            display: flex;
            flex-direction: column;
        }
        
        .group-message-sent-wrapper {
            align-items: flex-end;
        }
        
        .group-message-received-wrapper {
            align-items: flex-start;
        }
        
        .group-message-bubble {
            max-width: 80%;
            padding: 6px 10px 4px 10px;
            border-radius: 15px;
            position: relative;
            box-shadow: 0 1px 2px rgba(0,0,0,0.3);
            word-wrap: break-word;
            line-height: 1.3;
        }
        
        .group-message-sent {
            background: #dcf8c6;
            color: #000 !important;
            border-bottom-right-radius: 3px;
            margin-left: auto;
        }
        
        .group-message-sent::after {
            content: '';
            position: absolute;
            bottom: 0;
            right: -6px;
            width: 0;
            height: 0;
            border: 6px solid transparent;
            border-left-color: #dcf8c6;
            border-bottom: 0;
        }
        
        .group-message-received {
            background: white;
            color: #000 !important;
            border-bottom-left-radius: 3px;
            margin-right: auto;
        }
        
        .group-message-received::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: -6px;
            width: 0;
            height: 0;
            border: 6px solid transparent;
            border-right-color: white;
            border-bottom: 0;
        }
        
        .group-sender-name {
            font-size: 12px !important;
            font-weight: 600 !important;
            color: #25d366 !important;
            margin-bottom: 2px !important;
        }
        
        .group-message-content {
            color: inherit !important;
            font-size: 14px;
            margin-bottom: 2px;
        }
        
        .group-message-time {
            font-size: 10px;
            color: rgba(0,0,0,0.5) !important;
            text-align: right;
            margin-top: 1px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 2px;
        }
        
        /* System Messages */
        .system-message {
            background: rgba(255,255,255,0.1);
            color: rgba(255,255,255,0.8) !important;
            text-align: center;
            padding: 6px 12px;
            border-radius: 10px;
            font-size: 12px;
            margin: 8px auto;
            max-width: 70%;
        }
        
        /* Group Input Area */
        .group-input-container {
            background: #f0f0f0;
            padding: 10px 15px;
            border-radius: 0 0 10px 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        /* Selectbox styling for groups */
        .stSelectbox label {
            color: white !important;
            font-weight: 600 !important;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.5) !important;
        }
        .stSelectbox div[role='button'] {
            color: black !important;
            background-color: white !important;
            border-radius: 25px !important;
            border: none !important;
            padding: 10px 16px !important;
        }
        
        /* Group text input */
        .stTextInput input {
            background-color: white !important;
            color: black !important;
            border: none !important;
            border-radius: 25px !important;
            padding: 12px 16px !important;
            font-size: 14px !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2) !important;
        }
        
        .stTextInput input::placeholder {
            color: rgba(0,0,0,0.5) !important;
        }
        
        /* Group send button */
        .stButton button[key="send_group_btn"] {
            background-color: #25d366 !important;
            color: white !important;
            border: none !important;
            border-radius: 50% !important;
            width: 45px !important;
            height: 45px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-size: 18px !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2) !important;
        }
        
        # Group Creation Section Styling */
        .stExpander {
            background: rgba(255, 255, 255, 0.05) !important;
            border-radius: 10px !important;
            margin-bottom: 20px !important;
        }
        
        .stExpander > div > div > div > div {
            color: white !important;
        }
        
        /* Create group button */
        button[key="create_group_btn"] {
            background: linear-gradient(45deg, #25d366, #128c7e) !important;
            color: white !important;
            border: none !important;
            border-radius: 25px !important;
            padding: 10px 20px !important;
            font-weight: 600 !important;
            box-shadow: 0 3px 10px rgba(37, 211, 102, 0.3) !important;
        }
        
        button[key="create_group_btn"]:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 5px 15px rgba(37, 211, 102, 0.4) !important;
        }
        
        /* Group info display */
        .group-info-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #25d366;
        }
        
        /* Admin badge */
        .admin-badge {
            background: #ff9800;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 600;
            margin-left: 5px;
        }
        
        /* System messages styling */
        .system-message {
            background: rgba(37, 211, 102, 0.2) !important;
            color: #25d366 !important;
            text-align: center;
            padding: 8px 15px;
            border-radius: 15px;
            font-size: 12px;
            margin: 10px auto;
            max-width: 80%;
            border: 1px solid rgba(37, 211, 102, 0.3);
        }
        
        /* No messages state */
        .no-group-messages {
            text-align: center;
            color: rgba(255,255,255,0.6) !important;
            font-style: italic;
            padding: 50px 20px;
        }
        
        /* Scrollbar for group chat */
        .group-messages-container::-webkit-scrollbar {
            width: 6px;
        }
        
        .group-messages-container::-webkit-scrollbar-track {
            background: rgba(255,255,255,0.1);
            border-radius: 3px;
        }
        
        .group-messages-container::-webkit-scrollbar-thumb {
            background: rgba(255,255,255,0.3);
            border-radius: 3px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='group-header'><h4>📢 SkillSwap Groups</h4></div>", unsafe_allow_html=True)
    
    # Group Creation Section
    with st.expander("➕ Create New Group", expanded=False):
        st.markdown("### 🆕 Create Your Own Group")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            new_group_name = st.text_input(
                "Group Name:", 
                placeholder="Enter group name (e.g., 'Python Developers', 'Design Hub')",
                key="new_group_name"
            )
        
        with col2:
            group_category = st.selectbox(
                "Category:",
                ["💻 Tech", "🎨 Design", "📈 Business", "🎓 Education", "🌟 General", "🏃 Fitness", "🍳 Cooking", "📚 Books"],
                key="group_category"
            )
        
        group_description = st.text_area(
            "Group Description:",
            placeholder="Describe what this group is about...",
            max_chars=200,
            key="group_description"
        )
        
        # Group privacy settings
        col3, col4 = st.columns([1, 1])
        
        with col3:
            is_private = st.checkbox("🔒 Private Group", help="Only invited members can join")
        
        with col4:
            max_members = st.number_input("👥 Max Members:", min_value=2, max_value=1000, value=100, key="max_members")
        
        if st.button("🚀 Create Group", key="create_group_btn", type="primary"):
            if new_group_name and new_group_name.strip():
                try:
                    # Check if group name already exists
                    existing_groups = [c.to_dict()["name"].lower() for c in db.collection("channels").stream()]
                    
                    if new_group_name.lower() in existing_groups:
                        st.error("❌ A group with this name already exists!")
                    else:
                        # Create new group
                        group_data = {
                            "name": new_group_name.strip(),
                            "description": group_description.strip() or "No description provided",
                            "category": group_category,
                            "creator": st.session_state.username,
                            "created_at": datetime.now(),
                            "followers": [st.session_state.username],  # Creator automatically joins
                            "admins": [st.session_state.username],  # Creator is admin
                            "is_private": is_private,
                            "max_members": max_members,
                            "member_count": 1
                        }
                        
                        # Add group to database
                        db.collection("channels").document(new_group_name.lower()).set(group_data)
                        
                        # Add welcome message
                        db.collection("channels").document(new_group_name.lower()).collection("messages").add({
                            "sender": "System",
                            "text": f"🎉 Welcome to {new_group_name}! This group was created by {st.session_state.username}.",
                            "timestamp": datetime.now(),
                            "is_system": True
                        })
                        
                        st.success(f"✅ Group '{new_group_name}' created successfully!")
                        st.balloons()
                        
                        # Clear form
                        st.session_state.new_group_name = ""
                        st.session_state.group_description = ""
                        
                        time.sleep(2)
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Error creating group: {e}")
            else:
                st.warning("⚠️ Please enter a group name!")
    
    # Get list of all channels
    try:
        channels_docs = db.collection("channels").stream()
        channels = []
        
        for c in channels_docs:
            channel_data = c.to_dict()
            channel_data["id"] = c.id
            channels.append(channel_data)
        
        # Sort channels by creation date (newest first)
        channels.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
        
        if not channels:
            st.info("🏗️ No groups available yet. Create the first group above!")
            return
        
        # Display available groups with details
        st.markdown("### 🌐 Available Groups")
        
        # Create channel selection with additional info
        channel_options = []
        for ch in channels:
            member_count = len(ch.get("followers", []))
            category = ch.get("category", "🌟 General")
            privacy = "🔒" if ch.get("is_private", False) else "🌐"
            
            option_text = f"{privacy} {ch['name']} ({member_count} members) - {category}"
            channel_options.append(option_text)
        
        selected_option = st.selectbox("🔍 Select a group:", [""] + channel_options)
        
        if not selected_option:
            st.info("💬 Select a group to start chatting")
            return
        
        # Extract selected channel name
        selected_channel = selected_option.split(" (")[0].replace("🔒 ", "").replace("🌐 ", "")
            
    except Exception as e:
        st.error(f"Error loading groups: {e}")
        return
    
    if not selected_channel:
        st.info("💬 Select a group to start chatting")
        return
    
    # WhatsApp-style group chat interface
    st.markdown('<div class="whatsapp-group-chat">', unsafe_allow_html=True)
    
    try:
        # Get channel data
        channel_ref = db.collection("channels").document(selected_channel.lower())
        channel_data = channel_ref.get().to_dict() or {}
        
        followers = channel_data.get("followers", [])
        admins = channel_data.get("admins", [])
        member_count = len(followers)
        is_member = st.session_state.username in followers
        is_admin = st.session_state.username in admins
        creator = channel_data.get("creator", "Unknown")
        description = channel_data.get("description", "No description")
        category = channel_data.get("category", "🌟 General")
        
        # Group header with enhanced info
        group_initial = selected_channel[0].upper() if selected_channel else "G"
        
        if is_member:
            admin_badge = '<span class="admin-badge">ADMIN</span>' if is_admin else ''
            
            st.markdown(f'''
                <div class="group-header">
                    <div class="group-info">
                        <div class="group-avatar">👥</div>
                        <div class="group-details">
                            <h4>{selected_channel} {admin_badge}</h4>
                            <div class="group-members">{member_count} members • {category}</div>
                        </div>
                    </div>
                </div>
                <div class="group-info-card">
                    <strong>📝 Description:</strong> {description}<br>
                    <strong>👑 Created by:</strong> {creator}<br>
                    <strong>📊 Category:</strong> {category}
                </div>
            ''', unsafe_allow_html=True)
        else:
            # Show join button if not a member
            privacy_status = "🔒 Private Group" if channel_data.get("is_private", False) else "🌐 Public Group"
            
            st.markdown(f'''
                <div class="group-header">
                    <div class="group-info">
                        <div class="group-avatar">👥</div>
                        <div class="group-details">
                            <h4>{selected_channel}</h4>
                            <div class="group-members">{member_count} members • {privacy_status}</div>
                        </div>
                    </div>
                </div>
                <div class="group-info-card">
                    <strong>📝 Description:</strong> {description}<br>
                    <strong>👑 Created by:</strong> {creator}<br>
                    <strong>📊 Category:</strong> {category}
                </div>
            ''', unsafe_allow_html=True)
            
            if st.button("🚀 Join Group", key="join_group_btn"):
                try:
                    # Check if group is at max capacity
                    max_members = channel_data.get("max_members", 100)
                    if member_count >= max_members:
                        st.error(f"❌ Group is full! Maximum {max_members} members allowed.")
                    else:
                        # Update member count and add user
                        channel_ref.update({
                            "followers": firestore.ArrayUnion([st.session_state.username]),
                            "member_count": member_count + 1
                        })
                        
                        # Add system message about new member
                        db.collection("channels").document(selected_channel.lower()).collection("messages").add({
                            "sender": "System",
                            "text": f"👋 {st.session_state.username} joined the group",
                            "timestamp": datetime.now(),
                            "is_system": True
                        })
                        
                        st.success("✅ Welcome to the group!")
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error joining group: {e}")
            
            st.info("👆 Join the group to participate in the chat")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        
        # Messages container
        st.markdown('<div class="group-messages-container">', unsafe_allow_html=True)
        
        # Load and display messages
        try:
            msgs = db.collection("channels").document(selected_channel.lower()).collection("messages").order_by("timestamp").stream()
            
            message_count = 0
            for msg in msgs:
                d = msg.to_dict()
                if not d:
                    continue
                    
                message_count += 1
                sender = d.get("sender", "Anonymous")
                text = d.get("text", "")
                
                # Format timestamp
                timestamp = d.get("timestamp")
                if timestamp:
                    try:
                        time_str = timestamp.strftime("%H:%M")
                    except:
                        time_str = "00:00"
                else:
                    time_str = "00:00"
                
                # Determine message type and styling
                is_own_message = sender == st.session_state.username
                is_system_message = d.get("is_system", False)
                
                if is_system_message:
                    # System messages (joins, leaves, etc.)
                    st.markdown(f'''
                        <div class="system-message">
                            {text}
                        </div>
                    ''', unsafe_allow_html=True)
                else:
                    # Regular user messages
                    wrapper_class = "group-message-sent-wrapper" if is_own_message else "group-message-received-wrapper"
                    bubble_class = "group-message-sent" if is_own_message else "group-message-received"
                    
                    # Display sender name only for received messages (like WhatsApp groups)
                    sender_display = "" if is_own_message else f'<div class="group-sender-name">{sender}</div>'
                    
                    st.markdown(f'''
                        <div class="group-message-wrapper {wrapper_class}">
                            <div class="group-message-bubble {bubble_class}">
                                {sender_display}
                                <div class="group-message-content">{text}</div>
                                <div class="group-message-time">
                                    {time_str}
                                    {'<span style="color: #4fc3f7;">✓✓</span>' if is_own_message else ''}
                                </div>
                            </div>
                        </div>
                    ''', unsafe_allow_html=True)
            
            if message_count == 0:
                st.markdown('<div class="no-group-messages">🎉 Be the first to send a message!</div>', unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"❌ Failed to load messages: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)  # Close messages container
        
        # Input area
        st.markdown('<div class="group-input-container">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([6, 1])
        
        with col1:
            msg = st.text_input(
                "", 
                key="group_msg_input", 
                placeholder=f"Message {selected_channel}...",
                label_visibility="collapsed"
            )
        
        with col2:
            send_button = st.button("➤", key="send_group_btn", help="Send message")
        
        st.markdown('</div>', unsafe_allow_html=True)  # Close input container
        
        # Send message functionality
        if send_button and msg and msg.strip():
            try:
                db.collection("channels").document(selected_channel.lower()).collection("messages").add({
                    "sender": st.session_state.username,
                    "text": msg.strip(),
                    "timestamp": datetime.now()
                })
                
                st.session_state.group_msg_input = ""
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error sending message: {e}")
        
        elif send_button and not msg.strip():
            st.warning("⚠️ Please enter a message")
        
    except Exception as e:
        st.error(f"❌ Error loading group: {e}")
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close whatsapp-group-chat
    
    # Live chat controls
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔄 Refresh", help="Get new messages"):
            st.rerun()
    
    with col2:
        live_mode = st.checkbox("🔴 Live Group Chat", value=True, help="Real-time updates")
    
    # Live chat functionality
    if live_mode:
        time.sleep(1.5)  # Faster refresh for group chats
        st.rerun()


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
